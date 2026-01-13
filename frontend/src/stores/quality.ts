import { create } from 'zustand';
import { qualityApi } from '@/api/quality';
import type {
  QualityInspection,
  NonConformanceReport,
  CAPA,
  PaginatedResponse,
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

interface QualityState {
  inspections: QualityInspection[];
  ncrs: NonConformanceReport[];
  capas: CAPA[];
  loading: boolean;
  error: string | null;
  totalInspections: number;
  totalNcrs: number;
  totalCapas: number;

  // Actions
  fetchInspections: (params?: PaginationParams) => Promise<void>;
  fetchNCRs: (params?: PaginationParams) => Promise<void>;
  fetchCAPAs: (params?: PaginationParams) => Promise<void>;
  
  createInspection: (data: CreateInspectionInput) => Promise<void>;
  updateInspection: (id: string, data: UpdateInspectionInput) => Promise<void>;
  
  createNCR: (data: CreateNCRInput) => Promise<void>;
  updateNCR: (id: string, data: UpdateNCRInput) => Promise<void>;
  
  createCAPA: (data: CreateCAPAInput) => Promise<void>;
  updateCAPA: (id: string, data: UpdateCAPAInput) => Promise<void>;
}

export const useQualityStore = create<QualityState>((set, get) => ({
  inspections: [],
  ncrs: [],
  capas: [],
  loading: false,
  error: null,
  totalInspections: 0,
  totalNcrs: 0,
  totalCapas: 0,

  fetchInspections: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await qualityApi.inspectionApi.list(params);
      set({ 
        inspections: response.items, 
        totalInspections: response.total,
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
      set({ 
        ncrs: response.items, 
        totalNcrs: response.total,
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
      set({ 
        capas: response.items, 
        totalCapas: response.total,
        loading: false 
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
}));
