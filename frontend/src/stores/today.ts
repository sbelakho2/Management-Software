import { create } from 'zustand';
import { todayApi, TodayScreenData } from '@/api/today';
import { getErrorMessage } from '@/lib/error-utils';

interface TodayState {
  data: TodayScreenData | null;
  loading: boolean;
  error: string | null;

  fetchTodayScreen: (userId: string, userName: string) => Promise<void>;
}

export const useTodayStore = create<TodayState>((set) => ({
  data: null,
  loading: false,
  error: null,

  fetchTodayScreen: async (userId, userName) => {
    set({ loading: true, error: null });
    try {
      const data = await todayApi.getTodayScreen(userId, userName);
      set({ data, loading: false });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error), loading: false });
    }
  },
}));
