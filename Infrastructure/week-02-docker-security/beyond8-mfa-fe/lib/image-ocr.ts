/**
 * OCR ảnh (Tesseract eng+vie) — dùng chung mọi màn: deck markdown, admin sửa câu, v.v.
 */

export function normalizeOcrText(text: string): string {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export async function recognizeTextFromImageFile(
  file: File,
  options?: { onProgress?: (percent: number) => void }
): Promise<string> {
  const Tesseract = await import("tesseract.js");
  const result = await Tesseract.recognize(file, "eng+vie", {
    logger: (m) => {
      if (m.status === "recognizing text" && typeof m.progress === "number") {
        options?.onProgress?.(Math.round(m.progress * 100));
      }
    },
  });
  return normalizeOcrText(result.data.text);
}
