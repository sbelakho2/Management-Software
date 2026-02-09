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
  /** @deprecated Use loadingOps for per-operation states */
  isLoading: boolean;
  /** Set of currently in-progress operation names */
  loadingOps: Set<string>;
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
  /** Check if a specific operation is in progress */
  isOpLoading: (op: string) => boolean;
}

const CACHE_DURATION = 30000; // 30 seconds
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';


/* ── Per-operation loading helpers ─────────────────────────────────── */
function startOp(set: (fn: (s: AdminState) => Partial<AdminState>) => void, op: string) {
  set((s) => {
    const next = new Set(s.loadingOps);
    next.add(op);
    return { loadingOps: next, isLoading: true, error: null };
  });
}
function endOp(set: (fn: (s: AdminState) => Partial<AdminState>) => void, op: string) {
  set((s) => {
    const next = new Set(s.loadingOps);
    next.delete(op);
    return { loadingOps: next, isLoading: next.size > 0 };
  });
}

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
  loadingOps: new Set<string>(),
        error: null,
        lastFetchedAt: null,
        
        // Gates Actions
        fetchGates: async () => {
          const now = Date.now();
          const { lastFetchedAt, isLoading } = get();

          if (isLoading) {
            return;
          }
          
          if (lastFetchedAt && now - lastFetchedAt < CACHE_DURATION) {
            return;
          }
          
          startOp(set, 'fetchGates');
          
          try {
            const data = await apiClient.get<any>('/admin/gates');
            
            set({
              gates: data.items || [],
              lastFetchedAt: now,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch gates',
            });
          }
            finally {
              endOp(set, 'fetchGates');
            }
        },
        
        fetchGateById: async (id: string) => {
          startOp(set, 'fetchGateById');
          
          try {
            const gate = await apiClient.get<Gate>(`/admin/gates/${id}`);
            
            set({  });
            return gate;
          } catch (error) {
            // Fallback to local cache if API fails
            const cachedGate = get().gates.find(g => g.id === id);
            if (cachedGate) {
              set({  });
              return cachedGate;
            }
            
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch gate',
            });
            throw error;
          }
            finally {
              endOp(set, 'fetchGateById');
            }
        },
        
        createGate: async (gateData) => {
          startOp(set, 'createGate');
          
          try {
            const newGate = await apiClient.post<Gate>('/admin/gates', gateData);
            
            set((state) => ({
              gates: [...state.gates, newGate],
            }));
            
            return newGate;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create gate',
            });
            throw error;
          }
            finally {
              endOp(set, 'createGate');
            }
        },
        
        updateGate: async (id: string, updates: Partial<Gate>) => {
          startOp(set, 'updateGate');
          
          try {
            const updatedGate = await apiClient.patch<Gate>(`/admin/gates/${id}`, updates);
            
            set((state) => ({
              gates: state.gates.map(g => g.id === id ? updatedGate : g),
            }));
            
            return updatedGate;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update gate',
            });
            throw error;
          }
            finally {
              endOp(set, 'updateGate');
            }
        },
        
        deleteGate: async (id: string) => {
          startOp(set, 'deleteGate');
          
          try {
            await apiClient.delete(`/admin/gates/${id}`);
            
            set((state) => ({
              gates: state.gates.filter(g => g.id !== id),
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete gate',
            });
            throw error;
          }
            finally {
              endOp(set, 'deleteGate');
            }
        },
        
        toggleGateStatus: async (id: string) => {
          const gate = get().gates.find(g => g.id === id);
          if (!gate) return;
          
          const newStatus: GateStatus = gate.status === 'active' ? 'inactive' : 'active';
          await get().updateGate(id, { status: newStatus });
        },
        
        reorderGates: async (gateIds: string[]) => {
          startOp(set, 'reorderGates');
          
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
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to reorder gates',
            });
            throw error;
          }
            finally {
              endOp(set, 'reorderGates');
            }
        },
        
        // Approvals Actions
        fetchApprovals: async () => {
          startOp(set, 'fetchApprovals');
          
          try {
            const data = await apiClient.get<any>('/admin/approvals');
            set({
              approvals: data.items || [],
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch approvals',
            });
          }
            finally {
              endOp(set, 'fetchApprovals');
            }
        },
        
        fetchApprovalById: async (id: string) => {
          const approval = get().approvals.find(a => a.id === id);
          if (!approval) throw new Error('Approval not found');
          return approval;
        },
        
        createApproval: async (approvalData) => {
          startOp(set, 'createApproval');
          
          try {
            const newApproval = await apiClient.post<ApprovalWorkflow>('/admin/approvals', approvalData);
            
            set((state) => ({
              approvals: [...state.approvals, newApproval],
            }));
            
            return newApproval;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create approval',
            });
            throw error;
          }
            finally {
              endOp(set, 'createApproval');
            }
        },
        
        updateApproval: async (id: string, updates: Partial<ApprovalWorkflow>) => {
          startOp(set, 'updateApproval');
          
          try {
            const updatedApproval = await apiClient.patch<ApprovalWorkflow>(`/admin/approvals/${id}`, updates);
            
            set((state) => ({
              approvals: state.approvals.map(a => a.id === id ? updatedApproval : a),
            }));
            
            return updatedApproval;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update approval',
            });
            throw error;
          }
            finally {
              endOp(set, 'updateApproval');
            }
        },
        
        deleteApproval: async (id: string) => {
          startOp(set, 'deleteApproval');
          
          try {
            await apiClient.delete(`/admin/approvals/${id}`);
            
            set((state) => ({
              approvals: state.approvals.filter(a => a.id !== id),
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete approval',
            });
            throw error;
          }
            finally {
              endOp(set, 'deleteApproval');
            }
        },
        
        toggleApprovalStatus: async (id: string) => {
          const approval = get().approvals.find(a => a.id === id);
          if (!approval) return;
          
          await get().updateApproval(id, { is_active: !approval.is_active });
        },
        
        // Templates Actions
        fetchTemplates: async () => {
          startOp(set, 'fetchTemplates');
          
          try {
            const data = await apiClient.get<any>('/admin/templates');
            set({
              templates: data.items || [],
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch templates',
            });
          }
            finally {
              endOp(set, 'fetchTemplates');
            }
        },
        
        fetchTemplateById: async (id: string) => {
          const template = get().templates.find(t => t.id === id);
          if (!template) throw new Error('Template not found');
          return template;
        },
        
        createTemplate: async (templateData) => {
          startOp(set, 'createTemplate');
          
          try {
            const newTemplate = await apiClient.post<Template>('/admin/templates', templateData);
            
            set((state) => ({
              templates: [...state.templates, newTemplate],
            }));
            
            return newTemplate;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create template',
            });
            throw error;
          }
            finally {
              endOp(set, 'createTemplate');
            }
        },
        
        updateTemplate: async (id: string, updates: Partial<Template>) => {
          startOp(set, 'updateTemplate');
          
          try {
            const updatedTemplate = await apiClient.patch<Template>(`/admin/templates/${id}`, updates);
            
            set((state) => ({
              templates: state.templates.map(t => t.id === id ? updatedTemplate : t),
            }));
            
            return updatedTemplate;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update template',
            });
            throw error;
          }
            finally {
              endOp(set, 'updateTemplate');
            }
        },
        
        deleteTemplate: async (id: string) => {
          startOp(set, 'deleteTemplate');
          
          try {
            await apiClient.delete(`/admin/templates/${id}`);
            
            set((state) => ({
              templates: state.templates.filter(t => t.id !== id),
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete template',
            });
            throw error;
          }
            finally {
              endOp(set, 'deleteTemplate');
            }
        },
        
        setDefaultTemplate: async (id: string) => {
          const template = get().templates.find(t => t.id === id);
          if (!template) return;
          
          try {
            await apiClient.patch(`/admin/templates/${id}`, { is_default: true });
            
            // Unset all other defaults for the same type
            set((state) => ({
              templates: state.templates.map(t =>
                t.type === template.type ? { ...t, is_default: t.id === id } : t
              ),
            }));
          } catch (error) {
            console.error('Failed to set default template:', error);
          }
        },
        
        // Roles Actions
        fetchRoles: async () => {
          startOp(set, 'fetchRoles');
          
          try {
            const data = await apiClient.get<any>('/admin/roles');
            set({
              roles: data.items || [],
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch roles',
            });
          }
            finally {
              endOp(set, 'fetchRoles');
            }
        },
        
        fetchRoleById: async (id: string) => {
          const role = get().roles.find(r => r.id === id);
          if (!role) throw new Error('Role not found');
          return role;
        },
        
        updateRolePermissions: async (id: string, permissions: string[]) => {
          startOp(set, 'updateRolePermissions');
          
          try {
            const updatedRole = {
              ...get().roles.find(r => r.id === id)!,
              permissions,
            };
            
            set((state) => ({
              roles: state.roles.map(r => r.id === id ? updatedRole : r),
            }));
            
            return updatedRole;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update role',
            });
            throw error;
          }
            finally {
              endOp(set, 'updateRolePermissions');
            }
        },
        
        // Learning Actions
        fetchLearningCadences: async () => {
          startOp(set, 'fetchLearningCadences');
          
          try {
            const data = await apiClient.get<any>('/admin/learning-cadences');
            set({
              learningCadences: data.items || [],
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch learning cadences',
            });
          }
            finally {
              endOp(set, 'fetchLearningCadences');
            }
        },
        
        fetchLearningCadenceById: async (id: string) => {
          const cadence = get().learningCadences.find(c => c.id === id);
          if (!cadence) throw new Error('Learning cadence not found');
          return cadence;
        },
        
        createLearningCadence: async (cadenceData) => {
          startOp(set, 'createLearningCadence');
          
          try {
            const newCadence = await apiClient.post<LearningCadence>('/admin/learning-cadences', cadenceData);
            
            set((state) => ({
              learningCadences: [...state.learningCadences, newCadence],
            }));
            
            return newCadence;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create learning cadence',
            });
            throw error;
          }
            finally {
              endOp(set, 'createLearningCadence');
            }
        },
        
        updateLearningCadence: async (id: string, updates: Partial<LearningCadence>) => {
          startOp(set, 'updateLearningCadence');
          
          try {
            const updatedCadence = await apiClient.patch<LearningCadence>(`/admin/learning-cadences/${id}`, updates);
            
            set((state) => ({
              learningCadences: state.learningCadences.map(c => c.id === id ? updatedCadence : c),
            }));
            
            return updatedCadence;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update learning cadence',
            });
            throw error;
          }
            finally {
              endOp(set, 'updateLearningCadence');
            }
        },
        
        deleteLearningCadence: async (id: string) => {
          startOp(set, 'deleteLearningCadence');
          
          try {
            await apiClient.delete(`/admin/learning-cadences/${id}`);
            
            set((state) => ({
              learningCadences: state.learningCadences.filter(c => c.id !== id),
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete learning cadence',
            });
            throw error;
          }
            finally {
              endOp(set, 'deleteLearningCadence');
            }
        },
        
        toggleLearningCadenceStatus: async (id: string) => {
          const cadence = get().learningCadences.find(c => c.id === id);
          if (!cadence) return;
          
          await get().updateLearningCadence(id, { is_active: !cadence.is_active });
        },
        
        // Feature Flags Actions
        fetchFeatureFlags: async () => {
          startOp(set, 'fetchFeatureFlags');
          
          try {
            const data = await apiClient.get<any>('/admin/feature-flags');
            set({
              featureFlags: data.items || [],
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch feature flags',
            });
          }
            finally {
              endOp(set, 'fetchFeatureFlags');
            }
        },
        
        updateFeatureFlag: async (id: string, updates: Partial<FeatureFlag>) => {
          startOp(set, 'updateFeatureFlag');
          
          try {
            const updatedFlag = await apiClient.patch<FeatureFlag>(`/admin/feature-flags/${id}`, updates);
            
            set((state) => ({
              featureFlags: state.featureFlags.map(f => f.id === id ? updatedFlag : f),
            }));
            
            return updatedFlag;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update feature flag',
            });
            throw error;
          }
            finally {
              endOp(set, 'updateFeatureFlag');
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
          startOp(set, 'fetchAuditLogs');
          try {
            const data = await apiClient.get<any>('/audit-logs');
            set({ auditLogs: data.items || [] });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch audit logs',
            });
          }
            finally {
              endOp(set, 'fetchAuditLogs');
            }
        },
        
        // Stats Actions
        fetchStats: async () => {
          startOp(set, 'fetchStats');
          
          try {
            const data = await apiClient.get<any>('/admin/stats');
            set({ stats: data });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch admin stats',
            });
          }
            finally {
              endOp(set, 'fetchStats');
            }
        },
        
        // Utility
        clearError: () => set({ error: null }),
        isOpLoading: (op: string) => get().loadingOps.has(op),
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
