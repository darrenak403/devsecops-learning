export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  code: number;
  metadata?: unknown;
}

export interface ApiError {
  code?: number;
  message: string;
  success: boolean;
  data?: unknown;
}
