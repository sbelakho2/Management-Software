'use client';

import React, { useMemo, useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { 
  LayoutList, 
  LayoutGrid, 
  Search, 
  Plus, 
  Filter, 
  ArrowRight,
  Clock,
  AlertCircle,
  MoreVertical,
  Download
} from 'lucide-react';
import { usePipelineStore } from '@/stores/pipeline';
import { useKanbanStore } from '@/stores/kanban-store';
import { KanbanBoard } from '@/components/kanban/kanban-board';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { cn, formatCurrency, formatDate } from '@/lib/utils';
import type { RFQStatus, Priority } from '@/types';

const STAGES: Array<{ id: RFQStatus; label: string }> = [
  { id: 'new', label: 'New' },
  { id: 'reviewing', label: 'Reviewing' },
  { id: 'quoting', label: 'Quoting' },
  { id: 'submitted', label: 'Submitted' },
];

export default function PipelinePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  const { 
    rfqs, 
    stats, 
    isLoading, 
    fetchRFQs, 
    setRFQStatus, 
    deleteRFQ,
    exportRFQs 
  } = usePipelineStore();

  const initialView = (searchParams?.get('view') || 'list').toLowerCase();
  const [view, setView] = useState<'list' | 'board'>(initialView === 'board' ? 'board' : 'list');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');

  useEffect(() => {
    fetchRFQs();
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rfqs.filter((rfq) => {
      if (statusFilter !== 'all' && rfq.status !== statusFilter) return false;
      if (priorityFilter !== 'all' && rfq.priority !== priorityFilter) return false;
      if (!q) return true;
      return (
        rfq.rfq_number.toLowerCase().includes(q) ||
        rfq.customer?.name?.toLowerCase().includes(q) ||
        rfq.assigned_user?.full_name?.toLowerCase().includes(q) ||
        rfq.title?.toLowerCase().includes(q)
      );
    });
  }, [rfqs, search, statusFilter, priorityFilter]);

  const setAndPersistView = (nextView: 'list' | 'board') => {
    setView(nextView);
    const params = new URLSearchParams(searchParams?.toString() || '');
    params.set('view', nextView);
    router.replace(`?${params.toString()}`);
  };

  const clearFilters = () => {
    setSearch('');
    setStatusFilter('all');
    setPriorityFilter('all');
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'destructive';
      case 'high': return 'warning';
      case 'medium': return 'default';
      case 'low': return 'secondary';
      default: return 'secondary';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'new': return <Badge variant="secondary">New</Badge>;
      case 'reviewing': return <Badge variant="default">Reviewing</Badge>;
      case 'quoting': return <Badge variant="warning">Quoting</Badge>;
      case 'submitted': return <Badge variant="success">Submitted</Badge>;
      case 'won': return <Badge variant="success">Won</Badge>;
      case 'lost': return <Badge variant="destructive">Lost</Badge>;
      default: return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (isLoading && rfqs.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32" />)}
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4 lg:space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Sales Pipeline</h1>
          <p className="text-muted-foreground">Manage RFQs and track quoting progress</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => exportRFQs()} disabled={isLoading}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button asChild size="sm">
            <Link href="/rfqs/new">
              <Plus className="mr-2 h-4 w-4" />
              New RFQ
            </Link>
          </Button>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active RFQs</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.activeRFQs}</div>
            <p className="text-xs text-muted-foreground">{stats.overdueCount} overdue</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pipeline Value</CardTitle>
            <span className="text-muted-foreground text-xs">$</span>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(stats.totalValue)}</div>
            <p className="text-xs text-muted-foreground">Across {stats.totalRFQs} items</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Response</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avgResponseTime}h</div>
            <p className="text-xs text-muted-foreground">Target: &lt; 24h</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.conversionRate}%</div>
            <p className="text-xs text-muted-foreground">+2% from last month</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center space-x-2 max-w-md">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search RFQs, customers..."
              className="pl-8"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              {STAGES.map(s => <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Priorities</SelectItem>
              <SelectItem value="urgent">Urgent</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
          {(search || statusFilter !== 'all' || priorityFilter !== 'all') && (
            <Button variant="ghost" onClick={clearFilters} size="sm">
              Clear
            </Button>
          )}
        </div>
        <div className="flex items-center rounded-md border p-1 bg-muted/50">
          <Button
            variant={view === 'list' ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => setAndPersistView('list')}
          >
            <LayoutList className="h-4 w-4" />
          </Button>
          <Button
            variant={view === 'board' ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => setAndPersistView('board')}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {view === 'board' ? (
        <KanbanBoard 
          rfqs={filtered} 
          onCardClick={(rfq) => router.push(`/rfqs/${rfq.id}`)}
          onCardMove={async (cardId, fromStatus, toStatus) => {
            // Update pipeline store when move happens in Kanban
            await setRFQStatus(cardId, toStatus);
          }}
        />
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>RFQ #</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((rfq) => (
                <TableRow 
                  key={rfq.id} 
                  className="cursor-pointer" 
                  onClick={() => router.push(`/rfqs/${rfq.id}`)}
                >
                  <TableCell className="font-mono">{rfq.rfq_number}</TableCell>
                  <TableCell className="font-medium">{rfq.customer?.name || 'N/A'}</TableCell>
                  <TableCell>{getStatusBadge(rfq.status)}</TableCell>
                  <TableCell>
                    <Badge variant={getPriorityColor(rfq.priority) as any} className="capitalize">
                      {rfq.priority}
                    </Badge>
                  </TableCell>
                  <TableCell>{formatCurrency(rfq.estimated_value || 0)}</TableCell>
                  <TableCell className={cn(
                    new Date(rfq.due_date) < new Date() && rfq.status !== 'won' && rfq.status !== 'lost' && "text-destructive font-medium"
                  )}>
                    {formatDate(rfq.due_date)}
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => router.push(`/rfqs/${rfq.id}`)}>View Details</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => router.push(`/rfqs/${rfq.id}/edit`)}>Edit</DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="text-destructive" onClick={() => deleteRFQ(rfq.id)}>Delete</DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center">
                    No results found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
