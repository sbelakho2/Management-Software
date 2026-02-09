import { create } from 'zustand';
import { accountApi, AccountListParams, CreateAccountData } from '@/api/accounts';
import { Customer } from '@/types';

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return 'An unexpected error occurred';
}

interface CustomersState {
  customers: Customer[];
  totalCustomers: number;
  loading: boolean;
  error: string | null;

  fetchCustomers: (params?: AccountListParams) => Promise<void>;
  createCustomer: (data: Partial<Customer> | CreateAccountData) => Promise<Customer>;
  updateCustomer: (id: string, data: Partial<Customer>) => Promise<Customer>;
  deleteCustomer: (id: string) => Promise<void>;
  clearError: () => void;
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
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },

  createCustomer: async (data) => {
    set({ loading: true, error: null });
    try {
      const customer = await accountApi.create(data as CreateAccountData);
      set((state) => ({ 
        customers: [customer, ...state.customers],
        totalCustomers: state.totalCustomers + 1,
        loading: false 
      }));
      return customer;
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
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
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
      throw error;
    }
  },

  deleteCustomer: async (id) => {
    set({ loading: true, error: null });
    try {
      await accountApi.delete(id);
      set((state) => ({
        customers: state.customers.filter((c) => c.id !== id),
        totalCustomers: state.totalCustomers - 1,
        loading: false,
      }));
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));
