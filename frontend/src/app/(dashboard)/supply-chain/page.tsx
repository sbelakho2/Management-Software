'use client';

import * as React from 'react';
import { Suspense, useEffect } from 'react';
import { useI18n } from '@/contexts/i18n-context';
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
  Plus,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useSupplyChainStore } from '@/stores';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

function SupplyChainStats() {
  const { stats, riskAnalysis } = useSupplyChainStore();
  
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-danger/60">Global Risk Index</p>
              <p className="text-3xl font-heading font-bold tracking-tight text-red-600 dark:text-red-500 mt-1">{(riskAnalysis?.global_risk_index * 100).toFixed(1)}%</p>
            </div>
            <div className="p-3 rounded-2xl bg-danger/10 text-danger shadow-sm">
              <Activity className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-primary/60">Active Intelligence Nodes</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats?.supply_chain_nodes || 0}</p>
            </div>
            <div className="p-3 rounded-2xl bg-primary/10 text-primary shadow-sm">
              <Globe className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-success/60">Mitigation Readiness</p>
              <p className="text-3xl font-heading font-bold tracking-tight text-emerald-600 dark:text-emerald-500 mt-1">{(riskAnalysis?.mitigation_readiness * 100).toFixed(1)}%</p>
            </div>
            <div className="p-3 rounded-2xl bg-success/10 text-success shadow-sm">
              <Shield className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-primary/60">Simulation Protocols</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats?.simulation_runs || 0}</p>
            </div>
            <div className="p-3 rounded-2xl bg-indigo-500/10 text-indigo-500 shadow-sm">
              <BarChart className="h-5 w-5" />
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
  const { t } = useI18n();
  const { fetchStats, fetchRiskAnalysis } = useSupplyChainStore();

  useEffect(() => {
    fetchStats();
    fetchRiskAnalysis();
  }, [fetchStats, fetchRiskAnalysis]);

  return (
    <div className="space-y-8 page-fade-in" data-testid="supply-chain-page">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight ">
            {t('pages.supplyChain.title')}
          </h1>
          <p className="text-muted-foreground font-medium">{t('pages.supplyChain.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine">
            <Plus className="mr-2 h-4 w-4" />
            New Simulation
          </Button>
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
