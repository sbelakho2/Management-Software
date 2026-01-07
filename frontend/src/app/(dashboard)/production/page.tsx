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

interface WorkOrder {
  id: string;
  woNumber: string;
  productName: string;
  partNumber: string;
  quantity: number;
  completedQty: number;
  status: 'planned' | 'released' | 'in_progress' | 'on_hold' | 'completed' | 'cancelled';
  priority: 'high' | 'normal' | 'low';
  workCenter: string;
  assignedTo?: string;
  startDate: string;
  dueDate: string;
  quoteNumber?: string;
}

const mockWorkOrders: WorkOrder[] = [
  {
    id: '1',
    woNumber: 'WO-2024-0089',
    productName: 'Precision Bracket Type A',
    partNumber: 'AER-001',
    quantity: 200,
    completedQty: 150,
    status: 'in_progress',
    priority: 'high',
    workCenter: 'CNC Machining',
    assignedTo: 'John Doe',
    startDate: '2024-01-08',
    dueDate: '2024-01-20',
    quoteNumber: 'Q-2024-0112',
  },
  {
    id: '2',
    woNumber: 'WO-2024-0088',
    productName: 'Mounting Plate Assembly',
    partNumber: 'MNT-100',
    quantity: 100,
    completedQty: 0,
    status: 'released',
    priority: 'normal',
    workCenter: 'Fabrication',
    startDate: '2024-01-15',
    dueDate: '2024-01-25',
  },
  {
    id: '3',
    woNumber: 'WO-2024-0087',
    productName: 'Structural Fastener Kit',
    partNumber: 'FST-200',
    quantity: 500,
    completedQty: 500,
    status: 'completed',
    priority: 'normal',
    workCenter: 'Assembly',
    assignedTo: 'Maria Garcia',
    startDate: '2024-01-05',
    dueDate: '2024-01-12',
  },
  {
    id: '4',
    woNumber: 'WO-2024-0086',
    productName: 'Hydraulic Fitting - 1/2"',
    partNumber: 'HYD-050',
    quantity: 300,
    completedQty: 100,
    status: 'on_hold',
    priority: 'high',
    workCenter: 'CNC Machining',
    assignedTo: 'Sarah Chen',
    startDate: '2024-01-03',
    dueDate: '2024-01-15',
  },
  {
    id: '5',
    woNumber: 'WO-2024-0085',
    productName: 'Precision Bracket Type B',
    partNumber: 'AER-002',
    quantity: 150,
    completedQty: 0,
    status: 'planned',
    priority: 'low',
    workCenter: 'CNC Machining',
    startDate: '2024-01-20',
    dueDate: '2024-02-01',
    quoteNumber: 'Q-2024-0111',
  },
];

const statusConfig = {
  planned: { label: 'Planned', variant: 'secondary' as const, icon: Calendar },
  released: { label: 'Released', variant: 'default' as const, icon: Package },
  in_progress: { label: 'In Progress', variant: 'warning' as const, icon: Play },
  on_hold: { label: 'On Hold', variant: 'danger' as const, icon: Pause },
  completed: { label: 'Completed', variant: 'success' as const, icon: CheckCircle },
  cancelled: { label: 'Cancelled', variant: 'outline' as const, icon: AlertTriangle },
};

const priorityConfig = {
  high: { label: 'High', variant: 'danger' as const },
  normal: { label: 'Normal', variant: 'secondary' as const },
  low: { label: 'Low', variant: 'outline' as const },
};

function ProductionStats({ workOrders }: { workOrders: WorkOrder[] }) {
  const stats = React.useMemo(() => {
    const inProgress = workOrders.filter((wo) => wo.status === 'in_progress').length;
    const onHold = workOrders.filter((wo) => wo.status === 'on_hold').length;
    const dueSoon = workOrders.filter((wo) => {
      const due = new Date(wo.dueDate);
      const today = new Date();
      const daysUntilDue = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
      return daysUntilDue <= 7 && daysUntilDue >= 0 && !['completed', 'cancelled'].includes(wo.status);
    }).length;
    const totalQty = workOrders.filter((wo) => !['cancelled'].includes(wo.status))
      .reduce((sum, wo) => sum + wo.quantity, 0);
    const completedQty = workOrders.filter((wo) => !['cancelled'].includes(wo.status))
      .reduce((sum, wo) => sum + wo.completedQty, 0);
    const onTimeRate = 85; // Mock
    return { inProgress, onHold, dueSoon, totalQty, completedQty, onTimeRate };
  }, [workOrders]);

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/10">
              <Play className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.inProgress}</p>
              <p className="text-sm text-muted-foreground">In Progress</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-lg', stats.onHold > 0 ? 'bg-danger/10' : 'bg-muted')}>
              <Pause className={cn('h-5 w-5', stats.onHold > 0 ? 'text-danger' : 'text-muted-foreground')} />
            </div>
            <div>
              <p className={cn('text-2xl font-bold', stats.onHold > 0 && 'text-danger')}>
                {stats.onHold}
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
              <p className="text-2xl font-bold">{stats.dueSoon}</p>
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
              <p className="text-2xl font-bold">{stats.onTimeRate}%</p>
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

function WorkOrderRow({ workOrder }: { workOrder: WorkOrder }) {
  const router = useRouter();
  const config = statusConfig[workOrder.status];
  const priorityCfg = priorityConfig[workOrder.priority];
  const StatusIcon = config.icon;
  const progress = (workOrder.completedQty / workOrder.quantity) * 100;
  const dueDate = new Date(workOrder.dueDate);
  const today = new Date();
  const isOverdue = dueDate < today && workOrder.status !== 'completed';

  return (
    <tr 
      className="border-b hover:bg-muted/50 cursor-pointer transition-colors"
      onClick={() => router.push(`/production/${workOrder.id}`)}
    >
      <td className="py-3 px-4">
        <div>
          <p className="font-medium">{workOrder.woNumber}</p>
          {workOrder.quoteNumber && (
            <p className="text-sm text-muted-foreground">{workOrder.quoteNumber}</p>
          )}
        </div>
      </td>
      <td className="py-3 px-4">
        <div>
          <p>{workOrder.productName}</p>
          <p className="text-sm text-muted-foreground font-mono">{workOrder.partNumber}</p>
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
            <span>{workOrder.completedQty}</span>
            <span>/ {workOrder.quantity}</span>
          </div>
          <ProgressBar value={workOrder.completedQty} max={workOrder.quantity} />
        </div>
      </td>
      <td className="py-3 px-4 text-muted-foreground">{workOrder.workCenter}</td>
      <td className="py-3 px-4">
        {workOrder.assignedTo ? (
          <div className="flex items-center gap-2">
            <Avatar size="sm">
              <AvatarFallback>{getInitials(workOrder.assignedTo)}</AvatarFallback>
            </Avatar>
            <span className="text-sm">{workOrder.assignedTo}</span>
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
            <Button variant="ghost" size="icon-sm">
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
            <DropdownMenuSeparator />
            {workOrder.status === 'planned' && (
              <DropdownMenuItem>
                <Package className="mr-2 h-4 w-4" />
                Release
              </DropdownMenuItem>
            )}
            {workOrder.status === 'released' && (
              <DropdownMenuItem>
                <Play className="mr-2 h-4 w-4" />
                Start
              </DropdownMenuItem>
            )}
            {workOrder.status === 'in_progress' && (
              <>
                <DropdownMenuItem>
                  <Pause className="mr-2 h-4 w-4" />
                  Put On Hold
                </DropdownMenuItem>
                <DropdownMenuItem className="text-success">
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Complete
                </DropdownMenuItem>
              </>
            )}
            {workOrder.status === 'on_hold' && (
              <DropdownMenuItem>
                <Play className="mr-2 h-4 w-4" />
                Resume
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

function WorkOrderCard({ workOrder }: { workOrder: WorkOrder }) {
  const router = useRouter();
  const config = statusConfig[workOrder.status];
  const priorityCfg = priorityConfig[workOrder.priority];
  const StatusIcon = config.icon;
  const progress = (workOrder.completedQty / workOrder.quantity) * 100;
  const dueDate = new Date(workOrder.dueDate);
  const today = new Date();
  const isOverdue = dueDate < today && workOrder.status !== 'completed';

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
            <p className="font-medium">{workOrder.woNumber}</p>
            <p className="text-sm text-muted-foreground">{workOrder.productName}</p>
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
            <span>{workOrder.completedQty} / {workOrder.quantity}</span>
          </div>
          <ProgressBar value={workOrder.completedQty} max={workOrder.quantity} />
        </div>

        <div className="flex items-center justify-between text-sm pt-3 border-t">
          <div className="flex items-center gap-1 text-muted-foreground">
            <Factory className="h-4 w-4" />
            {workOrder.workCenter}
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
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [workCenterFilter, setWorkCenterFilter] = React.useState<string>('all');
  const [viewMode, setViewMode] = React.useState<'list' | 'cards'>(
    (searchParams.get('view') as 'list' | 'cards') || 'list'
  );

  const workCenters = React.useMemo(() => {
    return [...new Set(mockWorkOrders.map((wo) => wo.workCenter))];
  }, []);

  const filteredWorkOrders = React.useMemo(() => {
    return mockWorkOrders.filter((wo) => {
      const matchesSearch = searchQuery === '' ||
        wo.woNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        wo.productName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        wo.partNumber.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'all' || wo.status === statusFilter;
      const matchesWorkCenter = workCenterFilter === 'all' || wo.workCenter === workCenterFilter;
      return matchesSearch && matchesStatus && matchesWorkCenter;
    });
  }, [searchQuery, statusFilter, workCenterFilter]);

  return (
    <div className="space-y-6">
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
      <ProductionStats workOrders={mockWorkOrders} />

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
                  <SelectItem value="planned">Planned</SelectItem>
                  <SelectItem value="released">Released</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="on_hold">On Hold</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                </SelectContent>
              </Select>
              <Select value={workCenterFilter} onValueChange={setWorkCenterFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Work Center" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All work centers</SelectItem>
                  {workCenters.map((wc) => (
                    <SelectItem key={wc} value={wc}>{wc}</SelectItem>
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
      {viewMode === 'list' ? (
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

      {filteredWorkOrders.length === 0 && (
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
