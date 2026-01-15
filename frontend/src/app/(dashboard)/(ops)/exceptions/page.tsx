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
import type { ExceptionSeverity, ExceptionCategory, ExceptionStatus } from '@/stores/exceptions';

export default function ExceptionsPage() {
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
      critical: 'bg-red-100 text-red-700 border-red-200',
      high: 'bg-orange-100 text-orange-700 border-orange-200',
      medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      low: 'bg-blue-100 text-blue-700 border-blue-200',
    };
    return colors[severity];
  };

  const getStatusBadgeVariant = (status: ExceptionStatus): 'default' | 'secondary' | 'destructive' | 'outline' => {
    const variants: Record<ExceptionStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      open: 'destructive',
      acknowledged: 'secondary',
      in_progress: 'default',
      resolved: 'outline',
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
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 animate-in fade-in duration-700">
      <div className="relative">
        <div className="absolute inset-0 bg-primary/20 blur-3xl rounded-full animate-pulse" />
        <div className="relative bg-card/40 backdrop-blur-2xl p-12 rounded-[3rem] border border-primary/20 shadow-2xl flex flex-col items-center">
          <div className="flex gap-2 mb-8">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-4 h-4 rounded-full bg-primary animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
          <h2 className="text-2xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mb-2">
            Auditing Anomalies
          </h2>
          <p className="text-muted-foreground font-medium text-sm">Synchronizing operational exceptions...</p>
        </div>
      </div>
    </div>
  );

  const byCategory = stats.by_category ?? {};

  return (
    <div className="space-y-8 page-fade-in" data-testid="exceptions-page">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Anomalous Node Registry
          </h1>
          <p className="text-muted-foreground font-medium">Real-time exception tracking, escalation velocity, and resolution protocol</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Sync Intelligence
          </Button>
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export Protocol
          </Button>
        </div>
      </div>

      {/* Critical Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Critical Open</CardTitle>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-destructive to-destructive/70">{stats.critical_count}</div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-2">
              {stats.total_open} total open nodes
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Overdue Protocol</CardTitle>
            <Clock className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-amber-500 to-amber-500/70">{stats.overdue_count}</div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-amber-500 mt-2">
              SLA Variance Detected
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Escalated Nodes</CardTitle>
            <TrendingUp className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{stats.escalated_count}</div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-2">
              Management Sync Required
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Avg Resolution</CardTitle>
            <Target className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-emerald-500 to-emerald-500/70">{Math.floor(stats.avg_resolution_time_minutes / 60)}h {stats.avg_resolution_time_minutes % 60}m</div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 mt-2">
              {stats.resolved_today} nodes resolved today
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-8 animate-in fade-in duration-700">
        <TabsList className="flex h-14 w-full justify-start gap-3 bg-muted/10 p-1.5 rounded-2xl backdrop-blur-md border border-border/5 overflow-x-auto no-scrollbar shadow-inner-soft">
          <TabsTrigger value="overview" className="rounded-xl px-8 font-heading font-bold text-xs uppercase tracking-widest transition-all data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-glow">Overview</TabsTrigger>
          <TabsTrigger value="critical" className="rounded-xl px-8 font-heading font-bold text-xs uppercase tracking-widest transition-all data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-glow">Critical Only</TabsTrigger>
          <TabsTrigger value="trends" className="rounded-xl px-8 font-heading font-bold text-xs uppercase tracking-widest transition-all data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-glow">Trends</TabsTrigger>
          <TabsTrigger value="by-category" className="rounded-xl px-8 font-heading font-bold text-xs uppercase tracking-widest transition-all data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-glow">By Category</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Filters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="text-sm font-medium mb-2 block">Category</label>
                  <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Categories</SelectItem>
                      <SelectItem value="andon">Andon</SelectItem>
                      <SelectItem value="quote">Quote</SelectItem>
                      <SelectItem value="production">Production</SelectItem>
                      <SelectItem value="quality">Quality</SelectItem>
                      <SelectItem value="a3">A3</SelectItem>
                      <SelectItem value="obeya">Obeya</SelectItem>
                      <SelectItem value="task">Task</SelectItem>
                      <SelectItem value="training">Training</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block">Severity</label>
                  <Select value={selectedSeverity} onValueChange={setSelectedSeverity}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Severities</SelectItem>
                      <SelectItem value="critical">Critical</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block">Status</label>
                  <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Statuses</SelectItem>
                      <SelectItem value="open">Open</SelectItem>
                      <SelectItem value="acknowledged">Acknowledged</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="escalated">Escalated</SelectItem>
                      <SelectItem value="resolved">Resolved</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Exceptions Table */}
          <Card>
            <CardHeader>
              <CardTitle>All Exceptions ({filteredExceptions.length})</CardTitle>
              <CardDescription>Real-time list of active exceptions requiring attention</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Severity</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Owner</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Due Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredExceptions.map((exception) => {
                    const CategoryIcon = getCategoryIcon(exception.category);
                    const overdue = isOverdue(exception.due_date);

                    return (
                      <TableRow key={exception.id} className={overdue ? 'bg-red-50' : ''}>
                        <TableCell>
                          <Badge className={getSeverityColor(exception.severity)}>
                            {exception.severity}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{exception.title}</div>
                            <div className="text-xs text-muted-foreground">{exception.description}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <CategoryIcon className="h-3 w-3 text-muted-foreground" />
                            <span className="capitalize">{exception.category}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="text-sm">{exception.owner}</div>
                            <div className="text-xs text-muted-foreground">{exception.department}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getStatusBadgeVariant(exception.status)}>
                            {exception.status.replace('_', ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">{formatRelativeTime(exception.created_at)}</div>
                        </TableCell>
                        <TableCell>
                          <div className={`text-sm ${overdue ? 'text-red-600 font-medium' : ''}`}>
                            {formatDate(exception.due_date)}
                            {overdue && (
                              <div className="text-xs">OVERDUE</div>
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
        <TabsContent value="critical" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-red-600">Critical Exceptions</CardTitle>
              <CardDescription>Immediate attention required</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {exceptions
                  .filter(exc => exc.severity === 'critical')
                  .map((exception) => (
                    <Card key={exception.id} className="border-red-200 bg-red-50">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <AlertTriangle className="h-5 w-5 text-red-600" />
                              <h3 className="font-semibold text-red-900">{exception.title}</h3>
                            </div>
                            <p className="text-sm text-muted-foreground mb-3">{exception.description}</p>
                            <div className="flex items-center gap-4 text-sm">
                              <div className="flex items-center gap-1">
                                <User className="h-3 w-3" />
                                {exception.owner}
                              </div>
                              <div className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                Due {formatDate(exception.due_date)}
                              </div>
                              <Badge variant={getStatusBadgeVariant(exception.status)}>
                                {exception.status.replace('_', ' ')}
                              </Badge>
                            </div>
                          </div>
                          <Button variant="destructive" size="sm" onClick={() => resolveException(exception.id, 'Resolved via Critical Dashboard')}>
                            Resolve
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trends Tab */}
        <TabsContent value="trends" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Exception Trend (7 Days)</CardTitle>
                <CardDescription>Daily exception count by severity</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {trendsList.map((trend) => (
                    <div key={trend.period}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="font-medium">{trend.period}</span>
                        <span className="text-muted-foreground">
                          {trend.critical + trend.high + trend.medium + trend.low} total
                        </span>
                      </div>
                      <div className="flex gap-1 h-6">
                        <div
                          className="bg-red-500 rounded-l"
                          style={{ width: `${(trend.critical / 50) * 100}%` }}
                          title={`${trend.critical} critical`}
                        />
                        <div
                          className="bg-orange-500"
                          style={{ width: `${(trend.high / 50) * 100}%` }}
                          title={`${trend.high} high`}
                        />
                        <div
                          className="bg-yellow-500"
                          style={{ width: `${(trend.medium / 50) * 100}%` }}
                          title={`${trend.medium} medium`}
                        />
                        <div
                          className="bg-blue-500 rounded-r"
                          style={{ width: `${(trend.low / 50) * 100}%` }}
                          title={`${trend.low} low`}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex gap-4 mt-4 text-xs">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-red-500 rounded" />
                    Critical
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-orange-500 rounded" />
                    High
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-yellow-500 rounded" />
                    Medium
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-blue-500 rounded" />
                    Low
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Resolution Performance</CardTitle>
                <CardDescription>Daily resolved exceptions</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {trendsList.map((trend) => (
                    <div key={trend.period}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="font-medium">{trend.period}</span>
                        <span className="text-green-600 font-medium">{trend.resolved} resolved</span>
                      </div>
                      <Progress value={(trend.resolved / 40) * 100} className="h-2" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* By Category Tab */}
        <TabsContent value="by-category" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {Object.entries(byCategory).map(([category, count]) => {
              const CategoryIcon = getCategoryIcon(category as ExceptionCategory);
              return (
                <Card key={category}>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium capitalize">{category}</CardTitle>
                    <CategoryIcon className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{count}</div>
                    <p className="text-xs text-muted-foreground">
                      {((count / stats.total_open) * 100).toFixed(1)}% of total
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
