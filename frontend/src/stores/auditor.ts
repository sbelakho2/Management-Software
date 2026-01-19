import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

export interface AuditStats {
  total_audits: number;
  completed_this_year: number;
  open_findings: number;
  critical_findings: number;
  upcoming_audits: number;
  compliance_score: number;
}

export interface Audit {
  id: string;
  name: string;
  audit_type: string;
  status: string;
  scheduled_date: string;
  completed_date?: string;
  findings_count: number;
  lead_auditor?: string;
  priority: string;
}

export interface AuditFinding {
  id: string;
  audit_id: string;
  title: string;
  description?: string;
  area: string;
  severity: string;
  status: string;
  due_date?: string;
  days_overdue: number;
  assigned_to?: string;
}

export interface ComplianceArea {
  name: string;
  score: number;
  audits: number;
  trend: string;
}

interface AuditorState {
  stats: AuditStats | null;
  audits: Audit[];
  upcomingAudits: Audit[];
  findings: AuditFinding[];
  openFindings: AuditFinding[];
  complianceAreas: ComplianceArea[];
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
  
  fetchStats: () => Promise<void>;
  fetchAudits: (params?: { status?: string; audit_type?: string }) => Promise<void>;
  fetchUpcomingAudits: (limit?: number) => Promise<void>;
  fetchFindings: (params?: { audit_id?: string; status?: string; severity?: string }) => Promise<void>;
  fetchOpenFindings: (limit?: number) => Promise<void>;
  fetchComplianceAreas: () => Promise<void>;
  fetchAll: () => Promise<void>;
  createAudit: (audit: Partial<Audit>) => Promise<Audit | null>;
  updateAuditStatus: (auditId: string, status: string) => Promise<void>;
  createFinding: (finding: Partial<AuditFinding>) => Promise<AuditFinding | null>;
  updateFindingStatus: (findingId: string, status: string) => Promise<void>;
  clearError: () => void;
}

export const useAuditorStore = create<AuditorState>()(
  devtools(
    persist(
      (set, get) => ({
        stats: null,
        audits: [],
        upcomingAudits: [],
        findings: [],
        openFindings: [],
        complianceAreas: [],
        isLoading: false,
        error: null,
        lastFetchedAt: null,

        fetchStats: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<AuditStats>('/auditor/stats');
            set({ stats: data, isLoading: false, lastFetchedAt: Date.now() });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchAudits: async (params) => {
          set({ isLoading: true, error: null });
          try {
            let url = '/auditor/audits';
            const queryParams = new URLSearchParams();
            if (params?.status) queryParams.append('status', params.status);
            if (params?.audit_type) queryParams.append('audit_type', params.audit_type);
            if (queryParams.toString()) url += `?${queryParams.toString()}`;
            
            const response = await apiClient.get<{ items: Audit[] }>(url);
            set({ audits: response.items || [], isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchUpcomingAudits: async (limit = 5) => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<Audit[]>(`/auditor/audits/upcoming?limit=${limit}`);
            set({ upcomingAudits: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchFindings: async (params) => {
          set({ isLoading: true, error: null });
          try {
            let url = '/auditor/findings';
            const queryParams = new URLSearchParams();
            if (params?.audit_id) queryParams.append('audit_id', params.audit_id);
            if (params?.status) queryParams.append('status', params.status);
            if (params?.severity) queryParams.append('severity', params.severity);
            if (queryParams.toString()) url += `?${queryParams.toString()}`;
            
            const response = await apiClient.get<{ items: AuditFinding[] }>(url);
            set({ findings: response.items || [], isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchOpenFindings: async (limit = 10) => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<AuditFinding[]>(`/auditor/findings/open?limit=${limit}`);
            set({ openFindings: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchComplianceAreas: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<ComplianceArea[]>('/auditor/compliance-areas');
            set({ complianceAreas: data, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        fetchAll: async () => {
          const { lastFetchedAt, isLoading } = get();
          const now = Date.now();
          
          // Cache for 60 seconds
          if (lastFetchedAt && now - lastFetchedAt < 60000) {
            return;
          }
          
          if (isLoading) return;
          
          set({ isLoading: true, error: null });
          try {
            await Promise.all([
              get().fetchStats(),
              get().fetchUpcomingAudits(),
              get().fetchOpenFindings(),
              get().fetchComplianceAreas(),
            ]);
            set({ isLoading: false, lastFetchedAt: now });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        createAudit: async (audit) => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.post<Audit>('/auditor/audits', audit);
            // Refresh audits list
            await get().fetchAudits();
            set({ isLoading: false });
            return data;
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
            return null;
          }
        },

        updateAuditStatus: async (auditId, status) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.patch(`/auditor/audits/${auditId}/status?status=${status}`, {});
            // Refresh audits list
            await get().fetchAudits();
            set({ isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        createFinding: async (finding) => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.post<AuditFinding>('/auditor/findings', finding);
            // Refresh findings list
            await get().fetchOpenFindings();
            set({ isLoading: false });
            return data;
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
            return null;
          }
        },

        updateFindingStatus: async (findingId, status) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.patch(`/auditor/findings/${findingId}/status?status=${status}`, {});
            // Refresh findings list
            await get().fetchOpenFindings();
            set({ isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, isLoading: false });
          }
        },

        clearError: () => set({ error: null }),
      }),
      { name: 'auditor-storage' }
    ),
    { name: 'AuditorStore' }
  )
);
