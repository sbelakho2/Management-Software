import { apiClient, type PaginationParams } from './client';
import type { PaginatedResponse } from '@/types';

// ============================================================================
// Contact API
// ============================================================================

export interface ContactListParams extends PaginationParams {
  account_id?: string;
  search?: string;
  job_title?: string;
  department?: string;
  country?: string;
  email_opt_out?: boolean;
  sort?: string;
}

export interface ContactResponse {
  id: string;
  first_name: string;
  last_name: string;
  display_name: string;
  email?: string;
  phone_mobile?: string;
  phone_work?: string;
  job_title?: string;
  created_at: string;
}

export const contactApi = {
  /**
   * List contacts with pagination and filters
   */
  async list(params?: ContactListParams): Promise<PaginatedResponse<ContactResponse>> {
    return apiClient.get('/contacts', { params });
  },

  /**
   * Get a contact by ID
   */
  async get(id: string): Promise<ContactResponse> {
    return apiClient.get(`/contacts/${id}`);
  },
};
