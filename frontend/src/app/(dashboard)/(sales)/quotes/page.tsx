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


const statusConfig: Record<Quote['status'], { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'danger' | 'outline'; icon: typeof Clock }> = {
  draft: { label: 'Draft', variant: 'secondary', icon: FileText },
  pending_approval: { label: 'Pending Approval', variant: 'warning', icon: Clock },
  approved: { label: 'Approved', variant: 'default', icon: CheckCircle },
  sent: { label: 'Sent', variant: 'default', icon: Send },
  accepted: { label: 'Accepted', variant: 'success', icon: CheckCircle },
  rejected: { label: 'Rejected', variant: 'danger', icon: XCircle },
  expired: { label: 'Expired', variant: 'outline', icon: Calendar },
};

function QuoteStats({ quotes }: { quotes: Quote[] }) {
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
    <div className="grid gap-4 md:grid-cols-4">
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Pending Approval</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats.pending}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-warning/10 text-warning">
              <Clock className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Sent to Customers</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats.sent}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-primary/10 text-primary">
              <Send className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Pipeline Value</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{formatCurrency(stats.totalValue)}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-emerald-500/10 text-emerald-600">
              <DollarSign className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Avg. Margin</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats.avgMargin.toFixed(1)}%</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-muted/30 text-foreground">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function QuoteRow({ quote }: { quote: Quote }) {
  const router = useRouter();
  const config = statusConfig[quote.status];
  const StatusIcon = config.icon;
  const isExpiringSoon = new Date(quote.valid_until) <= new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) 
    && quote.status === 'sent';

  return (
    <tr 
      className="border-b hover:bg-muted/50 cursor-pointer transition-colors"
      onClick={() => router.push(`/quotes/${quote.id}`)}
    >
      <td className="py-3 px-4">
        <div>
          <p className="font-medium">{quote.quote_number}</p>
          <p className="text-sm text-muted-foreground">
            <Link 
              href={`/pipeline/${quote.id}`} 
              className="hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {quote.rfq_number}
            </Link>
          </p>
        </div>
      </td>
      <td className="py-3 px-4">
        <Link 
          href={`/customers/${quote.id}`} 
          className="hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {quote.customer_name}
        </Link>
      </td>
      <td className="py-3 px-4">
        <Badge variant={config.variant} className="gap-1">
          <StatusIcon className="h-3 w-3" />
          {config.label}
        </Badge>
      </td>
      <td className="py-3 px-4 text-right font-medium">
        {formatCurrency(quote.total_amount)}
      </td>
      <td className="py-3 px-4 text-right">
        <span className={cn(
          'font-medium',
          quote.margin >= 30 ? 'text-success' : quote.margin >= 20 ? 'text-warning' : 'text-danger'
        )}>
          {quote.margin.toFixed(1)}%
        </span>
      </td>
      <td className="py-3 px-4">
        <div className={cn(isExpiringSoon && 'text-warning')}>
          {formatDate(new Date(quote.valid_until))}
          {isExpiringSoon && <span className="text-xs ml-1">(expires soon)</span>}
        </div>
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <Avatar size="sm">
            <AvatarImage src={quote.created_by.avatar} />
            <AvatarFallback>{getInitials(quote.created_by.name)}</AvatarFallback>
          </Avatar>
          <span className="text-sm">{quote.created_by.name}</span>
        </div>
      </td>
      <td className="py-3 px-4 text-center text-muted-foreground">
        v{quote.version}
      </td>
      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push(`/quotes/${quote.id}`)}>
              <Eye className="mr-2 h-4 w-4" />
              View
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Copy className="mr-2 h-4 w-4" />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuItem>
              <FileText className="mr-2 h-4 w-4" />
              Export PDF
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {quote.status === 'draft' && (
              <DropdownMenuItem>
                <Send className="mr-2 h-4 w-4" />
                Submit for Approval
              </DropdownMenuItem>
            )}
            {quote.status === 'approved' && (
              <DropdownMenuItem>
                <Send className="mr-2 h-4 w-4" />
                Send to Customer
              </DropdownMenuItem>
            )}
            {quote.status === 'sent' && (
              <>
                <DropdownMenuItem className="text-success">
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Mark Won
                </DropdownMenuItem>
                <DropdownMenuItem className="text-danger">
                  <XCircle className="mr-2 h-4 w-4" />
                  Mark Lost
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
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
    <div className="space-y-8 page-fade-in" data-testid="quotes-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight ">
            {t('pages.quotes.title')}
          </h1>
          <p className="text-muted-foreground font-medium">{t('pages.quotes.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine" onClick={() => router.push('/quotes/new')}>
            <Plus className="mr-2 h-4 w-4" />
            New Quotation
          </Button>
        </div>
      </div>

      {/* Stats */}
      <QuoteStats quotes={mappedQuotes} />

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search quotes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="pending_approval">Pending Approval</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="sent">Sent</SelectItem>
                  <SelectItem value="accepted">Accepted</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="expired">Expired</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">Quote / RFQ</th>
                  <th className="py-3 px-4 text-left font-medium">Customer</th>
                  <th className="py-3 px-4 text-left font-medium">Status</th>
                  <th className="py-3 px-4 text-right font-medium">Amount</th>
                  <th className="py-3 px-4 text-right font-medium">Margin</th>
                  <th className="py-3 px-4 text-left font-medium">Valid Until</th>
                  <th className="py-3 px-4 text-left font-medium">Created By</th>
                  <th className="py-3 px-4 text-center font-medium">Ver.</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filteredQuotes.map((quote) => (
                  <QuoteRow key={quote.id} quote={quote} />
                ))}
              </tbody>
            </table>
          </div>
          {filteredQuotes.length === 0 && (
            <div className="text-center py-12">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-medium">No quotes found</h3>
              <p className="text-muted-foreground">
                {searchQuery || statusFilter !== 'all' 
                  ? 'Try adjusting your filters' 
                  : 'Create your first quote to get started'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
