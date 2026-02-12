'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
import { useAuthStore } from '@/stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { useExecutiveStore, useQualityStore, useTodayStore, useAnalyticsStore } from '@/stores';
import { Loader2, Download, Search, Send, Users, AlertTriangle, TrendingUp, Shield, ArrowRight, RefreshCw, CheckCircle2, DollarSign, XCircle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { PageGuard } from '@/components/layout/page-guard';
import { EXECUTIVE_ROLES } from '@/lib/page-access';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';
import { API_ROOT } from '@/api/client';
import { cn } from '@/lib/utils';

function RiskBadge({ value }: { value: string }) {
  const v = (value || '').toLowerCase();
  const variant = v === 'critical' || v === 'high' ? 'destructive' : v === 'medium' ? 'warning' : 'secondary';
  return <Badge variant={variant as any}>{value}</Badge>;
}

export default function ExecutivePage() {
  const { t } = useI18n();
  const { user, isAuthenticated } = useAuthStore();
  const [nl2sqlQuestion, setNl2sqlQuestion] = React.useState('How many open CAPAs are there?');
  
  const { 
    nl2sqlResult, 
    riskResult, 
    nl2sqlLoading, 
    nl2sqlError,
    riskLoading,
    riskError,
    sqdcp,
    kpiSummary,
    sqdcpLoading,
    runNl2sql,
    analyzeRisk,
    fetchSQDCP,
    fetchKPISummary,
  } = useExecutiveStore();

  const { totalNcrs, totalCapas, fetchNCRs, fetchCAPAs } = useQualityStore();
  const { data: todayData, fetchTodayScreen } = useTodayStore();
  const { insights, fetchInsights } = useAnalyticsStore();

  React.useEffect(() => {
    if (isAuthenticated) {
      fetchNCRs();
      fetchCAPAs();
      fetchInsights();
      fetchSQDCP();
      fetchKPISummary();
      if (user) {
        const name = (user.full_name || '').trim() || (user.email || '').trim() || t('common.user');
        fetchTodayScreen(user.id, name);
      }
    }
  }, [fetchNCRs, fetchCAPAs, fetchInsights, fetchSQDCP, fetchKPISummary, fetchTodayScreen, user, isAuthenticated]);

  const [employeeName, setEmployeeName] = React.useState(() => t('pages.executive.risk.namePlaceholder'));
  const [department, setDepartment] = React.useState(() => t('pages.executive.risk.deptPlaceholder'));
  const [tenureMonths, setTenureMonths] = React.useState(3);
  const [overtimeHours, setOvertimeHours] = React.useState(20);
  const [skipRate, setSkipRate] = React.useState(0.25);
  const [peerComparison, setPeerComparison] = React.useState(1.4);

  // Derive dynamic quarter label from current date instead of hardcoding
  const currentQuarter = React.useMemo(() => {
    const now = new Date();
    const q = Math.ceil((now.getMonth() + 1) / 3);
    return `Q${q} ${now.getFullYear()}`;
  }, []);

  // Derive strategic directives from live insights data
  const strategicDirectives = React.useMemo(() => {
    const insightsList = Array.isArray(insights) ? insights : [];
    const priorityLabels = [
      t('pages.executive.strategicDirectives.priorityAlpha'),
      t('pages.executive.strategicDirectives.priorityBeta'),
      t('pages.executive.strategicDirectives.priorityGamma'),
      t('pages.executive.strategicDirectives.priorityDelta'),
    ];
    // Take the top insights sorted by severity (critical > warning > info)
    const severityOrder: Record<string, number> = { critical: 0, warning: 1, info: 2 };
    const sorted = [...insightsList]
      .sort((a, b) => (severityOrder[a.severity ?? 'info'] ?? 3) - (severityOrder[b.severity ?? 'info'] ?? 3))
      .slice(0, 4);
    if (sorted.length === 0) {
      return [
        {
          label: t('pages.executive.strategicDirectives.priorityAlpha'),
          title: t('pages.executive.strategicDirectives.awaitingDataTitle'),
          desc: t('pages.executive.strategicDirectives.awaitingDataDesc'),
          severity: 'info',
        },
      ];
    }
    return sorted.map((insight, idx) => ({
      label: priorityLabels[idx] || t('pages.executive.strategicDirectives.priorityFallback', { index: idx + 1 }),
      title: insight.title || t('pages.executive.strategicDirectives.insightFallback'),
      desc: insight.description || insight.recommendation || t('pages.executive.strategicDirectives.insightDescFallback'),
      severity: insight.severity === 'critical' ? 'critical' : insight.severity === 'warning' ? 'warning' : 'strategic',
    }));
  }, [insights, t]);

  // Compute revenue delta vs previous month (data-driven, not hardcoded)
  const revenueMtd = ((todayData as any)?.metrics?.revenue || 0);
  const revenuePrevMonth = ((todayData as any)?.metrics?.revenue_prev_month || 0);
  const revenueDeltaPct = revenuePrevMonth > 0
    ? (((revenueMtd - revenuePrevMonth) / revenuePrevMonth) * 100).toFixed(1)
    : '—';
  const revenueDeltaPositive = revenuePrevMonth > 0 && revenueMtd >= revenuePrevMonth;

  // Compute uptime from real data
  const uptimeValue = ((todayData as any)?.metrics?.uptime_pct ?? null);
  const uptimeDisplay = uptimeValue !== null ? `${Number(uptimeValue).toFixed(1)}%` : t('common.na');

  const handleRunNl2sql = () => {
    runNl2sql({ question: nl2sqlQuestion });
  };

  const handleAnalyzeRisk = () => {
    analyzeRisk({
      employee_name: employeeName,
      department,
      tenure_months: tenureMonths,
      overtime_hours_weekly: overtimeHours,
      skip_rate: skipRate,
      peer_comparison: peerComparison,
    });
  };

  const exportUrl = `${API_ROOT}/api/v1/executive/strategic-report/export`;

  return (
    <PageGuard requiredRoles={EXECUTIVE_ROLES}>
      <div className="space-y-8 page-fade-in pb-12" data-testid="executive-page">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              {t('pages.executive.title')}
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('pages.executive.subtitle')}</span>
              <span className="opacity-30">|</span>
              <span>{t('pages.executive.station')}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <AmbientStatus 
              status={totalNcrs > 5 ? 'critical' : totalNcrs > 0 ? 'warning' : 'operational'} 
              label={totalNcrs > 5 ? t('pages.executive.anomaliesDetected') : totalNcrs > 0 ? t('pages.executive.monitoringActive') : t('pages.executive.allSystemsNominal')}
            />
            <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line" asChild>
              <a href={exportUrl}>
                <Download className="mr-2 h-3.5 w-3.5" />
                {t('pages.executive.exportIntelligence')}
              </a>
            </Button>
          </div>
        </div>

        <Tabs defaultValue="north-star" className="space-y-8 animate-in fade-in duration-700">
          <TabsList className="bg-rams-panel border border-rams-line p-1 rounded-rams-sm w-fit overflow-x-auto no-scrollbar">
            <TabsTrigger value="north-star">{t('pages.executive.tabs.northStar')}</TabsTrigger>
            <TabsTrigger value="sqdcp">{t('pages.executive.tabs.sqdcp')}</TabsTrigger>
            <TabsTrigger value="nl2sql">{t('pages.executive.tabs.senseiAi')}</TabsTrigger>
            <TabsTrigger value="employee-risk">{t('pages.executive.tabs.riskPrediction')}</TabsTrigger>
          </TabsList>

          <TabsContent value="north-star" data-testid="north-star" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
            {/* Executive KPIs */}
            <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-line bg-rams-line">
              <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.executive.kpi.revenueMtd')}</p>
                <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">
                  ${(revenueMtd / 1000000).toFixed(1)}M
                </div>
                <p className={cn("text-[9px] font-mono font-bold uppercase tracking-widest mt-2 flex items-center gap-1", revenueDeltaPositive ? "text-rams-green" : "text-rams-red")}>
                  <TrendingUp className="h-3 w-3" /> {revenueDeltaPct !== '—' ? `${revenueDeltaPositive ? '+' : ''}${revenueDeltaPct}%` : revenueDeltaPct} {currentQuarter}
                </p>
              </div>
              <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.executive.kpi.activeAnomalies')}</p>
                <div className={cn("text-3xl font-mono font-bold tracking-tight tabular-nums", totalNcrs > 5 ? "text-rams-red" : "text-foreground/90")}>
                  {totalNcrs}
                </div>
                <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.executive.kpi.activeGateBlocks')}</p>
              </div>
              <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.executive.kpi.openResolutions')}</p>
                <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{totalCapas}</div>
                <p className="text-[9px] font-mono font-bold text-rams-orange uppercase tracking-widest mt-2">{t('pages.executive.kpi.capaSyncActive')}</p>
              </div>
              <div className="bg-rams-module p-6 border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.executive.kpi.operationalUptime')}</p>
                <div className={cn("text-3xl font-mono font-bold tracking-tight tabular-nums", uptimeValue !== null && uptimeValue >= 99 ? "text-rams-green" : uptimeValue !== null && uptimeValue < 95 ? "text-rams-red" : "text-foreground/90")}>{uptimeDisplay}</div>
                <p className={cn("text-[9px] font-mono font-bold uppercase tracking-widest mt-2", uptimeValue !== null && uptimeValue >= 99 ? "text-rams-green" : "text-muted-foreground/40")}>{uptimeValue !== null && uptimeValue >= 99 ? t('pages.executive.kpi.optimalState') : uptimeValue !== null ? t('pages.executive.kpi.belowTarget') : t('pages.executive.kpi.awaitingData')}</p>
              </div>
            </div>

            <div className="grid gap-8 lg:grid-cols-2">
              <Card className="rounded-rams-sm overflow-hidden border-rams-line">
                <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-rams-orange" />
                    {t('pages.executive.strategicDirectives.title')}
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-1 space-y-1">
                  {strategicDirectives.map((item) => (
                    <div key={item.label} className="p-5 bg-rams-panel/40 border border-rams-line hover:bg-rams-panel transition-none group">
                      <div className="flex items-center justify-between mb-4">
                        <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{item.label}</span>
                        <Badge variant={item.severity === 'critical' ? 'danger' : 'default'} size="sm" className="h-4 px-1">{item.severity.toUpperCase()}</Badge>
                      </div>
                      <p className="font-sans font-black text-sm uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{item.title}</p>
                      <p className="text-[10px] text-muted-foreground mt-2 leading-relaxed font-medium uppercase">{item.desc}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="rounded-rams-sm overflow-hidden border-rams-line">
                <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                    <Users className="h-4 w-4 text-rams-orange" />
                    {t('pages.executive.operationalOverview')}
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 bg-rams-module relative overflow-hidden space-y-4">
                  <div className="relative z-10 grid grid-cols-2 gap-4">
                    <div className="p-4 bg-rams-panel/40 border border-rams-line space-y-1">
                      <p className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/50">{t('pages.executive.ops.activeUsers')}</p>
                      <p className="text-2xl font-mono font-bold tabular-nums text-foreground/90">{(todayData as any)?.metrics?.active_users ?? '—'}</p>
                    </div>
                    <div className="p-4 bg-rams-panel/40 border border-rams-line space-y-1">
                      <p className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/50">{t('pages.executive.ops.openWorkOrders')}</p>
                      <p className="text-2xl font-mono font-bold tabular-nums text-foreground/90">{(todayData as any)?.metrics?.open_work_orders ?? '—'}</p>
                    </div>
                    <div className="p-4 bg-rams-panel/40 border border-rams-line space-y-1">
                      <p className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/50">{t('pages.executive.ops.productionEfficiency')}</p>
                      <p className="text-2xl font-mono font-bold tabular-nums text-rams-green">{(todayData as any)?.metrics?.production_efficiency ? `${Number((todayData as any).metrics.production_efficiency).toFixed(1)}%` : '—'}</p>
                    </div>
                    <div className="p-4 bg-rams-panel/40 border border-rams-line space-y-1">
                      <p className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/50">{t('pages.executive.ops.pendingApprovals')}</p>
                      <p className="text-2xl font-mono font-bold tabular-nums text-rams-orange">{(todayData as any)?.metrics?.pending_approvals ?? '—'}</p>
                    </div>
                  </div>
                  <div className="absolute inset-0 perforated-bg opacity-5" />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* SQDCP Dashboard Tab */}
          <TabsContent value="sqdcp" data-testid="sqdcp" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="grid gap-0 md:grid-cols-5 border border-rams-line bg-rams-line">
              {(['safety', 'quality', 'delivery', 'cost', 'people'] as const).map((pillar) => {
                const data = sqdcp?.[pillar];
                const status = (data?.status || 'GREEN') as string;
                const statusColor = status === 'RED' ? 'bg-rams-red text-white' : status === 'YELLOW' ? 'bg-rams-orange text-black' : 'bg-rams-green text-white';
                const entries = data ? Object.entries(data).filter(([k]) => k !== 'status') : [];
                return (
                  <div key={pillar} className="bg-rams-module p-6 border-r border-rams-line group hover:bg-rams-panel transition-none">
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50">{t(`pages.executive.sqdcp.${pillar}`)}</p>
                      <span className={cn("px-2 py-0.5 text-[8px] font-black uppercase tracking-widest", statusColor)}>{status}</span>
                    </div>
                    <div className="space-y-3">
                      {entries.map(([key, val]) => (
                        <div key={key} className="flex justify-between items-baseline">
                          <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-muted-foreground/50">
                            {key.replace(/_/g, ' ')}
                          </span>
                          <span className="text-sm font-mono font-bold tabular-nums text-foreground/90">
                            {typeof val === 'number' ? (val >= 1000 ? `${(val / 1000).toFixed(1)}K` : val.toLocaleString()) : String(val)}
                          </span>
                        </div>
                      ))}
                      {entries.length === 0 && (
                        <p className="text-[9px] font-mono text-muted-foreground/30 uppercase tracking-widest">{t('pages.executive.loading')}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* KPI Score Cards */}
            {kpiSummary && (
              <div className="grid gap-0 md:grid-cols-5 border border-rams-line bg-rams-line">
                {[
                  { label: t('pages.executive.kpi.qualityScore'), value: kpiSummary.quality_score },
                  { label: t('pages.executive.kpi.deliveryScore'), value: kpiSummary.delivery_score },
                  { label: t('pages.executive.kpi.costEfficiency'), value: kpiSummary.cost_efficiency },
                  { label: t('pages.executive.kpi.workforce'), value: kpiSummary.workforce_utilization },
                  { label: t('pages.executive.kpi.overallScore'), value: kpiSummary.overall_score },
                ].map((kpi) => (
                  <div key={kpi.label} className="bg-rams-module p-6 border-r border-rams-line text-center">
                    <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-3">{kpi.label}</p>
                    <div className={cn(
                      "text-3xl font-mono font-bold tracking-tight tabular-nums",
                      kpi.value >= 80 ? "text-rams-green" : kpi.value >= 60 ? "text-rams-orange" : "text-rams-red"
                    )}>
                      {kpi.value.toFixed(1)}
                    </div>
                    <Progress value={kpi.value} className="h-1 mt-4" indicatorClassName={
                      kpi.value >= 80 ? "bg-rams-green" : kpi.value >= 60 ? "bg-rams-orange" : "bg-rams-red"
                    } />
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="nl2sql" data-testid="nl2sql" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-none bg-rams-orange/10 border border-rams-orange/20 text-rams-orange">
                    <Send className="h-4 w-4" />
                  </div>
                  <div>
                    <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.executive.nl2sql.title')}</CardTitle>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{t('pages.executive.nl2sql.protocol')}</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-8 space-y-8 bg-rams-module relative overflow-hidden">
                <div className="space-y-4 relative z-10">
                  <div className="flex flex-col gap-2">
                    <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.executive.nl2sql.commandInput')}</label>
                    <Textarea
                      value={nl2sqlQuestion}
                      onChange={(e) => setNl2sqlQuestion(e.target.value)}
                      rows={4}
                      placeholder={t('pages.executive.nl2sql.placeholder')}
                      className="bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider p-4 h-32 focus-visible:ring-rams-orange"
                      data-testid="nl2sql-question"
                    />
                  </div>
                  <Button 
                    onClick={handleRunNl2sql} 
                    disabled={nl2sqlLoading || !nl2sqlQuestion}
                    className="w-full h-12 rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]"
                    data-testid="nl2sql-run"
                  >
                    {nl2sqlLoading ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        {t('pages.executive.nl2sql.reasoningInProgress')}
                      </div>
                    ) : (
                      t('pages.executive.nl2sql.executeInference')
                    )}
                  </Button>
                </div>

                {(nl2sqlResult || nl2sqlError) && (
                  <div className="mt-8 animate-in fade-in slide-in-from-top-4 duration-500 relative z-10">
                    {nl2sqlError ? (
                      <div className="p-6 bg-rams-red/5 border border-rams-red/20 flex gap-4" data-testid="nl2sql-error">
                        <AlertTriangle className="h-5 w-5 text-rams-red shrink-0" />
                        <div className="text-xs font-medium text-rams-red uppercase leading-relaxed">{nl2sqlError}</div>
                      </div>
                    ) : nl2sqlResult ? (
                      <div className="space-y-6" data-testid="nl2sql-result">
                        <div className="grid gap-6 md:grid-cols-2">
                          <div className="space-y-2">
                            <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{t('pages.executive.nl2sql.generatedLogic')}</label>
                            <pre className="p-4 bg-rams-panel border border-rams-line text-[10px] font-mono text-foreground/70 overflow-auto max-h-40 rounded-none uppercase tracking-tighter">{nl2sqlResult.generated_sql}</pre>
                          </div>
                          <div className="space-y-2">
                            <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{t('pages.executive.nl2sql.senseiReasoning')}</label>
                            <div className="p-4 bg-rams-orange/5 border border-rams-orange/20 text-xs font-medium leading-relaxed uppercase text-foreground/80">{nl2sqlResult.explanation}</div>
                          </div>
                        </div>
                        
                        <div className="space-y-2">
                          <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{t('pages.executive.nl2sql.dataOutput')}</label>
                          <pre className="p-4 bg-rams-panel border border-rams-line text-[10px] font-mono text-foreground/70 overflow-auto max-h-60 rounded-none uppercase tracking-tighter">
                            {JSON.stringify(nl2sqlResult.result, null, 2)}
                          </pre>
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}
                <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="employee-risk" data-testid="employee-risk" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-none bg-rams-orange/10 border border-rams-orange/20 text-rams-orange">
                    <Users className="h-4 w-4" />
                  </div>
                  <div>
                    <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.executive.risk.title')}</CardTitle>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{t('pages.executive.risk.protocol')}</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-8 space-y-10 bg-rams-module relative overflow-hidden">
                <div className="grid gap-8 md:grid-cols-2 relative z-10">
                  <div className="space-y-2">
                    <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.executive.risk.employeeIdentity')}</label>
                    <Input value={employeeName} onChange={(e) => setEmployeeName(e.target.value)} className="bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider" data-testid="risk-employee-name" placeholder={t('pages.executive.risk.namePlaceholder')} />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.executive.risk.departmentNode')}</label>
                    <Input value={department} onChange={(e) => setDepartment(e.target.value)} className="bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider" data-testid="risk-department" placeholder={t('pages.executive.risk.deptPlaceholder')} />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.executive.risk.tenureProtocol')}</label>
                    <Input
                      type="number"
                      value={tenureMonths}
                      onChange={(e) => setTenureMonths(Number(e.target.value))}
                      className="bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                      data-testid="risk-tenure"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.executive.risk.overtimeVelocity')}</label>
                    <Input
                      type="number"
                      value={overtimeHours}
                      onChange={(e) => setOvertimeHours(Number(e.target.value))}
                      className="bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                      data-testid="risk-overtime"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.executive.risk.skipRateIntel')}</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={skipRate}
                      onChange={(e) => setSkipRate(Number(e.target.value))}
                      className="bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                      data-testid="risk-skiprate"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.executive.risk.peerComparisonDelta')}</label>
                    <Input
                      type="number"
                      step="0.1"
                      value={peerComparison}
                      onChange={(e) => setPeerComparison(Number(e.target.value))}
                      className="bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                      data-testid="risk-peer"
                    />
                  </div>
                </div>

                <Button onClick={handleAnalyzeRisk} disabled={riskLoading} className="w-full h-12 rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] relative z-10" data-testid="risk-run">
                  {riskLoading ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      {t('pages.executive.risk.analystReasoning')}
                    </div>
                  ) : (
                    t('pages.executive.risk.executePredictiveModel')
                  )}
                </Button>

                {riskError && (
                  <div className="p-6 bg-rams-red/5 border border-rams-red/20 flex gap-4 animate-in slide-in-from-top-4 duration-500 relative z-10" data-testid="risk-error">
                    <AlertTriangle className="h-5 w-5 text-rams-red shrink-0" />
                    <div className="text-xs font-medium text-rams-red uppercase leading-relaxed">{riskError}</div>
                  </div>
                )}

                {riskResult && (
                  <div className="space-y-8 animate-in fade-in slide-in-from-top-4 duration-700 relative z-10" data-testid="risk-result">
                    <div className="flex flex-col md:flex-row md:items-center justify-between p-8 bg-rams-panel/40 border border-rams-line gap-6">
                      <div className="space-y-1">
                        <div className="text-3xl font-sans font-black uppercase tracking-tight text-foreground/90">{riskResult.employee_name}</div>
                        <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">{t('pages.executive.risk.scoreConfidence')} {riskResult.confidence ? `${(riskResult.confidence * 100).toFixed(1)}%` : 'N/A'}</div>
                      </div>
                      <div className="flex gap-12">
                        <div className="space-y-3">
                          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/40 block">{t('pages.executive.risk.retentionProtocol')}</span>
                          <RiskBadge value={riskResult.retention_risk} />
                        </div>
                        <div className="space-y-3">
                          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/40 block">{t('pages.executive.risk.burnoutThreshold')}</span>
                          <RiskBadge value={riskResult.burnout_risk} />
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-8 md:grid-cols-2">
                       <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
                          <CardContent className="p-8 space-y-8 bg-rams-module">
                             <div className="space-y-3">
                                <div className="flex justify-between text-[10px] font-black uppercase tracking-[0.2em] text-foreground/70">
                                   <span>{t('pages.executive.risk.retentionIndex')}</span>
                                   <span className="font-mono font-bold text-rams-orange">{riskResult.retention_score.toFixed(2)}</span>
                                </div>
                                <Progress value={riskResult.retention_score * 10} className="h-1" indicatorClassName="bg-rams-orange" />
                             </div>
                             <div className="space-y-3">
                                <div className="flex justify-between text-[10px] font-black uppercase tracking-[0.2em] text-foreground/70">
                                   <span>{t('pages.executive.risk.burnoutMagnitude')}</span>
                                   <span className="font-mono font-bold text-rams-red">{riskResult.burnout_score.toFixed(2)}</span>
                                </div>
                                <Progress value={riskResult.burnout_score * 10} className="h-1" indicatorClassName="bg-rams-red" />
                             </div>
                          </CardContent>
                       </Card>

                       <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none bg-rams-module">
                          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.executive.risk.riskFactorsIdentified')}</CardTitle>
                          </CardHeader>
                          <CardContent className="p-6">
                            {(riskResult.risk_factors?.length ?? 0) > 0 ? (
                              <ul className="space-y-3">
                                {riskResult.risk_factors.map((r) => (
                                  <li key={r} className="flex items-start gap-3">
                                    <div className="mt-1.5 h-1.5 w-1.5 bg-rams-orange shrink-0" />
                                    <span className="text-xs font-medium text-foreground/70 uppercase leading-snug">{r}</span>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <div className="flex items-center gap-3 text-muted-foreground/40">
                                <CheckCircle2 className="h-4 w-4" />
                                <p className="text-[10px] font-mono font-black uppercase tracking-widest">{t('pages.executive.risk.noRiskFactors')}</p>
                              </div>
                            )}
                          </CardContent>
                       </Card>
                    </div>
                  </div>
                )}
                <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </PageGuard>
  );
}
