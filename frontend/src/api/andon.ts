import { apiClient } from './client';

export interface AndonAnalytics {
  avg_response_time_minutes: number;
  avg_resolution_time_minutes: number;
  total_signals: number;
  uptime_impact_percent: number;
  signals_by_category: Record<string, number>;
  top_problem_stations: Array<{
    station_id: string;
    count: number;
    downtime_hours: number;
  }>;
}

export const andonApi = {
  getAnalytics: (days: number = 30): Promise<AndonAnalytics> =>
    apiClient.get<any>('/andon/analytics', { params: { days } }).then(res => res.data),
};
