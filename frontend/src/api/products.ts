import { apiClient, PaginationParams, ApiResponse } from './client';

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

export const productApi = {
  listProducts: (params?: ProductListParams) => 
    apiClient.get<ApiResponse<Product[]>>('/products', { params }),
  
  getProduct: (id: number) => 
    apiClient.get<ApiResponse<ProductDetail>>(`/products/${id}`),
  
  createProduct: (data: Partial<ProductDetail>) => 
    apiClient.post<ApiResponse<ProductDetail>>('/products', data),
  
  updateProduct: (id: number, data: Partial<ProductDetail>) => 
    apiClient.patch<ApiResponse<ProductDetail>>(`/products/${id}`, data),
  
  deleteProduct: (id: number) => 
    apiClient.delete<ApiResponse<void>>(`/products/${id}`),
    
  getProductStats: (id: number) =>
    apiClient.get<ApiResponse<any>>(`/products/${id}/stats`),
};
