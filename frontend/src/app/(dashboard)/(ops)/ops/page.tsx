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
  Plus,
  type LucideIcon,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarGroup } from '@/components/ui/avatar';
import { Skeleton, SkeletonCard } from '@/components/ui/skeleton';
import { cn, formatDate, formatCurrency, formatRelativeTime } from '@/lib/utils';
import { useAuthStore } from '@/stores';
import { useTodayStore } from '@/stores/today';
import { hasPageAccess } from '@/lib/page-access';
import { UserRole } from '@/types';

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
  const { data, loading, fetchTodayScreen } = useTodayStore();

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);

  React.useEffect(() => {
    if (user) {
      const name = (user.full_name || '').trim() || (user.email || '').trim() || 'User';
      fetchTodayScreen(user.id, name);
    }
  }, [user, fetchTodayScreen]);

  const greeting = data?.greeting || 'Hello';

  if (loading && !data) {
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

  // Map backend metrics to KPICardData and filter based on role
  const kpis: KPICardData[] = (data?.quick_metrics || [])
    .map((m: any) => ({
      id: m.id,
      label: m.name,
      value: m.value,
      change: m.trend_value,
      trend: m.trend as any,
      trendIsGood: m.status === 'success' || m.status === 'on_track',
      icon: m.name.includes('RFQ') ? FileText : m.name.includes('NCR') ? AlertTriangle : Package,
      href: m.link,
    }))
    .filter((k: KPICardData) => !k.href || hasPageAccess(k.href, userRoles));

  // Map backend priorities to TaskItem and filter
  const tasks: TaskItem[] = (data?.top_priorities || [])
    .map((p: any) => ({
      id: p.id,
      title: p.title,
      dueDate: p.due_date,
      priority: p.priority_level.toLowerCase() as 'low' | 'medium' | 'high' | 'urgent',
      status: 'todo' as const,
      linkedEntity: {
        type: p.entity_type,
        title: p.entity_id.substring(0, 8),
        href: `/${p.entity_type}/${p.entity_id}`,
      },
    }))
    .filter((t: TaskItem) => !t.linkedEntity?.href || hasPageAccess(t.linkedEntity.href, userRoles));

  return (
    <div className="space-y-8 page-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Operations Command
          </h1>
          <p className="text-muted-foreground font-medium flex items-center gap-2">
            <Calendar className="h-4 w-4 text-primary" />
            {formatDate(new Date(), { weekday: 'long', month: 'long', day: 'numeric' })} • Real-time Production Pulse
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasPageAccess('/pipeline/new', userRoles) && (
            <Button size="lg" className="rounded-xl shadow-glow subtle-shine" asChild>
              <Link href="/pipeline/new">
                <Plus className="mr-2 h-4 w-4" />
                Create RFQ
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <KPICard key={kpi.id} data={kpi} />
        ))}
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Tasks */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>My Priorities</CardTitle>
              <CardDescription>Top priorities for today</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/tasks">
                View All <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {tasks.length === 0 ? (
              <p className="text-center py-8 text-muted-foreground">
                No priorities set. Great job! 🎉
              </p>
            ) : (
              tasks.map((task) => <TaskCard key={task.id} task={task} />)
            )}
          </CardContent>
        </Card>

        {/* Abnormalities */}
        <Card>
          <CardHeader>
            <CardTitle>Abnormalities</CardTitle>
            <CardDescription>Issues requiring attention</CardDescription>
          </CardHeader>
          <CardContent>
            {(data?.abnormalities || []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No abnormalities detected.</p>
            ) : (
              <div className="space-y-4">
                {data?.abnormalities.map((a: any) => (
                  <div key={a.id} className="flex items-start gap-3 text-sm">
                    <AlertCircle className="h-4 w-4 text-danger mt-0.5" />
                    <div>
                      <p className="font-medium">{a.title}</p>
                      <p className="text-xs text-muted-foreground">{a.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
