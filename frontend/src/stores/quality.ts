import { create } from 'zustand';
import { qualityApi } from '@/api/quality';
import type {
  QualityInspection,
  NonConformanceReport,
  CAPA,
  PaginatedResponse,
} from '@/types';

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
  fetchInspections: (params?: any) => Promise<void>;
  fetchNCRs: (params?: any) => Promise<void>;
  fetchCAPAs: (params?: any) => Promise<void>;
  
  createInspection: (data: any) => Promise<void>;
  updateInspection: (id: string, data: any) => Promise<void>;
  
  createNCR: (data: any) => Promise<void>;
  updateNCR: (id: string, data: any) => Promise<void>;
  
  createCAPA: (data: any) => Promise<void>;
  updateCAPA: (id: string, data: any) => Promise<void>;
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
    } catch (error: any) {
      set({ error: error.message, loading: false });
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
    } catch (error: any) {
      set({ error: error.message, loading: false });
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
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createInspection: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.inspectionApi.create(data);
      await get().fetchInspections();
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  updateInspection: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.inspectionApi.update(id, data);
      await get().fetchInspections();
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createNCR: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.ncrApi.create(data);
      await get().fetchNCRs();
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  updateNCR: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.ncrApi.update(id, data);
      await get().fetchNCRs();
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createCAPA: async (data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.capaApi.create(data);
      await get().fetchCAPAs();
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  updateCAPA: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await qualityApi.capaApi.update(id, data);
      await get().fetchCAPAs();
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },
}));
