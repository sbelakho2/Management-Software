'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  FileText,
  Users,
  Package,
  AlertTriangle,
  type LucideIcon,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarGroup } from '@/components/ui/avatar';
import { Skeleton, SkeletonCard } from '@/components/ui/skeleton';
import { cn, formatDate, formatCurrency, formatRelativeTime } from '@/lib/utils';
import { useAuthStore } from '@/stores';

// Types
interface KPICardData {
  id: string;
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendIsGood?: boolean;
  icon: LucideIcon;
  href?: string;
}

interface TaskItem {
  id: string;
  title: string;
  dueDate: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'todo' | 'in_progress' | 'done';
  assignee?: {
    name: string;
    avatar?: string;
  };
  linkedEntity?: {
    type: string;
    title: string;
    href: string;
  };
}

interface ActivityItem {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  user: {
    name: string;
    avatar?: string;
  };
  link?: string;
}

interface RFQSummary {
  id: string;
  rfqNumber: string;
  customerName: string;
  title: string;
  dueDate: string;
  estimatedValue?: number;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: string;
}

// Mock data - would come from API
const mockKPIs: KPICardData[] = [
  {
    id: '1',
    label: 'Open RFQs',
    value: 12,
    change: 3,
    changeLabel: 'from last week',
    trend: 'up',
    trendIsGood: true,
    icon: FileText,
    href: '/pipeline',
  },
  {
    id: '2',
    label: 'Pending Quotes',
    value: 8,
    change: -2,
    changeLabel: 'from last week',
    trend: 'down',
    trendIsGood: true,
    icon: FileText,
    href: '/quotes?status=pending',
  },
  {
    id: '3',
    label: 'Active Customers',
    value: 47,
    change: 5,
    changeLabel: 'new this month',
    trend: 'up',
    trendIsGood: true,
    icon: Users,
    href: '/customers',
  },
  {
    id: '4',
    label: 'Open NCRs',
    value: 3,
    change: 1,
    changeLabel: 'from yesterday',
    trend: 'up',
    trendIsGood: false,
    icon: AlertTriangle,
    href: '/quality/ncrs',
  },
];

const mockTasks: TaskItem[] = [
  {
    id: '1',
    title: 'Review quote for Acme Corp',
    dueDate: new Date().toISOString(),
    priority: 'high',
    status: 'todo',
    linkedEntity: {
      type: 'Quote',
      title: 'Q-2024-0045',
      href: '/quotes/q-2024-0045',
    },
  },
  {
    id: '2',
    title: 'Complete NCR root cause analysis',
    dueDate: new Date(Date.now() + 86400000).toISOString(),
    priority: 'urgent',
    status: 'in_progress',
    linkedEntity: {
      type: 'NCR',
      title: 'NCR-2024-0012',
      href: '/quality/ncrs/ncr-2024-0012',
    },
  },
  {
    id: '3',
    title: 'Update product specifications',
    dueDate: new Date(Date.now() + 172800000).toISOString(),
    priority: 'medium',
    status: 'todo',
  },
  {
    id: '4',
    title: 'Prepare training materials',
    dueDate: new Date(Date.now() + 259200000).toISOString(),
    priority: 'low',
    status: 'todo',
  },
];

const mockActivity: ActivityItem[] = [
  {
    id: '1',
    type: 'quote_created',
    description: 'Created quote Q-2024-0046 for TechStart Inc',
    timestamp: new Date(Date.now() - 1800000).toISOString(),
    user: { name: 'John Smith' },
    link: '/quotes/q-2024-0046',
  },
  {
    id: '2',
    type: 'rfq_received',
    description: 'New RFQ received from Global Manufacturing',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    user: { name: 'System' },
    link: '/pipeline/rfq-2024-0089',
  },
  {
    id: '3',
    type: 'ncr_closed',
    description: 'NCR-2024-0011 closed after corrective action',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    user: { name: 'Jane Doe' },
    link: '/quality/ncrs/ncr-2024-0011',
  },
  {
    id: '4',
    type: 'quote_approved',
    description: 'Quote Q-2024-0044 approved by management',
    timestamp: new Date(Date.now() - 14400000).toISOString(),
    user: { name: 'Mike Johnson' },
    link: '/quotes/q-2024-0044',
  },
];

const mockRFQs: RFQSummary[] = [
  {
    id: '1',
    rfqNumber: 'RFQ-2024-0089',
    customerName: 'Global Manufacturing',
    title: 'Custom precision parts - 500 units',
    dueDate: new Date(Date.now() + 172800000).toISOString(),
    estimatedValue: 45000,
    priority: 'high',
    status: 'new',
  },
  {
    id: '2',
    rfqNumber: 'RFQ-2024-0088',
    customerName: 'TechStart Inc',
    title: 'Prototype assembly service',
    dueDate: new Date(Date.now() + 432000000).toISOString(),
    estimatedValue: 12500,
    priority: 'medium',
    status: 'reviewing',
  },
  {
    id: '3',
    rfqNumber: 'RFQ-2024-0087',
    customerName: 'Acme Corp',
    title: 'Annual maintenance contract',
    dueDate: new Date(Date.now() + 86400000).toISOString(),
    estimatedValue: 85000,
    priority: 'urgent',
    status: 'quoting',
  },
];

// Components
function KPICard({ data }: { data: KPICardData }) {
  const TrendIcon = data.trend === 'up' ? TrendingUp : data.trend === 'down' ? TrendingDown : null;
  const trendColor = data.trendIsGood ? 'text-success' : 'text-danger';

  const content = (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
              <data.icon className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{data.label}</p>
              <p className="text-2xl font-bold">{data.value}</p>
            </div>
          </div>
          {TrendIcon && data.change !== undefined && (
            <div className={cn('flex items-center gap-1 text-sm', trendColor)}>
              <TrendIcon className="h-4 w-4" />
              <span>{data.change > 0 ? '+' : ''}{data.change}</span>
            </div>
          )}
        </div>
        {data.changeLabel && (
          <p className="mt-2 text-xs text-muted-foreground">{data.changeLabel}</p>
        )}
      </CardContent>
    </Card>
  );

  if (data.href) {
    return <Link href={data.href}>{content}</Link>;
  }
  return content;
}

function TaskCard({ task }: { task: TaskItem }) {
  const priorityColors = {
    low: 'bg-muted text-muted-foreground',
    medium: 'bg-warning/10 text-warning',
    high: 'bg-danger/10 text-danger',
    urgent: 'bg-danger text-white',
  };

  const statusIcons = {
    todo: <Clock className="h-4 w-4 text-muted-foreground" />,
    in_progress: <AlertCircle className="h-4 w-4 text-warning" />,
    done: <CheckCircle2 className="h-4 w-4 text-success" />,
  };

  return (
    <div className="flex items-center gap-4 py-3 border-b last:border-0">
      {statusIcons[task.status]}
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{task.title}</p>
        {task.linkedEntity && (
          <Link
            href={task.linkedEntity.href}
            className="text-sm text-muted-foreground hover:text-primary"
          >
            {task.linkedEntity.type}: {task.linkedEntity.title}
          </Link>
        )}
      </div>
      <Badge className={priorityColors[task.priority]}>
        {task.priority}
      </Badge>
      <span className="text-sm text-muted-foreground whitespace-nowrap">
        {formatRelativeTime(new Date(task.dueDate))}
      </span>
    </div>
  );
}

function ActivityCard({ activity }: { activity: ActivityItem }) {
  return (
    <div className="flex items-start gap-4 py-3 border-b last:border-0">
      <Avatar fallback={activity.user.name} size="sm" />
      <div className="flex-1 min-w-0">
        <p className="text-sm">
          <span className="font-medium">{activity.user.name}</span>{' '}
          {activity.link ? (
            <Link href={activity.link} className="text-primary hover:underline">
              {activity.description}
            </Link>
          ) : (
            activity.description
          )}
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          {formatRelativeTime(new Date(activity.timestamp))}
        </p>
      </div>
    </div>
  );
}

function RFQCard({ rfq }: { rfq: RFQSummary }) {
  const priorityColors = {
    low: 'secondary',
    medium: 'warning',
    high: 'danger',
    urgent: 'destructive',
  } as const;

  const statusColors: Record<string, string> = {
    new: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    reviewing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
    quoting: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
  };

  return (
    <Link href={`/pipeline/${rfq.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-start justify-between mb-2">
            <div>
              <p className="font-medium">{rfq.rfqNumber}</p>
              <p className="text-sm text-muted-foreground">{rfq.customerName}</p>
            </div>
            <Badge variant={priorityColors[rfq.priority]}>{rfq.priority}</Badge>
          </div>
          <p className="text-sm mb-3 line-clamp-2">{rfq.title}</p>
          <div className="flex items-center justify-between">
            <Badge className={statusColors[rfq.status] || 'bg-muted'}>
              {rfq.status}
            </Badge>
            <div className="text-right">
              {rfq.estimatedValue && (
                <p className="font-medium">{formatCurrency(rfq.estimatedValue)}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Due {formatRelativeTime(new Date(rfq.dueDate))}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function TodayPage() {
  const { user } = useAuthStore();
  const [isLoading] = React.useState(false); // Will be true when fetching from API

  const greeting = React.useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            {greeting}, {user?.full_name?.split(' ')[0] || 'there'}!
          </h1>
          <p className="text-muted-foreground">
            <Calendar className="inline-block h-4 w-4 mr-1" />
            {formatDate(new Date(), { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <Button asChild>
          <Link href="/pipeline/new">
            Create RFQ
          </Link>
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {mockKPIs.map((kpi) => (
          <KPICard key={kpi.id} data={kpi} />
        ))}
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Tasks */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>My Tasks</CardTitle>
              <CardDescription>Tasks due today and upcoming</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/tasks">
                View All <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {mockTasks.length === 0 ? (
              <p className="text-center py-8 text-muted-foreground">
                No tasks due. Great job! 🎉
              </p>
            ) : (
              mockTasks.map((task) => <TaskCard key={task.id} task={task} />)
            )}
          </CardContent>
        </Card>

        {/* Activity */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>What's happening</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {mockActivity.map((activity) => (
              <ActivityCard key={activity.id} activity={activity} />
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Priority RFQs */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Priority RFQs</CardTitle>
            <CardDescription>Requests requiring immediate attention</CardDescription>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/pipeline">
              View Pipeline <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {mockRFQs.map((rfq) => (
              <RFQCard key={rfq.id} rfq={rfq} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
