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
  Target,
  Shield,
  type LucideIcon,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarGroup } from '@/components/ui/avatar';
import { Skeleton, SkeletonCard } from '@/components/ui/skeleton';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { cn, formatDate, formatCurrency, formatRelativeTime } from '@/lib/utils';
import { useAuthStore } from '@/stores';
import { useTodayStore } from '@/stores/today';
import { hasPageAccess } from '@/lib/page-access';
import { UserRole } from '@/types';
import { useI18n } from '@/contexts/i18n-context';

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

// Icon color mapping for KPI data
const getIconColor = (label: string, trendIsGood?: boolean): 'primary' | 'success' | 'warning' | 'danger' => {
  if (label.includes('RFQ')) return 'primary';
  if (label.includes('NCR') || label.includes('Alert')) return trendIsGood ? 'success' : 'danger';
  if (label.includes('Pending')) return 'warning';
  return 'primary';
};

function TaskCard({ task }: { task: TaskItem }) {
  const priorityConfig = {
    low: { variant: 'secondary' as const, label: 'Low' },
    medium: { variant: 'default' as const, label: 'Medium' },
    high: { variant: 'warning' as const, label: 'High' },
    urgent: { variant: 'danger' as const, label: 'Urgent' },
  };

  const statusIcons = {
    todo: <Clock className="h-3.5 w-3.5 text-muted-foreground/40" />,
    in_progress: <AlertCircle className="h-3.5 w-3.5 text-rams-orange/60" />,
    done: <CheckCircle2 className="h-3.5 w-3.5 text-rams-green/60" />,
  };

  const cfg = priorityConfig[task.priority];

  return (
    <div className="flex items-center justify-between p-4 bg-rams-panel/40 border border-rams-line hover:bg-rams-panel transition-none group">
      <div className="flex items-center gap-4 min-w-0">
        <div className="p-2 rounded-rams-sm bg-rams-module border border-rams-line group-hover:border-rams-orange transition-none">
          {statusIcons[task.status]}
        </div>
        <div className="min-w-0">
          <p className="font-sans font-black text-xs uppercase tracking-tight truncate text-foreground/80 group-hover:text-rams-orange transition-none">{task.title}</p>
          {task.linkedEntity && (
            <Link
              href={task.linkedEntity.href}
              className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 hover:text-rams-orange transition-none"
            >
              {task.linkedEntity.type}: {task.linkedEntity.title}
            </Link>
          )}
        </div>
      </div>
      <div className="flex items-center gap-4 shrink-0">
        <Badge variant={cfg.variant} size="sm">
          {cfg.label.toUpperCase()}
        </Badge>
        <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/30 whitespace-nowrap">
          {formatRelativeTime(new Date(task.dueDate)).toUpperCase()}
        </span>
      </div>
    </div>
  );
}

function ActivityCard({ activity }: { activity: ActivityItem }) {
  return (
    <div className="flex items-start gap-4 p-4 bg-rams-panel/20 border border-rams-line hover:bg-rams-panel transition-none group">
      <Avatar fallback={activity.user.name} size="sm" className="rounded-rams-sm border border-rams-line" />
      <div className="flex-1 min-w-0">
        <p className="font-sans font-black text-[11px] uppercase tracking-tight text-foreground/80 leading-snug group-hover:text-rams-orange transition-none">
          <span className="text-muted-foreground/40">{activity.user.name.split(' ')[0]}</span> — {activity.description}
        </p>
        <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/20 mt-2">
          {formatRelativeTime(new Date(activity.timestamp)).toUpperCase()}
        </p>
      </div>
      {activity.link && (
        <Button variant="ghost" size="icon" asChild className="h-7 w-7 rounded-rams-sm hover:bg-rams-panel transition-none">
          <Link href={activity.link}>
            <ArrowRight className="h-3.5 w-3.5 opacity-20 group-hover:opacity-100 group-hover:text-rams-orange group-hover:translate-x-0.5 transition-all" />
          </Link>
        </Button>
      )}
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
    new: 'bg-rams-steel/10 text-rams-steel border-rams-steel/20',
    reviewing: 'bg-rams-orange/10 text-rams-orange border-rams-orange/20',
    quoting: 'bg-rams-green/10 text-rams-green border-rams-green/20',
  };

  return (
    <Link href={`/pipeline/${rfq.id}`} className="group block h-full">
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module hover:border-rams-orange/40 transition-none h-full">
        <CardContent className="p-5 space-y-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-mono text-[10px] font-bold text-rams-orange tabular-nums">{rfq.rfqNumber}</p>
              <p className="font-sans font-black text-sm uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none mt-0.5">{rfq.customerName}</p>
            </div>
            <Badge variant={priorityColors[rfq.priority]} size="sm">
              {rfq.priority.toUpperCase()}
            </Badge>
          </div>
          <p className="text-xs font-medium text-muted-foreground/60 line-clamp-2 uppercase leading-relaxed">{rfq.title}</p>
          <div className="flex items-center justify-between pt-6 border-t border-rams-line">
            <Badge 
              variant="outline"
              className={cn(
                'rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4', 
                statusColors[rfq.status] || 'bg-rams-panel'
              )}
            >
              {rfq.status.toUpperCase()}
            </Badge>
            <div className="text-right">
              {rfq.estimatedValue && (
                <p className="text-sm font-mono font-bold tabular-nums text-foreground/90">{formatCurrency(rfq.estimatedValue)}</p>
              )}
              <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/30 mt-1">
                DUE {formatRelativeTime(new Date(rfq.dueDate)).toUpperCase()}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function TodayPage() {
  const { t } = useI18n();
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
    <div className="space-y-8 page-fade-in pb-12" data-testid="ops-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.ops.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.ops.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: OPS-CENTER-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <AmbientStatus 
            status={(data?.abnormalities || []).length > 0 ? 'warning' : 'operational'} 
            label={(data?.abnormalities || []).length > 0 ? t('pages.ops.issuesDetected') : t('pages.ops.allSystemsOperational')}
          />
          {hasPageAccess('/pipeline/new', userRoles) && (
            <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]" asChild>
              <Link href="/pipeline/new">
                <Plus className="mr-2 h-3.5 w-3.5" />
                {t('pages.ops.initializeRfq')}
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-line bg-rams-line">
        {kpis.map((kpi) => (
          <div key={kpi.id} className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group hover:bg-rams-panel transition-none cursor-help">
            <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{kpi.label}</p>
            <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{kpi.value}</div>
            {kpi.change !== undefined && (
              <p className={cn(
                "text-[9px] font-mono font-bold uppercase tracking-widest mt-2 flex items-center gap-1",
                kpi.trend === 'up' ? (kpi.trendIsGood ? "text-rams-green" : "text-rams-red") : 
                kpi.trend === 'down' ? (kpi.trendIsGood ? "text-rams-green" : "text-rams-red") : 
                "text-muted-foreground/40"
              )}>
                {kpi.trend === 'up' ? <TrendingUp className="h-3 w-3" /> : 
                 kpi.trend === 'down' ? <TrendingDown className="h-3 w-3" /> : null}
                {kpi.change > 0 ? '+' : ''}{kpi.change}% ALPHA
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Tasks */}
        <Card className="lg:col-span-2 rounded-rams-sm overflow-hidden border-rams-line">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                <Target className="h-4 w-4 text-rams-orange" />
                {t('pages.ops.strategicPriorities')}
              </CardTitle>
            </div>
            <Button variant="ghost" size="sm" asChild className="rounded-rams-sm text-[9px] font-black uppercase tracking-widest hover:bg-rams-orange/10 hover:text-rams-orange transition-none">
              <Link href="/tasks">
                {t('common.viewAll')} <ArrowRight className="ml-2 h-3.5 w-3.5" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="p-1 space-y-1">
            {tasks.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground/20">
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-20" />
                <p className="text-[9px] font-mono font-black uppercase tracking-widest">ZERO_PRIORITIES_IDENTIFIED</p>
              </div>
            ) : (
              tasks.map((task) => <TaskCard key={task.id} task={task} />)
            )}
          </CardContent>
        </Card>

        {/* Abnormalities */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-line">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2 text-rams-red">
              <AlertTriangle className="h-4 w-4" />
              {t('pages.ops.criticalAnomalies')}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {(data?.abnormalities || []).length === 0 ? (
              <div className="py-12 text-center text-muted-foreground/20">
                <Shield className="h-8 w-8 mx-auto mb-2 opacity-20" />
                <p className="text-[9px] font-mono font-black uppercase tracking-widest">{t('pages.ops.systemStable')}</p>
              </div>
            ) : (
              <div className="divide-y divide-rams-line/30">
                {data?.abnormalities.map((a: any) => (
                  <div key={a.id} className="p-4 flex items-start gap-4 hover:bg-rams-red/5 transition-none group">
                    <div className="mt-0.5 p-2 rounded-rams-sm bg-rams-red/5 border border-rams-red/20 text-rams-red">
                      <AlertCircle className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-red transition-none">{a.title}</p>
                      <p className="text-[10px] text-muted-foreground mt-1 uppercase leading-relaxed font-medium">{a.description}</p>
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
