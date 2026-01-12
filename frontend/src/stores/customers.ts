import { create } from 'zustand';
import { accountApi, AccountListParams } from '@/api/accounts';
import { Customer } from '@/types';

interface CustomersState {
  customers: Customer[];
  totalCustomers: number;
  loading: boolean;
  error: string | null;

  fetchCustomers: (params?: AccountListParams) => Promise<void>;
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
      set({ 
        customers: response.items, 
        totalCustomers: response.total,
        loading: false 
      });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },
}));
