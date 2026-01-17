'use client';

import * as React from 'react';
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
  const { user } = useAuthStore();

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);

  return (
    <div className="space-y-8 page-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Logistics & Inventory
          </h1>
          <p className="text-muted-foreground font-medium">
            Monitor global stock levels, track material flow, and manage supply chain velocity
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasPageAccess('/warehouse/sync', userRoles) && (
            <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
              <RefreshCw className="h-4 w-4 mr-2" />
              Sync Real-time Stock
            </Button>
          )}
          {hasPageAccess('/supply-chain', userRoles) && (
            <Button size="lg" className="rounded-xl shadow-glow subtle-shine" asChild>
              <Link href="/supply-chain">
                <Package className="h-4 w-4 mr-2" />
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
      <StatSection label="Inventory Metrics" columns={4}>
        <StatCard
          value={inventoryStats.totalItems.toLocaleString()}
          label="Inventory Nodes (SKUs)"
          icon={Box}
          iconColor="primary"
          trend="up"
          trendValue="+124 this cycle"
        />
        <StatCard
          value={inventoryStats.lowStock}
          label="Abnormal Stock Levels"
          icon={AlertTriangle}
          iconColor="warning"
          critical={inventoryStats.lowStock > 20}
        />
        <StatCard
          value={inventoryStats.pendingReceipts}
          label="Inbound Synchronization"
          icon={Truck}
          iconColor="info"
        />
        <StatCard
          value={inventoryStats.pendingShipments}
          label="Outbound Velocity"
          icon={Package}
          iconColor="success"
        />
      </StatSection>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Movements */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Recent Movements
            </CardTitle>
            <CardDescription>Latest inventory transactions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentMovements.map((movement) => (
                <div
                  key={movement.id}
                  className="flex items-center justify-between py-2 border-b last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-full ${
                      movement.type === 'in' 
                        ? 'bg-emerald-100 text-emerald-600' 
                        : 'bg-blue-100 text-blue-600'
                    }`}>
                      {movement.type === 'in' ? (
                        <ArrowDownRight className="h-4 w-4" />
                      ) : (
                        <ArrowUpRight className="h-4 w-4" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-sm">{movement.item}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <MapPin className="h-3 w-3" />
                        {movement.location}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-sm">
                      {movement.type === 'in' ? '+' : '-'}{movement.quantity}
                    </p>
                    <p className="text-xs text-muted-foreground">{movement.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Low Stock Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Low Stock Alerts
            </CardTitle>
            <CardDescription>Items below reorder point</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {lowStockItems.map((item) => (
                <div key={item.id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-sm">{item.name}</p>
                    <Badge variant="outline" className="text-amber-600">
                      {item.current} / {item.reorder} {item.unit}
                    </Badge>
                  </div>
                  <Progress 
                    value={(item.current / item.reorder) * 100} 
                    className="h-2"
                  />
                </div>
              ))}
            </div>
            {hasPageAccess('/supply-chain', userRoles) && (
              <Button variant="outline" className="w-full mt-4" asChild>
                <Link href="/supply-chain?filter=low-stock">
                  <ClipboardList className="h-4 w-4 mr-2" />
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
