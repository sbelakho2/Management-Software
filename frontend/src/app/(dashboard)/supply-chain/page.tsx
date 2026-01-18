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
    <div className="grid gap-0 md:grid-cols-4 border border-rams-border bg-rams-border">
      <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-red/60 mb-4">Global Risk Index</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-rams-red tabular-nums">{(riskAnalysis?.global_risk_index * 100).toFixed(1)}%</div>
        <p className="text-[9px] font-mono font-bold text-rams-red uppercase tracking-widest mt-2">THRESHOLD_EXCEEDED</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Intel Nodes</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats?.supply_chain_nodes || 0}</div>
        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">ACTIVE_SYNC_NODES</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Mitigation Readiness</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{(riskAnalysis?.mitigation_readiness * 100).toFixed(1)}%</div>
        <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">OPTIMAL_RESERVE</p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-border group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Simulation Cycles</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-rams-steel tabular-nums">{stats?.simulation_runs || 0}</div>
        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">PROTOCOL_VERIFICATIONS</p>
      </div>
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
    <div className="space-y-8 page-fade-in pb-12" data-testid="supply-chain-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.supplyChain.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.supplyChain.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: GLOBAL-LOGISTICS-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-border" onClick={() => fetchStats()}>
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            Sync Pulse
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]" onClick={() => {}}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            Initialize Simulation
          </Button>
        </div>
      </div>

      <SupplyChainStats />

      {/* Main Content (Modular Rack) */}
      <Card className="rounded-rams-sm overflow-hidden border-rams-border shadow-none">
        <CardHeader className="p-0 border-b border-rams-border bg-rams-panel/20">
          <div className="flex">
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative',
                activeTab === 'overview'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('overview')}
            >
              Overview
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative border-l border-rams-border/30',
                activeTab === 'scenarios'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('scenarios')}
            >
              Scenarios
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative border-l border-rams-border/30',
                activeTab === 'disruptions'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('disruptions')}
            >
              Disruptions
            </button>
          </div>
        </CardHeader>
        <CardContent className="p-6 bg-rams-module">
          <div className="animate-in fade-in duration-300">
            {activeTab === 'overview' && <OverviewTab />}
            {activeTab === 'scenarios' && <ScenariosTab />}
            {activeTab === 'disruptions' && <DisruptionsTab />}
          </div>
        </CardContent>
      </Card>
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
