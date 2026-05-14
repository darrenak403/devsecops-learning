"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { fetchSubjectListPage, type SubjectItem } from "@/lib/api/services/fetchQuestionSources";
import { QUESTION_SOURCE_QUERY_KEYS } from "@/hooks/useQuestionSources";
import { BookOpen, FileText, ListChecks, PlusCircle, Search, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils/cn";

const SUBJECT_PICKER_PAGE_SIZE = 50;
const SUBJECT_SEARCH_DEBOUNCE_MS = 300;

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}

type SubjectFilenameCardProps = {
  /** Môn đang chọn (từ cache danh sách parent) — hiển thị khi ô đóng */
  selectedSubjectMeta: SubjectItem | null;
  isSubjectMetaLoading: boolean;
  selectedSlug: string;
  newSlugDraft: string;
  deckFilename: string;
  uploadFileName: string;
  isSourcesLoading: boolean;
  filenameDuplicate: boolean;
  isEnsuringSubject: boolean;
  onSubjectChange: (slug: string) => void;
  onSlugDraftChange: (value: string) => void;
  onEnsureSubject: () => void;
  onDeckFilenameChange: (value: string) => void;
};

export function SubjectFilenameCard(props: SubjectFilenameCardProps) {
  const {
    selectedSubjectMeta,
    isSubjectMetaLoading,
    selectedSlug,
    newSlugDraft,
    deckFilename,
    uploadFileName,
    isSourcesLoading,
    filenameDuplicate,
    isEnsuringSubject,
    onSubjectChange,
    onSlugDraftChange,
    onEnsureSubject,
    onDeckFilenameChange,
  } = props;

  const [subjectPickerOpen, setSubjectPickerOpen] = useState(false);
  /** Search text while dropdown is open; when closed, input shows selected label instead */
  const [subjectQuery, setSubjectQuery] = useState("");
  const subjectPickerRef = useRef<HTMLDivElement>(null);

  const debouncedSubjectQuery = useDebouncedValue(subjectQuery, SUBJECT_SEARCH_DEBOUNCE_MS);

  const subjectPickerInfinite = useInfiniteQuery({
    queryKey: [
      ...QUESTION_SOURCE_QUERY_KEYS.subjects(),
      "deck-markdown-picker",
      debouncedSubjectQuery.trim() || "__no_q__",
    ],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      fetchSubjectListPage({
        page: pageParam,
        limit: SUBJECT_PICKER_PAGE_SIZE,
        q: debouncedSubjectQuery.trim() || undefined,
      }),
    getNextPageParam: (lastPage) => (lastPage.hasNext ? lastPage.page + 1 : undefined),
    enabled: subjectPickerOpen,
  });

  const fetchedSubjects = useMemo(
    () => subjectPickerInfinite.data?.pages.flatMap((p) => p.items) ?? [],
    [subjectPickerInfinite.data?.pages]
  );

  const listSubjectsMerged = useMemo(() => {
    const seen = new Set(fetchedSubjects.map((s) => s.slug));
    const out = [...fetchedSubjects];
    if (
      selectedSubjectMeta &&
      selectedSlug &&
      selectedSlug === selectedSubjectMeta.slug &&
      !seen.has(selectedSlug)
    ) {
      out.unshift(selectedSubjectMeta);
    }
    return out;
  }, [fetchedSubjects, selectedSubjectMeta, selectedSlug]);

  const selectedSubjectLabel = selectedSubjectMeta
    ? `${selectedSubjectMeta.code} (${selectedSubjectMeta.slug})`
    : selectedSlug.trim()
      ? selectedSlug
      : "";

  /** One input: collapsed shows selection; expanded shows search query */
  const subjectInputValue = subjectPickerOpen ? subjectQuery : selectedSubjectLabel;

  useEffect(() => {
    if (!subjectPickerOpen) return;
    const onDocDown = (e: MouseEvent) => {
      const el = subjectPickerRef.current;
      if (el && !el.contains(e.target as Node)) {
        setSubjectPickerOpen(false);
        setSubjectQuery("");
      }
    };
    document.addEventListener("mousedown", onDocDown);
    return () => document.removeEventListener("mousedown", onDocDown);
  }, [subjectPickerOpen]);

  return (
    <Card className="overflow-hidden border border-border shadow-none">
      <CardHeader className="space-y-4 border-b border-border/80 bg-muted/20 pb-2">
        <div>
          <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-primary">
            Hướng dẫn
          </p>
          <CardTitle className="mt-1 text-base">Bước 1: Môn & tên file</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 bg-muted/15 p-4 sm:p-6 md:grid-cols-2 md:items-stretch md:gap-6">
        <div className="flex h-full min-h-0 min-w-0 flex-col gap-4">
          <section
            aria-labelledby="deck-step1-subject-heading"
            className={cn(
              "rounded-xl border border-border bg-background p-4",
              "flex flex-col gap-3"
            )}
          >
            <div className="flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/60 text-foreground">
                <BookOpen className="h-5 w-5" aria-hidden />
              </span>
              <div className="min-w-0 flex-1 space-y-1">
                <h3
                  id="deck-step1-subject-heading"
                  className="text-sm font-bold tracking-tight text-foreground"
                >
                  1. Chọn môn học
                </h3>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Danh sách môn đang có trên hệ thống — luôn chọn lại sau khi{" "}
                  <span className="font-medium text-foreground">tạo môn mới</span> ở khối bên dưới.
                </p>
              </div>
            </div>
            {isSubjectMetaLoading ? (
              <Skeleton className="h-11 w-full rounded-lg" />
            ) : (
              <div ref={subjectPickerRef} className="relative">
                <div className="relative">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden
                  />
                  <Input
                    id="deck-subject-combobox"
                    type="text"
                    role="combobox"
                    aria-expanded={subjectPickerOpen}
                    aria-controls="deck-subject-listbox"
                    aria-autocomplete="list"
                    autoComplete="off"
                    value={subjectInputValue}
                    placeholder="Chọn hoặc tìm môn (mã, slug)…"
                    onChange={(e) => {
                      setSubjectQuery(e.target.value);
                      setSubjectPickerOpen(true);
                    }}
                    onFocus={() => {
                      setSubjectPickerOpen(true);
                      setSubjectQuery("");
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Escape") {
                        setSubjectPickerOpen(false);
                        setSubjectQuery("");
                        e.currentTarget.blur();
                      }
                    }}
                    className={cn(
                      "h-11 border border-input bg-background pl-9 text-sm font-medium shadow-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                      !subjectPickerOpen &&
                        !selectedSubjectMeta &&
                        !selectedSlug.trim() &&
                        "text-muted-foreground"
                    )}
                  />
                </div>

                {subjectPickerOpen ? (
                  <ul
                    id="deck-subject-listbox"
                    role="listbox"
                    aria-label="Danh sách môn"
                    className={cn(
                      "absolute left-0 right-0 top-[calc(100%+4px)] z-50 max-h-[min(260px,45vh)] overflow-y-auto rounded-md border border-input bg-popover p-1 text-popover-foreground shadow-none"
                    )}
                  >
                    {subjectPickerInfinite.isLoading ? (
                      <li className="px-3 py-6 text-center text-sm text-muted-foreground">
                        Đang tải danh sách…
                      </li>
                    ) : subjectPickerInfinite.isError ? (
                      <li className="px-3 py-6 text-center text-sm text-destructive">
                        Không tải được danh sách môn. Thử lại sau.
                      </li>
                    ) : listSubjectsMerged.length === 0 ? (
                      <li className="px-3 py-6 text-center text-sm text-muted-foreground">
                        {debouncedSubjectQuery.trim()
                          ? `Không có môn khớp “${debouncedSubjectQuery.trim()}”.`
                          : "Chưa có môn nào."}
                      </li>
                    ) : (
                      <>
                        {listSubjectsMerged.map((s) => {
                          const active = s.slug === selectedSlug;
                          return (
                            <li key={s.slug} role="presentation">
                              <button
                                type="button"
                                role="option"
                                aria-selected={active}
                                className={cn(
                                  "flex w-full rounded-sm px-2 py-2 text-left text-sm outline-none",
                                  active
                                    ? "bg-accent font-medium text-accent-foreground"
                                    : "hover:bg-accent/80 hover:text-accent-foreground"
                                )}
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                }}
                                onClick={() => {
                                  onSubjectChange(s.slug);
                                  setSubjectQuery("");
                                  setSubjectPickerOpen(false);
                                }}
                              >
                                <span className="break-all">
                                  {s.code} ({s.slug})
                                </span>
                              </button>
                            </li>
                          );
                        })}
                        {subjectPickerInfinite.hasNextPage ? (
                          <li className="sticky bottom-0 border-t border-border bg-popover p-1">
                            <Button
                              type="button"
                              variant="ghost"
                              className="h-9 w-full text-sm text-muted-foreground"
                              disabled={subjectPickerInfinite.isFetchingNextPage}
                              onMouseDown={(e) => e.preventDefault()}
                              onClick={() => void subjectPickerInfinite.fetchNextPage()}
                            >
                              {subjectPickerInfinite.isFetchingNextPage ? "Đang tải…" : "Tải thêm"}
                            </Button>
                          </li>
                        ) : null}
                      </>
                    )}
                  </ul>
                ) : null}
              </div>
            )}
          </section>

          <section
            aria-labelledby="deck-step1-new-subject-heading"
            className={cn(
              "rounded-xl border border-border bg-background p-4",
              "flex flex-col gap-3"
            )}
          >
            <div className="flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/60 text-foreground">
                <PlusCircle className="h-5 w-5" aria-hidden />
              </span>
              <div className="min-w-0 flex-1 space-y-1">
                <h3
                  id="deck-step1-new-subject-heading"
                  className="text-sm font-bold tracking-tight text-foreground"
                >
                  Môn chưa có trong danh sách?
                </h3>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Nhập slug (vd{" "}
                  <span className="font-mono font-medium text-foreground">mln131</span>), bấm{" "}
                  <span className="font-semibold text-amber-800 dark:text-amber-300">
                    Tạo môn học mới
                  </span>
                  , rồi chọn lại môn ở <span className="font-semibold text-foreground">mục 1</span>.
                </p>
              </div>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
              <Input
                placeholder="Slug môn mới (vd mln131)"
                value={newSlugDraft}
                onChange={(e) => onSlugDraftChange(e.target.value)}
                className="min-w-0 border border-input bg-background shadow-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:flex-1"
              />
              <Button
                type="button"
                className="h-10 shrink-0 gap-2 bg-amber-600 font-semibold text-white shadow-none hover:bg-amber-700 dark:bg-amber-600 dark:hover:bg-amber-500 sm:w-auto"
                onClick={onEnsureSubject}
                disabled={isEnsuringSubject}
              >
                <Sparkles className="h-4 w-4 shrink-0 opacity-90" aria-hidden />
                {isEnsuringSubject ? "Đang tạo…" : "Tạo môn học mới"}
              </Button>
            </div>
          </section>
        </div>

        <section
          aria-labelledby="deck-step1-file-heading"
          className={cn(
            "flex h-full min-h-0 min-w-0 flex-col gap-3 rounded-xl border border-border bg-background p-4"
          )}
        >
          <div className="flex shrink-0 items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/60 text-foreground">
              <FileText className="h-5 w-5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1 space-y-1">
              <h3
                id="deck-step1-file-heading"
                className="text-sm font-bold tracking-tight text-foreground"
              >
                2. Tên file deck (.md)
              </h3>
              <p className="text-xs leading-relaxed text-muted-foreground">
                Tên file khi upload lên server — không trùng file đã có của{" "}
                <span className="font-medium text-foreground">môn đã chọn</span>.
              </p>
            </div>
          </div>
          <Input
            placeholder="Ví dụ MLN111C2 - SU 2025 - FEKTS"
            value={deckFilename}
            onChange={(e) => onDeckFilenameChange(e.target.value)}
            className="shrink-0 border border-input bg-background font-medium shadow-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
          <div className="shrink-0 rounded-lg border border-dashed border-border bg-muted/30 px-3 py-2 font-mono text-xs text-muted-foreground">
            <span className="font-sans text-[11px] font-semibold uppercase tracking-wide text-foreground/80">
              Tên gửi lên server
            </span>
            <p className="mt-1 break-all text-foreground">{uploadFileName || "—"}</p>
          </div>
          {selectedSlug && isSourcesLoading ? (
            <p className="shrink-0 text-xs text-muted-foreground">Đang tải danh sách file…</p>
          ) : null}
          {filenameDuplicate ? (
            <p className="shrink-0 rounded-lg border border-amber-500/35 bg-amber-500/10 px-3 py-2 text-sm font-medium text-amber-900 dark:text-amber-100">
              File này đã có trên môn này — đổi tên hoặc mở file đã upload.
            </p>
          ) : null}
          <div className="min-h-0 flex-1" aria-hidden />
          <p className="shrink-0 border-t border-border pt-3 text-center text-[11px] leading-relaxed text-muted-foreground sm:text-left">
            <ListChecks
              className="mb-1 inline h-3.5 w-3.5 align-text-bottom text-foreground sm:mb-0 sm:mr-1"
              aria-hidden
            />
            Xong hai mục trên thì bấm{" "}
            <span className="font-semibold text-foreground">Tiếp tục — soạn câu</span> ngay{" "}
            <span className="font-medium text-foreground">dưới thẻ này</span>.
          </p>
        </section>
      </CardContent>
    </Card>
  );
}
