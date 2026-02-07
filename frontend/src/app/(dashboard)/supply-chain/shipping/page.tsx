'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';
import { useShippingStore } from '@/stores';
import { 
  Truck, 
  Package,
  ClipboardList,
  MapPin,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Plus,
  Search,
  Filter,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { StatCard, StatSection } from '@/components/ui/stat-card';
import { cn } from '@/lib/utils';
import { SUPPLY_CHAIN_ROLES } from '@/lib/page-access';
import { PageGuard } from '@/components/layout/page-guard';
import type { Shipment, PickList, ShipmentStatus, PickListStatus } from '@/types';

const statusColors: Record<ShipmentStatus | PickListStatus, string> = {
  pending: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
  picked: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  packed: 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20',
  shipped: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  delivered: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
  canceled: 'bg-red-500/10 text-red-500 border-red-500/20',
  in_progress: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  completed: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
};

export default function ShippingPage() {
  const { t } = useI18n();
  const {
    shipments,
    pickLists,
    stats,
    isLoading,
    error,
    fetchShipments,
    fetchPickLists,
    fetchStats,
    updateShipmentStatus,
    startPicking,
    completePicking,
  } = useShippingStore();

  const [searchTerm, setSearchTerm] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');

  React.useEffect(() => {
    fetchStats();
    fetchShipments();
    fetchPickLists();
  }, [fetchStats, fetchShipments, fetchPickLists]);

  const filteredShipments = React.useMemo(() => {
    return shipments.filter((s) => {
      const matchesSearch = searchTerm === '' || 
        s.shipment_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.ship_to_name.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'all' || s.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [shipments, searchTerm, statusFilter]);

  const filteredPickLists = React.useMemo(() => {
    return pickLists.filter((pl) => {
      const matchesSearch = searchTerm === '' || 
        pl.pick_number.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'all' || pl.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [pickLists, searchTerm, statusFilter]);

  const handleRefresh = () => {
    fetchStats();
    fetchShipments();
    fetchPickLists();
  };

  return (
    <PageGuard requiredRoles={SUPPLY_CHAIN_ROLES}>
      <div className="space-y-8 page-fade-in pb-12">
        {/* Header */}
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              Shipping & Fulfillment
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">
              Manage shipments and pick lists
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
              <RefreshCw className={cn('h-4 w-4 mr-2', isLoading && 'animate-spin')} />
              Refresh
            </Button>
            <Button size="sm">
              <Plus className="h-4 w-4 mr-2" />
              New Shipment
            </Button>
          </div>
        </div>

        {/* Stats Section */}
        <StatSection label="Shipments" columns={3}>
          <StatCard
            label="Pending Shipments"
            value={stats?.pending_shipments ?? 0}
            icon={Package}
            iconColor="warning"
          />
          <StatCard
            label="In Transit"
            value={stats?.in_transit ?? 0}
            icon={Truck}
            iconColor="info"
          />
          <StatCard
            label="Delivered Today"
            value={stats?.delivered_today ?? 0}
            icon={CheckCircle2}
            iconColor="success"
          />
        </StatSection>
        <StatSection label="Pick Lists" columns={3}>
          <StatCard
            label="Pending Picks"
            value={stats?.pending_picks ?? 0}
            icon={ClipboardList}
            iconColor="warning"
          />
          <StatCard
            label="Picks In Progress"
            value={stats?.picks_in_progress ?? 0}
            icon={Clock}
            iconColor="info"
          />
          <StatCard
            label="Completed Picks"
            value={stats?.completed_picks ?? 0}
            icon={CheckCircle2}
            iconColor="success"
          />
        </StatSection>

        {/* Search and Filter */}
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search shipments or pick lists..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <select
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="picked">Picked</option>
            <option value="packed">Packed</option>
            <option value="shipped">Shipped</option>
            <option value="delivered">Delivered</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
          </select>
        </div>

        {/* Tabs for Shipments and Pick Lists */}
        <Tabs defaultValue="shipments" className="space-y-6">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="shipments" className="flex items-center gap-2">
              <Truck className="h-4 w-4" />
              Shipments ({filteredShipments.length})
            </TabsTrigger>
            <TabsTrigger value="picklists" className="flex items-center gap-2">
              <ClipboardList className="h-4 w-4" />
              Pick Lists ({filteredPickLists.length})
            </TabsTrigger>
          </TabsList>

          {/* Shipments Tab */}
          <TabsContent value="shipments" className="space-y-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : filteredShipments.length === 0 ? (
              <Card className="rounded-rams-sm border-rams-line bg-rams-module">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Truck className="h-12 w-12 text-muted-foreground/50 mb-4" />
                  <p className="text-muted-foreground">No shipments found</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {filteredShipments.map((shipment) => (
                  <Card key={shipment.id} className="rounded-rams-sm border-rams-line bg-rams-module hover:border-rams-accent/50 transition-colors">
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="space-y-2">
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold">{shipment.shipment_number}</h3>
                            <Badge className={cn('text-xs', statusColors[shipment.status])}>
                              {shipment.status.replace('_', ' ').toUpperCase()}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3 w-3" />
                              {shipment.ship_to_name}
                            </span>
                            <span>{shipment.ship_to_city}, {shipment.ship_to_country}</span>
                          </div>
                          {shipment.carrier && (
                            <div className="flex items-center gap-2 text-sm">
                              <Truck className="h-3 w-3" />
                              <span>{shipment.carrier}</span>
                              {shipment.tracking_number && (
                                <span className="text-muted-foreground">#{shipment.tracking_number}</span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          <span className="text-xs text-muted-foreground">
                            {shipment.lines?.length || 0} items
                          </span>
                          {shipment.status === 'pending' && (
                            <Button size="sm" variant="outline" onClick={() => updateShipmentStatus(shipment.id, 'picked')}>
                              Start Packing
                            </Button>
                          )}
                          {shipment.status === 'packed' && (
                            <Button size="sm" onClick={() => updateShipmentStatus(shipment.id, 'shipped')}>
                              Ship Now
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Pick Lists Tab */}
          <TabsContent value="picklists" className="space-y-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : filteredPickLists.length === 0 ? (
              <Card className="rounded-rams-sm border-rams-line bg-rams-module">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <ClipboardList className="h-12 w-12 text-muted-foreground/50 mb-4" />
                  <p className="text-muted-foreground">No pick lists found</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {filteredPickLists.map((pickList) => (
                  <Card key={pickList.id} className="rounded-rams-sm border-rams-line bg-rams-module hover:border-rams-accent/50 transition-colors">
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="space-y-2">
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold">{pickList.pick_number}</h3>
                            <Badge className={cn('text-xs', statusColors[pickList.status])}>
                              {pickList.status.replace('_', ' ').toUpperCase()}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {pickList.pick_strategy}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>Source: {pickList.source_type.replace('_', ' ')}</span>
                            <span>Priority: {pickList.priority}</span>
                          </div>
                          {pickList.assigned_to && (
                            <div className="text-sm">
                              Assigned to: {pickList.assigned_to.full_name}
                            </div>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          <span className="text-xs text-muted-foreground">
                            {pickList.lines?.length || 0} lines
                          </span>
                          {pickList.status === 'pending' && (
                            <Button size="sm" onClick={() => startPicking(pickList.id)}>
                              Start Picking
                            </Button>
                          )}
                          {pickList.status === 'in_progress' && (
                            <Button size="sm" variant="outline" onClick={() => completePicking(pickList.id)}>
                              Complete
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </PageGuard>
  );
}
