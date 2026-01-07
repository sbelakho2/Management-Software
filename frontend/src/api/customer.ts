import { apiClient, type PaginationParams } from './client';
import type {
  Customer,
  CustomerType,
  Contact,
  Status,
  PaginatedResponse,
} from '@/types';

// ============================================================================
// Customer API
// ============================================================================

export interface CustomerListParams extends PaginationParams {
  status?: Status;
  type?: CustomerType;
  industry?: string;
  search?: string;
  tags?: string[];
}

export interface CreateCustomerData {
  name: string;
  code?: string;
  type?: CustomerType;
  industry?: string;
  website?: string;
  phone?: string;
  email?: string;
  address?: AddressData;
  billing_address?: AddressData;
  shipping_address?: AddressData;
  tax_id?: string;
  payment_terms?: string;
  credit_limit?: number;
  notes?: string;
  tags?: string[];
}

export interface UpdateCustomerData {
  name?: string;
  code?: string;
  type?: CustomerType;
  status?: Status;
  industry?: string;
  website?: string;
  phone?: string;
  email?: string;
  address?: AddressData;
  billing_address?: AddressData;
  shipping_address?: AddressData;
  primary_contact_id?: string | null;
  tax_id?: string;
  payment_terms?: string;
  credit_limit?: number;
  notes?: string;
  tags?: string[];
}

export interface AddressData {
  street1: string;
  street2?: string;
  city: string;
  state?: string;
  postal_code: string;
  country: string;
}

export const customerApi = {
  /**
   * List customers with pagination and filters
   */
  async list(params?: CustomerListParams): Promise<PaginatedResponse<Customer>> {
    return apiClient.get('/customers', { params });
  },

  /**
   * Get a customer by ID
   */
  async get(id: string): Promise<Customer> {
    return apiClient.get(`/customers/${id}`);
  },

  /**
   * Create a new customer
   */
  async create(data: CreateCustomerData): Promise<Customer> {
    return apiClient.post('/customers', data);
  },

  /**
   * Update a customer
   */
  async update(id: string, data: UpdateCustomerData): Promise<Customer> {
    return apiClient.patch(`/customers/${id}`, data);
  },

  /**
   * Delete a customer
   */
  async delete(id: string): Promise<void> {
    return apiClient.delete(`/customers/${id}`);
  },

  /**
   * Activate a customer
   */
  async activate(id: string): Promise<Customer> {
    return apiClient.post(`/customers/${id}/activate`);
  },

  /**
   * Deactivate a customer
   */
  async deactivate(id: string): Promise<Customer> {
    return apiClient.post(`/customers/${id}/deactivate`);
  },

  /**
   * Get customer's RFQs
   */
  async getRFQs(id: string, params?: PaginationParams): Promise<PaginatedResponse<unknown>> {
    return apiClient.get(`/customers/${id}/rfqs`, { params });
  },

  /**
   * Get customer's quotes
   */
  async getQuotes(id: string, params?: PaginationParams): Promise<PaginatedResponse<unknown>> {
    return apiClient.get(`/customers/${id}/quotes`, { params });
  },

  /**
   * Get customer statistics
   */
  async getStats(id: string): Promise<CustomerStats> {
    return apiClient.get(`/customers/${id}/stats`);
  },

  /**
   * Get customer timeline/activity
   */
  async getTimeline(id: string, params?: PaginationParams): Promise<TimelineEvent[]> {
    return apiClient.get(`/customers/${id}/timeline`, { params });
  },

  /**
   * Search customers by name or code
   */
  async search(query: string, limit?: number): Promise<Customer[]> {
    return apiClient.get('/customers/search', { params: { q: query, limit } });
  },

  /**
   * Merge duplicate customers
   */
  async merge(sourceId: string, targetId: string): Promise<Customer> {
    return apiClient.post('/customers/merge', { source_id: sourceId, target_id: targetId });
  },

  /**
   * Export customers to CSV
   */
  async exportCsv(params?: CustomerListParams): Promise<Blob> {
    return apiClient.get('/customers/export/csv', {
      params,
      responseType: 'blob',
    });
  },

  /**
   * Import customers from CSV
   */
  async importCsv(file: File): Promise<ImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/customers/import/csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // Contacts
  contacts: {
    /**
     * List contacts for a customer
     */
    async list(customerId: string): Promise<Contact[]> {
      return apiClient.get(`/customers/${customerId}/contacts`);
    },

    /**
     * Get a contact by ID
     */
    async get(customerId: string, contactId: string): Promise<Contact> {
      return apiClient.get(`/customers/${customerId}/contacts/${contactId}`);
    },

    /**
     * Create a new contact
     */
    async create(customerId: string, data: CreateContactData): Promise<Contact> {
      return apiClient.post(`/customers/${customerId}/contacts`, data);
    },

    /**
     * Update a contact
     */
    async update(customerId: string, contactId: string, data: UpdateContactData): Promise<Contact> {
      return apiClient.patch(`/customers/${customerId}/contacts/${contactId}`, data);
    },

    /**
     * Delete a contact
     */
    async delete(customerId: string, contactId: string): Promise<void> {
      return apiClient.delete(`/customers/${customerId}/contacts/${contactId}`);
    },

    /**
     * Set a contact as primary
     */
    async setPrimary(customerId: string, contactId: string): Promise<Contact> {
      return apiClient.post(`/customers/${customerId}/contacts/${contactId}/set-primary`);
    },
  },
};

export interface CreateContactData {
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  mobile?: string;
  job_title?: string;
  department?: string;
  is_primary?: boolean;
  notes?: string;
}

export interface UpdateContactData {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  mobile?: string;
  job_title?: string;
  department?: string;
  is_primary?: boolean;
  is_active?: boolean;
  notes?: string;
}

export interface CustomerStats {
  total_rfqs: number;
  total_quotes: number;
  total_revenue: number;
  average_quote_value: number;
  win_rate: number;
  last_order_date?: string;
  lifetime_value: number;
}

export interface TimelineEvent {
  id: string;
  type: string;
  action: string;
  description: string;
  user_id?: string;
  user_name?: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface ImportResult {
  success: boolean;
  imported: number;
  failed: number;
  errors: Array<{
    row: number;
    message: string;
  }>;
}
