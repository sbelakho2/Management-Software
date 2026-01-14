'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
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
import { PageGuard } from '@/components/layout/page-guard';
import { ANALYTICS_ROLES } from '@/lib/page-access';

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
    <div className="space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 flex items-center gap-3">
            <Shield className="h-10 w-10 text-primary" />
            North Star Intelligence
          </h1>
          <p className="text-muted-foreground font-medium">
            Unified organizational intelligence and strategic cross-gate analytics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
            <SelectTrigger className="w-40 h-11 rounded-xl bg-background/50 border-border/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">Last 24 Hours</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
              <SelectItem value="90d">Last 90 Days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            <Download className="h-4 w-4 mr-2" />
            Export Intel
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-primary/5 border-primary/20 hover:shadow-glow-primary transition-all">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-primary/60">Organizational OEE</CardTitle>
            <Activity className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight">{currentOEE}%</div>
            <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-success mt-1">
              {oeeTrend ? (
                <>
                  {oeeTrend.trend === 'up' ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  {oeeTrend.change_percent > 0 ? '+' : ''}{oeeTrend.change_percent.toFixed(1)}% Alpha
                </>
              ) : "+2.1% Alpha"}
            </div>
            <Progress value={currentOEE} className="h-1.5 mt-4" />
          </CardContent>
        </Card>

        <Card className="bg-success/5 border-success/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-success/60">Strategic Risk</CardTitle>
            <Shield className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight text-success">LOW</div>
            <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-success mt-1">
              Stable Gradient
            </div>
            <div className="flex gap-1 mt-4">
              <div className="h-1.5 flex-1 rounded-full bg-success shadow-[0_0_8px_rgba(34,197,94,0.4)]" />
              <div className="h-1.5 flex-1 rounded-full bg-muted" />
              <div className="h-1.5 flex-1 rounded-full bg-muted" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-primary/5 border-primary/20 overflow-hidden relative group">
          <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:scale-110 transition-transform">
             <Brain className="h-24 w-24 text-primary" />
          </div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-primary/60">AI Insights</CardTitle>
            <Brain className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight">{insights.length}</div>
            <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-warning mt-1">
              {insights.filter(i => i.impact === 'high').length} High Impact
            </div>
            <div className="mt-4 flex -space-x-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-6 w-6 rounded-full bg-primary/20 border-2 border-background flex items-center justify-center text-[10px] font-bold text-primary">
                  AI
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-primary/5 border-primary/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-primary/60">Health Index</CardTitle>
            <Activity className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight">{systemHealth}%</div>
            <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-success mt-1">
              {parseFloat(systemHealth) > 90 ? "OPTIMAL VELOCITY" : "DEGRADED"}
            </div>
            <div className="mt-4 flex gap-0.5 h-6 items-end">
              {(health?.health_history || [4, 6, 5, 8, 7, 9, 8, 10, 9, 10]).map((h: number, i: number) => (
                <div key={i} className="flex-1 bg-primary/40 rounded-t-sm hover:bg-primary transition-colors cursor-help" style={{ height: `${h * 10}%` }} />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="bg-muted/50 p-1 rounded-xl h-12 border border-border/10 w-fit">
          <TabsTrigger value="overview" className="rounded-lg px-6 h-10 data-[state=active]:shadow-premium data-[state=active]:bg-primary data-[state=active]:text-primary-foreground transition-all">Overview</TabsTrigger>
          <TabsTrigger value="insights" className="rounded-lg px-6 h-10 data-[state=active]:shadow-premium data-[state=active]:bg-primary data-[state=active]:text-primary-foreground transition-all">ML Insights</TabsTrigger>
          <TabsTrigger value="trends" className="rounded-lg px-6 h-10 data-[state=active]:shadow-premium data-[state=active]:bg-primary data-[state=active]:text-primary-foreground transition-all">Predictive Trends</TabsTrigger>
          <TabsTrigger value="models" className="rounded-lg px-6 h-10 data-[state=active]:shadow-premium data-[state=active]:bg-primary data-[state=active]:text-primary-foreground transition-all">Model Health</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="premium-glass">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xl flex items-center gap-2">
                    <Zap className="h-5 w-5 text-primary fill-primary" />
                    Strategic Intelligence Feed
                  </CardTitle>
                  <CardDescription>AI-generated directives requiring immediate command attention</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {analyticsLoading ? (
                <div className="py-20 text-center text-muted-foreground flex flex-col items-center gap-4">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <p className="font-bold uppercase tracking-widest text-xs">Sensei AI is reasoning...</p>
                </div>
              ) : insights.length > 0 ? (
                insights
                  .filter(i => i.impact === 'high')
                  .map((insight) => {
                    const Icon = getInsightIcon(insight.type);
                    return (
                      <div key={insight.id} className="p-5 rounded-2xl bg-muted/30 border border-border/10 hover:bg-muted/50 transition-all group">
                        <div className="flex items-start gap-4">
                          <div className="p-3 bg-primary/10 rounded-xl text-primary shadow-sm">
                            <Icon className="h-6 w-6" />
                          </div>
                          <div className="flex-1 space-y-3">
                            <div className="flex items-start justify-between">
                              <div>
                                <h4 className="font-bold text-lg group-hover:text-primary transition-colors">{insight.title}</h4>
                                <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
                                  {insight.description}
                                </p>
                              </div>
                              <Badge className={cn("rounded-md font-bold uppercase tracking-widest text-[10px] px-2 py-0.5", getImpactColor(insight.impact))}>
                                {insight.impact} IMPACT
                              </Badge>
                            </div>
                            <div className="flex items-center gap-4 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
                              <div className="flex items-center gap-1">
                                <Eye className="h-3 w-3" />
                                Confidence: {(insight.confidence * 100).toFixed(0)}%
                              </div>
                              <div className="flex items-center gap-1">
                                <Brain className="h-3 w-3" />
                                {insight.model_name}
                              </div>
                              <Badge variant="outline" className="text-[9px] rounded-md">{insight.category}</Badge>
                            </div>
                            {insight.action_items && (
                              <div className="mt-4 p-4 bg-background/50 rounded-xl border border-border/20">
                                <div className="text-[10px] font-bold uppercase tracking-widest text-primary mb-3">Sensei Recommended Actions:</div>
                                <ul className="space-y-2">
                                  {insight.action_items.map((action, idx) => (
                                    <li key={idx} className="flex items-start gap-3 text-sm font-medium">
                                      <CheckCircle2 className="h-4 w-4 mt-0.5 text-primary shrink-0" />
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
                <div className="py-20 text-center text-muted-foreground font-medium italic">No priority insights at this time. Organizational performance is within optimal parameters.</div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-xl">Predictive Metric Gradients</CardTitle>
                <CardDescription>Current trajectory vs AI forecasted outcome</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {trends.slice(0, 3).map((trend) => (
                  <div key={trend.metric} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80">{trend.metric}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-xl font-bold">{trend.current_value}%</span>
                        <Badge 
                          variant={trend.trend === 'up' ? 'default' : trend.trend === 'down' ? 'destructive' : 'secondary'}
                          className="rounded-md font-bold text-[10px] uppercase tracking-wider"
                        >
                          {trend.trend === 'up' ? <TrendingUp className="h-3 w-3 mr-1" /> : trend.trend === 'down' ? <TrendingDown className="h-3 w-3 mr-1" /> : null}
                          {Math.abs(trend.change_percent).toFixed(1)}%
                        </Badge>
                      </div>
                    </div>
                    <Progress 
                      value={trend.current_value} 
                      className="h-2 rounded-full"
                    />
                    <div className="flex justify-between text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40">
                      <span>Historical Average</span>
                      <span className="text-primary/60 italic">Forecast (7d): {trend.prediction_7d}%</span>
                    </div>
                  </div>
                ))}
                {trends.length === 0 && <div className="text-center text-muted-foreground py-12 font-medium italic">Establishing data baseline...</div>}
              </CardContent>
            </Card>

            <Card className="premium-glass">
              <CardHeader>
                <CardTitle className="text-xl">Autonomous Model Health</CardTitle>
                <CardDescription>Real-time monitoring of inference reliability</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {models.map((model) => (
                  <div key={model.model_name} className="p-3 rounded-xl bg-muted/20 border border-border/10 flex items-center justify-between">
                    <div className="flex-1">
                      <div className="text-sm font-bold capitalize tracking-tight">{model.model_name.replace('_', ' ')} Intelligence</div>
                      <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">
                        <span className="text-primary/70">Accuracy: {((model.accuracy || 0) * 100).toFixed(1)}%</span>
                        <span>•</span>
                        <span>{model.predictions_today || 0} Inferences Today</span>
                      </div>
                    </div>
                    <Badge
                      variant={model.status === 'healthy' ? 'default' : model.status === 'warning' ? 'secondary' : 'destructive'}
                      className="rounded-md text-[9px] font-bold uppercase tracking-widest px-2"
                    >
                      {model.status || 'OPTIMAL'}
                    </Badge>
                  </div>
                ))}
                {models.length === 0 && <div className="text-center text-muted-foreground py-12 font-medium italic">Warming up ML compute clusters...</div>}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="insights" className="space-y-4">
          <div className="grid gap-4">
            {insightsList.map((insight) => {
              const Icon = getInsightIcon(insight.type);
              return (
                <Card key={insight.id}>
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4">
                      <div className="p-3 bg-primary/10 rounded-lg">
                        <Icon className="h-6 w-6 text-primary" />
                      </div>
                      <div className="flex-1 space-y-3">
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="font-semibold text-lg">{insight.title}</h3>
                            <Badge variant="outline" className="mt-1 capitalize">{insight.type}</Badge>
                          </div>
                          <Badge className={getImpactColor(insight.impact)}>
                            {insight.impact} impact
                          </Badge>
                        </div>
                        <p className="text-muted-foreground">{insight.description}</p>
                        <div className="flex items-center gap-6 text-sm">
                          <div className="flex items-center gap-2">
                            <Eye className="h-4 w-4 text-muted-foreground" />
                            <span>Confidence: {(insight.confidence * 100).toFixed(0)}%</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Brain className="h-4 w-4 text-muted-foreground" />
                            <span>{insight.model_name}</span>
                          </div>
                          <Badge variant="secondary">{insight.category}</Badge>
                        </div>
                        {insight.action_items && (
                          <div className="mt-4 p-4 bg-muted rounded-lg">
                            <div className="font-medium mb-3">Recommended Actions:</div>
                            <ul className="space-y-2">
                              {insight.action_items.map((action, idx) => (
                                <li key={idx} className="flex items-start gap-2">
                                  <CheckCircle2 className="h-5 w-5 mt-0.5 text-primary flex-shrink-0" />
                                  <span>{action}</span>
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
            {insightsList.length === 0 && <div className="text-center py-12 text-muted-foreground">No insights found.</div>}
          </div>
        </TabsContent>

        <TabsContent value="trends" className="space-y-4">
          <div className="grid gap-4">
            {trendsList.map((trend) => (
              <Card key={trend.metric}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{trend.metric}</CardTitle>
                    <Badge
                      variant={trend.trend === 'up' ? 'default' : trend.trend === 'down' ? 'destructive' : 'secondary'}
                      className="gap-1"
                    >
                      {trend.trend === 'up' ? <TrendingUp className="h-3 w-3" /> : 
                       trend.trend === 'down' ? <TrendingDown className="h-3 w-3" /> : null}
                      {trend.change_percent > 0 ? '+' : ''}{trend.change_percent.toFixed(1)}%
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-4 bg-muted rounded-lg">
                      <div className="text-xs text-muted-foreground mb-1">Current</div>
                      <div className="text-2xl font-bold">{trend.current_value}%</div>
                    </div>
                    <div className="text-center p-4 bg-muted rounded-lg">
                      <div className="text-xs text-muted-foreground mb-1">7-Day Forecast</div>
                      <div className="text-2xl font-bold">{trend.prediction_7d}%</div>
                    </div>
                    <div className="text-center p-4 bg-muted rounded-lg">
                      <div className="text-xs text-muted-foreground mb-1">30-Day Forecast</div>
                      <div className="text-2xl font-bold">{trend.prediction_7d}%</div>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>Progress to 30-day target</span>
                      <span className={trend.prediction_7d > trend.current_value ? 'text-green-600' : 'text-red-600'}>
                        {((trend.prediction_7d - trend.current_value) / trend.current_value * 100).toFixed(1)}% change expected
                      </span>
                    </div>
                    <Progress value={(trend.current_value / (trend as any).prediction_30d) * 100} className="h-3" />
                  </div>
                </CardContent>
              </Card>
            ))}
            {trendsList.length === 0 && <div className="text-center py-12 text-muted-foreground">No predictive trends found.</div>}
          </div>
        </TabsContent>

        <TabsContent value="models" className="space-y-4">
          <div className="grid gap-4">
            {models.map((model) => (
              <Card key={model.model_name}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="capitalize">{model.model_name.replace('_', ' ')}</CardTitle>
                    <Badge
                      variant={model.status === 'healthy' ? 'default' : model.status === 'warning' ? 'secondary' : 'destructive'}
                      className="capitalize"
                    >
                      {model.status || 'healthy'}
                    </Badge>
                  </div>
                  <CardDescription>
                    {model.predictions_today || 0} predictions today • {model.latency_ms || 0}ms avg latency
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <div className="text-xs text-muted-foreground mb-1">Accuracy</div>
                      <div className="text-xl font-bold">{((model.accuracy || 0) * 100).toFixed(1)}%</div>
                      <Progress value={(model.accuracy || 0) * 100} className="h-1 mt-2" />
                    </div>
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <div className="text-xs text-muted-foreground mb-1">Precision</div>
                      <div className="text-xl font-bold">{((model.precision || 0) * 100).toFixed(1)}%</div>
                      <Progress value={(model.precision || 0) * 100} className="h-1 mt-2" />
                    </div>
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <div className="text-xs text-muted-foreground mb-1">Recall</div>
                      <div className="text-xl font-bold">{((model.recall || 0) * 100).toFixed(1)}%</div>
                      <Progress value={(model.recall || 0) * 100} className="h-1 mt-2" />
                    </div>
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <div className="text-xs text-muted-foreground mb-1">F1 Score</div>
                      <div className="text-xl font-bold">{((model.f1_score || 0) * 100).toFixed(1)}%</div>
                      <Progress value={(model.f1_score || 0) * 100} className="h-1 mt-2" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {models.length === 0 && <div className="text-center py-12 text-muted-foreground">No model performance data found.</div>}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
