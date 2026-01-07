import { apiClient, type PaginationParams } from './client';
import type {
  AuthTokens,
  LoginCredentials,
  RegisterData,
  User,
  UserPreferences,
} from '@/types';

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  password: string;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

export const authApi = {
  /**
   * Login with email and password
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/login', credentials);
    apiClient.setToken(response.tokens.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('refresh_token', response.tokens.refresh_token);
    }
    return response;
  },

  /**
   * Register a new user
   */
  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/register', data);
    apiClient.setToken(response.tokens.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('refresh_token', response.tokens.refresh_token);
    }
    return response;
  },

  /**
   * Logout the current user
   */
  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      apiClient.clearToken();
    }
  },

  /**
   * Get the current user's profile
   */
  async getCurrentUser(): Promise<User> {
    return apiClient.get<User>('/auth/me');
  },

  /**
   * Update the current user's profile
   */
  async updateProfile(data: Partial<User>): Promise<User> {
    return apiClient.patch<User>('/auth/me', data);
  },

  /**
   * Update the current user's preferences
   */
  async updatePreferences(preferences: Partial<UserPreferences>): Promise<User> {
    return apiClient.patch<User>('/auth/me/preferences', preferences);
  },

  /**
   * Change password
   */
  async changePassword(data: PasswordChange): Promise<void> {
    return apiClient.post('/auth/change-password', data);
  },

  /**
   * Request password reset email
   */
  async requestPasswordReset(data: PasswordResetRequest): Promise<void> {
    return apiClient.post('/auth/forgot-password', data);
  },

  /**
   * Reset password with token
   */
  async resetPassword(data: PasswordResetConfirm): Promise<void> {
    return apiClient.post('/auth/reset-password', data);
  },

  /**
   * Verify email with token
   */
  async verifyEmail(token: string): Promise<void> {
    return apiClient.post('/auth/verify-email', { token });
  },

  /**
   * Resend verification email
   */
  async resendVerificationEmail(): Promise<void> {
    return apiClient.post('/auth/resend-verification');
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    if (typeof window !== 'undefined') {
      return !!localStorage.getItem('access_token');
    }
    return false;
  },
};

export interface UsersListParams extends PaginationParams {
  role?: string;
  department?: string;
  is_active?: boolean;
  search?: string;
}

export interface CreateUserData {
  email: string;
  password: string;
  full_name: string;
  role?: string;
  department?: string;
  job_title?: string;
}

export interface UpdateUserData {
  email?: string;
  full_name?: string;
  role?: string;
  department?: string;
  job_title?: string;
  phone?: string;
  timezone?: string;
  locale?: string;
  is_active?: boolean;
}

export const usersApi = {
  /**
   * List users with pagination and filters
   */
  async list(params?: UsersListParams): Promise<{ items: User[]; total: number }> {
    return apiClient.get('/users', { params });
  },

  /**
   * Get a user by ID
   */
  async get(id: string): Promise<User> {
    return apiClient.get(`/users/${id}`);
  },

  /**
   * Create a new user
   */
  async create(data: CreateUserData): Promise<User> {
    return apiClient.post('/users', data);
  },

  /**
   * Update a user
   */
  async update(id: string, data: UpdateUserData): Promise<User> {
    return apiClient.patch(`/users/${id}`, data);
  },

  /**
   * Delete a user
   */
  async delete(id: string): Promise<void> {
    return apiClient.delete(`/users/${id}`);
  },

  /**
   * Activate a user
   */
  async activate(id: string): Promise<User> {
    return apiClient.post(`/users/${id}/activate`);
  },

  /**
   * Deactivate a user
   */
  async deactivate(id: string): Promise<User> {
    return apiClient.post(`/users/${id}/deactivate`);
  },

  /**
   * Reset a user's password (admin)
   */
  async resetPassword(id: string): Promise<void> {
    return apiClient.post(`/users/${id}/reset-password`);
  },

  /**
   * Get user's assigned tasks
   */
  async getTasks(id: string, params?: PaginationParams): Promise<{ items: unknown[]; total: number }> {
    return apiClient.get(`/users/${id}/tasks`, { params });
  },

  /**
   * Get user's activity log
   */
  async getActivity(id: string, params?: PaginationParams): Promise<{ items: unknown[]; total: number }> {
    return apiClient.get(`/users/${id}/activity`, { params });
  },
};
