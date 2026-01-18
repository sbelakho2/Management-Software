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
  Edit,
  FileText,
  Send,
  CheckCircle,
  XCircle,
  Clock,
  DollarSign,
  TrendingUp,
  Package,
  Truck,
  CreditCard,
  ArrowRight,
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn, formatCurrency, formatDate } from '@/lib/utils';
import { apiClient } from '@/api/client';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

interface SalesOrder {
  id: string;
  so_number: string;
  account_id: string;
  account_name?: string;
  status: 'draft' | 'approved' | 'released' | 'shipped' | 'invoiced' | 'closed';
  currency: string;
  total_amount: number;
  line_count: number;
  payment_terms_days: number;
  source_quote_id?: string;
  created_at: string;
  approved_at?: string;
  released_at?: string;
}

interface SOStats {
  orders: {
    draft: number;
    approved: number;
    released: number;
  };
  invoices: {
    issued: number;
    paid: number;
    overdue: number;
  };
}

const statusConfig: Record<SalesOrder['status'], { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'danger' | 'outline'; icon: typeof Clock }> = {
  draft: { label: 'Draft', variant: 'secondary', icon: FileText },
  approved: { label: 'Approved', variant: 'default', icon: CheckCircle },
  released: { label: 'Released', variant: 'warning', icon: Package },
  shipped: { label: 'Shipped', variant: 'default', icon: Truck },
  invoiced: { label: 'Invoiced', variant: 'default', icon: CreditCard },
  closed: { label: 'Closed', variant: 'success', icon: CheckCircle },
};

function OrderStats({ stats }: { stats: SOStats | null }) {
  if (!stats) return null;

  return (
    <div className="grid gap-0 md:grid-cols-4 border border-rams-border bg-rams-border">
      <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Draft Orders</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.orders.draft}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Approved Orders</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.orders.approved}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Issued Invoices</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.invoices.issued}</p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-border">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-red/60 mb-4">Overdue Invoices</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-red tabular-nums">{stats.invoices.overdue}</p>
      </div>
    </div>
  );
}

function OrderRow({ order, onApprove, onRelease }: { 
  order: SalesOrder; 
  onApprove: (id: string) => void;
  onRelease: (id: string) => void;
}) {
  const config = statusConfig[order.status];
  const StatusIcon = config.icon;

  return (
    <TableRow 
      className="transition-none"
    >
      <TableCell>
        <div>
          <p className="font-mono font-bold text-rams-orange tabular-nums">{order.so_number}</p>
          {order.source_quote_id && (
            <Link 
              href={`/quotes/${order.source_quote_id}`}
              className="text-[9px] font-mono uppercase tracking-tight text-muted-foreground/40 hover:text-rams-orange"
              onClick={(e) => e.stopPropagation()}
            >
              Protocol: Source_Quote
            </Link>
          )}
        </div>
      </TableCell>
      <TableCell>
        <Link 
          href={`/customers/${order.account_id}`}
          className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 hover:text-rams-orange transition-none"
          onClick={(e) => e.stopPropagation()}
        >
          {order.account_name || 'Unknown'}
        </Link>
      </TableCell>
      <TableCell>
        <Badge variant={config.variant} size="sm">
          {config.label}
        </Badge>
      </TableCell>
      <TableCell className="text-right">
        <span className="font-mono font-bold tabular-nums">
          {formatCurrency(order.total_amount, order.currency)}
        </span>
      </TableCell>
      <TableCell className="text-center font-mono text-[10px] text-muted-foreground/40">
        {order.line_count}
      </TableCell>
      <TableCell className="font-mono text-[10px] text-muted-foreground/60 uppercase">
        {formatDate(new Date(order.created_at))}
      </TableCell>
      <TableCell onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-rams-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Eye className="mr-2 h-3.5 w-3.5" />
              Analyze Details
            </DropdownMenuItem>
            {order.status === 'draft' && (
              <DropdownMenuItem onClick={() => onApprove(order.id)}>
                <CheckCircle className="mr-2 h-3.5 w-3.5 text-rams-green" />
                Approve Protocol
              </DropdownMenuItem>
            )}
            {order.status === 'approved' && (
              <DropdownMenuItem onClick={() => onRelease(order.id)}>
                <Package className="mr-2 h-3.5 w-3.5 text-rams-orange" />
                Release to Station
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <CreditCard className="mr-2 h-3.5 w-3.5" />
              Generate Invoice
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

export default function SalesOrdersPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [orders, setOrders] = React.useState<SalesOrder[]>([]);
  const [stats, setStats] = React.useState<SOStats | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [search, setSearch] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');

  const fetchOrders = React.useCallback(async () => {
    setLoading(true);
    try {
      const [ordersRes, statsRes] = await Promise.all([
        apiClient.get('/sales/orders') as Promise<{ data: SalesOrder[] } | SalesOrder[]>,
        apiClient.get('/sales/stats') as Promise<{ data: SOStats } | SOStats>,
      ]);
      setOrders((ordersRes as { data: SalesOrder[] })?.data || (ordersRes as SalesOrder[]) || []);
      setStats((statsRes as { data: SOStats })?.data || (statsRes as SOStats) || null);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleApprove = async (orderId: string) => {
    try {
      await apiClient.post(`/sales/orders/${orderId}/approve`);
      fetchOrders();
    } catch (error) {
      console.error('Failed to approve order:', error);
    }
  };

  const handleRelease = async (orderId: string) => {
    try {
      await apiClient.post(`/sales/orders/${orderId}/release`);
      fetchOrders();
    } catch (error) {
      console.error('Failed to release order:', error);
    }
  };

  const filteredOrders = React.useMemo(() => {
    return orders.filter((order) => {
      const matchesSearch = 
        order.so_number.toLowerCase().includes(search.toLowerCase()) ||
        (order.account_name || '').toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === 'all' || order.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [orders, search, statusFilter]);

  return (
    <div className="space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('pages.orders.title')}</h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.orders.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: SALES-01</span>
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            className="rounded-rams-sm"
            onClick={() => router.push('/quotes')}
          >
            <FileText className="mr-2 h-3.5 w-3.5" />
            Quotes
          </Button>
          <Button 
            className="rounded-rams-sm"
            onClick={() => router.push('/quotes/new')}
          >
            <Plus className="mr-2 h-3.5 w-3.5" />
            New Order
          </Button>
        </div>
      </div>

      {/* Stats */}
      <OrderStats stats={stats} />

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40" />
          <Input 
            placeholder="SEARCH_PROTOCOL..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10 h-10 text-[10px]"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px] h-10 text-[10px]">
            <Filter className="mr-2 h-3.5 w-3.5 opacity-40" />
            <SelectValue placeholder="STATUS_FILTER" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">ALL_STATUS</SelectItem>
            <SelectItem value="draft">DRAFT</SelectItem>
            <SelectItem value="approved">APPROVED</SelectItem>
            <SelectItem value="released">RELEASED</SelectItem>
            <SelectItem value="shipped">SHIPPED</SelectItem>
            <SelectItem value="invoiced">INVOICED</SelectItem>
            <SelectItem value="closed">CLOSED</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Orders Table */}
      <Card className="rounded-rams-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ORDER_ID</TableHead>
              <TableHead>CUSTOMER_ACCOUNT</TableHead>
              <TableHead>STATUS_NODE</TableHead>
              <TableHead className="text-right">TOTAL_VALUE</TableHead>
              <TableHead className="text-center">LINES</TableHead>
              <TableHead>TIMESTAMP</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-16">
                  <div className="flex flex-col items-center gap-3">
                    <div className="animate-spin rounded-none h-8 w-8 border border-rams-orange border-t-transparent"></div>
                    <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">Synchronizing Protocols...</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : filteredOrders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-16">
                  <div className="flex flex-col items-center gap-3">
                    <Package className="h-12 w-12 text-muted-foreground/20" />
                    <div>
                      <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">Zero protocols identified</p>
                      <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">
                        {search || statusFilter !== 'all' 
                          ? 'Adjust filtering parameters' 
                          : 'Initialize your first order protocol'}
                      </p>
                    </div>
                    <Button 
                      className="mt-4 rounded-rams-sm"
                      onClick={() => router.push('/quotes/new')}
                    >
                      <Plus className="mr-2 h-3.5 w-3.5" />
                      Initialize Order
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              filteredOrders.map((order) => (
                <OrderRow 
                  key={order.id} 
                  order={order} 
                  onApprove={handleApprove}
                  onRelease={handleRelease}
                />
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-0 md:grid-cols-3 border border-rams-border bg-rams-border">
        <div 
          className="flex items-center justify-between p-6 bg-rams-module border-r border-rams-border cursor-pointer hover:bg-rams-panel transition-colors group"
          onClick={() => router.push('/quotes')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2 rounded-rams-sm bg-rams-panel border border-rams-border group-hover:border-rams-orange transition-colors">
              <FileText className="h-4 w-4 text-muted-foreground" />
            </div>
            <div>
              <p className="text-[11px] font-black uppercase tracking-tight text-foreground/80">Quote_Repository</p>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">Analyze source documents</p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-1 transition-all" />
        </div>
        
        <div 
          className="flex items-center justify-between p-6 bg-rams-module border-r border-rams-border cursor-pointer hover:bg-rams-panel transition-colors group"
          onClick={() => router.push('/customers')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2 rounded-rams-sm bg-rams-panel border border-rams-border group-hover:border-rams-orange transition-colors">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </div>
            <div>
              <p className="text-[11px] font-black uppercase tracking-tight text-foreground/80">Account_Intelligence</p>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">Manage customer nodes</p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-1 transition-all" />
        </div>

        <div 
          className="flex items-center justify-between p-6 bg-rams-module cursor-pointer hover:bg-rams-panel transition-colors group"
          onClick={() => router.push('/finance')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2 rounded-rams-sm bg-rams-panel border border-rams-border group-hover:border-rams-orange transition-colors">
              <CreditCard className="h-4 w-4 text-muted-foreground" />
            </div>
            <div>
              <p className="text-[11px] font-black uppercase tracking-tight text-foreground/80">Invoicing</p>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">Manage customer invoices</p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-1 transition-all" />
        </div>
      </div>
    </div>
  );
}
