"use client";

import { isAxiosError } from "axios";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  fetchAdmin,
  type AdminUserItem,
  type AdminUsersListResponse,
  type BlockUserPayload,
} from "@/lib/api/services/fetchAdmin";

export const adminKeys = {
  all: ["admin"] as const,
  stats: () => [...adminKeys.all, "stats"] as const,
  users: (params: { search?: string }) => [...adminKeys.all, "users", params] as const,
  user: (userId: string) => [...adminKeys.all, "user", userId] as const,
  history: () => [...adminKeys.all, "history"] as const,
};

// Default staleTime of 5 minutes to prevent aggressive re-fetching
// Default gcTime of 10 minutes to keep data in cache
const DEFAULT_STALE_TIME = 5 * 60 * 1000;
const DEFAULT_GC_TIME = 10 * 60 * 1000;
const USERS_QUERY_PREFIX = [...adminKeys.all, "users"] as const;

function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

function extractApiErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const payload = error.response?.data as
      | { message?: string; error?: string; data?: { message?: string } }
      | undefined;
    const message =
      payload?.message || payload?.error || payload?.data?.message || error.message || fallback;
    const status = error.response?.status;
    return status ? `[${status}] ${message}` : message;
  }
  if (error instanceof Error && error.message.trim()) return error.message;
  return fallback;
}

// --- Queries ---

export function useAdminStats() {
  return useQuery({
    queryKey: adminKeys.stats(),
    queryFn: () => fetchAdmin.getStats(),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
  });
}

export function useAdminUsers(params: { search?: string }) {
  return useQuery({
    queryKey: adminKeys.users(params),
    queryFn: () => fetchAdmin.getUsers({ offset: 0, limit: 100, search: params.search }),
    placeholderData: keepPreviousData,
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
  });
}

export function useAdminHistory() {
  return useQuery({
    queryKey: adminKeys.history(),
    queryFn: () => fetchAdmin.getHistory(),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
  });
}

export function useAdminUser(userId?: string) {
  return useQuery({
    queryKey: adminKeys.user(userId || ""),
    queryFn: async () => {
      if (!userId) throw new Error("Missing user id");
      return fetchAdmin.getUserById(userId);
    },
    enabled: Boolean(userId),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
  });
}

// --- Helpers ---

function updateUsersCache(queryClient: ReturnType<typeof useQueryClient>, updatedUser: AdminUserItem) {
  // Keep every users cache variant in sync for immediate UI feedback.
  queryClient.setQueriesData<AdminUsersListResponse | undefined>(
    { queryKey: USERS_QUERY_PREFIX },
    (oldData) => {
      if (!oldData || !oldData.users) return oldData;
      return {
        ...oldData,
        users: oldData.users.map((u) => (u.id === updatedUser.id ? { ...u, ...updatedUser } : u)),
      };
    }
  );
}

// --- Mutations ---

export function useGenerateOtp() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (targetEmail: string) => {
      const normalizedTargetEmail = normalizeEmail(targetEmail);
      if (!normalizedTargetEmail) {
        throw new Error("Email user không được để trống");
      }
      return fetchAdmin.generateOtp(normalizedTargetEmail);
    },
    onSuccess: (data) => {
      toast.success(`Đã lấy OTP cho ${data.target_email}: ${data.otp}`);
      
      // Update the user's last_generated_otp in the cache
      queryClient.setQueriesData<AdminUsersListResponse | undefined>(
        { queryKey: USERS_QUERY_PREFIX },
        (oldData) => {
          if (!oldData || !oldData.users) return oldData;
          return {
            ...oldData,
            users: oldData.users.map((u) =>
              u.email.toLowerCase() === data.target_email.toLowerCase()
                ? { ...u, last_generated_otp: data.otp }
                : u
            ),
          };
        }
      );
      
      // Still invalidate to be safe, but the UI has already updated
      void queryClient.invalidateQueries({ queryKey: USERS_QUERY_PREFIX });
    },
    onError: (error: unknown) => {
      console.error(error);
      toast.error(extractApiErrorMessage(error, "Không thể lấy OTP cho user này"));
    },
  });
}

export function useGenerateOtpByUserId() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const userDetail = await fetchAdmin.getUserById(userId);
      return fetchAdmin.generateOtp(userDetail.user.email);
    },
    onSuccess: (data, userId) => {
      toast.success(`Đã lấy OTP cho ${data.target_email}: ${data.otp}`);
      void queryClient.invalidateQueries({ queryKey: USERS_QUERY_PREFIX });
      void queryClient.invalidateQueries({ queryKey: adminKeys.user(userId), exact: true });
    },
    onError: (error: unknown) => {
      console.error(error);
      toast.error(extractApiErrorMessage(error, "Không thể lấy OTP cho user này"));
    },
  });
}

export function useDeleteUserPermanently() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => fetchAdmin.deleteUserPermanently(userId),
    onSuccess: (_, userId) => {
      toast.success("Đã xóa người dùng vĩnh viễn");

      queryClient.setQueriesData<AdminUsersListResponse | undefined>(
        { queryKey: USERS_QUERY_PREFIX },
        (oldData) => {
          if (!oldData || !oldData.users) return oldData;
          return {
            ...oldData,
            total_users: Math.max(0, oldData.total_users - 1),
            users: oldData.users.filter((u) => u.id !== userId),
          };
        }
      );

      queryClient.removeQueries({ queryKey: adminKeys.user(userId), exact: true });
      void queryClient.invalidateQueries({ queryKey: USERS_QUERY_PREFIX });
      void queryClient.invalidateQueries({ queryKey: adminKeys.stats() });
      void queryClient.invalidateQueries({ queryKey: adminKeys.history() });
    },
    onError: (error: unknown) => {
      console.error(error);
      toast.error(extractApiErrorMessage(error, "Xóa người dùng thất bại"));
    },
  });
}

export function useBlockUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, payload }: { userId: string; payload: BlockUserPayload }) =>
      fetchAdmin.blockUser(userId, payload),
    onSuccess: (data) => {
      toast.success(`Đã khóa ${data.email}`);
      updateUsersCache(queryClient, data);
      void queryClient.invalidateQueries({ queryKey: adminKeys.stats() });
      void queryClient.invalidateQueries({ queryKey: adminKeys.user(data.id) });
    },
    onError: (error: unknown) => {
      console.error(error);
      toast.error("Thao tác khóa thất bại");
    },
  });
}

export function useUnblockUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => fetchAdmin.unblockUser(userId),
    onSuccess: (data) => {
      toast.success(`Đã mở khóa ${data.email}`);
      updateUsersCache(queryClient, data);
      void queryClient.invalidateQueries({ queryKey: adminKeys.stats() });
      void queryClient.invalidateQueries({ queryKey: adminKeys.user(data.id) });
    },
    onError: (error: unknown) => {
      console.error(error);
      toast.error("Thao tác mở khóa thất bại");
    },
  });
}

export function useClearVerifiedOtpKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId }: { userId: string; search?: string }) => fetchAdmin.clearVerifiedOtpKey(userId),
    onSuccess: (data, variables) => {
      toast.success(`Đã xóa key đã verify của ${data.email}. User cần verify key mới để mở khóa lại.`);
      updateUsersCache(queryClient, data);
      void queryClient.invalidateQueries({ queryKey: adminKeys.stats() });
      void queryClient.invalidateQueries({
        queryKey: adminKeys.users({ search: variables.search }),
        exact: true,
      });
      void queryClient.invalidateQueries({ queryKey: adminKeys.user(data.id) });
    },
    onError: (error: unknown) => {
      console.error(error);
      toast.error("Xóa OTP key thất bại");
    },
  });
}
