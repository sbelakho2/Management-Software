import { apiClient } from './client';

export interface Asset {
  id: string;
  asset_number: string;
  name: string;
  asset_type: string;
  status: string;
  criticality: string;
  location_id?: string;
  work_center_id?: string;
  parent_asset_id?: string;
  meter_reading: number;
  meter_unit: string;
  last_pm_date?: string;
  next_pm_date?: string;
}

export interface MaintenanceWorkOrder {
  id: string;
  work_order_number: string;
  asset_id: string;
  work_order_type: string;
  status: string;
  priority: number;
  description?: string;
  assigned_to?: string;
  scheduled_start?: string;
  scheduled_end?: string;
  created_at: string;
  approval_status?: string;
  approval_requested_at?: string;
  approved_by_id?: string;
  approved_at?: string;
  approval_notes?: string;
}

export interface MaintenanceStats {
  total_assets: number;
  assets_by_status: Record<string, number>;
  assets_by_criticality: Record<string, number>;
  total_pm_schedules: number;
  active_pm_schedules: number;
  overdue_pms: number;
  total_work_orders: number;
  work_orders_by_status: Record<string, number>;
  total_downtime_events: number;
  total_spare_parts: number;
  parts_below_reorder: number;
}

export interface LOTOEnergySource {
  id: string;
  procedure_id: string;
  source_type: string;
  isolation_point: string;
  lock_required: boolean;
  verification_steps?: any[];
  notes?: string;
}

export interface LOTOProcedure {
  id: string;
  asset_id: string;
  title: string;
  description?: string;
  status: string;
  requires_verification: boolean;
  version: string;
  energy_sources: LOTOEnergySource[];
}

export interface LOTOLock {
  id: string;
  procedure_id: string;
  asset_id: string;
  work_order_id?: string;
  lock_number: string;
  status: string;
  reason?: string;
  applied_by_id: string;
  applied_at: string;
  released_by_id?: string;
  released_at?: string;
  verification_required: boolean;
  verified_by_id?: string;
  verified_at?: string;
  verification_notes?: string;
}

export interface ToolItem {
  id: string;
  tool_number: string;
  name: string;
  description?: string;
  category?: string;
  status: string;
  location_id?: string;
  quantity_on_hand: number;
  min_quantity: number;
  life_limit_cycles?: number;
  life_used_cycles: number;
  calibration_due_at?: string;
}

export interface ToolCheckout {
  id: string;
  tool_id: string;
  work_order_id?: string;
  checked_out_by_id: string;
  checked_out_at: string;
  due_back_at?: string;
  returned_by_id?: string;
  returned_at?: string;
  condition_out?: string;
  condition_in?: string;
  notes?: string;
}

export interface WarrantyClaim {
  id: string;
  warranty_id: string;
  asset_id: string;
  work_order_id?: string;
  claim_number: string;
  status: string;
  claim_amount?: number;
  approved_amount?: number;
  submitted_at: string;
  resolved_at?: string;
  notes?: string;
}

export interface AssetWarranty {
  id: string;
  asset_id: string;
  warranty_type: string;
  provider_name?: string;
  vendor_id?: string;
  start_date: string;
  end_date: string;
  coverage_type: string;
  status: string;
  terms?: string;
  claim_contact?: string;
  claims: WarrantyClaim[];
}

export interface FieldReturn {
  id: string;
  asset_id: string;
  warranty_id?: string;
  claim_id?: string;
  customer_id?: string;
  return_number: string;
  status: string;
  failure_date?: string;
  received_at: string;
  defect_code?: string;
  failure_mode?: string;
  root_cause?: string;
  corrective_action?: string;
  cost_impact?: number;
  notes?: string;
}

export interface MaintenanceBudget {
  id: string;
  name: string;
  period_start: string;
  period_end: string;
  budget_amount: number;
  actual_amount: number;
  variance_amount: number;
  currency: string;
  notes?: string;
}

export const maintenanceApi = {
  getStats: (): Promise<MaintenanceStats> => 
    apiClient.get('/maintenance/stats'),
  
  listAssets: (): Promise<Asset[]> => 
    apiClient.get('/maintenance/assets'),
  
  getAsset: (id: string): Promise<Asset> => 
    apiClient.get(`/maintenance/assets/${id}`),
  
  listWorkOrders: (): Promise<MaintenanceWorkOrder[]> => 
    apiClient.get('/maintenance/work-orders'),

  requestWorkOrderApproval: (workOrderId: string): Promise<MaintenanceWorkOrder> =>
    apiClient.post(`/maintenance/work-orders/${workOrderId}/approval/request`, {}),

  approveWorkOrder: (workOrderId: string, payload: { notes?: string }): Promise<MaintenanceWorkOrder> =>
    apiClient.post(`/maintenance/work-orders/${workOrderId}/approval/approve`, payload),

  rejectWorkOrder: (workOrderId: string, payload: { notes?: string }): Promise<MaintenanceWorkOrder> =>
    apiClient.post(`/maintenance/work-orders/${workOrderId}/approval/reject`, payload),
  
  listOverduePMs: (): Promise<any[]> => 
    apiClient.get('/maintenance/overdue-pms'),

  listPMSchedules: (): Promise<any[]> =>
    apiClient.get('/maintenance/pm-schedules'),

  getPMRoute: (daysAhead: number = 7): Promise<any[]> =>
    apiClient.get(`/maintenance/pm-route?days_ahead=${daysAhead}`),

  listLotoProcedures: (): Promise<LOTOProcedure[]> =>
    apiClient.get('/maintenance/loto/procedures'),

  getLotoProcedure: (id: string): Promise<LOTOProcedure> =>
    apiClient.get(`/maintenance/loto/procedures/${id}`),

  createLotoProcedure: (payload: Partial<LOTOProcedure> & { asset_id: string; title: string }): Promise<LOTOProcedure> =>
    apiClient.post('/maintenance/loto/procedures', payload),

  listActiveLotoLocks: (): Promise<LOTOLock[]> =>
    apiClient.get('/maintenance/loto/locks/active'),

  createLotoLock: (payload: { procedure_id: string; asset_id: string; lock_number: string; reason?: string; work_order_id?: string; verification_required?: boolean }): Promise<LOTOLock> =>
    apiClient.post('/maintenance/loto/locks', payload),

  verifyLotoLock: (lockId: string, payload: { verification_notes?: string }): Promise<LOTOLock> =>
    apiClient.post(`/maintenance/loto/locks/${lockId}/verify`, payload),

  releaseLotoLock: (lockId: string, payload: { verification_notes?: string }): Promise<LOTOLock> =>
    apiClient.post(`/maintenance/loto/locks/${lockId}/release`, payload),

  listTools: (): Promise<ToolItem[]> =>
    apiClient.get('/maintenance/tools'),

  getTool: (id: string): Promise<ToolItem> =>
    apiClient.get(`/maintenance/tools/${id}`),

  createTool: (payload: Partial<ToolItem> & { tool_number: string; name: string }): Promise<ToolItem> =>
    apiClient.post('/maintenance/tools', payload),

  listActiveToolCheckouts: (): Promise<ToolCheckout[]> =>
    apiClient.get('/maintenance/tools/checkouts/active'),

  checkoutTool: (payload: { tool_id: string; work_order_id?: string; due_back_at?: string; condition_out?: string; notes?: string }): Promise<ToolCheckout> =>
    apiClient.post('/maintenance/tools/checkouts', payload),

  returnTool: (checkoutId: string, payload: { condition_in?: string; notes?: string }): Promise<ToolCheckout> =>
    apiClient.post(`/maintenance/tools/checkouts/${checkoutId}/return`, payload),

  listWarranties: (): Promise<AssetWarranty[]> =>
    apiClient.get('/maintenance/warranties'),

  getWarranty: (id: string): Promise<AssetWarranty> =>
    apiClient.get(`/maintenance/warranties/${id}`),

  createWarranty: (payload: Partial<AssetWarranty> & { asset_id: string; warranty_type: string; start_date: string; end_date: string }): Promise<AssetWarranty> =>
    apiClient.post('/maintenance/warranties', payload),

  fileWarrantyClaim: (warrantyId: string, payload: { asset_id: string; claim_number: string; work_order_id?: string; claim_amount?: number; notes?: string }): Promise<WarrantyClaim> =>
    apiClient.post(`/maintenance/warranties/${warrantyId}/claims`, payload),

  resolveWarrantyClaim: (claimId: string, payload: { status?: string; approved_amount?: number; notes?: string }): Promise<WarrantyClaim> =>
    apiClient.post(`/maintenance/warranties/claims/${claimId}/resolve`, payload),

  listFieldReturns: (): Promise<FieldReturn[]> =>
    apiClient.get('/maintenance/field-returns'),

  createFieldReturn: (payload: Partial<FieldReturn> & { asset_id: string; return_number: string }): Promise<FieldReturn> =>
    apiClient.post('/maintenance/field-returns', payload),

  updateFieldReturn: (returnId: string, payload: Partial<FieldReturn>): Promise<FieldReturn> =>
    apiClient.patch(`/maintenance/field-returns/${returnId}`, payload),

  closeFieldReturn: (returnId: string): Promise<FieldReturn> =>
    apiClient.post(`/maintenance/field-returns/${returnId}/close`),

  listMaintenanceBudgets: (): Promise<MaintenanceBudget[]> =>
    apiClient.get('/maintenance/budgets'),

  createMaintenanceBudget: (payload: Partial<MaintenanceBudget> & { name: string; period_start: string; period_end: string; budget_amount: number }): Promise<MaintenanceBudget> =>
    apiClient.post('/maintenance/budgets', payload),

  updateMaintenanceBudgetActuals: (budgetId: string, payload: { actual_amount: number }): Promise<MaintenanceBudget> =>
    apiClient.post(`/maintenance/budgets/${budgetId}/actuals`, payload),
};
