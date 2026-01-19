'use client';

import * as React from 'react';
import {
  AlertTriangle,
  Clock,
  TrendingUp,
  AlertCircle,
  Calendar,
  User,
  Target,
  CheckCircle2,
  Ban,
  Download,
  RefreshCw,
  Filter,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { useExceptionsStore } from '@/stores/exceptions';
import { useI18n } from '@/contexts/i18n-context';
import { cn } from '@/lib/utils';
import type { ExceptionSeverity, ExceptionCategory, ExceptionStatus } from '@/stores/exceptions';

export default function ExceptionsPage() {
  const { t } = useI18n();
  const { 
    exceptions, 
    stats, 
    trends, 
    isLoading, 
    fetchExceptions, 
    fetchStats, 
    fetchTrends,
    resolveException 
  } = useExceptionsStore();

  const [activeTab, setActiveTab] = React.useState('overview');
  const [selectedCategory, setSelectedCategory] = React.useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = React.useState<string>('all');
  const [selectedStatus, setSelectedStatus] = React.useState<string>('open');

  const exceptionsList = React.useMemo(() => (Array.isArray(exceptions) ? exceptions : []), [exceptions]);
  const trendsList = React.useMemo(() => (Array.isArray(trends) ? trends : []), [trends]);

  React.useEffect(() => {
    fetchExceptions();
    fetchStats();
    fetchTrends();
  }, [fetchExceptions, fetchStats, fetchTrends]);

  const handleRefresh = async () => {
    await Promise.all([
      fetchExceptions({
        category: selectedCategory !== 'all' ? selectedCategory as any : undefined,
        severity: selectedSeverity !== 'all' ? selectedSeverity as any : undefined,
        status: selectedStatus !== 'all' ? selectedStatus as any : undefined,
      }),
      fetchStats(),
      fetchTrends()
    ]);
  };

  const handleExport = () => {
    const csvContent = exceptions.map(e => 
      `${e.id},${e.title},${e.severity},${e.status},${e.category}`
    ).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'exceptions-export.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const getSeverityColor = (severity: ExceptionSeverity): string => {
    const colors = {
      critical: 'bg-rams-red/10 text-rams-red border-rams-red/20',
      high: 'bg-rams-orange/10 text-rams-orange border-rams-orange/20',
      medium: 'bg-rams-panel text-foreground/70 border-rams-line',
      low: 'bg-rams-steel/10 text-rams-steel border-rams-steel/20',
    };
    return colors[severity];
  };

  const getStatusBadgeVariant = (status: ExceptionStatus): 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning' => {
    const variants: Record<ExceptionStatus, 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'> = {
      open: 'destructive',
      acknowledged: 'warning',
      in_progress: 'default',
      resolved: 'success',
      escalated: 'destructive',
    };
    return variants[status];
  };

  const getCategoryIcon = (category: ExceptionCategory) => {
    const icons = {
      andon: AlertTriangle,
      quote: Target,
      production: AlertCircle,
      quality: Ban,
      a3: Target,
      obeya: Target,
      task: CheckCircle2,
      training: User,
    };
    return icons[category] || AlertCircle;
  };

  const isOverdue = (dueDate: string): boolean => {
    return new Date(dueDate) < new Date();
  };

  const formatRelativeTime = (timestamp: string): string => {
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const formatDate = (timestamp: string): string => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filteredExceptions = exceptionsList.filter(exc => {
    if (selectedCategory !== 'all' && exc.category !== selectedCategory) return false;
    if (selectedSeverity !== 'all' && exc.severity !== selectedSeverity) return false;
    if (selectedStatus !== 'all' && exc.status !== selectedStatus) return false;
    return true;
  });

  if (!stats) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 animate-in fade-in duration-700 bg-rams-chassis">
      <div className="relative">
        <div className="h-20 w-20 bg-rams-module flex items-center justify-center border border-rams-line">
          <div className="h-10 w-10 bg-rams-orange text-black flex items-center justify-center font-mono font-black text-2xl border border-black/10">
            !
          </div>
        </div>
        <div className="absolute -inset-4 border border-rams-orange/20 animate-pulse" />
      </div>
      
      <div className="space-y-4 text-center">
        <h2 className="text-[10px] font-mono font-black uppercase tracking-[0.3em] text-foreground/60">
          AUDITING_ANOMALIES...
        </h2>
        <div className="flex items-center justify-center gap-1">
          <div className="h-1 w-4 bg-rams-orange animate-pulse" />
          <div className="h-1 w-4 bg-rams-orange animate-pulse [animation-delay:150ms]" />
          <div className="h-1 w-4 bg-rams-orange animate-pulse [animation-delay:300ms]" />
        </div>
        <p className="text-[9px] font-mono text-muted-foreground/40 uppercase tracking-widest pt-4">Synchronizing operational exceptions</p>
      </div>
    </div>
  );

  const byCategory = stats.by_category ?? {};

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="exceptions-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.exceptions.title') || 'Anomalous Node Registry'}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.exceptions.subtitle') || 'Exception tracking and escalation protocol'}</span>
            <span className="opacity-30">|</span>
            <span>STATION: OPS-EXCEPTION-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={cn("h-3.5 w-3.5 mr-2", isLoading && "animate-spin")} />
            {t('pages.exceptions.syncIntel') || 'Sync Intel'}
          </Button>
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line" onClick={handleExport}>
            <Download className="h-3.5 w-3.5 mr-2" />
            {t('pages.exceptions.exportProtocol') || 'Export Protocol'}
          </Button>
        </div>
      </div>

      {/* Stats Grid (Industrial Modules) */}
      <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-line bg-rams-line">
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.exceptions.criticalOpenNodes') || 'Critical Open Nodes'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-red tabular-nums">{stats.critical_count}</div>
          <p className="text-[9px] font-mono font-bold text-rams-red uppercase tracking-widest mt-2">{stats.total_open} TOTAL_OPEN</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.exceptions.overdueProtocols') || 'Overdue Protocols'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{stats.overdue_count}</div>
          <p className="text-[9px] font-mono font-bold text-rams-orange uppercase tracking-widest mt-2">SLA_VARIANCE_DETECTED</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-line group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.exceptions.escalatedNodes') || 'Escalated Nodes'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.escalated_count}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">MGMT_SYNC_REQUIRED</p>
        </div>
        <div className="bg-rams-module p-6 border-b md:border-b-0 border-rams-line group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.exceptions.meanResolution') || 'Mean Resolution'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{Math.floor(stats.avg_resolution_time_minutes / 60)}h {stats.avg_resolution_time_minutes % 60}m</div>
          <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">{stats.resolved_today} RESOLVED_TODAY</p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-8 animate-in fade-in duration-700">
        <TabsList className="bg-rams-panel border border-rams-line p-1 rounded-rams-sm w-fit overflow-x-auto no-scrollbar">
          <TabsTrigger value="overview">{t('pages.exceptions.tabs.overview')}</TabsTrigger>
          <TabsTrigger value="critical">{t('pages.exceptions.tabs.criticalOnly')}</TabsTrigger>
          <TabsTrigger value="trends">{t('pages.exceptions.tabs.temporalTrends')}</TabsTrigger>
          <TabsTrigger value="by-category">{t('pages.exceptions.tabs.byCategory')}</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          {/* Filters */}
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="flex flex-1 items-center gap-4 flex-wrap max-w-4xl">
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger className="w-[160px] h-10 text-[10px]">
                  <Filter className="mr-2 h-3.5 w-3.5 opacity-40" />
                  <SelectValue placeholder="CATEGORY" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('pages.exceptions.filters.allCategories')}</SelectItem>
                  <SelectItem value="andon">{t('pages.exceptions.filters.andonSignals')}</SelectItem>
                  <SelectItem value="quote">{t('pages.exceptions.filters.quoteBreaches')}</SelectItem>
                  <SelectItem value="production">{t('pages.exceptions.filters.prodVariances')}</SelectItem>
                  <SelectItem value="quality">{t('pages.exceptions.filters.qualityAnomalies')}</SelectItem>
                  <SelectItem value="a3">{t('pages.exceptions.filters.a3Problems')}</SelectItem>
                  <SelectItem value="obeya">{t('pages.exceptions.filters.obeyaSyclos')}</SelectItem>
                  <SelectItem value="task">{t('pages.exceptions.filters.taskDelays')}</SelectItem>
                  <SelectItem value="training">{t('pages.exceptions.filters.trainingGaps')}</SelectItem>
                </SelectContent>
              </Select>

              <Select value={selectedSeverity} onValueChange={setSelectedSeverity}>
                <SelectTrigger className="w-[160px] h-10 text-[10px]">
                  <AlertCircle className="mr-2 h-3.5 w-3.5 opacity-40" />
                  <SelectValue placeholder="SEVERITY" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('pages.exceptions.filters.allSeverities')}</SelectItem>
                  <SelectItem value="critical">{t('pages.exceptions.filters.criticalOnly')}</SelectItem>
                  <SelectItem value="high">{t('pages.exceptions.filters.highSeverity')}</SelectItem>
                  <SelectItem value="medium">{t('pages.exceptions.filters.mediumSeverity')}</SelectItem>
                  <SelectItem value="low">{t('pages.exceptions.filters.lowSeverity')}</SelectItem>
                </SelectContent>
              </Select>

              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger className="w-[160px] h-10 text-[10px]">
                  <Clock className="mr-2 h-3.5 w-3.5 opacity-40" />
                  <SelectValue placeholder="STATUS" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('pages.exceptions.filters.allStatus')}</SelectItem>
                  <SelectItem value="open">{t('pages.exceptions.filters.openProtocol')}</SelectItem>
                  <SelectItem value="acknowledged">{t('pages.exceptions.filters.acknowledged')}</SelectItem>
                  <SelectItem value="in_progress">{t('pages.exceptions.filters.inProgress')}</SelectItem>
                  <SelectItem value="escalated">{t('pages.exceptions.filters.escalated')}</SelectItem>
                  <SelectItem value="resolved">{t('pages.exceptions.filters.resolved')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Exceptions Table */}
          <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.exceptions.protocolRegistry')} ({filteredExceptions.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('pages.exceptions.table.severity')}</TableHead>
                    <TableHead>{t('pages.exceptions.table.descriptionProtocol')}</TableHead>
                    <TableHead>{t('pages.exceptions.table.categoryNode')}</TableHead>
                    <TableHead>{t('pages.exceptions.table.ownerSync')}</TableHead>
                    <TableHead>{t('pages.exceptions.table.statusNode')}</TableHead>
                    <TableHead>{t('pages.exceptions.table.pulseDetection')}</TableHead>
                    <TableHead>{t('pages.exceptions.table.horizon')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredExceptions.map((exception) => {
                    const CategoryIcon = getCategoryIcon(exception.category);
                    const overdue = isOverdue(exception.due_date);

                    return (
                      <TableRow key={exception.id} className={cn("transition-none", overdue && "bg-rams-red/5")}>
                        <TableCell>
                          <Badge variant="outline" className={cn("rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4", getSeverityColor(exception.severity))}>
                            {exception.severity.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 leading-snug">{exception.title}</div>
                            <div className="text-[10px] text-muted-foreground mt-1 uppercase line-clamp-1">{exception.description}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <CategoryIcon className="h-3.5 w-3.5 text-muted-foreground/40" />
                            <span className="text-[10px] font-bold text-muted-foreground/60 uppercase">{exception.category}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="text-[10px] font-black uppercase tracking-widest text-foreground/70">{exception.owner}</div>
                            <div className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase">{exception.department}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getStatusBadgeVariant(exception.status)} size="sm">
                            {exception.status.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="text-[10px] font-mono text-muted-foreground/60 uppercase">{formatRelativeTime(exception.created_at).toUpperCase()}</div>
                        </TableCell>
                        <TableCell>
                          <div className={cn("text-[10px] font-mono uppercase tracking-tighter", overdue ? 'text-rams-red' : 'text-muted-foreground/60')}>
                            {formatDate(exception.due_date)}
                            {overdue && (
                              <div className="text-[8px] font-black tracking-widest">OVERDUE_BREACH</div>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Critical Only Tab */}
        <TabsContent value="critical" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="rounded-rams-sm overflow-hidden border-rams-red/30 bg-rams-red/5">
            <CardHeader className="bg-rams-red/10 border-b border-rams-red/20">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] text-rams-red flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                {t('pages.exceptions.highUrgencyDeviations') || 'High Urgency Deviations'}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-rams-red/10">
                {exceptionsList.filter(e => e.severity === 'critical' || e.severity === 'high').map(e => (
                  <div key={e.id} className="p-6 flex items-start gap-6 hover:bg-rams-red/10 transition-none group">
                    <div className="p-3 bg-rams-red text-white rounded-none shadow-[2px_2px_0_0_rgba(0,0,0,0.2)]">
                      <AlertCircle className="h-6 w-6" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-4">
                        <h3 className="font-sans font-black text-sm uppercase tracking-tight text-foreground/90 group-hover:text-rams-red transition-none">{e.title}</h3>
                        <Badge variant="destructive" size="lg" className="rounded-none h-5 px-2">{e.severity.toUpperCase()}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2 leading-relaxed font-medium uppercase">{e.description}</p>
                      <div className="flex flex-wrap items-center gap-6 mt-6">
                        <div className="flex items-center gap-2 text-[9px] font-mono font-black uppercase tracking-widest text-muted-foreground/40">
                          <User className="h-3 w-3" /> {e.owner}
                        </div>
                        <div className="flex items-center gap-2 text-[9px] font-mono font-black uppercase tracking-widest text-muted-foreground/40">
                          <Target className="h-3 w-3" /> {e.category.toUpperCase()}
                        </div>
                        <div className="flex items-center gap-2 text-[9px] font-mono font-black uppercase tracking-widest text-rams-red/60">
                          <Clock className="h-3 w-3" /> DUE {formatRelativeTime(e.due_date).toUpperCase()}
                        </div>
                      </div>
                    </div>
                    <Button size="default" className="rounded-rams-sm bg-rams-red text-white font-black uppercase tracking-widest text-[10px] h-10 px-6 hover:bg-rams-red/90" onClick={() => resolveException(e.id, 'Resolved via quick action')}>
                      RESOLVE_NODE
                    </Button>
                  </div>
                ))}
                {exceptionsList.filter(e => e.severity === 'critical' || e.severity === 'high').length === 0 && (
                  <div className="py-24 text-center">
                    <CheckCircle2 className="h-12 w-12 text-rams-green/20 mx-auto mb-4" />
                    <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">Zero high-urgency nodes identified</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Temporal Trends Tab */}
        <TabsContent value="trends" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="grid gap-8 lg:grid-cols-2">
            <Card className="rounded-rams-sm overflow-hidden border-rams-line">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-rams-orange" />
                  Exception Intensity Trend
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-4">
                  {trendsList.map((trend) => (
                    <div key={trend.period}>
                      <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest mb-2">
                        <span className="text-foreground/70">{trend.period}</span>
                        <span className="font-mono text-muted-foreground/40">
                          {trend.critical + trend.high + trend.medium + trend.low} NODES_LOGGED
                        </span>
                      </div>
                      <div className="flex gap-0.5 h-6">
                        <div
                          className="bg-rams-red"
                          style={{ width: `${(trend.critical / 50) * 100}%` }}
                          title={`${trend.critical} critical`}
                        />
                        <div
                          className="bg-rams-orange"
                          style={{ width: `${(trend.high / 50) * 100}%` }}
                          title={`${trend.high} high`}
                        />
                        <div
                          className="bg-rams-steel"
                          style={{ width: `${(trend.medium / 50) * 100}%` }}
                          title={`${trend.medium} medium`}
                        />
                        <div
                          className="bg-rams-panel"
                          style={{ width: `${(trend.low / 50) * 100}%` }}
                          title={`${trend.low} low`}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex gap-6 mt-8 pt-6 border-t border-rams-line text-[9px] font-black uppercase tracking-widest">
                  <div className="flex items-center gap-2 text-rams-red">
                    <div className="w-2 h-2 bg-rams-red" />
                    Critical
                  </div>
                  <div className="flex items-center gap-2 text-rams-orange">
                    <div className="w-2 h-2 bg-rams-orange" />
                    High
                  </div>
                  <div className="flex items-center gap-2 text-foreground/60">
                    <div className="w-2 h-2 bg-rams-steel" />
                    Medium
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground/40">
                    <div className="w-2 h-2 bg-rams-panel border border-rams-line" />
                    Low
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-rams-sm overflow-hidden border-rams-line">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                  <Target className="h-4 w-4 text-rams-green" />
                  Resolution Performance Pulse
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-4">
                  {trendsList.map((trend) => (
                    <div key={trend.period}>
                      <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest mb-2">
                        <span className="text-foreground/70">{trend.period}</span>
                        <span className="font-mono text-rams-green">
                          {trend.resolved} NODES_CLEARED
                        </span>
                      </div>
                      <div className="h-1.5 bg-rams-panel border border-rams-line overflow-hidden">
                        <div 
                          className="h-full bg-rams-green transition-all duration-1000" 
                          style={{ width: `${(trend.resolved / 40) * 100}%` }} 
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* By Category Tab */}
        <TabsContent value="by-category" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="grid gap-px border border-rams-line bg-rams-line sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(byCategory).map(([category, count]) => {
              const CategoryIcon = getCategoryIcon(category as ExceptionCategory);
              return (
                <div key={category} className="bg-rams-module p-8 hover:bg-rams-panel transition-none group cursor-help">
                  <div className="flex items-center justify-between mb-6">
                    <div className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/50 group-hover:text-rams-orange transition-none">{category.toUpperCase()}</div>
                    <CategoryIcon className="h-4 w-4 text-muted-foreground/40 group-hover:text-rams-orange transition-none" />
                  </div>
                  <div className="text-4xl font-mono font-bold tracking-tighter text-foreground/90 tabular-nums">{count}</div>
                  <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/30 mt-2">
                    {((count / stats.total_open) * 100).toFixed(1)}% OF_TOTAL_VOLUME
                  </p>
                </div>
              );
            })}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
