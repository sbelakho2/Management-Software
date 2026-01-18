'use client';

import * as React from 'react';
import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useI18n } from '@/contexts/i18n-context';
import {
  Plus,
  Search,
  Filter,
  Download,
  FileText,
  CheckCircle,
  Clock,
  AlertTriangle,
  TrendingUp,
  Users,
  Target,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { useA3Store } from '@/stores/a3';
import { useAuthStore } from '@/stores';
import { hasPageAccess } from '@/lib/page-access';
import { UserRole } from '@/types';

type A3Type = 'problem_solving' | 'proposal' | 'status_report' | 'strategy';
type A3Status = 'draft' | 'in_progress' | 'review' | 'approved' | 'implemented' | 'closed' | 'cancelled';
type A3Priority = 'critical' | 'high' | 'medium' | 'low';

interface A3 {
  id: string;
  a3_number: string;
  title: string;
  a3_type: A3Type;
  status: A3Status;
  author_name: string;
  sponsor_name?: string;
  coach_name?: string;
  target_completion_date?: string;
  progress_percentage: number;
  priority: A3Priority;
  department?: string;
  tags?: string[];
  created_at: string;
  updated_at: string;
}

interface A3Stats {
  total: number;
  by_status: Record<A3Status, number>;
  overdue_count: number;
  approval_pending: number;
}

const statusBadgeVariant: Record<A3Status, 'default' | 'secondary' | 'warning' | 'destructive' | 'success' | 'outline'> = {
  draft: 'secondary',
  in_progress: 'default',
  review: 'warning',
  approved: 'success',
  implemented: 'success',
  closed: 'outline',
  cancelled: 'destructive',
};

const priorityBadgeVariant: Record<A3Priority, 'default' | 'secondary' | 'warning' | 'danger'> = {
  low: 'secondary',
  medium: 'default',
  high: 'warning',
  critical: 'danger',
};

const typeConfig: Record<A3Type, { label: string; color: string }> = {
  problem_solving: { label: 'Problem Solving', color: 'bg-rams-steel/10 text-rams-steel border-rams-steel/20' },
  proposal: { label: 'Proposal', color: 'bg-rams-green/10 text-rams-green border-rams-green/20' },
  status_report: { label: 'Status Report', color: 'bg-rams-panel text-muted-foreground border-rams-border' },
  strategy: { label: 'Strategy', color: 'bg-rams-orange/10 text-rams-orange border-rams-orange/20' },
};

export default function A3Page() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const { user } = useAuthStore();
  
  const { 
    a3s, 
    stats, 
    isLoading, 
    fetchA3s, 
    deleteA3 
  } = useA3Store();

  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');

  useEffect(() => {
    fetchA3s();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await deleteA3(id);
      toast({
        title: 'Success',
        description: 'A3 report deleted successfully',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete A3 report',
        variant: 'destructive',
      });
    }
  };

  const filteredA3s = a3s.filter(a3 => {
    const matchesSearch = 
      a3.a3_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a3.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a3.author_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a3.department?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesType = typeFilter === 'all' || a3.a3_type === typeFilter;
    const matchesStatus = statusFilter === 'all' || a3.status === statusFilter;
    const matchesPriority = priorityFilter === 'all' || a3.priority === priorityFilter;

    return matchesSearch && matchesType && matchesStatus && matchesPriority;
  });

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const isOverdue = (a3: A3): boolean => {
    if (!a3.target_completion_date) return false;
    if (['closed', 'cancelled'].includes(a3.status)) return false;
    return new Date(a3.target_completion_date) < new Date();
  };

  const userRoles = useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="a3-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.a3.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.a3.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: PROBLEM-SOLVING-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-border">
            <Download className="h-3.5 w-3.5 mr-2" />
            Export Intel
          </Button>
          {hasPageAccess('/a3/new', userRoles) && (
            <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]" onClick={() => router.push('/a3/new')}>
              <Plus className="mr-2 h-3.5 w-3.5" />
              Initialize Resolution
            </Button>
          )}
        </div>
      </div>

      {/* Stats Grid (Industrial Modules) */}
      <div className="grid gap-0 md:grid-cols-4 border border-rams-border bg-rams-border">
        <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Total A3 Nodes</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats?.total || 0}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">Aggregated Registry</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Execution Pulse</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{stats?.by_status?.in_progress || 0}</div>
          <p className="text-[9px] font-mono font-bold text-rams-orange uppercase tracking-widest mt-2">ACTIVE_PROTOCOLS</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Pending Approvals</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-steel tabular-nums">{stats?.approval_pending || 0}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">QUEUE_GATES</p>
        </div>
        <div className="bg-rams-module p-6 border-b md:border-b-0 border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-red/60 mb-4">Horizon Overdue</p>
          <div className={cn("text-3xl font-mono font-bold tracking-tight tabular-nums", (stats?.overdue_count || 0) > 0 ? "text-rams-red" : "text-foreground/90")}>
            {stats?.overdue_count || 0}
          </div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">THRESHOLD_EXCEPTIONS</p>
        </div>
      </div>

      {/* Filters & Content */}
      <div className="space-y-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-1 items-center gap-4 max-w-4xl">
            <div className="relative flex-1 min-w-[240px] group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 transition-colors group-focus-within:text-rams-orange" />
              <Input
                placeholder="SEARCH_RESOLUTION_NODES..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 h-10 text-[10px]"
              />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[160px] h-10 text-[10px]">
                <Filter className="mr-2 h-3.5 w-3.5 opacity-40" />
                <SelectValue placeholder="TYPE_NODE" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">ALL_TYPES</SelectItem>
                <SelectItem value="problem_solving">PROBLEM_SOLVING</SelectItem>
                <SelectItem value="proposal">PROPOSAL</SelectItem>
                <SelectItem value="status_report">STATUS_REPORT</SelectItem>
                <SelectItem value="strategy">STRATEGY</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[160px] h-10 text-[10px]">
                <Clock className="mr-2 h-3.5 w-3.5 opacity-40" />
                <SelectValue placeholder="STATUS_STATE" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">ALL_STATUS</SelectItem>
                <SelectItem value="draft">DRAFT</SelectItem>
                <SelectItem value="in_progress">IN_PROGRESS</SelectItem>
                <SelectItem value="review">UNDER_REVIEW</SelectItem>
                <SelectItem value="approved">APPROVED</SelectItem>
                <SelectItem value="implemented">IMPLEMENTED</SelectItem>
                <SelectItem value="closed">CLOSED</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <Card className="rounded-rams-sm overflow-hidden border-rams-border shadow-none">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>A3_IDENTIFIER</TableHead>
                <TableHead>RESOLUTION_TITLE</TableHead>
                <TableHead>PROTOCOL_TYPE</TableHead>
                <TableHead>STATUS_NODE</TableHead>
                <TableHead>PRIORITY</TableHead>
                <TableHead>AUTHOR</TableHead>
                <TableHead>PROGRESS_KPI</TableHead>
                <TableHead>TARGET_HORIZON</TableHead>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredA3s.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-24">
                    <FileText className="h-12 w-12 text-muted-foreground/20 mx-auto mb-4" />
                    <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">Zero A3 protocols identified</p>
                    <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">Adjust parameters or initialize new resolution protocol</p>
                  </TableCell>
                </TableRow>
              ) : (
                filteredA3s.map((a3) => (
                  <TableRow 
                    key={a3.id} 
                    className="group transition-none cursor-pointer"
                    onClick={() => router.push(`/a3/${a3.id}`)}
                  >
                    <TableCell className="font-mono font-bold text-rams-orange tabular-nums">{a3.a3_number}</TableCell>
                    <TableCell>
                      <span className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{a3.title}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn("rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4", typeConfig[a3.a3_type].color)}>
                        {typeConfig[a3.a3_type].label.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant[a3.status]} size="sm">
                        {a3.status.toUpperCase().replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={priorityBadgeVariant[a3.priority]} size="sm">
                        {a3.priority.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">{a3.author_name}</TableCell>
                    <TableCell>
                      <div className="w-24 space-y-1.5">
                        <div className="flex justify-between text-[9px] font-mono font-bold tabular-nums">
                          <span>{a3.progress_percentage}%</span>
                        </div>
                        <div className="h-1 bg-rams-panel border border-rams-border/30 overflow-hidden">
                          <div className="h-full bg-rams-orange transition-all duration-500" style={{ width: `${a3.progress_percentage}%` }} />
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className={cn("font-mono text-[10px] uppercase tracking-tighter", isOverdue(a3) ? 'text-rams-red' : 'text-muted-foreground/60')}>
                        {a3.target_completion_date ? formatDate(a3.target_completion_date) : 'N/A'}
                        {isOverdue(a3) && <span className="text-[8px] ml-1 opacity-60">(OVERDUE)</span>}
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
                          <DropdownMenuItem onClick={() => router.push(`/a3/${a3.id}`)}>
                            <Eye className="mr-2 h-3.5 w-3.5" /> ANALYZE
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => router.push(`/a3/${a3.id}/edit`)}>
                            <Edit className="mr-2 h-3.5 w-3.5" /> REFINE
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-rams-red" onClick={() => handleDelete(a3.id)}>
                            TERMINATE_NODE
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}
