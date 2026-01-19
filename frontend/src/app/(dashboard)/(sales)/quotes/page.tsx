'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  Copy,
  FileText,
  Send,
  CheckCircle,
  XCircle,
  Clock,
  DollarSign,
  TrendingUp,
  Calendar,
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
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn, formatCurrency, formatDate, getInitials } from '@/lib/utils';
import { useQuoteStore } from '@/stores/quotes';
import type { QuoteStatus } from '@/types';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

interface Quote {
  id: string;
  quote_number: string;
  rfq_number: string;
  customer_name: string;
  status: 'draft' | 'pending_approval' | 'approved' | 'sent' | 'accepted' | 'rejected' | 'expired';
  total_amount: number;
  margin: number;
  valid_until: string;
  created_at: string;
  created_by: {
    name: string;
    avatar?: string;
  };
  version: number;
}


const statusConfig: Record<Quote['status'], { labelKey: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'danger' | 'outline'; icon: typeof Clock }> = {
  draft: { labelKey: 'common.draft', variant: 'secondary', icon: FileText },
  pending_approval: { labelKey: 'pages.quotes.status.pendingApproval', variant: 'warning', icon: Clock },
  approved: { labelKey: 'common.approved', variant: 'default', icon: CheckCircle },
  sent: { labelKey: 'pages.quotes.status.sent', variant: 'default', icon: Send },
  accepted: { labelKey: 'pages.quotes.status.accepted', variant: 'success', icon: CheckCircle },
  rejected: { labelKey: 'pages.quotes.status.rejected', variant: 'danger', icon: XCircle },
  expired: { labelKey: 'pages.quotes.status.expired', variant: 'outline', icon: Calendar },
};

function QuoteStats({ quotes }: { quotes: Quote[] }) {
  const { t } = useI18n();
  const stats = React.useMemo(() => {
    const pending = quotes.filter((q) => q.status === 'pending_approval').length;
    const sent = quotes.filter((q) => q.status === 'sent').length;
    const totalValue = quotes.filter((q) => ['sent', 'pending_approval'].includes(q.status))
      .reduce((sum, q) => sum + q.total_amount, 0);
    const avgMargin = quotes.length > 0
      ? quotes.reduce((sum, q) => sum + q.margin, 0) / quotes.length
      : 0;
    return { pending, sent, totalValue, avgMargin };
  }, [quotes]);

  return (
    <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.quotes.stats.pendingApproval')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.pending}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.quotes.stats.sentToCustomer')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.sent}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.quotes.stats.pipelineValue')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{formatCurrency(stats.totalValue)}</p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-line">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.quotes.stats.avgMargin')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{stats.avgMargin.toFixed(1)}%</p>
      </div>
    </div>
  );
}

function QuoteRow({ quote }: { quote: Quote }) {
  const router = useRouter();
  const { t } = useI18n();
  const config = statusConfig[quote.status];
  const StatusIcon = config.icon;
  const isExpiringSoon = new Date(quote.valid_until).getTime() - new Date().getTime() < 1000 * 60 * 60 * 24 * 7;

  return (
    <TableRow 
      className="transition-none"
    >
      <TableCell>
        <div>
          <p className="font-mono font-bold text-rams-orange tabular-nums">{quote.quote_number}</p>
          <p className="text-[9px] font-mono uppercase tracking-tight text-muted-foreground/40">{t('pages.quotes.rfqNumber')}: {quote.rfq_number}</p>
        </div>
      </TableCell>
      <TableCell>
        <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{quote.customer_name}</p>
      </TableCell>
      <TableCell>
        <Badge variant={config.variant} size="sm">
          {t(config.labelKey)}
        </Badge>
      </TableCell>
      <TableCell className="text-right">
        <span className="font-mono font-bold tabular-nums">
          {formatCurrency(quote.total_amount)}
        </span>
      </TableCell>
      <TableCell className="text-right">
        <span className={cn(
          'font-mono font-bold tabular-nums',
          quote.margin >= 30 ? 'text-rams-green' : quote.margin >= 20 ? 'text-rams-orange' : 'text-rams-red'
        )}>
          {quote.margin.toFixed(1)}%
        </span>
      </TableCell>
      <TableCell>
        <div className={cn("font-mono text-[10px] uppercase tracking-tighter", isExpiringSoon ? 'text-rams-orange' : 'text-muted-foreground/60')}>
          {formatDate(new Date(quote.valid_until))}
          {isExpiringSoon && <span className="text-[8px] ml-1 opacity-60">({t('pages.quotes.labels.expiresSoon')})</span>}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <Avatar className="h-6 w-6 rounded-none border border-rams-line">
            <AvatarImage src={quote.created_by.avatar} />
            <AvatarFallback className="text-[8px] bg-rams-panel font-mono font-black">{getInitials(quote.created_by.name)}</AvatarFallback>
          </Avatar>
          <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{quote.created_by.name.split(' ')[0]}</span>
        </div>
      </TableCell>
      <TableCell className="text-center font-mono text-[9px] text-muted-foreground/30">
        v{quote.version}
      </TableCell>
      <TableCell onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-rams-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push(`/quotes/${quote.id}`)}>
              <Eye className="mr-2 h-3.5 w-3.5" />
              {t('pages.quotes.actions.analyze')}
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Copy className="mr-2 h-3.5 w-3.5" />
              {t('pages.quotes.actions.cloneProtocol')}
            </DropdownMenuItem>
            <DropdownMenuItem>
              <FileText className="mr-2 h-3.5 w-3.5" />
              {t('pages.quotes.actions.exportProtocol')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {quote.status === 'draft' && (
              <DropdownMenuItem>
                <Send className="mr-2 h-3.5 w-3.5" />
                {t('pages.quotes.actions.initiateApproval')}
              </DropdownMenuItem>
            )}
            {quote.status === 'approved' && (
              <DropdownMenuItem>
                <Send className="mr-2 h-3.5 w-3.5 text-rams-orange" />
                {t('pages.quotes.actions.transmitProtocol')}
              </DropdownMenuItem>
            )}
            {quote.status === 'sent' && (
              <>
                <DropdownMenuItem className="text-rams-green font-black">
                  <CheckCircle className="mr-2 h-3.5 w-3.5" />
                  {t('pages.quotes.actions.protocolWon')}
                </DropdownMenuItem>
                <DropdownMenuItem className="text-rams-red font-black">
                  <XCircle className="mr-2 h-3.5 w-3.5" />
                  {t('pages.quotes.actions.protocolLost')}
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

export default function QuotesPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { quotes, isLoading, fetchQuotes } = useQuoteStore();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');

  React.useEffect(() => {
    fetchQuotes();
  }, [fetchQuotes]);

  const mappedQuotes: Quote[] = React.useMemo(() => {
    return quotes.map(q => ({
      id: q.id,
      quote_number: q.quoteNumber,
      rfq_number: 'RFQ-2024-' + q.id.substring(0, 4),
      customer_name: q.customerName,
      status: q.status,
      total_amount: q.total,
      margin: q.subtotal > 0 ? ((q.total - q.subtotal) / q.total) * 100 : 0,
      valid_until: q.validUntil,
      created_at: q.createdAt,
      created_by: { name: 'System' },
      version: q.version,
    }));
  }, [quotes]);

  const filteredQuotes = React.useMemo(() => {
    return mappedQuotes.filter((quote) => {
      const matchesSearch = searchQuery === '' ||
        quote.quote_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        quote.rfq_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        quote.customer_name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'all' || quote.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [mappedQuotes, searchQuery, statusFilter]);

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="quotes-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.quotes.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.quotes.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: PRICING-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button size="default" className="rounded-rams-sm" onClick={() => router.push('/quotes/new')}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            {t('pages.quotes.initializeQuotation')}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <QuoteStats quotes={mappedQuotes} />

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40" />
          <Input
            placeholder={t('pages.quotes.searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-10 text-[10px]"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px] h-10 text-[10px]">
            <Filter className="mr-2 h-3.5 w-3.5 opacity-40" />
            <SelectValue placeholder="STATUS_FILTER" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('pages.quotes.filters.allProtocols')}</SelectItem>
            <SelectItem value="draft">{t('pages.quotes.filters.draft')}</SelectItem>
            <SelectItem value="pending_approval">{t('pages.quotes.filters.pendingReview')}</SelectItem>
            <SelectItem value="approved">{t('pages.quotes.filters.approved')}</SelectItem>
            <SelectItem value="sent">{t('pages.quotes.filters.transmitted')}</SelectItem>
            <SelectItem value="accepted">{t('pages.quotes.filters.accepted')}</SelectItem>
            <SelectItem value="rejected">{t('pages.quotes.filters.rejected')}</SelectItem>
            <SelectItem value="expired">{t('pages.quotes.filters.expired')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <Card className="rounded-rams-sm overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('pages.quotes.table.quoteProtocol')}</TableHead>
                <TableHead>{t('pages.quotes.table.customerNode')}</TableHead>
                <TableHead>{t('pages.quotes.table.statusState')}</TableHead>
                <TableHead className="text-right">{t('pages.quotes.table.totalValue')}</TableHead>
                <TableHead className="text-right">{t('pages.quotes.table.marginKpi')}</TableHead>
                <TableHead>{t('pages.quotes.table.validThru')}</TableHead>
                <TableHead>{t('pages.quotes.table.operator')}</TableHead>
                <TableHead className="text-center">{t('pages.quotes.table.version')}</TableHead>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredQuotes.map((quote) => (
                <QuoteRow key={quote.id} quote={quote} />
              ))}
            </TableBody>
          </Table>
        </div>
        {filteredQuotes.length === 0 && (
          <div className="text-center py-16">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground/20" />
            <div className="mt-4">
              <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">{t('pages.quotes.emptyState.title')}</p>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">
                {searchQuery || statusFilter !== 'all' 
                  ? t('pages.quotes.emptyState.adjustFilters')
                  : t('pages.quotes.emptyState.initializeFirst')}
              </p>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
