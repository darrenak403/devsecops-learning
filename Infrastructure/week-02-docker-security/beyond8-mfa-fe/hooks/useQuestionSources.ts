"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  fetchQuestionSources,
  type AdminPatchQuestionBody,
  type AdminSourceQuestionItem,
  type PaginationParams,
  type SourceItem,
  type SourceQuestionUpdateInput,
  type SubjectItem,
} from "@/lib/api/services/fetchQuestionSources";
import { type InfinityScrollFilters, useInfinityScroll } from "@/hooks/useInfinityScroll";
import type { ApiResponse } from "@/types/api";

export const QUESTION_SOURCE_QUERY_KEYS = {
  all: ["question-sources"] as const,
  subjects: () => [...QUESTION_SOURCE_QUERY_KEYS.all, "subjects"] as const,
  subjectList: (params: PaginationParams) =>
    [...QUESTION_SOURCE_QUERY_KEYS.subjects(), params] as const,
  allSubjectsFlat: () => [...QUESTION_SOURCE_QUERY_KEYS.all, "all-subjects"] as const,
  sources: (slug: string) => [...QUESTION_SOURCE_QUERY_KEYS.all, "sources", slug] as const,
  sourceList: (slug: string, params: PaginationParams) =>
    [...QUESTION_SOURCE_QUERY_KEYS.sources(slug), params] as const,
  allSourcesFlat: (slug: string) => [...QUESTION_SOURCE_QUERY_KEYS.sources(slug), "all"] as const,
  sourceQuestions: (slug: string, sourceId: string) =>
    [...QUESTION_SOURCE_QUERY_KEYS.all, "source-questions", slug, sourceId] as const,
};

const DEFAULT_STALE_TIME = 2 * 60 * 1000;
const DEFAULT_GC_TIME = 10 * 60 * 1000;

export function useQuestionSourceSubjects(params: PaginationParams) {
  return useQuery({
    queryKey: QUESTION_SOURCE_QUERY_KEYS.subjectList(params),
    queryFn: () => fetchQuestionSources.listSubjects(params),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
    placeholderData: keepPreviousData,
  });
}

export type QuestionSourceSubjectsInfiniteFilters = InfinityScrollFilters & { q?: string };

export type QuestionSourcesInfiniteFilters = InfinityScrollFilters & { q?: string };

export interface UseQuestionSourceSubjectsInfinityScrollOptions {
  /** Giới hạn mỗi lần fetch (mặc định 10, giống API admin subjects). */
  pageSize?: number;
  scrollOffset?: number;
  enabled?: boolean;
  staleTime?: number;
  gcTime?: number;
  filters?: QuestionSourceSubjectsInfiniteFilters;
  errorMessage?: string;
}

/**
 * Danh sách subjects với infinite query + {@link useInfinityScroll.onScrollToLoadMore}.
 * Phân trang server theo `page` / `limit` của {@link fetchQuestionSources.listSubjects}.
 */
export function useQuestionSourceSubjectsInfinityScroll(
  options: UseQuestionSourceSubjectsInfinityScrollOptions = {}
) {
  const {
    pageSize = 10,
    scrollOffset = 16,
    enabled = true,
    staleTime = DEFAULT_STALE_TIME,
    gcTime = DEFAULT_GC_TIME,
    filters,
    errorMessage = "Không thể tải danh sách môn học",
  } = options;

  return useInfinityScroll<SubjectItem, QuestionSourceSubjectsInfiniteFilters>({
    queryKey: [...QUESTION_SOURCE_QUERY_KEYS.subjects(), "infinity-scroll"],
    fetchPage: async ({
      pageNumber,
      pageSize: limit,
      ...extra
    }): Promise<ApiResponse<SubjectItem[]>> => {
      const bundle = await fetchQuestionSources.listSubjects({
        page: pageNumber,
        limit,
        ...(extra as PaginationParams),
      });
      return {
        success: true,
        message: "",
        code: 0,
        data: bundle.items,
        metadata: {
          pageNumber: bundle.page,
          totalPages: bundle.totalPages,
          totalItems: bundle.total,
          hasPreviousPage: bundle.hasPrevious,
          hasNextPage: bundle.hasNext,
        },
      };
    },
    filters,
    pageSize,
    scrollOffset,
    enabled,
    staleTime,
    gcTime,
    refetchOnWindowFocus: false,
    errorMessage,
  });
}

export interface UseQuestionSourcesInfinityScrollOptions {
  pageSize?: number;
  scrollOffset?: number;
  enabled?: boolean;
  staleTime?: number;
  gcTime?: number;
  filters?: QuestionSourcesInfiniteFilters;
  errorMessage?: string;
}

/**
 * Danh sách sources (đề) theo subject với infinite query + scroll load more.
 */
export function useQuestionSourcesInfinityScroll(
  slug: string | undefined,
  options: UseQuestionSourcesInfinityScrollOptions = {}
) {
  const {
    pageSize = 20,
    scrollOffset = 16,
    enabled = true,
    staleTime = DEFAULT_STALE_TIME,
    gcTime = DEFAULT_GC_TIME,
    filters,
    errorMessage = "Không thể tải danh sách đề",
  } = options;

  const resolvedEnabled = Boolean(slug) && enabled;

  return useInfinityScroll<SourceItem, QuestionSourcesInfiniteFilters>({
    queryKey: slug
      ? [...QUESTION_SOURCE_QUERY_KEYS.sources(slug), "infinity-scroll"]
      : [...QUESTION_SOURCE_QUERY_KEYS.all, "sources", "__none__", "infinity-scroll"],
    fetchPage: async ({
      pageNumber,
      pageSize: limit,
      ...extra
    }): Promise<ApiResponse<SourceItem[]>> => {
      if (!slug) {
        throw new Error("Missing subject slug");
      }
      const bundle = await fetchQuestionSources.listSourcesBySubject(slug, {
        page: pageNumber,
        limit,
        ...(extra as PaginationParams),
      });
      return {
        success: true,
        message: "",
        code: 0,
        data: bundle.items,
        metadata: {
          pageNumber: bundle.page,
          totalPages: bundle.totalPages,
          totalItems: bundle.total,
          hasPreviousPage: bundle.hasPrevious,
          hasNextPage: bundle.hasNext,
        },
      };
    },
    filters,
    pageSize,
    scrollOffset,
    enabled: resolvedEnabled,
    staleTime,
    gcTime,
    refetchOnWindowFocus: false,
    errorMessage,
  });
}

export function useQuestionSourcesBySubject(slug?: string, params: PaginationParams = {}) {
  return useQuery({
    queryKey: QUESTION_SOURCE_QUERY_KEYS.sourceList(slug ?? "", params),
    queryFn: async () => {
      if (!slug) {
        throw new Error("Missing subject slug");
      }
      return fetchQuestionSources.listSourcesBySubject(slug, params);
    },
    enabled: Boolean(slug),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
    placeholderData: keepPreviousData,
  });
}

export function useCreateAdminSubject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { slug: string }) => fetchQuestionSources.ensureAdminSubject(payload),
    onSuccess: (data) => {
      toast.success(`Đã có subject: ${data.code} (${data.slug})`);
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.allSubjectsFlat(),
      });
      void queryClient.invalidateQueries({ queryKey: QUESTION_SOURCE_QUERY_KEYS.subjects() });
    },
    onError: () => {
      toast.error("Không tạo / đồng bộ được subject");
    },
  });
}

export function useUploadQuestionSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { slug: string; file: File }) =>
      fetchQuestionSources.uploadSourceBySlug(payload),
    onSuccess: (data) => {
      toast.success(`Upload source thành công: ${data.fileName}`);
      void queryClient.invalidateQueries({ queryKey: QUESTION_SOURCE_QUERY_KEYS.subjects() });
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.sources(data.subjectSlug),
      });
      void queryClient.invalidateQueries({
        queryKey: [...QUESTION_SOURCE_QUERY_KEYS.sources(data.subjectSlug), "infinity-scroll"],
      });
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.allSourcesFlat(data.subjectSlug),
      });
    },
    onError: () => {
      toast.error("Upload source thất bại");
    },
  });
}

export function useDeleteQuestionSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { slug: string; sourceId: string }) =>
      fetchQuestionSources.deleteSource(payload),
    onSuccess: (_, variables) => {
      toast.success("Đã xóa source");
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.sources(variables.slug),
      });
      void queryClient.invalidateQueries({
        queryKey: [...QUESTION_SOURCE_QUERY_KEYS.sources(variables.slug), "infinity-scroll"],
      });
    },
    onError: () => {
      toast.error("Xóa source thất bại");
    },
  });
}

export function useAllAdminSubjects() {
  return useQuery({
    queryKey: QUESTION_SOURCE_QUERY_KEYS.allSubjectsFlat(),
    queryFn: () => fetchQuestionSources.listAllSubjects(),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
  });
}

export function useAllAdminSourcesForSlug(slug: string | undefined) {
  return useQuery({
    queryKey: QUESTION_SOURCE_QUERY_KEYS.allSourcesFlat(slug ?? ""),
    queryFn: async () => {
      if (!slug) return [];
      return fetchQuestionSources.listAllSourcesBySubject(slug);
    },
    enabled: Boolean(slug),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
  });
}

export function useMergeBankPreview() {
  return useMutation({
    mutationFn: (payload: { slug: string; deckSourceId: string }) =>
      fetchQuestionSources.mergeBankPreview(payload),
    onError: () => {
      toast.error("Xem trước merge thất bại");
    },
  });
}

export function useMergeIntoBank() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { slug: string; deckSourceId: string }) =>
      fetchQuestionSources.mergeIntoBank(payload),
    onSuccess: (data) => {
      toast.success(
        `Đã hợp nhất ngân hàng: +${data.added} câu, bỏ qua trùng ${data.skippedDuplicate}, tổng ${data.bankQuestionCount}`
      );
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.sources(data.subjectSlug),
      });
      void queryClient.invalidateQueries({
        queryKey: [...QUESTION_SOURCE_QUERY_KEYS.sources(data.subjectSlug), "infinity-scroll"],
      });
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.allSourcesFlat(data.subjectSlug),
      });
    },
    onError: () => {
      toast.error("Hợp nhất ngân hàng thất bại");
    },
  });
}

export type AdminSourceQuestionsFilters = InfinityScrollFilters & { q?: string };

export interface UseAdminSourceQuestionsInfinityScrollOptions {
  pageSize?: number;
  scrollOffset?: number;
  enabled?: boolean;
  staleTime?: number;
  gcTime?: number;
  filters?: AdminSourceQuestionsFilters;
  errorMessage?: string;
}

/**
 * Admin: danh sách câu hỏi của một source (phân trang + cuộn tải thêm).
 * `AdminSourceQuestionItem.id` trùng ordinal API (PATCH `/questions/{ordinal}`).
 */
export function useAdminSourceQuestionsInfinityScroll(
  slug: string | undefined,
  sourceId: string | undefined,
  options: UseAdminSourceQuestionsInfinityScrollOptions = {}
) {
  const {
    pageSize = 30,
    scrollOffset = 48,
    enabled = true,
    staleTime = DEFAULT_STALE_TIME,
    gcTime = DEFAULT_GC_TIME,
    filters,
    errorMessage = "Không thể tải câu hỏi",
  } = options;

  const resolvedEnabled = Boolean(slug) && Boolean(sourceId) && enabled;

  return useInfinityScroll<AdminSourceQuestionItem, AdminSourceQuestionsFilters>({
    queryKey: slug
      ? [...QUESTION_SOURCE_QUERY_KEYS.sourceQuestions(slug, sourceId ?? ""), "infinity-scroll"]
      : [...QUESTION_SOURCE_QUERY_KEYS.all, "source-questions", "__none__", "infinity-scroll"],
    fetchPage: async ({ pageNumber, pageSize: limit, ...extra }) => {
      if (!slug || !sourceId) {
        throw new Error("Missing subject slug or source id");
      }
      const qFilter = (extra as AdminSourceQuestionsFilters).q?.trim();
      const bundle = await fetchQuestionSources.listAdminSourceQuestions(slug, sourceId, {
        page: pageNumber,
        limit,
        ...(qFilter ? { q: qFilter } : {}),
      });
      return {
        success: true,
        message: "",
        code: 0,
        data: bundle.items,
        metadata: {
          pageNumber: bundle.page,
          totalPages: bundle.totalPages,
          totalItems: bundle.total,
          hasPreviousPage: bundle.hasPrevious,
          hasNextPage: bundle.hasNext,
        },
      };
    },
    filters,
    pageSize,
    scrollOffset,
    enabled: resolvedEnabled,
    staleTime,
    gcTime,
    refetchOnWindowFocus: false,
    errorMessage,
  });
}

export function usePatchAdminSourceQuestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: {
      slug: string;
      sourceId: string;
      ordinal: number;
      body: AdminPatchQuestionBody;
    }) => fetchQuestionSources.patchAdminSourceQuestion(payload),
    onSuccess: (data) => {
      toast.success(`Đã cập nhật câu #${data.ordinal}`);
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.sourceQuestions(data.subjectSlug, data.sourceId),
      });
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.sources(data.subjectSlug),
      });
      void queryClient.invalidateQueries({
        queryKey: [...QUESTION_SOURCE_QUERY_KEYS.sources(data.subjectSlug), "infinity-scroll"],
      });
    },
    onError: () => {
      toast.error("Không lưu được câu hỏi");
    },
  });
}

export function useCheckQuestionInBank() {
  return useMutation({
    mutationFn: (payload: { slug: string; body: SourceQuestionUpdateInput }) =>
      fetchQuestionSources.checkQuestionInBank(payload.slug, payload.body),
    onError: () => {
      toast.error("Không kiểm tra được ngân hàng câu hỏi");
    },
  });
}

/** Một câu mới: POST append; BE tự merge deck → bank khi cần. */
export function useAppendAdminSourceQuestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { slug: string; sourceId: string; body: SourceQuestionUpdateInput }) =>
      fetchQuestionSources.appendAdminSourceQuestion(payload),
    onSuccess: (data) => {
      if (data.warnings.length > 0) {
        toast.message("Đã thêm câu", { description: data.warnings.join(" · ") });
      } else {
        toast.success(`Đã thêm câu #${data.ordinal}`);
      }
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.sourceQuestions(data.subjectSlug, data.sourceId),
      });
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.sources(data.subjectSlug),
      });
      void queryClient.invalidateQueries({
        queryKey: [...QUESTION_SOURCE_QUERY_KEYS.sources(data.subjectSlug), "infinity-scroll"],
      });
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.allSourcesFlat(data.subjectSlug),
      });
    },
    onError: () => {
      toast.error("Không thêm được câu hỏi");
    },
  });
}

export function useDeleteAdminSourceQuestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { slug: string; sourceId: string; ordinal: number }) =>
      fetchQuestionSources.deleteAdminSourceQuestion(payload),
    onSuccess: (data) => {
      toast.success(`Đã xóa câu · còn ${data.questionCount} câu`);
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.sourceQuestions(data.subjectSlug, data.sourceId),
      });
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.sources(data.subjectSlug),
      });
      void queryClient.invalidateQueries({
        queryKey: [...QUESTION_SOURCE_QUERY_KEYS.sources(data.subjectSlug), "infinity-scroll"],
      });
      void queryClient.invalidateQueries({
        queryKey: QUESTION_SOURCE_QUERY_KEYS.allSourcesFlat(data.subjectSlug),
      });
    },
    onError: () => {
      toast.error("Không xóa được câu hỏi");
    },
  });
}
