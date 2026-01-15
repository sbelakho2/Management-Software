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
    <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md hover:shadow-premium-hover hover:-translate-y-1 transition-all duration-500 group">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-sm transition-transform duration-500 group-hover:scale-110">
              <data.icon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{data.label}</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{data.value}</p>
            </div>
          </div>
          {TrendIcon && data.change !== undefined && (
            <div className={cn('flex flex-col items-end gap-1', trendColor)}>
              <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest">
                <TrendIcon className="h-3 w-3" />
                <span>{data.change > 0 ? '+' : ''}{data.change}%</span>
              </div>
            </div>
          )}
        </div>
        {data.changeLabel && (
          <p className="mt-3 text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40">{data.changeLabel}</p>
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
  const priorityConfig = {
    low: { bg: 'bg-muted/50', text: 'text-muted-foreground', label: 'Low' },
    medium: { bg: 'bg-warning/10', text: 'text-warning', label: 'Medium' },
    high: { bg: 'bg-danger/10', text: 'text-danger', label: 'High' },
    urgent: { bg: 'bg-danger', text: 'text-white', label: 'Urgent' },
  };

  const statusIcons = {
    todo: <Clock className="h-4 w-4 text-muted-foreground/40" />,
    in_progress: <AlertCircle className="h-4 w-4 text-warning/60" />,
    done: <CheckCircle2 className="h-4 w-4 text-success/60" />,
  };

  const cfg = priorityConfig[task.priority];

  return (
    <div className="flex items-center justify-between p-4 rounded-2xl bg-muted/10 border border-border/5 hover:bg-primary/5 hover:border-primary/10 transition-all duration-300 group">
      <div className="flex items-center gap-4 min-w-0">
        <div className="p-2 rounded-xl bg-background shadow-sm">
          {statusIcons[task.status]}
        </div>
        <div className="min-w-0">
          <p className="font-heading font-bold text-sm tracking-tight truncate text-foreground/80 group-hover:text-primary transition-colors">{task.title}</p>
          {task.linkedEntity && (
            <Link
              href={task.linkedEntity.href}
              className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 hover:text-primary transition-colors"
            >
              {task.linkedEntity.type}: {task.linkedEntity.title}
            </Link>
          )}
        </div>
      </div>
      <div className="flex items-center gap-4 shrink-0">
        <Badge className={cn('rounded-md px-1.5 py-0 text-[9px] font-bold uppercase tracking-widest border-none', cfg.bg, cfg.text)}>
          {cfg.label}
        </Badge>
        <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/30 whitespace-nowrap">
          {formatRelativeTime(new Date(task.dueDate))}
        </span>
      </div>
    </div>
  );
}

function ActivityCard({ activity }: { activity: ActivityItem }) {
  return (
    <div className="flex items-start gap-4 p-4 rounded-2xl bg-muted/5 border border-border/5 hover:bg-muted/10 transition-all duration-300 group">
      <Avatar fallback={activity.user.name} size="sm" className="ring-2 ring-background shadow-sm" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-relaxed">
          <span className="font-heading font-bold text-foreground/90">{activity.user.name}</span>{' '}
          {activity.link ? (
            <Link href={activity.link} className="text-primary hover:underline underline-offset-4 decoration-primary/30">
              {activity.description}
            </Link>
          ) : (
            <span className="text-muted-foreground">{activity.description}</span>
          )}
        </p>
        <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-muted-foreground/30 mt-1.5">
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
    <Link href={`/pipeline/${rfq.id}`} className="group">
      <Card className="hover:shadow-premium-hover hover:-translate-y-1 transition-all duration-500 border-border/40 bg-card/40 backdrop-blur-sm rounded-[1.5rem] h-full">
        <CardContent className="p-5 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-mono text-xs font-bold text-primary/60">{rfq.rfqNumber}</p>
              <p className="font-heading font-bold text-sm tracking-tight group-hover:text-primary transition-colors">{rfq.customerName}</p>
            </div>
            <Badge variant={priorityColors[rfq.priority]} className="rounded-md px-1.5 py-0 text-[9px] font-bold uppercase tracking-widest">{rfq.priority}</Badge>
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2 font-medium leading-relaxed">{rfq.title}</p>
          <div className="flex items-center justify-between pt-4 border-t border-border/10">
            <Badge className={cn('rounded-md px-1.5 py-0 text-[9px] font-bold uppercase tracking-widest border-none', statusColors[rfq.status] || 'bg-muted')}>
              {rfq.status}
            </Badge>
            <div className="text-right">
              {rfq.estimatedValue && (
                <p className="text-sm font-heading font-bold tracking-tight">{formatCurrency(rfq.estimatedValue)}</p>
              )}
              <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">
                DUE {formatRelativeTime(new Date(rfq.dueDate))}
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
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Operations Command
          </h1>
          <p className="text-sm text-muted-foreground font-medium flex items-center gap-2">
            <Calendar className="h-4 w-4 text-primary/60" />
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
