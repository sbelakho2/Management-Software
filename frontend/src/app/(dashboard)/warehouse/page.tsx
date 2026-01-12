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
import { Skeleton } from '@/components/ui/skeleton';
import Link from 'next/link';

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

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  trend, 
  trendLabel,
  variant = 'default' 
}: { 
  title: string; 
  value: string | number; 
  icon: React.ElementType;
  trend?: 'up' | 'down';
  trendLabel?: string;
  variant?: 'default' | 'warning' | 'danger' | 'success';
}) {
  const variantStyles = {
    default: 'bg-primary/10 text-primary',
    warning: 'bg-amber-500/10 text-amber-600',
    danger: 'bg-destructive/10 text-destructive',
    success: 'bg-emerald-500/10 text-emerald-600',
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold mt-1">{value}</p>
            {trend && trendLabel && (
              <div className={`flex items-center gap-1 text-xs mt-1 ${trend === 'up' ? 'text-emerald-600' : 'text-destructive'}`}>
                {trend === 'up' ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                {trendLabel}
              </div>
            )}
          </div>
          <div className={`p-3 rounded-full ${variantStyles[variant]}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function WarehouseDashboard() {
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => setIsLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Warehouse Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor inventory, track movements, and manage stock levels
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Sync Inventory
          </Button>
          <Button asChild>
            <Link href="/supply-chain">
              <Package className="h-4 w-4 mr-2" />
              View Inventory
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total SKUs"
          value={inventoryStats.totalItems.toLocaleString()}
          icon={Box}
          trend="up"
          trendLabel="+124 this month"
        />
        <StatCard
          title="Low Stock Items"
          value={inventoryStats.lowStock}
          icon={AlertTriangle}
          variant="warning"
        />
        <StatCard
          title="Pending Receipts"
          value={inventoryStats.pendingReceipts}
          icon={Truck}
        />
        <StatCard
          title="Pending Shipments"
          value={inventoryStats.pendingShipments}
          icon={Package}
        />
      </div>

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
            <Button variant="outline" className="w-full mt-4" asChild>
              <Link href="/supply-chain?filter=low-stock">
                <ClipboardList className="h-4 w-4 mr-2" />
                View All Low Stock Items
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
