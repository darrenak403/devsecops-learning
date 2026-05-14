"use client";

import {
  type ClipboardEvent as ReactClipboardEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  forwardRef,
  useCallback,
  useEffect,
  useId,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { toast } from "sonner";
import {
  Check,
  ChevronDown,
  ChevronRight,
  ClipboardPaste,
  FileText,
  ImageIcon,
  Trash2,
  PencilLine,
  Sparkles,
  Telescope,
} from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { recognizeTextFromImageFile } from "@/lib/image-ocr";
import { parseRawQuestionBlock } from "@/lib/questionMarkdown";
import { cn } from "@/lib/utils/cn";

/** Chiều ngang cột đáp án wizard (px) — để flex thu nhỏ phần stem, không đè lên nhau */
const WIZARD_ANSWER_PANEL_W = 148;

function isKeyboardTypingTarget(target: EventTarget | null): boolean {
  const el = target instanceof HTMLElement ? target : null;
  if (!el) return false;
  if (el.isContentEditable) return true;
  const tag = el.tagName;
  if (tag === "TEXTAREA" || tag === "SELECT") return true;
  if (tag === "INPUT") {
    const input = el as HTMLInputElement;
    const type = (input.type ?? "text").toLowerCase();
    if (
      type === "button" ||
      type === "checkbox" ||
      type === "radio" ||
      type === "submit" ||
      type === "reset" ||
      type === "file" ||
      type === "hidden"
    ) {
      return false;
    }
    return true;
  }
  return false;
}

function letterFromKeyCode(code: string): string | null {
  if (!code.startsWith("Key")) return null;
  const ch = code.slice(3);
  return ch.length === 1 ? ch.toUpperCase() : null;
}

export type QuestionEditorWizardHandle = {
  /** Đọc ảnh từ clipboard API (giống nút Paste ảnh trong form). */
  pasteImage: () => Promise<void>;
};

type QuestionEditorProps = {
  rawBlock: string;
  accumulatedMd: string;
  optionLabels: string[];
  answerSelected: Record<string, boolean>;
  onRawBlockChange: (value: string) => void;
  onToggleAnswer: (label: string) => void;
  onAppendQuestion: () => void;
  onAccumulatedMdChange: (value: string) => void;
  wizardMode?: boolean;
  onProceedToPreview?: () => void;
  onOcrBusyChange?: (busy: boolean) => void;
};

export const QuestionEditorSection = forwardRef<QuestionEditorWizardHandle, QuestionEditorProps>(
  function QuestionEditorSection(props, ref) {
    const {
      rawBlock,
      accumulatedMd,
      optionLabels,
      answerSelected,
      onRawBlockChange,
      onToggleAnswer,
      onAppendQuestion,
      onAccumulatedMdChange,
      wizardMode = false,
      onProceedToPreview,
      onOcrBusyChange,
    } = props;
    const [ocrProgress, setOcrProgress] = useState<number | null>(null);
    const [isExtracting, setIsExtracting] = useState(false);
    const [mobileTab, setMobileTab] = useState<"compose" | "preview">("compose");
    const [clearMdDialogOpen, setClearMdDialogOpen] = useState(false);
    const headingId = useId();
    const composeLabelId = useId();
    const wizardAnswerHeadingId = useId();

    const previewStats = useMemo(() => {
      const len = accumulatedMd.length;
      const lines = accumulatedMd ? accumulatedMd.split("\n").length : 0;
      return { len, lines };
    }, [accumulatedMd]);

    const wizardParsedOptions = useMemo(() => {
      if (!wizardMode) return [];
      const t = rawBlock.trim();
      if (!t) return [];
      try {
        return parseRawQuestionBlock(t).options;
      } catch {
        return [];
      }
    }, [wizardMode, rawBlock]);

    const hasSelectedAnswer = useMemo(
      () => Object.values(answerSelected).some(Boolean),
      [answerSelected]
    );

    const prefersReducedMotion = useReducedMotion();
    const appendAfterSheetCloseRef = useRef(false);
    const [sheetForcedClosed, setSheetForcedClosed] = useState(false);

    const answerSheetOpen = wizardMode && wizardParsedOptions.length > 0 && !sheetForcedClosed;

    useEffect(() => {
      if (wizardParsedOptions.length === 0) {
        setSheetForcedClosed(false);
      }
    }, [wizardParsedOptions.length]);

    const handleSheetExitComplete = useCallback(() => {
      if (appendAfterSheetCloseRef.current) {
        appendAfterSheetCloseRef.current = false;
        onAppendQuestion();
      }
      setSheetForcedClosed(false);
    }, [onAppendQuestion]);

    const handleWizardAppendQuestion = useCallback(() => {
      if (!wizardMode || sheetForcedClosed) return;
      if (!rawBlock.trim() || !hasSelectedAnswer) return;
      appendAfterSheetCloseRef.current = true;
      setSheetForcedClosed(true);
    }, [wizardMode, sheetForcedClosed, rawBlock, hasSelectedAnswer]);

    const handleComposeKeyDown = useCallback(
      (e: ReactKeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key !== "Enter" || !(e.metaKey || e.ctrlKey)) return;
        e.preventDefault();
        if (wizardMode) {
          if (!rawBlock.trim() || !hasSelectedAnswer || sheetForcedClosed) return;
          handleWizardAppendQuestion();
        } else {
          onAppendQuestion();
        }
      },
      [
        wizardMode,
        rawBlock,
        hasSelectedAnswer,
        sheetForcedClosed,
        handleWizardAppendQuestion,
        onAppendQuestion,
      ]
    );

    useEffect(() => {
      const onGlobalKeyDown = (e: KeyboardEvent) => {
        if (e.defaultPrevented || e.repeat) return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        if (clearMdDialogOpen) return;
        if (isKeyboardTypingTarget(e.target)) return;

        const letter = letterFromKeyCode(e.code);
        if (!letter) return;

        if (letter === "Q") {
          if (wizardMode) {
            if (!rawBlock.trim() || !hasSelectedAnswer || sheetForcedClosed) return;
            e.preventDefault();
            handleWizardAppendQuestion();
          } else {
            e.preventDefault();
            onAppendQuestion();
          }
          return;
        }

        const labels: string[] =
          wizardMode && answerSheetOpen
            ? wizardParsedOptions.map((o) => o.label)
            : wizardMode
              ? []
              : optionLabels;

        const matched = labels.find((l) => l.toUpperCase() === letter);
        if (!matched) return;

        e.preventDefault();
        onToggleAnswer(matched);
      };

      window.addEventListener("keydown", onGlobalKeyDown);
      return () => window.removeEventListener("keydown", onGlobalKeyDown);
    }, [
      clearMdDialogOpen,
      wizardMode,
      answerSheetOpen,
      wizardParsedOptions,
      optionLabels,
      rawBlock,
      hasSelectedAnswer,
      sheetForcedClosed,
      handleWizardAppendQuestion,
      onAppendQuestion,
      onToggleAnswer,
    ]);

    const sheetSpring = prefersReducedMotion
      ? { duration: 0.2 }
      : { type: "spring" as const, stiffness: 420, damping: 38, mass: 0.85 };

    const openClearMdDialog = useCallback(() => {
      if (!accumulatedMd.trim()) return;
      setClearMdDialogOpen(true);
    }, [accumulatedMd]);

    useEffect(() => {
      if (!accumulatedMd.trim()) setClearMdDialogOpen(false);
    }, [accumulatedMd]);

    const handleExtractFromClipboard = async (event: ReactClipboardEvent<HTMLDivElement>) => {
      const items = Array.from(event.clipboardData.items);
      const imageItem = items.find((item) => item.type.startsWith("image/"));
      if (!imageItem) return;

      event.preventDefault();
      const file = imageItem.getAsFile();
      if (!file) {
        toast.error("Không đọc được ảnh từ clipboard");
        return;
      }
      await handleExtractFromImage(file);
    };

    const handleExtractFromImage = useCallback(
      async (file: File | null) => {
        if (!file) return;
        setIsExtracting(true);
        setOcrProgress(0);
        try {
          const text = await recognizeTextFromImageFile(file, { onProgress: setOcrProgress });
          if (!text) {
            toast.error("Không đọc được nội dung từ ảnh");
            return;
          }
          onRawBlockChange(text);
          toast.success("Đã đọc ảnh, kiểm tra lại và chọn đáp án đúng");
        } catch {
          toast.error("OCR thất bại. Thử ảnh rõ hơn hoặc cắt nhỏ câu hỏi.");
        } finally {
          setIsExtracting(false);
          setOcrProgress(null);
        }
      },
      [onRawBlockChange]
    );

    const handlePasteImageClick = useCallback(async () => {
      if (!navigator.clipboard?.read) {
        toast.error("Trình duyệt chưa hỗ trợ nút Paste Image");
        return;
      }
      try {
        const clipboardItems = await navigator.clipboard.read();
        for (const item of clipboardItems) {
          const imageType = item.types.find((type) => type.startsWith("image/"));
          if (!imageType) continue;
          const blob = await item.getType(imageType);
          const file = new File([blob], "clipboard-image.png", { type: imageType });
          await handleExtractFromImage(file);
          return;
        }
        toast.error("Clipboard chưa có ảnh để OCR");
      } catch {
        toast.error("Không đọc được clipboard. Hãy cấp quyền rồi thử lại.");
      }
    }, [handleExtractFromImage]);

    useImperativeHandle(
      ref,
      () => ({
        pasteImage: handlePasteImageClick,
      }),
      [handlePasteImageClick]
    );

    useEffect(() => {
      onOcrBusyChange?.(isExtracting);
    }, [isExtracting, onOcrBusyChange]);

    useEffect(() => {
      const onWindowPaste = (event: ClipboardEvent) => {
        const items = Array.from(event.clipboardData?.items ?? []);
        const imageItem = items.find((item) => item.type.startsWith("image/"));
        if (!imageItem) return;
        const file = imageItem.getAsFile();
        if (!file) return;
        event.preventDefault();
        void handleExtractFromImage(file);
      };

      window.addEventListener("paste", onWindowPaste as unknown as EventListener);
      return () => {
        window.removeEventListener("paste", onWindowPaste as unknown as EventListener);
      };
    }, [handleExtractFromImage]);

    const composeBlock = (
      <div
        className={cn(
          "flex min-h-0 flex-col",
          wizardMode ? "h-full min-h-0 flex-1 gap-2 overflow-hidden" : "gap-5"
        )}
      >
        {!wizardMode ? (
          <div className="rounded-xl border border-border bg-muted/25 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <ImageIcon className="h-4 w-4 shrink-0 text-primary" aria-hidden />
                OCR từ ảnh
              </div>
              <span className="text-[11px] text-muted-foreground">
                Toàn trang: dán ảnh (Ctrl+V)
              </span>
            </div>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-stretch">
              <div
                role="textbox"
                tabIndex={0}
                aria-label="Vùng dán ảnh để nhận dạng chữ"
                onPaste={(e) => void handleExtractFromClipboard(e)}
                className="flex min-h-12 flex-1 cursor-pointer items-center rounded-lg border-2 border-dashed border-border bg-background/80 px-3 py-2.5 text-xs leading-snug text-muted-foreground outline-none transition-colors duration-200 hover:border-primary/40 hover:bg-muted/40 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="flex items-start gap-2">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
                  Kích hoạt vùng này rồi dán ảnh câu hỏi — hoặc dán ảnh bất kỳ đâu trên trang.
                </span>
              </div>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-11 shrink-0 cursor-pointer gap-2 self-stretch rounded-lg px-4 transition-colors duration-200 sm:h-auto sm:self-auto"
                disabled={isExtracting}
                onClick={() => void handlePasteImageClick()}
              >
                <ClipboardPaste className="h-4 w-4 shrink-0" aria-hidden />
                Paste ảnh
              </Button>
            </div>
            {isExtracting ? (
              <div className="mt-3 space-y-1.5">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Đang nhận dạng</span>
                  <span className="font-mono tabular-nums">
                    {typeof ocrProgress === "number" ? `${ocrProgress}%` : "…"}
                  </span>
                </div>
                <div
                  className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={typeof ocrProgress === "number" ? ocrProgress : undefined}
                  aria-label="Tiến độ OCR"
                >
                  <div
                    className="h-full rounded-full bg-primary transition-[width] duration-300 motion-reduce:transition-none"
                    style={{
                      width: `${typeof ocrProgress === "number" ? Math.min(100, Math.max(0, ocrProgress)) : 12}%`,
                    }}
                  />
                </div>
              </div>
            ) : null}
          </div>
        ) : isExtracting ? (
          <div
            className="shrink-0 space-y-1.5 rounded-lg border border-border bg-muted/30 px-3 py-2"
            aria-live="polite"
          >
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Đang OCR từ ảnh…</span>
              <span className="font-mono tabular-nums">
                {typeof ocrProgress === "number" ? `${ocrProgress}%` : "…"}
              </span>
            </div>
            <div
              className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={typeof ocrProgress === "number" ? ocrProgress : undefined}
              aria-label="Tiến độ OCR"
            >
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-300 motion-reduce:transition-none"
                style={{
                  width: `${typeof ocrProgress === "number" ? Math.min(100, Math.max(0, ocrProgress)) : 12}%`,
                }}
              />
            </div>
          </div>
        ) : null}

        <div
          className={cn(
            wizardMode
              ? cn(
                  "grid min-h-0 min-w-0 flex-1 overflow-hidden",
                  answerSheetOpen
                    ? "grid-cols-[minmax(0,1fr)_max-content] grid-rows-[auto_minmax(0,1fr)] gap-x-3 gap-y-2"
                    : "grid-cols-1 grid-rows-[auto_minmax(0,1fr)] gap-y-2"
                )
              : "space-y-2"
          )}
        >
          {!wizardMode ? (
            <>
              <label
                htmlFor="deck-raw-question"
                id={composeLabelId}
                className="shrink-0 text-sm font-semibold text-foreground"
              >
                Nội dung câu (stem + A. B. …)
              </label>
              <Textarea
                id="deck-raw-question"
                aria-labelledby={composeLabelId}
                placeholder="Stem và các dòng A. ... B. ..."
                value={rawBlock}
                onChange={(e) => onRawBlockChange(e.target.value)}
                onKeyDown={handleComposeKeyDown}
                className="min-h-[min(22rem,55vh)] resize-y font-mono text-sm leading-relaxed md:min-h-72"
              />
            </>
          ) : (
            <>
              <label
                htmlFor="deck-raw-question"
                id={composeLabelId}
                className="col-start-1 row-start-1 flex min-h-9 shrink-0 items-end text-sm font-semibold leading-5 text-foreground"
              >
                Nội dung câu (stem + A. B. …)
              </label>

              {answerSheetOpen ? (
                <p
                  id={wizardAnswerHeadingId}
                  className="col-start-2 row-start-1 flex min-h-9 shrink-0 items-end text-sm font-semibold leading-5 text-foreground"
                >
                  Đáp án đúng
                </p>
              ) : null}

              <Textarea
                id="deck-raw-question"
                aria-labelledby={composeLabelId}
                placeholder="Stem và các dòng A. ... B. ..."
                value={rawBlock}
                onChange={(e) => onRawBlockChange(e.target.value)}
                onKeyDown={handleComposeKeyDown}
                className="col-start-1 row-start-2 min-h-0 w-full resize-none rounded-lg border-2 border-input bg-background px-3 py-2 font-mono text-sm leading-relaxed md:text-base"
              />

              <AnimatePresence mode="popLayout" onExitComplete={handleSheetExitComplete}>
                {answerSheetOpen ? (
                  <motion.div
                    key="wizard-answer-panel"
                    role="presentation"
                    className="col-start-2 row-start-2 flex min-h-0 max-h-full min-w-0 overflow-hidden self-stretch"
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: WIZARD_ANSWER_PANEL_W, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    transition={sheetSpring}
                  >
                    <motion.div
                      role="region"
                      aria-labelledby={wizardAnswerHeadingId}
                      className="flex h-full min-h-0 w-full flex-col rounded-lg border-2 border-input bg-background px-3 py-2 shadow-sm"
                      initial={prefersReducedMotion ? false : { x: 14 }}
                      animate={{ x: 0 }}
                      exit={prefersReducedMotion ? undefined : { x: 14 }}
                      transition={sheetSpring}
                    >
                      <div
                        className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto pb-1 pt-2 font-mono text-sm leading-relaxed md:text-base"
                        role="group"
                        aria-label="Chọn đáp án đúng — phím A đến F khi không đang gõ trong ô nhập"
                      >
                        {wizardParsedOptions.map((opt, index) => {
                          const selected = Boolean(answerSelected[opt.label]);
                          return (
                            <motion.div
                              key={opt.label}
                              className="shrink-0"
                              initial={prefersReducedMotion ? false : { opacity: 0, y: 6 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{
                                ...sheetSpring,
                                delay: prefersReducedMotion ? 0 : index * 0.04,
                              }}
                            >
                              <Button
                                type="button"
                                variant={selected ? "default" : "outline"}
                                size="sm"
                                aria-pressed={selected}
                                className={cn(
                                  "h-8 w-full cursor-pointer justify-center gap-1 rounded-full border px-2 font-mono text-sm font-semibold tabular-nums leading-relaxed transition-colors duration-200 md:h-9 md:text-base",
                                  selected && "shadow-none"
                                )}
                                onClick={() => onToggleAnswer(opt.label)}
                              >
                                {selected ? (
                                  <Check className="h-3 w-3 shrink-0" aria-hidden />
                                ) : null}
                                {opt.label}
                              </Button>
                            </motion.div>
                          );
                        })}
                      </div>
                    </motion.div>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </>
          )}
        </div>

        {!wizardMode ? (
          <>
            <div className="space-y-2 shrink-0">
              <p className="text-sm font-semibold text-foreground">Đáp án đúng</p>
              <div
                className="flex flex-wrap gap-2"
                role="group"
                aria-label="Chọn đáp án đúng — phím A đến F khi không đang gõ trong ô nhập"
              >
                {optionLabels.length === 0 ? (
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    Nhập block có định dạng{" "}
                    <span className="font-mono font-medium text-foreground">A.</span>{" "}
                    <span className="font-mono font-medium text-foreground">B.</span> … để hiện nút
                    chọn.
                  </p>
                ) : (
                  optionLabels.map((label) => {
                    const selected = Boolean(answerSelected[label]);
                    return (
                      <Button
                        key={label}
                        type="button"
                        variant={selected ? "default" : "outline"}
                        size="sm"
                        aria-pressed={selected}
                        className={cn(
                          "h-9 min-w-11 cursor-pointer gap-1.5 rounded-lg border-2 transition-colors duration-200",
                          selected && "shadow-none"
                        )}
                        onClick={() => onToggleAnswer(label)}
                      >
                        {selected ? <Check className="h-3.5 w-3.5 shrink-0" aria-hidden /> : null}
                        {label}
                      </Button>
                    );
                  })
                )}
              </div>
            </div>

            <div className="mt-auto shrink-0 border-t border-border pt-4">
              <Button
                type="button"
                className="h-11 w-full cursor-pointer gap-2 rounded-lg text-sm font-semibold transition-colors duration-200 md:w-auto md:min-w-48"
                onClick={onAppendQuestion}
                title="Thêm câu vào file — phím Q hoặc ⌘Enter / Ctrl+Enter trong ô nội dung câu"
              >
                <PencilLine className="h-4 w-4 shrink-0" aria-hidden />
                Thêm câu vào file
              </Button>
              <p className="mt-2 text-[11px] text-muted-foreground">
                Markdown cập nhật ở khung bên phải (hoặc tab trên điện thoại).
              </p>
            </div>
          </>
        ) : null}
      </div>
    );

    const previewBlock = (
      <div
        className={cn(
          "flex min-h-0 flex-col",
          wizardMode ? "h-full min-h-0 flex-1 gap-2 overflow-hidden" : "gap-3"
        )}
      >
        <div
          className={cn(
            "flex flex-wrap items-end justify-between gap-2",
            wizardMode &&
              "min-h-9 shrink-0 md:flex-nowrap md:items-end md:gap-x-3 [&>label]:min-w-0 [&>label]:flex-1"
          )}
        >
          <label
            htmlFor="deck-md-preview"
            className="shrink-0 text-sm font-semibold leading-5 text-foreground"
          >
            Format câu hỏi đã chuẩn hoá
          </label>
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5 md:flex-nowrap">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 shrink-0 gap-1.5 px-2 text-xs text-muted-foreground hover:text-destructive"
              disabled={!accumulatedMd.trim()}
              onClick={openClearMdDialog}
              aria-label="Xóa hết format câu hỏi đã chuẩn hoá"
              title="Xóa hết"
            >
              <Trash2 className="h-3.5 w-3.5 shrink-0" aria-hidden />
              Xóa hết
            </Button>
            <Badge variant="secondary" className="font-mono text-[10px] font-normal">
              {previewStats.lines} dòng
            </Badge>
            <Badge variant="outline" className="font-mono text-[10px] font-normal">
              {previewStats.len} ký tự
            </Badge>
          </div>
        </div>
        <Textarea
          id="deck-md-preview"
          aria-label="Format câu hỏi đã chuẩn hoá, có thể chỉnh sửa"
          spellCheck={false}
          value={accumulatedMd}
          onChange={(e) => onAccumulatedMdChange(e.target.value)}
          className={cn(
            "rounded-lg border-2 border-input bg-background font-mono text-xs leading-relaxed",
            wizardMode
              ? "h-full min-h-0 flex-1 resize-none text-sm md:text-base"
              : "min-h-[min(50vh,24rem)] flex-1 resize-y md:min-h-0"
          )}
        />
      </div>
    );

    const clearMarkdownConfirmDialog = (
      <AlertDialog open={clearMdDialogOpen} onOpenChange={setClearMdDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xóa hết format câu hỏi đã chuẩn hoá?</AlertDialogTitle>
            <AlertDialogDescription>
              Toàn bộ nội dung trong khung Format câu hỏi đã chuẩn hoá sẽ bị xóa. Thao tác này không
              thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel type="button">Hủy</AlertDialogCancel>
            <AlertDialogAction
              type="button"
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90 focus-visible:ring-destructive"
              onClick={() => {
                onAccumulatedMdChange("");
                setClearMdDialogOpen(false);
              }}
            >
              Xóa hết
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );

    if (wizardMode) {
      return (
        <>
          <section
            className="flex h-full min-h-0 w-full flex-1 flex-col gap-2"
            aria-label="Soạn câu cho đề"
          >
            <span id={headingId} className="sr-only">
              Soạn câu cho đề
            </span>
            <span className="sr-only">
              Phím tắt khi con trỏ không trong ô nhập văn bản: các phím đáp án A đến F bật/tắt đáp
              án tương ứng; phím Q thêm câu vào file (đủ điều kiện như nút mũi tên).
            </span>

            <div className="flex min-h-0 w-full flex-1 flex-col md:flex-row md:items-stretch">
              <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto px-0.5 pb-1 pt-2 md:px-2 md:pb-2 md:pr-2 md:pt-0">
                {composeBlock}
              </div>

              <div className="flex shrink-0 flex-row items-center justify-center gap-2 border-y border-border bg-muted/20 px-3 py-3 md:w-19 md:flex-col md:border-x md:border-y-0 md:px-2 md:py-4">
                <Button
                  type="button"
                  variant="default"
                  size="lg"
                  className="h-11 shrink-0 gap-2 rounded-full px-5 shadow-md md:h-14 md:w-14 md:rounded-xl md:p-0"
                  disabled={!rawBlock.trim() || !hasSelectedAnswer || sheetForcedClosed}
                  onClick={handleWizardAppendQuestion}
                  aria-label="Thêm câu vào file format câu hỏi đã chuẩn hoá"
                  title="Thêm vào file — phím Q (khi không gõ ô nhập), hoặc ⌘Enter / Ctrl+Enter trong ô nội dung câu"
                >
                  <ChevronDown className="h-5 w-5 md:hidden" aria-hidden />
                  <ChevronRight className="hidden h-7 w-7 md:block" aria-hidden />
                  <span className="text-sm font-semibold md:sr-only">Thêm vào file</span>
                </Button>
              </div>

              <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto border-t border-border px-0.5 pb-1 pt-2 md:border-t-0 md:px-2 md:pb-2 md:pl-2 md:pt-0">
                {previewBlock}
              </div>
            </div>

            {onProceedToPreview ? (
              <footer className="shrink-0 border-t border-border pt-2">
                <div className="flex justify-end">
                  <Button
                    type="button"
                    size="lg"
                    className="h-12 min-w-56 shrink-0 cursor-pointer gap-2 rounded-lg px-4 transition-colors duration-200"
                    onClick={onProceedToPreview}
                  >
                    <Telescope className="h-5 w-5 shrink-0" aria-hidden />
                    Xem trước
                  </Button>
                </div>
              </footer>
            ) : null}
          </section>
          {clearMarkdownConfirmDialog}
        </>
      );
    }

    return (
      <>
        <Card className="flex min-h-0 flex-col overflow-hidden border-2 border-border shadow-none">
          <div className="flex shrink-0 flex-col gap-1 border-b-2 border-border bg-muted/30 px-4 py-4 sm:px-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-primary">
                  Soạn câu
                </p>
                <h2
                  id={headingId}
                  className="flex flex-wrap items-center gap-2 text-lg font-bold tracking-tight text-foreground"
                >
                  Tạo câu cho đề
                </h2>
                <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                  Nhập hoặc OCR block, chọn đáp án — markdown cập nhật bên phải hoặc tab{" "}
                  <span className="font-medium text-foreground">Xem file</span> trên điện thoại.
                </p>
                <span className="sr-only">
                  Phím tắt khi con trỏ không trong ô nhập văn bản: các phím đáp án A đến F bật/tắt
                  đáp án; phím Q thêm câu vào file.
                </span>
              </div>
              <div className="flex items-center gap-2 rounded-xl border border-border bg-background p-1 md:hidden">
                <Button
                  type="button"
                  variant={mobileTab === "compose" ? "secondary" : "ghost"}
                  size="sm"
                  className="h-9 cursor-pointer gap-1.5 rounded-lg px-3"
                  aria-pressed={mobileTab === "compose"}
                  onClick={() => setMobileTab("compose")}
                >
                  <PencilLine className="h-4 w-4" aria-hidden />
                  Soạn
                </Button>
                <Button
                  type="button"
                  variant={mobileTab === "preview" ? "secondary" : "ghost"}
                  size="sm"
                  className="h-9 cursor-pointer gap-1.5 rounded-lg px-3"
                  aria-pressed={mobileTab === "preview"}
                  onClick={() => setMobileTab("preview")}
                >
                  <FileText className="h-4 w-4" aria-hidden />
                  Xem file
                </Button>
              </div>
            </div>
          </div>

          <CardContent className="flex min-h-0 flex-1 flex-col p-0">
            <div className="hidden min-h-0 md:grid md:grid-cols-2 md:divide-x-2 md:divide-border">
              <div className="min-h-0 p-5 sm:p-6">{composeBlock}</div>
              <div className="min-h-0 p-5 sm:p-6">{previewBlock}</div>
            </div>
            <div className="md:hidden" aria-labelledby={headingId}>
              <div className="p-4 sm:p-5">
                {mobileTab === "compose" ? composeBlock : previewBlock}
              </div>
            </div>
          </CardContent>
        </Card>
        {clearMarkdownConfirmDialog}
      </>
    );
  }
);

QuestionEditorSection.displayName = "QuestionEditorSection";
