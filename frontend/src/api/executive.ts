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
  confidence?: number;
}

export interface SQDCPPillar {
  status: 'GREEN' | 'YELLOW' | 'RED';
  [key: string]: unknown;
}

export interface SQDCPResponse {
  safety: SQDCPPillar;
  quality: SQDCPPillar;
  delivery: SQDCPPillar;
  cost: SQDCPPillar;
  people: SQDCPPillar;
  generated_at: string;
}

export interface CrossFunctionalKPIResponse {
  quality_score: number;
  delivery_score: number;
  cost_efficiency: number;
  workforce_utilization: number;
  overall_score: number;
  details: Record<string, unknown>;
}

export interface StrategicDirective {
  priority: string;
  title: string;
  description: string;
  severity: string;
  category: string;
}

export interface StrategicDirectivesResponse {
  directives: StrategicDirective[];
  generated_at: string;
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

  async getSQDCP(): Promise<SQDCPResponse> {
    return apiClient.get<SQDCPResponse>('/executive/sqdcp');
  },

  async getKPISummary(): Promise<CrossFunctionalKPIResponse> {
    return apiClient.get<CrossFunctionalKPIResponse>('/executive/kpi-summary');
  },

  async getStrategicDirectives(): Promise<StrategicDirectivesResponse> {
    return apiClient.get<StrategicDirectivesResponse>('/executive/strategic-directives');
  },
};
