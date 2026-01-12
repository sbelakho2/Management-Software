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

export const maintenanceApi = {
  getStats: (): Promise<MaintenanceStats> => 
    apiClient.get('/maintenance/stats'),
  
  listAssets: (): Promise<Asset[]> => 
    apiClient.get('/maintenance/assets'),
  
  getAsset: (id: string): Promise<Asset> => 
    apiClient.get(`/maintenance/assets/${id}`),
  
  listWorkOrders: (): Promise<MaintenanceWorkOrder[]> => 
    apiClient.get('/maintenance/work-orders'),
  
  listOverduePMs: (): Promise<any[]> => 
    apiClient.get('/maintenance/overdue-pms'),
};
