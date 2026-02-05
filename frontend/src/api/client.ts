import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';

/**
 * Safely normalize an API root URL.
 * 
 * Handles various input formats:
 * - "http://localhost:8000" -> "http://localhost:8000"
 * - "http://localhost:8000/" -> "http://localhost:8000"
 * - "http://localhost:8000/api/v1" -> "http://localhost:8000"
 * - "http://localhost:8000/api/v1/" -> "http://localhost:8000"
 * - "http://localhost:8000/api" -> "http://localhost:8000"
 * - "" or undefined -> falls back to default
 */
function normalizeApiRoot(rawUrl: string | undefined): string {
  if (!rawUrl || typeof rawUrl !== 'string') {
    return '';
  }
  
  // Remove trailing slashes
  let trimmed = rawUrl.replace(/\/+$/, '');
  
  // Remove /api/v1 suffix if present
  if (trimmed.endsWith('/api/v1')) {
    trimmed = trimmed.slice(0, -'/api/v1'.length);
  }
  // Remove /api suffix if present (but not if it's part of a longer path)
  else if (trimmed.endsWith('/api')) {
    trimmed = trimmed.slice(0, -'/api'.length);
  }
  
  // Final cleanup of trailing slashes
  return trimmed.replace(/\/+$/, '');
}

/**
 * Determine the API root URL with proper fallback chain.
 * 
 * Priority:
 * 1. Server-side: API_INTERNAL_URL (for SSR/internal communication)
 * 2. Client-side: NEXT_PUBLIC_API_URL (from environment)
 * 3. Fallback: http://localhost:8000
 * 
 * SECURITY: In production, ensure NEXT_PUBLIC_API_URL uses HTTPS to avoid
 * mixed content warnings when the frontend is served over HTTPS.
 */
function getApiRoot(): string {
  const DEFAULT_PUBLIC_API_URL = 'http://localhost:8000';
  
  const isServer = typeof window === 'undefined';
  
  let rawUrl: string | undefined;
  
  if (isServer) {
    // Server-side rendering: prefer internal URL for service-to-service calls
    rawUrl = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL;
  } else {
    // Client-side: use public URL only
    rawUrl = process.env.NEXT_PUBLIC_API_URL;
  }
  
  const normalized = normalizeApiRoot(rawUrl);
  
  // Return normalized URL or default
  return normalized || DEFAULT_PUBLIC_API_URL;
}

const API_ROOT = getApiRoot();

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
  private refreshPromise: Promise<void> | null = null;

  constructor() {
    console.log('[API CLIENT] Initializing with API_ROOT:', API_ROOT);
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
        const requestUrl = originalRequest?.url || '';
        const isAuthEndpoint = requestUrl.includes('/auth/login') || requestUrl.includes('/auth/register') || requestUrl.includes('/auth/refresh');

        // Handle 401 - token expired
        if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
          originalRequest._retry = true;

          try {
            await this.refreshToken();
            return this.client(originalRequest);
          } catch (refreshError) {
            this.clearToken();
            // Clear all pending requests on auth failure
            this.cancelAllRequests();
            // Only redirect if not already on an auth page
            if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
              window.location.href = '/login';
            }
            // Reject the promise so callers know the request failed
            return Promise.reject({ message: 'Session expired', code: 'AUTH_EXPIRED' });
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
    if (this.refreshPromise) {
      return this.refreshPromise;
    }
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

    this.refreshPromise = axios
      .post(`${API_ROOT}/api/v1/auth/refresh`, {
        refresh_token: refreshToken,
      })
      .then((response) => {
        this.setToken(response.data.access_token);
        if (response.data.refresh_token && typeof window !== 'undefined') {
          try {
            localStorage.setItem('refresh_token', response.data.refresh_token);
          } catch {
            // localStorage not available
          }
        }
      })
      .finally(() => {
        this.refreshPromise = null;
      });

    return this.refreshPromise;
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
