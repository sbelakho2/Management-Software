import { apiClient } from './client';
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
  status: WorkOrderStatus;
  priority: WorkOrderPriority;
  work_center_id?: number;
  work_center_name?: string;
  assigned_to_name?: string;
  scheduled_start?: string;
  scheduled_end?: string;
  actual_start?: string;
  actual_end?: string;
  created_at: string;
}

export const productionApi = {
  listWorkOrders: (params?: any): Promise<PaginatedResponse<WorkOrder>> => 
    apiClient.get('/work-orders', { params }),
  
  getWorkOrder: (id: number): Promise<WorkOrder> => 
    apiClient.get(`/work-orders/${id}`),
  
  createWorkOrder: (data: any): Promise<WorkOrder> => 
    apiClient.post('/work-orders', data),
  
  updateWorkOrder: (id: number, data: any): Promise<WorkOrder> => 
    apiClient.patch(`/work-orders/${id}`, data),
  
  getStats: (): Promise<any> => 
    apiClient.get('/work-orders/stats'),
};
