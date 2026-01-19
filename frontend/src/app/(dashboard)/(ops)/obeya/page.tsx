'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
import {
  Plus,
  Settings,
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  CheckCircle,
  AlertTriangle,
  Users,
  Calendar,
  LayoutGrid,
  MessageSquare,
  FileText,
  Clock,
  ArrowRight,
  MoreHorizontal,
  Shield,
  Award,
  Truck,
  DollarSign,
  Heart,
  Activity,
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import { cn, getInitials } from '@/lib/utils';
import { useObeyaStore } from '@/stores/obeya';
import { Skeleton } from '@/components/ui/skeleton';

function SQDCPCard({ 
  title, 
  icon: Icon, 
  metrics, 
  status 
}: { 
  title: string; 
  icon: React.ElementType; 
  metrics: { label: string; value: string | number; trend?: 'up' | 'down' | 'stable' }[];
  status: 'green' | 'yellow' | 'red';
}) {
  const statusColors = {
    green: 'border-rams-green/30 text-rams-green bg-rams-green/5',
    yellow: 'border-rams-orange/30 text-rams-orange bg-rams-orange/5',
    red: 'border-rams-red/30 text-rams-red bg-rams-red/5',
  };

  const badgeVariants = {
    green: 'success' as const,
    yellow: 'warning' as const,
    red: 'danger' as const,
  };

  return (
    <Card className={cn('rounded-rams-sm border border-rams-line bg-rams-module transition-none group', statusColors[status])}>
      <CardHeader className="pb-4 border-b border-rams-line bg-rams-panel/10">
        <CardTitle className="text-sm font-black uppercase tracking-[0.2em] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Icon className="h-4 w-4" />
            {title}
          </div>
          <Badge variant={badgeVariants[status]} size="sm" className="h-4 px-1">{status.toUpperCase()}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 space-y-1">
        {metrics.map((metric, idx) => (
          <div key={idx} className="flex items-center justify-between p-3 bg-rams-panel/40 border border-rams-line hover:bg-rams-panel transition-none">
            <span className="text-[9px] font-mono font-black uppercase tracking-widest text-muted-foreground/60">{metric.label}</span>
            <div className="flex items-center gap-3">
              <span className="text-xl font-mono font-bold tabular-nums text-foreground/80">{metric.value}</span>
              {metric.trend && (
                metric.trend === 'up' ? <TrendingUp className="h-3.5 w-3.5 text-rams-green" /> :
                metric.trend === 'down' ? <TrendingDown className="h-3.5 w-3.5 text-rams-red" /> :
                <Minus className="h-3.5 w-3.5 opacity-30" />
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function ObeyaPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { 
    cognitiveInsights, 
    isLoading, 
    fetchCognitiveInsights,
    fetchItems,
    connect,
    disconnect,
    items 
  } = useObeyaStore();

  React.useEffect(() => {
    fetchCognitiveInsights();
    fetchItems();
    connect();
    return () => disconnect();
  }, [fetchCognitiveInsights, fetchItems, connect, disconnect]);

  if (isLoading && !cognitiveInsights) {
    return (
      <div className="space-y-6" data-testid="obeya-page">
        <div className="flex items-center justify-between">
          <Skeleton className="h-10 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  const summary = cognitiveInsights?.summary || {
    metrics: { total_tracked: 0, warnings: 0, causal_links: 0 },
    cross_functional: { active_alerts: 0, pending_rebalances: 0 },
    heijunka: { pending_suggestions: 0 }
  };

  const siloAlerts = cognitiveInsights?.silo_alerts || [];
  const rebalanceSuggestions = cognitiveInsights?.resource_rebalancing || [];
  const heijunkaSuggestions = cognitiveInsights?.heijunka_suggestions || [];

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="obeya-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90 flex items-center gap-3">
            <Shield className="h-6 w-6 text-rams-orange" />
            {t('pages.obeya.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.obeya.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: COMMAND-CENTER-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line" onClick={() => fetchCognitiveInsights()} disabled={isLoading}>
            <RefreshCw className={cn("h-3.5 w-3.5 mr-2", isLoading && "animate-spin")} />
            {t('pages.obeya.syncIntel')}
          </Button>
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line">
            <Settings className="h-3.5 w-3.5 mr-2" />
            {t('pages.obeya.parameters')}
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]" onClick={() => router.push('/obeya/new')}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            {t('pages.obeya.initializeBoard')}
          </Button>
        </div>
      </div>

      {/* Tabs for different views */}
      <Tabs defaultValue="overview" className="space-y-8 animate-in fade-in duration-700">
        <TabsList className="bg-rams-panel border border-rams-line p-1 rounded-rams-sm w-fit overflow-x-auto no-scrollbar">
          <TabsTrigger value="overview">{t('pages.obeya.tabs.overview')}</TabsTrigger>
          <TabsTrigger value="intelligence">{t('pages.obeya.tabs.senseiAi')}</TabsTrigger>
          <TabsTrigger value="sqdcp">{t('pages.obeya.tabs.sqdcpDetail')}</TabsTrigger>
          <TabsTrigger value="exceptions">{t('pages.obeya.tabs.exceptions')}</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-line bg-rams-line">
            <Card className="rounded-none border-0 border-r border-b lg:border-b-0 bg-rams-module p-6 hover:bg-rams-panel/50 transition-none group">
              <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.obeya.predictiveBreaches')}</p>
              <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{summary.metrics.warnings}</div>
              <p className="text-[9px] font-mono font-bold uppercase text-rams-orange mt-2 flex items-center gap-1">
                <TrendingDown className="h-3 w-3" /> TRENDING_TOWARD_RED
              </p>
            </Card>
            <Card className="rounded-none border-0 border-r border-b lg:border-b-0 bg-rams-module p-6 hover:bg-rams-panel/50 transition-none group">
              <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.obeya.siloBottlenecks')}</p>
              <div className="text-3xl font-mono font-bold tracking-tight text-rams-red tabular-nums">{summary.cross_functional.active_alerts}</div>
              <p className="text-[9px] font-mono font-bold uppercase text-rams-red mt-2 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" /> INTER-DEPT_FRICTION
              </p>
            </Card>
            <Card className="rounded-none border-0 border-r border-b md:border-b-0 bg-rams-module p-6 hover:bg-rams-panel/50 transition-none group">
              <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.obeya.rebalanceOps')}</p>
              <div className="text-3xl font-mono font-bold tracking-tight text-rams-steel tabular-nums">{summary.cross_functional.pending_rebalances}</div>
              <p className="text-[9px] font-mono font-bold uppercase text-rams-steel mt-2 flex items-center gap-1">
                <Users className="h-3 w-3" /> SKILL_GAP_NODES
              </p>
            </Card>
            <Card className="rounded-none border-0 bg-rams-module p-6 hover:bg-rams-panel/50 transition-none group">
              <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.obeya.heijunkaTips')}</p>
              <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{summary.heijunka.pending_suggestions}</div>
              <p className="text-[9px] font-mono font-bold uppercase text-rams-green mt-2 flex items-center gap-1">
                <Activity className="h-3 w-3" /> SMOOTHING_PROTOCOLS
              </p>
            </Card>
          </div>

          <div className="grid gap-8 lg:grid-cols-2">
            <Card className="rounded-rams-sm overflow-hidden border-rams-line">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                  <Activity className="h-4 w-4 text-rams-orange" />
                  {t('pages.obeya.primaryNorthStars')}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-6">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-black uppercase tracking-widest text-foreground/70">First Pass Yield</span>
                    <span className="text-sm font-mono font-bold tabular-nums text-rams-green">98.1%</span>
                  </div>
                  <Progress value={98.1} className="h-1" indicatorClassName="bg-rams-green" />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-black uppercase tracking-widest text-foreground/70">On-Time Delivery</span>
                    <span className="text-sm font-mono font-bold tabular-nums text-rams-orange">94.2%</span>
                  </div>
                  <Progress value={94.2} className="h-1" indicatorClassName="bg-rams-orange" />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-black uppercase tracking-widest text-foreground/70">Customer Satisfaction</span>
                    <span className="text-sm font-mono font-bold tabular-nums text-rams-green">4.6/5.0</span>
                  </div>
                  <Progress value={92} className="h-1" indicatorClassName="bg-rams-green" />
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-rams-sm overflow-hidden border-rams-line">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                  <Shield className="h-4 w-4 text-rams-orange" />
                  {t('pages.obeya.recentSiloAlerts')}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-rams-line/30">
                  {siloAlerts.map((alert: any) => (
                    <div key={alert.alert_id} className="flex items-start gap-4 p-4 hover:bg-rams-panel transition-none group">
                      <div className={cn(
                        "mt-0.5 p-2 rounded-rams-sm border border-rams-line",
                        alert.severity === 'critical' ? 'bg-rams-red/5 text-rams-red border-rams-red/20' : 'bg-rams-orange/5 text-rams-orange border-rams-orange/20'
                      )}>
                        <AlertTriangle className="h-4 w-4" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{alert.impact}</p>
                          <Badge variant={alert.severity === 'critical' ? 'danger' : 'warning'} size="sm" className="h-4">{alert.severity.toUpperCase()}</Badge>
                        </div>
                        <p className="text-[10px] text-muted-foreground mt-1">SOURCE: {alert.source.toUpperCase()} → IMPACTING: {alert.affected.toUpperCase()}</p>
                        <p className="text-[9px] font-mono italic mt-2 opacity-0 group-hover:opacity-100 transition-opacity">"{alert.event}"</p>
                      </div>
                    </div>
                  ))}
                  {siloAlerts.length === 0 && (
                    <div className="py-12 text-center text-muted-foreground/20">
                      <CheckCircle className="h-8 w-8 mx-auto mb-2 opacity-20" />
                      <p className="text-[9px] font-mono font-black uppercase tracking-widest">ZERO_ACTIVE_SILO_ALERTS</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Intelligence Tab */}
        <TabsContent value="intelligence" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="grid gap-8 lg:grid-cols-2">
            <Card className="rounded-rams-sm overflow-hidden border-rams-line">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                    <Users className="h-4 w-4 text-rams-orange" />
                    {t('pages.obeya.resourceRebalancing')}
                  </CardTitle>
                  <Badge variant="default" className="animate-pulse h-4 px-1 text-[8px] font-black uppercase">AI_SYNC</Badge>
                </div>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                {rebalanceSuggestions.map((s: any) => (
                  <div key={s.suggestion_id} className="p-4 bg-rams-panel/40 border border-rams-line space-y-4 group hover:bg-rams-panel transition-none">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="font-mono text-[9px] rounded-none border-rams-line h-4">{s.from_work_center}</Badge>
                        <ArrowRight className="h-3 w-3 text-muted-foreground/40" />
                        <Badge variant="default" className="font-mono text-[9px] rounded-none h-4">{s.to_work_center}</Badge>
                      </div>
                      <div className="text-right">
                        <p className="text-[8px] text-muted-foreground/40 uppercase font-black tracking-widest">IMPROVEMENT</p>
                        <p className="text-lg font-mono font-bold text-rams-green tabular-nums">+{Math.round(s.expected_improvement * 100)}%</p>
                      </div>
                    </div>
                    <p className="text-xs font-medium leading-relaxed text-foreground/70 uppercase">{s.reason}</p>
                    <div className="space-y-2">
                      <p className="text-[8px] uppercase font-black tracking-widest text-muted-foreground/40">RECOMMENDED_OPERATORS</p>
                      <div className="flex flex-wrap gap-2">
                        {s.operators.map((op: string) => (
                          <div key={op} className="flex items-center gap-2 bg-rams-module border border-rams-line px-2 py-1 rounded-none text-[10px] font-bold uppercase">
                            <Avatar className="h-4 w-4 rounded-none border border-rams-line">
                              <AvatarFallback className="text-[8px] font-mono">{getInitials(op)}</AvatarFallback>
                            </Avatar>
                            {op}
                          </div>
                        ))}
                      </div>
                    </div>
                    <Button size="sm" className="w-full rounded-none h-8 text-[9px] font-black uppercase tracking-widest">EXECUTE_DEPLOYMENT</Button>
                  </div>
                ))}
                {rebalanceSuggestions.length === 0 && (
                  <div className="text-center py-16 text-muted-foreground/20">
                    <Users className="h-12 w-12 mx-auto mb-4 opacity-10" />
                    <p className="text-[9px] font-mono font-black uppercase tracking-widest">Skill nodes optimized across all work centers</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="rounded-rams-sm overflow-hidden border-rams-line">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                    <Activity className="h-4 w-4 text-rams-green" />
                    {t('pages.obeya.heijunkaLeveling')}
                  </CardTitle>
                  <Badge variant="success" className="h-4 px-1 text-[8px] font-black uppercase">PRESCRIPTIVE</Badge>
                </div>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                {heijunkaSuggestions.map((s: any) => (
                  <div key={s.suggestion_id} className="p-4 bg-rams-green/5 border border-rams-green/20 space-y-4 group hover:bg-rams-green/10 transition-none">
                    <div className="flex items-center justify-between">
                      <Badge variant="success" className="uppercase tracking-tighter text-[9px] rounded-none h-4">{s.period} HORIZON</Badge>
                      <div className="text-right">
                        <p className="text-[8px] text-rams-green/60 uppercase font-black tracking-widest">MURA_REDUCTION</p>
                        <p className="text-lg font-mono font-bold text-rams-green tabular-nums">-{Math.round(s.mura_reduction)}%</p>
                      </div>
                    </div>
                    <p className="text-xs font-medium leading-relaxed text-foreground/70 uppercase">{s.reasoning}</p>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40">Current Pattern</p>
                        <div className="h-12 w-full bg-rams-panel rounded-none flex items-end gap-0.5 p-1 border border-rams-line">
                          {[40, 80, 20, 90, 30].map((h, i) => <div key={i} className="flex-1 bg-rams-red/40" style={{height: `${h}%`}} />)}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <p className="text-[8px] font-black uppercase tracking-widest text-rams-green/60">Suggested Pattern</p>
                        <div className="h-12 w-full bg-rams-green/10 rounded-none flex items-end gap-0.5 p-1 border border-rams-green/20">
                          {[50, 55, 48, 52, 53].map((h, i) => <div key={i} className="flex-1 bg-rams-green/40" style={{height: `${h}%`}} />)}
                        </div>
                      </div>
                    </div>
                    <Button size="sm" variant="success" className="w-full rounded-none h-8 text-[9px] font-black uppercase tracking-widest">APPLY_SMOOTHING</Button>
                  </div>
                ))}
                {heijunkaSuggestions.length === 0 && (
                  <div className="text-center py-16 text-muted-foreground/20">
                    <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-10" />
                    <p className="text-[9px] font-mono font-black uppercase tracking-widest">Production mix is sufficiently leveled</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="sqdcp" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            <SQDCPCard
              title="Quality"
              icon={Award}
              status="green"
              metrics={[
                { label: 'First Pass Yield', value: `98.1%`, trend: 'up' },
                { label: 'Defect Rate', value: `1.9%`, trend: 'down' },
                { label: 'Open NCRs', value: summary.metrics.total_tracked > 0 ? 3 : 0 },
              ]}
            />
            <SQDCPCard
              title="Delivery"
              icon={Truck}
              status="yellow"
              metrics={[
                { label: 'On-Time Delivery', value: `94.2%`, trend: 'down' },
                { label: 'Backlog Items', value: 23 },
              ]}
            />
            <div className="col-span-full py-12 text-center industrial-panel bg-rams-panel/20 border-dashed">
              <RefreshCw className="h-8 w-8 mx-auto mb-4 animate-spin text-muted-foreground/20" />
              <p className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-muted-foreground/40">Switching to real-time shop floor sensor fusion...</p>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="exceptions" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="rounded-rams-sm overflow-hidden border-rams-line">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">Anomalies & Exceptions</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-rams-line/30">
                {items.filter(i => i.status === 'blocked' || i.is_escalated).map(item => (
                  <div key={item.id} className="flex items-center gap-4 p-4 hover:bg-rams-panel transition-none group">
                    <div className="p-2 rounded-rams-sm bg-rams-red/5 text-rams-red border border-rams-red/20 group-hover:bg-rams-red group-hover:text-white transition-none">
                      <AlertTriangle className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{item.title}</p>
                        <Badge variant="destructive" size="sm">{item.status.toUpperCase()}</Badge>
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-1 uppercase">{item.blocked_reason || item.escalation_reason || 'Pending action'}</p>
                    </div>
                  </div>
                ))}
                {items.filter(i => i.status === 'blocked' || i.is_escalated).length === 0 && (
                  <div className="flex items-center gap-4 p-8 justify-center">
                    <CheckCircle className="h-5 w-5 text-rams-green opacity-40" />
                    <p className="text-[9px] font-mono font-black uppercase tracking-widest text-muted-foreground/40">Zero critical exceptions identified</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
