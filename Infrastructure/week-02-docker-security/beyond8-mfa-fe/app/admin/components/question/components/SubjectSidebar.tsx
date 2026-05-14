"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { SubjectItem } from "@/lib/api/services/fetchQuestionSources";
import { flattenInfinitePages } from "@/hooks/useInfinityScroll";
import { useQuestionSourceSubjectsInfinityScroll } from "@/hooks/useQuestionSources";
import { cn } from "@/lib/utils/cn";

interface SubjectSidebarProps {
  selectedSlug: string | null;
  onSelectSubject: (subject: SubjectItem) => void;
  className?: string;
}

const SUBJECT_PAGE_SIZE = 13;

export function SubjectSidebar({ selectedSlug, onSelectSubject, className }: SubjectSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const { data, isPending, isFetchingNextPage, hasNextPage, error, refetch, onScrollToLoadMore } =
    useQuestionSourceSubjectsInfinityScroll({
      pageSize: SUBJECT_PAGE_SIZE,
      scrollOffset: 48,
      filters: debouncedSearch.trim() ? { q: debouncedSearch.trim() } : undefined,
    });

  const subjects = flattenInfinitePages(data?.pages);

  return (
    <Card
      className={cn(
        "flex h-full min-h-0 max-h-full flex-col overflow-hidden border bg-white shadow-sm",
        className
      )}
    >
      <CardHeader className="shrink-0 space-y-2 border-b px-3 py-3 pb-3 pt-4">
        <CardTitle className="text-base text-left">Danh sách subjects</CardTitle>
        <Input
          type="search"
          placeholder="Môn học"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="h-9 text-sm"
          aria-label="Tìm môn"
        />
      </CardHeader>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div
          className="min-h-0 flex-1 space-y-2 overflow-y-auto overflow-x-hidden px-3 py-3"
          onScroll={onScrollToLoadMore}
        >
          {isPending && subjects.length === 0 ? (
            <>
              {Array.from({ length: 6 }).map((_, idx) => (
                <Skeleton key={idx} className="h-12 w-full shrink-0" />
              ))}
            </>
          ) : error && subjects.length === 0 ? (
            <div className="flex flex-col gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-4 text-sm">
              <p className="text-destructive">
                {error instanceof Error ? error.message : "Lỗi tải dữ liệu"}
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-fit"
                onClick={() => void refetch()}
              >
                Thử lại
              </Button>
            </div>
          ) : subjects.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {debouncedSearch.trim() ? "Không tìm thấy môn nào." : "Chưa có subject nào."}
            </p>
          ) : (
            <>
              {subjects.map((subject) => (
                <button
                  key={subject.slug}
                  type="button"
                  className={cn(
                    "w-full shrink-0 rounded-lg border px-3 py-2 text-left transition-colors",
                    selectedSlug === subject.slug
                      ? "border-[#f9c48d] bg-[#fff3e5]"
                      : "hover:bg-muted/40"
                  )}
                  onClick={() => onSelectSubject(subject)}
                >
                  <p className="text-sm font-semibold">{subject.code}</p>
                  <p className="truncate text-xs text-muted-foreground">{subject.slug}</p>
                </button>
              ))}
              {isFetchingNextPage ? (
                <div className="flex justify-center py-2">
                  <Skeleton className="h-10 w-full max-w-[200px]" />
                </div>
              ) : null}
            </>
          )}
        </div>

        <div className="shrink-0 border-t border-border/80 bg-muted/10 px-3 py-2 text-center text-xs text-muted-foreground">
          {error && subjects.length > 0 ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-auto py-1 text-destructive"
              onClick={() => void refetch()}
            >
              Lỗi đồng bộ · Thử lại
            </Button>
          ) : isFetchingNextPage ? (
            "Đang tải thêm môn..."
          ) : hasNextPage ? (
            `${subjects.length} môn hiển thị · cuộn để tải tiếp`
          ) : subjects.length > 0 ? (
            `${subjects.length} môn`
          ) : null}
        </div>
      </div>
    </Card>
  );
}
