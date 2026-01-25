import { create } from 'zustand';
import { productApi, Product, ProductDetail, ProductListParams } from '@/api/products';
import { getErrorMessage } from '@/lib/error-utils';

interface ProductState {
  products: Product[];
  totalProducts: number;
  currentProduct: ProductDetail | null;
  loading: boolean;
  error: string | null;

  fetchProducts: (params?: ProductListParams) => Promise<void>;
  fetchProduct: (id: number) => Promise<void>;
  createProduct: (data: Partial<ProductDetail>) => Promise<void>;
  updateProduct: (id: number, data: Partial<ProductDetail>) => Promise<void>;
  deleteProduct: (id: number) => Promise<void>;
}

export const useProductStore = create<ProductState>((set, get) => ({
  products: [],
  totalProducts: 0,
  currentProduct: null,
  loading: false,
  error: null,

  fetchProducts: async (params) => {
    set({ loading: true, error: null });
    try {
      // productApi returns unwrapped data directly (Product[])
      const products = await productApi.listProducts(params);
      set({ 
        products: products, 
        totalProducts: products.length,
        loading: false 
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  fetchProduct: async (id) => {
    set({ loading: true, error: null });
    try {
      // productApi returns unwrapped data directly (ProductDetail)
      const product = await productApi.getProduct(id);
      set({ currentProduct: product, loading: false });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createProduct: async (data) => {
    set({ loading: true, error: null });
    try {
      await productApi.createProduct(data);
      await get().fetchProducts();
      set({ loading: false });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
      throw error;
    }
  },

  updateProduct: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await productApi.updateProduct(id, data);
      await get().fetchProducts();
      if (get().currentProduct?.id === id) {
        await get().fetchProduct(id);
      }
      set({ loading: false });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
      throw error;
    }
  },

  deleteProduct: async (id) => {
    set({ loading: true, error: null });
    try {
      await productApi.deleteProduct(id);
      await get().fetchProducts();
      set({ loading: false });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
      throw error;
    }
  },
}));
