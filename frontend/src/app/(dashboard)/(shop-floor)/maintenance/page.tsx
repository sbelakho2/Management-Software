'use client';

import * as React from 'react';
import { Suspense, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Settings,
  AlertTriangle,
  CheckCircle,
  Clock,
  Wrench,
  Activity,
  History,
  Box,
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
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn, formatDate } from '@/lib/utils';
import { useMaintenanceStore } from '@/stores';

type TabType = 'assets' | 'work-orders' | 'pm-schedules';

function MaintenanceStats() {
  const { stats } = useMaintenanceStore();
  
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
              <Box className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.total_assets || 0}</p>
              <p className="text-sm text-muted-foreground">Total Assets</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/30">
              <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.assets_by_status?.down || 0}</p>
              <p className="text-sm text-muted-foreground">Assets Down</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-yellow-100 dark:bg-yellow-900/30">
              <Clock className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.overdue_pms || 0}</p>
              <p className="text-sm text-muted-foreground">Overdue PMs</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
              <Activity className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">88.5%</p>
              <p className="text-sm text-muted-foreground">Overall OEE</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AssetsTab() {
  const { assets, loading, fetchAssets } = useMaintenanceStore();
  const [searchQuery, setSearchQuery] = React.useState('');

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  const filteredAssets = assets.filter((asset) => 
    asset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    asset.asset_number.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search assets..." 
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Button variant="outline" className="gap-2">
          <Filter className="h-4 w-4" />
          Filter
        </Button>
      </div>
      
      <Card>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">Asset #</th>
                <th className="py-3 px-4 text-left font-medium">Name</th>
                <th className="py-3 px-4 text-left font-medium">Type</th>
                <th className="py-3 px-4 text-left font-medium">Status</th>
                <th className="py-3 px-4 text-left font-medium">Criticality</th>
                <th className="py-3 px-4 text-left font-medium">Last PM</th>
                <th className="py-3 px-4 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="py-8 text-center text-muted-foreground">Loading assets...</td></tr>
              ) : filteredAssets.length === 0 ? (
                <tr><td colSpan={7} className="py-8 text-center text-muted-foreground">No assets found.</td></tr>
              ) : (
                filteredAssets.map((asset) => (
                  <tr key={asset.id} className="border-b hover:bg-muted/50 transition-colors">
                    <td className="py-3 px-4 font-medium">{asset.asset_number}</td>
                    <td className="py-3 px-4">{asset.name}</td>
                    <td className="py-3 px-4 capitalize">{asset.asset_type}</td>
                    <td className="py-3 px-4">
                      <Badge variant={asset.status === 'operational' ? 'success' : asset.status === 'down' ? 'danger' : 'warning'}>
                        {asset.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant="outline">{asset.criticality}</Badge>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {asset.last_pm_date ? formatDate(new Date(asset.last_pm_date)) : 'N/A'}
                    </td>
                    <td className="py-3 px-4">
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

function WorkOrdersTab() {
  const { workOrders, loading, fetchWorkOrders } = useMaintenanceStore();

  useEffect(() => {
    fetchWorkOrders();
  }, [fetchWorkOrders]);

  return (
    <Card>
      <CardContent className="p-0">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="py-3 px-4 text-left font-medium">WO #</th>
              <th className="py-3 px-4 text-left font-medium">Type</th>
              <th className="py-3 px-4 text-left font-medium">Status</th>
              <th className="py-3 px-4 text-left font-medium">Priority</th>
              <th className="py-3 px-4 text-left font-medium">Assigned To</th>
              <th className="py-3 px-4 text-left font-medium">Created</th>
              <th className="py-3 px-4 w-10"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="py-8 text-center text-muted-foreground">Loading work orders...</td></tr>
            ) : workOrders.length === 0 ? (
              <tr><td colSpan={7} className="py-8 text-center text-muted-foreground">No work orders found.</td></tr>
            ) : (
              workOrders.map((wo) => (
                <tr key={wo.id} className="border-b hover:bg-muted/50 transition-colors">
                  <td className="py-3 px-4 font-medium">{wo.work_order_number}</td>
                  <td className="py-3 px-4 capitalize">{wo.work_order_type}</td>
                  <td className="py-3 px-4 capitalize">{wo.status}</td>
                  <td className="py-3 px-4">{wo.priority}</td>
                  <td className="py-3 px-4 text-muted-foreground">{wo.assigned_to || 'Unassigned'}</td>
                  <td className="py-3 px-4 text-muted-foreground">{formatDate(new Date(wo.created_at))}</td>
                  <td className="py-3 px-4">
                    <Button variant="ghost" size="icon">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function MaintenancePageContent() {
  const [activeTab, setActiveTab] = React.useState<TabType>('assets');
  const { fetchStats } = useMaintenanceStore();

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return (
    <div className="space-y-6" data-testid="maintenance-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Maintenance & TPM</h1>
          <p className="text-muted-foreground">Asset reliability, preventive maintenance, and OEE tracking</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2">
            <History className="h-4 w-4" />
            History
          </Button>
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            New Asset
          </Button>
        </div>
      </div>

      <MaintenanceStats />

      <div className="border-b">
        <nav className="flex gap-4">
          <button
            onClick={() => setActiveTab('assets')}
            className={cn(
              'pb-3 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'assets'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            Assets
          </button>
          <button
            onClick={() => setActiveTab('work-orders')}
            className={cn(
              'pb-3 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'work-orders'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            Work Orders
          </button>
          <button
            onClick={() => setActiveTab('pm-schedules')}
            className={cn(
              'pb-3 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'pm-schedules'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            PM Schedules
          </button>
        </nav>
      </div>

      <div className="mt-4">
        {activeTab === 'assets' && <AssetsTab />}
        {activeTab === 'work-orders' && <WorkOrdersTab />}
        {activeTab === 'pm-schedules' && <div className="text-center py-12 text-muted-foreground">PM Schedules view coming soon...</div>}
      </div>
    </div>
  );
}

export default function MaintenancePage() {
  return (
    <Suspense fallback={<div>Loading Maintenance...</div>}>
      <MaintenancePageContent />
    </Suspense>
  );
}
