"use client";

import type { UIEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { SourceItem, SubjectItem } from "@/lib/api/services/fetchQuestionSources";
import { useMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils/cn";
import { SourcesTableSkeleton } from "./SourcesTableSkeleton";

function formatUploadedAt(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

interface SourcesPanelProps {
  selectedSubject: SubjectItem | null;
  sources: SourceItem[];
  isLoading: boolean;
  isFetchingNextPage: boolean;
  hasNextPage: boolean;
  error: Error | null;
  onScrollToLoadMore: (event: UIEvent<HTMLElement>) => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  onRefetch: () => void;
  onDeleteSource: (sourceId: string) => void;
  onOpenQuestions?: (source: SourceItem) => void;
  deletePending: boolean;
  className?: string;
}

export function SourcesPanel({
  selectedSubject,
  sources,
  isLoading,
  isFetchingNextPage,
  hasNextPage,
  error,
  onScrollToLoadMore,
  searchQuery,
  onSearchQueryChange,
  onRefetch,
  onDeleteSource,
  onOpenQuestions,
  deletePending,
  className,
}: SourcesPanelProps) {
  const isMobile = useMobile();
  const trimmedSearch = searchQuery.trim();
  const showNoMatch =
    !isLoading && Boolean(selectedSubject) && sources.length === 0 && Boolean(trimmedSearch);
  const showEmptySubject =
    !isLoading && Boolean(selectedSubject) && sources.length === 0 && !trimmedSearch;

  return (
    <div className={cn("flex h-full min-h-0 max-h-full flex-col overflow-hidden", className)}>
      <Card className="flex h-full min-h-0 max-h-full flex-col overflow-hidden border bg-white shadow-sm">
        <CardHeader className="shrink-0 space-y-2 border-b px-4 py-3 pb-3 pt-4">
          <CardTitle className="text-base">
            {selectedSubject ? `Sources — ${selectedSubject.code}` : "Danh sách sources"}
          </CardTitle>
          {selectedSubject ? (
            <>
              <Input
                type="search"
                placeholder="Tìm đề"
                value={searchQuery}
                onChange={(e) => onSearchQueryChange(e.target.value)}
                className="h-9 text-sm"
                aria-label="Tìm đề"
              />
              <p className="truncate text-xs text-muted-foreground md:hidden">
                {selectedSubject.slug}
              </p>
            </>
          ) : null}
        </CardHeader>

        <CardContent className="flex min-h-0 flex-1 flex-col gap-0 overflow-hidden px-0 pb-0 pt-0">
          {!selectedSubject ? (
            <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-8 text-center">
              <p className="text-sm font-medium text-foreground">Chưa chọn môn</p>
              <p className="mt-2 max-w-sm text-xs text-muted-foreground md:text-sm">
                {isMobile
                  ? "Mở tab «Danh sách môn», chọn một subject rồi quay lại tab «Sources»."
                  : "Chọn một subject ở cột trái để xem và quản lý sources."}
              </p>
            </div>
          ) : (
            <>
              <div
                className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-4 pt-2 md:overflow-x-auto md:pt-3"
                onScroll={onScrollToLoadMore}
              >
                {error && sources.length === 0 ? (
                  <div className="flex flex-col gap-2 rounded-lg border border-destructive/30 bg-destructive/5 py-4 text-sm">
                    <p className="text-destructive">{error.message}</p>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="w-fit"
                      onClick={() => void onRefetch()}
                    >
                      Thử lại
                    </Button>
                  </div>
                ) : isLoading && sources.length === 0 ? (
                  <SourcesTableSkeleton variant={isMobile ? "cards" : "table"} />
                ) : showEmptySubject ? (
                  <p className="py-4 text-sm text-muted-foreground">
                    Subject này chưa có source nào.
                  </p>
                ) : showNoMatch ? (
                  <p className="py-4 text-sm text-muted-foreground">
                    Không tìm thấy đề nào khớp tìm kiếm.
                  </p>
                ) : isMobile ? (
                  <div className="space-y-3 pb-2">
                    {sources.map((source) => (
                      <Card
                        key={source.sourceId}
                        className={cn(
                          "border shadow-sm",
                          isFetchingNextPage && "border-dashed opacity-70 transition-opacity"
                        )}
                      >
                        <CardContent className="space-y-3 p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                                Exam
                              </p>
                              <p className="font-semibold">{source.examCode}</p>
                            </div>
                            <div className="flex shrink-0 gap-2">
                              {onOpenQuestions ? (
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  type="button"
                                  onClick={() => onOpenQuestions(source)}
                                >
                                  Câu hỏi
                                </Button>
                              ) : null}
                              <Button
                                variant="destructive"
                                size="sm"
                                disabled={deletePending}
                                onClick={() => onDeleteSource(source.sourceId)}
                              >
                                Xóa
                              </Button>
                            </div>
                          </div>
                          <div>
                            <p className="text-[11px] font-medium text-muted-foreground">File</p>
                            <p className="break-all font-mono text-sm">{source.fileName}</p>
                          </div>
                          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
                            <div>
                              <p className="text-[11px] text-muted-foreground">Số câu</p>
                              <p className="font-medium">{source.questionCount}</p>
                            </div>
                            <div>
                              <p className="text-[11px] text-muted-foreground">Upload</p>
                              <p className="text-muted-foreground">
                                {formatUploadedAt(source.uploadedAt)}
                              </p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <div className="max-h-full overflow-x-auto rounded-xl border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Exam</TableHead>
                          <TableHead>File</TableHead>
                          <TableHead>Số câu</TableHead>
                          <TableHead>Upload</TableHead>
                          <TableHead className="text-right">Thao tác</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sources.map((source) => (
                          <TableRow key={source.sourceId}>
                            <TableCell className="whitespace-nowrap">{source.examCode}</TableCell>
                            <TableCell className="max-w-[min(12rem,40vw)] truncate">
                              {source.fileName}
                            </TableCell>
                            <TableCell>{source.questionCount}</TableCell>
                            <TableCell className="whitespace-nowrap">
                              {formatUploadedAt(source.uploadedAt)}
                            </TableCell>
                            <TableCell>
                              <div className="flex justify-end gap-2">
                                {onOpenQuestions ? (
                                  <Button
                                    variant="secondary"
                                    size="sm"
                                    type="button"
                                    onClick={() => onOpenQuestions(source)}
                                  >
                                    Câu hỏi
                                  </Button>
                                ) : null}
                                <Button
                                  variant="destructive"
                                  size="sm"
                                  disabled={deletePending}
                                  onClick={() => onDeleteSource(source.sourceId)}
                                >
                                  Xóa
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>

              <div className="shrink-0 border-t border-border/80 bg-muted/10 px-4 py-2 text-center text-xs text-muted-foreground">
                {error && sources.length > 0 ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-auto py-1 text-destructive"
                    onClick={() => void onRefetch()}
                  >
                    Lỗi đồng bộ · Thử lại
                  </Button>
                ) : isFetchingNextPage ? (
                  "Đang tải thêm đề..."
                ) : hasNextPage ? (
                  `${sources.length} đề hiển thị · cuộn để tải tiếp`
                ) : sources.length > 0 ? (
                  `${sources.length} đề`
                ) : null}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
