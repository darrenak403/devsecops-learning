"use client";

import type { ClipboardEvent as ReactClipboardEvent, Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ClipboardPaste, Image as ImageIcon, Loader2, Plus, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { QuestionDraft } from "@/lib/types/source-questions-dialog";
import { emptyOption } from "@/lib/utils/questionDraft";
import type { BankCheckDuplicateResponse } from "@/lib/api/services/fetchQuestionSources";
import { recognizeTextFromImageFile } from "@/lib/image-ocr";
import { parseLooseOcrQuestionText } from "@/lib/questionMarkdown";
import { cn } from "@/lib/utils/cn";

function parseAnswerLabels(answer: string): Set<string> {
  const out = new Set<string>();
  for (const part of answer.split(/[,;]/)) {
    const t = part.trim().toUpperCase();
    if (t) out.add(t);
  }
  return out;
}

function buildAnswerString(d: QuestionDraft, selected: Set<string>): string {
  const parts: string[] = [];
  for (const opt of d.options) {
    const raw = opt.label.trim();
    if (!raw) continue;
    if (selected.has(raw.toUpperCase())) {
      parts.push(raw.toUpperCase());
    }
  }
  return parts.join(",");
}

function shortHashDisplay(normalizedHash: string): string {
  const raw = normalizedHash.startsWith("sha256:") ? normalizedHash.slice(7) : normalizedHash;
  return raw.length <= 14 ? raw : `${raw.slice(0, 12)}…`;
}

export type QuestionEditorMode = "empty" | "compose" | "edit";

interface QuestionEditorPanelProps {
  draft: QuestionDraft | null;
  setDraft: Dispatch<SetStateAction<QuestionDraft | null>>;
  mode: QuestionEditorMode;
  isDirty: boolean;
  patchPending: boolean;
  appendPending: boolean;
  checkPending: boolean;
  deletePending: boolean;
  bankCheck: BankCheckDuplicateResponse | null;
  onCheckBank: () => void;
  onSaveEdit: () => void;
  onSaveNew: () => void;
  onDeselect: () => void;
  onRequestDelete: () => void;
}

export function QuestionEditorPanel({
  draft,
  setDraft,
  mode,
  isDirty,
  patchPending,
  appendPending,
  checkPending,
  deletePending,
  bankCheck,
  onCheckBank,
  onSaveEdit,
  onSaveNew,
  onDeselect,
  onRequestDelete,
}: QuestionEditorPanelProps) {
  const editorSurfaceRef = useRef<HTMLDivElement>(null);
  const [isOcrExtracting, setIsOcrExtracting] = useState(false);
  const [ocrProgress, setOcrProgress] = useState<number | null>(null);

  const mergeOcrIntoStem = useCallback(
    (text: string) => {
      setDraft((d) => {
        if (!d) return d;
        const next = d.stem.trim() ? `${d.stem.trim()}\n\n${text}` : text;
        return { ...d, stem: next };
      });
    },
    [setDraft]
  );

  const applyOcrRecognizedText = useCallback(
    (text: string) => {
      const parsed = parseLooseOcrQuestionText(text);
      if (parsed.structured) {
        setDraft((d) => {
          if (!d) return d;
          return { stem: parsed.stem, options: parsed.options, answer: parsed.answer };
        });
        toast.success("Đã đọc ảnh — đã tách đề và các lựa chọn; kiểm tra đáp án.");
      } else {
        mergeOcrIntoStem(text);
        toast.success(
          "Đã đọc ảnh — chưa nhận dạng đủ dạng (cần ít nhất 2 dòng kiểu A. …, B. …); nội dung gộp vào ô trên."
        );
      }
    },
    [setDraft, mergeOcrIntoStem]
  );

  const runOcrOnFile = useCallback(
    async (file: File | null) => {
      if (!file) return;
      setIsOcrExtracting(true);
      setOcrProgress(0);
      try {
        const text = await recognizeTextFromImageFile(file, { onProgress: setOcrProgress });
        if (!text) {
          toast.error("Không đọc được nội dung từ ảnh");
          return;
        }
        applyOcrRecognizedText(text);
      } catch {
        toast.error("OCR thất bại. Thử ảnh rõ hơn hoặc cắt nhỏ vùng chữ.");
      } finally {
        setIsOcrExtracting(false);
        setOcrProgress(null);
      }
    },
    [applyOcrRecognizedText]
  );

  /** Dán ảnh từ `clipboardData` (ô nội dung / vùng dashed) — giống QuestionEditorSection. */
  const tryHandleImagePasteFromDataTransfer = useCallback(
    (event: ReactClipboardEvent<Element> | ClipboardEvent) => {
      const items = Array.from(event.clipboardData?.items ?? []);
      const imageItem = items.find((item) => item.type.startsWith("image/"));
      if (!imageItem) return false;
      event.preventDefault();
      const file = imageItem.getAsFile();
      if (!file) {
        toast.error("Không đọc được ảnh từ clipboard");
        return true;
      }
      void runOcrOnFile(file);
      return true;
    },
    [runOcrOnFile]
  );

  const handlePasteImageFromClipboardApi = useCallback(async () => {
    if (!navigator.clipboard?.read) {
      toast.error(
        "Trình duyệt chưa hỗ trợ nút Paste ảnh — hãy dán trực tiếp (Ctrl+V) vào ô nội dung hoặc vùng bên dưới."
      );
      return;
    }
    try {
      const clipboardItems = await navigator.clipboard.read();
      for (const item of clipboardItems) {
        const imageType = item.types.find((type) => type.startsWith("image/"));
        if (!imageType) continue;
        const blob = await item.getType(imageType);
        const file = new File([blob], "clipboard-image.png", { type: imageType });
        await runOcrOnFile(file);
        return;
      }
      toast.error("Clipboard chưa có ảnh để OCR");
    } catch {
      toast.error("Không đọc được clipboard. Hãy cấp quyền rồi thử lại.");
    }
  }, [runOcrOnFile]);

  useEffect(() => {
    if (mode === "empty" || !draft) return;

    const onWindowPaste = (event: ClipboardEvent) => {
      const t = event.target;
      if (!(t instanceof Node) || !editorSurfaceRef.current?.contains(t)) return;
      const items = Array.from(event.clipboardData?.items ?? []);
      const imageItem = items.find((item) => item.type.startsWith("image/"));
      if (!imageItem) return;
      const file = imageItem.getAsFile();
      if (!file) return;
      event.preventDefault();
      void runOcrOnFile(file);
    };

    window.addEventListener("paste", onWindowPaste);
    return () => window.removeEventListener("paste", onWindowPaste);
  }, [mode, draft, runOcrOnFile]);

  const answerLabelRows = useMemo(() => {
    if (!draft) return [];
    return draft.options.map((opt, index) => ({
      index,
      display: opt.label.trim() || `Lựa chọn ${index + 1}`,
      key: opt.label.trim() || `opt-${index}`,
      norm: opt.label.trim().toUpperCase(),
    }));
  }, [draft]);

  const selectedAnswerNorms = useMemo(
    () => (draft ? parseAnswerLabels(draft.answer) : new Set<string>()),
    [draft]
  );

  const toggleAnswerLabel = useCallback(
    (labelNorm: string) => {
      if (!labelNorm) return;
      setDraft((d) => {
        if (!d) return d;
        const sel = parseAnswerLabels(d.answer);
        if (sel.has(labelNorm)) {
          sel.delete(labelNorm);
        } else {
          sel.add(labelNorm);
        }
        return { ...d, answer: buildAnswerString(d, sel) };
      });
    },
    [setDraft]
  );

  const clearCorrectAnswer = useCallback(() => {
    setDraft((d) => (d ? { ...d, answer: "" } : d));
  }, [setDraft]);

  if (mode === "empty" || !draft) {
    return (
      <div className="flex min-h-0 flex-col gap-3 overflow-y-auto px-4 py-4 sm:px-6">
        <p className="text-sm text-muted-foreground">
          Chọn một câu bên trái để xem và chỉnh sửa, hoặc bấm <strong>Thêm câu hỏi</strong> để soạn
          câu mới — dán ảnh (Ctrl+V) / Paste ảnh để OCR, hoặc nhập tay, rồi kiểm tra ngân hàng và
          lưu.
        </p>
      </div>
    );
  }

  const hasLabeledOptions = answerLabelRows.some((r) => r.norm.length > 0);
  const canSubmitBody = Boolean(draft.stem.trim());
  const saveEditDisabled = patchPending || !canSubmitBody || !isDirty;
  const saveNewDisabled = appendPending || !canSubmitBody;
  const checkDisabled = checkPending || !canSubmitBody;
  const anySavePending = patchPending || appendPending;

  return (
    <div
      ref={editorSurfaceRef}
      className="flex min-h-0 flex-col gap-3 overflow-y-auto px-4 py-4 sm:px-6"
    >
      {mode === "compose" ? (
        <p className="text-xs text-muted-foreground">
          Soạn nội dung mới — chưa lưu vào đề. Kiểm tra trùng ngân hàng trước khi lưu nếu cần.
        </p>
      ) : null}

      <div className="space-y-2">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <ImageIcon className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
            <label htmlFor="q-stem">Nội dung câu hỏi</label>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] text-muted-foreground sm:text-right">
              Vùng soạn: dán ảnh (Ctrl+V) — hoặc bấm Paste ảnh
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              disabled={isOcrExtracting}
              onClick={() => void handlePasteImageFromClipboardApi()}
            >
              {isOcrExtracting ? (
                <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" aria-hidden />
              ) : (
                <ClipboardPaste className="h-3.5 w-3.5 shrink-0" aria-hidden />
              )}
              Paste ảnh
            </Button>
            {isOcrExtracting && typeof ocrProgress === "number" ? (
              <span className="text-[11px] text-muted-foreground tabular-nums">{ocrProgress}%</span>
            ) : null}
          </div>
        </div>
        <div
          role="textbox"
          tabIndex={0}
          aria-label="Vùng dán ảnh để nhận dạng chữ"
          onPaste={(e) => {
            void tryHandleImagePasteFromDataTransfer(e);
          }}
          className="flex min-h-11 cursor-pointer items-center rounded-lg border-2 border-dashed border-border bg-muted/25 px-3 py-2 text-xs leading-snug text-muted-foreground outline-none transition-colors hover:border-primary/40 hover:bg-muted/40 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="flex items-start gap-2">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
            Kích hoạt vùng này rồi dán ảnh câu hỏi — hoặc dán khi đang gõ trong ô bên dưới (ảnh,
            không phải chữ).
          </span>
        </div>
        {isOcrExtracting ? (
          <div
            className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={typeof ocrProgress === "number" ? ocrProgress : undefined}
          >
            <div
              className="h-full bg-primary transition-[width] duration-150"
              style={{
                width: `${typeof ocrProgress === "number" ? Math.min(100, Math.max(0, ocrProgress)) : 12}%`,
              }}
            />
          </div>
        ) : null}
        <Textarea
          id="q-stem"
          value={draft.stem}
          onChange={(e) => setDraft((d) => (d ? { ...d, stem: e.target.value } : d))}
          onPaste={(e) => {
            void tryHandleImagePasteFromDataTransfer(e);
          }}
          className="min-h-[140px] text-sm"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-medium text-muted-foreground">Đáp án</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 gap-1 text-xs"
            onClick={() =>
              setDraft((d) => (d ? { ...d, options: [...d.options, emptyOption()] } : d))
            }
          >
            <Plus className="h-3.5 w-3.5" />
            Thêm lựa chọn
          </Button>
        </div>
        <div className="space-y-2">
          {draft.options.map((opt, idx) => (
            <div key={idx} className="flex gap-2">
              <Input
                className="h-9 w-14 shrink-0 font-mono text-sm"
                placeholder="A"
                value={opt.label}
                maxLength={4}
                onChange={(e) =>
                  setDraft((d) => {
                    if (!d) return d;
                    const next = [...d.options];
                    next[idx] = { ...next[idx], label: e.target.value };
                    return { ...d, options: next };
                  })
                }
                aria-label={`Nhãn đáp án ${idx + 1}`}
              />
              <Input
                className="h-9 flex-1 text-sm"
                placeholder="Nội dung lựa chọn"
                value={opt.text}
                onChange={(e) =>
                  setDraft((d) => {
                    if (!d) return d;
                    const next = [...d.options];
                    next[idx] = { ...next[idx], text: e.target.value };
                    return { ...d, options: next };
                  })
                }
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-9 w-9 shrink-0 text-muted-foreground"
                disabled={draft.options.length <= 1}
                onClick={() =>
                  setDraft((d) => {
                    if (!d || d.options.length <= 1) return d;
                    return {
                      ...d,
                      options: d.options.filter((_, i) => i !== idx),
                    };
                  })
                }
                aria-label="Xóa lựa chọn"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs font-medium text-muted-foreground">Đáp án đúng</span>
          {draft.answer ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 text-[11px] text-muted-foreground"
              onClick={clearCorrectAnswer}
            >
              Xóa lựa chọn
            </Button>
          ) : null}
        </div>
        {!hasLabeledOptions ? (
          <p className="text-xs text-muted-foreground">
            Nhập nhãn cột đầu (A, B, C…) cho từng lựa chọn để bật nút chọn đáp án đúng.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2" role="group" aria-label="Chọn đáp án đúng">
            {answerLabelRows.map((row) => {
              if (!row.norm) {
                return (
                  <Button
                    key={row.key}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-9 min-w-9 font-mono text-xs opacity-50"
                    disabled
                  >
                    {row.display}
                  </Button>
                );
              }
              const selected = selectedAnswerNorms.has(row.norm);
              return (
                <Button
                  key={row.key}
                  type="button"
                  variant={selected ? "default" : "outline"}
                  size="sm"
                  className={cn("h-9 min-w-9 font-mono text-xs", selected && "shadow-sm")}
                  onClick={() => toggleAnswerLabel(row.norm)}
                  aria-pressed={selected}
                >
                  {draft.options[row.index]?.label.trim() || row.norm}
                </Button>
              );
            })}
          </div>
        )}
        {hasLabeledOptions && draft.answer ? (
          <p className="font-mono text-[11px] text-muted-foreground">
            Lưu dưới dạng: <span className="text-foreground">{draft.answer}</span>
          </p>
        ) : null}
      </div>

      {bankCheck ? (
        <div
          className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs"
          role="status"
        >
          <span className="font-medium text-foreground">
            {bankCheck.existsInBank
              ? "Đã có trong ngân hàng tổng hợp (cau-hoi-tong-hop)."
              : "Chưa có trong ngân hàng — có thể là câu mới."}
          </span>
          <span className="mt-1 block font-mono text-[11px] text-muted-foreground">
            Hash: {shortHashDisplay(bankCheck.normalizedHash)}
          </span>
        </div>
      ) : null}

      <DialogFooter className="flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:space-x-0">
        <div className="flex w-full flex-wrap gap-2 sm:w-auto">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onDeselect}
            disabled={anySavePending}
          >
            {mode === "compose" ? "Hủy soạn" : "Bỏ chọn"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={checkDisabled}
            onClick={onCheckBank}
          >
            {checkPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Đang kiểm tra…
              </>
            ) : (
              "Kiểm tra ngân hàng"
            )}
          </Button>
          {mode === "edit" ? (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              disabled={deletePending || anySavePending}
              onClick={onRequestDelete}
            >
              {deletePending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Đang xóa…
                </>
              ) : (
                "Xóa câu"
              )}
            </Button>
          ) : null}
        </div>
        <div className="flex w-full justify-end gap-2 sm:w-auto">
          {mode === "compose" ? (
            <Button type="button" size="sm" disabled={saveNewDisabled} onClick={onSaveNew}>
              {appendPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Đang lưu…
                </>
              ) : (
                "Lưu vào đề"
              )}
            </Button>
          ) : (
            <Button type="button" size="sm" disabled={saveEditDisabled} onClick={onSaveEdit}>
              {patchPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Đang lưu…
                </>
              ) : (
                "Lưu thay đổi"
              )}
            </Button>
          )}
        </div>
      </DialogFooter>
    </div>
  );
}
