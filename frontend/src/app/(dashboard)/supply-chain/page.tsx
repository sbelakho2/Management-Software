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
import type { DisruptionScenario } from '@/api/supply-chain';
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
        <div className="text-3xl font-mono font-bold tracking-tight text-rams-red tabular-nums">{((riskAnalysis?.global_risk_index ?? 0) * 100).toFixed(1)}%</div>
        <p className="text-[9px] font-mono font-bold text-rams-red uppercase tracking-widest mt-2">{t('pages.supplyChain.stats.thresholdExceeded')}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.supplyChain.stats.intelNodes')}</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats?.supply_chain_nodes || 0}</div>
        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.supplyChain.stats.activeSyncNodes')}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.supplyChain.stats.mitigationReadiness')}</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{((riskAnalysis?.mitigation_readiness ?? 0) * 100).toFixed(1)}%</div>
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
  const { stats, riskAnalysis, scenarios, loading } = useSupplyChainStore();

  const criticalScenarios = scenarios.filter(s => s.severity === 'critical');
  const highScenarios = scenarios.filter(s => s.severity === 'high');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">{t('pages.supplyChain.overview.title')}</p>
        {loading && <RefreshCw className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
      </div>

      {/* Key Metrics Grid */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-rams-line">
          <CardContent className="p-4 space-y-2">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-muted-foreground" />
              <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/60">{t('pages.supplyChain.overview.networkNodes') || 'Network Nodes'}</span>
            </div>
            <p className="text-2xl font-mono font-bold tabular-nums">{stats?.supply_chain_nodes ?? 0}</p>
            <p className="text-[9px] text-muted-foreground">{t('pages.supplyChain.overview.activeSuppliers') || 'Active suppliers in monitored network'}</p>
          </CardContent>
        </Card>
        <Card className="border-rams-line">
          <CardContent className="p-4 space-y-2">
            <div className="flex items-center gap-2">
              <BarChart className="h-4 w-4 text-muted-foreground" />
              <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/60">{t('pages.supplyChain.overview.confidence') || 'Confidence Level'}</span>
            </div>
            <p className="text-2xl font-mono font-bold tabular-nums">{((stats?.confidence_level ?? 0) * 100).toFixed(0)}%</p>
            <p className="text-[9px] text-muted-foreground">{t('pages.supplyChain.overview.simulationAccuracy') || 'Simulation accuracy metric'}</p>
          </CardContent>
        </Card>
        <Card className="border-rams-line">
          <CardContent className="p-4 space-y-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rams-red" />
              <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/60">{t('pages.supplyChain.overview.criticalRisks') || 'Critical Risks'}</span>
            </div>
            <p className="text-2xl font-mono font-bold tabular-nums text-rams-red">{criticalScenarios.length}</p>
            <p className="text-[9px] text-muted-foreground">{highScenarios.length} {t('pages.supplyChain.overview.highSeverity') || 'high severity scenarios'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Risk Breakdown */}
      {riskAnalysis && (
        <Card className="border-rams-line">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono uppercase tracking-widest">{t('pages.supplyChain.overview.riskBreakdown') || 'Risk Analysis Breakdown'}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{t('pages.supplyChain.stats.globalRiskIndex')}</span>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-rams-red rounded-full" style={{ width: `${((riskAnalysis.global_risk_index ?? 0) * 100)}%` }} />
                  </div>
                  <span className="text-xs font-mono font-bold tabular-nums">{((riskAnalysis.global_risk_index ?? 0) * 100).toFixed(1)}%</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{t('pages.supplyChain.stats.mitigationReadiness')}</span>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-rams-green rounded-full" style={{ width: `${((riskAnalysis.mitigation_readiness ?? 0) * 100)}%` }} />
                  </div>
                  <span className="text-xs font-mono font-bold tabular-nums">{((riskAnalysis.mitigation_readiness ?? 0) * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Top Disruption Scenarios */}
      {criticalScenarios.length > 0 && (
        <Card className="border-rams-line border-l-2 border-l-rams-red">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono uppercase tracking-widest text-rams-red">{t('pages.supplyChain.overview.criticalAlerts') || 'Critical Disruption Alerts'}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {criticalScenarios.slice(0, 5).map(s => (
                <div key={s.scenario_id} className="flex items-center justify-between py-2 border-b border-rams-line last:border-0">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-3.5 w-3.5 text-rams-red" />
                    <span className="text-sm font-medium">{s.name}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{t('pages.supplyChain.scenarios.probability')} {(s.probability * 100).toFixed(0)}%</span>
                    <Badge variant="danger" className="text-[9px]">{s.severity}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function DisruptionsTab() {
  const { t } = useI18n();
  const { scenarios, loading } = useSupplyChainStore();

  // Group by disruption_type
  const grouped = scenarios.reduce<Record<string, DisruptionScenario[]>>((acc, s) => {
    const key = s.disruption_type || 'other';
    if (!acc[key]) acc[key] = [];
    acc[key].push(s);
    return acc;
  }, {});

  const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">{t('pages.supplyChain.disruptions.title')}</p>
        {loading && <RefreshCw className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
      </div>

      {scenarios.length === 0 && !loading ? (
        <div className="text-center py-12 text-muted-foreground">
          <Shield className="h-8 w-8 mx-auto mb-3 opacity-30" />
          <p className="text-sm">{t('pages.supplyChain.disruptions.noDisruptions') || 'No disruption scenarios detected'}</p>
        </div>
      ) : (
        Object.entries(grouped).map(([type, items]) => (
          <Card key={type} className="border-rams-line">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-mono uppercase tracking-widest">{type.replace(/_/g, ' ')}</CardTitle>
                <Badge variant="secondary" className="text-[9px]">{items.length} {t('pages.supplyChain.disruptions.scenarios') || 'scenarios'}</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {items
                  .sort((a, b) => (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99))
                  .map(scenario => (
                    <div key={scenario.scenario_id} className="flex items-center justify-between py-2 border-b border-rams-line last:border-0">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <Activity className={cn('h-3.5 w-3.5 shrink-0', scenario.severity === 'critical' ? 'text-rams-red' : scenario.severity === 'high' ? 'text-rams-orange' : 'text-muted-foreground')} />
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{scenario.name}</p>
                          <p className="text-[10px] text-muted-foreground truncate">{scenario.description}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0 ml-4">
                        <div className="text-right">
                          <p className="text-[9px] text-muted-foreground">{t('pages.supplyChain.scenarios.delayImpact')}</p>
                          <p className="text-xs font-mono font-bold tabular-nums">{(scenario.delay_percentage * 100).toFixed(0)}%</p>
                        </div>
                        <Badge variant={scenario.severity === 'critical' ? 'danger' : scenario.severity === 'high' ? 'warning' : 'secondary'} className="text-[9px]">
                          {scenario.severity}
                        </Badge>
                      </div>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        ))
      )}
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
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]" onClick={() => setActiveTab('scenarios')}>
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
