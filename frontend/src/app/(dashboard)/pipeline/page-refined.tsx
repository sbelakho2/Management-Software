'use client';

import * as React from 'react';
import { Suspense, useState, useEffect, useCallback } from 'react';
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
  Download,
  Upload,
  CheckSquare,
  X,
  Calendar,
  DollarSign,
  TrendingUp,
  AlertCircle,
  Clock,
  Users,
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
  DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu';
import { Avatar } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn, formatCurrency, formatRelativeTime, formatDate } from '@/lib/utils';
import { usePipelineStore } from '@/stores/pipeline';
import type { RFQStatus, Priority } from '@/types';

// Types
interface RFQItem {
  id: string;
  rfqNumber: string;
  customerName: string;
  customerId: string;
  title: string;
  description?: string;
  dueDate: string;
  receivedDate: string;
  estimatedValue?: number;
  priority: Priority;
  status: RFQStatus;
  assignee?: {
    id: string;
    name: string;
    avatar?: string;
  };
  tags: string[];
  version: number; // For optimistic locking
  attachmentCount: number;
  commentCount: number;
  lastActivityAt: string;
}

interface PipelineStats {
  totalRFQs: number;
  activeRFQs: number;
  totalValue: number;
  avgResponseTime: number; // hours
  conversionRate: number; // percentage
  overdueCount: number;
}

// Status & Priority Configuration
const statusConfig: Record<RFQStatus, { label: string; color: string; icon: React.ReactNode }> = {
  new: {
    label: 'New',
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    icon: <AlertCircle className="h-3 w-3" />,
  },
  reviewing: {
    label: 'Reviewing',
    color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
    icon: <Clock className="h-3 w-3" />,
  },
  quoting: {
    label: 'Quoting',
    color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
    icon: <DollarSign className="h-3 w-3" />,
  },
  submitted: {
    label: 'Submitted',
    color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300',
    icon: <Upload className="h-3 w-3" />,
  },
  won: {
    label: 'Won',
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    icon: <TrendingUp className="h-3 w-3" />,
  },
  lost: {
    label: 'Lost',
    color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
    icon: <X className="h-3 w-3" />,
  },
  no_bid: {
    label: 'No Bid',
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
    icon: <X className="h-3 w-3" />,
  },
  cancelled: {
    label: 'Cancelled',
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
    icon: <X className="h-3 w-3" />,
  },
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

// Analytics Dashboard Component
function PipelineAnalytics({ stats }: { stats: PipelineStats }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4" data-testid="pipeline-analytics">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total RFQs</CardTitle>
          <LayoutGrid className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.totalRFQs}</div>
          <p className="text-xs text-muted-foreground">
            {stats.activeRFQs} active
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Value</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatCurrency(stats.totalValue)}</div>
          <p className="text-xs text-muted-foreground">
            Est. pipeline value
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.avgResponseTime}h</div>
          <p className="text-xs text-muted-foreground">
            Time to first response
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Conversion Rate</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.conversionRate}%</div>
          <p className="text-xs text-muted-foreground">
            {stats.overdueCount} overdue
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// RFQ List Item Component
function RFQListItem({
  rfq,
  isSelected,
  onSelect,
}: {
  rfq: RFQItem;
  isSelected: boolean;
  onSelect: (id: string) => void;
}) {
  const router = useRouter();
  const isOverdue = new Date(rfq.dueDate) < new Date();

  const handleRowClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('[data-no-propagate]')) {
      return;
    }
    router.push(`/pipeline/${rfq.id}`);
  };

  return (
    <tr 
      className="border-b hover:bg-muted/50 cursor-pointer"
      onClick={handleRowClick}
      data-testid="rfq-row"
    >
      <td className="py-3 px-4" data-no-propagate>
        <Checkbox
          checked={isSelected}
          onCheckedChange={() => onSelect(rfq.id)}
        />
      </td>
      <td className="py-3 px-4">
        <div>
          <p className="font-medium" data-testid="rfq-number">{rfq.rfqNumber}</p>
          <p className="text-sm text-muted-foreground">{rfq.customerName}</p>
        </div>
      </td>
      <td className="py-3 px-4">
        <div>
          <p className="max-w-xs truncate">{rfq.title}</p>
          {(rfq.attachmentCount > 0 || rfq.commentCount > 0) && (
            <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
              {rfq.attachmentCount > 0 && <span>📎 {rfq.attachmentCount}</span>}
              {rfq.commentCount > 0 && <span>💬 {rfq.commentCount}</span>}
            </div>
          )}
        </div>
      </td>
      <td className="py-3 px-4">
        <Badge className={statusConfig[rfq.status].color}>
          <span className="flex items-center gap-1">
            {statusConfig[rfq.status].icon}
            {statusConfig[rfq.status].label}
          </span>
        </Badge>
      </td>
      <td className="py-3 px-4">
        <Badge variant={priorityConfig[rfq.priority].color as any}>
          {priorityConfig[rfq.priority].label}
        </Badge>
      </td>
      <td className="py-3 px-4">
        <div>
          <span className={cn(isOverdue && 'text-danger font-medium')}>
            {formatDate(new Date(rfq.dueDate))}
          </span>
          {isOverdue && (
            <p className="text-xs text-danger">Overdue</p>
          )}
        </div>
      </td>
      <td className="py-3 px-4">
        {rfq.estimatedValue ? formatCurrency(rfq.estimatedValue) : '-'}
      </td>
      <td className="py-3 px-4">
        {rfq.assignee ? (
          <div className="flex items-center gap-2">
            <Avatar
              fallback={rfq.assignee.name}
              src={rfq.assignee.avatar}
              size="xs"
            />
            <span className="text-sm">{rfq.assignee.name}</span>
          </div>
        ) : (
          <span className="text-muted-foreground">Unassigned</span>
        )}
      </td>
      <td className="py-3 px-4">
        <span className="text-xs text-muted-foreground">
          {formatRelativeTime(new Date(rfq.lastActivityAt))}
        </span>
      </td>
      <td className="py-3 px-4" data-no-propagate>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" data-testid="rfq-actions">
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
              <Link href={`/pipeline/${rfq.id}/edit`}>
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

// Kanban Card Component
function RFQKanbanCard({ rfq }: { rfq: RFQItem }) {
  const isOverdue = new Date(rfq.dueDate) < new Date();

  return (
    <Link href={`/pipeline/${rfq.id}`}>
      <Card className="mb-3 hover:shadow-md transition-shadow cursor-pointer" data-testid="kanban-card">
        <CardContent className="p-4">
          <div className="flex items-start justify-between mb-2">
            <p className="font-medium text-sm">{rfq.rfqNumber}</p>
            <Badge variant={priorityConfig[rfq.priority].color as any} className="text-xs">
              {priorityConfig[rfq.priority].label}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mb-1">{rfq.customerName}</p>
          <p className="text-sm mb-3 line-clamp-2">{rfq.title}</p>
          <div className="flex items-center justify-between text-xs">
            <span className={cn(isOverdue ? 'text-danger' : 'text-muted-foreground')}>
              Due {formatRelativeTime(new Date(rfq.dueDate))}
            </span>
            {rfq.estimatedValue && (
              <span className="font-medium">{formatCurrency(rfq.estimatedValue)}</span>
            )}
          </div>
          {rfq.assignee && (
            <div className="flex items-center gap-2 mt-3 pt-3 border-t">
              <Avatar fallback={rfq.assignee.name} size="xs" />
              <span className="text-xs text-muted-foreground">{rfq.assignee.name}</span>
            </div>
          )}
          {rfq.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {rfq.tags.slice(0, 3).map((tag) => (
                <span key={tag} className="px-1.5 py-0.5 bg-muted text-muted-foreground text-xs rounded">
                  {tag}
                </span>
              ))}
            </div>
          )}
          {(rfq.attachmentCount > 0 || rfq.commentCount > 0) && (
            <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
              {rfq.attachmentCount > 0 && <span>📎 {rfq.attachmentCount}</span>}
              {rfq.commentCount > 0 && <span>💬 {rfq.commentCount}</span>}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

// Kanban Column Component
function KanbanColumn({ title, status, rfqs }: { title: string; status: RFQStatus; rfqs: RFQItem[] }) {
  const statusItems = rfqs.filter((r) => r.status === status);
  const totalValue = statusItems.reduce((sum, r) => sum + (r.estimatedValue || 0), 0);

  return (
    <div className="flex-1 min-w-[280px] max-w-[350px]" data-testid="kanban-column">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold">{title}</h3>
          <Badge variant="secondary" className="rounded-full">
            {statusItems.length}
          </Badge>
        </div>
        <span className="text-sm text-muted-foreground">
          {formatCurrency(totalValue)}
        </span>
      </div>
      <div className="bg-muted/50 rounded-lg p-3 min-h-[400px]">
        {statusItems.length === 0 ? (
          <p className="text-center text-sm text-muted-foreground py-8">
            No RFQs
          </p>
        ) : (
          statusItems.map((rfq) => (
            <RFQKanbanCard key={rfq.id} rfq={rfq} />
          ))
        )}
      </div>
    </div>
  );
}

// Bulk Actions Toolbar
function BulkActionsToolbar({
  selectedCount,
  onClearSelection,
  onBulkAction,
}: {
  selectedCount: number;
  onClearSelection: () => void;
  onBulkAction: (action: string) => void;
}) {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
      <Card className="shadow-lg border-2">
        <CardContent className="flex items-center gap-4 p-4">
          <div className="flex items-center gap-2">
            <CheckSquare className="h-5 w-5" />
            <span className="font-medium">{selectedCount} selected</span>
          </div>
          <div className="h-6 w-px bg-border" />
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => onBulkAction('assign')}>
              <Users className="mr-2 h-4 w-4" />
              Assign
            </Button>
            <Button size="sm" variant="outline" onClick={() => onBulkAction('archive')}>
              <Archive className="mr-2 h-4 w-4" />
              Archive
            </Button>
            <Button size="sm" variant="outline" onClick={() => onBulkAction('export')}>
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
            <Button size="sm" variant="destructive" onClick={() => onBulkAction('delete')}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
          <div className="h-6 w-px bg-border" />
          <Button size="sm" variant="ghost" onClick={onClearSelection}>
            <X className="h-4 w-4" />
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// Main Pipeline Page Component
function PipelinePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { rfqs, stats, isLoading, fetchRFQs, exportRFQs } = usePipelineStore();

  const [view, setView] = useState<'list' | 'kanban'>(
    (searchParams.get('view') as 'list' | 'kanban') || 'list'
  );
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [selectedRFQs, setSelectedRFQs] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<string>('dueDate');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Fetch RFQs on mount
  useEffect(() => {
    fetchRFQs();
  }, [fetchRFQs]);

  // Filter RFQs
  const filteredRFQs = React.useMemo(() => {
    let filtered = rfqs.filter((rfq) => {
      const matchesSearch = !search ||
        rfq.rfqNumber.toLowerCase().includes(search.toLowerCase()) ||
        rfq.title.toLowerCase().includes(search.toLowerCase()) ||
        rfq.customerName.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === 'all' || rfq.status === statusFilter;
      const matchesPriority = priorityFilter === 'all' || rfq.priority === priorityFilter;
      return matchesSearch && matchesStatus && matchesPriority;
    });

    // Sort
    filtered.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'dueDate':
          comparison = new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime();
          break;
        case 'value':
          comparison = (a.estimatedValue || 0) - (b.estimatedValue || 0);
          break;
        case 'priority':
          const priorityOrder = { urgent: 4, high: 3, medium: 2, low: 1 };
          comparison = priorityOrder[a.priority] - priorityOrder[b.priority];
          break;
        case 'receivedDate':
          comparison = new Date(a.receivedDate).getTime() - new Date(b.receivedDate).getTime();
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [rfqs, search, statusFilter, priorityFilter, sortBy, sortOrder]);

  // Selection handlers
  const handleSelectAll = useCallback(() => {
    if (selectedRFQs.size === filteredRFQs.length) {
      setSelectedRFQs(new Set());
    } else {
      setSelectedRFQs(new Set(filteredRFQs.map(rfq => rfq.id)));
    }
  }, [filteredRFQs, selectedRFQs.size]);

  const handleSelectRFQ = useCallback((id: string) => {
    setSelectedRFQs(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleBulkAction = useCallback(async (action: string) => {
    console.log(`Bulk action: ${action}`, Array.from(selectedRFQs));
    // Implement bulk actions
    if (action === 'export') {
      await exportRFQs(Array.from(selectedRFQs));
    }
    setSelectedRFQs(new Set());
  }, [selectedRFQs, exportRFQs]);

  // Update URL when view changes
  useEffect(() => {
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
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="pipeline-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Pipeline</h1>
          <p className="text-muted-foreground">
            Manage your RFQs and opportunities
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => exportRFQs()}>
            <Download className="h-4 w-4" />
          </Button>
          <Button asChild data-testid="new-rfq-button">
            <Link href="/pipeline/new">
              <Plus className="mr-2 h-4 w-4" />
              New RFQ
            </Link>
          </Button>
        </div>
      </div>

      {/* Analytics */}
      <PipelineAnalytics stats={stats} />

      {/* Filters & View Toggle */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search RFQs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="search-input"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px]">
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
          <SelectTrigger className="w-[160px]">
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
        <Select value={sortBy} onValueChange={setSortBy}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="dueDate">Due Date</SelectItem>
            <SelectItem value="receivedDate">Received Date</SelectItem>
            <SelectItem value="value">Value</SelectItem>
            <SelectItem value="priority">Priority</SelectItem>
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="icon"
          onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
        >
          <ArrowUpDown className="h-4 w-4" />
        </Button>
        <div className="flex border rounded-md">
          <Button
            variant={view === 'list' ? 'default' : 'ghost'}
            size="sm"
            className="rounded-r-none"
            onClick={() => setView('list')}
            data-testid="view-list"
          >
            <List className="h-4 w-4" />
          </Button>
          <Button
            variant={view === 'kanban' ? 'default' : 'ghost'}
            size="sm"
            className="rounded-l-none"
            onClick={() => setView('kanban')}
            data-testid="view-kanban"
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      {view === 'list' ? (
        <Card>
          <div className="overflow-x-auto" data-testid="rfq-table">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left">
                    <Checkbox
                      checked={selectedRFQs.size === filteredRFQs.length && filteredRFQs.length > 0}
                      onCheckedChange={handleSelectAll}
                    />
                  </th>
                  <th className="py-3 px-4 text-left text-sm font-medium">RFQ</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Title</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Status</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Priority</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Due Date</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Value</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Assignee</th>
                  <th className="py-3 px-4 text-left text-sm font-medium">Activity</th>
                  <th className="py-3 px-4 text-left text-sm font-medium w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filteredRFQs.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="py-12 text-center text-muted-foreground">
                      No RFQs found
                    </td>
                  </tr>
                ) : (
                  filteredRFQs.map((rfq) => (
                    <RFQListItem
                      key={rfq.id}
                      rfq={rfq}
                      isSelected={selectedRFQs.has(rfq.id)}
                      onSelect={handleSelectRFQ}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <div className="flex gap-6 overflow-x-auto pb-4" data-testid="kanban-board">
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
      <div className="flex items-center justify-between text-sm text-muted-foreground" data-testid="pipeline-summary">
        <p>
          Showing {filteredRFQs.length} of {rfqs.length} RFQs
        </p>
        <p>
          Total Value: {formatCurrency(filteredRFQs.reduce((sum, r) => sum + (r.estimatedValue || 0), 0))}
        </p>
      </div>

      {/* Bulk Actions Toolbar */}
      <BulkActionsToolbar
        selectedCount={selectedRFQs.size}
        onClearSelection={() => setSelectedRFQs(new Set())}
        onBulkAction={handleBulkAction}
      />
    </div>
  );
}

// Main Page Export
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
