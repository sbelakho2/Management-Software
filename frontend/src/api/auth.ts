import { apiClient, type PaginationParams } from './client';
import type {
  AuthTokens,
  LoginCredentials,
  RegisterData,
  User,
  UserPreferences,
  UserRole,
} from '@/types';

export interface TwoFactorRequiredResponse {
  requires_2fa: true;
  message: string;
}

type BackendTokenResponse = AuthTokens;

type BackendLoginResponse = BackendTokenResponse | TwoFactorRequiredResponse;

function isTwoFactorRequiredResponse(value: unknown): value is TwoFactorRequiredResponse {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as { requires_2fa?: unknown }).requires_2fa === true
  );
}

const ROLE_PRIORITY: UserRole[] = [
  'admin',
  'ceo',
  'gm',
  'exec',
  'finance',
  'accountant',
  'hr',
  'ops',
  'quality',
  'auditor',
  'it',
  'sales',
  'purchasing',
  'sales_engineer',
  'estimator',
  'supply_chain',
  'logistics',
  'maintenance',
  'warehouse',
  'engineering',
  'supervisor',
  'team_lead',
  'operator',
  'viewer',
];

const USER_ROLE_SET = new Set<string>(ROLE_PRIORITY);

function normalizeBackendRole(raw: unknown): UserRole | null {
  if (typeof raw !== 'string') return null;
  const cleaned = raw.trim();
  if (!cleaned) return null;

  // Common backend variants / display names
  const normalized = cleaned.toLowerCase().replace(/\s+/g, '_');

  // Some deployments may include non-RBAC markers like "superuser".
  // We ignore those here and rely on explicit RBAC roles like "ceo"/"admin".
  if (normalized === 'superuser') return null;

  // Canonical aliases
  if (normalized === 'general_manager') return 'gm';
  if (normalized === 'executive') return 'exec';

  return USER_ROLE_SET.has(normalized) ? (normalized as UserRole) : null;
}

function normalizeRoles(raw: unknown): UserRole[] {
  const roles: UserRole[] = [];
  const pushRole = (value: unknown) => {
    const role = normalizeBackendRole(value);
    if (role && !roles.includes(role)) {
      roles.push(role);
    }
  };

  if (Array.isArray(raw)) {
    raw.forEach(pushRole);
    return roles;
  }

  // Defensive: occasionally roles can be a single string
  pushRole(raw);
  return roles;
}

function pickPrimaryRole(user: any, normalizedRoles: UserRole[]): UserRole {
  // Prefer any explicit primary role when present (then fall back to roles list)
  const explicit = normalizeBackendRole(user?.role);
  const roles = explicit ? [explicit, ...normalizedRoles] : normalizedRoles;

  for (const role of ROLE_PRIORITY) {
    if (roles.includes(role)) return role;
  }
  return roles[0] ?? 'viewer';
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
  async login(credentials: LoginCredentials): Promise<BackendTokenResponse> {
    const payload = {
      email: credentials.email.trim().toLowerCase(),
      password: credentials.password.trim(),
    };
    console.log('[AUTH DEBUG] Login request payload:', JSON.stringify(payload, null, 2));
    const response = await apiClient.post<BackendLoginResponse>('/auth/login', payload);

    if (isTwoFactorRequiredResponse(response)) {
      throw new Error(response.message || 'Two-factor authentication required');
    }

    apiClient.setToken(response.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('refresh_token', response.refresh_token);
    }
    return response;
  },

  /**
   * Register a new user
   */
  async register(data: RegisterData): Promise<BackendTokenResponse> {
    const response = await apiClient.post<BackendTokenResponse>('/auth/register', {
      ...data,
      email: data.email.trim().toLowerCase(),
    });
    apiClient.setToken(response.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('refresh_token', response.refresh_token);
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
    const user = await apiClient.get<any>('/users/me');
    const roles = normalizeRoles(user?.roles);

    return {
      ...user,
      role: pickPrimaryRole(user, roles),
      roles,
    };
  },

  /**
   * Update the current user's profile
   */
  async updateProfile(data: Partial<User>): Promise<User> {
    // Backend response for /users/me patch omits role/roles; re-hydrate from token.
    await apiClient.patch('/users/me', data);
    return this.getCurrentUser();
  },

  /**
   * Update the current user's preferences
   */
  async updatePreferences(preferences: Partial<UserPreferences>): Promise<User> {
    // Backend user profile update currently supports core profile fields.
    // Persisted preferences can be mapped onto supported fields as they evolve.
    await apiClient.patch('/users/me', preferences as unknown as Partial<User>);
    return this.getCurrentUser();
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
    return apiClient.post('/auth/password-reset', data);
  },

  /**
   * Reset password with token
   */
  async resetPassword(data: PasswordResetConfirm): Promise<void> {
    return apiClient.post('/auth/password-reset/confirm', data);
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
