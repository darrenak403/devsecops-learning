"use client";

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { toast } from "sonner";
import { ArrowLeft, ClipboardPaste, Pencil } from "lucide-react";
import { hasAdminRole } from "@/lib/types/roles";
import { useAuth } from "@/hooks/useAuth";
import {
  useAllAdminSourcesForSlug,
  useAllAdminSubjects,
  useCreateAdminSubject,
  useMergeBankPreview,
  useMergeIntoBank,
  useUploadQuestionSource,
} from "@/hooks/useQuestionSources";
import type { MergeBankPreviewResponse } from "@/lib/api/services/fetchQuestionSources";
import {
  parseAnswerKeys,
  parseRawQuestionBlock,
  refactorMarkdownText,
  renderQuestionBlock,
} from "@/lib/questionMarkdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";
import { ClientHydrationGate } from "./ClientHydrationGate";
import { DeckAccessDenied } from "./DeckAccessDenied";
import { DeckPublishStep } from "./DeckPublishStep";
import type { DeckWizardStep } from "./DeckStepIndicator";
import { DeckStepIndicator } from "./DeckStepIndicator";
import { QuestionEditorSection, type QuestionEditorWizardHandle } from "./QuestionEditorSection";
import { SubjectFilenameCard } from "./SubjectFilenameCard";

function normalizeFileKey(name: string): string {
  let s = name.trim().toLowerCase();
  if (!s.endsWith(".md")) s = `${s}.md`;
  return s;
}

function ensureMdExtension(name: string): string {
  const t = name.trim();
  if (!t) return "";
  return t.toLowerCase().endsWith(".md") ? t : `${t}.md`;
}

interface DeckMarkdownPageClientProps {
  /** Nhúng trong `/admin`: khớp layout sidebar, ẩn đăng xuất / full-page trùng */
  embedded?: boolean;
}

export function DeckMarkdownPageClient({ embedded = false }: DeckMarkdownPageClientProps) {
  const { user, doLogout } = useAuth();
  const hydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  const subjectsQuery = useAllAdminSubjects();
  const [deckStep, setDeckStep] = useState<DeckWizardStep>(1);
  const [step1Phase, setStep1Phase] = useState<"form" | "summary">("form");
  const summaryDismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [selectedSlug, setSelectedSlug] = useState("");
  const [newSlugDraft, setNewSlugDraft] = useState("");
  const [deckFilename, setDeckFilename] = useState("");
  const [accumulatedMd, setAccumulatedMd] = useState("");
  const [rawBlock, setRawBlock] = useState("");
  const [answerSelected, setAnswerSelected] = useState<Record<string, boolean>>({});
  const [lastUploadSourceId, setLastUploadSourceId] = useState<string | null>(null);
  const [previewMerge, setPreviewMerge] = useState<MergeBankPreviewResponse | null>(null);
  const questionEditorRef = useRef<QuestionEditorWizardHandle | null>(null);
  const [wizardOcrBusy, setWizardOcrBusy] = useState(false);

  const sourcesQuery = useAllAdminSourcesForSlug(selectedSlug || undefined);
  const existingNameKeys = useMemo(() => {
    const set = new Set<string>();
    for (const s of sourcesQuery.data ?? []) {
      set.add(normalizeFileKey(s.fileName));
    }
    return set;
  }, [sourcesQuery.data]);

  const uploadFileName = useMemo(() => ensureMdExtension(deckFilename), [deckFilename]);
  const filenameDuplicate = useMemo(() => {
    if (!uploadFileName) return false;
    return existingNameKeys.has(normalizeFileKey(uploadFileName));
  }, [uploadFileName, existingNameKeys]);

  const subjectDisplay = useMemo(() => {
    const list = subjectsQuery.data ?? [];
    const s = list.find((x) => x.slug === selectedSlug);
    if (s) return `${s.code} · ${s.slug}`;
    return selectedSlug || "—";
  }, [subjectsQuery.data, selectedSlug]);

  const canProceedStep1 = Boolean(
    selectedSlug.trim() && uploadFileName.trim() && !filenameDuplicate
  );

  const createSubjectMutation = useCreateAdminSubject();
  const uploadMutation = useUploadQuestionSource();
  const mergePreviewMutation = useMergeBankPreview();
  const mergeMutation = useMergeIntoBank();

  const optionLabels = useMemo(() => {
    const t = rawBlock.trim();
    if (!t) return [];
    try {
      return parseRawQuestionBlock(t).options.map((o) => o.label);
    } catch {
      return [];
    }
  }, [rawBlock]);

  const handleRawBlockChange = (value: string) => {
    setRawBlock(value);
    const trimmed = value.trim();
    if (!trimmed) {
      setAnswerSelected({});
      return;
    }
    try {
      const { options } = parseRawQuestionBlock(trimmed);
      const labels = options.map((o) => o.label);
      setAnswerSelected((prev) => {
        const next: Record<string, boolean> = {};
        for (const label of labels) next[label] = prev[label] ?? false;
        return next;
      });
    } catch {
      setAnswerSelected({});
    }
  };

  const handleSubjectChange = (slug: string) => {
    setSelectedSlug(slug);
    setDeckFilename("");
    setLastUploadSourceId(null);
    setPreviewMerge(null);
  };

  const handleEnsureSubject = () => {
    const s = newSlugDraft.trim().toLowerCase();
    if (!s) {
      toast.error("Nhap slug (vd mln111)");
      return;
    }
    createSubjectMutation.mutate(
      { slug: s },
      {
        onSuccess: (data) => {
          setSelectedSlug(data.slug);
          setNewSlugDraft("");
        },
      }
    );
  };

  const handleAppendQuestion = () => {
    if (!rawBlock.trim()) {
      toast.error("Dan noi dung cau hoi va cac lua chon");
      return;
    }
    try {
      const { stem, options } = parseRawQuestionBlock(rawBlock);
      const keys = options
        .map((o) => o.label)
        .filter((label) => answerSelected[label])
        .sort();
      const parsedKeys = parseAnswerKeys(keys.join(", "));
      if (!parsedKeys.length) {
        toast.error("Chon it nhat mot dap an dung");
        return;
      }
      const block = renderQuestionBlock(stem, options, parsedKeys);
      const combined = accumulatedMd.trim() ? `${accumulatedMd.trim()}\n\n${block}` : block;
      setAccumulatedMd(refactorMarkdownText(combined));
      setRawBlock("");
      setAnswerSelected({});
      toast.success("Da them cau va chuan hoa file");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Khong parse duoc block");
    }
  };

  const handleUpload = () => {
    if (!selectedSlug || !uploadFileName || !accumulatedMd.trim()) {
      toast.error("Chon mon, nhap ten file va co noi dung markdown");
      return;
    }
    if (filenameDuplicate) {
      toast.error("Ten file da ton tai tren he thong");
      return;
    }
    const blob = new Blob([accumulatedMd], { type: "text/markdown;charset=utf-8" });
    const file = new File([blob], uploadFileName, { type: "text/markdown" });
    uploadMutation.mutate(
      { slug: selectedSlug, file },
      { onSuccess: (data) => setLastUploadSourceId(data.sourceId) }
    );
  };

  const handlePreviewMerge = () => {
    if (!selectedSlug || !lastUploadSourceId) {
      toast.error("Upload thất bại!");
      return;
    }
    mergePreviewMutation.mutate(
      { slug: selectedSlug, deckSourceId: lastUploadSourceId },
      { onSuccess: (data) => setPreviewMerge(data) }
    );
  };

  const handleMergeCommit = () => {
    if (!selectedSlug || !lastUploadSourceId) {
      toast.error("Thiếu slug hoặc source deck");
      return;
    }
    mergeMutation.mutate(
      { slug: selectedSlug, deckSourceId: lastUploadSourceId },
      {
        onSuccess: () => {
          setAccumulatedMd("");
          setRawBlock("");
          setAnswerSelected({});
          setDeckFilename("");
          setLastUploadSourceId(null);
          setPreviewMerge(null);
          setDeckStep(1);
        },
      }
    );
  };

  const handleDownload = () => {
    if (!accumulatedMd.trim()) return;
    const blob = new Blob([accumulatedMd], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = uploadFileName || "deck.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleStep1Continue = () => {
    if (!canProceedStep1) {
      toast.error("Chọn môn và nhập tên file .md (không trùng tên đã có)");
      return;
    }
    if (summaryDismissTimerRef.current) {
      clearTimeout(summaryDismissTimerRef.current);
    }
    setStep1Phase("summary");
    summaryDismissTimerRef.current = setTimeout(() => {
      setDeckStep(2);
      setStep1Phase("form");
      summaryDismissTimerRef.current = null;
    }, 720);
  };

  const handleEditMeta = () => {
    setDeckStep(1);
    setStep1Phase("form");
  };

  useEffect(() => {
    return () => {
      if (summaryDismissTimerRef.current) {
        clearTimeout(summaryDismissTimerRef.current);
      }
    };
  }, []);

  const isAdmin = Boolean(user && hasAdminRole(user.role));

  const uploadMergeProps = {
    selectedSlug,
    accumulatedMd,
    filenameDuplicate,
    uploadFileName,
    isUploading: uploadMutation.isPending,
    isPreviewing: mergePreviewMutation.isPending,
    isMerging: mergeMutation.isPending,
    lastUploadSourceId,
    previewMerge,
    onUpload: handleUpload,
    onDownload: handleDownload,
    onPreviewMerge: handlePreviewMerge,
    onMergeCommit: handleMergeCommit,
  };

  const inner = (
    <div
      className={cn(
        "flex w-full min-w-0 flex-col gap-4",
        embedded && "min-h-0 flex-1",
        embedded && (deckStep === 2 || deckStep === 3) && "min-h-0 overflow-hidden"
      )}
    >
      <DeckStepIndicator current={deckStep} />

      {deckStep >= 2 ? (
        <div className="animate-in fade-in slide-in-from-top-2 flex flex-wrap items-center justify-between gap-2 gap-y-2 duration-300">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <Badge variant="secondary" className="max-w-full truncate font-normal">
              Môn: {subjectDisplay}
            </Badge>
            <Badge variant="outline" className="max-w-full truncate font-mono text-xs font-normal">
              File: {uploadFileName || "—"}
            </Badge>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {deckStep === 2 ? (
              <>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-9 cursor-pointer gap-2 rounded-lg"
                  disabled={wizardOcrBusy}
                  onClick={() => void questionEditorRef.current?.pasteImage()}
                >
                  <ClipboardPaste className="h-4 w-4 shrink-0" aria-hidden />
                  Paste ảnh
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-9 cursor-pointer gap-1 text-muted-foreground"
                  onClick={handleEditMeta}
                >
                  <Pencil className="h-3.5 w-3.5" aria-hidden />
                  Sửa môn / file
                </Button>
              </>
            ) : (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-9 cursor-pointer gap-2 rounded-lg"
                onClick={() => setDeckStep(2)}
              >
                <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
                Quay lại chọn câu
              </Button>
            )}
          </div>
        </div>
      ) : null}

      {deckStep === 1 ? (
        <div className="space-y-4">
          {step1Phase === "summary" ? (
            <div
              className="animate-in zoom-in-95 fade-in flex min-h-50 flex-col items-center justify-center rounded-xl border-2 border-primary/35 bg-linear-to-b from-muted/80 to-muted/40 p-8 duration-300"
              role="status"
              aria-live="polite"
            >
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Đã chọn
              </p>
              <p className="mt-3 text-center text-xl font-bold tracking-tight text-foreground">
                {subjectDisplay}
              </p>
              <p className="mt-6 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Tên file
              </p>
              <p className="mt-2 max-w-full break-all text-center font-mono text-base font-semibold text-foreground">
                {uploadFileName}
              </p>
            </div>
          ) : (
            <>
              <SubjectFilenameCard
                selectedSubjectMeta={
                  selectedSlug.trim()
                    ? (subjectsQuery.data?.find((x) => x.slug === selectedSlug) ?? null)
                    : null
                }
                isSubjectMetaLoading={subjectsQuery.isLoading}
                selectedSlug={selectedSlug}
                newSlugDraft={newSlugDraft}
                deckFilename={deckFilename}
                uploadFileName={uploadFileName}
                isSourcesLoading={sourcesQuery.isLoading}
                filenameDuplicate={filenameDuplicate}
                isEnsuringSubject={createSubjectMutation.isPending}
                onSubjectChange={handleSubjectChange}
                onSlugDraftChange={setNewSlugDraft}
                onEnsureSubject={handleEnsureSubject}
                onDeckFilenameChange={setDeckFilename}
              />
              <div className="flex justify-end">
                <Button
                  type="button"
                  size="lg"
                  className="h-12 w-full min-w-48 cursor-pointer rounded-lg transition-colors duration-200 sm:w-auto"
                  disabled={!canProceedStep1}
                  onClick={handleStep1Continue}
                >
                  Tiếp tục — soạn câu
                </Button>
              </div>
            </>
          )}
        </div>
      ) : null}

      {deckStep === 2 ? (
        <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
          <QuestionEditorSection
            ref={questionEditorRef}
            wizardMode
            onOcrBusyChange={setWizardOcrBusy}
            onProceedToPreview={() => setDeckStep(3)}
            rawBlock={rawBlock}
            accumulatedMd={accumulatedMd}
            optionLabels={optionLabels}
            answerSelected={answerSelected}
            onRawBlockChange={handleRawBlockChange}
            onToggleAnswer={(label) =>
              setAnswerSelected((prev) => ({ ...prev, [label]: !prev[label] }))
            }
            onAppendQuestion={handleAppendQuestion}
            onAccumulatedMdChange={setAccumulatedMd}
          />
        </div>
      ) : null}

      {deckStep === 3 ? (
        <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
          <DeckPublishStep accumulatedMd={accumulatedMd} uploadMergeProps={uploadMergeProps} />
        </div>
      ) : null}
    </div>
  );

  return (
    <ClientHydrationGate hydrated={hydrated}>
      {!isAdmin ? (
        <DeckAccessDenied embedded={embedded} onLogout={doLogout} />
      ) : embedded ? (
        inner
      ) : (
        <main className="min-h-screen bg-[#fcfaf6] px-4 py-6 md:px-6 md:py-8">{inner}</main>
      )}
    </ClientHydrationGate>
  );
}
