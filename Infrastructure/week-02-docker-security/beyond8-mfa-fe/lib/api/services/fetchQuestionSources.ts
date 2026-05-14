import apiService from "../core";
import type { ApiResponse } from "@/types/api";

export interface PaginationParams {
  page?: number;
  limit?: number;
  q?: string;
}

export interface SubjectItem {
  slug: string;
  code: string;
  hint: string;
  bankQuestionCount?: number;
}

export interface SubjectListResponse {
  items: SubjectItem[];
  page: number;
  limit: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface SourceItem {
  sourceId: string;
  examCode: string;
  fileName: string;
  questionCount: number;
  isAggregatedBank: boolean;
  uploadedAt: string | null;
}

export interface SourceListResponse {
  items: SourceItem[];
  page: number;
  limit: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface UploadSourceResponse {
  sourceId: string;
  subjectSlug: string;
  subjectCode: string;
  examCode: string;
  fileName: string;
  checksum: string;
  questionCount: number;
  warnings: string[];
  deduplicated: boolean;
}

export interface MergeBankPreviewResponse {
  subjectSlug: string;
  deckSourceId: string;
  added: number;
  skippedDuplicate: number;
  bankQuestionCountAfter: number;
  wouldCreateBank: boolean;
}

export interface MergeIntoBankResponse {
  subjectSlug: string;
  bankSourceId: string;
  deckSourceId: string;
  added: number;
  skippedDuplicate: number;
  bankQuestionCount: number;
}

export interface AdminSourceQuestionItem {
  id: number;
  stem: string;
  options: { label: string; text: string }[];
  answer: string;
  answerCount: number;
  imageUrl: string | null;
}

export interface AdminSourceQuestionsPageResponse {
  items: AdminSourceQuestionItem[];
  page: number;
  limit: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface AdminPatchQuestionBody {
  stem?: string;
  options?: { label: string; text: string }[];
  answer?: string;
}

export interface AdminPatchQuestionResponse {
  sourceId: string;
  subjectSlug: string;
  examCode: string;
  fileName: string;
  ordinal: number;
}

export interface SourceQuestionUpdateInput {
  stem: string;
  options: { label: string; text: string }[];
  answer: string;
}

export interface BankCheckDuplicateResponse {
  normalizedHash: string;
  existsInBank: boolean;
}

export interface AdminAppendQuestionResponse {
  sourceId: string;
  subjectSlug: string;
  examCode: string;
  fileName: string;
  ordinal: number;
  questionCount: number;
  warnings: string[];
}

export interface AdminDeleteQuestionResponse {
  sourceId: string;
  subjectSlug: string;
  examCode: string;
  fileName: string;
  questionCount: number;
}

const MAX_PAGE = 100;

export async function fetchSubjectListPage(params: PaginationParams): Promise<SubjectListResponse> {
  const trimmed = params.q?.trim();
  const query: Record<string, string | number> = {
    page: params.page ?? 1,
    limit: params.limit ?? 10,
  };
  if (trimmed) query.q = trimmed;
  const response = await apiService.get<ApiResponse<SubjectListResponse>>(
    "/api/v1/admin/question-sources/subjects",
    query
  );
  return response.data.data;
}

async function fetchSourceListPage(
  slug: string,
  params: PaginationParams
): Promise<SourceListResponse> {
  const trimmed = params.q?.trim();
  const query: Record<string, string | number> = {
    page: params.page ?? 1,
    limit: params.limit ?? 10,
  };
  if (trimmed) query.q = trimmed;
  const response = await apiService.get<ApiResponse<SourceListResponse>>(
    `/api/v1/admin/question-sources/subjects/${slug}/sources`,
    query
  );
  return response.data.data;
}

export const fetchQuestionSources = {
  listAllSubjects: async (): Promise<SubjectItem[]> => {
    const items: SubjectItem[] = [];
    let page = 1;
    for (;;) {
      const data = await fetchSubjectListPage({ page, limit: MAX_PAGE });
      items.push(...data.items);
      if (!data.hasNext) break;
      page += 1;
    }
    return items;
  },

  listAllSourcesBySubject: async (slug: string): Promise<SourceItem[]> => {
    const items: SourceItem[] = [];
    let page = 1;
    for (;;) {
      const data = await fetchSourceListPage(slug, { page, limit: MAX_PAGE });
      items.push(...data.items);
      if (!data.hasNext) break;
      page += 1;
    }
    return items;
  },

  listSubjects: async (params: PaginationParams = {}) => fetchSubjectListPage(params),

  listSourcesBySubject: async (slug: string, params: PaginationParams = {}) =>
    fetchSourceListPage(slug, params),

  uploadSourceBySlug: async (payload: { slug: string; file: File }) => {
    const formData = new FormData();
    formData.append("file", payload.file);

    const response = await apiService.post<ApiResponse<UploadSourceResponse>, FormData>(
      `/api/v1/admin/question-sources/subjects/${payload.slug}/upload`,
      formData
    );
    return response.data.data;
  },

  deleteSource: async (payload: { slug: string; sourceId: string }) => {
    const response = await apiService.request<ApiResponse<Record<string, never>>>({
      method: "DELETE",
      url: `/api/v1/admin/question-sources/subjects/${payload.slug}/sources/${payload.sourceId}`,
    });
    return response.data;
  },

  mergeBankPreview: async (payload: { slug: string; deckSourceId: string }) => {
    const response = await apiService.get<ApiResponse<MergeBankPreviewResponse>>(
      `/api/v1/admin/question-sources/subjects/${payload.slug}/sources/${payload.deckSourceId}/merge-into-bank/preview`
    );
    return response.data.data;
  },

  mergeIntoBank: async (payload: { slug: string; deckSourceId: string }) => {
    const response = await apiService.post<ApiResponse<MergeIntoBankResponse>>(
      `/api/v1/admin/question-sources/subjects/${payload.slug}/sources/${payload.deckSourceId}/merge-into-bank`
    );
    return response.data.data;
  },

  ensureAdminSubject: async (payload: { slug: string }) => {
    const slug = payload.slug.trim().toLowerCase();
    const response = await apiService.post<ApiResponse<SubjectItem>, { slug: string }>(
      "/api/v1/admin/question-sources/subjects",
      { slug }
    );
    return response.data.data;
  },

  listAdminSourceQuestions: async (
    slug: string,
    sourceId: string,
    params: PaginationParams = {}
  ): Promise<AdminSourceQuestionsPageResponse> => {
    const query: Record<string, string | number> = {
      page: params.page ?? 1,
      limit: params.limit ?? MAX_PAGE,
    };
    const qq = params.q?.trim();
    if (qq) query.q = qq;
    const response = await apiService.get<ApiResponse<AdminSourceQuestionsPageResponse>>(
      `/api/v1/admin/question-sources/subjects/${slug}/sources/${sourceId}/questions`,
      query
    );
    return response.data.data;
  },

  patchAdminSourceQuestion: async (payload: {
    slug: string;
    sourceId: string;
    ordinal: number;
    body: AdminPatchQuestionBody;
  }) => {
    const response = await apiService.patch<
      ApiResponse<AdminPatchQuestionResponse>,
      AdminPatchQuestionBody
    >(
      `/api/v1/admin/question-sources/subjects/${payload.slug}/sources/${payload.sourceId}/questions/${payload.ordinal}`,
      payload.body
    );
    return response.data.data;
  },

  checkQuestionInBank: async (slug: string, body: SourceQuestionUpdateInput) => {
    const response = await apiService.post<
      ApiResponse<BankCheckDuplicateResponse>,
      SourceQuestionUpdateInput
    >(`/api/v1/admin/question-sources/subjects/${slug}/bank/check-duplicate`, body);
    return response.data.data;
  },

  appendAdminSourceQuestion: async (payload: {
    slug: string;
    sourceId: string;
    body: SourceQuestionUpdateInput;
  }) => {
    const response = await apiService.post<
      ApiResponse<AdminAppendQuestionResponse>,
      SourceQuestionUpdateInput
    >(
      `/api/v1/admin/question-sources/subjects/${payload.slug}/sources/${payload.sourceId}/questions`,
      payload.body
    );
    return response.data.data;
  },

  deleteAdminSourceQuestion: async (payload: { slug: string; sourceId: string; ordinal: number }) => {
    const response = await apiService.request<ApiResponse<AdminDeleteQuestionResponse>>({
      method: "DELETE",
      url: `/api/v1/admin/question-sources/subjects/${payload.slug}/sources/${payload.sourceId}/questions/${payload.ordinal}`,
    });
    return response.data.data;
  },
};
