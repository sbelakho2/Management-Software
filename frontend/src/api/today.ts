import { apiClient } from './client';

export interface TodayScreenData {
  user_id: string;
  user_name: string;
  current_date: string;
  greeting: string;
  top_priorities: any[];
  top_risks: Record<string, any[]>;
  todays_commitments: any[];
  abnormalities: any[];
  quick_metrics: any[];
  lsw_summary: any;
  todays_micro_drills: any[];
}

export const todayApi = {
  getTodayScreen: (userId: string, userName: string): Promise<TodayScreenData> => 
    apiClient.get(`/today/screen/${userId}`, { params: { user_name: userName } }),
};
