import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';

/**
 * Circuit Breaker States
 */
enum CircuitState {
  CLOSED = 'CLOSED',      // Normal operation - requests flow through
  OPEN = 'OPEN',          // Circuit tripped - requests fail fast
  HALF_OPEN = 'HALF_OPEN' // Testing if service recovered
}

/**
 * Circuit Breaker Configuration
 */
interface CircuitBreakerConfig {
  failureThreshold: number;      // Number of failures before opening circuit
  successThreshold: number;      // Successes needed in half-open to close
  timeout: number;               // Time in ms before trying half-open
  monitoringWindow: number;      // Time window for failure counting (ms)
}

/**
 * Circuit Breaker Implementation
 * 
 * Prevents cascading failures by failing fast when the backend is unhealthy.
 * This protects both the user experience (fast failure feedback) and the
 * backend (reduces load during recovery).
 */
class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failures: number[] = [];  // Timestamps of failures
  private successes: number = 0;
  private lastFailureTime: number = 0;
  private config: CircuitBreakerConfig;

  constructor(config?: Partial<CircuitBreakerConfig>) {
    this.config = {
      failureThreshold: 5,        // 5 failures
      successThreshold: 2,        // 2 successes to close
      timeout: 30000,             // 30 seconds before half-open
      monitoringWindow: 60000,    // 1 minute window
      ...config
    };
  }

  /**
   * Check if request should be allowed
   */
  canRequest(): boolean {
    this.cleanupOldFailures();

    switch (this.state) {
      case CircuitState.CLOSED:
        return true;

      case CircuitState.OPEN:
        // Check if timeout has passed to try half-open
        if (Date.now() - this.lastFailureTime >= this.config.timeout) {
          this.state = CircuitState.HALF_OPEN;
          this.successes = 0;
          console.log('[CIRCUIT BREAKER] Transitioning to HALF_OPEN state');
          return true;
        }
        return false;

      case CircuitState.HALF_OPEN:
        return true;
    }
  }

  /**
   * Record a successful request
   */
  recordSuccess(): void {
    if (this.state === CircuitState.HALF_OPEN) {
      this.successes++;
      if (this.successes >= this.config.successThreshold) {
        this.state = CircuitState.CLOSED;
        this.failures = [];
        this.successes = 0;
        console.log('[CIRCUIT BREAKER] Circuit CLOSED - service recovered');
      }
    } else if (this.state === CircuitState.CLOSED) {
      // Partial healing - remove oldest failure on success
      if (this.failures.length > 0) {
        this.failures.shift();
      }
    }
  }

  /**
   * Record a failed request
   */
  recordFailure(): void {
    const now = Date.now();
    this.lastFailureTime = now;
    
    if (this.state === CircuitState.HALF_OPEN) {
      // Any failure in half-open reopens the circuit
      this.state = CircuitState.OPEN;
      console.log('[CIRCUIT BREAKER] Circuit OPEN - failure during recovery');
      return;
    }

    // Add failure timestamp
    this.failures.push(now);
    this.cleanupOldFailures();

    // Check if we should open the circuit
    if (this.failures.length >= this.config.failureThreshold) {
      this.state = CircuitState.OPEN;
      console.log('[CIRCUIT BREAKER] Circuit OPEN - failure threshold reached', {
        failures: this.failures.length,
        threshold: this.config.failureThreshold
      });
    }
  }

  /**
   * Remove failures outside the monitoring window
   */
  private cleanupOldFailures(): void {
    const cutoff = Date.now() - this.config.monitoringWindow;
    this.failures = this.failures.filter(t => t > cutoff);
  }

  /**
   * Get current circuit state
   */
  getState(): { state: CircuitState; failures: number; isOpen: boolean } {
    return {
      state: this.state,
      failures: this.failures.length,
      isOpen: this.state === CircuitState.OPEN
    };
  }

  /**
   * Force close the circuit (for recovery/admin purposes)
   */
  forceClose(): void {
    this.state = CircuitState.CLOSED;
    this.failures = [];
    this.successes = 0;
    console.log('[CIRCUIT BREAKER] Circuit force-closed');
  }

  /**
   * Determine if error should trip circuit
   * Only server errors (5xx) and network errors should count
   */
  shouldCountAsFailure(error: AxiosError): boolean {
    // Network errors always count
    if (!error.response) {
      return true;
    }

    const status = error.response.status;
    
    // Server errors (5xx) count
    if (status >= 500 && status < 600) {
      return true;
    }

    // Rate limiting (429) counts but with less weight
    if (status === 429) {
      return true;
    }

    // Client errors (4xx) don't count - they're not service issues
    return false;
  }
}

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
  private circuitBreaker: CircuitBreaker;
  // Deduplication: coalesce identical in-flight GET requests
  private inflightGets: Map<string, Promise<unknown>> = new Map();
  // Limit pending request map size to prevent memory leaks
  private static readonly MAX_PENDING_REQUESTS = 200;

  constructor() {
    console.log('[API CLIENT] Initializing with API_ROOT:', API_ROOT);
    
    // Initialize circuit breaker
    this.circuitBreaker = new CircuitBreaker({
      failureThreshold: 5,
      successThreshold: 2,
      timeout: 30000,
      monitoringWindow: 60000
    });
    
    this.client = axios.create({
      baseURL: `${API_ROOT}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Load token immediately
    this.loadToken();

    // Request interceptor - includes circuit breaker check
    this.client.interceptors.request.use(
      (config) => {
        // Check circuit breaker before making request
        if (!this.circuitBreaker.canRequest()) {
          const circuitError = new Error('Service temporarily unavailable - circuit breaker open');
          (circuitError as Error & { code: string }).code = 'CIRCUIT_OPEN';
          return Promise.reject(circuitError);
        }
        
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - updates circuit breaker state
    this.client.interceptors.response.use(
      (response) => {
        // Successful response - record success
        this.circuitBreaker.recordSuccess();
        return response;
      },
      async (error: AxiosError<ApiError>) => {
        // Don't count aborted requests as failures
        if (isAbortError(error)) {
          return Promise.reject({ message: 'Request cancelled', code: 'CANCELLED' });
        }

        // Check if this error should count towards circuit breaker
        if (this.circuitBreaker.shouldCountAsFailure(error)) {
          this.circuitBreaker.recordFailure();
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

  /**
   * Get the current circuit breaker state
   */
  getCircuitState(): { state: CircuitState; failures: number; isOpen: boolean } {
    return this.circuitBreaker.getState();
  }

  /**
   * Force reset the circuit breaker (admin/debug use)
   */
  resetCircuitBreaker(): void {
    this.circuitBreaker.forceClose();
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
    // Guard against unbounded map growth (e.g. component re-render storms)
    if (this.pendingRequests.size >= ApiClient.MAX_PENDING_REQUESTS) {
      // Evict oldest entries
      const keys = Array.from(this.pendingRequests.keys());
      for (let i = 0; i < keys.length / 2; i++) {
        const oldKey = keys[i];
        const oldController = this.pendingRequests.get(oldKey);
        if (oldController) oldController.abort();
        this.pendingRequests.delete(oldKey);
      }
    }
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
    // Deduplicate identical in-flight GET requests to avoid redundant network calls.
    // This is critical for React Strict Mode and concurrent renders that may fire
    // the same query multiple times simultaneously.
    const cacheKey = `${url}|${JSON.stringify(config?.params ?? '')}`;
    const inflight = this.inflightGets.get(cacheKey);
    if (inflight) {
      return inflight as Promise<T>;
    }
    const promise = this.client
      .get<T | { success: boolean; data: T }>(url, config)
      .then((response) => this.unwrapResponse<T>(response.data))
      .finally(() => {
        this.inflightGets.delete(cacheKey);
      });
    this.inflightGets.set(cacheKey, promise);
    return promise;
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
