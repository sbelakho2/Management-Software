'use client';

import * as React from 'react';
import { Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Plus,
  Search,
  Filter,
  LayoutGrid,
  List,
  ArrowUpDown,
  MoreHorizontal,
  Eye,
  Edit,
  Trash2,
  Archive,
  Copy,
  ChevronDown,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
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
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { cn, formatCurrency, formatRelativeTime, formatDate } from '@/lib/utils';
import type { RFQStatus, Priority, UserRole, RFQ } from '@/types';
import { usePipelineStore } from '@/stores/pipeline';
import { useAuthStore } from '@/stores';
import { hasPageAccess } from '@/lib/page-access';

// Use RFQ type directly from the types
type RFQItem = RFQ;


const statusConfig: Record<RFQStatus, { label: string; color: string }> = {
  new: { label: 'New', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' },
  reviewing: { label: 'Reviewing', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' },
  quoting: { label: 'Quoting', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300' },
  submitted: { label: 'Submitted', color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300' },
  won: { label: 'Won', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' },
  lost: { label: 'Lost', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' },
  no_bid: { label: 'No Bid', color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300' },
  cancelled: { label: 'Cancelled', color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300' },
};

const priorityConfig: Record<Priority, { label: string; color: string }> = {
  low: { label: 'Low', color: 'secondary' },
  medium: { label: 'Medium', color: 'warning' },
  high: { label: 'High', color: 'danger' },
  urgent: { label: 'Urgent', color: 'destructive' },
};

const kanbanColumns: { status: RFQStatus; title: string }[] = [
  { status: 'new', title: 'New' },
  { status: 'reviewing', title: 'Reviewing' },
  { status: 'quoting', title: 'Quoting' },
  { status: 'submitted', title: 'Submitted' },
];

// Components
function RFQListItem({ rfq }: { rfq: RFQItem }) {
  const router = useRouter();
  const isOverdue = new Date(rfq.due_date) < new Date();

  return (
    <tr 
      className="border-b hover:bg-muted/50 cursor-pointer"
      onClick={() => router.push(`/pipeline/${rfq.id}`)}
    >
      <td className="py-3 px-4">
        <div>
          <p className="font-medium">{rfq.rfq_number}</p>
          <p className="text-sm text-muted-foreground">{rfq.customer?.name || 'Unknown'}</p>
        </div>
      </td>
      <td className="py-3 px-4">
        <p className="max-w-xs truncate">{rfq.title}</p>
      </td>
      <td className="py-3 px-4">
        <Badge className={statusConfig[rfq.status].color}>
          {statusConfig[rfq.status].label}
        </Badge>
      </td>
      <td className="py-3 px-4">
        <Badge variant={priorityConfig[rfq.priority].color as 'secondary' | 'warning' | 'danger' | 'destructive'}>
          {priorityConfig[rfq.priority].label}
        </Badge>
      </td>
      <td className="py-3 px-4">
        <span className={cn(isOverdue && 'text-danger font-medium')}>
          {formatDate(new Date(rfq.due_date))}
        </span>
      </td>
      <td className="py-3 px-4">
        {rfq.estimated_value ? formatCurrency(rfq.estimated_value) : '-'}
      </td>
      <td className="py-3 px-4">
        {rfq.assigned_user ? (
          <div className="flex items-center gap-2">
            <Avatar
              fallback={rfq.assigned_user.full_name || rfq.assigned_user.email}
              src={rfq.assigned_user.avatar_url}
              size="xs"
            />
            <span className="text-sm">{rfq.assigned_user.full_name || rfq.assigned_user.email}</span>
          </div>
        ) : (
          <span className="text-muted-foreground">Unassigned</span>
        )}
      </td>
      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link href={`/pipeline/${rfq.id}`}>
                <Eye className="mr-2 h-4 w-4" />
                View
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href={`/pipeline/${rfq.id}?mode=edit`}>
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Copy className="mr-2 h-4 w-4" />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Archive className="mr-2 h-4 w-4" />
              Archive
            </DropdownMenuItem>
            <DropdownMenuItem className="text-danger">
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

function RFQKanbanCard({ rfq }: { rfq: RFQItem }) {
  const isOverdue = new Date(rfq.due_date) < new Date();

  return (
    <Link href={`/pipeline/${rfq.id}`} className="group">
      <Card className="mb-4 transition-all duration-500 hover:shadow-glow hover:-translate-y-1 group border-border/40 bg-card/60 backdrop-blur-sm rounded-[1.5rem]">
        <CardContent className="p-5 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-mono text-[10px] font-bold text-primary/60">{rfq.rfq_number}</p>
              <p className="font-heading font-bold text-sm tracking-tight group-hover:text-primary transition-colors mt-0.5">{rfq.customer?.name || 'Unknown Partner'}</p>
            </div>
            <Badge variant={priorityConfig[rfq.priority].color as any} className="text-[9px] font-bold uppercase tracking-widest rounded-md px-1.5 py-0">
              {priorityConfig[rfq.priority].label}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed font-medium">{rfq.title}</p>
          <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest pt-4 border-t border-border/10">
            <span className={cn(isOverdue ? 'text-danger' : 'text-muted-foreground/60')}>
              DUE {formatRelativeTime(new Date(rfq.due_date))}
            </span>
            {rfq.estimated_value && (
              <span className="text-foreground/80 font-heading">{formatCurrency(rfq.estimated_value)}</span>
            )}
          </div>
          {rfq.assigned_user && (
            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border/5">
              <Avatar fallback={rfq.assigned_user.full_name || rfq.assigned_user.email} size="xs" className="ring-2 ring-background" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{rfq.assigned_user.full_name || rfq.assigned_user.email}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

function KanbanColumn({ title, status, rfqs }: { title: string; status: RFQStatus; rfqs: RFQItem[] }) {
  const statusItems = rfqs.filter((r) => r.status === status);
  const totalValue = statusItems.reduce((sum, r) => sum + (r.estimated_value || 0), 0);

  return (
    <div className="flex-1 min-w-[300px] max-w-[380px]">
      <div className="flex items-center justify-between mb-6 px-2">
        <div className="flex items-center gap-3">
          <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">{title}</h3>
          <Badge variant="secondary" className="bg-primary/10 text-primary border-none text-[9px] font-bold rounded-full">
            {statusItems.length}
          </Badge>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
          {formatCurrency(totalValue)}
        </span>
      </div>
      <div className="bg-muted/10 rounded-[2.5rem] p-4 min-h-[600px] border border-border/5">
        {statusItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 border-2 border-dashed border-border/20 rounded-[2rem] text-muted-foreground/40 m-2">
            <p className="text-[10px] font-bold uppercase tracking-widest">Empty Stage</p>
          </div>
        ) : (
          statusItems.map((rfq) => (
            <RFQKanbanCard key={rfq.id} rfq={rfq} />
          ))
        )}
      </div>
    </div>
  );
}

function PipelinePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { rfqs, isLoading, fetchRFQs } = usePipelineStore();
  const { user } = useAuthStore();

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);
  
  const [view, setView] = React.useState<'list' | 'kanban'>(
    (searchParams.get('view') as 'list' | 'kanban') || 'list'
  );
  const [search, setSearch] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [priorityFilter, setPriorityFilter] = React.useState<string>('all');

  React.useEffect(() => {
    fetchRFQs();
  }, [fetchRFQs]);

  // Filter RFQs
  const filteredRFQs = React.useMemo(() => {
    return rfqs.filter((rfq) => {
      const matchesSearch = !search ||
        rfq.rfq_number.toLowerCase().includes(search.toLowerCase()) ||
        rfq.title.toLowerCase().includes(search.toLowerCase()) ||
        (rfq.customer?.name || '').toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === 'all' || rfq.status === statusFilter;
      const matchesPriority = priorityFilter === 'all' || rfq.priority === priorityFilter;
      return matchesSearch && matchesStatus && matchesPriority;
    });
  }, [rfqs, search, statusFilter, priorityFilter]);

  // Update URL when view changes
  React.useEffect(() => {
    const params = new URLSearchParams(searchParams);
    params.set('view', view);
    router.replace(`/pipeline?${params.toString()}`, { scroll: false });
  }, [view, searchParams, router]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="flex gap-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 w-32" />
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-8 page-fade-in" data-testid="pipeline-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Pipeline Velocity
          </h1>
          <p className="text-muted-foreground font-medium">
            Strategic RFQ management, opportunity tracking, and revenue forecasting
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasPageAccess('/pipeline/new', userRoles) && (
            <Button size="lg" className="rounded-xl shadow-glow subtle-shine" asChild>
              <Link href="/pipeline/new">
                <Plus className="mr-2 h-4 w-4" />
                New Opportunity
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* Filters & View Toggle */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search RFQs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            {Object.entries(statusConfig).map(([value, { label }]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={priorityFilter} onValueChange={setPriorityFilter}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Priority" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Priority</SelectItem>
            {Object.entries(priorityConfig).map(([value, { label }]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex border rounded-md">
          <Button
            variant={view === 'list' ? 'default' : 'ghost'}
            size="sm"
            className="rounded-r-none"
            onClick={() => setView('list')}
            aria-label="List view"
          >
            <List className="h-4 w-4" />
          </Button>
          <Button
            variant={view === 'kanban' ? 'default' : 'ghost'}
            size="sm"
            className="rounded-l-none"
            onClick={() => setView('kanban')}
            aria-label="Board view"
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      {view === 'list' ? (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left text-sm font-medium">RFQ</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Title</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Status</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Priority</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Due Date</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Value</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Assignee</th>
                  <th className="py-3 px-4 text-left text-sm font-medium w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filteredRFQs.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-muted-foreground">
                      No RFQs found
                    </td>
                  </tr>
                ) : (
                  filteredRFQs.map((rfq) => (
                    <RFQListItem key={rfq.id} rfq={rfq} />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <div className="flex gap-6 overflow-x-auto pb-4">
          {kanbanColumns.map((col) => (
            <KanbanColumn
              key={col.status}
              title={col.title}
              status={col.status}
              rfqs={filteredRFQs}
            />
          ))}
        </div>
      )}

      {/* Summary */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <p>
          Showing {filteredRFQs.length} of {rfqs.length} RFQs
        </p>
        <p>
          Total Value: {formatCurrency(filteredRFQs.reduce((sum, r) => sum + (r.estimated_value || 0), 0))}
        </p>
      </div>
    </div>
  );
}

export default function PipelinePage() {
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
      <PipelinePageContent />
    </Suspense>
  );
}
