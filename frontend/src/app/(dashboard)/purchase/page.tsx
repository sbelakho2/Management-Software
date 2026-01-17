'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useI18n } from '@/contexts/i18n-context';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
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
  Plus, 
  ShoppingCart, 
  Truck, 
  FileText, 
  Search, 
  Filter,
  MoreHorizontal,
  Eye,
  CheckCircle,
  Send,
  Package,
  ClipboardList,
  ArrowRight,
  DollarSign,
} from 'lucide-react';
import { apiClient } from '@/api/client';
import { cn, formatCurrency, formatDate } from '@/lib/utils';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

interface PurchaseOrder {
  id: string;
  po_number: string;
  supplier_id?: string;
  supplier_name?: string;
  status: 'draft' | 'pending_approval' | 'approved' | 'sent' | 'partially_received' | 'received' | 'cancelled';
  currency: string;
  total_amount: number;
  line_count: number;
  created_at: string;
  approved_at?: string;
  sent_at?: string;
}

interface PurchaseRequisition {
  id: string;
  pr_number: string;
  status: 'draft' | 'submitted' | 'approved' | 'rejected' | 'converted';
  justification?: string;
  line_count: number;
  created_at: string;
}

interface POStats {
  requisitions: {
    draft: number;
    submitted: number;
    approved: number;
  };
  orders: {
    draft: number;
    pending_approval: number;
    approved: number;
    sent: number;
  };
  receipts: {
    pending: number;
    today: number;
  };
}

const poStatusConfig: Record<PurchaseOrder['status'], { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'danger' | 'outline'; }> = {
  draft: { label: 'Draft', variant: 'secondary' },
  pending_approval: { label: 'Pending Approval', variant: 'warning' },
  approved: { label: 'Approved', variant: 'default' },
  sent: { label: 'Sent', variant: 'default' },
  partially_received: { label: 'Partial', variant: 'warning' },
  received: { label: 'Received', variant: 'success' },
  cancelled: { label: 'Cancelled', variant: 'outline' },
};

const prStatusConfig: Record<PurchaseRequisition['status'], { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'danger' | 'outline'; }> = {
  draft: { label: 'Draft', variant: 'secondary' },
  submitted: { label: 'Submitted', variant: 'warning' },
  approved: { label: 'Approved', variant: 'success' },
  rejected: { label: 'Rejected', variant: 'danger' },
  converted: { label: 'Converted to PO', variant: 'default' },
};

function StatsCards({ stats }: { stats: POStats | null }) {
  if (!stats) return null;

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Open Requisitions</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats.requisitions.submitted}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-primary/10 text-primary">
              <ClipboardList className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Pending POs</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats.orders.pending_approval + stats.orders.approved}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-warning/10 text-warning">
              <ShoppingCart className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Sent to Suppliers</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats.orders.sent}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-muted/30 text-foreground">
              <Send className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Receipts Today</p>
              <p className="text-3xl font-heading font-bold tracking-tight  mt-1">{stats.receipts.today}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-emerald-500/10 text-emerald-600">
              <Truck className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PORow({ order, onApprove, onSend }: { 
  order: PurchaseOrder; 
  onApprove: (id: string) => void;
  onSend: (id: string) => void;
}) {
  const config = poStatusConfig[order.status];

  return (
    <TableRow 
      className="transition-colors hover:bg-muted/50"
    >
      <TableCell>
        <p className="font-mono font-bold text-primary">{order.po_number}</p>
      </TableCell>
      <TableCell>
        <p className="font-medium">{order.supplier_name || 'TBD'}</p>
      </TableCell>
      <TableCell>
        <Badge variant={config.variant}>
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
            {order.status === 'pending_approval' && (
              <DropdownMenuItem onClick={() => onApprove(order.id)}>
                <CheckCircle className="mr-2 h-4 w-4 text-success" />
                Approve PO
              </DropdownMenuItem>
            )}
            {order.status === 'approved' && (
              <DropdownMenuItem onClick={() => onSend(order.id)}>
                <Send className="mr-2 h-4 w-4 text-primary" />
                Send to Supplier
              </DropdownMenuItem>
            )}
            {order.status === 'sent' && (
              <DropdownMenuItem>
                <Package className="mr-2 h-4 w-4 text-warning" />
                Record Receipt
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

export default function PurchasePage() {
  const { t } = useI18n();
  const router = useRouter();
  const [orders, setOrders] = React.useState<PurchaseOrder[]>([]);
  const [requisitions, setRequisitions] = React.useState<PurchaseRequisition[]>([]);
  const [stats, setStats] = React.useState<POStats | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [search, setSearch] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [view, setView] = React.useState<'orders' | 'requisitions'>('orders');

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const [ordersRes, reqsRes, statsRes] = await Promise.all([
        apiClient.get('/purchase/orders') as Promise<{ data: PurchaseOrder[] } | PurchaseOrder[]>,
        apiClient.get('/purchase/requisitions') as Promise<{ data: PurchaseRequisition[] } | PurchaseRequisition[]>,
        apiClient.get('/purchase/stats') as Promise<{ data: POStats } | POStats>,
      ]);
      setOrders((ordersRes as { data: PurchaseOrder[] })?.data || (ordersRes as PurchaseOrder[]) || []);
      setRequisitions((reqsRes as { data: PurchaseRequisition[] })?.data || (reqsRes as PurchaseRequisition[]) || []);
      setStats((statsRes as { data: POStats })?.data || (statsRes as POStats) || null);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleApprove = async (orderId: string) => {
    try {
      await apiClient.post(`/purchase/orders/${orderId}/approve`);
      fetchData();
    } catch (error) {
      console.error('Failed to approve order:', error);
    }
  };

  const handleSend = async (orderId: string) => {
    try {
      await apiClient.post(`/purchase/orders/${orderId}/send`);
      fetchData();
    } catch (error) {
      console.error('Failed to send order:', error);
    }
  };

  const filteredOrders = React.useMemo(() => {
    return orders.filter((order) => {
      const matchesSearch = 
        order.po_number.toLowerCase().includes(search.toLowerCase()) ||
        (order.supplier_name || '').toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === 'all' || order.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [orders, search, statusFilter]);

  const filteredRequisitions = React.useMemo(() => {
    return requisitions.filter((req) => {
      const matchesSearch = req.pr_number.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === 'all' || req.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [requisitions, search, statusFilter]);

  return (
    <div className="space-y-8 page-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight ">{t('pages.purchase.title')}</h1>
          <p className="text-muted-foreground font-medium">{t('pages.purchase.subtitle')}</p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            className="rounded-xl"
            onClick={() => router.push('/supply-chain')}
          >
            <Truck className="mr-2 h-4 w-4" />
            Suppliers
          </Button>
          <Button 
            className="rounded-xl shadow-glow"
            onClick={() => router.push('/purchase/requisitions/new')}
          >
            <Plus className="mr-2 h-4 w-4" />
            New Requisition
          </Button>
        </div>
      </div>

      {/* Stats */}
      <StatsCards stats={stats} />

      {/* View Toggle */}
      <div className="flex items-center gap-4">
        <div className="flex rounded-xl overflow-hidden border border-border">
          <Button 
            variant={view === 'orders' ? 'default' : 'ghost'} 
            className="rounded-none"
            onClick={() => setView('orders')}
          >
            <ShoppingCart className="mr-2 h-4 w-4" />
            Purchase Orders
          </Button>
          <Button 
            variant={view === 'requisitions' ? 'default' : 'ghost'} 
            className="rounded-none"
            onClick={() => setView('requisitions')}
          >
            <ClipboardList className="mr-2 h-4 w-4" />
            Requisitions
          </Button>
        </div>
        <div className="flex-1" />
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder={`Search ${view}...`}
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
            {view === 'orders' ? (
              <>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="pending_approval">Pending Approval</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="sent">Sent</SelectItem>
                <SelectItem value="partially_received">Partially Received</SelectItem>
                <SelectItem value="received">Received</SelectItem>
              </>
            ) : (
              <>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="submitted">Submitted</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
                <SelectItem value="converted">Converted</SelectItem>
              </>
            )}
          </SelectContent>
        </Select>
      </div>

      {/* Data Table */}
      <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium overflow-hidden">
        {view === 'orders' ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>PO Number</TableHead>
                <TableHead>Supplier</TableHead>
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
                      <ShoppingCart className="h-12 w-12 text-muted-foreground/50" />
                      <div>
                        <p className="font-medium">No purchase orders found</p>
                        <p className="text-sm text-muted-foreground">Create a requisition first</p>
                      </div>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                filteredOrders.map((order) => (
                  <PORow 
                    key={order.id} 
                    order={order}
                    onApprove={handleApprove}
                    onSend={handleSend}
                  />
                ))
              )}
            </TableBody>
          </Table>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>PR Number</TableHead>
                <TableHead>Justification</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-center">Lines</TableHead>
                <TableHead>Date</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-16">
                    <div className="flex flex-col items-center gap-3">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                      <p className="text-muted-foreground">Loading requisitions...</p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : filteredRequisitions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-16">
                    <div className="flex flex-col items-center gap-3">
                      <ClipboardList className="h-12 w-12 text-muted-foreground/50" />
                      <div>
                        <p className="font-medium">No requisitions found</p>
                        <p className="text-sm text-muted-foreground">Create your first purchase requisition</p>
                      </div>
                      <Button 
                        className="mt-2 rounded-xl"
                        onClick={() => router.push('/purchase/requisitions/new')}
                      >
                        <Plus className="mr-2 h-4 w-4" />
                        New Requisition
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                filteredRequisitions.map((req) => {
                  const config = prStatusConfig[req.status];
                  return (
                    <TableRow 
                      key={req.id}
                      className="transition-colors hover:bg-muted/50"
                    >
                      <TableCell>
                        <p className="font-mono font-bold text-primary">{req.pr_number}</p>
                      </TableCell>
                      <TableCell>
                        <p className="truncate max-w-xs">{req.justification || '-'}</p>
                      </TableCell>
                      <TableCell>
                        <Badge variant={config.variant}>
                          {config.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <span className="text-muted-foreground">{req.line_count}</span>
                      </TableCell>
                      <TableCell>
                        {formatDate(new Date(req.created_at))}
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        <div 
          className="flex items-center justify-between p-4 rounded-2xl bg-muted/20 border border-border/10 hover:bg-muted/30 transition-colors cursor-pointer"
          onClick={() => router.push('/mrp/mps')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-bold">MRP Suggestions</div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Convert MRP buy suggestions to PRs</div>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </div>
        <div 
          className="flex items-center justify-between p-4 rounded-2xl bg-muted/20 border border-border/10 hover:bg-muted/30 transition-colors cursor-pointer"
          onClick={() => router.push('/warehouse')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-600">
              <Package className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-bold">Goods Receipt</div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Record incoming shipments</div>
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
              <DollarSign className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-bold">3-Way Matching</div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">PO, GRN & Invoice reconciliation</div>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
    </div>
  );
}
