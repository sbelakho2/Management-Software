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

export const executiveApi = {
  async nl2sql(payload: NL2SQLRequest): Promise<NL2SQLResponse> {
    // apiClient already unwraps the { success, data } envelope
    return apiClient.post<NL2SQLResponse>('/executive/nl2sql', payload);
  },

  async analyzeEmployeeRisk(payload: EmployeeRiskRequest): Promise<EmployeeRiskResponse> {
    // apiClient already unwraps the { success, data } envelope
    return apiClient.post<EmployeeRiskResponse>(
      '/executive/employee-risk/analyze',
      payload
    );
  },
};
