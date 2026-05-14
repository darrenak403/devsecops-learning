/* eslint-disable @typescript-eslint/no-explicit-any */
import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import { deleteCookie } from "cookies-next";
import { getAuthCookieConfig } from "@/utils/cookieConfig";

type AuthBridge = {
  getRefreshToken: () => string | null;
  onRefreshSuccess: (payload: { token: string; refreshToken: string }) => void;
  onAuthFailure: () => void;
};

let authBridge: AuthBridge | null = null;

export function configureApiAuthBridge(bridge: AuthBridge) {
  authBridge = bridge;
}

class ApiService {
  private client: AxiosInstance;
  private authToken: string | null = null;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (token: string) => void;
    reject: (error: any) => void;
  }> = [];

  constructor(baseURL: string, timeout = 600000) {
    this.client = axios.create({
      baseURL,
      timeout,
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.setupInterceptors();
  }

  private processQueue(error: any, token: string | null = null) {
    this.failedQueue.forEach((prom) => {
      if (error) {
        prom.reject(error);
      } else if (token) {
        prom.resolve(token);
      }
    });

    this.failedQueue = [];
  }

  private setupInterceptors() {
    this.client.interceptors.request.use((config) => {
      if (config.data instanceof FormData && config.headers) {
        delete config.headers["Content-Type"];
      }

      if (this.authToken && config.headers) {
        config.headers.Authorization = `Bearer ${this.authToken}`;
      }

      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<any>) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
        const status = error.response?.status;
        const requestUrl = originalRequest?.url || "";
        const isRefreshCall = requestUrl.includes("/api/auth/refresh");

        if (isRefreshCall) {
          return Promise.reject(error);
        }

        if (status !== 401 || originalRequest._retry) {
          return Promise.reject(error);
        }

        const currentRefreshToken = authBridge?.getRefreshToken() || null;
        if (!currentRefreshToken) {
          authBridge?.onAuthFailure();
          return Promise.reject(error);
        }

        if (this.isRefreshing) {
          return new Promise((resolve, reject) => {
            this.failedQueue.push({
              resolve: (token: string) => {
                if (originalRequest.headers) {
                  originalRequest.headers.Authorization = `Bearer ${token}`;
                }
                resolve(this.client(originalRequest));
              },
              reject,
            });
          });
        }

        originalRequest._retry = true;
        this.isRefreshing = true;

        try {
          const refreshResponse = await this.client.post("/api/auth/refresh", {
            refresh_token: currentRefreshToken,
          });

          const nextAccessToken = refreshResponse.data?.data?.access_token as string;
          const nextRefreshToken =
            (refreshResponse.data?.data?.refresh_token as string | undefined) ||
            currentRefreshToken;

          authBridge?.onRefreshSuccess({
            token: nextAccessToken,
            refreshToken: nextRefreshToken,
          });

          this.authToken = nextAccessToken;
          this.processQueue(null, nextAccessToken);

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`;
          }

          return this.client(originalRequest);
        } catch (refreshError) {
          this.processQueue(refreshError, null);
          deleteCookie("auth_token", getAuthCookieConfig());
          authBridge?.onAuthFailure();
          return Promise.reject(refreshError);
        } finally {
          this.isRefreshing = false;
        }
      }
    );
  }

  setAuthToken(token: string | null) {
    this.authToken = token;
  }

  async request<T>(config: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.request<T>(config);
  }

  async get<T>(url: string, params?: Record<string, any>): Promise<AxiosResponse<T>> {
    return this.request<T>({ method: "GET", url, params });
  }

  async post<T, D = any>(url: string, data?: D): Promise<AxiosResponse<T>> {
    return this.request<T>({ method: "POST", url, data });
  }

  async put<T, D = any>(url: string, data?: D): Promise<AxiosResponse<T>> {
    return this.request<T>({ method: "PUT", url, data });
  }

  async patch<T, D = any>(url: string, data?: D): Promise<AxiosResponse<T>> {
    return this.request<T>({ method: "PATCH", url, data });
  }

  async delete<T>(url: string): Promise<AxiosResponse<T>> {
    return this.request<T>({ method: "DELETE", url });
  }
}

const resolvedApiBaseUrl =
  process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.trim()
    ? process.env.NEXT_PUBLIC_API_URL.trim()
    : "";

/**
 * Do not fallback to localhost in browser builds.
 * When env is missing, use same-origin so /api rewrites/proxy can still work.
 */
const apiService = new ApiService(resolvedApiBaseUrl || "/");

export { apiService };
export default apiService;
