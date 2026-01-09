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
}

// Mock data
const mockRFQs: RFQItem[] = [
  {
    id: '1',
    rfqNumber: 'RFQ-2024-0089',
    customerName: 'Global Manufacturing',
    customerId: 'c1',
    title: 'Custom precision parts - 500 units',
    description: 'High-precision machined parts for aerospace application',
    dueDate: new Date(Date.now() + 172800000).toISOString(),
    receivedDate: new Date(Date.now() - 86400000).toISOString(),
    estimatedValue: 45000,
    priority: 'high',
    status: 'new',
    tags: ['aerospace', 'precision'],
  },
  {
    id: '2',
    rfqNumber: 'RFQ-2024-0088',
    customerName: 'TechStart Inc',
    customerId: 'c2',
    title: 'Prototype assembly service',
    dueDate: new Date(Date.now() + 432000000).toISOString(),
    receivedDate: new Date(Date.now() - 172800000).toISOString(),
    estimatedValue: 12500,
    priority: 'medium',
    status: 'reviewing',
    assignee: { id: 'u1', name: 'John Smith' },
    tags: ['prototype'],
  },
  {
    id: '3',
    rfqNumber: 'RFQ-2024-0087',
    customerName: 'Acme Corp',
    customerId: 'c3',
    title: 'Annual maintenance contract renewal',
    dueDate: new Date(Date.now() + 86400000).toISOString(),
    receivedDate: new Date(Date.now() - 259200000).toISOString(),
    estimatedValue: 85000,
    priority: 'urgent',
    status: 'quoting',
    assignee: { id: 'u2', name: 'Jane Doe' },
    tags: ['contract', 'maintenance'],
  },
  {
    id: '4',
    rfqNumber: 'RFQ-2024-0086',
    customerName: 'BuildRight LLC',
    customerId: 'c4',
    title: 'Steel fabrication - 200 brackets',
    dueDate: new Date(Date.now() + 604800000).toISOString(),
    receivedDate: new Date(Date.now() - 345600000).toISOString(),
    estimatedValue: 18000,
    priority: 'low',
    status: 'reviewing',
    tags: ['fabrication'],
  },
  {
    id: '5',
    rfqNumber: 'RFQ-2024-0085',
    customerName: 'MegaParts International',
    customerId: 'c5',
    title: 'CNC machined components - annual supply',
    dueDate: new Date(Date.now() + 1209600000).toISOString(),
    receivedDate: new Date(Date.now() - 432000000).toISOString(),
    estimatedValue: 250000,
    priority: 'high',
    status: 'new',
    assignee: { id: 'u1', name: 'John Smith' },
    tags: ['cnc', 'annual'],
  },
  {
    id: '6',
    rfqNumber: 'RFQ-2024-0084',
    customerName: 'QuickFix Motors',
    customerId: 'c6',
    title: 'Automotive spare parts - batch order',
    dueDate: new Date(Date.now() - 86400000).toISOString(),
    receivedDate: new Date(Date.now() - 604800000).toISOString(),
    estimatedValue: 32000,
    priority: 'medium',
    status: 'submitted',
    assignee: { id: 'u2', name: 'Jane Doe' },
    tags: ['automotive'],
  },
];

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
  const isOverdue = new Date(rfq.dueDate) < new Date();

  return (
    <tr 
      className="border-b hover:bg-muted/50 cursor-pointer"
      onClick={() => router.push(`/pipeline/${rfq.id}`)}
    >
      <td className="py-3 px-4">
        <div>
          <p className="font-medium">{rfq.rfqNumber}</p>
          <p className="text-sm text-muted-foreground">{rfq.customerName}</p>
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
          {formatDate(new Date(rfq.dueDate))}
        </span>
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

function RFQKanbanCard({ rfq }: { rfq: RFQItem }) {
  const isOverdue = new Date(rfq.dueDate) < new Date();

  return (
    <Link href={`/pipeline/${rfq.id}`}>
      <Card className="mb-3 hover:shadow-md transition-shadow cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-start justify-between mb-2">
            <p className="font-medium text-sm">{rfq.rfqNumber}</p>
            <Badge variant={priorityConfig[rfq.priority].color as 'secondary' | 'warning' | 'danger' | 'destructive'} className="text-xs">
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
        </CardContent>
      </Card>
    </Link>
  );
}

function KanbanColumn({ title, status, rfqs }: { title: string; status: RFQStatus; rfqs: RFQItem[] }) {
  const statusItems = rfqs.filter((r) => r.status === status);
  const totalValue = statusItems.reduce((sum, r) => sum + (r.estimatedValue || 0), 0);

  return (
    <div className="flex-1 min-w-[280px] max-w-[350px]">
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

function PipelinePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [view, setView] = React.useState<'list' | 'kanban'>(
    (searchParams.get('view') as 'list' | 'kanban') || 'list'
  );
  const [search, setSearch] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [priorityFilter, setPriorityFilter] = React.useState<string>('all');
  const [isLoading] = React.useState(false); // Will be true when fetching from API

  // Filter RFQs
  const filteredRFQs = React.useMemo(() => {
    return mockRFQs.filter((rfq) => {
      const matchesSearch = !search ||
        rfq.rfqNumber.toLowerCase().includes(search.toLowerCase()) ||
        rfq.title.toLowerCase().includes(search.toLowerCase()) ||
        rfq.customerName.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === 'all' || rfq.status === statusFilter;
      const matchesPriority = priorityFilter === 'all' || rfq.priority === priorityFilter;
      return matchesSearch && matchesStatus && matchesPriority;
    });
  }, [search, statusFilter, priorityFilter]);

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Pipeline</h1>
          <p className="text-muted-foreground">
            Manage your RFQs and opportunities
          </p>
        </div>
        <Button asChild>
          <Link href="/pipeline/new">
            <Plus className="mr-2 h-4 w-4" />
            New RFQ
          </Link>
        </Button>
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
          Showing {filteredRFQs.length} of {mockRFQs.length} RFQs
        </p>
        <p>
          Total Value: {formatCurrency(filteredRFQs.reduce((sum, r) => sum + (r.estimatedValue || 0), 0))}
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
