'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
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

interface Quote {
  id: string;
  quoteNumber: string;
  rfqNumber: string;
  customerName: string;
  status: 'draft' | 'pending_approval' | 'approved' | 'sent' | 'accepted' | 'rejected' | 'expired';
  totalAmount: number;
  margin: number;
  validUntil: string;
  createdAt: string;
  createdBy: {
    name: string;
    avatar?: string;
  };
  version: number;
}

const mockQuotes: Quote[] = [
  {
    id: '1',
    quoteNumber: 'Q-2024-0112',
    rfqNumber: 'RFQ-2024-0089',
    customerName: 'Aerospace Dynamics Inc.',
    status: 'sent',
    totalAmount: 124500,
    margin: 28.5,
    validUntil: '2024-02-15',
    createdAt: '2024-01-10',
    createdBy: { name: 'Sarah Chen' },
    version: 2,
  },
  {
    id: '2',
    quoteNumber: 'Q-2024-0111',
    rfqNumber: 'RFQ-2024-0087',
    customerName: 'TechCorp Manufacturing',
    status: 'accepted',
    totalAmount: 89200,
    margin: 32.1,
    validUntil: '2024-02-10',
    createdAt: '2024-01-09',
    createdBy: { name: 'John Doe' },
    version: 1,
  },
  {
    id: '3',
    quoteNumber: 'Q-2024-0110',
    rfqNumber: 'RFQ-2024-0085',
    customerName: 'Global Defense Systems',
    status: 'pending_approval',
    totalAmount: 215000,
    margin: 24.8,
    validUntil: '2024-02-20',
    createdAt: '2024-01-08',
    createdBy: { name: 'Maria Garcia' },
    version: 1,
  },
  {
    id: '4',
    quoteNumber: 'Q-2024-0109',
    rfqNumber: 'RFQ-2024-0082',
    customerName: 'Industrial Solutions Ltd.',
    status: 'draft',
    totalAmount: 45000,
    margin: 22.0,
    validUntil: '2024-02-25',
    createdAt: '2024-01-07',
    createdBy: { name: 'Sarah Chen' },
    version: 1,
  },
  {
    id: '5',
    quoteNumber: 'Q-2024-0108',
    rfqNumber: 'RFQ-2024-0080',
    customerName: 'Precision Parts Co.',
    status: 'rejected',
    totalAmount: 67800,
    margin: 19.5,
    validUntil: '2024-01-30',
    createdAt: '2024-01-05',
    createdBy: { name: 'John Doe' },
    version: 3,
  },
  {
    id: '6',
    quoteNumber: 'Q-2024-0107',
    rfqNumber: 'RFQ-2024-0078',
    customerName: 'Aerospace Dynamics Inc.',
    status: 'expired',
    totalAmount: 98500,
    margin: 26.3,
    validUntil: '2024-01-01',
    createdAt: '2024-01-02',
    createdBy: { name: 'Maria Garcia' },
    version: 1,
  },
];

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
      .reduce((sum, q) => sum + q.totalAmount, 0);
    const avgMargin = quotes.length > 0
      ? quotes.reduce((sum, q) => sum + q.margin, 0) / quotes.length
      : 0;
    return { pending, sent, totalValue, avgMargin };
  }, [quotes]);

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/10">
              <Clock className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.pending}</p>
              <p className="text-sm text-muted-foreground">Pending Approval</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Send className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.sent}</p>
              <p className="text-sm text-muted-foreground">Sent to Customers</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-success/10">
              <DollarSign className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold">{formatCurrency(stats.totalValue)}</p>
              <p className="text-sm text-muted-foreground">Pipeline Value</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-secondary/50">
              <TrendingUp className="h-5 w-5 text-foreground" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.avgMargin.toFixed(1)}%</p>
              <p className="text-sm text-muted-foreground">Avg. Margin</p>
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
  const isExpiringSoon = new Date(quote.validUntil) <= new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) 
    && quote.status === 'sent';

  return (
    <tr 
      className="border-b hover:bg-muted/50 cursor-pointer transition-colors"
      onClick={() => router.push(`/quotes/${quote.id}`)}
    >
      <td className="py-3 px-4">
        <div>
          <p className="font-medium">{quote.quoteNumber}</p>
          <p className="text-sm text-muted-foreground">
            <Link 
              href={`/pipeline/${quote.id}`} 
              className="hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {quote.rfqNumber}
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
          {quote.customerName}
        </Link>
      </td>
      <td className="py-3 px-4">
        <Badge variant={config.variant} className="gap-1">
          <StatusIcon className="h-3 w-3" />
          {config.label}
        </Badge>
      </td>
      <td className="py-3 px-4 text-right font-medium">
        {formatCurrency(quote.totalAmount)}
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
          {formatDate(new Date(quote.validUntil))}
          {isExpiringSoon && <span className="text-xs ml-1">(expires soon)</span>}
        </div>
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <Avatar size="sm">
            <AvatarImage src={quote.createdBy.avatar} />
            <AvatarFallback>{getInitials(quote.createdBy.name)}</AvatarFallback>
          </Avatar>
          <span className="text-sm">{quote.createdBy.name}</span>
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
  const router = useRouter();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');

  const filteredQuotes = React.useMemo(() => {
    return mockQuotes.filter((quote) => {
      const matchesSearch = searchQuery === '' ||
        quote.quoteNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        quote.rfqNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        quote.customerName.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'all' || quote.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [searchQuery, statusFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Quotes</h1>
          <p className="text-muted-foreground">Manage quotes and track approval status</p>
        </div>
        <Button onClick={() => router.push('/quotes/new')}>
          <Plus className="mr-2 h-4 w-4" />
          New Quote
        </Button>
      </div>

      {/* Stats */}
      <QuoteStats quotes={mockQuotes} />

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
