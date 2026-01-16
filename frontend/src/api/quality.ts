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
  MSAStudy,
  MSAMeasurement,
  MSAResult,
  MSAStudyStatus,
  MSAStudyType,
  ProcessCapabilityStudy,
  ProcessCapabilityMeasurement,
  ProcessCapabilityResult,
  ProcessCapabilityStatus,
  CustomerComplaint,
  CustomerSurvey,
  CustomerSurveyResponse,
  CustomerSatisfactionStats,
  FAIInspection,
  FAICharacteristic,
  FAIStatus,
  SelfInspection,
  SelfInspectionCheck,
  SelfInspectionStatus,
  LabTestMethod,
  LabSample,
  LabTestRun,
  AQLSamplingPlan,
  AQLLotInspection,
  TraceabilityMatrix,
  TraceabilityLink,
  ChangePointStudy,
  ChangePointObservation,
  ChangePointEvent,
  ManagementReview,
  ManagementReviewAction,
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
    return apiClient.get('/quality/non-conformances', { params });
  },

  /**
   * Get an NCR by ID
   */
  async get(id: string): Promise<NonConformanceReport> {
    return apiClient.get(`/quality/non-conformances/${id}`);
  },

  /**
   * Create a new NCR
   */
  async create(data: CreateNCRData): Promise<NonConformanceReport> {
    return apiClient.post('/quality/non-conformances', data);
  },

  /**
   * Update an NCR
   */
  async update(id: string, data: UpdateNCRData): Promise<NonConformanceReport> {
    return apiClient.patch(`/quality/non-conformances/${id}`, data);
  },

  /**
   * Delete an NCR
   */
  async delete(id: string): Promise<void> {
    return apiClient.delete(`/quality/non-conformances/${id}`);
  },

  /**
   * Start investigation
   */
  async startInvestigation(id: string): Promise<NonConformanceReport> {
    return apiClient.post(`/quality/non-conformances/${id}/investigate`);
  },

  /**
   * Set disposition
   */
  async setDisposition(id: string, disposition: NCRDisposition, notes?: string): Promise<NonConformanceReport> {
    return apiClient.post(`/quality/non-conformances/${id}/disposition`, { disposition, notes });
  },

  /**
   * Close NCR
   */
  async close(id: string, notes?: string): Promise<NonConformanceReport> {
    return apiClient.post(`/quality/non-conformances/${id}/close`, { notes });
  },

  /**
   * Create CAPA from NCR
   */
  async createCAPA(id: string, data: Partial<CreateCAPAData>): Promise<CAPA> {
    return apiClient.post(`/quality/non-conformances/${id}/create-capa`, data);
  },

  /**
   * Get NCR statistics
   */
  async getStats(params?: { from_date?: string; to_date?: string }): Promise<NCRStats> {
    return apiClient.get('/quality/non-conformances/stats', { params });
  },

  /**
   * Get NCR timeline
   */
  async getTimeline(id: string): Promise<TimelineEvent[]> {
    return apiClient.get(`/quality/non-conformances/${id}/timeline`);
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

// =============================================================================
// MSA / GRR API
// =============================================================================

export interface MSAStudyListParams extends PaginationParams {
  gauge_id?: string;
  status?: MSAStudyStatus | MSAStudyStatus[];
  study_type?: MSAStudyType | MSAStudyType[];
  search?: string;
}

export interface CreateMSAStudyData {
  gauge_id: string;
  name: string;
  study_type?: MSAStudyType;
  parts_count?: number;
  operators_count?: number;
  trials_count?: number;
  notes?: string;
}

export interface AddMSAMeasurementData {
  operator_id: string;
  part_id: string;
  trial_number?: number;
  measured_value: number;
}

export const msaApi = {
  /**
   * List MSA studies
   */
  async list(params?: MSAStudyListParams): Promise<MSAStudy[]> {
    return apiClient.get('/quality/msa-studies', { params });
  },

  /**
   * Get an MSA study
   */
  async get(id: string): Promise<MSAStudy> {
    return apiClient.get(`/quality/msa-studies/${id}`);
  },

  /**
   * Create an MSA study
   */
  async create(data: CreateMSAStudyData): Promise<MSAStudy> {
    return apiClient.post('/quality/msa-studies', data);
  },

  /**
   * Add measurement to MSA study
   */
  async addMeasurement(studyId: string, data: AddMSAMeasurementData): Promise<MSAMeasurement> {
    return apiClient.post(`/quality/msa-studies/${studyId}/measurements`, data);
  },

  /**
   * Compute GRR results
   */
  async compute(studyId: string): Promise<MSAResult> {
    return apiClient.post(`/quality/msa-studies/${studyId}/compute`);
  },
};

// =============================================================================
// Process Capability (Cp/Cpk) API
// =============================================================================

export interface CapabilityStudyListParams extends PaginationParams {
  status?: ProcessCapabilityStatus | ProcessCapabilityStatus[];
  search?: string;
}

export interface CreateCapabilityStudyData {
  name: string;
  process_name: string;
  characteristic: string;
  lsl: number;
  usl: number;
  target?: number;
  unit?: string;
  notes?: string;
}

export interface AddCapabilityMeasurementData {
  measured_value: number;
  sample_label?: string;
}

export const capabilityApi = {
  /**
   * List capability studies
   */
  async list(params?: CapabilityStudyListParams): Promise<ProcessCapabilityStudy[]> {
    return apiClient.get('/quality/capability-studies', { params });
  },

  /**
   * Get a capability study
   */
  async get(id: string): Promise<ProcessCapabilityStudy> {
    return apiClient.get(`/quality/capability-studies/${id}`);
  },

  /**
   * Create a capability study
   */
  async create(data: CreateCapabilityStudyData): Promise<ProcessCapabilityStudy> {
    return apiClient.post('/quality/capability-studies', data);
  },

  /**
   * Add measurement to capability study
   */
  async addMeasurement(studyId: string, data: AddCapabilityMeasurementData): Promise<ProcessCapabilityMeasurement> {
    return apiClient.post(`/quality/capability-studies/${studyId}/measurements`, data);
  },

  /**
   * Compute Cp/Cpk results
   */
  async compute(studyId: string): Promise<ProcessCapabilityResult> {
    return apiClient.post(`/quality/capability-studies/${studyId}/compute`);
  },
};

// =============================================================================
// Customer Satisfaction API
// =============================================================================

export interface CreateCustomerComplaintData {
  customer_id?: string;
  title: string;
  description: string;
  received_at?: string;
  status?: string;
  lot_id?: string;
  related_nc_id?: number;
  related_capa_id?: number;
  rma_number?: string;
  root_cause?: string;
  containment_actions?: string[];
  corrective_actions?: string[];
}

export interface UpdateCustomerComplaintData {
  status?: string;
  root_cause?: string;
  containment_actions?: string[];
  corrective_actions?: string[];
  closed_at?: string;
}

export interface CreateCustomerSurveyData {
  title: string;
  description?: string;
  status?: string;
  period_start?: string;
  period_end?: string;
  target_responses?: number;
  notes?: string;
}

export interface CreateCustomerSurveyResponseData {
  customer_id?: string;
  respondent_name?: string;
  respondent_email?: string;
  nps_score: number;
  comment?: string;
}

export const customerSatisfactionApi = {
  async listComplaints(): Promise<CustomerComplaint[]> {
    return apiClient.get('/quality/customer-complaints');
  },

  async getComplaint(id: string): Promise<CustomerComplaint> {
    return apiClient.get(`/quality/customer-complaints/${id}`);
  },

  async createComplaint(data: CreateCustomerComplaintData): Promise<CustomerComplaint> {
    return apiClient.post('/quality/customer-complaints', data);
  },

  async updateComplaint(id: string, data: UpdateCustomerComplaintData): Promise<CustomerComplaint> {
    return apiClient.patch(`/quality/customer-complaints/${id}`, data);
  },

  async closeComplaint(id: string): Promise<CustomerComplaint> {
    return apiClient.post(`/quality/customer-complaints/${id}/close`);
  },

  async listSurveys(): Promise<CustomerSurvey[]> {
    return apiClient.get('/quality/customer-surveys');
  },

  async getSurvey(id: string): Promise<CustomerSurvey> {
    return apiClient.get(`/quality/customer-surveys/${id}`);
  },

  async createSurvey(data: CreateCustomerSurveyData): Promise<CustomerSurvey> {
    return apiClient.post('/quality/customer-surveys', data);
  },

  async addSurveyResponse(surveyId: string, data: CreateCustomerSurveyResponseData): Promise<CustomerSurveyResponse> {
    return apiClient.post(`/quality/customer-surveys/${surveyId}/responses`, data);
  },

  async getStats(surveyId?: string): Promise<CustomerSatisfactionStats> {
    return apiClient.get('/quality/customer-satisfaction/stats', {
      params: surveyId ? { survey_id: surveyId } : undefined,
    });
  },
};

// =============================================================================
// FAI / AS9102 API
// =============================================================================

export interface CreateFAIInspectionData {
  inspection_number: string;
  product_id?: string;
  work_order_id?: string;
  part_number: string;
  revision?: string;
  drawing_number?: string;
  inspector_id?: string;
  notes?: string;
}

export interface UpdateFAIInspectionData {
  status?: FAIStatus;
  notes?: string;
}

export interface CreateFAICharacteristicData {
  characteristic_number: number;
  requirement: string;
  nominal?: number;
  tolerance?: string;
  actual?: number;
  result?: string;
  method?: string;
  tool_id?: string;
  notes?: string;
}

export const faiApi = {
  async list(): Promise<FAIInspection[]> {
    return apiClient.get('/quality/fai-inspections');
  },

  async get(id: string): Promise<FAIInspection> {
    return apiClient.get(`/quality/fai-inspections/${id}`);
  },

  async create(data: CreateFAIInspectionData): Promise<FAIInspection> {
    return apiClient.post('/quality/fai-inspections', data);
  },

  async update(id: string, data: UpdateFAIInspectionData): Promise<FAIInspection> {
    return apiClient.patch(`/quality/fai-inspections/${id}`, data);
  },

  async addCharacteristic(inspectionId: string, data: CreateFAICharacteristicData): Promise<FAICharacteristic> {
    return apiClient.post(`/quality/fai-inspections/${inspectionId}/characteristics`, data);
  },

  async close(inspectionId: string): Promise<FAIInspection> {
    return apiClient.post(`/quality/fai-inspections/${inspectionId}/close`);
  },
};

// =============================================================================
// Operator Self-Inspection API
// =============================================================================

export interface CreateSelfInspectionData {
  inspection_number: string;
  work_order_id?: string;
  product_id?: string;
  operator_id?: string;
  notes?: string;
}

export interface UpdateSelfInspectionData {
  status?: SelfInspectionStatus;
  notes?: string;
}

export interface CreateSelfInspectionCheckData {
  characteristic: string;
  specification?: string;
  actual_value?: string;
  result?: string;
  notes?: string;
}

export const selfInspectionApi = {
  async list(): Promise<SelfInspection[]> {
    return apiClient.get('/quality/self-inspections');
  },

  async get(id: string): Promise<SelfInspection> {
    return apiClient.get(`/quality/self-inspections/${id}`);
  },

  async create(data: CreateSelfInspectionData): Promise<SelfInspection> {
    return apiClient.post('/quality/self-inspections', data);
  },

  async update(id: string, data: UpdateSelfInspectionData): Promise<SelfInspection> {
    return apiClient.patch(`/quality/self-inspections/${id}`, data);
  },

  async addCheck(inspectionId: string, data: CreateSelfInspectionCheckData): Promise<SelfInspectionCheck> {
    return apiClient.post(`/quality/self-inspections/${inspectionId}/checks`, data);
  },

  async close(inspectionId: string): Promise<SelfInspection> {
    return apiClient.post(`/quality/self-inspections/${inspectionId}/close`);
  },
};

// =============================================================================
// Lab Management API
// =============================================================================

export interface CreateLabMethodData {
  name: string;
  standard?: string;
  description?: string;
  unit?: string;
  lower_spec?: number;
  upper_spec?: number;
  target_value?: number;
  status?: string;
}

export interface CreateLabSampleData {
  sample_number: string;
  product_id?: string;
  work_order_id?: string;
  lot_number?: string;
  collected_at?: string;
  collected_by_id?: string;
  notes?: string;
}

export interface CreateLabTestRunData {
  method_id: string;
  result_value?: number;
  result_text?: string;
  result_status?: string;
  tester_id?: string;
  notes?: string;
}

export interface CreateAQLPlanData {
  plan_code: string;
  standard?: string;
  inspection_level?: string;
  aql_level?: string;
  lot_size_min: number;
  lot_size_max: number;
  sample_size: number;
  accept_limit: number;
  reject_limit: number;
  status?: string;
  notes?: string;
}

export interface CreateAQLInspectionData {
  plan_id: string;
  lot_number: string;
  lot_size: number;
  sample_size?: number;
  defect_count: number;
  inspected_at?: string;
  inspector_id?: string;
  defects_json?: Array<Record<string, unknown>>;
  notes?: string;
}

export interface CreateTraceabilityMatrixData {
  name: string;
  description?: string;
  status?: string;
  product_id?: number;
  work_order_id?: number;
  lot_number?: string;
  batch_id?: string;
  external_reference?: string;
  metadata_json?: Record<string, unknown>;
}

export interface CreateTraceabilityLinkData {
  matrix_id: string;
  link_type: string;
  reference_id: string;
  reference_table?: string;
  notes?: string;
  metadata_json?: Record<string, unknown>;
}

export interface CreateChangePointStudyData {
  name: string;
  process_name: string;
  characteristic: string;
  method?: string;
  sensitivity?: number;
  status?: string;
  started_at?: string;
  notes?: string;
  metadata_json?: Record<string, unknown>;
}

export interface CreateChangePointObservationData {
  observed_at?: string;
  value: number;
  sample_label?: string;
}

export interface CreateManagementReviewData {
  title: string;
  period_start: string;
  period_end: string;
  scheduled_for: string;
  status?: string;
  notes?: string;
  attendees?: string[];
  metrics_snapshot?: Record<string, unknown>;
}

export interface CreateManagementReviewActionData {
  title: string;
  status?: string;
  due_date?: string;
  assignee_id?: string;
  notes?: string;
}

export const labApi = {
  async listMethods(): Promise<LabTestMethod[]> {
    return apiClient.get('/quality/lab-methods');
  },

  async createMethod(data: CreateLabMethodData): Promise<LabTestMethod> {
    return apiClient.post('/quality/lab-methods', data);
  },

  async listSamples(): Promise<LabSample[]> {
    return apiClient.get('/quality/lab-samples');
  },

  async createSample(data: CreateLabSampleData): Promise<LabSample> {
    return apiClient.post('/quality/lab-samples', data);
  },

  async addTestRun(sampleId: string, data: CreateLabTestRunData): Promise<LabTestRun> {
    return apiClient.post(`/quality/lab-samples/${sampleId}/tests`, data);
  },
};

export const aqlApi = {
  async listPlans(): Promise<AQLSamplingPlan[]> {
    return apiClient.get('/quality/aql/plans');
  },

  async createPlan(data: CreateAQLPlanData): Promise<AQLSamplingPlan> {
    return apiClient.post('/quality/aql/plans', data);
  },

  async listInspections(planId?: string): Promise<AQLLotInspection[]> {
    const params = planId ? { plan_id: planId } : undefined;
    return apiClient.get('/quality/aql/inspections', { params });
  },

  async createInspection(data: CreateAQLInspectionData): Promise<AQLLotInspection> {
    return apiClient.post('/quality/aql/inspections', data);
  },
};

export const traceabilityApi = {
  async listMatrices(): Promise<TraceabilityMatrix[]> {
    return apiClient.get('/quality/traceability/matrices');
  },

  async createMatrix(data: CreateTraceabilityMatrixData): Promise<TraceabilityMatrix> {
    return apiClient.post('/quality/traceability/matrices', data);
  },

  async listLinks(matrixId?: string): Promise<TraceabilityLink[]> {
    const params = matrixId ? { matrix_id: matrixId } : undefined;
    return apiClient.get('/quality/traceability/links', { params });
  },

  async createLink(data: CreateTraceabilityLinkData): Promise<TraceabilityLink> {
    return apiClient.post('/quality/traceability/links', data);
  },
};

export const changePointApi = {
  async listStudies(): Promise<ChangePointStudy[]> {
    return apiClient.get('/quality/change-point/studies');
  },

  async createStudy(data: CreateChangePointStudyData): Promise<ChangePointStudy> {
    return apiClient.post('/quality/change-point/studies', data);
  },

  async listObservations(studyId: string): Promise<ChangePointObservation[]> {
    return apiClient.get(`/quality/change-point/studies/${studyId}/observations`);
  },

  async addObservation(studyId: string, data: CreateChangePointObservationData): Promise<ChangePointObservation> {
    return apiClient.post(`/quality/change-point/studies/${studyId}/observations`, data);
  },

  async listEvents(studyId: string): Promise<ChangePointEvent[]> {
    return apiClient.get(`/quality/change-point/studies/${studyId}/events`);
  },

  async detect(studyId: string): Promise<ChangePointEvent | null> {
    return apiClient.post(`/quality/change-point/studies/${studyId}/detect`, {});
  },
};

export const managementReviewApi = {
  async listReviews(): Promise<ManagementReview[]> {
    return apiClient.get('/quality/management-reviews');
  },

  async createReview(data: CreateManagementReviewData): Promise<ManagementReview> {
    return apiClient.post('/quality/management-reviews', data);
  },

  async addAction(reviewId: string, data: CreateManagementReviewActionData): Promise<ManagementReviewAction> {
    return apiClient.post(`/quality/management-reviews/${reviewId}/actions`, data);
  },

  async listActions(reviewId?: string): Promise<ManagementReviewAction[]> {
    const params = reviewId ? { review_id: reviewId } : undefined;
    return apiClient.get('/quality/management-reviews/actions', { params });
  },

  async closeReview(reviewId: string): Promise<ManagementReview> {
    return apiClient.post(`/quality/management-reviews/${reviewId}/close`, {});
  },
};

export const qualityApi = {
  inspectionApi,
  ncrApi,
  capaApi,
  msaApi,
  capabilityApi,
  customerSatisfactionApi,
  faiApi,
  selfInspectionApi,
  labApi,
  aqlApi,
  traceabilityApi,
  changePointApi,
  managementReviewApi,
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
