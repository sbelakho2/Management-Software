import { apiClient, type PaginationParams } from './client';
import type {
  Customer,
  CustomerType,
  Contact,
  Status,
  PaginatedResponse,
} from '@/types';

// ============================================================================
// Account API (Customers, Suppliers, Prospects)
// ============================================================================

export interface AccountListParams extends PaginationParams {
  status?: string;
  account_type?: string;
  industry?: string;
  search?: string;
  country?: string;
  city?: string;
  tier?: string;
  parent_id?: string;
  sort?: string;
}

export interface CreateAccountData {
  name: string;
  legal_name?: string;
  account_type?: string;
  status?: string;
  tier?: string;
  industry?: string;
  sub_industry?: string;
  website?: string;
  phone?: string;
  email?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  tax_id?: string;
  registration_number?: string;
  employees_count?: number;
  annual_revenue?: number;
  revenue_currency?: string;
  description?: string;
  internal_notes?: string;
  custom_fields?: Record<string, any>;
  tags?: string[];
  parent_id?: string;
}

export interface UpdateAccountData extends Partial<CreateAccountData> {}

export interface AccountStats {
  total_accounts: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  by_tier: Record<string, number>;
  by_country: Record<string, number>;
  new_this_month: number;
  active_customers: number;
}

export const accountApi = {
  /**
   * List accounts with pagination and filters
   */
  async list(params?: AccountListParams): Promise<PaginatedResponse<Customer>> {
    return apiClient.get('/accounts', { params });
  },

  /**
   * Get an account by ID
   */
  async get(id: string): Promise<Customer> {
    const response = await apiClient.get<{ data: Customer }>(`/accounts/${id}`);
    return response.data;
  },

  /**
   * Create a new account
   */
  async create(data: CreateAccountData): Promise<Customer> {
    const response = await apiClient.post<{ data: Customer }>('/accounts', data);
    return response.data;
  },

  /**
   * Update an account
   */
  async update(id: string, data: UpdateAccountData): Promise<Customer> {
    const response = await apiClient.patch<{ data: Customer }>(`/accounts/${id}`, data);
    return response.data;
  },

  /**
   * Delete an account
   */
  async delete(id: string, hardDelete: boolean = false): Promise<void> {
    return apiClient.delete(`/accounts/${id}`, { params: { hard_delete: hardDelete } });
  },

  /**
   * Restore a soft-deleted account
   */
  async restore(id: string): Promise<Customer> {
    const response = await apiClient.post<{ data: Customer }>(`/accounts/${id}/restore`);
    return response.data;
  },

  /**
   * Get account statistics
   */
  async getGlobalStats(): Promise<AccountStats> {
    const response = await apiClient.get<{ data: AccountStats }>('/accounts/stats');
    return response.data;
  },

  /**
   * List subsidiaries of an account
   */
  async listSubsidiaries(id: string, params?: PaginationParams): Promise<PaginatedResponse<Customer>> {
    return apiClient.get(`/accounts/${id}/subsidiaries`, { params });
  },

  /**
   * Search accounts
   */
  async search(query: string, limit?: number): Promise<Customer[]> {
    const response = await accountApi.list({ search: query, limit } as any);
    return response.items;
  },
};
