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
  active_pulses: GlobalPulseSummary[];
  active_handovers: HandoverNoteSummary[];
  active_risks?: Array<{ id: string; title: string; severity: string; area: string }>;
}

export interface GlobalPulseSummary {
  id: number;
  message: string;
  severity: string;
  highlight_metric_name?: string;
  highlight_metric_value?: string;
}

export interface HandoverNoteSummary {
  id: number;
  station_id: number;
  severity: string;
  safety: string;
  quality: string;
  delivery: string;
  cost: string;
  people: string;
  notes: string;
  created_at: string;
}

export const todayApi = {
  getTodayScreen: (userId: string, userName?: string): Promise<TodayScreenData> => {
    const safeName = (userName || '').trim() || 'User';
    return apiClient.get(`/today/screen/${userId}`, { params: { user_name: safeName } });
  },
};
