import { create } from 'zustand';
import { executiveApi, type NL2SQLResponse, type EmployeeRiskResponse, type NL2SQLRequest, type EmployeeRiskRequest } from '@/api/executive';

interface ExecutiveState {
  nl2sqlResult: NL2SQLResponse | null;
  riskResult: EmployeeRiskResponse | null;
  nl2sqlLoading: boolean;
  nl2sqlError: string | null;
  riskLoading: boolean;
  riskError: string | null;

  runNl2sql: (payload: NL2SQLRequest) => Promise<void>;
  analyzeRisk: (payload: EmployeeRiskRequest) => Promise<void>;
  clearResults: () => void;
}

export const useExecutiveStore = create<ExecutiveState>((set) => ({
  nl2sqlResult: null,
  riskResult: null,
  nl2sqlLoading: false,
  nl2sqlError: null,
  riskLoading: false,
  riskError: null,

  runNl2sql: async (payload) => {
    set({ nl2sqlLoading: true, nl2sqlError: null });
    try {
      const result = await executiveApi.nl2sql(payload);
      set({ nl2sqlResult: result, nl2sqlLoading: false });
    } catch (error: any) {
      set({ nl2sqlError: error.message, nl2sqlLoading: false });
    }
  },

  analyzeRisk: async (payload) => {
    set({ riskLoading: true, riskError: null });
    try {
      const result = await executiveApi.analyzeEmployeeRisk(payload);
      set({ riskResult: result, riskLoading: false });
    } catch (error: any) {
      set({ riskError: error.message, riskLoading: false });
    }
  },

  clearResults: () => set({ 
    nl2sqlResult: null, 
    riskResult: null, 
    nl2sqlError: null, 
    riskError: null 
  }),
}));
