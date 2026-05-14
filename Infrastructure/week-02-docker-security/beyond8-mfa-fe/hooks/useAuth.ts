"use client";

import { toast } from "sonner";
import { useCallback, useEffect, useRef } from "react";
import { deleteCookie, setCookie } from "cookies-next";
import { hasAdminRole } from "@/lib/types/roles";
import { fetchAuth } from "@/lib/api/services/fetchAuth";
import { apiService } from "@/lib/api/core";
import { getAuthCookieConfig } from "@/utils/cookieConfig";
import {
  decodeTokenWithExpiry,
  dismissError as dismissAuthError,
  logout as logoutAuth,
  setError,
  setLoading,
  setTokens,
} from "@/lib/redux/authSlice";
import { useAppDispatch, useAppSelector } from "@/lib/redux/hooks";
import { useRouter } from "@/lib/navigation";

export function useAuth() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const { user, token, isAuthenticated, isLoading, error, refreshToken } = useAppSelector(
    (state) => state.auth
  );

  const doLogout = useCallback(() => {
    dispatch(logoutAuth());
    apiService.setAuthToken(null);
    deleteCookie("auth_token", getAuthCookieConfig());
    window.dispatchEvent(new Event("logout"));
    router.push("/login");
  }, [dispatch, router]);

  const refreshAccessToken = useCallback(async () => {
    if (!refreshToken) {
      doLogout();
      return;
    }

    try {
      const response = await fetchAuth.refreshToken(refreshToken);
      const data = response.data;
      dispatch(setTokens({ token: data.access_token, refreshToken: data.refresh_token || refreshToken }));
      apiService.setAuthToken(data.access_token);
      setCookie("auth_token", data.access_token, getAuthCookieConfig());
    } catch {
      doLogout();
    }
  }, [dispatch, doLogout, refreshToken]);

  useEffect(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }

    if (!token) return;

    const decoded = decodeTokenWithExpiry(token);
    if (!decoded?.exp || !refreshToken) return;

    const refreshTime = decoded.exp * 1000 - Date.now() - 2 * 60 * 1000;
    if (refreshTime <= 0) {
      void refreshAccessToken();
      return;
    }

    refreshTimerRef.current = setTimeout(() => {
      void refreshAccessToken();
    }, refreshTime);

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, [token, refreshToken, refreshAccessToken]);

  const login = async (email: string, password?: string) => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    try {
      const response = await fetchAuth.login({ email, password });
      const data = response.data;
      dispatch(setTokens({ token: data.access_token, refreshToken: data.refresh_token }));
      apiService.setAuthToken(data.access_token);
      setCookie("auth_token", data.access_token, getAuthCookieConfig());
      dispatch(setLoading(false));

      const currentUser = decodeTokenWithExpiry(data.access_token);
      const roles = currentUser?.role ?? [];
      if (hasAdminRole(roles)) {
        router.push("/admin");
        return true;
      }

      doLogout();
      toast.error("Tài khoản không có quyền admin để truy cập hệ thống này");
      return false;
    } catch (error) {
      const nextError =
        error && typeof error === "object" && "message" in error
          ? String(error.message)
          : "Login failed";
      dispatch(setError(nextError));
      dispatch(setLoading(false));
      return false;
    }
  };

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    error,
    login,
    doLogout,
    dismissError: () => dispatch(dismissAuthError()),
  };
}
