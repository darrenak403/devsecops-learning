import { type QueryKey, useInfiniteQuery } from "@tanstack/react-query";
import { type UIEvent, useCallback } from "react";
import type { ApiResponse } from "@/types/api";

/** Filter object được merge với pageNumber / pageSize khi gọi API. */
export type InfinityScrollFilters = Record<string, unknown>;

export interface InfinitePageResult<TItem> {
  pageIndex: number;
  totalPages: number;
  totalItems: number;
  hasPreviousPage: boolean;
  hasNextPage: boolean;
  items: TItem[];
}

/** Metadata phân trang thường gặp từ backend (optional). */
interface PaginationMetadata {
  pageNumber?: number;
  totalPages?: number;
  totalItems?: number;
  hasPreviousPage?: boolean;
  hasNextPage?: boolean;
}

function getPaginationMetadata(metadata: unknown): PaginationMetadata {
  if (metadata && typeof metadata === "object") {
    return metadata as PaginationMetadata;
  }
  return {};
}

interface UseInfinityScrollOptions<
  TItem,
  TFilters extends InfinityScrollFilters = InfinityScrollFilters,
> {
  queryKey: QueryKey;
  fetchPage: (
    params: TFilters & { pageNumber: number; pageSize: number }
  ) => Promise<ApiResponse<TItem[]>>;
  filters?: TFilters;
  pageSize?: number;
  scrollOffset?: number;
  enabled?: boolean;
  staleTime?: number;
  gcTime?: number;
  refetchOnWindowFocus?: boolean;
  errorMessage?: string;
  mapItems?: (response: ApiResponse<TItem[]>) => TItem[];
}

export function useInfinityScroll<
  TItem,
  TFilters extends InfinityScrollFilters = InfinityScrollFilters,
>({
  queryKey,
  fetchPage,
  filters,
  pageSize = 20,
  scrollOffset = 16,
  enabled = true,
  staleTime = 0,
  gcTime = 0,
  refetchOnWindowFocus = false,
  errorMessage = "Không thể tải dữ liệu",
  mapItems,
}: UseInfinityScrollOptions<TItem, TFilters>) {
  const infiniteQuery = useInfiniteQuery({
    queryKey: [...queryKey, filters ?? {}, pageSize],
    initialPageParam: 1,
    enabled,
    staleTime,
    gcTime,
    refetchOnWindowFocus,
    queryFn: async ({ pageParam }): Promise<InfinitePageResult<TItem>> => {
      const response = await fetchPage({
        ...(filters ?? ({} as TFilters)),
        pageNumber: pageParam,
        pageSize,
      });

      if (!response.success) {
        throw new Error(response.message || errorMessage);
      }

      const meta = getPaginationMetadata(response.metadata);
      const pageIndex = meta.pageNumber ?? pageParam;
      const totalPages = meta.totalPages ?? pageIndex;
      const totalItems = meta.totalItems ?? response.data.length;

      return {
        pageIndex,
        totalPages,
        totalItems,
        hasPreviousPage: meta.hasPreviousPage ?? pageIndex > 1,
        hasNextPage: meta.hasNextPage ?? pageIndex < totalPages,
        items: mapItems ? mapItems(response) : response.data,
      };
    },
    getNextPageParam: (lastPage) => (lastPage.hasNextPage ? lastPage.pageIndex + 1 : undefined),
  });

  const { hasNextPage, isFetchingNextPage, fetchNextPage } = infiniteQuery;

  const onScrollToLoadMore = useCallback(
    (event: UIEvent<HTMLElement>) => {
      const element = event.currentTarget;
      const reachedBottom =
        element.scrollTop + element.clientHeight >= element.scrollHeight - scrollOffset;

      if (reachedBottom && hasNextPage && !isFetchingNextPage) {
        void fetchNextPage();
      }
    },
    [fetchNextPage, hasNextPage, isFetchingNextPage, scrollOffset]
  );

  return {
    ...infiniteQuery,
    onScrollToLoadMore,
  };
}

export const flattenInfinitePages = <TItem,>(pages?: InfinitePageResult<TItem>[]) =>
  pages?.flatMap((page) => page.items) ?? [];
