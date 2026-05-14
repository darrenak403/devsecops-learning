"use client";

import { useEffect, useState } from "react";
import { useDeleteQuestionSource, useQuestionSourcesInfinityScroll } from "@/hooks/useQuestionSources";
import type { SourceItem, SubjectItem } from "@/lib/api/services/fetchQuestionSources";
import { flattenInfinitePages } from "@/hooks/useInfinityScroll";
import { useMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils/cn";
import { DeleteSourceDialog } from "./components/DeleteSourceDialog";
import { SourceQuestionsDialog } from "./components/QuestionsDialog";
import { SourcesPanel } from "./components/SourcesPanel";
import { SubjectSidebar } from "./components/SubjectSidebar";

type MobileQuestionTab = "subjects" | "sources";

export function QuestionManagementPlaceholder() {
  const isMobile = useMobile();
  const [mobileTab, setMobileTab] = useState<MobileQuestionTab>("subjects");
  const [selectedSubject, setSelectedSubject] = useState<SubjectItem | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sourceToDelete, setSourceToDelete] = useState<string | null>(null);
  const [questionsDialogOpen, setQuestionsDialogOpen] = useState(false);
  const [questionsDialogSource, setQuestionsDialogSource] = useState<SourceItem | null>(null);
  const [sourceSearchQuery, setSourceSearchQuery] = useState("");
  const [debouncedSourceQuery, setDebouncedSourceQuery] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSourceQuery(sourceSearchQuery), 300);
    return () => clearTimeout(t);
  }, [sourceSearchQuery]);

  const sourcesInfinite = useQuestionSourcesInfinityScroll(selectedSubject?.slug, {
    pageSize: 20,
    scrollOffset: 48,
    filters: debouncedSourceQuery.trim() ? { q: debouncedSourceQuery.trim() } : undefined,
    enabled: Boolean(selectedSubject),
  });

  const deleteMutation = useDeleteQuestionSource();

  const sources = flattenInfinitePages(sourcesInfinite.data?.pages);

  const handleDeleteSource = (sourceId: string) => {
    setSourceToDelete(sourceId);
    setDeleteDialogOpen(true);
  };

  const confirmDeleteSource = () => {
    if (!selectedSubject || !sourceToDelete) return;
    deleteMutation.mutate({ slug: selectedSubject.slug, sourceId: sourceToDelete });
    setDeleteDialogOpen(false);
    setSourceToDelete(null);
  };

  const handleSelectSubject = (subject: SubjectItem) => {
    setSelectedSubject(subject);
    setSourceSearchQuery("");
    setDebouncedSourceQuery("");
    setQuestionsDialogOpen(false);
    setQuestionsDialogSource(null);
    if (isMobile) setMobileTab("sources");
  };

  const handleOpenQuestions = (source: SourceItem) => {
    setQuestionsDialogSource(source);
    setQuestionsDialogOpen(true);
  };

  const panelShell = "h-full min-h-0 max-h-full min-w-0 overflow-hidden";

  const subjectSidebarEl = (
    <SubjectSidebar
      selectedSlug={selectedSubject?.slug ?? null}
      onSelectSubject={handleSelectSubject}
      className={cn(panelShell, isMobile ? "flex-1" : "md:h-full")}
    />
  );

  const sourcesError =
    sourcesInfinite.error == null
      ? null
      : sourcesInfinite.error instanceof Error
        ? sourcesInfinite.error
        : new Error(String(sourcesInfinite.error));

  const sourcesPanelEl = (
    <SourcesPanel
      selectedSubject={selectedSubject}
      sources={sources}
      isLoading={sourcesInfinite.isPending}
      isFetchingNextPage={sourcesInfinite.isFetchingNextPage}
      hasNextPage={Boolean(sourcesInfinite.hasNextPage)}
      error={sourcesError}
      onScrollToLoadMore={sourcesInfinite.onScrollToLoadMore}
      searchQuery={sourceSearchQuery}
      onSearchQueryChange={setSourceSearchQuery}
      onRefetch={() => void sourcesInfinite.refetch()}
      onDeleteSource={handleDeleteSource}
      onOpenQuestions={handleOpenQuestions}
      deletePending={deleteMutation.isPending}
      className={cn(panelShell, isMobile ? "flex-1" : "md:h-full")}
    />
  );

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-hidden md:gap-4">
      {isMobile ? (
        <div className="flex min-h-0 flex-1 flex-col gap-3">
          <div className="flex shrink-0 gap-1 rounded-xl border bg-muted/40 p-1">
            <button
              type="button"
              className={cn(
                "flex min-h-11 flex-1 flex-col justify-center rounded-lg px-2 py-1.5 text-center text-sm font-medium transition-colors",
                mobileTab === "subjects"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setMobileTab("subjects")}
            >
              Danh sách môn
            </button>
            <button
              type="button"
              className={cn(
                "flex min-h-11 flex-1 flex-col justify-center rounded-lg px-2 py-1.5 text-center text-sm font-medium transition-colors",
                mobileTab === "sources"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setMobileTab("sources")}
            >
              <span>Sources</span>
              {selectedSubject ? (
                <span className="truncate text-xs font-normal text-muted-foreground">
                  {selectedSubject.code}
                </span>
              ) : (
                <span className="text-xs font-normal text-muted-foreground">Chưa chọn</span>
              )}
            </button>
          </div>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            {mobileTab === "subjects" ? subjectSidebarEl : sourcesPanelEl}
          </div>
        </div>
      ) : (
        <div className="grid min-h-0 min-w-0 flex-1 auto-rows-fr gap-4 overflow-hidden md:grid-cols-[minmax(0,280px)_minmax(0,1fr)]">
          {subjectSidebarEl}
          {sourcesPanelEl}
        </div>
      )}

      <DeleteSourceDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={confirmDeleteSource}
        isDeleting={deleteMutation.isPending}
      />

      <SourceQuestionsDialog
        open={questionsDialogOpen}
        onOpenChange={(next) => {
          setQuestionsDialogOpen(next);
          if (!next) setQuestionsDialogSource(null);
        }}
        subjectSlug={selectedSubject?.slug ?? null}
        source={questionsDialogSource}
      />
    </div>
  );
}

export default QuestionManagementPlaceholder;
