import { create } from 'zustand';
import { apiClient } from '@/api/client';

export type DisciplineType = 'ee' | 'embedded' | 'me' | 'mfge' | 'qe' | 'purchasing';
export type WorkPacketStatus = 'pending' | 'in_progress' | 'done' | 'done_with_risks' | 'blocked' | 'waived';

export interface WorkPacket {
  id: string;
  rfq_id: string;
  discipline: DisciplineType;
  status: WorkPacketStatus;
  due_at: string | null;
  created_at: string;
  owner_id: string | null;
  outputs: any;
  attachments: any[];
  notes: string | null;
  blocker_reason: string | null;
}

interface QuotingHelperState {
  workPackets: WorkPacket[];
  clarifications: any[];
  quoteMemory: any[];
  isLoading: boolean;
  error: string | null;
  
  fetchWorkPackets: (rfqId: string) => Promise<void>;
  generateWorkPackets: (rfqId: string) => Promise<void>;
  updateWorkPacket: (packetId: string, data: Partial<WorkPacket>) => Promise<void>;
  calculateCost: (quoteId: string) => Promise<any>;
  fetchClarifications: (rfqId: string) => Promise<void>;
  fetchQuoteMemory: (rfqId: string) => Promise<void>;
  convertToNpi: (quoteId: string) => Promise<any>;
}

export const useQuotingHelperStore = create<QuotingHelperState>((set, get) => ({
  workPackets: [],
  clarifications: [],
  quoteMemory: [],
  isLoading: false,
  error: null,

  fetchWorkPackets: async (rfqId: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiClient.get<{ data: WorkPacket[] }>(`/quoting-helper/rfqs/${rfqId}/workpackets`);
      set({ workPackets: response.data, isLoading: false });
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
    }
  },

  generateWorkPackets: async (rfqId: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiClient.post<{ data: WorkPacket[] }>(`/quoting-helper/rfqs/${rfqId}/workpackets/generate`);
      set({ workPackets: response.data, isLoading: false });
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
    }
  },

  updateWorkPacket: async (packetId: string, data: Partial<WorkPacket>) => {
    try {
      const response = await apiClient.patch<{ data: WorkPacket }>(`/quoting-helper/workpackets/${packetId}`, data);
      const updatedPacket = response.data;
      set(state => ({
        workPackets: state.workPackets.map(p => p.id === packetId ? updatedPacket : p)
      }));
    } catch (error: any) {
      set({ error: error.message });
    }
  },

  calculateCost: async (quoteId: string) => {
    try {
      const response = await apiClient.post<{ data: unknown }>(`/quoting-helper/quotes/${quoteId}/cost/build`);
      return response.data;
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  fetchClarifications: async (rfqId: string) => {
    try {
      const response = await apiClient.get<{ data: unknown[] }>(`/quoting-helper/ai/clarifications/suggest/${rfqId}`);
      set({ clarifications: response.data });
    } catch (error: any) {
      set({ error: error.message });
    }
  },

  fetchQuoteMemory: async (rfqId: string) => {
    try {
      const response = await apiClient.get<{ data: unknown[] }>(`/quoting-helper/ai/quote-memory/retrieve/${rfqId}`);
      set({ quoteMemory: response.data });
    } catch (error: any) {
      set({ error: error.message });
    }
  },

  convertToNpi: async (quoteId: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiClient.post<{ data: { project_id: string; project_name: string } }>(`/quoting-helper/quotes/${quoteId}/convert-to-npi`);
      set({ isLoading: false });
      return response.data;
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },
}));
