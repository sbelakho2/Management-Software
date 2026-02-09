import { apiClient } from './client';

export interface MLInsight {
  id: string;
  type: 'prediction' | 'anomaly' | 'recommendation' | 'trend';
  title: string;
  description: string;
  confidence: number;
  impact: 'high' | 'medium' | 'low';
  category: string;
  model_name: string;
  action_items?: string[];
  severity?: 'critical' | 'warning' | 'info';
  recommendation?: string;
}

export interface PerformanceTrend {
  metric: string;
  current_value: number;
  previous_value: number;
  change_percent: number;
  trend: 'up' | 'down' | 'stable';
  prediction_7d: number;
  prediction_30d?: number;
}

export const analyticsApi = {
  getInsights: (): Promise<MLInsight[]> => 
    apiClient.get('/analytics/insights'),
  
  getTrends: (): Promise<PerformanceTrend[]> => 
    apiClient.get('/analytics/trends'),
  
  getHealth: (): Promise<any> => 
    apiClient.get('/analytics/health'),
};
