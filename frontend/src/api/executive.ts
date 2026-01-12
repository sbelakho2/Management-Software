import { apiClient } from './client';

export interface NL2SQLRequest {
  question: string;
}

export interface NL2SQLResponse {
  query_id: string;
  natural_language: string;
  generated_sql: string;
  explanation: string;
  result: Record<string, unknown>;
}

export interface EmployeeRiskRequest {
  employee_name: string;
  department?: string;
  tenure_months?: number;
  overtime_hours_weekly?: number;
  skip_rate?: number;
  peer_comparison?: number;
}

export interface EmployeeRiskResponse {
  employee_name: string;
  retention_risk: string;
  retention_score: number;
  burnout_risk: string;
  burnout_score: number;
  risk_factors: string[];
  recommendations: string[];
}

interface ApiEnvelope<T> {
  success: boolean;
  message?: string | null;
  data?: T | null;
  errors?: string[] | null;
}

export const executiveApi = {
  async nl2sql(payload: NL2SQLRequest): Promise<NL2SQLResponse> {
    const res = await apiClient.post<ApiEnvelope<NL2SQLResponse>>('/executive/nl2sql', payload);
    if (!res.success || !res.data) {
      throw new Error(res.message || 'NL2SQL request failed');
    }
    return res.data;
  },

  async analyzeEmployeeRisk(payload: EmployeeRiskRequest): Promise<EmployeeRiskResponse> {
    const res = await apiClient.post<ApiEnvelope<EmployeeRiskResponse>>(
      '/executive/employee-risk/analyze',
      payload
    );
    if (!res.success || !res.data) {
      throw new Error(res.message || 'Employee risk analysis failed');
    }
    return res.data;
  },
};
