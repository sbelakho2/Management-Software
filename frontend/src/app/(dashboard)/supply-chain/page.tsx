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
  RefreshCw,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import { useSupplyChainStore } from '@/stores';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { PageGuard } from '@/components/layout/page-guard';
import { SUPPLY_CHAIN_ROLES } from '@/lib/page-access';

function SupplyChainStats() {
  const { stats, riskAnalysis } = useSupplyChainStore();
  const { t } = useI18n();
  
  return (
    <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-red/60 mb-4">{t('pages.supplyChain.stats.globalRiskIndex')}</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-rams-red tabular-nums">{(riskAnalysis?.global_risk_index * 100).toFixed(1)}%</div>
        <p className="text-[9px] font-mono font-bold text-rams-red uppercase tracking-widest mt-2">{t('pages.supplyChain.stats.thresholdExceeded')}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.supplyChain.stats.intelNodes')}</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats?.supply_chain_nodes || 0}</div>
        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.supplyChain.stats.activeSyncNodes')}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.supplyChain.stats.mitigationReadiness')}</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{(riskAnalysis?.mitigation_readiness * 100).toFixed(1)}%</div>
        <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">{t('pages.supplyChain.stats.optimalReserve')}</p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-line group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.supplyChain.stats.simulationCycles')}</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-rams-steel tabular-nums">{stats?.simulation_runs || 0}</div>
        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.supplyChain.stats.protocolVerifications')}</p>
      </div>
    </div>
  );
}

function ScenariosTab() {
  const { scenarios, loading, fetchScenarios } = useSupplyChainStore();
  const { t } = useI18n();
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
            placeholder={t('pages.supplyChain.scenarios.searchPlaceholder')} 
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {loading ? (
          <div className="col-span-full py-12 text-center text-muted-foreground">{t('pages.supplyChain.scenarios.loading')}</div>
        ) : filteredScenarios.length === 0 ? (
          <div className="col-span-full py-12 text-center text-muted-foreground">{t('pages.supplyChain.scenarios.noScenarios')}</div>
        ) : (
          filteredScenarios.map((scenario) => (
            <Card key={scenario.scenario_id} className="overflow-hidden">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <Badge variant={scenario.severity === 'critical' ? 'danger' : scenario.severity === 'high' ? 'warning' : 'secondary'}>
                    {scenario.severity}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{t('pages.supplyChain.scenarios.probability')} {(scenario.probability * 100).toFixed(0)}%</span>
                </div>
                <CardTitle className="text-lg mt-2">{scenario.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
                  {scenario.description}
                </p>
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">{t('pages.supplyChain.scenarios.delayImpact')}</span>
                    <span className="font-medium">{(scenario.delay_percentage * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">{t('pages.supplyChain.scenarios.costIncrease')}</span>
                    <span className="font-medium">{(scenario.cost_increase_percentage * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <Button className="w-full gap-2" variant="outline">
                  <Play className="h-4 w-4" />
                  {t('pages.supplyChain.actions.runSimulation')}
                </Button>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}

function OverviewTab() {
  const { t } = useI18n();
  return (
    <div className="text-center py-12 text-muted-foreground">
      <p className="text-[10px] font-mono uppercase tracking-widest">{t('pages.supplyChain.overview.title')}</p>
    </div>
  );
}

function DisruptionsTab() {
  const { t } = useI18n();
  return (
    <div className="text-center py-12 text-muted-foreground">
      <p className="text-[10px] font-mono uppercase tracking-widest">{t('pages.supplyChain.disruptions.title')}</p>
    </div>
  );
}

function SupplyChainPageContent() {
  const { t } = useI18n();
  const { fetchStats, fetchRiskAnalysis } = useSupplyChainStore();
  const [activeTab, setActiveTab] = React.useState<'overview' | 'scenarios' | 'disruptions'>('overview');

  useEffect(() => {
    fetchStats();
    fetchRiskAnalysis();
  }, [fetchStats, fetchRiskAnalysis]);

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="supply-chain-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.supplyChain.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.supplyChain.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.supplyChain.station')}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line" onClick={() => fetchStats()}>
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            {t('pages.supplyChain.syncPulse')}
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]" onClick={() => {}}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            {t('pages.supplyChain.initializeSimulation')}
          </Button>
        </div>
      </div>

      <SupplyChainStats />

      {/* Main Content (Modular Rack) */}
      <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
        <CardHeader className="p-0 border-b border-rams-line bg-rams-panel/20">
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
              {t('pages.supplyChain.tabs.overview')}
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative border-l border-rams-line',
                activeTab === 'scenarios'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('scenarios')}
            >
              {t('pages.supplyChain.tabs.scenarios')}
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative border-l border-rams-line',
                activeTab === 'disruptions'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('disruptions')}
            >
              {t('pages.supplyChain.tabs.disruptions')}
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
  const { t } = useI18n();
  return (
    <PageGuard requiredRoles={SUPPLY_CHAIN_ROLES}>
      <Suspense fallback={<div>{t('pages.supplyChain.loading')}</div>}>
        <SupplyChainPageContent />
      </Suspense>
    </PageGuard>
  );
}
