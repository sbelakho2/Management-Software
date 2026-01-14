import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

// Types
export type GateStatus = 'active' | 'inactive';
export type ApprovalType = 'quote' | 'change_order' | 'invoice' | 'purchase' | 'expense';
export type TemplateType = 'a3' | 'obeya' | 'email' | 'report';
export type RoleType = 'operator' | 'team_lead' | 'supervisor' | 'gm' | 'admin';
export type LearningFrequency = 'daily' | 'weekly' | 'monthly' | 'quarterly';
export type FeatureFlagCategory = 'feature' | 'experiment' | 'killswitch';

export interface Gate {
  id: string;
  name: string;
  phase: string;
  description: string;
  required_approvers: number;
  bypass_roles: RoleType[];
  conditions: string[];
  status: GateStatus;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface ApprovalWorkflow {
  id: string;
  type: ApprovalType;
  name: string;
  threshold_amount?: number;
  required_roles: RoleType[];
  sequence_required: boolean;
  timeout_hours: number;
  auto_escalate: boolean;
  escalation_roles: RoleType[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Template {
  id: string;
  type: TemplateType;
  name: string;
  description: string;
  content: string;
  sections?: string[];
  variables: string[];
  is_default: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Role {
  id: string;
  name: RoleType;
  display_name: string;
  description: string;
  permissions: string[];
  member_count: number;
  can_approve: boolean;
  hierarchy_level: number;
}

export interface LearningCadence {
  id: string;
  name: string;
  frequency: LearningFrequency;
  duration_minutes: number;
  mandatory: boolean;
  target_roles: RoleType[];
  topics: string[];
  reminder_days_before: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FeatureFlag {
  id: string;
  key: string;
  name: string;
  description: string;
  enabled: boolean;
  rollout_percentage: number;
  target_roles?: RoleType[];
  requires_restart: boolean;
  category: FeatureFlagCategory;
  created_at: string;
  updated_at: string;
}

export interface AuditLogEntry {
  id: string;
  created_at: string;
  user_email: string;
  action: string;
  entity_type: string;
  entity_id: string;
  request_id: string;
  ip_address?: string;
  extra_data?: any;
}

export interface AdminStats {
  total_gates: number;
  active_gates: number;
  total_approvals: number;
  active_approvals: number;
  total_templates: number;
  default_templates: number;
  total_roles: number;
  total_users: number;
  total_learning_cadences: number;
  active_learning_cadences: number;
  total_feature_flags: number;
  enabled_features: number;
}

interface AdminState {
  // Data
  gates: Gate[];
  approvals: ApprovalWorkflow[];
  templates: Template[];
  roles: Role[];
  learningCadences: LearningCadence[];
  featureFlags: FeatureFlag[];
  auditLogs: AuditLogEntry[];
  stats: AdminStats | null;
  
  // Loading & Error States
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
  
  // Actions - Gates
  fetchGates: () => Promise<void>;
  fetchGateById: (id: string) => Promise<Gate>;
  createGate: (gate: Omit<Gate, 'id' | 'created_at' | 'updated_at'>) => Promise<Gate>;
  updateGate: (id: string, updates: Partial<Gate>) => Promise<Gate>;
  deleteGate: (id: string) => Promise<void>;
  toggleGateStatus: (id: string) => Promise<void>;
  reorderGates: (gateIds: string[]) => Promise<void>;
  
  // Actions - Approvals
  fetchApprovals: () => Promise<void>;
  fetchApprovalById: (id: string) => Promise<ApprovalWorkflow>;
  createApproval: (approval: Omit<ApprovalWorkflow, 'id' | 'created_at' | 'updated_at'>) => Promise<ApprovalWorkflow>;
  updateApproval: (id: string, updates: Partial<ApprovalWorkflow>) => Promise<ApprovalWorkflow>;
  deleteApproval: (id: string) => Promise<void>;
  toggleApprovalStatus: (id: string) => Promise<void>;
  
  // Actions - Templates
  fetchTemplates: () => Promise<void>;
  fetchTemplateById: (id: string) => Promise<Template>;
  createTemplate: (template: Omit<Template, 'id' | 'created_at' | 'updated_at'>) => Promise<Template>;
  updateTemplate: (id: string, updates: Partial<Template>) => Promise<Template>;
  deleteTemplate: (id: string) => Promise<void>;
  setDefaultTemplate: (id: string) => Promise<void>;
  
  // Actions - Roles
  fetchRoles: () => Promise<void>;
  fetchRoleById: (id: string) => Promise<Role>;
  updateRolePermissions: (id: string, permissions: string[]) => Promise<Role>;
  
  // Actions - Learning
  fetchLearningCadences: () => Promise<void>;
  fetchLearningCadenceById: (id: string) => Promise<LearningCadence>;
  createLearningCadence: (cadence: Omit<LearningCadence, 'id' | 'created_at' | 'updated_at'>) => Promise<LearningCadence>;
  updateLearningCadence: (id: string, updates: Partial<LearningCadence>) => Promise<LearningCadence>;
  deleteLearningCadence: (id: string) => Promise<void>;
  toggleLearningCadenceStatus: (id: string) => Promise<void>;
  
  // Actions - Feature Flags
  fetchFeatureFlags: () => Promise<void>;
  updateFeatureFlag: (id: string, updates: Partial<FeatureFlag>) => Promise<FeatureFlag>;
  toggleFeatureFlag: (id: string) => Promise<void>;
  updateRolloutPercentage: (id: string, percentage: number) => Promise<void>;
  
  // Actions - Audit Logs
  fetchAuditLogs: () => Promise<void>;

  // Actions - Stats
  fetchStats: () => Promise<void>;
  
  // Utility
  clearError: () => void;
}

const CACHE_DURATION = 30000; // 30 seconds
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const useAdminStore = create<AdminState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial State
        gates: [],
        approvals: [],
        templates: [],
        roles: [],
        learningCadences: [],
        featureFlags: [],
        auditLogs: [],
        stats: null,
        isLoading: false,
        error: null,
        lastFetchedAt: null,
        
        // Gates Actions
        fetchGates: async () => {
          const now = Date.now();
          const { lastFetchedAt } = get();
          
          if (lastFetchedAt && now - lastFetchedAt < CACHE_DURATION) {
            return;
          }
          
          set({ isLoading: true, error: null });
          
          try {
            const data = await apiClient.get<any>('/admin/gates');
            
            set({
              gates: data.items || [],
              isLoading: false,
              lastFetchedAt: now,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch gates',
              isLoading: false,
            });
          }
        },
        
        fetchGateById: async (id: string) => {
          set({ isLoading: true, error: null });
          
          try {
            const gate = await apiClient.get<Gate>(`/admin/gates/${id}`);
            
            set({ isLoading: false });
            return gate;
          } catch (error) {
            // Fallback to local cache if API fails
            const cachedGate = get().gates.find(g => g.id === id);
            if (cachedGate) {
              set({ isLoading: false });
              return cachedGate;
            }
            
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch gate',
              isLoading: false,
            });
            throw error;
          }
        },
        
        createGate: async (gateData) => {
          set({ isLoading: true, error: null });
          
          try {
            const newGate = await apiClient.post<Gate>('/admin/gates', gateData);
            
            set((state) => ({
              gates: [...state.gates, newGate],
              isLoading: false,
            }));
            
            return newGate;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create gate',
              isLoading: false,
            });
            throw error;
          }
        },
        
        updateGate: async (id: string, updates: Partial<Gate>) => {
          set({ isLoading: true, error: null });
          
          try {
            const updatedGate = await apiClient.patch<Gate>(`/admin/gates/${id}`, updates);
            
            set((state) => ({
              gates: state.gates.map(g => g.id === id ? updatedGate : g),
              isLoading: false,
            }));
            
            return updatedGate;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update gate',
              isLoading: false,
            });
            throw error;
          }
        },
        
        deleteGate: async (id: string) => {
          set({ isLoading: true, error: null });
          
          try {
            await apiClient.delete(`/admin/gates/${id}`);
            
            set((state) => ({
              gates: state.gates.filter(g => g.id !== id),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete gate',
              isLoading: false,
            });
            throw error;
          }
        },
        
        toggleGateStatus: async (id: string) => {
          const gate = get().gates.find(g => g.id === id);
          if (!gate) return;
          
          const newStatus: GateStatus = gate.status === 'active' ? 'inactive' : 'active';
          await get().updateGate(id, { status: newStatus });
        },
        
        reorderGates: async (gateIds: string[]) => {
          set({ isLoading: true, error: null });
          
          try {
            await apiClient.post('/admin/gates/reorder', { gate_ids: gateIds });
            // await fetch('/api/v1/admin/gates/reorder', {
            //   method: 'POST',
            //   headers: {
            //     'Content-Type': 'application/json',
            //     Authorization: `Bearer ${token}`
            //   },
            //   body: JSON.stringify({ gate_ids: gateIds })
            // });
            
            set((state) => ({
              gates: gateIds
                .map((id, index) => {
                  const gate = state.gates.find(g => g.id === id);
                  return gate ? { ...gate, order: index + 1 } : null;
                })
                .filter(Boolean) as Gate[],
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to reorder gates',
              isLoading: false,
            });
            throw error;
          }
        },
        
        // Approvals Actions
        fetchApprovals: async () => {
          set({ isLoading: true, error: null });
          
          try {
            const data = await apiClient.get<any>('/admin/approvals');
            set({
              approvals: data.items || [],
              isLoading: false,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch approvals',
              isLoading: false,
            });
          }
        },
        
        fetchApprovalById: async (id: string) => {
          const approval = get().approvals.find(a => a.id === id);
          if (!approval) throw new Error('Approval not found');
          return approval;
        },
        
        createApproval: async (approvalData) => {
          set({ isLoading: true, error: null });
          
          try {
            const newApproval = await apiClient.post<ApprovalWorkflow>('/admin/approvals', approvalData);
            
            set((state) => ({
              approvals: [...state.approvals, newApproval],
              isLoading: false,
            }));
            
            return newApproval;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create approval',
              isLoading: false,
            });
            throw error;
          }
        },
        
        updateApproval: async (id: string, updates: Partial<ApprovalWorkflow>) => {
          set({ isLoading: true, error: null });
          
          try {
            const updatedApproval = await apiClient.patch<ApprovalWorkflow>(`/admin/approvals/${id}`, updates);
            
            set((state) => ({
              approvals: state.approvals.map(a => a.id === id ? updatedApproval : a),
              isLoading: false,
            }));
            
            return updatedApproval;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update approval',
              isLoading: false,
            });
            throw error;
          }
        },
        
        deleteApproval: async (id: string) => {
          set({ isLoading: true, error: null });
          
          try {
            await apiClient.delete(`/admin/approvals/${id}`);
            
            set((state) => ({
              approvals: state.approvals.filter(a => a.id !== id),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete approval',
              isLoading: false,
            });
            throw error;
          }
        },
        
        toggleApprovalStatus: async (id: string) => {
          const approval = get().approvals.find(a => a.id === id);
          if (!approval) return;
          
          await get().updateApproval(id, { is_active: !approval.is_active });
        },
        
        // Templates Actions
        fetchTemplates: async () => {
          set({ isLoading: true, error: null });
          
          try {
            const data = await apiClient.get<any>('/admin/templates');
            set({
              templates: data.items || [],
              isLoading: false,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch templates',
              isLoading: false,
            });
          }
        },
        
        fetchTemplateById: async (id: string) => {
          const template = get().templates.find(t => t.id === id);
          if (!template) throw new Error('Template not found');
          return template;
        },
        
        createTemplate: async (templateData) => {
          set({ isLoading: true, error: null });
          
          try {
            const newTemplate = await apiClient.post<Template>('/admin/templates', templateData);
            
            set((state) => ({
              templates: [...state.templates, newTemplate],
              isLoading: false,
            }));
            
            return newTemplate;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create template',
              isLoading: false,
            });
            throw error;
          }
        },
        
        updateTemplate: async (id: string, updates: Partial<Template>) => {
          set({ isLoading: true, error: null });
          
          try {
            const updatedTemplate = await apiClient.patch<Template>(`/admin/templates/${id}`, updates);
            
            set((state) => ({
              templates: state.templates.map(t => t.id === id ? updatedTemplate : t),
              isLoading: false,
            }));
            
            return updatedTemplate;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update template',
              isLoading: false,
            });
            throw error;
          }
        },
        
        deleteTemplate: async (id: string) => {
          set({ isLoading: true, error: null });
          
          try {
            await apiClient.delete(`/admin/templates/${id}`);
            
            set((state) => ({
              templates: state.templates.filter(t => t.id !== id),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete template',
              isLoading: false,
            });
            throw error;
          }
        },
        
        setDefaultTemplate: async (id: string) => {
          const template = get().templates.find(t => t.id === id);
          if (!template) return;
          
          // Unset all other defaults for the same type
          set((state) => ({
            templates: state.templates.map(t =>
              t.type === template.type ? { ...t, is_default: t.id === id } : t
            ),
          }));
        },
        
        // Roles Actions
        fetchRoles: async () => {
          set({ isLoading: true, error: null });
          
          try {
            const data = await apiClient.get<any>('/admin/roles');
            set({
              roles: data.items || [],
              isLoading: false,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch roles',
              isLoading: false,
            });
          }
        },
        
        fetchRoleById: async (id: string) => {
          const role = get().roles.find(r => r.id === id);
          if (!role) throw new Error('Role not found');
          return role;
        },
        
        updateRolePermissions: async (id: string, permissions: string[]) => {
          set({ isLoading: true, error: null });
          
          try {
            const updatedRole = {
              ...get().roles.find(r => r.id === id)!,
              permissions,
            };
            
            set((state) => ({
              roles: state.roles.map(r => r.id === id ? updatedRole : r),
              isLoading: false,
            }));
            
            return updatedRole;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update role',
              isLoading: false,
            });
            throw error;
          }
        },
        
        // Learning Actions
        fetchLearningCadences: async () => {
          set({ isLoading: true, error: null });
          
          try {
            const data = await apiClient.get<any>('/admin/learning-cadences');
            set({
              learningCadences: data.items || [],
              isLoading: false,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch learning cadences',
              isLoading: false,
            });
          }
        },
        
        fetchLearningCadenceById: async (id: string) => {
          const cadence = get().learningCadences.find(c => c.id === id);
          if (!cadence) throw new Error('Learning cadence not found');
          return cadence;
        },
        
        createLearningCadence: async (cadenceData) => {
          set({ isLoading: true, error: null });
          
          try {
            const newCadence = await apiClient.post<LearningCadence>('/admin/learning-cadences', cadenceData);
            
            set((state) => ({
              learningCadences: [...state.learningCadences, newCadence],
              isLoading: false,
            }));
            
            return newCadence;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create learning cadence',
              isLoading: false,
            });
            throw error;
          }
        },
        
        updateLearningCadence: async (id: string, updates: Partial<LearningCadence>) => {
          set({ isLoading: true, error: null });
          
          try {
            const updatedCadence = await apiClient.patch<LearningCadence>(`/admin/learning-cadences/${id}`, updates);
            
            set((state) => ({
              learningCadences: state.learningCadences.map(c => c.id === id ? updatedCadence : c),
              isLoading: false,
            }));
            
            return updatedCadence;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update learning cadence',
              isLoading: false,
            });
            throw error;
          }
        },
        
        deleteLearningCadence: async (id: string) => {
          set({ isLoading: true, error: null });
          
          try {
            await apiClient.delete(`/admin/learning-cadences/${id}`);
            
            set((state) => ({
              learningCadences: state.learningCadences.filter(c => c.id !== id),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete learning cadence',
              isLoading: false,
            });
            throw error;
          }
        },
        
        toggleLearningCadenceStatus: async (id: string) => {
          const cadence = get().learningCadences.find(c => c.id === id);
          if (!cadence) return;
          
          await get().updateLearningCadence(id, { is_active: !cadence.is_active });
        },
        
        // Feature Flags Actions
        fetchFeatureFlags: async () => {
          set({ isLoading: true, error: null });
          
          try {
            const data = await apiClient.get<any>('/admin/feature-flags');
            set({
              featureFlags: data.items || [],
              isLoading: false,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch feature flags',
              isLoading: false,
            });
          }
        },
        
        updateFeatureFlag: async (id: string, updates: Partial<FeatureFlag>) => {
          set({ isLoading: true, error: null });
          
          try {
            const updatedFlag = await apiClient.patch<FeatureFlag>(`/admin/feature-flags/${id}`, updates);
            
            set((state) => ({
              featureFlags: state.featureFlags.map(f => f.id === id ? updatedFlag : f),
              isLoading: false,
            }));
            
            return updatedFlag;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update feature flag',
              isLoading: false,
            });
            throw error;
          }
        },
        
        toggleFeatureFlag: async (id: string) => {
          const flag = get().featureFlags.find(f => f.id === id);
          if (!flag) return;
          
          await get().updateFeatureFlag(id, { enabled: !flag.enabled });
        },
        
        updateRolloutPercentage: async (id: string, percentage: number) => {
          await get().updateFeatureFlag(id, { rollout_percentage: percentage });
        },
        
        // Audit Logs Actions
        fetchAuditLogs: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<any>('/audit-logs');
            set({ auditLogs: data.items || [], isLoading: false });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch audit logs',
              isLoading: false,
            });
          }
        },
        
        // Stats Actions
        fetchStats: async () => {
          set({ isLoading: true, error: null });
          
          try {
            const data = await apiClient.get<any>('/admin/stats');
            set({ stats: data, isLoading: false });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch admin stats',
              isLoading: false,
            });
          }
        },
        
        // Utility
        clearError: () => set({ error: null }),
      }),
      {
        name: 'admin-storage',
        partialize: (state) => ({
          gates: state.gates,
          approvals: state.approvals,
          templates: state.templates,
          roles: state.roles,
          learningCadences: state.learningCadences,
          featureFlags: state.featureFlags,
        }),
      }
    )
  )
);
