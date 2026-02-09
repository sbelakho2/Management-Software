import { create } from 'zustand';
import { executiveApi, type NL2SQLResponse, type EmployeeRiskResponse, type NL2SQLRequest, type EmployeeRiskRequest, type SQDCPResponse, type CrossFunctionalKPIResponse, type StrategicDirectivesResponse } from '@/api/executive';

interface ExecutiveState {
  nl2sqlResult: NL2SQLResponse | null;
  riskResult: EmployeeRiskResponse | null;
  sqdcp: SQDCPResponse | null;
  kpiSummary: CrossFunctionalKPIResponse | null;
  directives: StrategicDirectivesResponse | null;
  nl2sqlLoading: boolean;
  nl2sqlError: string | null;
  riskLoading: boolean;
  riskError: string | null;
  sqdcpLoading: boolean;

  runNl2sql: (payload: NL2SQLRequest) => Promise<void>;
  analyzeRisk: (payload: EmployeeRiskRequest) => Promise<void>;
  fetchSQDCP: () => Promise<void>;
  fetchKPISummary: () => Promise<void>;
  fetchDirectives: () => Promise<void>;
  clearResults: () => void;
}

export const useExecutiveStore = create<ExecutiveState>((set) => ({
  nl2sqlResult: null,
  riskResult: null,
  sqdcp: null,
  kpiSummary: null,
  directives: null,
  nl2sqlLoading: false,
  nl2sqlError: null,
  riskLoading: false,
  riskError: null,
  sqdcpLoading: false,

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

  fetchSQDCP: async () => {
    set({ sqdcpLoading: true });
    try {
      const result = await executiveApi.getSQDCP();
      set({ sqdcp: result, sqdcpLoading: false });
    } catch {
      set({ sqdcpLoading: false });
    }
  },

  fetchKPISummary: async () => {
    try {
      const result = await executiveApi.getKPISummary();
      set({ kpiSummary: result });
    } catch {
      // silent fail
    }
  },

  fetchDirectives: async () => {
    try {
      const result = await executiveApi.getStrategicDirectives();
      set({ directives: result });
    } catch {
      // silent fail
    }
  },

  clearResults: () => set({ 
    nl2sqlResult: null, 
    riskResult: null, 
    nl2sqlError: null, 
    riskError: null 
  }),
}));
