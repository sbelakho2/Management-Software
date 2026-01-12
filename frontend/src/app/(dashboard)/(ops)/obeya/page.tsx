'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
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
    green: 'bg-success/10 border-success',
    yellow: 'bg-warning/10 border-warning',
    red: 'bg-destructive/10 border-destructive',
  };

  return (
    <Card className={cn('border-2', statusColors[status])}>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {metrics.map((metric, idx) => (
          <div key={idx} className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{metric.label}</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold">{metric.value}</span>
              {metric.trend && (
                metric.trend === 'up' ? <TrendingUp className="h-3 w-3 text-success" /> :
                metric.trend === 'down' ? <TrendingDown className="h-3 w-3 text-destructive" /> :
                <Minus className="h-3 w-3 text-muted-foreground" />
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function ObeyaPage() {
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
    <div className="space-y-6" data-testid="obeya-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Cognitive Obeya</h1>
          <p className="text-sm text-muted-foreground">Prescriptive organizational intelligence & visual management</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => fetchCognitiveInsights()} disabled={isLoading}>
            <RefreshCw className={cn("mr-2 h-4 w-4", isLoading && "animate-spin")} />
            Sync AI
          </Button>
          <Button variant="outline" size="sm">
            <Settings className="mr-2 h-4 w-4" />
            Config
          </Button>
        </div>
      </div>

      {/* Tabs for different views */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="intelligence">Sensei AI</TabsTrigger>
          <TabsTrigger value="sqdcp">SQDCP Detail</TabsTrigger>
          <TabsTrigger value="exceptions">Exceptions</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Predictive Breaches</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-warning">{summary.metrics.warnings}</div>
                <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
                  <TrendingDown className="h-3 w-3" /> Trending toward RED
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Silo Bottlenecks</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-danger">{summary.cross_functional.active_alerts}</div>
                <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" /> Inter-departmental friction
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Rebalance Ops</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">{summary.cross_functional.pending_rebalances}</div>
                <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
                  <Users className="h-3 w-3" /> Skill gap opportunities
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Heijunka Tips</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-success">{summary.heijunka.pending_suggestions}</div>
                <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
                  <Activity className="h-3 w-3" /> Smoothing possibilities
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  Primary North Stars
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">First Pass Yield</span>
                    <span className="text-sm font-bold text-success">98.1%</span>
                  </div>
                  <Progress value={98.1} className="h-2" />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">On-Time Delivery</span>
                    <span className="text-sm font-bold text-warning">94.2%</span>
                  </div>
                  <Progress value={94.2} className="h-2" />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Customer Satisfaction</span>
                    <span className="text-sm font-bold text-success">4.6/5.0</span>
                  </div>
                  <Progress value={92} className="h-2" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  Recent Silo Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {siloAlerts.map((alert: any) => (
                    <div key={alert.alert_id} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 border border-transparent hover:border-border transition-all group">
                      <div className={cn(
                        "mt-0.5 p-1 rounded-full",
                        alert.severity === 'critical' ? 'bg-danger/10 text-danger' : 'bg-warning/10 text-warning'
                      )}>
                        <AlertTriangle className="h-4 w-4" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-semibold">{alert.impact}</p>
                          <Badge variant="outline" className="text-[10px] uppercase">{alert.severity}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">Source: {alert.source} → Impacting: {alert.affected}</p>
                        <p className="text-xs italic mt-2 opacity-0 group-hover:opacity-100 transition-opacity">"{alert.event}"</p>
                      </div>
                    </div>
                  ))}
                  {siloAlerts.length === 0 && (
                    <div className="text-center py-12 text-muted-foreground">
                      <CheckCircle className="h-8 w-8 mx-auto mb-2 opacity-20" />
                      <p className="text-sm">No active silo alerts detected</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Intelligence Tab */}
        <TabsContent value="intelligence" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="border-primary/20 shadow-lg shadow-primary/5">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-primary" />
                    Resource Rebalancing
                  </CardTitle>
                  <Badge variant="primary" className="animate-pulse">AI Suggested</Badge>
                </div>
                <CardDescription>Real-time skill gap analysis and labor leveling</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {rebalanceSuggestions.map((s: any) => (
                  <div key={s.suggestion_id} className="p-4 border rounded-xl space-y-4 bg-gradient-to-br from-background to-muted/20">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="font-mono">{s.from_work_center}</Badge>
                        <ArrowRight className="h-3 w-3 text-muted-foreground" />
                        <Badge variant="default" className="font-mono">{s.to_work_center}</Badge>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground uppercase font-bold">Improvement</p>
                        <p className="text-lg font-bold text-success">+{Math.round(s.expected_improvement * 100)}%</p>
                      </div>
                    </div>
                    <p className="text-sm leading-relaxed">{s.reason}</p>
                    <div className="space-y-2">
                      <p className="text-[10px] uppercase font-bold text-muted-foreground">Recommended Operators</p>
                      <div className="flex flex-wrap gap-2">
                        {s.operators.map((op: string) => (
                          <div key={op} className="flex items-center gap-1 bg-background border px-2 py-1 rounded-md text-xs font-medium">
                            <Avatar className="h-4 w-4">
                              <AvatarFallback className="text-[8px]">{getInitials(op)}</AvatarFallback>
                            </Avatar>
                            {op}
                          </div>
                        ))}
                      </div>
                    </div>
                    <Button size="sm" className="w-full shadow-md">Execute Move</Button>
                  </div>
                ))}
                {rebalanceSuggestions.length === 0 && (
                  <div className="text-center py-16 text-muted-foreground">
                    <Users className="h-12 w-12 mx-auto mb-4 opacity-10" />
                    <p>Skill profiles are currently optimized across all work centers</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-success/20 shadow-lg shadow-success/5">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-success" />
                    Heijunka Leveling
                  </CardTitle>
                  <Badge variant="success">Prescriptive</Badge>
                </div>
                <CardDescription>Minimizing Mura (Unevenness) in production schedule</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {heijunkaSuggestions.map((s: any) => (
                  <div key={s.suggestion_id} className="p-4 border rounded-xl space-y-4 border-success/20 bg-success/5">
                    <div className="flex items-center justify-between">
                      <Badge variant="success" className="uppercase tracking-tighter">{s.period} Horizon</Badge>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground uppercase font-bold text-success/70">Mura Reduction</p>
                        <p className="text-lg font-bold text-success">-{Math.round(s.mura_reduction)}%</p>
                      </div>
                    </div>
                    <p className="text-sm font-medium leading-snug">{s.reasoning}</p>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <p className="text-[10px] uppercase font-bold text-muted-foreground">Current Pattern</p>
                        <div className="h-12 w-full bg-muted rounded-md flex items-end gap-0.5 p-1">
                          {[40, 80, 20, 90, 30].map((h, i) => <div key={i} className="flex-1 bg-muted-foreground/30 rounded-t-sm" style={{height: `${h}%`}} />)}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <p className="text-[10px] uppercase font-bold text-success/70">Suggested Pattern</p>
                        <div className="h-12 w-full bg-success/10 rounded-md flex items-end gap-0.5 p-1">
                          {[50, 55, 48, 52, 53].map((h, i) => <div key={i} className="flex-1 bg-success/40 rounded-t-sm" style={{height: `${h}%`}} />)}
                        </div>
                      </div>
                    </div>
                    <Button size="sm" variant="success" className="w-full shadow-md">Smooth Schedule</Button>
                  </div>
                ))}
                {heijunkaSuggestions.length === 0 && (
                  <div className="text-center py-16 text-muted-foreground">
                    <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-10" />
                    <p>Production mix is sufficiently leveled for the current horizon</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="sqdcp">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
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
            <p className="text-muted-foreground p-8 text-center col-span-full italic">Switching to real-time shop floor sensor fusion...</p>
          </div>
        </TabsContent>

        <TabsContent value="exceptions">
          <Card>
            <CardHeader>
              <CardTitle>Anomalies & Exceptions</CardTitle>
              <CardDescription>AI-flagged deviations from standard work or performance targets</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {items.filter(i => i.status === 'blocked' || i.is_escalated).map(item => (
                  <div key={item.id} className="flex items-center gap-3 p-3 border rounded-lg bg-danger/5">
                    <AlertTriangle className="h-5 w-5 text-danger flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{item.title}</p>
                      <p className="text-xs text-muted-foreground">{item.blocked_reason || item.escalation_reason || 'Pending action'}</p>
                    </div>
                    <Badge variant="destructive">{item.status}</Badge>
                  </div>
                ))}
                {items.filter(i => i.status === 'blocked' || i.is_escalated).length === 0 && (
                  <div className="flex items-center gap-3 p-3 border rounded-lg bg-success/5">
                    <CheckCircle className="h-5 w-5 text-success flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">No critical exceptions</p>
                      <p className="text-xs text-muted-foreground">System operating within normal parameters</p>
                    </div>
                    <Badge variant="success">Healthy</Badge>
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
