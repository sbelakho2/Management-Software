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
import { Avatar, AvatarFallback, AvatarImage, AvatarGroup } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import { cn, formatDate, formatNumber, formatCurrency, getInitials } from '@/lib/utils';

interface KPI {
  id: string;
  name: string;
  value: number;
  target: number;
  unit: string;
  trend: 'up' | 'down' | 'flat';
  trendValue: number;
  status: 'green' | 'yellow' | 'red';
}

interface A3Report {
  id: string;
  title: string;
  owner: string;
  status: 'draft' | 'review' | 'approved' | 'completed';
  dueDate: string;
  category: 'problem_solving' | 'improvement' | 'strategy';
}

interface ActionItem {
  id: string;
  description: string;
  owner: string;
  dueDate: string;
  status: 'pending' | 'in_progress' | 'completed' | 'overdue';
}

interface Meeting {
  id: string;
  title: string;
  time: string;
  attendees: string[];
  type: 'daily' | 'weekly' | 'monthly';
}

const mockKPIs: KPI[] = [
  { id: '1', name: 'On-Time Delivery', value: 94.2, target: 95, unit: '%', trend: 'up', trendValue: 2.3, status: 'yellow' },
  { id: '2', name: 'First Pass Yield', value: 98.1, target: 97, unit: '%', trend: 'up', trendValue: 0.8, status: 'green' },
  { id: '3', name: 'Quote Win Rate', value: 68, target: 70, unit: '%', trend: 'down', trendValue: -3.2, status: 'yellow' },
  { id: '4', name: 'Customer Satisfaction', value: 4.6, target: 4.5, unit: '/5', trend: 'up', trendValue: 0.2, status: 'green' },
  { id: '5', name: 'Open NCRs', value: 3, target: 2, unit: '', trend: 'flat', trendValue: 0, status: 'red' },
  { id: '6', name: 'CAPA Closure Rate', value: 85, target: 90, unit: '%', trend: 'up', trendValue: 5, status: 'yellow' },
];

const mockA3Reports: A3Report[] = [
  { id: '1', title: 'Reduce Setup Time for CNC Machines', owner: 'John Doe', status: 'review', dueDate: '2024-01-25', category: 'improvement' },
  { id: '2', title: 'Surface Finish Defect Root Cause', owner: 'Sarah Chen', status: 'approved', dueDate: '2024-02-01', category: 'problem_solving' },
  { id: '3', title: 'Q1 Strategic Objectives', owner: 'Maria Garcia', status: 'completed', dueDate: '2024-01-15', category: 'strategy' },
];

const mockActions: ActionItem[] = [
  { id: '1', description: 'Update CMM inspection program for bracket tolerances', owner: 'John Doe', dueDate: '2024-01-18', status: 'in_progress' },
  { id: '2', description: 'Train operators on new setup procedure', owner: 'Sarah Chen', dueDate: '2024-01-20', status: 'pending' },
  { id: '3', description: 'Review supplier quality agreement with vendor X', owner: 'Maria Garcia', dueDate: '2024-01-12', status: 'overdue' },
  { id: '4', description: 'Implement 5S audit schedule', owner: 'David Lee', dueDate: '2024-01-25', status: 'pending' },
];

const mockMeetings: Meeting[] = [
  { id: '1', title: 'Daily Standup', time: '9:00 AM', attendees: ['John', 'Sarah', 'Maria'], type: 'daily' },
  { id: '2', title: 'Quality Review', time: '2:00 PM', attendees: ['Sarah', 'David'], type: 'weekly' },
  { id: '3', title: 'Management Review', time: 'Jan 20, 10:00 AM', attendees: ['John', 'Sarah', 'Maria', 'David'], type: 'monthly' },
];

const statusColors = {
  green: 'bg-success text-success-foreground',
  yellow: 'bg-warning text-warning-foreground',
  red: 'bg-danger text-danger-foreground',
};

const a3StatusConfig = {
  draft: { label: 'Draft', variant: 'secondary' as const },
  review: { label: 'In Review', variant: 'warning' as const },
  approved: { label: 'Approved', variant: 'default' as const },
  completed: { label: 'Completed', variant: 'success' as const },
};

const a3CategoryConfig = {
  problem_solving: { label: 'Problem Solving', color: 'bg-danger/10 text-danger' },
  improvement: { label: 'Improvement', color: 'bg-primary/10 text-primary' },
  strategy: { label: 'Strategy', color: 'bg-success/10 text-success' },
};

const actionStatusConfig = {
  pending: { label: 'Pending', variant: 'secondary' as const },
  in_progress: { label: 'In Progress', variant: 'warning' as const },
  completed: { label: 'Completed', variant: 'success' as const },
  overdue: { label: 'Overdue', variant: 'danger' as const },
};

function KPICard({ kpi }: { kpi: KPI }) {
  const TrendIcon = kpi.trend === 'up' ? TrendingUp : kpi.trend === 'down' ? TrendingDown : Minus;
  const isAtTarget = kpi.status === 'green';
  
  return (
    <Card className={cn('relative overflow-hidden')}>
      <div className={cn('absolute top-0 left-0 w-1 h-full', statusColors[kpi.status])} />
      <CardContent className="pt-4 pl-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{kpi.name}</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-bold">{kpi.value}</span>
              <span className="text-sm text-muted-foreground">{kpi.unit}</span>
            </div>
          </div>
          <div className={cn(
            'flex items-center gap-1 text-sm',
            kpi.trend === 'up' ? 'text-success' : kpi.trend === 'down' ? 'text-danger' : 'text-muted-foreground'
          )}>
            <TrendIcon className="h-4 w-4" />
            {kpi.trendValue > 0 ? '+' : ''}{kpi.trendValue}
          </div>
        </div>
        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
          <Target className="h-3 w-3" />
          Target: {kpi.target}{kpi.unit}
          {isAtTarget && <CheckCircle className="h-3 w-3 text-success" />}
        </div>
      </CardContent>
    </Card>
  );
}

function A3Card({ report }: { report: A3Report }) {
  const router = useRouter();
  const statusCfg = a3StatusConfig[report.status];
  const categoryCfg = a3CategoryConfig[report.category];

  return (
    <div 
      className="border rounded-lg p-3 hover:bg-muted/50 cursor-pointer transition-colors"
      onClick={() => router.push(`/obeya/a3/${report.id}`)}
    >
      <div className="flex items-start justify-between mb-2">
        <span className={cn('text-xs px-2 py-0.5 rounded', categoryCfg.color)}>
          {categoryCfg.label}
        </span>
        <Badge variant={statusCfg.variant} size="sm">{statusCfg.label}</Badge>
      </div>
      <h4 className="font-medium text-sm mb-2">{report.title}</h4>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{report.owner}</span>
        <span>Due {formatDate(new Date(report.dueDate), { month: 'short', day: 'numeric' })}</span>
      </div>
    </div>
  );
}

function ActionRow({ action }: { action: ActionItem }) {
  const statusCfg = actionStatusConfig[action.status];
  const isOverdue = action.status === 'overdue';

  return (
    <div className={cn('flex items-center gap-3 py-2 border-b last:border-0', isOverdue && 'bg-danger/5')}>
      <div className="flex-1 min-w-0">
        <p className="text-sm truncate">{action.description}</p>
        <p className="text-xs text-muted-foreground">
          {action.owner} • Due {formatDate(new Date(action.dueDate), { month: 'short', day: 'numeric' })}
        </p>
      </div>
      <Badge variant={statusCfg.variant} size="sm">{statusCfg.label}</Badge>
    </div>
  );
}

// SQDCP Metrics mock data
const mockSQDCPMetrics = {
  safety: {
    incidents: 0,
    days_since_last_incident: 127,
    near_misses: 2,
    training_completion: 98,
    status: 'green' as const,
  },
  quality: {
    first_pass_yield: 98.1,
    defect_rate: 1.9,
    customer_complaints: 1,
    ncr_open: 3,
    status: 'green' as const,
  },
  delivery: {
    on_time_delivery: 94.2,
    lead_time_days: 14.5,
    schedule_adherence: 96.3,
    backlog_items: 23,
    status: 'yellow' as const,
  },
  cost: {
    variance_percent: -2.3,
    cost_savings: 15420,
    waste_reduction: 8.7,
    budget_utilization: 87.5,
    status: 'green' as const,
  },
  people: {
    morale_score: 4.3,
    training_hours: 156,
    attendance_rate: 97.8,
    active_improvements: 12,
    status: 'green' as const,
  },
};

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Obeya Board</h1>
          <p className="text-muted-foreground">Visual management and team alignment</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline">
            <Settings className="mr-2 h-4 w-4" />
            Customize
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <FileText className="mr-2 h-4 w-4" />
                New A3 Report
              </DropdownMenuItem>
              <DropdownMenuItem>
                <CheckCircle className="mr-2 h-4 w-4" />
                New Action Item
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Calendar className="mr-2 h-4 w-4" />
                Schedule Meeting
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Tabs for different views */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="sqdcp">SQDCP Metrics</TabsTrigger>
          <TabsTrigger value="exceptions">Exceptions</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {/* Visual Metrics & Charts */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Status Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <LayoutGrid className="h-4 w-4" />
                  Status Overview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="p-4 rounded-lg bg-success/10">
                    <p className="text-3xl font-bold text-success">12</p>
                    <p className="text-sm text-muted-foreground">On Track</p>
                  </div>
                  <div className="p-4 rounded-lg bg-warning/10">
                    <p className="text-3xl font-bold text-warning">4</p>
                    <p className="text-sm text-muted-foreground">At Risk</p>
                  </div>
                  <div className="p-4 rounded-lg bg-danger/10">
                    <p className="text-3xl font-bold text-danger">2</p>
                    <p className="text-sm text-muted-foreground">Critical</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Team Focus */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Team Focus This Week
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <Avatar>
                      <AvatarFallback>JD</AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <p className="font-medium text-sm">John Doe</p>
                      <p className="text-xs text-muted-foreground">CMM program updates, Setup time reduction</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Avatar>
                      <AvatarFallback>SC</AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <p className="font-medium text-sm">Sarah Chen</p>
                      <p className="text-xs text-muted-foreground">Surface finish investigation, Training</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Avatar>
                      <AvatarFallback>MG</AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <p className="font-medium text-sm">Maria Garcia</p>
                      <p className="text-xs text-muted-foreground">Supplier quality review, Q1 objectives</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Announcements */}
          <Card className="border-primary/50 bg-primary/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                Announcements
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-4 w-4 text-warning mt-0.5" />
                <div>
                  <p className="text-sm font-medium">Scheduled Maintenance</p>
                  <p className="text-xs text-muted-foreground">CNC Machine #3 will be down for maintenance on Friday, Jan 19th from 2-5 PM</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle className="h-4 w-4 text-success mt-0.5" />
                <div>
                  <p className="text-sm font-medium">AS9100 Audit Complete</p>
                  <p className="text-xs text-muted-foreground">Congratulations! Zero major findings. Final report available next week.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* SQDCP Metrics Tab */}
        <TabsContent value="sqdcp" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <SQDCPCard
              title="Safety"
              icon={Shield}
              status={mockSQDCPMetrics.safety.status}
              metrics={[
                { label: 'Incidents', value: mockSQDCPMetrics.safety.incidents },
                { label: 'Days Since Last', value: `${mockSQDCPMetrics.safety.days_since_last_incident} days`, trend: 'up' },
                { label: 'Near Misses', value: mockSQDCPMetrics.safety.near_misses },
                { label: 'Training Complete', value: `${mockSQDCPMetrics.safety.training_completion}%`, trend: 'up' },
              ]}
            />
            <SQDCPCard
              title="Quality"
              icon={Award}
              status={mockSQDCPMetrics.quality.status}
              metrics={[
                { label: 'First Pass Yield', value: `${mockSQDCPMetrics.quality.first_pass_yield}%`, trend: 'up' },
                { label: 'Defect Rate', value: `${mockSQDCPMetrics.quality.defect_rate}%`, trend: 'down' },
                { label: 'Complaints', value: mockSQDCPMetrics.quality.customer_complaints },
                { label: 'Open NCRs', value: mockSQDCPMetrics.quality.ncr_open },
              ]}
            />
            <SQDCPCard
              title="Delivery"
              icon={Truck}
              status={mockSQDCPMetrics.delivery.status}
              metrics={[
                { label: 'On-Time Delivery', value: `${mockSQDCPMetrics.delivery.on_time_delivery}%`, trend: 'down' },
                { label: 'Lead Time', value: `${mockSQDCPMetrics.delivery.lead_time_days} days` },
                { label: 'Schedule Adherence', value: `${mockSQDCPMetrics.delivery.schedule_adherence}%`, trend: 'stable' },
                { label: 'Backlog Items', value: mockSQDCPMetrics.delivery.backlog_items },
              ]}
            />
            <SQDCPCard
              title="Cost"
              icon={DollarSign}
              status={mockSQDCPMetrics.cost.status}
              metrics={[
                { label: 'Budget Variance', value: `${mockSQDCPMetrics.cost.variance_percent}%`, trend: 'up' },
                { label: 'Cost Savings', value: `$${formatNumber(mockSQDCPMetrics.cost.cost_savings)}`, trend: 'up' },
                { label: 'Waste Reduction', value: `${mockSQDCPMetrics.cost.waste_reduction}%`, trend: 'up' },
                { label: 'Budget Used', value: `${mockSQDCPMetrics.cost.budget_utilization}%` },
              ]}
            />
            <SQDCPCard
              title="People"
              icon={Heart}
              status={mockSQDCPMetrics.people.status}
              metrics={[
                { label: 'Morale Score', value: `${mockSQDCPMetrics.people.morale_score}/5`, trend: 'up' },
                { label: 'Training Hours', value: `${mockSQDCPMetrics.people.training_hours}h`, trend: 'up' },
                { label: 'Attendance', value: `${mockSQDCPMetrics.people.attendance_rate}%`, trend: 'stable' },
                { label: 'Active Improvements', value: mockSQDCPMetrics.people.active_improvements },
              ]}
            />
          </div>

          {/* SQDCP Summary */}
          <Card>
            <CardHeader>
              <CardTitle>SQDCP Summary</CardTitle>
              <CardDescription>Overall performance across all dimensions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Overall Health</span>
                    <Badge variant="success">Healthy</Badge>
                  </div>
                  <Progress value={88} className="h-2" />
                  <p className="text-xs text-muted-foreground mt-1">4 of 5 metrics green, 1 yellow</p>
                </div>
                <div className="grid grid-cols-5 gap-4 text-center pt-4">
                  <div>
                    <div className="w-12 h-12 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-2">
                      <Shield className="h-6 w-6 text-success" />
                    </div>
                    <p className="text-xs font-medium">Safety</p>
                    <Badge variant="success" size="sm" className="mt-1">Green</Badge>
                  </div>
                  <div>
                    <div className="w-12 h-12 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-2">
                      <Award className="h-6 w-6 text-success" />
                    </div>
                    <p className="text-xs font-medium">Quality</p>
                    <Badge variant="success" size="sm" className="mt-1">Green</Badge>
                  </div>
                  <div>
                    <div className="w-12 h-12 rounded-full bg-warning/10 flex items-center justify-center mx-auto mb-2">
                      <Truck className="h-6 w-6 text-warning" />
                    </div>
                    <p className="text-xs font-medium">Delivery</p>
                    <Badge variant="warning" size="sm" className="mt-1">Yellow</Badge>
                  </div>
                  <div>
                    <div className="w-12 h-12 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-2">
                      <DollarSign className="h-6 w-6 text-success" />
                    </div>
                    <p className="text-xs font-medium">Cost</p>
                    <Badge variant="success" size="sm" className="mt-1">Green</Badge>
                  </div>
                  <div>
                    <div className="w-12 h-12 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-2">
                      <Heart className="h-6 w-6 text-success" />
                    </div>
                    <p className="text-xs font-medium">People</p>
                    <Badge variant="success" size="sm" className="mt-1">Green</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Exceptions Tab */}
        <TabsContent value="exceptions" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Exception Items</CardTitle>
              <CardDescription>Items requiring attention - overdue, blocked, or escalated</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-3 p-3 border rounded-lg bg-destructive/5">
                  <AlertTriangle className="h-5 w-5 text-destructive flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">Supplier quality review with vendor X</p>
                    <p className="text-xs text-muted-foreground">Overdue by 3 days • Assigned to Maria Garcia</p>
                  </div>
                  <Badge variant="destructive">Overdue</Badge>
                </div>
                <div className="flex items-center gap-3 p-3 border rounded-lg bg-warning/5">
                  <AlertTriangle className="h-5 w-5 text-warning flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">CMM inspection program update</p>
                    <p className="text-xs text-muted-foreground">Blocked - waiting on engineering • Assigned to John Doe</p>
                  </div>
                  <Badge variant="warning">Blocked</Badge>
                </div>
                <div className="flex items-center gap-3 p-3 border rounded-lg">
                  <Activity className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">No exceptions to report</p>
                    <p className="text-xs text-muted-foreground">All other items on track</p>
                  </div>
                  <Badge variant="success">On Track</Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Exception Trends */}
          <div className="grid gap-6 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Overdue Items</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-destructive">1</div>
                <p className="text-xs text-muted-foreground mt-1">Down from 3 last week</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Blocked Items</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-warning">1</div>
                <p className="text-xs text-muted-foreground mt-1">Same as last week</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Escalated Items</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">0</div>
                <p className="text-xs text-muted-foreground mt-1">No active escalations</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Visual Metrics & Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Status Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <LayoutGrid className="h-4 w-4" />
              Status Overview
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="p-4 rounded-lg bg-success/10">
                <p className="text-3xl font-bold text-success">12</p>
                <p className="text-sm text-muted-foreground">On Track</p>
              </div>
              <div className="p-4 rounded-lg bg-warning/10">
                <p className="text-3xl font-bold text-warning">4</p>
                <p className="text-sm text-muted-foreground">At Risk</p>
              </div>
              <div className="p-4 rounded-lg bg-danger/10">
                <p className="text-3xl font-bold text-danger">2</p>
                <p className="text-sm text-muted-foreground">Critical</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Team Focus */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Users className="h-4 w-4" />
              Team Focus This Week
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Avatar>
                  <AvatarFallback>JD</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <p className="font-medium text-sm">John Doe</p>
                  <p className="text-xs text-muted-foreground">CMM program updates, Setup time reduction</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Avatar>
                  <AvatarFallback>SC</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <p className="font-medium text-sm">Sarah Chen</p>
                  <p className="text-xs text-muted-foreground">Surface finish investigation, Training</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Avatar>
                  <AvatarFallback>MG</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <p className="font-medium text-sm">Maria Garcia</p>
                  <p className="text-xs text-muted-foreground">Supplier quality review, Q1 objectives</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Announcements */}
      <Card className="border-primary/50 bg-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Announcements
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-4 w-4 text-warning mt-0.5" />
            <div>
              <p className="text-sm font-medium">Scheduled Maintenance</p>
              <p className="text-xs text-muted-foreground">CNC Machine #3 will be down for maintenance on Friday, Jan 19th from 2-5 PM</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <CheckCircle className="h-4 w-4 text-success mt-0.5" />
            <div>
              <p className="text-sm font-medium">AS9100 Audit Complete</p>
              <p className="text-xs text-muted-foreground">Congratulations! Zero major findings. Final report available next week.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
