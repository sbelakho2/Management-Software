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

const ALLOWED_ROLES = ['admin', 'ceo', 'gm', 'exec', 'ops', 'finance', 'quality'];

export default function AnalyticsPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuthStore();
  const router = useRouter();
  const [selectedPeriod, setSelectedPeriod] = React.useState('7d');
  const [activeTab, setActiveTab] = React.useState('overview');
  
  const { insights, trends, health, loading: analyticsLoading, fetchInsights, fetchTrends, fetchHealth } = useAnalyticsStore();

  React.useEffect(() => {
    if (!authLoading && isAuthenticated && user && !ALLOWED_ROLES.includes(user.role)) {
      router.push('/today');
    }
  }, [user, isAuthenticated, authLoading, router]);

  React.useEffect(() => {
    if (isAuthenticated) {
      fetchInsights();
      fetchTrends();
      fetchHealth();
    }
  }, [fetchInsights, fetchTrends, fetchHealth, isAuthenticated]);

  if (authLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated || (user && !ALLOWED_ROLES.includes(user.role))) {
    return null;
  }

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

  const models = health?.models ? Object.entries(health.models).map(([name, data]: [string, any]) => ({
    model_name: name,
    ...data
  })) : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Shield className="h-8 w-8 text-primary" />
            North Star Control Plane
          </h1>
          <p className="text-muted-foreground">
            Unified organizational intelligence and strategic health indicators
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">24 Hours</SelectItem>
              <SelectItem value="7d">7 Days</SelectItem>
              <SelectItem value="30d">30 Days</SelectItem>
              <SelectItem value="90d">90 Days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" className="gap-2">
            <Download className="h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-primary/5 border-primary/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Organizational OEE</CardTitle>
            <Activity className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">84.2%</div>
            <div className="flex items-center gap-1 text-xs text-green-600 mt-1">
              <TrendingUp className="h-3 w-3" />
              +2.1% from last week
            </div>
            <Progress value={84.2} className="h-1.5 mt-3" />
          </CardContent>
        </Card>

        <Card className="bg-primary/5 border-primary/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Strategic Risk Level</CardTitle>
            <Shield className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Low</div>
            <div className="flex items-center gap-1 text-xs text-green-600 mt-1">
              Stable trend
            </div>
            <div className="flex gap-1 mt-3">
              <div className="h-1.5 flex-1 rounded-full bg-green-500" />
              <div className="h-1.5 flex-1 rounded-full bg-muted" />
              <div className="h-1.5 flex-1 rounded-full bg-muted" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-primary/5 border-primary/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">ML Insights</CardTitle>
            <Brain className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{insights.length}</div>
            <div className="flex items-center gap-1 text-xs text-amber-600 mt-1">
              {insights.filter(i => i.impact === 'high').length} high impact
            </div>
            <div className="mt-3 flex -space-x-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-6 w-6 rounded-full bg-muted border-2 border-background flex items-center justify-center text-[10px] font-bold">
                  AI
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-primary/5 border-primary/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            <Activity className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">99.9%</div>
            <div className="flex items-center gap-1 text-xs text-green-600 mt-1">
              All services operational
            </div>
            <div className="mt-3 flex gap-0.5 h-6 items-end">
              {[4, 6, 5, 8, 7, 9, 8, 10, 9, 10].map((h, i) => (
                <div key={i} className="flex-1 bg-green-500 rounded-t-sm" style={{ height: `${h * 10}%` }} />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="insights">ML Insights</TabsTrigger>
          <TabsTrigger value="trends">Predictive Trends</TabsTrigger>
          <TabsTrigger value="models">Model Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-primary" />
                Priority ML Insights
              </CardTitle>
              <CardDescription>AI-generated insights requiring attention</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {analyticsLoading ? (
                <div className="py-12 text-center text-muted-foreground">Loading AI insights...</div>
              ) : insights.length > 0 ? (
                insights
                  .filter(i => i.impact === 'high')
                  .map((insight) => {
                    const Icon = getInsightIcon(insight.type);
                    return (
                      <Card key={insight.id} className="border-l-4 border-l-primary">
                        <CardContent className="p-4">
                          <div className="flex items-start gap-3">
                            <div className="p-2 bg-primary/10 rounded-lg">
                              <Icon className="h-5 w-5 text-primary" />
                            </div>
                            <div className="flex-1 space-y-2">
                              <div className="flex items-start justify-between">
                                <div>
                                  <h4 className="font-semibold">{insight.title}</h4>
                                  <p className="text-sm text-muted-foreground mt-1">
                                    {insight.description}
                                  </p>
                                </div>
                                <Badge className={getImpactColor(insight.impact)}>
                                  {insight.impact}
                                </Badge>
                              </div>
                              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                <div className="flex items-center gap-1">
                                  <Eye className="h-3 w-3" />
                                  Confidence: {(insight.confidence * 100).toFixed(0)}%
                                </div>
                                <div className="flex items-center gap-1">
                                  <Brain className="h-3 w-3" />
                                  {insight.model_name}
                                </div>
                                <Badge variant="outline">{insight.category}</Badge>
                              </div>
                              {insight.action_items && (
                                <div className="mt-3 p-3 bg-muted rounded-lg">
                                  <div className="text-xs font-medium mb-2">Recommended Actions:</div>
                                  <ul className="text-xs space-y-1">
                                    {insight.action_items.map((action, idx) => (
                                      <li key={idx} className="flex items-start gap-2">
                                        <CheckCircle2 className="h-3 w-3 mt-0.5 text-primary" />
                                        {action}
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
                  })
              ) : (
                <div className="py-12 text-center text-muted-foreground">No priority insights at this time.</div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Key Metric Trends</CardTitle>
                <CardDescription>Current vs predicted values</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {trends.slice(0, 2).map((trend) => (
                  <div key={trend.metric}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">{trend.metric}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-2xl font-bold">{trend.current_value}%</span>
                        <Badge variant={trend.trend === 'up' ? 'default' : trend.trend === 'down' ? 'destructive' : 'secondary'}>
                          {trend.trend === 'up' ? <TrendingUp className="h-3 w-3" /> : trend.trend === 'down' ? <TrendingDown className="h-3 w-3" /> : null}
                          {Math.abs(trend.change_percent).toFixed(1)}%
                        </Badge>
                      </div>
                    </div>
                    <div className="flex gap-2 text-xs text-muted-foreground">
                      <div>7d: {trend.prediction_7d}%</div>
                      <div>30d: {trend.prediction_7d}%</div>
                    </div>
                    <Progress 
                      value={(trend.current_value / 100) * 100} 
                      className="h-2 mt-2"
                    />
                  </div>
                ))}
                {trends.length === 0 && <div className="text-center text-muted-foreground py-8">No trend data available.</div>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Model Health Status</CardTitle>
                <CardDescription>Real-time model monitoring</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {models.map((model) => (
                  <div key={model.model_name} className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="text-sm font-medium capitalize">{model.model_name.replace('_', ' ')}</div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{model.metric || 'Accuracy'}: {((model.accuracy || 0) * 100).toFixed(1)}%</span>
                        <span>•</span>
                        <span>{model.predictions_today || 0} predictions</span>
                      </div>
                    </div>
                    <Badge
                      variant={model.status === 'healthy' ? 'default' : model.status === 'warning' ? 'secondary' : 'destructive'}
                      className="capitalize"
                    >
                      {model.status || 'healthy'}
                    </Badge>
                  </div>
                ))}
                {models.length === 0 && <div className="text-center text-muted-foreground py-8">No model health data available.</div>}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="insights" className="space-y-4">
          <div className="grid gap-4">
            {insights.map((insight) => {
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
            {insights.length === 0 && <div className="text-center py-12 text-muted-foreground">No insights found.</div>}
          </div>
        </TabsContent>

        <TabsContent value="trends" className="space-y-4">
          <div className="grid gap-4">
            {trends.map((trend) => (
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
            {trends.length === 0 && <div className="text-center py-12 text-muted-foreground">No predictive trends found.</div>}
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
