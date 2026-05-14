"use client";

import type { UIEvent } from "react";
import { Loader2 } from "lucide-react";

import type { AdminSourceQuestionItem } from "@/lib/api/services/fetchQuestionSources";
import { cn } from "@/lib/utils/cn";

import { SearchBar } from "./SearchQuestionBar";

interface QuestionListPanelProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  questions: AdminSourceQuestionItem[];
  selectedId: number | null;
  onSelect: (q: AdminSourceQuestionItem) => void;
  onScroll: (event: UIEvent<HTMLElement>) => void;
  isPending: boolean;
  isFetchingNextPage: boolean;
  error: Error | null;
  totalItems: number | undefined;
}

export function QuestionListPanel({
  searchValue,
  onSearchChange,
  questions,
  selectedId,
  onSelect,
  onScroll,
  isPending,
  isFetchingNextPage,
  error,
  totalItems,
}: QuestionListPanelProps) {
  return (
    <div className="flex min-h-0 flex-col overflow-hidden border-b md:border-b-0">
      <SearchBar value={searchValue} onChange={onSearchChange} />
      <div className="shrink-0 border-b px-3 py-2 text-xs text-muted-foreground">
        {isPending && questions.length === 0 ? (
          <span className="flex items-center gap-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Đang tải…
          </span>
        ) : error && questions.length === 0 ? (
          <span className="text-destructive">{error.message}</span>
        ) : (
          <>
            {questions.length} / {totalItems ?? "—"} câu
            {isFetchingNextPage ? " · Đang tải thêm…" : ""}
          </>
        )}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto" onScroll={onScroll}>
        {questions.map((q) => (
          <button
            key={q.id}
            type="button"
            onClick={() => onSelect(q)}
            className={cn(
              "flex w-full flex-col gap-0.5 border-b px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted/60",
              selectedId === q.id && "bg-primary/10 hover:bg-primary/15"
            )}
          >
            <span className="text-[11px] font-medium text-muted-foreground">Câu {q.id}</span>
            <span className="line-clamp-3 text-foreground">{q.stem || "—"}</span>
          </button>
        ))}
        {isPending && questions.length === 0 ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : null}
      </div>
    </div>
  );
}
