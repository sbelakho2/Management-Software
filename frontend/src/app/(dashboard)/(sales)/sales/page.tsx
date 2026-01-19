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
import { AmbientStatus } from '@/components/ui/stat-card';
import { useI18n } from '@/contexts/i18n-context';

// Use RFQ type directly from the types
type RFQItem = RFQ;


const statusConfig: Record<RFQStatus, { labelKey: string; color: string }> = {
  new: { labelKey: 'pages.sales.status.new', color: 'bg-rams-steel/20 text-rams-steel border border-rams-steel/30' },
  reviewing: { labelKey: 'pages.sales.status.reviewing', color: 'bg-rams-orange/20 text-rams-orange border border-rams-orange/30' },
  quoting: { labelKey: 'pages.sales.status.quoting', color: 'bg-rams-muted/20 text-foreground/80 border border-rams-line' },
  submitted: { labelKey: 'pages.sales.status.submitted', color: 'bg-rams-steel/20 text-rams-steel border border-rams-steel/30' },
  won: { labelKey: 'pages.sales.status.won', color: 'bg-rams-green/20 text-rams-green border border-rams-green/30' },
  lost: { labelKey: 'pages.sales.status.lost', color: 'bg-rams-red/20 text-rams-red border border-rams-red/30' },
  no_bid: { labelKey: 'pages.sales.status.noBid', color: 'bg-rams-panel text-muted-foreground border border-rams-line' },
  cancelled: { labelKey: 'pages.sales.status.cancelled', color: 'bg-rams-panel text-muted-foreground border border-rams-line' },
};

const priorityConfig: Record<Priority, { labelKey: string; color: string }> = {
  low: { labelKey: 'pages.sales.priority.low', color: 'secondary' },
  medium: { labelKey: 'pages.sales.priority.medium', color: 'warning' },
  high: { labelKey: 'pages.sales.priority.high', color: 'danger' },
  urgent: { labelKey: 'pages.sales.priority.urgent', color: 'destructive' },
};

const kanbanColumns: { status: RFQStatus; titleKey: string }[] = [
  { status: 'new', titleKey: 'pages.sales.kanban.new' },
  { status: 'reviewing', titleKey: 'pages.sales.kanban.reviewing' },
  { status: 'quoting', titleKey: 'pages.sales.kanban.quoting' },
  { status: 'submitted', titleKey: 'pages.sales.kanban.submitted' },
];

// Components
function RFQListItem({ rfq }: { rfq: RFQItem }) {
  const router = useRouter();
  const { t } = useI18n();
  const isOverdue = new Date(rfq.due_date) < new Date();

  return (
    <tr 
      className="border-b hover:bg-muted/50 cursor-pointer"
      onClick={() => router.push(`/pipeline/${rfq.id}`)}
    >
      <td className="py-3 px-4">
        <div>
          <p className="font-medium">{rfq.rfq_number}</p>
          <p className="text-sm text-muted-foreground">{rfq.customer?.name || t('pages.sales.unknownPartner')}</p>
        </div>
      </td>
      <td className="py-3 px-4">
        <p className="max-w-xs truncate">{rfq.title}</p>
      </td>
      <td className="py-3 px-4">
        <Badge className={statusConfig[rfq.status].color}>
          {t(statusConfig[rfq.status].labelKey)}
        </Badge>
      </td>
      <td className="py-3 px-4">
        <Badge variant={priorityConfig[rfq.priority].color as 'secondary' | 'warning' | 'danger' | 'destructive'}>
          {t(priorityConfig[rfq.priority].labelKey)}
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
          <span className="text-muted-foreground">{t('pages.sales.unassigned')}</span>
        )}
      </td>
      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>'
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
                {t('common.view')}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href={`/pipeline/${rfq.id}?mode=edit`}>
                <Edit className="mr-2 h-4 w-4" />
                {t('common.edit')}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Copy className="mr-2 h-4 w-4" />
              {t('common.duplicate')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Archive className="mr-2 h-4 w-4" />
              {t('common.archive')}
            </DropdownMenuItem>
            <DropdownMenuItem className="text-danger">
              <Trash2 className="mr-2 h-4 w-4" />
              {t('common.delete')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

function RFQKanbanCard({ rfq }: { rfq: RFQItem }) {
  const { t } = useI18n();
  const isOverdue = new Date(rfq.due_date) < new Date();

  return (
    <Link href={`/pipeline/${rfq.id}`} className="group">
      <Card className="mb-4 group border-rams-line bg-rams-module hover:bg-rams-panel rounded-rams-sm">
        <CardContent className="p-5 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-mono text-[10px] font-bold text-rams-orange/60">{rfq.rfq_number}</p>
              <p className="font-sans font-black text-xs uppercase tracking-tight group-hover:text-rams-orange mt-0.5">{rfq.customer?.name || t('pages.sales.unknownPartner')}</p>
            </div>
            <Badge variant={priorityConfig[rfq.priority].color as any} className="text-[9px] font-black uppercase tracking-widest rounded-rams-sm px-1.5 py-0">
              {t(priorityConfig[rfq.priority].labelKey)}
            </Badge>
          </div>
          <p className="text-[10px] text-muted-foreground/60 line-clamp-2 leading-relaxed font-medium">{rfq.title}</p>
          <div className="flex items-center justify-between text-[9px] font-mono font-bold uppercase tracking-widest pt-4 border-t border-rams-line">
            <span className={cn(isOverdue ? 'text-rams-red' : 'text-muted-foreground/40')}>
              {t('pages.sales.due')} {formatRelativeTime(new Date(rfq.due_date))}
            </span>
            {rfq.estimated_value && (
              <span className="text-foreground/80 font-mono">{formatCurrency(rfq.estimated_value)}</span>
            )}
          </div>
          {rfq.assigned_user && (
            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-rams-line">
              <Avatar fallback={rfq.assigned_user.full_name || rfq.assigned_user.email} size="xs" className="border border-rams-line" />
              <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">{rfq.assigned_user.full_name || rfq.assigned_user.email}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

function KanbanColumn({ titleKey, status, rfqs }: { titleKey: string; status: RFQStatus; rfqs: RFQItem[] }) {
  const { t } = useI18n();
  const statusItems = rfqs.filter((r) => r.status === status);
  const totalValue = statusItems.reduce((sum, r) => sum + (r.estimated_value || 0), 0);

  return (
    <div className="flex-1 min-w-[300px] max-w-[380px]">
      <div className="flex items-center justify-between mb-6 px-2">
        <div className="flex items-center gap-3">
          <h3 className="text-[10px] font-mono font-black uppercase tracking-[0.2em] text-muted-foreground/60">{t(titleKey)}</h3>
          <Badge variant="secondary" className="bg-rams-orange/10 text-rams-orange border-none text-[9px] font-mono font-bold rounded-rams-sm">
            {statusItems.length}
          </Badge>
        </div>
        <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
          {formatCurrency(totalValue)}
        </span>
      </div>
      <div className="bg-rams-panel/30 rounded-rams-sm p-4 min-h-[600px] border border-rams-line">
        {statusItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 border border-dashed border-rams-line rounded-rams-sm text-muted-foreground/40 m-2">
            <p className="text-[9px] font-mono font-bold uppercase tracking-widest">{t('pages.sales.emptyStage')}</p>
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
  const { t } = useI18n();
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
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.sales.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.sales.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: SALES-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasPageAccess('/pipeline/new', userRoles) && (
            <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase" asChild>
              <Link href="/pipeline/new">
                <Plus className="mr-2 h-4 w-4" />
                {t('pages.sales.newOpportunity')}
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
            placeholder={t('pages.sales.searchPlaceholder')}
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
            <SelectItem value="all">{t('pages.sales.allStatus')}</SelectItem>
            {Object.entries(statusConfig).map(([value, { labelKey }]) => (
              <SelectItem key={value} value={value}>
                {t(labelKey)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={priorityFilter} onValueChange={setPriorityFilter}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Priority" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('pages.sales.allPriority')}</SelectItem>
            {Object.entries(priorityConfig).map(([value, { labelKey }]) => (
              <SelectItem key={value} value={value}>
                {t(labelKey)}
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
                  <th className="py-3 px-4 text-left text-sm font-medium">{t('pages.sales.table.rfq')}</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">{t('pages.sales.table.title')}</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">{t('pages.sales.table.status')}</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">{t('pages.sales.table.priority')}</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">{t('pages.sales.table.dueDate')}</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">{t('pages.sales.table.value')}</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">{t('pages.sales.table.assignee')}</th>
                  <th className="py-3 px-4 text-left text-sm font-medium w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filteredRFQs.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-muted-foreground">
                      {t('pages.sales.noRfqsFound')}
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
              titleKey={col.titleKey}
              status={col.status}
              rfqs={filteredRFQs}
            />
          ))}
        </div>
      )}

      {/* Summary */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <p>
          {t('pages.sales.showingCount', { filtered: filteredRFQs.length, total: rfqs.length })}
        </p>
        <p>
          {t('pages.sales.totalValue')}: {formatCurrency(filteredRFQs.reduce((sum, r) => sum + (r.estimated_value || 0), 0))}
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
