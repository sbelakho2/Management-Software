import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';

function normalizeApiRoot(rawUrl: string): string {
  const trimmed = rawUrl.replace(/\/+$/, '');
  if (trimmed.endsWith('/api/v1')) {
    return trimmed.slice(0, -'/api/v1'.length);
  }
  if (trimmed.endsWith('/api')) {
    return trimmed.slice(0, -'/api'.length);
  }
  return trimmed;
}

const DEFAULT_PUBLIC_API_URL = 'http://localhost:8000';
const API_ROOT = normalizeApiRoot(
  typeof window === 'undefined'
    ? (process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || DEFAULT_PUBLIC_API_URL)
    : (process.env.NEXT_PUBLIC_API_URL || DEFAULT_PUBLIC_API_URL)
);

export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
  status?: number;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
  };
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/**
 * Extended config with abort signal support
 */
export interface ApiRequestConfig extends AxiosRequestConfig {
  signal?: AbortSignal;
}

/**
 * Create an AbortController with optional timeout
 */
export function createAbortController(timeoutMs?: number): AbortController {
  const controller = new AbortController();
  if (timeoutMs) {
    setTimeout(() => controller.abort(), timeoutMs);
  }
  return controller;
}

/**
 * Check if an error is an abort error
 */
export function isAbortError(error: unknown): boolean {
  return axios.isCancel(error) || (error instanceof Error && error.name === 'AbortError');
}

class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private pendingRequests: Map<string, AbortController> = new Map();

  constructor() {
    this.client = axios.create({
      baseURL: `${API_ROOT}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Load token immediately
    this.loadToken();

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<ApiError>) => {
        // Don't retry aborted requests
        if (isAbortError(error)) {
          return Promise.reject({ message: 'Request cancelled', code: 'CANCELLED' });
        }

        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        // Handle 401 - token expired
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await this.refreshToken();
            return this.client(originalRequest);
          } catch {
            this.clearToken();
            // Clear all pending requests on auth failure
            this.cancelAllRequests();
            if (typeof window !== 'undefined') {
              window.location.href = '/login';
            }
          }
        }

        return Promise.reject(this.formatError(error));
      }
    );
  }

  private formatError(error: AxiosError<ApiError>): ApiError {
    if (error.response?.data) {
      return {
        message: error.response.data.message || 'An error occurred',
        code: error.response.data.code,
        details: error.response.data.details,
        status: error.response.status,
      };
    }
    return {
      message: error.message || 'Network error',
      code: 'NETWORK_ERROR',
    };
  }

  /**
   * Cancel all pending requests
   */
  cancelAllRequests(): void {
    this.pendingRequests.forEach((controller) => {
      controller.abort();
    });
    this.pendingRequests.clear();
  }

  /**
   * Cancel a specific request by key
   */
  cancelRequest(key: string): void {
    const controller = this.pendingRequests.get(key);
    if (controller) {
      controller.abort();
      this.pendingRequests.delete(key);
    }
  }

  /**
   * Create a cancellable request
   */
  createCancellableRequest(key: string): AbortController {
    // Cancel any existing request with this key
    this.cancelRequest(key);
    const controller = new AbortController();
    this.pendingRequests.set(key, controller);
    return controller;
  }

  setToken(token: string) {
    this.accessToken = token;
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('access_token', token);
      } catch {
        // localStorage not available (SSR or private browsing)
      }
    }
  }

  clearToken() {
    this.accessToken = null;
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      } catch {
        // localStorage not available
      }
    }
  }

  loadToken() {
    if (typeof window !== 'undefined') {
      try {
        const token = localStorage.getItem('access_token');
        if (token) {
          this.accessToken = token;
        }
      } catch {
        // localStorage not available
      }
    }
  }

  getToken(): string | null {
    return this.accessToken;
  }

  async refreshToken(): Promise<void> {
    let refreshToken: string | null = null;
    
    if (typeof window !== 'undefined') {
      try {
        refreshToken = localStorage.getItem('refresh_token');
      } catch {
        // localStorage not available
      }
    }

    if (!refreshToken) {
      throw new Error('No refresh token');
    }

    const response = await axios.post(`${API_ROOT}/api/v1/auth/refresh`, {
      refresh_token: refreshToken,
    });

    this.setToken(response.data.access_token);
    if (response.data.refresh_token && typeof window !== 'undefined') {
      try {
        localStorage.setItem('refresh_token', response.data.refresh_token);
      } catch {
        // localStorage not available
      }
    }
  }

  // Response type for wrapped API responses
  private unwrapResponse<T>(data: unknown): T {
    if (data && typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { success: boolean; data: T }).data;
    }
    return data as T;
  }

  // HTTP methods with AbortSignal support
  async get<T>(url: string, config?: ApiRequestConfig): Promise<T> {
    const response = await this.client.get<T | { success: boolean; data: T }>(url, config);
    return this.unwrapResponse<T>(response.data);
  }

  async post<T>(url: string, data?: unknown, config?: ApiRequestConfig): Promise<T> {
    const response = await this.client.post<T | { success: boolean; data: T }>(url, data, config);
    return this.unwrapResponse<T>(response.data);
  }

  async put<T>(url: string, data?: unknown, config?: ApiRequestConfig): Promise<T> {
    const response = await this.client.put<T | { success: boolean; data: T }>(url, data, config);
    return this.unwrapResponse<T>(response.data);
  }

  async patch<T>(url: string, data?: unknown, config?: ApiRequestConfig): Promise<T> {
    const response = await this.client.patch<T | { success: boolean; data: T }>(url, data, config);
    return this.unwrapResponse<T>(response.data);
  }

  async delete<T>(url: string, config?: ApiRequestConfig): Promise<T> {
    const response = await this.client.delete<T | { success: boolean; data: T }>(url, config);
    return this.unwrapResponse<T>(response.data);
  }
}

export const apiClient = new ApiClient();

// Export API_ROOT for use in other modules
export { API_ROOT };

// Initialize token on load
if (typeof window !== 'undefined') {
  apiClient.loadToken();
}
