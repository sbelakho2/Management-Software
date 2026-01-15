import { apiClient } from './client';
import type { AndonEvent } from '@/types';

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

  acknowledgeEvent: (eventId: string): Promise<AndonEvent> =>
    apiClient.post<AndonEvent>(`/andon/${eventId}/acknowledge`).then(res => res.data),

  resolveEvent: (eventId: string, data: { resolution: string; root_cause?: string }): Promise<AndonEvent> =>
    apiClient.post<AndonEvent>(`/andon/${eventId}/resolve`, data).then(res => res.data),

  escalateEvent: (eventId: string): Promise<AndonEvent> =>
    apiClient.post<AndonEvent>(`/andon/${eventId}/escalate`).then(res => res.data),

  triggerAndon: (data: { work_center_id: string; type: string; severity: string; description: string }): Promise<AndonEvent> =>
    apiClient.post<AndonEvent>('/andon', data).then(res => res.data),
};
