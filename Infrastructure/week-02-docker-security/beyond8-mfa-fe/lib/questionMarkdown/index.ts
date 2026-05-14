/**
 * Client-side quiz markdown helpers (ported from beyond8-mfa/supports:
 * create_questions_list.py + refactor_markdown.py). Diacritics restoration is skipped.
 */

/** Một chữ cái làm nhãn lựa chọn (A–Z), theo sau là . ) ： : — hỗ trợ OCR / nhiều lựa chọn hơn A–F. */
const OPTION_LINE_RE = /^([A-Za-z])\s*[\.)：:]\s*(.*)$/;
const NUMBERED_STEM_RE = /^\d{1,3}\.\s+(.*)$/;
const ANSWER_MARKER_RE = /^(?:ANSWER|Đáp án)\s*:\s*.+$/i;

const ANSWER_RE = /^(?:ANSWER|Đáp án)\s*:\s*(.*)$/i;
const OPTION_RE = /^([A-Za-z])[\.)]\s*(.*)$/;
const REFACTOR_NUMBERED_STEM_RE = /^\d{1,3}\.\s+(.*)$/;

function normalizeWs(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

export function parseAnswerKeys(rawAnswer: string): string[] {
  const cleaned = normalizeWs(rawAnswer);
  const seen = new Set<string>();
  const unique: string[] = [];
  for (const part of cleaned.split(/[,;\s|/]+/)) {
    const t = part.trim();
    if (t.length === 1 && /[A-Za-z]/.test(t)) {
      const k = t.toUpperCase();
      if (!seen.has(k)) {
        seen.add(k);
        unique.push(k);
      }
    }
  }
  return unique;
}

export type ParsedOption = { label: string; text: string };

export function parseRawQuestionBlock(rawBlock: string): { stem: string; options: ParsedOption[] } {
  const stemLines: string[] = [];
  const optionParts: Record<string, string[]> = {};
  const optionOrder: string[] = [];
  let currentOption: string | null = null;

  for (const rawLine of rawBlock.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;

    const optMatch = line.match(OPTION_LINE_RE);
    if (optMatch) {
      const label = optMatch[1].toUpperCase();
      const text = normalizeWs(optMatch[2]);
      if (!optionParts[label]) {
        optionParts[label] = [];
        optionOrder.push(label);
      }
      optionParts[label].push(text);
      currentOption = label;
      continue;
    }

    if (currentOption !== null) {
      const arr = optionParts[currentOption];
      if (arr) arr.push(normalizeWs(line));
    } else {
      const numbered = line.match(NUMBERED_STEM_RE);
      stemLines.push(numbered ? numbered[1] : line);
    }
  }

  const stem = normalizeWs(stemLines.join(" "));
  if (!stem) throw new Error("Không nhận diện được nội dung câu hỏi.");
  if (optionOrder.length < 2) throw new Error("Cần ít nhất 2 options (ví dụ A, B).");

  const options: ParsedOption[] = [];
  for (const label of optionOrder) {
    const parts = optionParts[label];
    const text = normalizeWs((parts ?? []).join(" "));
    if (!text) throw new Error(`Nội dung option ${label} đang rỗng.`);
    options.push({ label, text });
  }

  return { stem, options };
}

/** Kết quả tách OCR / văn dán: nếu `structured`, điền stem + options + answer; ngược lại gộp raw vào một ô stem. */
export type OcrQuestionParseResult = {
  stem: string;
  options: ParsedOption[];
  answer: string;
  structured: boolean;
};

/**
 * Parser lỏng cho OCR: nhãn lựa chọn một chữ cái A–Z (A. / A) / A： …), nối dòng tiếp theo vào lựa chọn đang mở,
 * bỏ qua dòng `Đáp án:` / `ANSWER:`. Không giới hạn A–F.
 */
export function parseLooseOcrQuestionText(rawBlock: string): OcrQuestionParseResult {
  let answerKeysFromLine: string[] = [];
  const stemLines: string[] = [];
  const optionParts: Record<string, string[]> = {};
  const optionOrder: string[] = [];
  let currentOption: string | null = null;

  for (const rawLine of rawBlock.replace(/\r\n/g, "\n").split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;

    const answerMatch = line.match(/^(?:ANSWER|Đáp án)\s*:\s*(.+)$/i);
    if (answerMatch) {
      answerKeysFromLine = parseAnswerKeys(answerMatch[1]);
      continue;
    }

    const optMatch = line.match(OPTION_LINE_RE);
    if (optMatch) {
      const letter = optMatch[1].toUpperCase();
      const text = normalizeWs(optMatch[2]);
      if (!optionParts[letter]) {
        optionParts[letter] = [];
        optionOrder.push(letter);
      }
      optionParts[letter].push(text);
      currentOption = letter;
      continue;
    }

    if (currentOption !== null) {
      const arr = optionParts[currentOption];
      if (arr) arr.push(normalizeWs(line));
    } else {
      const numbered = line.match(NUMBERED_STEM_RE);
      stemLines.push(numbered ? numbered[1] : line);
    }
  }

  const stem = normalizeWs(stemLines.join(" "));
  const options: ParsedOption[] = [];
  for (const label of optionOrder) {
    const parts = optionParts[label];
    const text = normalizeWs((parts ?? []).join(" "));
    if (text) options.push({ label, text });
  }

  if (stem.length > 0 && options.length >= 2) {
    const labelSet = new Set(options.map((o) => o.label));
    const filtered = answerKeysFromLine.filter((k) => labelSet.has(k));
    const answer = filtered.length > 0 ? filtered.join(",") : (options[0]?.label ?? "A");
    return { stem, options, answer, structured: true };
  }

  return {
    stem: normalizeWs(rawBlock.replace(/\r\n/g, "\n")),
    options: [],
    answer: "",
    structured: false,
  };
}

export function renderQuestionBlock(
  stem: string,
  options: ParsedOption[],
  answerKeys: string[]
): string {
  const lines: string[] = [stem, ""];
  for (const { label, text } of options) {
    lines.push(`${label}. ${text}`);
    lines.push("");
  }
  lines.push(`Đáp án: ${answerKeys.join(", ")}`);
  lines.push("");
  return lines.join("\n");
}

interface QuestionBlock {
  stemLines: string[];
  options: ParsedOption[];
  answer: string;
}

function parseQuestionBlockLines(lines: string[]): QuestionBlock | null {
  if (!lines.length) return null;

  let answerIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (ANSWER_RE.test(lines[i].trim())) {
      answerIdx = i;
      break;
    }
  }
  if (answerIdx === -1) return null;

  const body = lines.slice(0, answerIdx);
  const answerLine = lines[answerIdx];
  const answerMatch = answerLine.trim().match(ANSWER_RE);
  if (!answerMatch) return null;
  const answer = normalizeWs(answerMatch[1]);

  const stemLines: string[] = [];
  const options: ParsedOption[] = [];
  let currentOptionIdx = -1;

  for (const rawLine of body) {
    const line = rawLine.trim();
    if (!line) continue;

    const optionMatch = line.match(OPTION_RE);
    if (optionMatch) {
      const label = optionMatch[1];
      const text = normalizeWs(optionMatch[2]);
      options.push({ label, text });
      currentOptionIdx = options.length - 1;
      continue;
    }

    if (currentOptionIdx >= 0) {
      const prev = options[currentOptionIdx];
      if (prev) {
        options[currentOptionIdx] = {
          label: prev.label,
          text: normalizeWs(`${prev.text} ${line}`),
        };
      }
    } else {
      const numbered = line.match(REFACTOR_NUMBERED_STEM_RE);
      stemLines.push(numbered ? numbered[1] : line);
    }
  }

  if (!stemLines.length) return null;
  const mergedStem = normalizeWs(stemLines.join(" "));
  return { stemLines: [mergedStem], options, answer };
}

/** Refactor full file text to numbered blocks (1. stem …áp án), matching Python refactor_markdown_text (no diacritics pass). */
export function refactorMarkdownText(rawText: string): string {
  const lines = rawText.replace(/\r\n/g, "\n").split("\n").map((l) => l.replace(/\r/g, "").replace(/[\t]*$/, ""));

  const chunks: string[][] = [];
  let current: string[] = [];
  for (const line of lines) {
    current.push(line);
    if (ANSWER_RE.test(line.trim())) {
      chunks.push(current);
      current = [];
    }
  }
  if (current.some((item) => item.trim())) {
    throw new Error("Unparsed trailing content detected; aborting overwrite.");
  }

  const parsedBlocks: QuestionBlock[] = [];
  for (const chunk of chunks) {
    const block = parseQuestionBlockLines(chunk);
    if (block) parsedBlocks.push(block);
  }

  if (!parsedBlocks.length) {
    throw new Error("No valid question blocks found; aborting overwrite.");
  }

  const outLines: string[] = [];
  for (let idx = 0; idx < parsedBlocks.length; idx++) {
    const block = parsedBlocks[idx];
    if (!block) continue;
    const stem0 = block.stemLines[0];
    if (stem0 === undefined) continue;
    outLines.push(`${idx + 1}. ${stem0}`);
    outLines.push("");
    for (const { label, text } of block.options) {
      outLines.push(`${label}. ${text}`);
      outLines.push("");
    }
    outLines.push(`Đáp án: ${block.answer}`);
    outLines.push("");
  }

  return `${outLines.join("\n").replace(/\n+$/, "")}\n`;
}

export function fileHasAnswerLine(content: string): boolean {
  return ANSWER_MARKER_RE.test(content);
}
