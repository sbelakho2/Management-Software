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
    <div className="grid gap-0 md:grid-cols-4 border border-rams-border bg-rams-border">
      <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Open Requisitions</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.requisitions.submitted}</p>
        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">WAITING_FOR_ACTION</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Pending Orders</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{stats.orders.pending_approval + stats.orders.approved}</p>
        <p className="text-[9px] font-mono font-bold text-rams-orange uppercase tracking-widest mt-2">GATE_SYNC_REQUIRED</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0 group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Sent to Suppliers</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.orders.sent}</p>
        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">ACTIVE_TRANSMISSIONS</p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-border group">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Receipts Today</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{stats.receipts.today}</p>
        <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">DUE_HORIZON_TODAY</p>
      </div>
    </div>
  );
}

function PORow({ order, onApprove, onSend }: { 
  order: PurchaseOrder; 
  onApprove: (id: string) => void;
  onSend: (id: string) => void;
}) {
  const router = useRouter();
  const config = poStatusConfig[order.status];

  return (
    <TableRow 
      className="transition-none cursor-pointer group"
      onClick={() => router.push(`/purchase/orders/${order.id}`)}
    >
      <TableCell>
        <div>
          <p className="font-mono font-bold text-rams-orange tabular-nums">{order.po_number}</p>
          <p className="text-[9px] font-mono uppercase tracking-tight text-muted-foreground/40">PO_NODE</p>
        </div>
      </TableCell>
      <TableCell>
        <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{order.supplier_name || 'UNKNOWN_SUPPLIER'}</p>
      </TableCell>
      <TableCell>
        <Badge variant={config.variant} size="sm">
          {config.label.toUpperCase()}
        </Badge>
      </TableCell>
      <TableCell className="text-right">
        <span className="font-mono font-bold tabular-nums text-foreground/90">
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
            <DropdownMenuItem onClick={() => router.push(`/purchase/orders/${order.id}`)}>
              <Eye className="mr-2 h-3.5 w-3.5" />
              ANALYZE
            </DropdownMenuItem>
            {order.status === 'pending_approval' && (
              <DropdownMenuItem onClick={() => onApprove(order.id)}>
                <CheckCircle className="mr-2 h-3.5 w-3.5 text-rams-green" />
                APPROVE_GATE
              </DropdownMenuItem>
            )}
            {order.status === 'approved' && (
              <DropdownMenuItem onClick={() => onSend(order.id)}>
                <Send className="mr-2 h-3.5 w-3.5 text-rams-orange" />
                TRANSMIT_TO_SUPPLIER
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Package className="mr-2 h-3.5 w-3.5" />
              RECORD_RECEIPT
            </DropdownMenuItem>
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
    <div className="space-y-8 page-fade-in pb-12" data-testid="purchase-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.purchase.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.purchase.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: PROCUREMENT-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-border" onClick={() => router.push('/supply-chain')}>
            <Truck className="mr-2 h-3.5 w-3.5" />
            Suppliers
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]" onClick={() => router.push('/purchase/requisitions/new')}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            Initialize Requisition
          </Button>
        </div>
      </div>

      {/* Stats */}
      <StatsCards stats={stats} />

      {/* Filters and Toggle */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 items-center gap-4 flex-wrap max-w-4xl">
          <div className="flex bg-rams-panel p-1 border border-rams-border rounded-rams-sm">
            <Button 
              variant={view === 'orders' ? 'default' : 'ghost'} 
              size="sm"
              className={cn("h-8 px-3 rounded-none", view === 'orders' ? "bg-rams-orange text-black font-black" : "text-muted-foreground/60")}
              onClick={() => setView('orders')}
            >
              <ShoppingCart className="mr-2 h-3.5 w-3.5" />
              ORDERS
            </Button>
            <Button 
              variant={view === 'requisitions' ? 'default' : 'ghost'} 
              size="sm"
              className={cn("h-8 px-3 rounded-none", view === 'requisitions' ? "bg-rams-orange text-black font-black" : "text-muted-foreground/60")}
              onClick={() => setView('requisitions')}
            >
              <ClipboardList className="mr-2 h-3.5 w-3.5" />
              REQUISITIONS
            </Button>
          </div>

          <div className="relative flex-1 min-w-[240px] group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 transition-colors group-focus-within:text-rams-orange" />
            <Input 
              placeholder={`SEARCH_${view.toUpperCase()}...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 h-10 text-[10px]"
            />
          </div>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px] h-10 text-[10px]">
              <Filter className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder="STATUS_STATE" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">ALL_STATUS</SelectItem>
              {view === 'orders' ? (
                <>
                  <SelectItem value="draft">DRAFT_NODE</SelectItem>
                  <SelectItem value="pending_approval">GATE_APPROVAL</SelectItem>
                  <SelectItem value="approved">APPROVED_SYNC</SelectItem>
                  <SelectItem value="sent">TRANSMITTED</SelectItem>
                  <SelectItem value="received">RECEIVED</SelectItem>
                </>
              ) : (
                <>
                  <SelectItem value="draft">DRAFT_NODE</SelectItem>
                  <SelectItem value="submitted">SUBMITTED</SelectItem>
                  <SelectItem value="approved">APPROVED_SYNC</SelectItem>
                  <SelectItem value="converted">CONVERTED</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Data Table */}
      <Card className="rounded-rams-sm overflow-hidden border-rams-border shadow-none">
        {view === 'orders' ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ORDER_ID</TableHead>
                  <TableHead>SUPPLIER_NODE</TableHead>
                  <TableHead>STATUS_STATE</TableHead>
                  <TableHead className="text-right">TOTAL_VALUE</TableHead>
                  <TableHead className="text-center">LINES</TableHead>
                  <TableHead>TIMESTAMP</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-16">
                      <div className="flex flex-col items-center gap-3">
                        <div className="animate-spin rounded-none h-8 w-8 border border-rams-orange border-t-transparent"></div>
                        <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">Synchronizing Orders...</p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : filteredOrders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-16">
                      <div className="flex flex-col items-center gap-3">
                        <ShoppingCart className="h-12 w-12 text-muted-foreground/20" />
                        <div>
                          <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">Zero orders identified</p>
                          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">Initialize requisition protocol first</p>
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
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>REQ_NUMBER</TableHead>
                  <TableHead>JUSTIFICATION_LOG</TableHead>
                  <TableHead>STATUS_STATE</TableHead>
                  <TableHead className="text-center">LINES</TableHead>
                  <TableHead>TIMESTAMP</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-16">
                      <div className="flex flex-col items-center gap-3">
                        <div className="animate-spin rounded-none h-8 w-8 border border-rams-orange border-t-transparent"></div>
                        <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">Synchronizing Requisitions...</p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : filteredRequisitions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-16">
                      <div className="flex flex-col items-center gap-3">
                        <ClipboardList className="h-12 w-12 text-muted-foreground/20" />
                        <div>
                          <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">Zero requisitions identified</p>
                          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">Initialize first requisition protocol</p>
                        </div>
                        <Button 
                          className="mt-4 rounded-rams-sm"
                          onClick={() => router.push('/purchase/requisitions/new')}
                        >
                          <Plus className="mr-2 h-3.5 w-3.5" />
                          Initialize Requisition
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
                        className="transition-none cursor-pointer group"
                        onClick={() => router.push(`/purchase/requisitions/${req.id}`)}
                      >
                        <TableCell>
                          <p className="font-mono font-bold text-rams-orange tabular-nums">{req.pr_number}</p>
                        </TableCell>
                        <TableCell>
                          <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none truncate max-w-xs">{req.justification || '-'}</p>
                        </TableCell>
                        <TableCell>
                          <Badge variant={config.variant} size="sm">
                            {config.label.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center font-mono text-[10px] text-muted-foreground/40">
                          {req.line_count}
                        </TableCell>
                        <TableCell className="font-mono text-[10px] text-muted-foreground/60 uppercase">
                          {formatDate(new Date(req.created_at))}
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Button variant="ghost" size="icon" className="h-8 w-8 rounded-rams-sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-0 md:grid-cols-3 border border-rams-border bg-rams-border">
        <div 
          className="flex items-center justify-between p-6 bg-rams-module border-r border-rams-border cursor-pointer hover:bg-rams-panel transition-none group"
          onClick={() => router.push('/mrp/mps')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2 rounded-rams-sm bg-rams-panel border border-rams-border group-hover:border-rams-orange transition-none">
              <FileText className="h-4 w-4 text-muted-foreground" />
            </div>
            <div>
              <p className="text-[11px] font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">MRP_INTELLIGENCE</p>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-0.5">Convert suggestions to PRs</p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-1 transition-all" />
        </div>
        
        <div 
          className="flex items-center justify-between p-6 bg-rams-module border-r border-rams-border cursor-pointer hover:bg-rams-panel transition-none group"
          onClick={() => router.push('/warehouse')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2 rounded-rams-sm bg-rams-panel border border-rams-border group-hover:border-rams-orange transition-none">
              <Package className="h-4 w-4 text-muted-foreground" />
            </div>
            <div>
              <p className="text-[11px] font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">GOODS_RECEIPT</p>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-0.5">Record incoming shipments</p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-1 transition-all" />
        </div>

        <div 
          className="flex items-center justify-between p-6 bg-rams-module cursor-pointer hover:bg-rams-panel transition-none group"
          onClick={() => router.push('/finance')}
        >
          <div className="flex items-center gap-4">
            <div className="p-2 rounded-rams-sm bg-rams-panel border border-rams-border group-hover:border-rams-orange transition-none">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </div>
            <div>
              <p className="text-[11px] font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">3-WAY_MATCHING</p>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-0.5">PO, GRN & Invoice sync</p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-1 transition-all" />
        </div>
      </div>
    </div>
  );
}
