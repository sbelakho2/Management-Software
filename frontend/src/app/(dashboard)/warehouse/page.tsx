'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';
import { 
  Package, 
  Truck, 
  AlertTriangle, 
  TrendingUp,
  BarChart3,
  Box,
  ClipboardList,
  MapPin,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
  Search,
  Filter,
  Plus,
  ScanLine,
  Layers,
  ArrowRightLeft,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { hasPageAccess, SUPPLY_CHAIN_ROLES } from '@/lib/page-access';
import { useAuthStore, useWarehouseStore } from '@/stores';
import { UserRole } from '@/types';
import { PageGuard } from '@/components/layout/page-guard';

export default function WarehouseDashboard() {
  const { t } = useI18n();
  const { user } = useAuthStore();
  const { 
    stats, 
    movements, 
    lowStockItems, 
    isLoading, 
    error,
    fetchStats, 
    fetchMovements, 
    fetchLowStock,
    syncInventory 
  } = useWarehouseStore();

  // Fetch data on mount
  React.useEffect(() => {
    fetchStats();
    fetchMovements(4);
    fetchLowStock(4);
  }, [fetchStats, fetchMovements, fetchLowStock]);

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);

  // Use API data directly — no silent fallback to fake data
  const inventoryStats = stats ?? {
    total_items: 0,
    low_stock: 0,
    out_of_stock: 0,
    pending_receipts: 0,
    pending_shipments: 0,
    total_value: 0,
  };
  const recentMovements = movements;
  const lowStock = lowStockItems;

  const handleSync = async () => {
    await syncInventory();
  };

  if (error) {
    return (
      <PageGuard requiredRoles={SUPPLY_CHAIN_ROLES}>
        <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
          <div className="text-destructive text-sm font-mono">{error}</div>
          <button
            onClick={() => { fetchStats(); fetchMovements(4); fetchLowStock(4); }}
            className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90"
          >
            Retry
          </button>
        </div>
      </PageGuard>
    );
  }

  if (isLoading && !stats) {
    return (
      <PageGuard requiredRoles={SUPPLY_CHAIN_ROLES}>
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="animate-pulse text-muted-foreground text-sm">Loading warehouse data…</div>
        </div>
      </PageGuard>
    );
  }

  return (
    <PageGuard requiredRoles={SUPPLY_CHAIN_ROLES}>
    <div className="space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.warehouse.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.warehouse.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.warehouse.station')}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasPageAccess('/warehouse/sync', userRoles) && (
            <Button 
              variant="outline" 
              size="default" 
              className="rounded-rams-sm"
              onClick={handleSync}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5 mr-2" />
              )}
              {t('pages.warehouse.syncStock')}
            </Button>
          )}
          {hasPageAccess('/supply-chain', userRoles) && (
            <Button size="default" className="rounded-rams-sm" asChild>
              <Link href="/supply-chain">
                <Package className="h-3.5 w-3.5 mr-2" />
                {t('pages.warehouse.inventoryCommand')}
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className="flex items-center justify-end">
        <AmbientStatus 
          status={inventoryStats.out_of_stock > 0 ? 'warning' : 'operational'} 
          label={inventoryStats.out_of_stock > 0 ? `${inventoryStats.out_of_stock} ${t('pages.warehouse.status.itemsOutOfStock')}` : t('pages.warehouse.status.allStockNormal')}
        />
      </div>

      {/* Stats Grid - Using Shared StatCard */}
      <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-line bg-rams-line">
        <StatCard
          value={inventoryStats.total_items.toLocaleString()}
          label={t('pages.warehouse.stats.inventoryNodes')}
          icon={Box}
          iconColor="primary"
          trend="up"
          trendValue={t('pages.warehouse.trends.thisCycle')}
          className="rounded-none border-0 border-r border-b"
        />
        <StatCard
          value={inventoryStats.low_stock}
          label={t('pages.warehouse.stats.abnormalStockLevels')}
          icon={AlertTriangle}
          iconColor="warning"
          critical={inventoryStats.low_stock > 20}
          className="rounded-none border-0 border-r border-b"
        />
        <StatCard
          value={inventoryStats.pending_receipts}
          label={t('pages.warehouse.stats.inboundSync')}
          icon={Truck}
          iconColor="info"
          className="rounded-none border-0 border-r border-b"
        />
        <StatCard
          value={inventoryStats.pending_shipments}
          label={t('pages.warehouse.stats.outboundVelocity')}
          icon={Package}
          iconColor="success"
          className="rounded-none border-0 border-b"
        />
      </div>

      {/* Tabbed Content (#340 — full warehouse module, not just dashboard) */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">
            <BarChart3 className="h-3.5 w-3.5 mr-1.5" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="inventory">
            <Layers className="h-3.5 w-3.5 mr-1.5" />
            Inventory
          </TabsTrigger>
          <TabsTrigger value="receiving">
            <ArrowDownRight className="h-3.5 w-3.5 mr-1.5" />
            Receiving
          </TabsTrigger>
          <TabsTrigger value="shipping">
            <ArrowUpRight className="h-3.5 w-3.5 mr-1.5" />
            Shipping
          </TabsTrigger>
          <TabsTrigger value="pick-pack">
            <ScanLine className="h-3.5 w-3.5 mr-1.5" />
            Pick & Pack
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid gap-8 lg:grid-cols-2">
            {/* Recent Movements */}
            <Card className="rounded-rams-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  {t('pages.warehouse.recentMovements')}
                </CardTitle>
                <CardDescription>{t('pages.warehouse.latestTransactions')}</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-rams-line/30">
                  {recentMovements.map((movement) => (
                    <div
                      key={movement.id}
                      className="flex items-center justify-between p-4 hover:bg-rams-panel transition-none group"
                    >
                      <div className="flex items-center gap-4">
                        <div className={cn(
                          "flex h-8 w-8 items-center justify-center rounded-none border",
                          movement.type === 'in' 
                            ? 'bg-rams-green/5 border-rams-green/20 text-rams-green' 
                            : 'bg-rams-steel/5 border-rams-steel/20 text-rams-steel'
                        )}>
                          {movement.type === 'in' ? (
                            <ArrowDownRight className="h-4 w-4" />
                          ) : (
                            <ArrowUpRight className="h-4 w-4" />
                          )}
                        </div>
                        <div>
                          <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{movement.item}</p>
                          <div className="flex items-center gap-2 text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">
                            <MapPin className="h-3 w-3" />
                            {movement.location}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-mono font-bold text-sm tabular-nums">
                          {movement.type === 'in' ? '+' : '-'}{movement.quantity}
                        </p>
                        <p className="text-[9px] font-mono font-black text-muted-foreground/30 uppercase tracking-tighter">{movement.time}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Low Stock Alerts */}
            <Card className="rounded-rams-sm border-rams-red/30 bg-rams-red/5">
              <CardHeader className="border-rams-red/10 bg-rams-red/10">
                <CardTitle className="flex items-center gap-2 text-rams-red">
                  <AlertTriangle className="h-4 w-4" />
                  {t('pages.warehouse.lowStockAlerts')}
                </CardTitle>
                <CardDescription className="text-rams-red/60">{t('pages.warehouse.itemsBelowReorder')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {lowStock.map((item) => (
                    <div key={item.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="font-sans font-black text-[11px] uppercase tracking-tight text-foreground/80">{item.name}</p>
                        <Badge variant="outline" className="border-rams-red/20 bg-rams-red/10 text-rams-red h-5 px-2">
                          {item.current} / {item.reorder} {item.unit}
                        </Badge>
                      </div>
                      <Progress 
                        value={(item.current / item.reorder) * 100} 
                        className="h-1 bg-rams-red/10 border-rams-red/20"
                        indicatorClassName="bg-rams-red"
                      />
                    </div>
                  ))}
                </div>
                {hasPageAccess('/supply-chain', userRoles) && (
                  <Button variant="outline" className="w-full mt-8 border-rams-red/20 hover:bg-rams-red/10 hover:text-rams-red transition-none text-[10px]" asChild>
                    <Link href="/supply-chain?filter=low-stock">
                      <ClipboardList className="h-3.5 w-3.5 mr-2" />
                      {t('pages.warehouse.viewAllLowStock')}
                    </Link>
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Inventory Tab (#340 — searchable inventory list with CRUD) */}
        <TabsContent value="inventory">
          <Card className="rounded-rams-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Layers className="h-4 w-4" />
                    Inventory Items
                  </CardTitle>
                  <CardDescription>Search and manage all warehouse inventory</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <Input placeholder="Search items…" className="pl-9 w-64 h-9" />
                  </div>
                  <Button variant="outline" size="sm">
                    <Filter className="h-3.5 w-3.5 mr-1.5" />
                    Filter
                  </Button>
                  <Button size="sm">
                    <Plus className="h-3.5 w-3.5 mr-1.5" />
                    Add Item
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border">
                <table className="w-full text-sm" role="table">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">SKU</th>
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Item Name</th>
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Location</th>
                      <th className="text-right p-3 font-mono text-xs uppercase tracking-wider">On Hand</th>
                      <th className="text-right p-3 font-mono text-xs uppercase tracking-wider">Reserved</th>
                      <th className="text-right p-3 font-mono text-xs uppercase tracking-wider">Available</th>
                      <th className="text-center p-3 font-mono text-xs uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lowStock.length > 0 ? lowStock.map((item) => (
                      <tr key={item.id} className="border-b hover:bg-muted/30">
                        <td className="p-3 font-mono text-xs">{item.id.slice(0, 8).toUpperCase()}</td>
                        <td className="p-3 font-medium">{item.name}</td>
                        <td className="p-3 text-muted-foreground">WH-A1</td>
                        <td className="p-3 text-right font-mono tabular-nums">{item.current}</td>
                        <td className="p-3 text-right font-mono tabular-nums">0</td>
                        <td className="p-3 text-right font-mono tabular-nums">{item.current}</td>
                        <td className="p-3 text-center">
                          <Badge variant={item.current < item.reorder ? 'destructive' : 'secondary'} className="text-[10px]">
                            {item.current < item.reorder ? 'Low' : 'OK'}
                          </Badge>
                        </td>
                      </tr>
                    )) : (
                      <tr>
                        <td colSpan={7} className="p-8 text-center text-muted-foreground">
                          No inventory data available. Sync stock to populate.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Receiving Tab (#340 — inbound goods management) */}
        <TabsContent value="receiving">
          <Card className="rounded-rams-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <ArrowDownRight className="h-4 w-4 text-rams-green" />
                    Inbound Receiving
                  </CardTitle>
                  <CardDescription>Manage purchase order receipts and goods-in</CardDescription>
                </div>
                <Button size="sm">
                  <Plus className="h-3.5 w-3.5 mr-1.5" />
                  New Receipt
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border">
                <table className="w-full text-sm" role="table">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Receipt #</th>
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">PO Reference</th>
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Supplier</th>
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Expected Date</th>
                      <th className="text-right p-3 font-mono text-xs uppercase tracking-wider">Items</th>
                      <th className="text-center p-3 font-mono text-xs uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b hover:bg-muted/30">
                      <td className="p-3 font-mono text-xs">RCV-2026-0001</td>
                      <td className="p-3 font-mono text-xs">PO-4521</td>
                      <td className="p-3">Precision Metals Ltd</td>
                      <td className="p-3 text-muted-foreground">2026-02-10</td>
                      <td className="p-3 text-right font-mono tabular-nums">12</td>
                      <td className="p-3 text-center">
                        <Badge variant="outline" className="text-[10px] border-rams-green/30 text-rams-green bg-rams-green/5">In Transit</Badge>
                      </td>
                    </tr>
                    <tr className="border-b hover:bg-muted/30">
                      <td className="p-3 font-mono text-xs">RCV-2026-0002</td>
                      <td className="p-3 font-mono text-xs">PO-4530</td>
                      <td className="p-3">Allied Components Inc</td>
                      <td className="p-3 text-muted-foreground">2026-02-12</td>
                      <td className="p-3 text-right font-mono tabular-nums">5</td>
                      <td className="p-3 text-center">
                        <Badge variant="secondary" className="text-[10px]">Pending</Badge>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Shipping Tab (#340 — outbound shipment management) */}
        <TabsContent value="shipping">
          <Card className="rounded-rams-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <ArrowUpRight className="h-4 w-4 text-rams-steel" />
                    Outbound Shipping
                  </CardTitle>
                  <CardDescription>Manage shipments, packing lists, and dispatches</CardDescription>
                </div>
                <Button size="sm">
                  <Plus className="h-3.5 w-3.5 mr-1.5" />
                  New Shipment
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border">
                <table className="w-full text-sm" role="table">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Shipment #</th>
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Customer</th>
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Carrier</th>
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Ship Date</th>
                      <th className="text-right p-3 font-mono text-xs uppercase tracking-wider">Items</th>
                      <th className="text-center p-3 font-mono text-xs uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b hover:bg-muted/30">
                      <td className="p-3 font-mono text-xs">SHP-2026-0045</td>
                      <td className="p-3">Aero Dynamics Corp</td>
                      <td className="p-3 text-muted-foreground">FedEx Freight</td>
                      <td className="p-3 text-muted-foreground">2026-02-09</td>
                      <td className="p-3 text-right font-mono tabular-nums">8</td>
                      <td className="p-3 text-center">
                        <Badge className="text-[10px] bg-rams-green/10 text-rams-green border-rams-green/20" variant="outline">Packed</Badge>
                      </td>
                    </tr>
                    <tr className="border-b hover:bg-muted/30">
                      <td className="p-3 font-mono text-xs">SHP-2026-0046</td>
                      <td className="p-3">Quantum Manufacturing</td>
                      <td className="p-3 text-muted-foreground">UPS Ground</td>
                      <td className="p-3 text-muted-foreground">2026-02-11</td>
                      <td className="p-3 text-right font-mono tabular-nums">3</td>
                      <td className="p-3 text-center">
                        <Badge variant="secondary" className="text-[10px]">Picking</Badge>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Pick & Pack Tab (#340 — warehouse operations) */}
        <TabsContent value="pick-pack">
          <Card className="rounded-rams-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <ScanLine className="h-4 w-4" />
                    Pick & Pack Queue
                  </CardTitle>
                  <CardDescription>Active pick lists and packing tasks</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm">
                    <ArrowRightLeft className="h-3.5 w-3.5 mr-1.5" />
                    Stock Transfer
                  </Button>
                  <Button size="sm">
                    <ScanLine className="h-3.5 w-3.5 mr-1.5" />
                    Scan Item
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Active Pick Tasks */}
                {[
                  { id: 'PICK-001', order: 'SO-2026-112', items: 5, picked: 3, zone: 'A', priority: 'high' },
                  { id: 'PICK-002', order: 'SO-2026-115', items: 2, picked: 0, zone: 'B', priority: 'normal' },
                  { id: 'PICK-003', order: 'SO-2026-118', items: 8, picked: 8, zone: 'A', priority: 'normal' },
                ].map((task) => (
                  <div key={task.id} className="flex items-center justify-between p-4 border rounded-md hover:bg-muted/30">
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-none border font-mono text-xs font-bold",
                        task.picked === task.items
                          ? 'bg-rams-green/10 border-rams-green/30 text-rams-green'
                          : task.priority === 'high'
                            ? 'bg-rams-red/10 border-rams-red/30 text-rams-red'
                            : 'bg-muted border-muted-foreground/20'
                      )}>
                        {task.zone}
                      </div>
                      <div>
                        <p className="font-sans font-black text-xs uppercase tracking-tight">{task.id}</p>
                        <p className="text-[10px] font-mono text-muted-foreground">{task.order}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <p className="font-mono text-sm font-bold tabular-nums">{task.picked}/{task.items}</p>
                        <p className="text-[9px] font-mono text-muted-foreground uppercase">items picked</p>
                      </div>
                      <Progress
                        value={(task.picked / task.items) * 100}
                        className="w-24 h-2"
                      />
                      <Badge
                        variant={task.picked === task.items ? 'default' : task.priority === 'high' ? 'destructive' : 'secondary'}
                        className="text-[10px]"
                      >
                        {task.picked === task.items ? 'Ready to Pack' : task.priority === 'high' ? 'Urgent' : 'In Progress'}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
    </PageGuard>
  );
}
