import { apiClient } from './client';

export interface DisruptionScenario {
  scenario_id: string;
  name: string;
  disruption_type: string;
  severity: string;
  delay_percentage: number;
  cost_increase_percentage: number;
  availability_impact: number;
  duration_days: number;
  probability: number;
  description: string;
  affected_regions: string[];
  affected_suppliers: string[];
}

export interface SupplyChainStats {
  simulation_runs: number;
  confidence_level: number;
  supply_chain_nodes: number;
  custom_scenarios: number;
  standard_scenarios: number;
}

export const supplyChainApi = {
  getStats: (): Promise<SupplyChainStats> => 
    apiClient.get('/supply-chain/stats'),
  
  listScenarios: (): Promise<DisruptionScenario[]> => 
    apiClient.get('/supply-chain/scenarios'),
  
  getRiskAnalysis: (): Promise<any> => 
    apiClient.get('/supply-chain/risk-analysis'),
};
