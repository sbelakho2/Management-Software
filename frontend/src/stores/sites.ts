import { create } from 'zustand';
import { apiClient } from '@/api/client';
import type { Site } from '@/types';

interface SitesState {
  sites: Site[];
  loading: boolean;
  error: string | null;

  fetchSites: () => Promise<void>;
  createSite: (payload: Partial<Site> & { site_code: string; name: string }) => Promise<void>;
  updateSite: (id: string, payload: Partial<Site>) => Promise<void>;
}

export const useSitesStore = create<SitesState>((set, get) => ({
  sites: [],
  loading: false,
  error: null,

  fetchSites: async () => {
    set({ loading: true, error: null });
    try {
      const response = await apiClient.get('/sites');
      set({ sites: response, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createSite: async (payload) => {
    set({ loading: true, error: null });
    try {
      await apiClient.post('/sites', payload);
      await get().fetchSites();
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  updateSite: async (id, payload) => {
    set({ loading: true, error: null });
    try {
      await apiClient.patch(`/sites/${id}`, payload);
      await get().fetchSites();
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },
}));
