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
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage, AvatarGroup } from '@/components/ui/avatar';
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

      {/* KPIs */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Key Performance Indicators</h2>
          <Button variant="ghost" size="sm" className="gap-1">
            View All <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {mockKPIs.map((kpi) => (
            <KPICard key={kpi.id} kpi={kpi} />
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* A3 Reports */}
        <Card className="lg:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="h-4 w-4" />
                A3 Reports
              </CardTitle>
              <CardDescription>Active problem solving & improvements</CardDescription>
            </div>
            <Button variant="ghost" size="icon-sm">
              <Plus className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {mockA3Reports.map((report) => (
              <A3Card key={report.id} report={report} />
            ))}
            <Button variant="ghost" size="sm" className="w-full">
              View All A3s
            </Button>
          </CardContent>
        </Card>

        {/* Action Items */}
        <Card className="lg:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Action Items
              </CardTitle>
              <CardDescription>Tasks from meetings & reviews</CardDescription>
            </div>
            <Button variant="ghost" size="icon-sm">
              <Plus className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            {mockActions.map((action) => (
              <ActionRow key={action.id} action={action} />
            ))}
            <Button variant="ghost" size="sm" className="w-full mt-2">
              View All Actions
            </Button>
          </CardContent>
        </Card>

        {/* Meetings & Schedule */}
        <Card className="lg:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Upcoming Meetings
              </CardTitle>
              <CardDescription>Team sync & reviews</CardDescription>
            </div>
            <Button variant="ghost" size="icon-sm">
              <Plus className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {mockMeetings.map((meeting) => (
              <div key={meeting.id} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="font-medium text-sm">{meeting.title}</p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {meeting.time}
                    <Badge variant="outline" size="sm" className="capitalize">{meeting.type}</Badge>
                  </div>
                </div>
                <AvatarGroup max={3}>
                  {meeting.attendees.map((name) => (
                    <Avatar key={name} size="sm">
                      <AvatarFallback>{getInitials(name)}</AvatarFallback>
                    </Avatar>
                  ))}
                </AvatarGroup>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

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
