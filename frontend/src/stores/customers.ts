import { create } from 'zustand';
import { accountApi, AccountListParams } from '@/api/accounts';
import { Customer } from '@/types';

interface CustomersState {
  customers: Customer[];
  totalCustomers: number;
  loading: boolean;
  error: string | null;

  fetchCustomers: (params?: AccountListParams) => Promise<void>;
  createCustomer: (data: any) => Promise<Customer>;
  updateCustomer: (id: string, data: any) => Promise<Customer>;
}

export const useCustomersStore = create<CustomersState>((set) => ({
  customers: [],
  totalCustomers: 0,
  loading: false,
  error: null,

  fetchCustomers: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await accountApi.list(params);
      const items = Array.isArray(response.items) ? response.items : [];
      const total = typeof response.total === 'number' ? response.total : items.length;
      set({ 
        customers: items,
        totalCustomers: total,
        loading: false 
      });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createCustomer: async (data) => {
    set({ loading: true, error: null });
    try {
      const customer = await accountApi.create(data);
      set((state) => ({ 
        customers: [customer, ...state.customers],
        totalCustomers: state.totalCustomers + 1,
        loading: false 
      }));
      return customer;
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  updateCustomer: async (id, data) => {
    set({ loading: true, error: null });
    try {
      const customer = await accountApi.update(id, data);
      set((state) => ({ 
        customers: state.customers.map((c) => (c.id === id ? customer : c)),
        loading: false 
      }));
      return customer;
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },
}));
