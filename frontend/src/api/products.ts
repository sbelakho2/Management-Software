import { apiClient, PaginationParams } from './client';

export interface Product {
  id: number;
  name: string;
  part_number: string;
  revision: string;
  full_part_number: string;
  product_family?: string;
  product_category?: string;
  status: string;
  standard_cost?: number;
  lead_time_days: number;
  created_at: string;
}

export interface ProductDetail extends Product {
  description?: string;
  unit_of_measure: string;
  weight_kg?: number;
  dimensions?: string;
  standard_labor_hours?: number;
  setup_time_hours?: number;
  list_price?: number;
  reorder_point?: number;
  is_active: boolean;
  bom_item_count: number;
  routing_step_count: number;
  updated_at: string;
}

export interface ProductListParams extends PaginationParams {
  search?: string;
  product_family?: string;
  product_category?: string;
  status?: string;
}

// Note: apiClient.unwrapResponse() extracts the 'data' field from { success, data, ... } responses
// So these methods return the unwrapped data directly
export const productApi = {
  listProducts: (params?: ProductListParams): Promise<Product[]> => 
    apiClient.get<Product[]>('/products', { params }),
  
  getProduct: (id: number): Promise<ProductDetail> => 
    apiClient.get<ProductDetail>(`/products/${id}`),
  
  createProduct: (data: Partial<ProductDetail>): Promise<ProductDetail> => 
    apiClient.post<ProductDetail>('/products', data),
  
  updateProduct: (id: number, data: Partial<ProductDetail>): Promise<ProductDetail> => 
    apiClient.patch<ProductDetail>(`/products/${id}`, data),
  
  deleteProduct: (id: number): Promise<void> => 
    apiClient.delete<void>(`/products/${id}`),
    
  getProductStats: (id: number): Promise<any> =>
    apiClient.get<any>(`/products/${id}/stats`),
};
