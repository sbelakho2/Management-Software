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
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import Link from 'next/link';
import { hasPageAccess } from '@/lib/page-access';
import { useAuthStore } from '@/stores';
import { UserRole } from '@/types';

// Demo data - in production, this would come from API
const inventoryStats = {
  totalItems: 12450,
  lowStock: 23,
  outOfStock: 4,
  pendingReceipts: 12,
  pendingShipments: 28,
  inventoryValue: 2450000,
};

const recentMovements = [
  { id: 1, type: 'in', item: 'Steel Plate 4mm', quantity: 500, location: 'Zone A-3', time: '10 min ago' },
  { id: 2, type: 'out', item: 'Aluminum Bar 25mm', quantity: 100, location: 'Zone B-1', time: '25 min ago' },
  { id: 3, type: 'in', item: 'Fastener Kit M8', quantity: 1000, location: 'Zone C-2', time: '1 hour ago' },
  { id: 4, type: 'out', item: 'Copper Wire 2mm', quantity: 200, location: 'Zone A-1', time: '2 hours ago' },
];

const lowStockItems = [
  { id: 1, name: 'Bearing 6205-2RS', current: 12, reorder: 50, unit: 'pcs' },
  { id: 2, name: 'Hydraulic Fluid ISO 46', current: 5, reorder: 20, unit: 'L' },
  { id: 3, name: 'Safety Gloves XL', current: 8, reorder: 30, unit: 'pairs' },
  { id: 4, name: 'Welding Wire 1.2mm', current: 3, reorder: 15, unit: 'kg' },
];

export default function WarehouseDashboard() {
  const { t } = useI18n();
  const { user } = useAuthStore();

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);

  return (
    <div className="space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.warehouse.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.warehouse.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: WAREHOUSE-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasPageAccess('/warehouse/sync', userRoles) && (
            <Button variant="outline" size="default" className="rounded-rams-sm">
              <RefreshCw className="h-3.5 w-3.5 mr-2" />
              Sync Real-time Stock
            </Button>
          )}
          {hasPageAccess('/supply-chain', userRoles) && (
            <Button size="default" className="rounded-rams-sm" asChild>
              <Link href="/supply-chain">
                <Package className="h-3.5 w-3.5 mr-2" />
                Inventory Command
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className="flex items-center justify-end">
        <AmbientStatus 
          status={inventoryStats.outOfStock > 0 ? 'warning' : 'operational'} 
          label={inventoryStats.outOfStock > 0 ? `${inventoryStats.outOfStock} Items Out of Stock` : 'All Stock Levels Normal'}
        />
      </div>

      {/* Stats Grid - Using Shared StatCard */}
      <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-border bg-rams-border">
        <StatCard
          value={inventoryStats.totalItems.toLocaleString()}
          label="Inventory Nodes (SKUs)"
          icon={Box}
          iconColor="primary"
          trend="up"
          trendValue="+124 this cycle"
          className="rounded-none border-0 border-r border-b"
        />
        <StatCard
          value={inventoryStats.lowStock}
          label="Abnormal Stock Levels"
          icon={AlertTriangle}
          iconColor="warning"
          critical={inventoryStats.lowStock > 20}
          className="rounded-none border-0 border-r border-b"
        />
        <StatCard
          value={inventoryStats.pendingReceipts}
          label="Inbound Synchronization"
          icon={Truck}
          iconColor="info"
          className="rounded-none border-0 border-r border-b"
        />
        <StatCard
          value={inventoryStats.pendingShipments}
          label="Outbound Velocity"
          icon={Package}
          iconColor="success"
          className="rounded-none border-0 border-b"
        />
      </div>

      {/* Main Content */}
      <div className="grid gap-8 lg:grid-cols-2">
        {/* Recent Movements */}
        <Card className="rounded-rams-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Recent Movements
            </CardTitle>
            <CardDescription>Latest inventory transactions</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-border/30">
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
              Low Stock Alerts
            </CardTitle>
            <CardDescription className="text-rams-red/60">Items below reorder point</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {lowStockItems.map((item) => (
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
                  View All Low Stock Items
                </Link>
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
