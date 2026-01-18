'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
import { useAuthStore } from '@/stores';
import {
  TrendingUp,
  TrendingDown,
  Brain,
  Target,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Users,
  BarChart3,
  LineChart,
  PieChart,
  Zap,
  Activity,
  Eye,
  Shield,
  Loader2,
  Download,
  Cpu,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { useAnalyticsStore } from '@/stores';
import { cn } from '@/lib/utils';
import { StatCard, StatSection, AmbientStatus, ConfidenceIndicator } from '@/components/ui/stat-card';
import { PageGuard } from '@/components/layout/page-guard';
import { ANALYTICS_ROLES } from '@/lib/page-access';
import { KPI_COLORS, Sparkline } from '@/components/ui/data-visualization';

// Types
interface MLInsight {
  id: string;
  type: 'prediction' | 'anomaly' | 'recommendation' | 'trend';
  title: string;
  description: string;
  confidence: number;
  impact: 'high' | 'medium' | 'low';
  category: string;
  created_at: string;
  model_name: string;
  action_items?: string[];
}

interface PerformanceTrend {
  metric: string;
  current_value: number;
  previous_value: number;
  change_percent: number;
  trend: 'up' | 'down' | 'stable';
  prediction_7d: number;
  prediction_30d: number;
}

export default function AnalyticsPage() {
  const { t } = useI18n();
  const [selectedPeriod, setSelectedPeriod] = React.useState('7d');
  const [activeTab, setActiveTab] = React.useState('overview');
  const { isAuthenticated } = useAuthStore();
  
  const { insights, trends, health, fetchInsights, fetchTrends, fetchHealth, loading: analyticsLoading } = useAnalyticsStore();

  const insightsList = React.useMemo(() => (Array.isArray(insights) ? insights : []), [insights]);
  const trendsList = React.useMemo(() => (Array.isArray(trends) ? trends : []), [trends]);

  React.useEffect(() => {
    if (isAuthenticated) {
      fetchInsights();
      fetchTrends();
      fetchHealth();
    }
  }, [fetchInsights, fetchTrends, fetchHealth, isAuthenticated]);

  const getInsightIcon = (type: MLInsight['type']) => {
    const icons = {
      prediction: TrendingUp,
      anomaly: AlertTriangle,
      recommendation: Target,
      trend: LineChart,
    };
    return icons[type] || Brain;
  };

  const getImpactColor = (impact: string) => {
    const colors = {
      high: 'bg-red-100 text-red-700 border-red-200',
      medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      low: 'bg-blue-100 text-blue-700 border-blue-200',
    };
    return colors[impact as keyof typeof colors] || colors.low;
  };

  const models = health?.models && typeof health.models === 'object'
    ? Object.entries(health.models as Record<string, any>).map(([name, data]: [string, any]) => ({
        model_name: name,
        ...data,
      }))
    : [];

  const oeeTrend = trendsList.find(t => String(t.metric).toLowerCase().includes('oee'));
  const currentOEE = oeeTrend ? oeeTrend.current_value : 0;
  const systemHealth = health?.overall_health_score !== undefined ? (health.overall_health_score * 100).toFixed(1) : "0";

  return (
    <div className="space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90 flex items-center gap-3">
            <Shield className="h-6 w-6 text-rams-orange" />
            {t('pages.analytics.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.analytics.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: ANALYTICS-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
            <SelectTrigger className="w-40 h-10 text-[10px] rounded-rams-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">LAST_24_HOURS</SelectItem>
              <SelectItem value="7d">LAST_7_DAYS</SelectItem>
              <SelectItem value="30d">LAST_30_DAYS</SelectItem>
              <SelectItem value="90d">LAST_90_DAYS</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="default" className="rounded-rams-sm" onClick={() => {}} disabled={analyticsLoading}>
            <Download className="h-3.5 w-3.5 mr-2" />
            EXPORT_INTEL
          </Button>
        </div>
      </div>

      {/* Stats Grid (Industrial Modules) */}
      <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-border bg-rams-border">
        <div className="bg-rams-module p-6 border-r border-b border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.analytics.stats.oee')}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{currentOEE}%</div>
          <div className="flex items-center gap-1 text-[9px] font-mono font-bold uppercase tracking-tighter text-rams-green mt-2">
            {oeeTrend ? (
              <>
                {oeeTrend.trend === 'up' ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {oeeTrend.change_percent > 0 ? '+' : ''}{oeeTrend.change_percent.toFixed(1)}% ALPHA
              </>
            ) : "+2.1% ALPHA"}
          </div>
          <Progress value={currentOEE} className="h-1 mt-4" indicatorClassName="bg-rams-orange" />
        </div>

        <div className="bg-rams-module p-6 border-r border-b border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.analytics.stats.risk')}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">LOW</div>
          <div className="flex items-center gap-1 text-[9px] font-mono font-bold uppercase tracking-tighter text-rams-green mt-2">
            STABLE_GRADIENT
          </div>
          <div className="flex gap-1 mt-4">
            <div className="h-1 flex-1 bg-rams-green" />
            <div className="h-1 flex-1 bg-rams-panel" />
            <div className="h-1 flex-1 bg-rams-panel" />
          </div>
        </div>

        <div className="bg-rams-module p-6 border-r border-b border-rams-border group overflow-hidden relative">
          <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:scale-110 transition-transform">
             <Brain className="h-24 w-24 text-foreground" />
          </div>
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.analytics.stats.insights')}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{insightsList.length}</div>
          <div className="flex items-center gap-1 text-[9px] font-mono font-bold uppercase tracking-tighter text-rams-orange mt-2">
            {insightsList.filter(i => i.impact === 'high').length} HIGH_IMPACT_EVENTS
          </div>
          <div className="mt-4 flex -space-x-1">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-5 w-5 rounded-none bg-rams-panel border border-rams-border flex items-center justify-center text-[8px] font-mono font-black text-muted-foreground">
                AI
              </div>
            ))}
          </div>
        </div>

        <div className="bg-rams-module p-6 border-b border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">HEALTH_INDEX</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{systemHealth}%</div>
          <div className="flex items-center gap-1 text-[9px] font-mono font-bold uppercase tracking-tighter text-rams-green mt-2">
            {parseFloat(systemHealth) > 90 ? "OPTIMAL_VELOCITY" : "DEGRADED_STATE"}
          </div>
          <div className="mt-4 flex gap-0.5 h-6 items-end">
            {(health?.health_history || [4, 6, 5, 8, 7, 9, 8, 10, 9, 10]).map((h: number, i: number) => (
              <div key={i} className="flex-1 bg-rams-orange/40 hover:bg-rams-orange transition-none cursor-help" style={{ height: `${h * 10}%` }} />
            ))}
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="bg-rams-panel border-rams-border p-1 rounded-rams-sm w-fit">
          <TabsTrigger value="overview">OVERVIEW</TabsTrigger>
          <TabsTrigger value="insights">ML_INSIGHTS</TabsTrigger>
          <TabsTrigger value="trends">PREDICTIVE_TRENDS</TabsTrigger>
          <TabsTrigger value="models">MODEL_HEALTH</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6 animate-in fade-in duration-300">
          <Card className="rounded-rams-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-4 w-4 text-rams-orange" />
                    STRATEGIC_INTELLIGENCE_FEED
                  </CardTitle>
                  <CardDescription>AI-generated directives requiring immediate command attention</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {analyticsLoading ? (
                <div className="py-20 text-center text-muted-foreground flex flex-col items-center gap-4">
                  <div className="animate-spin rounded-none h-8 w-8 border border-rams-orange border-t-transparent"></div>
                  <p className="font-mono font-black uppercase tracking-[0.3em] text-[10px]">Sensei AI is reasoning...</p>
                </div>
              ) : insightsList.length > 0 ? (
                insightsList
                  .filter(i => i.impact === 'high')
                  .map((insight) => {
                    const Icon = getInsightIcon(insight.type);
                    return (
                      <div key={insight.id} className="p-5 bg-rams-panel/40 border border-rams-border hover:bg-rams-panel transition-none group">
                        <div className="flex items-start gap-4">
                          <div className="p-2 bg-rams-module border border-rams-border text-muted-foreground group-hover:border-rams-orange group-hover:text-rams-orange transition-none">
                            <Icon className="h-5 w-5" />
                          </div>
                          <div className="flex-1 space-y-3">
                            <div className="flex items-start justify-between">
                              <div>
                                <h4 className="font-sans font-black text-sm uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{insight.title}</h4>
                                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                                  {insight.description}
                                </p>
                              </div>
                              <Badge variant={insight.impact === 'high' ? 'destructive' : 'default'} size="sm">
                                {insight.impact.toUpperCase()}_IMPACT
                              </Badge>
                            </div>
                            <div className="flex items-center gap-4 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                              <div className="flex items-center gap-1">
                                <Eye className="h-3 w-3" />
                                CONFIDENCE: {(insight.confidence * 100).toFixed(0)}%
                              </div>
                              <div className="flex items-center gap-1">
                                <Brain className="h-3 w-3" />
                                {insight.model_name.toUpperCase()}
                              </div>
                              <span className="opacity-30">|</span>
                              <span>CAT: {insight.category.toUpperCase()}</span>
                            </div>
                            {insight.action_items && (
                              <div className="mt-4 p-4 bg-rams-panel border border-rams-border/50">
                                <div className="text-[9px] font-mono font-black uppercase tracking-widest text-rams-orange mb-3">Sensei Recommended Actions:</div>
                                <ul className="space-y-2">
                                  {insight.action_items.map((action, idx) => (
                                    <li key={idx} className="flex items-start gap-3 text-xs font-medium text-foreground/70">
                                      <div className="mt-1.5 h-1.5 w-1.5 bg-rams-orange" />
                                      {action}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
              ) : (
                <div className="py-20 text-center border border-dashed border-rams-border bg-rams-panel/20">
                  <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">No priority insights at this time. Organizational performance is within optimal parameters.</p>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-8 lg:grid-cols-2">
            <Card className="rounded-rams-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LineChart className="h-4 w-4 text-rams-orange" />
                  PREDICTIVE_METRIC_GRADIENTS
                </CardTitle>
                <CardDescription>Current trajectory vs AI forecasted outcome</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {trendsList.slice(0, 3).map((trend) => (
                  <div key={trend.metric} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-black uppercase tracking-[0.2em] text-foreground/70">{trend.metric}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-xl font-mono font-bold text-foreground/90">{trend.current_value}%</span>
                        <Badge 
                          variant={trend.trend === 'up' ? 'default' : trend.trend === 'down' ? 'destructive' : 'secondary'}
                          size="sm"
                        >
                          {trend.trend === 'up' ? <TrendingUp className="h-3 w-3 mr-1" /> : trend.trend === 'down' ? <TrendingDown className="h-3 w-3 mr-1" /> : null}
                          {Math.abs(trend.change_percent).toFixed(1)}%
                        </Badge>
                      </div>
                    </div>
                    <Progress 
                      value={trend.current_value} 
                      className="h-1"
                      indicatorClassName="bg-rams-orange"
                    />
                    <div className="flex justify-between text-[8px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                      <span>HISTORICAL_AVG</span>
                      <span className="text-rams-orange/60">FORECAST (7D): {trend.prediction_7d}%</span>
                    </div>
                  </div>
                ))}
                {trends.length === 0 && <div className="text-center text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 py-12">Establishing data baseline...</div>}
              </CardContent>
            </Card>

            <Card className="rounded-rams-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-rams-orange" />
                  AUTONOMOUS_MODEL_HEALTH
                </CardTitle>
                <CardDescription>Real-time monitoring of inference reliability</CardDescription>
              </CardHeader>
              <CardContent className="space-y-1">
                {models.map((model) => (
                  <div key={model.model_name} className="p-4 bg-rams-panel/40 border border-rams-border/50 flex items-center justify-between hover:bg-rams-panel transition-none group">
                    <div className="flex-1">
                      <div className="text-[11px] font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{model.model_name.replace('_', ' ')} Intelligence</div>
                      <div className="flex items-center gap-3 text-[8px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">
                        <span className="text-rams-green/70">ACCURACY: {((model.accuracy || 0) * 100).toFixed(1)}%</span>
                        <span className="opacity-30">•</span>
                        <span>{model.predictions_today || 0} INFERENCES_TODAY</span>
                      </div>
                    </div>
                    <Badge
                      variant={model.status === 'healthy' ? 'default' : model.status === 'warning' ? 'warning' : 'destructive'}
                      size="sm"
                    >
                      {model.status?.toUpperCase() || 'OPTIMAL'}
                    </Badge>
                  </div>
                ))}
                {models.length === 0 && <div className="text-center text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 py-12">Warming up ML compute clusters...</div>}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="insights" className="space-y-6 animate-in fade-in duration-300">
          <div className="grid gap-6">
            {insightsList.map((insight) => {
              const Icon = getInsightIcon(insight.type);
              return (
                <Card key={insight.id} className="rounded-rams-sm group">
                  <CardContent className="p-8">
                    <div className="flex flex-col md:flex-row items-start gap-8">
                      <div className="p-4 bg-rams-panel border border-rams-border text-muted-foreground group-hover:border-rams-orange group-hover:text-rams-orange transition-none">
                        <Icon className="h-8 w-8" />
                      </div>
                      <div className="flex-1 space-y-6">
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                          <div className="space-y-1">
                            <h3 className="font-sans font-black text-lg uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{insight.title}</h3>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" size="sm" className="text-rams-orange border-rams-orange/20">{insight.type.toUpperCase()}</Badge>
                              <span className="text-[9px] font-mono font-black text-muted-foreground/30 uppercase tracking-widest">Protocol: INSIGHT_{insight.id.substring(0, 4)}</span>
                            </div>
                          </div>
                          <Badge variant={insight.impact === 'high' ? 'destructive' : 'default'} size="lg">
                            {insight.impact.toUpperCase()}_IMPACT_PROTOCOL
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed font-medium">{insight.description}</p>
                        <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
                          <div className="flex items-center gap-2.5 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                            <Eye className="h-3 w-3" />
                            <span>CONFIDENCE_SIGNAL: {(insight.confidence * 100).toFixed(0)}%</span>
                          </div>
                          <div className="flex items-center gap-2.5 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                            <Brain className="h-3 w-3" />
                            <span>MODEL_NODE: {insight.model_name.toUpperCase()}</span>
                          </div>
                          <Badge variant="secondary" size="sm">{insight.category.toUpperCase()}</Badge>
                        </div>
                        {insight.action_items && (
                          <div className="mt-8 p-6 bg-rams-panel border border-rams-border/50 space-y-4">
                            <div className="text-[9px] font-mono font-black uppercase tracking-[0.2em] text-rams-orange flex items-center gap-2">
                              <Target className="h-3.5 w-3.5" />
                              STRATEGIC_COUNTERMEASURES
                            </div>
                            <ul className="grid gap-3">
                              {insight.action_items.map((action, idx) => (
                                <li key={idx} className="flex items-start gap-3">
                                  <div className="h-1.5 w-1.5 bg-rams-orange mt-1.5" />
                                  <span className="text-[11px] font-medium text-foreground/80 leading-snug uppercase">{action}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
            {insightsList.length === 0 && (
              <div className="text-center py-20 industrial-panel bg-rams-panel/20 border-dashed">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-rams-module border border-rams-border mb-6">
                  <Brain className="h-8 w-8 text-muted-foreground/20" />
                </div>
                <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">Sensei AI is synthesizing new intelligence nodes...</p>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="trends" className="space-y-8 animate-in fade-in duration-300">
          <div className="grid gap-6">
            {trendsList.map((trend) => (
              <Card key={trend.metric} className="rounded-rams-sm overflow-hidden group">
                <CardHeader className="border-b border-rams-border bg-rams-panel/30 p-6">
                  <div className="flex items-center justify-between">
                    <CardTitle className="font-sans font-black text-sm uppercase tracking-tight group-hover:text-rams-orange transition-none">{trend.metric} PROTOCOL</CardTitle>
                    <Badge
                      variant={trend.trend === 'up' ? 'default' : trend.trend === 'down' ? 'destructive' : 'secondary'}
                      size="sm"
                    >
                      {trend.trend === 'up' ? <TrendingUp className="h-3 w-3 mr-1" /> : 
                       trend.trend === 'down' ? <TrendingDown className="h-3 w-3 mr-1" /> : null}
                      {Math.abs(trend.change_percent).toFixed(1)}% ALPHA
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-8">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border border-rams-border bg-rams-border">
                    <div className="p-6 bg-rams-module border-r border-rams-border text-center space-y-2">
                      <div className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/40">CURRENT_MAGNITUDE</div>
                      <div className="text-4xl font-mono font-bold tracking-tighter tabular-nums">{trend.current_value}%</div>
                    </div>
                    <div className="p-6 bg-rams-module border-r border-rams-border text-center space-y-2">
                      <div className="text-[9px] font-black uppercase tracking-[0.2em] text-rams-orange/60">7-DAY_PROJECTION</div>
                      <div className="text-4xl font-mono font-bold tracking-tighter text-rams-orange tabular-nums">{trend.prediction_7d}%</div>
                    </div>
                    <div className="p-6 bg-rams-module text-center space-y-2">
                      <div className="text-[9px] font-black uppercase tracking-[0.2em] text-rams-orange/60">30-DAY_PROJECTION</div>
                      <div className="text-4xl font-mono font-bold tracking-tighter text-rams-orange tabular-nums">{trend.prediction_30d}%</div>
                    </div>
                  </div>
                  
                  <div className="mt-8 pt-8 border-t border-rams-border/30">
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Inference Stream Visualization</span>
                      <span className="text-[9px] font-mono font-bold text-rams-orange/40 uppercase">Model: TEMPORAL-CONV-04</span>
                    </div>
                    <div className="h-24 w-full bg-rams-panel/20 border border-rams-border/50 flex items-center justify-center relative overflow-hidden">
                       <Sparkline 
                         data={[trend.previous_value, trend.current_value, trend.prediction_7d, trend.prediction_30d ?? trend.prediction_7d]} 
                         width={800} 
                         height={60} 
                         color={KPI_COLORS.VOLUME} 
                         showArea 
                         className="opacity-60"
                       />
                       <div className="absolute inset-0 perforated-bg opacity-10 pointer-events-none" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {trendsList.length === 0 && (
              <div className="text-center py-20 industrial-panel bg-rams-panel/20 border-dashed">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-rams-module border border-rams-border mb-6">
                  <LineChart className="h-8 w-8 text-muted-foreground/20" />
                </div>
                <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">Sensei AI is training temporal projection models...</p>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="models" className="space-y-8 animate-in fade-in duration-300">
          <div className="grid gap-6">
            {models.map((model) => (
              <Card key={model.model_name} className="rounded-rams-sm overflow-hidden group">
                <CardHeader className="border-b border-rams-border bg-rams-panel/30 p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-rams-module border border-rams-border text-muted-foreground group-hover:border-rams-orange group-hover:text-rams-orange transition-none">
                        <Brain className="h-5 w-5" />
                      </div>
                      <div>
                        <CardTitle className="font-sans font-black text-sm uppercase tracking-tight group-hover:text-rams-orange transition-none">{model.model_name.replace('_', ' ')} INTELLIGENCE</CardTitle>
                        <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">
                          {model.predictions_today || 0} INFERENCES_TODAY • {model.latency_ms || 0}MS_LATENCY
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={model.status === 'healthy' ? 'default' : model.status === 'warning' ? 'warning' : 'destructive'}
                      size="sm"
                    >
                      {model.status?.toUpperCase() || 'OPTIMAL'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-8">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-0 border border-rams-border bg-rams-border">
                    <div className="p-4 bg-rams-module border-r border-b md:border-b-0 border-rams-border text-center space-y-1">
                      <div className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Accuracy</div>
                      <div className="text-2xl font-mono font-bold tabular-nums text-rams-green">{((model.accuracy || 0) * 100).toFixed(1)}%</div>
                    </div>
                    <div className="p-4 bg-rams-module border-r border-b md:border-b-0 border-rams-border text-center space-y-1">
                      <div className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Precision</div>
                      <div className="text-2xl font-mono font-bold tabular-nums">{((model.precision || 0) * 100).toFixed(1)}%</div>
                    </div>
                    <div className="p-4 bg-rams-module border-r border-rams-border text-center space-y-1">
                      <div className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Recall</div>
                      <div className="text-2xl font-mono font-bold tabular-nums">{((model.recall || 0) * 100).toFixed(1)}%</div>
                    </div>
                    <div className="p-4 bg-rams-module text-center space-y-1">
                      <div className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">F1 Score</div>
                      <div className="text-2xl font-mono font-bold tabular-nums">{((model.f1_score || 0) * 100).toFixed(1)}%</div>
                    </div>
                  </div>

                  <div className="mt-8 space-y-4">
                    <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-foreground/70">
                      <span>Neural Compute Stream</span>
                      <Cpu className="h-3.5 w-3.5 opacity-40" />
                    </div>
                    <Progress value={74} className="h-1" indicatorClassName="bg-rams-orange" />
                  </div>
                </CardContent>
              </Card>
            ))}
            {models.length === 0 && (
              <div className="text-center py-20 industrial-panel bg-rams-panel/20 border-dashed">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-rams-module border border-rams-border mb-6">
                  <Cpu className="h-10 w-10 text-muted-foreground/30" />
                </div>
                <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">Warming up distributed ML compute clusters...</p>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
