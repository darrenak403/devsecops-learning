"use client";

import { useCallback, useEffect, useMemo, useState, type SetStateAction } from "react";

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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useAdminSourceQuestionsInfinityScroll,
  useAppendAdminSourceQuestion,
  useCheckQuestionInBank,
  useDeleteAdminSourceQuestion,
  usePatchAdminSourceQuestion,
} from "@/hooks/useQuestionSources";
import { flattenInfinitePages } from "@/hooks/useInfinityScroll";
import type { QuestionDraft, SourceQuestionsDialogProps } from "@/lib/types/source-questions-dialog";
import { cloneDraft, emptyComposeDraft } from "@/lib/utils/questionDraft";
import type {
  AdminSourceQuestionItem,
  BankCheckDuplicateResponse,
  SourceQuestionUpdateInput,
} from "@/lib/api/services/fetchQuestionSources";
import { cn } from "@/lib/utils/cn";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

import { QuestionEditorPanel, type QuestionEditorMode } from "./QuestionEditorPanel";
import { QuestionListPanel } from "./QuestionListPanel";

function draftToPayload(d: QuestionDraft): SourceQuestionUpdateInput {
  return {
    stem: d.stem.trim(),
    options: d.options
      .map((o) => ({ label: o.label.trim(), text: o.text.trim() }))
      .filter((o) => o.label || o.text),
    answer: d.answer.trim(),
  };
}

export function SourceQuestionsDialog({
  open,
  onOpenChange,
  subjectSlug,
  source,
}: SourceQuestionsDialogProps) {
  const enabled = open && Boolean(subjectSlug) && Boolean(source?.sourceId);
  const slug = subjectSlug ?? undefined;
  const sourceId = source?.sourceId;

  const [questionSearchInput, setQuestionSearchInput] = useState("");
  const [debouncedQuestionSearch, setDebouncedQuestionSearch] = useState("");
  const [selected, setSelected] = useState<AdminSourceQuestionItem | null>(null);
  const [draft, setDraft] = useState<QuestionDraft | null>(null);
  const [isComposingNew, setIsComposingNew] = useState(false);
  const [bankCheck, setBankCheck] = useState<BankCheckDuplicateResponse | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuestionSearch(questionSearchInput.trim()), 300);
    return () => clearTimeout(t);
  }, [questionSearchInput]);

  useEffect(() => {
    /* Filter đổi → đóng editor (ordinal có thể không còn trong trang kết quả). */
    /* eslint-disable react-hooks/set-state-in-effect */
    setSelected(null);
    setDraft(null);
    setIsComposingNew(false);
    setBankCheck(null);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [debouncedQuestionSearch]);

  const setDraftAndClearBankCheck = useCallback((value: SetStateAction<QuestionDraft | null>) => {
    setBankCheck(null);
    setDraft(value);
  }, []);

  const infinite = useAdminSourceQuestionsInfinityScroll(slug, sourceId, {
    enabled,
    pageSize: 30,
    scrollOffset: 64,
    filters: debouncedQuestionSearch ? { q: debouncedQuestionSearch } : undefined,
  });

  const patchMutation = usePatchAdminSourceQuestion();
  const appendMutation = useAppendAdminSourceQuestion();
  const checkMutation = useCheckQuestionInBank();
  const deleteMutation = useDeleteAdminSourceQuestion();

  const questions = useMemo(
    () => flattenInfinitePages(infinite.data?.pages),
    [infinite.data?.pages]
  );

  const handleDialogOpenChange = useCallback(
    (next: boolean) => {
      if (!next) {
        setSelected(null);
        setDraft(null);
        setIsComposingNew(false);
        setBankCheck(null);
        setDeleteDialogOpen(false);
        setQuestionSearchInput("");
        setDebouncedQuestionSearch("");
      }
      onOpenChange(next);
    },
    [onOpenChange]
  );

  const handleSelect = useCallback((q: AdminSourceQuestionItem) => {
    setIsComposingNew(false);
    setBankCheck(null);
    setSelected(q);
    setDraft(cloneDraft(q));
  }, []);

  const handleAddQuestion = useCallback(() => {
    setSelected(null);
    setIsComposingNew(true);
    setBankCheck(null);
    setDraft(emptyComposeDraft());
  }, []);

  const handleDeselect = useCallback(() => {
    setSelected(null);
    setDraft(null);
    setIsComposingNew(false);
    setBankCheck(null);
  }, []);

  const handleCheckBank = useCallback(() => {
    if (!subjectSlug || !draft) return;
    const body = draftToPayload(draft);
    if (!body.stem) return;
    checkMutation.mutate(
      { slug: subjectSlug, body },
      {
        onSuccess: (data) => {
          setBankCheck(data);
        },
      }
    );
  }, [subjectSlug, draft, checkMutation]);

  const handleSaveEdit = useCallback(() => {
    if (!subjectSlug || !source || !selected || !draft) return;
    const ordinal = selected.id;
    patchMutation.mutate(
      {
        slug: subjectSlug,
        sourceId: source.sourceId,
        ordinal,
        body: {
          stem: draft.stem.trim(),
          options: draft.options
            .map((o) => ({ label: o.label.trim(), text: o.text.trim() }))
            .filter((o) => o.label || o.text),
          answer: draft.answer.trim(),
        },
      },
      {
        onSuccess: () => {
          void infinite.refetch();
          setSelected(null);
          setDraft(null);
        },
      }
    );
  }, [subjectSlug, source, selected, draft, patchMutation, infinite]);

  const handleSaveNew = useCallback(() => {
    if (!subjectSlug || !source || !draft) return;
    const body = draftToPayload(draft);
    if (!body.stem) return;
    appendMutation.mutate(
      {
        slug: subjectSlug,
        sourceId: source.sourceId,
        body,
      },
      {
        onSuccess: (data) => {
          setQuestionSearchInput("");
          setDebouncedQuestionSearch("");
          setIsComposingNew(false);
          void infinite.refetch();
          const newItem: AdminSourceQuestionItem = {
            id: data.ordinal,
            stem: body.stem,
            options: body.options.map((o) => ({ label: o.label, text: o.text })),
            answer: body.answer,
            answerCount: Math.max(1, body.answer.split(/[,;]/).filter(Boolean).length),
            imageUrl: null,
          };
          setSelected(newItem);
          setDraft(cloneDraft(newItem));
          setBankCheck(null);
        },
      }
    );
  }, [subjectSlug, source, draft, appendMutation, infinite]);

  const handleConfirmDelete = useCallback(() => {
    if (!subjectSlug || !source || !selected) return;
    deleteMutation.mutate(
      {
        slug: subjectSlug,
        sourceId: source.sourceId,
        ordinal: selected.id,
      },
      {
        onSuccess: () => {
          setDeleteDialogOpen(false);
          setSelected(null);
          setDraft(null);
          void infinite.refetch();
        },
      }
    );
  }, [subjectSlug, source, selected, deleteMutation, infinite]);

  const isDirty = useMemo(() => {
    if (!selected || !draft) return false;
    return (
      draft.stem !== selected.stem ||
      draft.answer !== selected.answer ||
      JSON.stringify(draft.options) !== JSON.stringify(selected.options)
    );
  }, [selected, draft]);

  const editorMode: QuestionEditorMode = useMemo(() => {
    if (isComposingNew && draft) return "compose";
    if (selected && draft) return "edit";
    return "empty";
  }, [isComposingNew, selected, draft]);

  const error =
    infinite.error == null
      ? null
      : infinite.error instanceof Error
        ? infinite.error
        : new Error(String(infinite.error));

  const title = source ? `${source.examCode}` : "Câu hỏi";
  const subtitle = source?.fileName ?? "";

  const headerBusy = patchMutation.isPending || appendMutation.isPending;

  return (
    <>
      <Dialog open={open} onOpenChange={handleDialogOpenChange}>
        <DialogContent
          className={cn(
            "flex h-dvh max-h-dvh w-full max-w-none flex-col gap-0 overflow-hidden p-0",
            "fixed inset-0 left-0 top-0 translate-x-0 translate-y-0 rounded-none border-0 shadow-none sm:rounded-none"
          )}
        >
          <DialogHeader className="shrink-0 space-y-3 border-b px-4 py-3 text-left sm:px-6 sm:py-4">
            <div className="flex flex-wrap items-start justify-between gap-2 pr-10">
              <div className="min-w-0 flex-1">
                <DialogTitle className="text-base sm:text-lg">{title}</DialogTitle>
                <DialogDescription className="truncate font-mono text-xs">
                  {subtitle}
                </DialogDescription>
              </div>
              <Button
                type="button"
                size="sm"
                className="shrink-0 gap-1"
                disabled={headerBusy || isComposingNew}
                onClick={handleAddQuestion}
              >
                <>
                  <Plus className="h-4 w-4" aria-hidden />
                  Thêm câu hỏi
                </>
              </Button>
            </div>
          </DialogHeader>

          <div className="grid min-h-0 flex-1 grid-rows-[minmax(0,38vh)_minmax(0,1fr)] gap-0 overflow-hidden md:grid-cols-[minmax(0,280px)_minmax(0,1fr)] md:grid-rows-1 md:divide-x">
            <QuestionListPanel
              searchValue={questionSearchInput}
              onSearchChange={setQuestionSearchInput}
              questions={questions}
              selectedId={selected?.id ?? null}
              onSelect={handleSelect}
              onScroll={infinite.onScrollToLoadMore}
              isPending={infinite.isPending}
              isFetchingNextPage={infinite.isFetchingNextPage}
              error={error}
              totalItems={infinite.data?.pages?.[0]?.totalItems}
            />

            <QuestionEditorPanel
              draft={draft}
              setDraft={setDraftAndClearBankCheck}
              mode={editorMode}
              isDirty={isDirty}
              patchPending={patchMutation.isPending}
              appendPending={appendMutation.isPending}
              checkPending={checkMutation.isPending}
              deletePending={deleteMutation.isPending}
              bankCheck={bankCheck}
              onCheckBank={handleCheckBank}
              onSaveEdit={handleSaveEdit}
              onSaveNew={handleSaveNew}
              onDeselect={handleDeselect}
              onRequestDelete={() => setDeleteDialogOpen(true)}
            />
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xóa câu hỏi này?</AlertDialogTitle>
            <AlertDialogDescription>
              Câu sẽ bị xóa khỏi file nguồn và các câu còn lại được đánh số lại. Thao tác không hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel type="button">Hủy</AlertDialogCancel>
            <AlertDialogAction
              type="button"
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={(e) => {
                e.preventDefault();
                handleConfirmDelete();
              }}
            >
              Xóa
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
