import { create } from 'zustand';
import { qualityApi } from '@/api/quality';
import type {
  QualityInspection,
  NonConformanceReport,
  CAPA,
  PaginatedResponse,
  MSAStudy,
  MSAResult,
  MSAStudyStatus,
  MSAStudyType,
  ProcessCapabilityStudy,
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

interface PaginationParams {
  page?: number;
  limit?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}
import { getErrorMessage } from '@/lib/error-utils';

// Type definitions for quality data operations
export interface CreateInspectionInput {
  work_order_id?: string;
  product_id: string;
  type: string;
  inspection_date: string;
  quantity_inspected: number;
  notes?: string;
}

export interface UpdateInspectionInput {
  status?: string;
  quantity_passed?: number;
  quantity_failed?: number;
  notes?: string;
}

export interface CreateNCRInput {
  title: string;
  description: string;
  severity: string;
  product_id?: string;
  work_order_id?: string;
  quantity_affected?: number;
}

export interface UpdateNCRInput {
  status?: string;
  disposition?: string;
  root_cause?: string;
  corrective_action?: string;
}

export interface CreateCAPAInput {
  title: string;
  description: string;
  type: string;
  source_ncr_id?: string;
}

export interface UpdateCAPAInput {
  status?: string;
  root_cause?: string;
  corrective_action?: string;
  preventive_action?: string;
  due_date?: string;
}

export interface CreateMSAStudyInput {
  gauge_id: string;
  name: string;
  study_type?: MSAStudyType;
  parts_count?: number;
  operators_count?: number;
  trials_count?: number;
  notes?: string;
}

export interface AddMSAMeasurementInput {
  operator_id: string;
  part_id: string;
  trial_number?: number;
  measured_value: number;
}

export interface CreateCapabilityStudyInput {
  name: string;
  process_name: string;
  characteristic: string;
  lsl: number;
  usl: number;
  target?: number;
  unit?: string;
  notes?: string;
}

export interface AddCapabilityMeasurementInput {
  measured_value: number;
  sample_label?: string;
}

export interface CreateCustomerComplaintInput {
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

export interface UpdateCustomerComplaintInput {
  status?: string;
  root_cause?: string;
  containment_actions?: string[];
  corrective_actions?: string[];
  closed_at?: string;
}

export interface CreateCustomerSurveyInput {
  title: string;
  description?: string;
  status?: string;
  period_start?: string;
  period_end?: string;
  target_responses?: number;
  notes?: string;
}

export interface CreateCustomerSurveyResponseInput {
  customer_id?: string;
  respondent_name?: string;
  respondent_email?: string;
  nps_score: number;
  comment?: string;
}

export interface CreateFAIInspectionInput {
  inspection_number: string;
  product_id?: string;
  work_order_id?: string;
  part_number: string;
  revision?: string;
  drawing_number?: string;
  inspector_id?: string;
  notes?: string;
}

export interface UpdateFAIInspectionInput {
  status?: FAIStatus;
  notes?: string;
}

export interface CreateFAICharacteristicInput {
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

export interface CreateSelfInspectionInput {
  inspection_number: string;
  work_order_id?: string;
  product_id?: string;
  operator_id?: string;
  notes?: string;
}

export interface UpdateSelfInspectionInput {
  status?: SelfInspectionStatus;
  notes?: string;
}

export interface CreateSelfInspectionCheckInput {
  characteristic: string;
  specification?: string;
  actual_value?: string;
  result?: string;
  notes?: string;
}

export interface CreateLabMethodInput {
  name: string;
  standard?: string;
  description?: string;
  unit?: string;
  lower_spec?: number;
  upper_spec?: number;
  target_value?: number;
  status?: string;
}

export interface CreateLabSampleInput {
  sample_number: string;
  product_id?: string;
  work_order_id?: string;
  lot_number?: string;
  collected_at?: string;
  collected_by_id?: string;
  notes?: string;
}

export interface CreateLabTestRunInput {
  method_id: string;
  result_value?: number;
  result_text?: string;
  result_status?: string;
  tester_id?: string;
  notes?: string;
}

export interface CreateAQLPlanInput {
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

export interface CreateAQLInspectionInput {
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

export interface CreateTraceabilityMatrixInput {
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

export interface CreateTraceabilityLinkInput {
  matrix_id: string;
  link_type: string;
  reference_id: string;
  reference_table?: string;
  notes?: string;
  metadata_json?: Record<string, unknown>;
}

export interface CreateChangePointStudyInput {
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

export interface CreateChangePointObservationInput {
  observed_at?: string;
  value: number;
  sample_label?: string;
}

export interface CreateManagementReviewInput {
  title: string;
  period_start: string;
  period_end: string;
  scheduled_for: string;
  status?: string;
  notes?: string;
  attendees?: string[];
  metrics_snapshot?: Record<string, unknown>;
}

export interface CreateManagementReviewActionInput {
  title: string;
  status?: string;
  due_date?: string;
  assignee_id?: string;
  notes?: string;
}

interface QualityState {
  inspections: QualityInspection[];
  ncrs: NonConformanceReport[];
  capas: CAPA[];
  msaStudies: MSAStudy[];
  capabilityStudies: ProcessCapabilityStudy[];
  customerComplaints: CustomerComplaint[];
  customerSurveys: CustomerSurvey[];
  customerSatisfactionStats: CustomerSatisfactionStats | null;
  faiInspections: FAIInspection[];
  selfInspections: SelfInspection[];
  labMethods: LabTestMethod[];
  labSamples: LabSample[];
  labTests: LabTestRun[];
  aqlPlans: AQLSamplingPlan[];
  aqlInspections: AQLLotInspection[];
  traceabilityMatrices: TraceabilityMatrix[];
  traceabilityLinks: TraceabilityLink[];
  changePointStudies: ChangePointStudy[];
  changePointObservations: ChangePointObservation[];
  changePointEvents: ChangePointEvent[];
  managementReviews: ManagementReview[];
  managementReviewActions: ManagementReviewAction[];
  loading: boolean;
  error: string | null;
  totalInspections: number;
  totalNcrs: number;
  totalCapas: number;
  totalMsaStudies: number;
  totalCapabilityStudies: number;
  totalCustomerComplaints: number;
  totalCustomerSurveys: number;
  totalFaiInspections: number;
  totalSelfInspections: number;
  totalLabMethods: number;
  totalLabSamples: number;
  totalAqlPlans: number;
  totalAqlInspections: number;
  totalTraceabilityMatrices: number;
  totalTraceabilityLinks: number;
  totalChangePointStudies: number;
  totalChangePointObservations: number;
  totalChangePointEvents: number;
  totalManagementReviews: number;
  totalManagementReviewActions: number;

  // Actions
  fetchInspections: (params?: PaginationParams) => Promise<void>;
  fetchNCRs: (params?: PaginationParams) => Promise<void>;
  fetchCAPAs: (params?: PaginationParams) => Promise<void>;
  fetchMsaStudies: (params?: PaginationParams & { status?: MSAStudyStatus | MSAStudyStatus[]; study_type?: MSAStudyType | MSAStudyType[] }) => Promise<void>;
  fetchCapabilityStudies: (params?: PaginationParams & { status?: ProcessCapabilityStatus | ProcessCapabilityStatus[] }) => Promise<void>;
  fetchCustomerComplaints: () => Promise<void>;
  fetchCustomerSurveys: () => Promise<void>;
  fetchCustomerSatisfactionStats: (surveyId?: string) => Promise<void>;
  fetchFAIInspections: () => Promise<void>;
  fetchSelfInspections: () => Promise<void>;
  fetchLabMethods: () => Promise<void>;
  fetchLabSamples: () => Promise<void>;
  fetchAqlPlans: () => Promise<void>;
  fetchAqlInspections: (planId?: string) => Promise<void>;
  fetchTraceabilityMatrices: () => Promise<void>;
  fetchTraceabilityLinks: (matrixId?: string) => Promise<void>;
  fetchChangePointStudies: () => Promise<void>;
  fetchChangePointObservations: (studyId: string) => Promise<void>;
  fetchChangePointEvents: (studyId: string) => Promise<void>;
  fetchManagementReviews: () => Promise<void>;
  fetchManagementReviewActions: (reviewId?: string) => Promise<void>;
  
  createInspection: (data: CreateInspectionInput) => Promise<void>;
  updateInspection: (id: string, data: UpdateInspectionInput) => Promise<void>;
  
  createNCR: (data: CreateNCRInput) => Promise<void>;
  updateNCR: (id: string, data: UpdateNCRInput) => Promise<void>;
  
  createCAPA: (data: CreateCAPAInput) => Promise<void>;
  updateCAPA: (id: string, data: UpdateCAPAInput) => Promise<void>;

  createMsaStudy: (data: CreateMSAStudyInput) => Promise<void>;
  addMsaMeasurement: (studyId: string, data: AddMSAMeasurementInput) => Promise<void>;
  computeMsaStudy: (studyId: string) => Promise<MSAResult | null>;

  createCapabilityStudy: (data: CreateCapabilityStudyInput) => Promise<void>;
  addCapabilityMeasurement: (studyId: string, data: AddCapabilityMeasurementInput) => Promise<void>;
  computeCapabilityStudy: (studyId: string) => Promise<ProcessCapabilityResult | null>;

  createCustomerComplaint: (data: CreateCustomerComplaintInput) => Promise<void>;
  updateCustomerComplaint: (id: string, data: UpdateCustomerComplaintInput) => Promise<void>;
  closeCustomerComplaint: (id: string) => Promise<void>;
  createCustomerSurvey: (data: CreateCustomerSurveyInput) => Promise<void>;
  addCustomerSurveyResponse: (surveyId: string, data: CreateCustomerSurveyResponseInput) => Promise<void>;

  createFAIInspection: (data: CreateFAIInspectionInput) => Promise<void>;
  updateFAIInspection: (id: string, data: UpdateFAIInspectionInput) => Promise<void>;
  addFAICharacteristic: (inspectionId: string, data: CreateFAICharacteristicInput) => Promise<void>;
  closeFAIInspection: (id: string) => Promise<void>;

  createSelfInspection: (data: CreateSelfInspectionInput) => Promise<void>;
  updateSelfInspection: (id: string, data: UpdateSelfInspectionInput) => Promise<void>;
  addSelfInspectionCheck: (inspectionId: string, data: CreateSelfInspectionCheckInput) => Promise<void>;
  closeSelfInspection: (id: string) => Promise<void>;

  createLabMethod: (data: CreateLabMethodInput) => Promise<void>;
  createLabSample: (data: CreateLabSampleInput) => Promise<void>;
  addLabTestRun: (sampleId: string, data: CreateLabTestRunInput) => Promise<void>;
  createAqlPlan: (data: CreateAQLPlanInput) => Promise<void>;
  createAqlInspection: (data: CreateAQLInspectionInput) => Promise<void>;
  createTraceabilityMatrix: (data: CreateTraceabilityMatrixInput) => Promise<void>;
  createTraceabilityLink: (data: CreateTraceabilityLinkInput) => Promise<void>;
  createChangePointStudy: (data: CreateChangePointStudyInput) => Promise<void>;
  addChangePointObservation: (studyId: string, data: CreateChangePointObservationInput) => Promise<void>;
  detectChangePoint: (studyId: string) => Promise<void>;
  createManagementReview: (data: CreateManagementReviewInput) => Promise<void>;
  addManagementReviewAction: (reviewId: string, data: CreateManagementReviewActionInput) => Promise<void>;
  closeManagementReview: (reviewId: string) => Promise<void>;
}

export const useQualityStore = create<QualityState>((set, get) => ({
  inspections: [],
  ncrs: [],
  capas: [],
  msaStudies: [],
  capabilityStudies: [],
  customerComplaints: [],
  customerSurveys: [],
  customerSatisfactionStats: null,
  faiInspections: [],
  selfInspections: [],
  labMethods: [],
  labSamples: [],
  labTests: [],
  aqlPlans: [],
  aqlInspections: [],
  traceabilityMatrices: [],
  traceabilityLinks: [],
  changePointStudies: [],
  changePointObservations: [],
  changePointEvents: [],
  managementReviews: [],
  managementReviewActions: [],
  loading: false,
  error: null,
  totalInspections: 0,
  totalNcrs: 0,
  totalCapas: 0,
  totalMsaStudies: 0,
  totalCapabilityStudies: 0,
  totalCustomerComplaints: 0,
  totalCustomerSurveys: 0,
  totalFaiInspections: 0,
  totalSelfInspections: 0,
  totalLabMethods: 0,
  totalLabSamples: 0,
  totalAqlPlans: 0,
  totalAqlInspections: 0,
  totalTraceabilityMatrices: 0,
  totalTraceabilityLinks: 0,
  totalChangePointStudies: 0,
  totalChangePointObservations: 0,
  totalChangePointEvents: 0,
  totalManagementReviews: 0,
  totalManagementReviewActions: 0,

  fetchInspections: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.inspectionApi.list(params);
      const items = Array.isArray(response.items) ? response.items : [];
      const total = typeof response.total === 'number' ? response.total : items.length;
      set({ 
        inspections: items,
        totalInspections: total,
        loading: false 
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchNCRs: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.ncrApi.list(params);
      const items = Array.isArray(response.items) ? response.items : [];
      const total = typeof response.total === 'number' ? response.total : items.length;
      set({ 
        ncrs: items,
        totalNcrs: total,
        loading: false 
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchCAPAs: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.capaApi.list(params);
      const items = Array.isArray(response.items) ? response.items : [];
      const total = typeof response.total === 'number' ? response.total : items.length;
      set({ 
        capas: items,
        totalCapas: total,
        loading: false 
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchMsaStudies: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.msaApi.list(params);
      const items = Array.isArray(response) ? response : [];
      set({
        msaStudies: items,
        totalMsaStudies: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchCapabilityStudies: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.capabilityApi.list(params);
      const items = Array.isArray(response) ? response : [];
      set({
        capabilityStudies: items,
        totalCapabilityStudies: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchCustomerComplaints: async () => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.customerSatisfactionApi.listComplaints();
      const items = Array.isArray(response) ? response : [];
      set({
        customerComplaints: items,
        totalCustomerComplaints: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchCustomerSurveys: async () => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.customerSatisfactionApi.listSurveys();
      const items = Array.isArray(response) ? response : [];
      set({
        customerSurveys: items,
        totalCustomerSurveys: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchCustomerSatisfactionStats: async (surveyId) => {
    set({ loading: true, error: null });
    try {
      const stats = await qualityApi.customerSatisfactionApi.getStats(surveyId);
      set({ customerSatisfactionStats: stats, loading: false });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchFAIInspections: async () => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.faiApi.list();
      const items = Array.isArray(response) ? response : [];
      set({
        faiInspections: items,
        totalFaiInspections: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchSelfInspections: async () => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.selfInspectionApi.list();
      const items = Array.isArray(response) ? response : [];
      set({
        selfInspections: items,
        totalSelfInspections: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchLabMethods: async () => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.labApi.listMethods();
      const items = Array.isArray(response) ? response : [];
      set({
        labMethods: items,
        totalLabMethods: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchLabSamples: async () => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.labApi.listSamples();
      const items = Array.isArray(response) ? response : [];
      set({
        labSamples: items,
        totalLabSamples: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchAqlPlans: async () => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.aqlApi.listPlans();
      const items = Array.isArray(response) ? response : [];
      set({
        aqlPlans: items,
        totalAqlPlans: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchAqlInspections: async (planId) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.aqlApi.listInspections(planId);
      const items = Array.isArray(response) ? response : [];
      set({
        aqlInspections: items,
        totalAqlInspections: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchTraceabilityMatrices: async () => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.traceabilityApi.listMatrices();
      const items = Array.isArray(response) ? response : [];
      set({
        traceabilityMatrices: items,
        totalTraceabilityMatrices: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchTraceabilityLinks: async (matrixId) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.traceabilityApi.listLinks(matrixId);
      const items = Array.isArray(response) ? response : [];
      set({
        traceabilityLinks: items,
        totalTraceabilityLinks: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchChangePointStudies: async () => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.changePointApi.listStudies();
      const items = Array.isArray(response) ? response : [];
      set({
        changePointStudies: items,
        totalChangePointStudies: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchChangePointObservations: async (studyId) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.changePointApi.listObservations(studyId);
      const items = Array.isArray(response) ? response : [];
      set({
        changePointObservations: items,
        totalChangePointObservations: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchChangePointEvents: async (studyId) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.changePointApi.listEvents(studyId);
      const items = Array.isArray(response) ? response : [];
      set({
        changePointEvents: items,
        totalChangePointEvents: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchManagementReviews: async () => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.managementReviewApi.listReviews();
      const items = Array.isArray(response) ? response : [];
      set({
        managementReviews: items,
        totalManagementReviews: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchManagementReviewActions: async (reviewId) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.managementReviewApi.listActions(reviewId);
      const items = Array.isArray(response) ? response : [];
      set({
        managementReviewActions: items,
        totalManagementReviewActions: items.length,
        loading: false,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createInspection: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.inspectionApi.create(data as Parameters<typeof qualityApi.inspectionApi.create>[0]);
      await get().fetchInspections();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  updateInspection: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.inspectionApi.update(id, data as Parameters<typeof qualityApi.inspectionApi.update>[1]);
      await get().fetchInspections();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createNCR: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.ncrApi.create(data as Parameters<typeof qualityApi.ncrApi.create>[0]);
      await get().fetchNCRs();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  updateNCR: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.ncrApi.update(id, data as Parameters<typeof qualityApi.ncrApi.update>[1]);
      await get().fetchNCRs();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createCAPA: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.capaApi.create(data as Parameters<typeof qualityApi.capaApi.create>[0]);
      await get().fetchCAPAs();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  updateCAPA: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.capaApi.update(id, data as Parameters<typeof qualityApi.capaApi.update>[1]);
      await get().fetchCAPAs();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createMsaStudy: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.msaApi.create(data as Parameters<typeof qualityApi.msaApi.create>[0]);
      await get().fetchMsaStudies();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  addMsaMeasurement: async (studyId, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.msaApi.addMeasurement(studyId, data as Parameters<typeof qualityApi.msaApi.addMeasurement>[1]);
      await get().fetchMsaStudies();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  computeMsaStudy: async (studyId) => {
    set({ loading: true, error: null });
    try {
      const result = await qualityApi.msaApi.compute(studyId);
      await get().fetchMsaStudies();
      return result;
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
      return null;
    }
  },

  createCapabilityStudy: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.capabilityApi.create(data as Parameters<typeof qualityApi.capabilityApi.create>[0]);
      await get().fetchCapabilityStudies();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  addCapabilityMeasurement: async (studyId, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.capabilityApi.addMeasurement(
        studyId,
        data as Parameters<typeof qualityApi.capabilityApi.addMeasurement>[1]
      );
      await get().fetchCapabilityStudies();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  computeCapabilityStudy: async (studyId) => {
    set({ loading: true, error: null });
    try {
      const result = await qualityApi.capabilityApi.compute(studyId);
      await get().fetchCapabilityStudies();
      return result;
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
      return null;
    }
  },

  createCustomerComplaint: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.customerSatisfactionApi.createComplaint(
        data as Parameters<typeof qualityApi.customerSatisfactionApi.createComplaint>[0]
      );
      await get().fetchCustomerComplaints();
      await get().fetchCustomerSatisfactionStats();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  updateCustomerComplaint: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.customerSatisfactionApi.updateComplaint(
        id,
        data as Parameters<typeof qualityApi.customerSatisfactionApi.updateComplaint>[1]
      );
      await get().fetchCustomerComplaints();
      await get().fetchCustomerSatisfactionStats();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  closeCustomerComplaint: async (id) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.customerSatisfactionApi.closeComplaint(id);
      await get().fetchCustomerComplaints();
      await get().fetchCustomerSatisfactionStats();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createCustomerSurvey: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.customerSatisfactionApi.createSurvey(
        data as Parameters<typeof qualityApi.customerSatisfactionApi.createSurvey>[0]
      );
      await get().fetchCustomerSurveys();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  addCustomerSurveyResponse: async (surveyId, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.customerSatisfactionApi.addSurveyResponse(
        surveyId,
        data as Parameters<typeof qualityApi.customerSatisfactionApi.addSurveyResponse>[1]
      );
      await get().fetchCustomerSurveys();
      await get().fetchCustomerSatisfactionStats(surveyId);
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createFAIInspection: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.faiApi.create(data as Parameters<typeof qualityApi.faiApi.create>[0]);
      await get().fetchFAIInspections();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  updateFAIInspection: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.faiApi.update(id, data as Parameters<typeof qualityApi.faiApi.update>[1]);
      await get().fetchFAIInspections();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  addFAICharacteristic: async (inspectionId, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.faiApi.addCharacteristic(
        inspectionId,
        data as Parameters<typeof qualityApi.faiApi.addCharacteristic>[1]
      );
      await get().fetchFAIInspections();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  closeFAIInspection: async (id) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.faiApi.close(id);
      await get().fetchFAIInspections();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createSelfInspection: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.selfInspectionApi.create(
        data as Parameters<typeof qualityApi.selfInspectionApi.create>[0]
      );
      await get().fetchSelfInspections();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  updateSelfInspection: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.selfInspectionApi.update(
        id,
        data as Parameters<typeof qualityApi.selfInspectionApi.update>[1]
      );
      await get().fetchSelfInspections();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  addSelfInspectionCheck: async (inspectionId, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.selfInspectionApi.addCheck(
        inspectionId,
        data as Parameters<typeof qualityApi.selfInspectionApi.addCheck>[1]
      );
      await get().fetchSelfInspections();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  closeSelfInspection: async (id) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.selfInspectionApi.close(id);
      await get().fetchSelfInspections();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createLabMethod: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.labApi.createMethod(
        data as Parameters<typeof qualityApi.labApi.createMethod>[0]
      );
      await get().fetchLabMethods();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createLabSample: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.labApi.createSample(
        data as Parameters<typeof qualityApi.labApi.createSample>[0]
      );
      await get().fetchLabSamples();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  addLabTestRun: async (sampleId, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.labApi.addTestRun(
        sampleId,
        data as Parameters<typeof qualityApi.labApi.addTestRun>[1]
      );
      await get().fetchLabSamples();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createAqlPlan: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.aqlApi.createPlan(
        data as Parameters<typeof qualityApi.aqlApi.createPlan>[0]
      );
      await get().fetchAqlPlans();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createAqlInspection: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.aqlApi.createInspection(
        data as Parameters<typeof qualityApi.aqlApi.createInspection>[0]
      );
      await get().fetchAqlInspections(data.plan_id);
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createTraceabilityMatrix: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.traceabilityApi.createMatrix(
        data as Parameters<typeof qualityApi.traceabilityApi.createMatrix>[0]
      );
      await get().fetchTraceabilityMatrices();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createTraceabilityLink: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.traceabilityApi.createLink(
        data as Parameters<typeof qualityApi.traceabilityApi.createLink>[0]
      );
      await get().fetchTraceabilityLinks(data.matrix_id);
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createChangePointStudy: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.changePointApi.createStudy(
        data as Parameters<typeof qualityApi.changePointApi.createStudy>[0]
      );
      await get().fetchChangePointStudies();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  addChangePointObservation: async (studyId, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.changePointApi.addObservation(
        studyId,
        data as Parameters<typeof qualityApi.changePointApi.addObservation>[1]
      );
      await get().fetchChangePointObservations(studyId);
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  detectChangePoint: async (studyId) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.changePointApi.detect(studyId);
      await get().fetchChangePointEvents(studyId);
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createManagementReview: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.managementReviewApi.createReview(
        data as Parameters<typeof qualityApi.managementReviewApi.createReview>[0]
      );
      await get().fetchManagementReviews();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  addManagementReviewAction: async (reviewId, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.managementReviewApi.addAction(
        reviewId,
        data as Parameters<typeof qualityApi.managementReviewApi.addAction>[1]
      );
      await get().fetchManagementReviewActions(reviewId);
      await get().fetchManagementReviews();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  closeManagementReview: async (reviewId) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.managementReviewApi.closeReview(reviewId);
      await get().fetchManagementReviews();
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },
}));
