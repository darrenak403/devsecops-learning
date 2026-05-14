import apiService from "../core";
import type { ApiResponse } from "@/types/api";

export interface AdminStatsResponse {
  verified_users: number;
  total_key_purchases: number;
  total_successful_verifications: number;
}

export interface AdminUserItem {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  course_access_active: boolean;
  course_access_version: number;
  course_access_verified_at: string | null;
  course_access_revoked_at: string | null;
  blocked_at: string | null;
  blocked_reason: string | null;
  blocked_by_user_id: string | null;
  last_generated_otp: string | null;
  created_at: string;
}

export interface AdminUsersListResponse {
  total_users: number;
  offset: number;
  limit: number;
  users: AdminUserItem[];
}

export interface AdminHistoryItem {
  user_id: string;
  email: string;
  verification_count: number;
  last_verified_at: string | null;
}

export interface AdminHistoryResponse {
  total_users: number;
  items: AdminHistoryItem[];
}

export interface AdminUserDetailResponse {
  user: AdminUserItem;
  otp_verification_history: AdminHistoryItem | null;
}

export interface GenerateOtpResponse {
  otp: string;
  expires_in: number | null;
  version: number;
  target_email: string;
}

export interface BlockUserPayload {
  reason?: string | null;
}

function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

export const fetchAdmin = {
  getUsers: async (params: { offset?: number; limit?: number; search?: string }) => {
    const searchEmail = params.search?.trim();
    const endpoint = searchEmail ? "/api/users/by-email" : "/api/users";
    const queryParams = searchEmail
      ? { offset: params.offset, limit: params.limit, email: searchEmail }
      : params;

    const response = await apiService.get<ApiResponse<AdminUsersListResponse>>(
      endpoint,
      queryParams
    );
    return response.data.data;
  },

  getUserById: async (userId: string) => {
    const response = await apiService.get<ApiResponse<AdminUserDetailResponse>>(
      `/api/users/${userId}`
    );
    return response.data.data;
  },

  getStats: async () => {
    const response = await apiService.get<ApiResponse<AdminStatsResponse>>(
      "/api/stats/otp-verifications"
    );
    return response.data.data;
  },

  getHistory: async (userId?: string) => {
    const response = await apiService.get<ApiResponse<AdminHistoryResponse>>(
      "/api/stats/otp-verifications/history",
      userId ? { user_id: userId } : undefined
    );
    return response.data.data;
  },

  generateOtp: async (targetEmail: string) => {
    const normalizedTargetEmail = normalizeEmail(targetEmail);
    if (!normalizedTargetEmail) {
      throw new Error("Email user không được để trống");
    }
    const response = await apiService.get<ApiResponse<GenerateOtpResponse>>("/api/otp/generate", {
      target_email: normalizedTargetEmail,
    });
    return response.data.data;
  },

  deleteUserPermanently: async (userId: string) => {
    const response = await apiService.request<ApiResponse<null>>({
      method: "DELETE",
      url: `/api/users/${userId}`,
      headers: {
        "X-Confirm-Delete": "permanent",
      },
    });
    return response.data.data;
  },

  blockUser: async (userId: string, payload: BlockUserPayload = {}) => {
    const response = await apiService.patch<ApiResponse<AdminUserItem>, BlockUserPayload>(
      `/api/users/${userId}/block`,
      payload
    );
    return response.data.data;
  },

  unblockUser: async (userId: string) => {
    const response = await apiService.patch<ApiResponse<AdminUserItem>, Record<string, never>>(
      `/api/users/${userId}/unblock`,
      {}
    );
    return response.data.data;
  },

  clearVerifiedOtpKey: async (userId: string) => {
    const response = await apiService.patch<ApiResponse<AdminUserItem>, Record<string, never>>(
      `/api/users/${userId}/otp-verified-key/clear`,
      {}
    );
    return response.data.data;
  },
};
