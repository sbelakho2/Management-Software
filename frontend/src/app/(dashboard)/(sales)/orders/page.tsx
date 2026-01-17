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
    <div className="grid gap-4 md:grid-cols-4">
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Draft Orders</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats.orders.draft}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-muted/20 text-muted-foreground">
              <FileText className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Approved</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats.orders.approved}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-primary/10 text-primary">
              <CheckCircle className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Released</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats.orders.released}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-warning/10 text-warning">
              <Package className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Overdue Invoices</p>
              <p className="text-3xl font-heading font-bold tracking-tight text-danger mt-1">{stats.invoices.overdue}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-danger/10 text-danger">
              <CreditCard className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
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
      className="transition-colors hover:bg-muted/50"
    >
      <TableCell>
        <div>
          <p className="font-mono font-bold text-primary">{order.so_number}</p>
          {order.source_quote_id && (
            <Link 
              href={`/quotes/${order.source_quote_id}`}
              className="text-xs text-muted-foreground hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              From Quote
            </Link>
          )}
        </div>
      </TableCell>
      <TableCell>
        <Link 
          href={`/customers/${order.account_id}`}
          className="font-medium hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {order.account_name || 'Unknown'}
        </Link>
      </TableCell>
      <TableCell>
        <Badge variant={config.variant} className="gap-1">
          <StatusIcon className="h-3 w-3" />
          {config.label}
        </Badge>
      </TableCell>
      <TableCell className="text-right">
        <span className="font-heading font-bold">
          {formatCurrency(order.total_amount, order.currency)}
        </span>
      </TableCell>
      <TableCell className="text-center">
        <span className="text-muted-foreground">{order.line_count}</span>
      </TableCell>
      <TableCell>
        {formatDate(new Date(order.created_at))}
      </TableCell>
      <TableCell onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            {order.status === 'draft' && (
              <DropdownMenuItem onClick={() => onApprove(order.id)}>
                <CheckCircle className="mr-2 h-4 w-4 text-success" />
                Approve Order
              </DropdownMenuItem>
            )}
            {order.status === 'approved' && (
              <DropdownMenuItem onClick={() => onRelease(order.id)}>
                <Package className="mr-2 h-4 w-4 text-warning" />
                Release to Production
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <CreditCard className="mr-2 h-4 w-4" />
              Create Invoice
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

export default function SalesOrdersPage() {
  const router = useRouter();
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
    <div className="space-y-8 page-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight ">{t('pages.orders.title')}</h1>
          <p className="text-muted-foreground font-medium">{t('pages.orders.subtitle')}</p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            className="rounded-xl"
            onClick={() => router.push('/quotes')}
          >
            <FileText className="mr-2 h-4 w-4" />
            Quotes
          </Button>
          <Button 
            className="rounded-xl shadow-glow"
            onClick={() => router.push('/quotes/new')}
          >
            <Plus className="mr-2 h-4 w-4" />
            New Order
          </Button>
        </div>
      </div>

      {/* Stats */}
      <OrderStats stats={stats} />

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search orders..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10 rounded-xl"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px] rounded-xl">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="released">Released</SelectItem>
            <SelectItem value="shipped">Shipped</SelectItem>
            <SelectItem value="invoiced">Invoiced</SelectItem>
            <SelectItem value="closed">Closed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Orders Table */}
      <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Order</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead className="text-center">Lines</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-16">
                  <div className="flex flex-col items-center gap-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                    <p className="text-muted-foreground">Loading orders...</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : filteredOrders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-16">
                  <div className="flex flex-col items-center gap-3">
                    <Package className="h-12 w-12 text-muted-foreground/50" />
                    <div>
                      <p className="font-medium">No sales orders found</p>
                      <p className="text-sm text-muted-foreground">
                        {search || statusFilter !== 'all' 
                          ? 'Try adjusting your filters' 
                          : 'Create your first order or convert a quote'}
                      </p>
                    </div>
                    <Button 
                      className="mt-2 rounded-xl"
                      onClick={() => router.push('/quotes/new')}
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Create Order
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
      <div className="grid gap-4 md:grid-cols-3">
        <div 
          className="flex items-center justify-between p-4 rounded-2xl bg-muted/20 border border-border/10 hover:bg-muted/30 transition-colors cursor-pointer"
          onClick={() => router.push('/quotes')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-bold">Convert Quotes</div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Turn accepted quotes into orders</div>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </div>
        <div 
          className="flex items-center justify-between p-4 rounded-2xl bg-muted/20 border border-border/10 hover:bg-muted/30 transition-colors cursor-pointer"
          onClick={() => router.push('/customers')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-600">
              <TrendingUp className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-bold">Customer Credit</div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Check credit limits and balances</div>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </div>
        <div 
          className="flex items-center justify-between p-4 rounded-2xl bg-muted/20 border border-border/10 hover:bg-muted/30 transition-colors cursor-pointer"
          onClick={() => router.push('/finance')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2.5 rounded-xl bg-warning/10 text-warning">
              <CreditCard className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-bold">Invoicing</div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Manage customer invoices</div>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
    </div>
  );
}
