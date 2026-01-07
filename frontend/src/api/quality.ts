import { apiClient, type PaginationParams } from './client';
import type {
  QualityInspection,
  InspectionType,
  InspectionStatus,
  InspectionResult,
  NonConformanceReport,
  NCRStatus,
  Severity,
  NCRDisposition,
  CAPA,
  CAPAStatus,
  CAPAType,
  PaginatedResponse,
} from '@/types';

// ============================================================================
// Quality Inspection API
// ============================================================================

export interface InspectionListParams extends PaginationParams {
  type?: InspectionType | InspectionType[];
  status?: InspectionStatus | InspectionStatus[];
  work_order_id?: string;
  product_id?: string;
  inspector_id?: string;
  inspection_date_from?: string;
  inspection_date_to?: string;
  search?: string;
}

export interface CreateInspectionData {
  work_order_id?: string;
  product_id: string;
  type: InspectionType;
  inspection_date: string;
  quantity_inspected: number;
  notes?: string;
  results?: CreateInspectionResultData[];
}

export interface UpdateInspectionData {
  status?: InspectionStatus;
  inspection_date?: string;
  quantity_inspected?: number;
  quantity_passed?: number;
  quantity_failed?: number;
  notes?: string;
}

export interface CreateInspectionResultData {
  characteristic: string;
  specification: string;
  actual_value: string;
  is_pass: boolean;
  notes?: string;
}

export const inspectionApi = {
  /**
   * List inspections with pagination and filters
   */
  async list(params?: InspectionListParams): Promise<PaginatedResponse<QualityInspection>> {
    return apiClient.get('/quality/inspections', { params });
  },

  /**
   * Get an inspection by ID
   */
  async get(id: string): Promise<QualityInspection> {
    return apiClient.get(`/quality/inspections/${id}`);
  },

  /**
   * Create a new inspection
   */
  async create(data: CreateInspectionData): Promise<QualityInspection> {
    return apiClient.post('/quality/inspections', data);
  },

  /**
   * Update an inspection
   */
  async update(id: string, data: UpdateInspectionData): Promise<QualityInspection> {
    return apiClient.patch(`/quality/inspections/${id}`, data);
  },

  /**
   * Delete an inspection
   */
  async delete(id: string): Promise<void> {
    return apiClient.delete(`/quality/inspections/${id}`);
  },

  /**
   * Start an inspection
   */
  async start(id: string): Promise<QualityInspection> {
    return apiClient.post(`/quality/inspections/${id}/start`);
  },

  /**
   * Complete an inspection
   */
  async complete(id: string): Promise<QualityInspection> {
    return apiClient.post(`/quality/inspections/${id}/complete`);
  },

  /**
   * Cancel an inspection
   */
  async cancel(id: string, reason?: string): Promise<QualityInspection> {
    return apiClient.post(`/quality/inspections/${id}/cancel`, { reason });
  },

  /**
   * Add inspection result
   */
  async addResult(inspectionId: string, data: CreateInspectionResultData): Promise<InspectionResult> {
    return apiClient.post(`/quality/inspections/${inspectionId}/results`, data);
  },

  /**
   * Update inspection result
   */
  async updateResult(inspectionId: string, resultId: string, data: Partial<CreateInspectionResultData>): Promise<InspectionResult> {
    return apiClient.patch(`/quality/inspections/${inspectionId}/results/${resultId}`, data);
  },

  /**
   * Delete inspection result
   */
  async deleteResult(inspectionId: string, resultId: string): Promise<void> {
    return apiClient.delete(`/quality/inspections/${inspectionId}/results/${resultId}`);
  },

  /**
   * Create NCR from failed inspection
   */
  async createNCR(id: string, data: Partial<CreateNCRData>): Promise<NonConformanceReport> {
    return apiClient.post(`/quality/inspections/${id}/create-ncr`, data);
  },

  /**
   * Get inspection statistics
   */
  async getStats(params?: { from_date?: string; to_date?: string }): Promise<InspectionStats> {
    return apiClient.get('/quality/inspections/stats', { params });
  },
};

export interface InspectionStats {
  total: number;
  by_type: Record<InspectionType, number>;
  by_status: Record<InspectionStatus, number>;
  pass_rate: number;
  total_inspected: number;
  total_passed: number;
  total_failed: number;
}

// ============================================================================
// Non-Conformance Report (NCR) API
// ============================================================================

export interface NCRListParams extends PaginationParams {
  status?: NCRStatus | NCRStatus[];
  severity?: Severity | Severity[];
  disposition?: NCRDisposition | NCRDisposition[];
  product_id?: string;
  assigned_to?: string;
  due_date_from?: string;
  due_date_to?: string;
  search?: string;
}

export interface CreateNCRData {
  inspection_id?: string;
  work_order_id?: string;
  product_id: string;
  severity: Severity;
  description: string;
  quantity_affected: number;
  assigned_to?: string;
  due_date?: string;
}

export interface UpdateNCRData {
  status?: NCRStatus;
  severity?: Severity;
  description?: string;
  root_cause?: string;
  disposition?: NCRDisposition;
  quantity_affected?: number;
  cost_impact?: number;
  assigned_to?: string | null;
  due_date?: string | null;
}

export const ncrApi = {
  /**
   * List NCRs with pagination and filters
   */
  async list(params?: NCRListParams): Promise<PaginatedResponse<NonConformanceReport>> {
    return apiClient.get('/quality/ncrs', { params });
  },

  /**
   * Get an NCR by ID
   */
  async get(id: string): Promise<NonConformanceReport> {
    return apiClient.get(`/quality/ncrs/${id}`);
  },

  /**
   * Create a new NCR
   */
  async create(data: CreateNCRData): Promise<NonConformanceReport> {
    return apiClient.post('/quality/ncrs', data);
  },

  /**
   * Update an NCR
   */
  async update(id: string, data: UpdateNCRData): Promise<NonConformanceReport> {
    return apiClient.patch(`/quality/ncrs/${id}`, data);
  },

  /**
   * Delete an NCR
   */
  async delete(id: string): Promise<void> {
    return apiClient.delete(`/quality/ncrs/${id}`);
  },

  /**
   * Start investigation
   */
  async startInvestigation(id: string): Promise<NonConformanceReport> {
    return apiClient.post(`/quality/ncrs/${id}/investigate`);
  },

  /**
   * Set disposition
   */
  async setDisposition(id: string, disposition: NCRDisposition, notes?: string): Promise<NonConformanceReport> {
    return apiClient.post(`/quality/ncrs/${id}/disposition`, { disposition, notes });
  },

  /**
   * Close NCR
   */
  async close(id: string, notes?: string): Promise<NonConformanceReport> {
    return apiClient.post(`/quality/ncrs/${id}/close`, { notes });
  },

  /**
   * Create CAPA from NCR
   */
  async createCAPA(id: string, data: Partial<CreateCAPAData>): Promise<CAPA> {
    return apiClient.post(`/quality/ncrs/${id}/create-capa`, data);
  },

  /**
   * Get NCR statistics
   */
  async getStats(params?: { from_date?: string; to_date?: string }): Promise<NCRStats> {
    return apiClient.get('/quality/ncrs/stats', { params });
  },

  /**
   * Get NCR timeline
   */
  async getTimeline(id: string): Promise<TimelineEvent[]> {
    return apiClient.get(`/quality/ncrs/${id}/timeline`);
  },
};

export interface NCRStats {
  total: number;
  by_status: Record<NCRStatus, number>;
  by_severity: Record<Severity, number>;
  by_disposition: Record<NCRDisposition, number>;
  total_cost_impact: number;
  average_resolution_days: number;
  open_count: number;
  overdue_count: number;
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
// CAPA API
// ============================================================================

export interface CAPAListParams extends PaginationParams {
  type?: CAPAType | CAPAType[];
  status?: CAPAStatus | CAPAStatus[];
  assigned_to?: string;
  due_date_from?: string;
  due_date_to?: string;
  search?: string;
}

export interface CreateCAPAData {
  ncr_id?: string;
  type: CAPAType;
  title: string;
  description: string;
  root_cause_analysis?: string;
  corrective_action?: string;
  preventive_action?: string;
  assigned_to: string;
  due_date: string;
}

export interface UpdateCAPAData {
  type?: CAPAType;
  status?: CAPAStatus;
  title?: string;
  description?: string;
  root_cause_analysis?: string;
  corrective_action?: string;
  preventive_action?: string;
  assigned_to?: string;
  due_date?: string;
  effectiveness_review?: string;
}

export const capaApi = {
  /**
   * List CAPAs with pagination and filters
   */
  async list(params?: CAPAListParams): Promise<PaginatedResponse<CAPA>> {
    return apiClient.get('/quality/capas', { params });
  },

  /**
   * Get a CAPA by ID
   */
  async get(id: string): Promise<CAPA> {
    return apiClient.get(`/quality/capas/${id}`);
  },

  /**
   * Create a new CAPA
   */
  async create(data: CreateCAPAData): Promise<CAPA> {
    return apiClient.post('/quality/capas', data);
  },

  /**
   * Update a CAPA
   */
  async update(id: string, data: UpdateCAPAData): Promise<CAPA> {
    return apiClient.patch(`/quality/capas/${id}`, data);
  },

  /**
   * Delete a CAPA
   */
  async delete(id: string): Promise<void> {
    return apiClient.delete(`/quality/capas/${id}`);
  },

  /**
   * Start work on CAPA
   */
  async start(id: string): Promise<CAPA> {
    return apiClient.post(`/quality/capas/${id}/start`);
  },

  /**
   * Submit for verification
   */
  async submitForVerification(id: string): Promise<CAPA> {
    return apiClient.post(`/quality/capas/${id}/submit-for-verification`);
  },

  /**
   * Verify CAPA
   */
  async verify(id: string, notes?: string): Promise<CAPA> {
    return apiClient.post(`/quality/capas/${id}/verify`, { notes });
  },

  /**
   * Reject verification
   */
  async rejectVerification(id: string, reason: string): Promise<CAPA> {
    return apiClient.post(`/quality/capas/${id}/reject-verification`, { reason });
  },

  /**
   * Close CAPA
   */
  async close(id: string, effectiveness_review?: string): Promise<CAPA> {
    return apiClient.post(`/quality/capas/${id}/close`, { effectiveness_review });
  },

  /**
   * Get CAPA statistics
   */
  async getStats(params?: { from_date?: string; to_date?: string }): Promise<CAPAStats> {
    return apiClient.get('/quality/capas/stats', { params });
  },

  /**
   * Get CAPA timeline
   */
  async getTimeline(id: string): Promise<TimelineEvent[]> {
    return apiClient.get(`/quality/capas/${id}/timeline`);
  },
};

export interface CAPAStats {
  total: number;
  by_type: Record<CAPAType, number>;
  by_status: Record<CAPAStatus, number>;
  completion_rate: number;
  average_completion_days: number;
  open_count: number;
  overdue_count: number;
  verification_rate: number;
}
