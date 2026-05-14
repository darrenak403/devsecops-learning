import type { ApiResponse } from "@/types/api";
import apiService from "../core";

export interface LoginRequest {
  email: string;
  password?: string;
}

export interface LoginTokenPayload {
  access_token: string;
  refresh_token?: string;
}

export const fetchAuth = {
  login: async (payload: LoginRequest) => {
    const response = await apiService.post<ApiResponse<LoginTokenPayload>, LoginRequest>(
      "/api/auth/login",
      payload
    );
    return response.data;
  },

  refreshToken: async (refreshToken: string) => {
    const response = await apiService.post<ApiResponse<LoginTokenPayload>, { refresh_token: string }>(
      "/api/auth/refresh",
      { refresh_token: refreshToken }
    );
    return response.data;
  },

  logout: async () => {
    const response = await apiService.post<ApiResponse<null>, Record<string, never>>(
      "/api/v1/auth/logout",
      {}
    );
    return response.data;
  }
};
