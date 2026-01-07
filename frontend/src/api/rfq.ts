import { apiClient, type PaginationParams } from './client';
import type {
  RFQ,
  RFQLineItem,
  RFQStatus,
  Quote,
  QuoteLineItem,
  QuoteStatus,
  Priority,
  PaginatedResponse,
} from '@/types';

// ============================================================================
// RFQ API
// ============================================================================

export interface RFQListParams extends PaginationParams {
  status?: RFQStatus | RFQStatus[];
  priority?: Priority | Priority[];
  customer_id?: string;
  assigned_to?: string;
  search?: string;
  due_date_from?: string;
  due_date_to?: string;
  received_date_from?: string;
  received_date_to?: string;
  tags?: string[];
}

export interface CreateRFQData {
  customer_id: string;
  title: string;
  description?: string;
  priority?: Priority;
  due_date: string;
  received_date: string;
  estimated_value?: number;
  currency?: string;
  notes?: string;
  tags?: string[];
  line_items?: CreateRFQLineItemData[];
}

export interface UpdateRFQData {
  customer_id?: string;
  title?: string;
  description?: string;
  status?: RFQStatus;
  priority?: Priority;
  due_date?: string;
  estimated_value?: number;
  currency?: string;
  notes?: string;
  assigned_to?: string | null;
  tags?: string[];
}

export interface CreateRFQLineItemData {
  part_number: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  target_price?: number;
  notes?: string;
  specifications?: Record<string, unknown>;
}

export interface UpdateRFQLineItemData {
  part_number?: string;
  description?: string;
  quantity?: number;
  unit_of_measure?: string;
  target_price?: number;
  notes?: string;
  specifications?: Record<string, unknown>;
}

export const rfqApi = {
  /**
   * List RFQs with pagination and filters
   */
  async list(params?: RFQListParams): Promise<PaginatedResponse<RFQ>> {
    return apiClient.get('/rfqs', { params });
  },

  /**
   * Get an RFQ by ID
   */
  async get(id: string): Promise<RFQ> {
    return apiClient.get(`/rfqs/${id}`);
  },

  /**
   * Create a new RFQ
   */
  async create(data: CreateRFQData): Promise<RFQ> {
    return apiClient.post('/rfqs', data);
  },

  /**
   * Update an RFQ
   */
  async update(id: string, data: UpdateRFQData): Promise<RFQ> {
    return apiClient.patch(`/rfqs/${id}`, data);
  },

  /**
   * Delete an RFQ
   */
  async delete(id: string): Promise<void> {
    return apiClient.delete(`/rfqs/${id}`);
  },

  /**
   * Submit an RFQ (change status to submitted)
   */
  async submit(id: string): Promise<RFQ> {
    return apiClient.post(`/rfqs/${id}/submit`);
  },

  /**
   * Mark RFQ as won
   */
  async markWon(id: string): Promise<RFQ> {
    return apiClient.post(`/rfqs/${id}/won`);
  },

  /**
   * Mark RFQ as lost
   */
  async markLost(id: string, reason?: string): Promise<RFQ> {
    return apiClient.post(`/rfqs/${id}/lost`, { reason });
  },

  /**
   * Mark RFQ as no bid
   */
  async noBid(id: string, reason?: string): Promise<RFQ> {
    return apiClient.post(`/rfqs/${id}/no-bid`, { reason });
  },

  /**
   * Cancel an RFQ
   */
  async cancel(id: string, reason?: string): Promise<RFQ> {
    return apiClient.post(`/rfqs/${id}/cancel`, { reason });
  },

  /**
   * Assign RFQ to a user
   */
  async assign(id: string, userId: string): Promise<RFQ> {
    return apiClient.post(`/rfqs/${id}/assign`, { user_id: userId });
  },

  /**
   * Unassign RFQ
   */
  async unassign(id: string): Promise<RFQ> {
    return apiClient.post(`/rfqs/${id}/unassign`);
  },

  /**
   * Duplicate an RFQ
   */
  async duplicate(id: string): Promise<RFQ> {
    return apiClient.post(`/rfqs/${id}/duplicate`);
  },

  /**
   * Get RFQ statistics
   */
  async getStats(params?: { from_date?: string; to_date?: string }): Promise<RFQStats> {
    return apiClient.get('/rfqs/stats', { params });
  },

  /**
   * Get RFQ timeline/activity
   */
  async getTimeline(id: string): Promise<TimelineEvent[]> {
    return apiClient.get(`/rfqs/${id}/timeline`);
  },

  // Line Items
  lineItems: {
    /**
     * List line items for an RFQ
     */
    async list(rfqId: string): Promise<RFQLineItem[]> {
      return apiClient.get(`/rfqs/${rfqId}/line-items`);
    },

    /**
     * Add a line item to an RFQ
     */
    async create(rfqId: string, data: CreateRFQLineItemData): Promise<RFQLineItem> {
      return apiClient.post(`/rfqs/${rfqId}/line-items`, data);
    },

    /**
     * Update a line item
     */
    async update(rfqId: string, lineItemId: string, data: UpdateRFQLineItemData): Promise<RFQLineItem> {
      return apiClient.patch(`/rfqs/${rfqId}/line-items/${lineItemId}`, data);
    },

    /**
     * Delete a line item
     */
    async delete(rfqId: string, lineItemId: string): Promise<void> {
      return apiClient.delete(`/rfqs/${rfqId}/line-items/${lineItemId}`);
    },

    /**
     * Bulk create line items
     */
    async bulkCreate(rfqId: string, items: CreateRFQLineItemData[]): Promise<RFQLineItem[]> {
      return apiClient.post(`/rfqs/${rfqId}/line-items/bulk`, { items });
    },

    /**
     * Bulk delete line items
     */
    async bulkDelete(rfqId: string, lineItemIds: string[]): Promise<void> {
      return apiClient.post(`/rfqs/${rfqId}/line-items/bulk-delete`, { ids: lineItemIds });
    },
  },
};

export interface RFQStats {
  total: number;
  by_status: Record<RFQStatus, number>;
  by_priority: Record<Priority, number>;
  total_value: number;
  average_value: number;
  win_rate: number;
  average_response_time_days: number;
  overdue: number;
  due_this_week: number;
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

// ============================================================================
// Quote API
// ============================================================================

export interface QuoteListParams extends PaginationParams {
  status?: QuoteStatus | QuoteStatus[];
  rfq_id?: string;
  customer_id?: string;
  search?: string;
  valid_from?: string;
  valid_to?: string;
  min_amount?: number;
  max_amount?: number;
}

export interface CreateQuoteData {
  rfq_id: string;
  valid_until: string;
  discount_percentage?: number;
  discount_amount?: number;
  tax_amount?: number;
  terms_and_conditions?: string;
  notes?: string;
  line_items: CreateQuoteLineItemData[];
}

export interface UpdateQuoteData {
  valid_until?: string;
  discount_percentage?: number;
  discount_amount?: number;
  tax_amount?: number;
  terms_and_conditions?: string;
  notes?: string;
}

export interface CreateQuoteLineItemData {
  rfq_line_item_id?: string;
  part_number: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  unit_price: number;
  cost?: number;
  lead_time_days?: number;
  notes?: string;
}

export interface UpdateQuoteLineItemData {
  part_number?: string;
  description?: string;
  quantity?: number;
  unit_of_measure?: string;
  unit_price?: number;
  cost?: number;
  lead_time_days?: number;
  notes?: string;
}

export const quoteApi = {
  /**
   * List quotes with pagination and filters
   */
  async list(params?: QuoteListParams): Promise<PaginatedResponse<Quote>> {
    return apiClient.get('/quotes', { params });
  },

  /**
   * Get a quote by ID
   */
  async get(id: string): Promise<Quote> {
    return apiClient.get(`/quotes/${id}`);
  },

  /**
   * Create a new quote
   */
  async create(data: CreateQuoteData): Promise<Quote> {
    return apiClient.post('/quotes', data);
  },

  /**
   * Update a quote
   */
  async update(id: string, data: UpdateQuoteData): Promise<Quote> {
    return apiClient.patch(`/quotes/${id}`, data);
  },

  /**
   * Delete a quote
   */
  async delete(id: string): Promise<void> {
    return apiClient.delete(`/quotes/${id}`);
  },

  /**
   * Submit quote for approval
   */
  async submitForApproval(id: string): Promise<Quote> {
    return apiClient.post(`/quotes/${id}/submit-for-approval`);
  },

  /**
   * Approve a quote
   */
  async approve(id: string, notes?: string): Promise<Quote> {
    return apiClient.post(`/quotes/${id}/approve`, { notes });
  },

  /**
   * Reject a quote
   */
  async reject(id: string, reason: string): Promise<Quote> {
    return apiClient.post(`/quotes/${id}/reject`, { reason });
  },

  /**
   * Send quote to customer
   */
  async send(id: string, email?: string): Promise<Quote> {
    return apiClient.post(`/quotes/${id}/send`, { email });
  },

  /**
   * Mark quote as accepted by customer
   */
  async accept(id: string): Promise<Quote> {
    return apiClient.post(`/quotes/${id}/accept`);
  },

  /**
   * Mark quote as rejected by customer
   */
  async customerReject(id: string, reason?: string): Promise<Quote> {
    return apiClient.post(`/quotes/${id}/customer-reject`, { reason });
  },

  /**
   * Create a new version of a quote
   */
  async createRevision(id: string): Promise<Quote> {
    return apiClient.post(`/quotes/${id}/revise`);
  },

  /**
   * Get quote versions
   */
  async getVersions(id: string): Promise<Quote[]> {
    return apiClient.get(`/quotes/${id}/versions`);
  },

  /**
   * Export quote to PDF
   */
  async exportPdf(id: string): Promise<Blob> {
    const response = await apiClient.get<Blob>(`/quotes/${id}/export/pdf`, {
      responseType: 'blob',
    });
    return response;
  },

  /**
   * Calculate quote totals
   */
  async calculate(data: {
    line_items: Array<{ quantity: number; unit_price: number }>;
    discount_percentage?: number;
    discount_amount?: number;
    tax_percentage?: number;
  }): Promise<QuoteTotals> {
    return apiClient.post('/quotes/calculate', data);
  },

  /**
   * Get quote statistics
   */
  async getStats(params?: { from_date?: string; to_date?: string }): Promise<QuoteStats> {
    return apiClient.get('/quotes/stats', { params });
  },

  /**
   * Get quote timeline/activity
   */
  async getTimeline(id: string): Promise<TimelineEvent[]> {
    return apiClient.get(`/quotes/${id}/timeline`);
  },

  // Line Items
  lineItems: {
    /**
     * List line items for a quote
     */
    async list(quoteId: string): Promise<QuoteLineItem[]> {
      return apiClient.get(`/quotes/${quoteId}/line-items`);
    },

    /**
     * Add a line item to a quote
     */
    async create(quoteId: string, data: CreateQuoteLineItemData): Promise<QuoteLineItem> {
      return apiClient.post(`/quotes/${quoteId}/line-items`, data);
    },

    /**
     * Update a line item
     */
    async update(quoteId: string, lineItemId: string, data: UpdateQuoteLineItemData): Promise<QuoteLineItem> {
      return apiClient.patch(`/quotes/${quoteId}/line-items/${lineItemId}`, data);
    },

    /**
     * Delete a line item
     */
    async delete(quoteId: string, lineItemId: string): Promise<void> {
      return apiClient.delete(`/quotes/${quoteId}/line-items/${lineItemId}`);
    },

    /**
     * Reorder line items
     */
    async reorder(quoteId: string, lineItemIds: string[]): Promise<QuoteLineItem[]> {
      return apiClient.post(`/quotes/${quoteId}/line-items/reorder`, { ids: lineItemIds });
    },
  },
};

export interface QuoteTotals {
  subtotal: number;
  discount: number;
  tax: number;
  total: number;
}

export interface QuoteStats {
  total: number;
  by_status: Record<QuoteStatus, number>;
  total_value: number;
  average_value: number;
  average_margin: number;
  approval_rate: number;
  average_approval_time_hours: number;
}
