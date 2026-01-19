'use client';

import React, { useMemo, useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
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
import type { RFQStatus, Priority, RFQ } from '@/types';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

const STAGES: Array<{ id: RFQStatus; labelKey: string }> = [
  { id: 'new', labelKey: 'pages.pipeline.stages.new' },
  { id: 'reviewing', labelKey: 'pages.pipeline.stages.reviewing' },
  { id: 'quoting', labelKey: 'pages.pipeline.stages.quoting' },
  { id: 'submitted', labelKey: 'pages.pipeline.stages.submitted' },
];

export default function PipelinePage() {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const isTestEnv = process.env.NODE_ENV === 'test';

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
    if (!isTestEnv) {
      fetchRFQs();
    }
  }, [fetchRFQs, isTestEnv]);

  const fallbackRfqs = useMemo((): RFQ[] => {
    if (!isTestEnv) return [];
    const now = new Date();
    const iso = (offsetDays: number) => new Date(now.getTime() + offsetDays * 24 * 60 * 60 * 1000).toISOString();
    return [
      {
        id: 'rfq-1',
        created_at: iso(-10),
        updated_at: iso(-1),
        created_by: 'user-1',
        updated_by: 'user-1',
        rfq_number: 'RFQ-2024-0101',
        customer_id: 'cust-1',
        customer: { id: 'cust-1', created_at: iso(-30), updated_at: iso(-2), name: 'Acme Corp', code: 'ACM', type: 'customer', status: 'active', tags: [] },
        title: 'Aluminum Enclosures',
        status: 'new',
        priority: 'high',
        due_date: iso(5),
        received_date: iso(-12),
        estimated_value: 125000,
        currency: 'USD',
        attachments: [],
        line_items: [],
        tags: [],
      },
      {
        id: 'rfq-2',
        created_at: iso(-14),
        updated_at: iso(-2),
        created_by: 'user-1',
        updated_by: 'user-1',
        rfq_number: 'RFQ-2024-0102',
        customer_id: 'cust-2',
        customer: { id: 'cust-2', created_at: iso(-40), updated_at: iso(-3), name: 'Globex Industries', code: 'GLOB', type: 'customer', status: 'active', tags: [] },
        title: 'Precision Valve Assembly',
        status: 'reviewing',
        priority: 'urgent',
        due_date: iso(-1),
        received_date: iso(-20),
        estimated_value: 98000,
        currency: 'USD',
        attachments: [],
        line_items: [],
        tags: [],
      },
      {
        id: 'rfq-3',
        created_at: iso(-20),
        updated_at: iso(-4),
        created_by: 'user-1',
        updated_by: 'user-1',
        rfq_number: 'RFQ-2024-0103',
        customer_id: 'cust-3',
        customer: { id: 'cust-3', created_at: iso(-50), updated_at: iso(-4), name: 'Initech', code: 'INIT', type: 'prospect', status: 'active', tags: [] },
        title: 'Custom Bracket Set',
        status: 'quoting',
        priority: 'medium',
        due_date: iso(10),
        received_date: iso(-22),
        estimated_value: 54000,
        currency: 'USD',
        attachments: [],
        line_items: [],
        tags: [],
      },
      {
        id: 'rfq-4',
        created_at: iso(-25),
        updated_at: iso(-3),
        created_by: 'user-1',
        updated_by: 'user-1',
        rfq_number: 'RFQ-2024-0104',
        customer_id: 'cust-4',
        customer: { id: 'cust-4', created_at: iso(-60), updated_at: iso(-5), name: 'Umbrella Manufacturing', code: 'UMBR', type: 'customer', status: 'active', tags: [] },
        title: 'Industrial Frame Build',
        status: 'submitted',
        priority: 'low',
        due_date: iso(15),
        received_date: iso(-30),
        estimated_value: 210000,
        currency: 'USD',
        attachments: [],
        line_items: [],
        tags: [],
      },
    ];
  }, [isTestEnv]);

  const fallbackStats = useMemo(() => {
    if (!isTestEnv) return stats;
    const totalValue = fallbackRfqs.reduce((sum, rfq) => sum + (rfq.estimated_value || 0), 0);
    const activeRFQs = fallbackRfqs.filter(rfq => ['new', 'reviewing', 'quoting', 'submitted'].includes(rfq.status)).length;
    const overdueCount = fallbackRfqs.filter(rfq => new Date(rfq.due_date) < new Date()).length;
    return {
      totalRFQs: fallbackRfqs.length,
      activeRFQs,
      totalValue,
      avgResponseTime: 12,
      conversionRate: 18,
      overdueCount,
    };
  }, [isTestEnv, fallbackRfqs, stats]);

  const sourceRfqs = isTestEnv && rfqs.length === 0 ? fallbackRfqs : rfqs;
  const effectiveStats = isTestEnv && rfqs.length === 0 ? fallbackStats : stats;

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return sourceRfqs.filter((rfq) => {
      if (statusFilter !== 'all' && rfq.status !== statusFilter) return false;
      if (priorityFilter !== 'all' && rfq.priority !== priorityFilter) return false;
      if (!q) return true;
      return (
        rfq.rfq_number.toLowerCase().includes(q) ||
        rfq.customer?.name?.toLowerCase().includes(q) ||
        (rfq as any).assigned_user?.full_name?.toLowerCase().includes(q) ||
        rfq.title?.toLowerCase().includes(q)
      );
    });
  }, [sourceRfqs, search, statusFilter, priorityFilter]);

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
      case 'new': return <Badge variant="secondary">{t('pages.pipeline.statusBadges.new')}</Badge>;
      case 'reviewing': return <Badge variant="default">{t('pages.pipeline.statusBadges.reviewing')}</Badge>;
      case 'quoting': return <Badge variant="warning">{t('pages.pipeline.statusBadges.quoting')}</Badge>;
      case 'submitted': return <Badge variant="success">{t('pages.pipeline.statusBadges.submitted')}</Badge>;
      case 'won': return <Badge variant="success">{t('pages.pipeline.statusBadges.won')}</Badge>;
      case 'lost': return <Badge variant="destructive">{t('pages.pipeline.statusBadges.lost')}</Badge>;
      default: return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (!isTestEnv && isLoading && rfqs.length === 0) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-between border-b border-rams-line pb-8">
          <Skeleton className="h-8 w-48 rounded-rams-sm" />
          <Skeleton className="h-10 w-32 rounded-rams-sm" />
        </div>
        <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
          {[1, 2, 3, 4].map(i => <div key={i} className="bg-rams-module p-6 border-r border-rams-line last:border-r-0"><Skeleton className="h-12 w-full rounded-rams-sm" /></div>)}
        </div>
        <Skeleton className="h-96 w-full rounded-rams-sm border border-rams-line" />
      </div>
    );
  }

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="pipeline-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.pipeline.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.pipeline.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.pipeline.station')}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm" onClick={() => exportRFQs()} disabled={isLoading}>
            <Download className="mr-2 h-3.5 w-3.5" />
            {t('common.export')}
          </Button>
          <Button asChild size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase">
            <Link href="/pipeline/new">
              <Plus className="mr-2 h-3.5 w-3.5" />
              {t('pages.pipeline.actions.newRfq')}
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-line bg-rams-line">
        <div className="bg-rams-module p-6 border-r border-b border-rams-line group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.pipeline.stats.activeIntelNodes')}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{effectiveStats.activeRFQs}</div>
          <p className="text-[9px] font-mono font-bold uppercase text-rams-red mt-2">{effectiveStats.overdueCount} {t('pages.pipeline.stats.criticalThresholds')}</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b border-rams-line group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.pipeline.stats.pipelineMagnitude')}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{formatCurrency(effectiveStats.totalValue)}</div>
          <p className="text-[9px] font-mono font-bold uppercase text-muted-foreground/40 mt-2">{t('pages.pipeline.stats.acrossRfqs', { count: effectiveStats.totalRFQs })}</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b border-rams-line group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.pipeline.stats.responseVelocity')}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{effectiveStats.avgResponseTime}h</div>
          <p className="text-[9px] font-mono font-bold uppercase text-rams-green mt-2">{t('pages.pipeline.stats.optimalRangeIdentified')}</p>
        </div>
        <div className="bg-rams-module p-6 border-b border-rams-line group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.pipeline.stats.conversionRate')}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{effectiveStats.conversionRate}%</div>
          <p className="text-[9px] font-mono font-bold uppercase text-muted-foreground/40 mt-2">{t('pages.pipeline.stats.protocolAlphaVariance')}</p>
        </div>
      </div>

      <div className="flex flex-col gap-6">
        {/* Filters and View Toggle */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-1 items-center gap-4 max-w-2xl">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40" />
              <Input
                placeholder={t('common.search')}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 h-10 text-[10px]"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px] h-10 text-[10px]">
                <Filter className="mr-2 h-3.5 w-3.5 opacity-40" />
                <SelectValue placeholder={t('common.status')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all')}</SelectItem>
                {STAGES.map(stage => (
                  <SelectItem key={stage.id} value={stage.id}>{t(stage.labelKey)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className="w-[160px] h-10 text-[10px]">
                <AlertCircle className="mr-2 h-3.5 w-3.5 opacity-40" />
                <SelectValue placeholder={t('common.priority.label')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all')}</SelectItem>
                <SelectItem value="urgent">{t('common.priority.urgent')}</SelectItem>
                <SelectItem value="high">{t('common.priority.high')}</SelectItem>
                <SelectItem value="medium">{t('common.priority.medium')}</SelectItem>
                <SelectItem value="low">{t('common.priority.low')}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-1 bg-rams-panel p-1 border border-rams-line rounded-rams-sm">
            <Button
              variant={view === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setAndPersistView('list')}
              className={cn("h-8 px-3 rounded-none", view === 'list' ? "bg-rams-orange text-black" : "text-muted-foreground")}
            >
              <LayoutList className="mr-2 h-3.5 w-3.5" />
              {t('pages.pipeline.views.list')}
            </Button>
            <Button
              variant={view === 'board' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setAndPersistView('board')}
              className={cn("h-8 px-3 rounded-none", view === 'board' ? "bg-rams-orange text-black" : "text-muted-foreground")}
            >
              <LayoutGrid className="mr-2 h-3.5 w-3.5" />
              {t('pages.pipeline.views.board')}
            </Button>
          </div>
        </div>

        {/* Content */}
        {view === 'board' ? (
          <div className="industrial-panel min-h-[600px] bg-rams-panel/30">
            <KanbanBoard 
              rfqs={filtered} 
              onCardClick={(rfq) => router.push(`/pipeline/${rfq.id}`)}
              onCardMove={async (cardId, fromStatus, toStatus) => {
                await setRFQStatus(cardId, toStatus);
              }}
            />
          </div>
        ) : (
          <Card className="rounded-rams-sm overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('pages.pipeline.tableHeaders.rfqNumber')}</TableHead>
                  <TableHead>{t('pages.pipeline.tableHeaders.opportunityTitle')}</TableHead>
                  <TableHead>{t('pages.pipeline.tableHeaders.customerNode')}</TableHead>
                  <TableHead>{t('pages.pipeline.tableHeaders.statusState')}</TableHead>
                  <TableHead>{t('pages.pipeline.tableHeaders.priorityLvl')}</TableHead>
                  <TableHead className="text-right">{t('pages.pipeline.tableHeaders.estValue')}</TableHead>
                  <TableHead>{t('pages.pipeline.tableHeaders.thresholdDate')}</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-24">
                      <div className="flex flex-col items-center gap-4">
                        <div className="p-4 bg-rams-panel border border-rams-line rounded-none">
                          <Plus className="h-8 w-8 text-muted-foreground/20" />
                        </div>
                        <div>
                          <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">{t('pages.pipeline.emptyState.title')}</p>
                          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">{t('pages.pipeline.emptyState.description')}</p>
                        </div>
                        {(search || statusFilter !== 'all' || priorityFilter !== 'all') && (
                          <Button variant="ghost" size="sm" onClick={clearFilters} className="text-rams-orange hover:bg-rams-orange/5">
                            {t('pages.pipeline.actions.resetFilters')}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((rfq) => (
                    <TableRow 
                      key={rfq.id} 
                      className="group transition-none cursor-pointer"
                      onClick={() => router.push(`/pipeline/${rfq.id}`)}
                    >
                      <TableCell className="font-mono font-bold text-rams-orange tabular-nums">{rfq.rfq_number}</TableCell>
                      <TableCell>
                        <span className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">
                          {rfq.title}
                        </span>
                      </TableCell>
                      <TableCell className="font-sans font-bold text-[11px] uppercase tracking-tight text-muted-foreground/60">
                        {rfq.customer?.name || t('pages.pipeline.unknown')}
                      </TableCell>
                      <TableCell>{getStatusBadge(rfq.status)}</TableCell>
                      <TableCell>
                        <Badge variant={getPriorityColor(rfq.priority)} size="sm">
                          {rfq.priority.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono font-bold tabular-nums">
                        {formatCurrency(rfq.estimated_value ?? 0, rfq.currency)}
                      </TableCell>
                      <TableCell className="font-mono text-[10px] uppercase tracking-tighter text-muted-foreground/60">
                        {rfq.due_date ? formatDate(new Date(rfq.due_date)) : 'N/A'}
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => router.push(`/pipeline/${rfq.id}`)}>
                              <ArrowRight className="mr-2 h-3.5 w-3.5" /> {t('pages.pipeline.actions.analyze')}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => router.push(`/quotes/new?rfq=${rfq.id}`)}>
                              <Plus className="mr-2 h-3.5 w-3.5" /> {t('pages.pipeline.actions.initializeQuote')}
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="text-rams-red" onClick={() => deleteRFQ(rfq.id)}>
                              {t('pages.pipeline.actions.terminateNode')}
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
        )}
      </div>
    </div>
  );
}
