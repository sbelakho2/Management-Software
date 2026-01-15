import { apiClient, type PaginationParams } from './client';
import type { PaginatedResponse } from '@/types';

export enum WorkOrderStatus {
  DRAFT = 'draft',
  RELEASED = 'released',
  IN_PROGRESS = 'in_progress',
  ON_HOLD = 'on_hold',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  CLOSED = 'closed',
}

export enum WorkOrderPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
  CRITICAL = 'critical',
}

export interface WorkOrder {
  id: number;
  work_order_number: string;
  external_reference?: string;
  product_id: number;
  product_name?: string;
  part_number?: string;
  quantity_ordered: number;
  quantity_completed: number;
  quantity_scrapped: number;
  quantity_in_progress?: number;
  quantity_remaining?: number;
  completion_percentage?: number;
  yield_percentage?: number;
  status: WorkOrderStatus;
  priority: WorkOrderPriority;
  hold_reason?: string;
  hold_notes?: string;
  held_at?: string;
  held_by_id?: string;
  work_center_id?: number;
  work_center_name?: string;
  current_station_id?: number;
  current_operation_sequence?: number;
  assigned_to_name?: string;
  scheduled_start?: string;
  scheduled_end?: string;
  actual_start?: string;
  actual_end?: string;
  lot_number?: string;
  batch_id?: string;
  notes?: string;
  production_notes?: string;
  jidoka_suggestions?: JidokaSuggestion[];
  is_late: boolean;
  is_on_hold: boolean;
  operation_count: number;
  created_at: string;
  updated_at: string;
  created_by_id?: string;
  updated_by_id?: string;
}

export interface JidokaSuggestion {
  title: string;
  rationale: string;
  actions: string[];
  related_non_conformance_ids: number[];
  confidence: number;
}

export interface WorkOrderFilters extends PaginationParams {
  status?: WorkOrderStatus;
  priority?: WorkOrderPriority;
  work_center_id?: number;
  assigned_to?: number;
  search?: string;
}

export interface CreateWorkOrderData {
  work_order_number: string;
  external_reference?: string;
  quote_id?: string;
  product_id: number;
  quantity_ordered: number;
  priority?: WorkOrderPriority;
  status?: WorkOrderStatus;
  work_center_id?: number;
  scheduled_start?: string;
  scheduled_end?: string;
  lot_number?: string;
  batch_id?: string;
  notes?: string;
  production_notes?: string;
}

export interface UpdateWorkOrderData {
  work_order_number?: string;
  external_reference?: string;
  quantity_ordered?: number;
  priority?: WorkOrderPriority;
  status?: WorkOrderStatus;
  work_center_id?: number;
  current_station_id?: number;
  scheduled_start?: string;
  scheduled_end?: string;
  actual_start?: string;
  actual_end?: string;
  lot_number?: string;
  batch_id?: string;
  notes?: string;
  production_notes?: string;
}

export interface ProductionStats {
  total_work_orders: number;
  in_progress: number;
  completed_today: number;
  on_hold: number;
  overdue: number;
  efficiency_rate: number;
  oee: number;
}

export const productionApi = {
  listWorkOrders: (params?: WorkOrderFilters): Promise<PaginatedResponse<WorkOrder>> => 
    apiClient.get('/work-orders', { params }),
  
  getWorkOrder: (id: number): Promise<WorkOrder> => 
    apiClient.get(`/work-orders/${id}`),
  
  createWorkOrder: (data: CreateWorkOrderData): Promise<WorkOrder> => 
    apiClient.post('/work-orders', data),
  
  updateWorkOrder: (id: number, data: UpdateWorkOrderData): Promise<WorkOrder> => 
    apiClient.patch(`/work-orders/${id}`, data),
  
  getStats: (): Promise<ProductionStats> => 
    apiClient.get('/work-orders/stats'),
};
