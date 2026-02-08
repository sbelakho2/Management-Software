'use client';

import * as React from 'react';
import { Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  Edit,
  Factory,
  Play,
  Pause,
  CheckCircle,
  Clock,
  AlertTriangle,
  AlertCircle,
  Calendar,
  Users,
  Package,
  TrendingUp,
  Gauge,
  Lock,
  List,
  LayoutGrid,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn, formatDate, formatNumber, getInitials } from '@/lib/utils';
import { Pagination } from '@/components/ui/pagination';
import { useProductionStore } from '@/stores/production';
import { WorkOrderStatus, WorkOrderPriority } from '@/api/production';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

const statusConfig = {
  planned: { labelKey: 'pages.production.status.planned', variant: 'secondary' as const, icon: Calendar },
  released: { labelKey: 'pages.production.status.released', variant: 'default' as const, icon: Package },
  in_progress: { labelKey: 'pages.production.status.inProgress', variant: 'warning' as const, icon: Play },
  on_hold: { labelKey: 'pages.production.status.onHold', variant: 'destructive' as const, icon: Pause },
  completed: { labelKey: 'common.completed', variant: 'success' as const, icon: CheckCircle },
  cancelled: { labelKey: 'common.cancelled', variant: 'outline' as const, icon: AlertTriangle },
  draft: { labelKey: 'common.draft', variant: 'secondary' as const, icon: Edit },
  closed: { labelKey: 'pages.production.status.closed', variant: 'outline' as const, icon: Lock },
};

const priorityConfig = {
  [WorkOrderPriority.LOW]: { labelKey: 'common.priority.low', variant: 'outline' as const },
  [WorkOrderPriority.NORMAL]: { labelKey: 'common.priority.normal', variant: 'secondary' as const },
  [WorkOrderPriority.HIGH]: { labelKey: 'common.priority.high', variant: 'danger' as const },
  [WorkOrderPriority.URGENT]: { labelKey: 'common.priority.urgent', variant: 'danger' as const },
  [WorkOrderPriority.CRITICAL]: { labelKey: 'common.priority.critical', variant: 'danger' as const },
};

function ProductionStats() {
  const { t } = useI18n();
  const { stats } = useProductionStore();
  
  const inProgress = stats?.in_progress || 0;
  const onHold = stats?.on_hold || 0;
  const overdue = stats?.overdue || 0;
  const efficiency = stats?.efficiency_rate || 0;

  return (
    <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('production.stats.executionPulse') || 'Execution Pulse'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{inProgress}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('production.stats.suspendedNodes') || 'Suspended Nodes'}</p>
        <p className={cn('text-3xl font-mono font-bold tracking-tight tabular-nums', onHold > 0 ? 'text-rams-red' : 'text-foreground/90')}>
          {onHold}
        </p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('production.stats.overdueHorizon') || 'Overdue Horizon'}</p>
        <p className={cn('text-3xl font-mono font-bold tracking-tight tabular-nums', overdue > 0 ? 'text-rams-red' : 'text-foreground/90')}>
          {overdue}
        </p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-line">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('production.stats.operationalVelocity') || 'Operational Velocity'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{efficiency}%</p>
      </div>
    </div>
  );
}

function ProgressBar({ value, max, className }: { value: number; max: number; className?: string }) {
  const percentage = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className={cn('w-full h-1 bg-rams-panel border border-rams-line overflow-hidden', className)}>
      <div
        className="h-full bg-rams-orange transition-all duration-500 ease-out"
        style={{ width: `${Math.min(percentage, 100)}%` }}
      />
    </div>
  );
}

function WorkOrderRow({ workOrder }: { workOrder: any }) {
  const { t } = useI18n();
  const router = useRouter();
  const config = (statusConfig as any)[workOrder.status] || statusConfig[WorkOrderStatus.DRAFT];
  const priorityCfg = (priorityConfig as any)[workOrder.priority] || priorityConfig[WorkOrderPriority.NORMAL];
  const StatusIcon = config.icon;
  const dueDate = new Date(workOrder.scheduled_end || workOrder.created_at);
  const today = new Date();
  const isOverdue = dueDate < today && workOrder.status !== WorkOrderStatus.COMPLETED;

  return (
    <TableRow 
      className="transition-none cursor-pointer group"
      onClick={() => router.push(`/production/${workOrder.id}`)}
    >
      <TableCell>
        <div>
          <p className="font-mono font-bold text-rams-orange tabular-nums">{workOrder.work_order_number}</p>
          {workOrder.external_reference && (
            <p className="text-[9px] font-mono uppercase tracking-tight text-muted-foreground/40">{workOrder.external_reference}</p>
          )}
        </div>
      </TableCell>
      <TableCell>
        <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none line-clamp-1">{workOrder.product_name || (t('common.unknownProduct') || 'UNKNOWN_PRODUCT')}</p>
        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">{workOrder.part_number || (t('common.na') || 'N/A')}</p>
      </TableCell>
      <TableCell>
        <Badge variant={config.variant} size="sm">
          {t(config.labelKey).toUpperCase()}
        </Badge>
      </TableCell>
      <TableCell>
        <Badge variant={priorityCfg.variant} size="sm">{t(priorityCfg.labelKey).toUpperCase()}</Badge>
      </TableCell>
      <TableCell>
        <div className="w-24 space-y-1.5">
          <div className="flex justify-between text-[9px] font-mono font-bold tabular-nums">
            <span>{workOrder.quantity_completed}</span>
            <span className="text-muted-foreground/40">/ {workOrder.quantity_ordered}</span>
          </div>
          <ProgressBar value={workOrder.quantity_completed} max={workOrder.quantity_ordered} />
        </div>
      </TableCell>
      <TableCell className="text-[10px] font-bold text-foreground/70 uppercase">
        <div className="flex items-center gap-2">
          <Factory className="h-3 w-3 opacity-40" />
          {workOrder.work_center_name || '—'}
        </div>
      </TableCell>
      <TableCell>
        {workOrder.assigned_to_name ? (
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">{workOrder.assigned_to_name.split(' ')[0]}</span>
          </div>
        ) : (
          <span className="text-[9px] font-mono font-black text-muted-foreground/20 uppercase tracking-widest">{t('common.unassigned') || 'UNASSIGNED'}</span>
        )}
      </TableCell>
      <TableCell>
        <div className={cn('font-mono text-[10px] uppercase tracking-tighter', isOverdue ? 'text-rams-red' : 'text-muted-foreground/60')}>
          {formatDate(dueDate)}
          {isOverdue && <span className="text-[8px] ml-1 opacity-60">({t('common.overdue') || 'OVERDUE'})</span>}
        </div>
      </TableCell>
      <TableCell onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push(`/production/${workOrder.id}`)}>
              <Eye className="mr-2 h-3.5 w-3.5" /> {t('pages.production.actions.analyze') || 'ANALYZE'}
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Edit className="mr-2 h-3.5 w-3.5" /> {t('pages.production.actions.modify') || 'MODIFY'}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

function WorkOrderCard({ workOrder }: { workOrder: any }) {
  const { t } = useI18n();
  const router = useRouter();
  const config = (statusConfig as any)[workOrder.status] || statusConfig[WorkOrderStatus.DRAFT];
  const priorityCfg = (priorityConfig as any)[workOrder.priority] || priorityConfig[WorkOrderPriority.NORMAL];
  const StatusIcon = config.icon;
  const dueDate = new Date(workOrder.scheduled_end || workOrder.created_at);
  const isOverdue = dueDate < new Date() && workOrder.status !== WorkOrderStatus.COMPLETED;

  return (
    <Card 
      className="rounded-rams-sm group cursor-pointer"
      onClick={() => router.push(`/production/${workOrder.id}`)}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="p-2 bg-rams-panel border border-rams-line text-rams-orange group-hover:bg-rams-orange group-hover:text-black transition-none">
              <StatusIcon className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-sans font-black text-sm uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{workOrder.work_order_number}</h3>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-0.5">{t('pages.production.protocolProductionNode') || 'PROTOCOL: PRODUCTION_NODE'}</p>
            </div>
          </div>
          <Badge variant={config.variant} size="sm">{t(config.labelKey).toUpperCase()}</Badge>
        </div>

        <div className="space-y-4 mb-6">
          <div>
            <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 line-clamp-1">{workOrder.product_name}</p>
            <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">{workOrder.part_number}</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40">{t('pages.production.workCenter')}</p>
              <div className="flex items-center gap-2 text-[10px] font-bold text-foreground/70 uppercase">
                <Factory className="h-3 w-3 opacity-40" />
                {workOrder.work_center_name || '—'}
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40">{t('common.priority.label')}</p>
              <Badge variant={priorityCfg.variant} size="sm" className="h-4">{t(priorityCfg.labelKey).toUpperCase()}</Badge>
            </div>
          </div>
        </div>

        <div className="space-y-2 mb-6">
          <div className="flex justify-between text-[9px] font-mono font-bold tabular-nums">
            <span className="text-muted-foreground/40 uppercase">{t('pages.production.table.exProgress') || 'EX_PROGRESS'}</span>
            <span>{workOrder.quantity_completed} / {workOrder.quantity_ordered}</span>
          </div>
          <ProgressBar value={workOrder.quantity_completed} max={workOrder.quantity_ordered} />
        </div>

        <div className="pt-6 border-t border-rams-line flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Avatar className="h-6 w-6 rounded-none border border-rams-line">
              <AvatarFallback className="text-[8px] bg-rams-panel font-mono font-black">{getInitials(workOrder.assigned_to_name || 'U')}</AvatarFallback>
            </Avatar>
            <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{workOrder.assigned_to_name ? workOrder.assigned_to_name.split(' ')[0] : (t('common.unassigned') || 'UNASSIGNED')}</span>
          </div>
          <div className={cn('font-mono text-[10px] uppercase tracking-tighter', isOverdue ? 'text-rams-red' : 'text-muted-foreground/60')}>
            {formatDate(dueDate)}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ProductionPageContent() {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { 
    workOrders, 
    fetchWorkOrders, 
    fetchStats,
    loading,
    error 
  } = useProductionStore();
  const workOrdersList = React.useMemo(() => (Array.isArray(workOrders) ? workOrders : []), [workOrders]);

  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [workCenterFilter, setWorkCenterFilter] = React.useState<string>('all');
  const [viewMode, setViewMode] = React.useState<'list' | 'cards'>(
    (searchParams.get('view') as 'list' | 'cards') || 'list'
  );

  React.useEffect(() => {
    fetchWorkOrders();
    fetchStats();
  }, [fetchWorkOrders, fetchStats]);

  const workCenters = React.useMemo(() => {
    return [...new Set(workOrdersList.map((wo) => wo.work_center_name).filter(Boolean))];
  }, [workOrdersList]);

  const filteredWorkOrders = React.useMemo(() => {
    return workOrdersList.filter((wo) => {
      const matchesSearch = searchQuery === '' ||
        wo.work_order_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (wo.product_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (wo.part_number || '').toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'all' || wo.status === statusFilter;
      const matchesWorkCenter = workCenterFilter === 'all' || wo.work_center_name === workCenterFilter;
      return matchesSearch && matchesStatus && matchesWorkCenter;
    });
  }, [workOrdersList, searchQuery, statusFilter, workCenterFilter]);

  const PAGE_SIZE = 12;
  const [woPage, setWoPage] = React.useState(1);
  React.useEffect(() => setWoPage(1), [searchQuery, statusFilter, workCenterFilter]);
  const woTotalPages = Math.max(1, Math.ceil(filteredWorkOrders.length / PAGE_SIZE));
  const paginatedWorkOrders = filteredWorkOrders.slice((woPage - 1) * PAGE_SIZE, woPage * PAGE_SIZE);

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="production-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.production.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.production.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.production.station') || 'STATION: PRODUCTION-01'}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={() => router.push('/production/new')} size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase">
            <Plus className="mr-2 h-3.5 w-3.5" />
            {t('production.initializeWO') || 'INITIALIZE_WO'}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <ProductionStats />

      {/* Filters & View Toggle */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-4 flex-wrap max-w-4xl">
          <div className="relative flex-1 min-w-[240px] group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 transition-colors group-focus-within:text-rams-orange" />
            <Input
              placeholder={t('production.searchPlaceholder') || 'SEARCH_WORK_ORDERS...'}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-10 text-[10px]"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[160px] h-10 text-[10px]">
              <Filter className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder={t('pages.production.filters.statusState')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('pages.production.filters.allStatus')}</SelectItem>
              {Object.values(WorkOrderStatus).map((status) => (
                <SelectItem key={status} value={status}>
                  {status.toUpperCase().replace('_', ' ')}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={workCenterFilter} onValueChange={setWorkCenterFilter}>
            <SelectTrigger className="w-[180px] h-10 text-[10px]">
              <Factory className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder={t('pages.production.filters.workCenter')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('pages.production.filters.allNodes')}</SelectItem>
              {workCenters.map((wc) => (
                <SelectItem key={wc as string} value={wc as string}>{String(wc).toUpperCase()}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1 bg-rams-panel p-1 border border-rams-line rounded-rams-sm">
          <Button
            variant={viewMode === 'list' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('list')}
            className={cn("h-8 px-3 rounded-none", viewMode === 'list' ? "bg-rams-orange text-black" : "text-muted-foreground")}
          >
            {t('common.list') || 'LIST'}
          </Button>
          <Button
            variant={viewMode === 'cards' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('cards')}
            className={cn("h-8 px-3 rounded-none", viewMode === 'cards' ? "bg-rams-orange text-black" : "text-muted-foreground")}
          >
            {t('common.grid') || 'GRID'}
          </Button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-rams-sm border border-destructive/50 bg-destructive/10 p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="text-sm font-bold text-destructive">Error loading production data</p>
              <p className="text-xs text-muted-foreground">{error}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => { fetchWorkOrders(); fetchStats(); }}>
            Retry
          </Button>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="industrial-panel p-6 space-y-4">
              <div className="h-4 w-1/3 bg-rams-panel animate-pulse" />
              <div className="h-12 bg-rams-panel animate-pulse" />
              <div className="h-4 w-full bg-rams-panel animate-pulse" />
            </div>
          ))}
        </div>
      ) : filteredWorkOrders.length === 0 ? (
        <div className="py-24 text-center border border-dashed border-rams-line bg-rams-panel/20">
          <Factory className="mx-auto h-12 w-12 text-muted-foreground/20" />
          <div className="mt-4">
            <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">{t('production.emptyState.title') || 'Zero protocols identified'}</p>
            <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">{t('production.emptyState.description') || 'Adjust parameters or initialize new work order'}</p>
          </div>
        </div>
      ) : viewMode === 'list' ? (
        <Card className="rounded-rams-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('pages.production.table.orderId')}</TableHead>
                <TableHead>{t('pages.production.table.productNode')}</TableHead>
                <TableHead>{t('pages.production.table.statusState')}</TableHead>
                <TableHead>{t('pages.production.table.priorityLevel')}</TableHead>
                <TableHead>{t('pages.production.table.exProgress')}</TableHead>
                <TableHead>{t('pages.production.table.workCenter')}</TableHead>
                <TableHead>{t('pages.production.table.operator')}</TableHead>
                <TableHead>{t('pages.production.table.dueHorizon')}</TableHead>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedWorkOrders.map((wo) => (
                <WorkOrderRow key={wo.id} workOrder={wo} />
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {paginatedWorkOrders.map((wo) => (
            <WorkOrderCard key={wo.id} workOrder={wo} />
          ))}
        </div>
      )}
      <Pagination currentPage={woPage} totalPages={woTotalPages} onPageChange={setWoPage} totalItems={filteredWorkOrders.length} />
    </div>
  );
}

export default function ProductionPage() {
  return (
    <Suspense fallback={
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-32 bg-muted animate-pulse rounded" />
            <div className="h-4 w-64 bg-muted animate-pulse rounded mt-2" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    }>
      <ProductionPageContent />
    </Suspense>
  );
}
