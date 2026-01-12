'use client';

import * as React from 'react';
import {
  AlertTriangle,
  Clock,
  TrendingUp,
  TrendingDown,
  Ban,
  AlertCircle,
  Calendar,
  User,
  Target,
  CheckCircle2,
  XCircle,
  Filter,
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

// Types
type ExceptionSeverity = 'critical' | 'high' | 'medium' | 'low';
type ExceptionCategory = 'andon' | 'quote' | 'production' | 'quality' | 'a3' | 'obeya' | 'task' | 'training';
type ExceptionStatus = 'open' | 'acknowledged' | 'in_progress' | 'resolved' | 'escalated';

interface Exception {
  id: string;
  title: string;
  category: ExceptionCategory;
  severity: ExceptionSeverity;
  status: ExceptionStatus;
  created_at: string;
  due_date: string;
  owner: string;
  department: string;
  description: string;
  resolution_time?: number; // minutes
  escalated_at?: string;
  blocked_reason?: string;
  related_entity_id?: string;
  related_entity_type?: string;
  tags: string[];
}

interface ExceptionTrend {
  period: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  resolved: number;
}

interface ExceptionStats {
  total_open: number;
  critical_count: number;
  overdue_count: number;
  escalated_count: number;
  blocked_count: number;
  avg_resolution_time_minutes: number;
  resolved_today: number;
  created_today: number;
  by_category: Record<ExceptionCategory, number>;
  by_severity: Record<ExceptionSeverity, number>;
}

export default function ExceptionsPage() {
  const [activeTab, setActiveTab] = React.useState('overview');
  const [selectedCategory, setSelectedCategory] = React.useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = React.useState<string>('all');
  const [selectedStatus, setSelectedStatus] = React.useState<string>('open');
  const [isRefreshing, setIsRefreshing] = React.useState(false);

  // Mock data - would come from API
  const [stats, setStats] = React.useState<ExceptionStats>({
    total_open: 47,
    critical_count: 8,
    overdue_count: 15,
    escalated_count: 5,
    blocked_count: 3,
    avg_resolution_time_minutes: 245,
    resolved_today: 12,
    created_today: 9,
    by_category: {
      andon: 12,
      quote: 8,
      production: 15,
      quality: 6,
      a3: 2,
      obeya: 1,
      task: 2,
      training: 1,
    },
    by_severity: {
      critical: 8,
      high: 18,
      medium: 15,
      low: 6,
    },
  });

  const [exceptions, setExceptions] = React.useState<Exception[]>([
    {
      id: '1',
      title: 'CNC Machine 3 - Emergency Stop Activated',
      category: 'andon',
      severity: 'critical',
      status: 'open',
      created_at: '2026-01-08T09:15:00Z',
      due_date: '2026-01-08T10:15:00Z',
      owner: 'John Smith',
      department: 'Manufacturing',
      description: 'Machine emergency stop activated. Production halted.',
      tags: ['machine-down', 'safety'],
    },
    {
      id: '2',
      title: 'Quote #Q-2024-156 - Approval Overdue 48h',
      category: 'quote',
      severity: 'high',
      status: 'escalated',
      created_at: '2026-01-06T14:30:00Z',
      due_date: '2026-01-07T14:30:00Z',
      owner: 'Sarah Johnson',
      department: 'Sales',
      description: '$125,000 quote awaiting GM approval for 2 days.',
      escalated_at: '2026-01-07T14:35:00Z',
      tags: ['approval', 'high-value'],
    },
    {
      id: '3',
      title: 'Work Order #WO-8945 - Material Shortage',
      category: 'production',
      severity: 'high',
      status: 'in_progress',
      created_at: '2026-01-08T07:00:00Z',
      due_date: '2026-01-09T07:00:00Z',
      owner: 'Mike Davis',
      department: 'Production',
      description: 'Aluminum sheet 6061-T6 out of stock, blocking 3 work orders.',
      blocked_reason: 'Waiting for material delivery',
      tags: ['material', 'blocked'],
    },
    {
      id: '4',
      title: 'CTQ-2024-023 - Surface Finish Exceeds Tolerance',
      category: 'quality',
      severity: 'critical',
      status: 'open',
      created_at: '2026-01-08T08:45:00Z',
      due_date: '2026-01-08T12:45:00Z',
      owner: 'Emily Chen',
      department: 'Quality',
      description: 'Last 5 measurements failed Ra < 32. Investigating tooling.',
      tags: ['measurement', 'ctq'],
    },
    {
      id: '5',
      title: 'A3-2024-012 - Root Cause Analysis Stalled',
      category: 'a3',
      severity: 'medium',
      status: 'open',
      created_at: '2026-01-05T11:00:00Z',
      due_date: '2026-01-10T11:00:00Z',
      owner: 'David Lee',
      department: 'Manufacturing',
      description: 'A3 for setup time reduction stuck at root cause stage for 3 days.',
      tags: ['a3', 'overdue'],
    },
    {
      id: '6',
      title: 'Task #T-5623 - Safety Training Expired',
      category: 'training',
      severity: 'high',
      status: 'open',
      created_at: '2026-01-07T13:00:00Z',
      due_date: '2026-01-08T13:00:00Z',
      owner: 'Lisa Williams',
      department: 'HR',
      description: '8 operators have expired forklift certifications.',
      tags: ['training', 'compliance'],
    },
  ]);

  const [trends, setTrends] = React.useState<ExceptionTrend[]>([
    { period: 'Mon', critical: 12, high: 25, medium: 18, low: 8, resolved: 35 },
    { period: 'Tue', critical: 10, high: 22, medium: 20, low: 7, resolved: 38 },
    { period: 'Wed', critical: 8, high: 20, medium: 15, low: 6, resolved: 32 },
    { period: 'Thu', critical: 9, high: 18, medium: 16, low: 5, resolved: 30 },
    { period: 'Fri', critical: 11, high: 21, medium: 17, low: 7, resolved: 34 },
    { period: 'Sat', critical: 5, high: 10, medium: 8, low: 3, resolved: 20 },
    { period: 'Sun', critical: 8, high: 18, medium: 15, low: 6, resolved: 28 },
  ]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsRefreshing(false);
  };

  const handleExport = () => {
    // Export to CSV
    console.log('Exporting exceptions...');
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

  // Filter exceptions
  const filteredExceptions = exceptions.filter(exc => {
    if (selectedCategory !== 'all' && exc.category !== selectedCategory) return false;
    if (selectedSeverity !== 'all' && exc.severity !== selectedSeverity) return false;
    if (selectedStatus !== 'all' && exc.status !== selectedStatus) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-red-600">Exceptions Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time monitoring of critical issues and overdue items
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" className="gap-2" onClick={handleExport}>
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Critical Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-red-200 bg-red-50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Critical Open</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.critical_count}</div>
            <p className="text-xs text-muted-foreground">
              {stats.total_open} total open
            </p>
          </CardContent>
        </Card>

        <Card className="border-orange-200 bg-orange-50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{stats.overdue_count}</div>
            <p className="text-xs text-muted-foreground">
              Past due date
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Escalated</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.escalated_count}</div>
            <p className="text-xs text-muted-foreground">
              Escalated to management
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Resolution</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.floor(stats.avg_resolution_time_minutes / 60)}h {stats.avg_resolution_time_minutes % 60}m</div>
            <p className="text-xs text-muted-foreground">
              {stats.resolved_today} resolved today
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="critical">Critical Only</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="by-category">By Category</TabsTrigger>
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
                          <Button variant="destructive" size="sm">
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
                  {trends.map((trend) => (
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
                  {trends.map((trend) => (
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
            {Object.entries(stats.by_category).map(([category, count]) => {
              const CategoryIcon = getCategoryIcon(category as ExceptionCategory);
              return (
                <Card key={category}>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium capitalize">{category}</CardTitle>
                    <CategoryIcon className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{count}</div>
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
