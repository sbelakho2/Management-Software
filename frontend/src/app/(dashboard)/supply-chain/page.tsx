'use client';

import * as React from 'react';
import { Suspense, useEffect } from 'react';
import {
  Search,
  Filter,
  AlertTriangle,
  Globe,
  TrendingDown,
  Activity,
  BarChart,
  Shield,
  Play,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useSupplyChainStore } from '@/stores';

function SupplyChainStats() {
  const { stats, riskAnalysis } = useSupplyChainStore();
  
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/30">
              <Activity className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{(riskAnalysis?.global_risk_index * 100).toFixed(1)}%</p>
              <p className="text-sm text-muted-foreground">Global Risk Index</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
              <Globe className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.supply_chain_nodes || 0}</p>
              <p className="text-sm text-muted-foreground">Active Nodes</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
              <Shield className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{(riskAnalysis?.mitigation_readiness * 100).toFixed(1)}%</p>
              <p className="text-sm text-muted-foreground">Mitigation Readiness</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/30">
              <BarChart className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.simulation_runs || 0}</p>
              <p className="text-sm text-muted-foreground">Simulations Run</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ScenariosTab() {
  const { scenarios, loading, fetchScenarios } = useSupplyChainStore();
  const [searchQuery, setSearchQuery] = React.useState('');

  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  const filteredScenarios = scenarios.filter((s) => 
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search scenarios..." 
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {loading ? (
          <div className="col-span-full py-12 text-center text-muted-foreground">Loading scenarios...</div>
        ) : filteredScenarios.length === 0 ? (
          <div className="col-span-full py-12 text-center text-muted-foreground">No scenarios found.</div>
        ) : (
          filteredScenarios.map((scenario) => (
            <Card key={scenario.scenario_id} className="overflow-hidden">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <Badge variant={scenario.severity === 'critical' ? 'danger' : scenario.severity === 'high' ? 'warning' : 'secondary'}>
                    {scenario.severity}
                  </Badge>
                  <span className="text-xs text-muted-foreground">Prob: {(scenario.probability * 100).toFixed(0)}%</span>
                </div>
                <CardTitle className="text-lg mt-2">{scenario.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
                  {scenario.description}
                </p>
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Delay Impact:</span>
                    <span className="font-medium">{(scenario.delay_percentage * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Cost Increase:</span>
                    <span className="font-medium">{(scenario.cost_increase_percentage * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <Button className="w-full gap-2" variant="outline">
                  <Play className="h-4 w-4" />
                  Run Simulation
                </Button>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}

function SupplyChainPageContent() {
  const { fetchStats, fetchRiskAnalysis } = useSupplyChainStore();

  useEffect(() => {
    fetchStats();
    fetchRiskAnalysis();
  }, [fetchStats, fetchRiskAnalysis]);

  return (
    <div className="space-y-6" data-testid="supply-chain-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Supply Chain Intelligence</h1>
          <p className="text-muted-foreground">Global disruption simulation and risk stress-testing</p>
        </div>
      </div>

      <SupplyChainStats />

      <div className="border-b">
        <nav className="flex gap-4">
          <button className="pb-3 px-1 border-b-2 border-primary text-primary font-medium text-sm">
            Disruption Scenarios
          </button>
          <button className="pb-3 px-1 border-b-2 border-transparent text-muted-foreground hover:text-foreground font-medium text-sm transition-colors">
            Risk Analysis
          </button>
          <button className="pb-3 px-1 border-b-2 border-transparent text-muted-foreground hover:text-foreground font-medium text-sm transition-colors">
            Network Map
          </button>
        </nav>
      </div>

      <div className="mt-4">
        <ScenariosTab />
      </div>
    </div>
  );
}

export default function SupplyChainPage() {
  return (
    <Suspense fallback={<div>Loading Supply Chain...</div>}>
      <SupplyChainPageContent />
    </Suspense>
  );
}
