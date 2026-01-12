'use client';

import * as React from 'react';
import { Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
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
  Calendar,
  Users,
  Package,
  TrendingUp,
  Gauge,
  Lock,
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
import { cn, formatDate, formatNumber, getInitials } from '@/lib/utils';
import { useProductionStore } from '@/stores/production';
import { WorkOrderStatus, WorkOrderPriority } from '@/api/production';

const statusConfig = {
  planned: { label: 'Planned', variant: 'secondary' as const, icon: Calendar },
  released: { label: 'Released', variant: 'default' as const, icon: Package },
  in_progress: { label: 'In Progress', variant: 'warning' as const, icon: Play },
  on_hold: { label: 'On Hold', variant: 'destructive' as const, icon: Pause },
  completed: { label: 'Completed', variant: 'success' as const, icon: CheckCircle },
  cancelled: { label: 'Cancelled', variant: 'outline' as const, icon: AlertTriangle },
  draft: { label: 'Draft', variant: 'secondary' as const, icon: Edit },
  closed: { label: 'Closed', variant: 'outline' as const, icon: Lock },
};

const priorityConfig = {
  [WorkOrderPriority.LOW]: { label: 'Low', variant: 'outline' as const },
  [WorkOrderPriority.NORMAL]: { label: 'Normal', variant: 'secondary' as const },
  [WorkOrderPriority.HIGH]: { label: 'High', variant: 'danger' as const },
  [WorkOrderPriority.URGENT]: { label: 'Urgent', variant: 'danger' as const },
  [WorkOrderPriority.CRITICAL]: { label: 'Critical', variant: 'danger' as const },
};

function ProductionStats() {
  const { stats } = useProductionStore();
  
  const inProgress = stats?.by_status?.in_progress || 0;
  const onHold = stats?.by_status?.on_hold || 0;
  const dueSoon = stats?.due_soon || 0;
  const onTimeRate = stats?.on_time_rate || 0;

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/10">
              <Play className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold">{inProgress}</p>
              <p className="text-sm text-muted-foreground">In Progress</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-lg', onHold > 0 ? 'bg-danger/10' : 'bg-muted')}>
              <Pause className={cn('h-5 w-5', onHold > 0 ? 'text-danger' : 'text-muted-foreground')} />
            </div>
            <div>
              <p className={cn('text-2xl font-bold', onHold > 0 && 'text-danger')}>
                {onHold}
              </p>
              <p className="text-sm text-muted-foreground">On Hold</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Clock className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">{dueSoon}</p>
              <p className="text-sm text-muted-foreground">Due This Week</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-success/10">
              <TrendingUp className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold">{onTimeRate}%</p>
              <p className="text-sm text-muted-foreground">On-Time Rate</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ProgressBar({ value, max, className }: { value: number; max: number; className?: string }) {
  const percentage = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className={cn('w-full h-2 bg-muted rounded-full overflow-hidden', className)}>
      <div
        className={cn(
          'h-full transition-all',
          percentage >= 100 ? 'bg-success' : percentage >= 50 ? 'bg-warning' : 'bg-primary'
        )}
        style={{ width: `${Math.min(percentage, 100)}%` }}
      />
    </div>
  );
}

function WorkOrderRow({ workOrder }: { workOrder: any }) {
  const router = useRouter();
  const config = (statusConfig as any)[workOrder.status] || statusConfig[WorkOrderStatus.DRAFT];
  const priorityCfg = (priorityConfig as any)[workOrder.priority] || priorityConfig[WorkOrderPriority.NORMAL];
  const StatusIcon = config.icon;
  const progress = (workOrder.quantity_completed / workOrder.quantity_ordered) * 100;
  const dueDate = new Date(workOrder.scheduled_end || workOrder.created_at);
  const today = new Date();
  const isOverdue = dueDate < today && workOrder.status !== WorkOrderStatus.COMPLETED;

  return (
    <tr 
      className="border-b hover:bg-muted/50 cursor-pointer transition-colors"
      onClick={() => router.push(`/production/${workOrder.id}`)}
    >
      <td className="py-3 px-4">
        <div>
          <p className="font-medium">{workOrder.work_order_number}</p>
          {workOrder.external_reference && (
            <p className="text-sm text-muted-foreground">{workOrder.external_reference}</p>
          )}
        </div>
      </td>
      <td className="py-3 px-4">
        <div>
          <p>{workOrder.product_name || 'Unknown Product'}</p>
          <p className="text-sm text-muted-foreground font-mono">{workOrder.part_number || 'N/A'}</p>
        </div>
      </td>
      <td className="py-3 px-4">
        <Badge variant={config.variant} className="gap-1">
          <StatusIcon className="h-3 w-3" />
          {config.label}
        </Badge>
      </td>
      <td className="py-3 px-4">
        <Badge variant={priorityCfg.variant}>{priorityCfg.label}</Badge>
      </td>
      <td className="py-3 px-4">
        <div className="w-24">
          <div className="flex justify-between text-xs mb-1">
            <span>{workOrder.quantity_completed}</span>
            <span>/ {workOrder.quantity_ordered}</span>
          </div>
          <ProgressBar value={workOrder.quantity_completed} max={workOrder.quantity_ordered} />
        </div>
      </td>
      <td className="py-3 px-4 text-muted-foreground">{workOrder.work_center_name || '—'}</td>
      <td className="py-3 px-4">
        {workOrder.assigned_to_name ? (
          <div className="flex items-center gap-2">
            <span className="text-sm">{workOrder.assigned_to_name}</span>
          </div>
        ) : (
          <span className="text-muted-foreground">Unassigned</span>
        )}
      </td>
      <td className={cn('py-3 px-4', isOverdue && 'text-danger font-medium')}>
        {formatDate(dueDate)}
        {isOverdue && ' (overdue)'}
      </td>
      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push(`/production/${workOrder.id}`)}>
              <Eye className="mr-2 h-4 w-4" />
              View
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

function WorkOrderCard({ workOrder }: { workOrder: any }) {
  const router = useRouter();
  const config = (statusConfig as any)[workOrder.status] || statusConfig[WorkOrderStatus.DRAFT];
  const priorityCfg = (priorityConfig as any)[workOrder.priority] || priorityConfig[WorkOrderPriority.NORMAL];
  const StatusIcon = config.icon;
  const progress = (workOrder.quantity_completed / workOrder.quantity_ordered) * 100;
  const dueDate = new Date(workOrder.scheduled_end || workOrder.created_at);
  const today = new Date();
  const isOverdue = dueDate < today && workOrder.status !== WorkOrderStatus.COMPLETED;

  return (
    <Card 
      className={cn(
        'hover:shadow-md transition-shadow cursor-pointer',
        isOverdue && 'border-danger/50'
      )}
      onClick={() => router.push(`/production/${workOrder.id}`)}
    >
      <CardContent className="pt-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="font-medium">{workOrder.work_order_number}</p>
            <p className="text-sm text-muted-foreground">{workOrder.product_name}</p>
          </div>
          <Badge variant={priorityCfg.variant}>{priorityCfg.label}</Badge>
        </div>

        <Badge variant={config.variant} className="gap-1 mb-3">
          <StatusIcon className="h-3 w-3" />
          {config.label}
        </Badge>

        <div className="space-y-2 mb-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span>{workOrder.quantity_completed} / {workOrder.quantity_ordered}</span>
          </div>
          <ProgressBar value={workOrder.quantity_completed} max={workOrder.quantity_ordered} />
        </div>

        <div className="flex items-center justify-between text-sm pt-3 border-t">
          <div className="flex items-center gap-1 text-muted-foreground">
            <Factory className="h-4 w-4" />
            {workOrder.work_center_name || '—'}
          </div>
          <div className={cn(isOverdue && 'text-danger font-medium')}>
            Due {formatDate(dueDate, { month: 'short', day: 'numeric' })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ProductionPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { 
    workOrders, 
    fetchWorkOrders, 
    fetchStats,
    loading 
  } = useProductionStore();

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
    return [...new Set(workOrders.map((wo) => wo.work_center_name).filter(Boolean))];
  }, [workOrders]);

  const filteredWorkOrders = React.useMemo(() => {
    return workOrders.filter((wo) => {
      const matchesSearch = searchQuery === '' ||
        wo.work_order_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (wo.product_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (wo.part_number || '').toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'all' || wo.status === statusFilter;
      const matchesWorkCenter = workCenterFilter === 'all' || wo.work_center_name === workCenterFilter;
      return matchesSearch && matchesStatus && matchesWorkCenter;
    });
  }, [workOrders, searchQuery, statusFilter, workCenterFilter]);

  return (
    <div className="space-y-6" data-testid="production-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Production</h1>
          <p className="text-muted-foreground">Manage work orders and track manufacturing progress</p>
        </div>
        <Button onClick={() => router.push('/production/new')}>
          <Plus className="mr-2 h-4 w-4" />
          New Work Order
        </Button>
      </div>

      {/* Stats */}
      <ProductionStats />

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search work orders..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  {Object.values(WorkOrderStatus).map((status) => (
                    <SelectItem key={status} value={status}>
                      {status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={workCenterFilter} onValueChange={setWorkCenterFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Work Center" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All work centers</SelectItem>
                  {workCenters.map((wc) => (
                    <SelectItem key={wc} value={wc as string}>{wc}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex border rounded-md">
                <Button
                  variant={viewMode === 'list' ? 'default' : 'ghost'}
                  size="sm"
                  className="rounded-r-none"
                  onClick={() => setViewMode('list')}
                >
                  List
                </Button>
                <Button
                  variant={viewMode === 'cards' ? 'default' : 'ghost'}
                  size="sm"
                  className="rounded-l-none"
                  onClick={() => setViewMode('cards')}
                >
                  Cards
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Content */}
      {loading ? (
        <div className="text-center py-12 text-muted-foreground">Loading work orders...</div>
      ) : viewMode === 'list' ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="py-3 px-4 text-left font-medium">Work Order</th>
                    <th className="py-3 px-4 text-left font-medium">Product</th>
                    <th className="py-3 px-4 text-left font-medium">Status</th>
                    <th className="py-3 px-4 text-left font-medium">Priority</th>
                    <th className="py-3 px-4 text-left font-medium">Progress</th>
                    <th className="py-3 px-4 text-left font-medium">Work Center</th>
                    <th className="py-3 px-4 text-left font-medium">Assigned To</th>
                    <th className="py-3 px-4 text-left font-medium">Due Date</th>
                    <th className="py-3 px-4 w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredWorkOrders.map((wo) => (
                    <WorkOrderRow key={wo.id} workOrder={wo} />
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredWorkOrders.map((wo) => (
            <WorkOrderCard key={wo.id} workOrder={wo} />
          ))}
        </div>
      )}

      {!loading && filteredWorkOrders.length === 0 && (
        <div className="text-center py-12">
          <Factory className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-medium">No work orders found</h3>
          <p className="text-muted-foreground">
            {searchQuery || statusFilter !== 'all' || workCenterFilter !== 'all'
              ? 'Try adjusting your filters'
              : 'Create your first work order to get started'}
          </p>
        </div>
      )}
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
