'use client';

import * as React from 'react';
import { Suspense, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
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
  ShieldAlert,
  Lock,
  Hammer,
  ShieldCheck,
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
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

type TabType = 'assets' | 'work-orders' | 'pm-schedules' | 'loto' | 'tool-crib' | 'warranty' | 'field-returns' | 'budget';

function MaintenanceStats({ t }: { t: (key: string) => string | undefined }) {
  const { stats } = useMaintenanceStore();
  
  return (
    <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.maintenance.stats.assetNodes') || 'Asset Nodes'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats?.total_assets || 0}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-red/60 mb-4">{t('pages.maintenance.stats.anomalousDown') || 'Anomalous Down'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-red tabular-nums">{stats?.assets_by_status?.down || 0}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-orange/60 mb-4">{t('pages.maintenance.stats.thresholdOverdue') || 'Threshold Overdue'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{stats?.overdue_pms || 0}</p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-line">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-green/60 mb-4">{t('pages.maintenance.stats.efficiencyPulse') || 'Efficiency Pulse'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{stats?.efficiency_pulse ?? 'N/A'}%</p>
      </div>
    </div>
  );
}

function AssetsTab() {
  const { t } = useI18n();
  const { assets, loading, fetchAssets } = useMaintenanceStore();
  const [searchQuery, setSearchQuery] = React.useState('');

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  const filteredAssets = assets.filter((asset) => 
    asset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    asset.asset_number.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const assetChildren = React.useMemo(() => {
    const childrenMap = new Map<string | null, typeof assets>();
    assets.forEach((asset) => {
      const parentId = asset.parent_asset_id || null;
      const bucket = childrenMap.get(parentId) ?? [];
      bucket.push(asset);
      childrenMap.set(parentId, bucket);
    });
    return childrenMap;
  }, [assets]);

  const renderAssetTree = (parentId: string | null, depth: number = 0) => {
    const children = assetChildren.get(parentId) ?? [];
    return children.map((asset) => (
      <div key={asset.id} className="space-y-2">
        <div className="flex items-center gap-2" style={{ paddingLeft: `${depth * 16}px` }}>
          <span className="text-xs text-muted-foreground">{asset.asset_number}</span>
          <span className="font-medium">{asset.name}</span>
          <Badge variant="outline" className="ml-auto">{asset.asset_type}</Badge>
        </div>
        {renderAssetTree(asset.id, depth + 1)}
      </div>
    ));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder={t('pages.maintenance.searchAssets') || 'Search assets...'} 
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Button variant="outline" className="gap-2">
          <Filter className="h-4 w-4" />
          {t('common.filter') || 'Filter'}
        </Button>
      </div>
      
      <Card>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.assetNumber') || 'Asset #'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('common.name') || 'Name'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('common.type') || 'Type'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.criticality') || 'Criticality'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.lastPM') || 'Last PM'}</th>
                <th className="py-3 px-4 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingAssets') || 'Loading assets...'}</td></tr>
              ) : filteredAssets.length === 0 ? (
                <tr><td colSpan={7} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noAssetsFound') || 'No assets found.'}</td></tr>
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
                      {asset.last_pm_date ? formatDate(new Date(asset.last_pm_date)) : (t('common.na') || 'N/A')}
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

      <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.maintenance.equipmentHierarchy') || 'Equipment Hierarchy'}</CardTitle>
        </CardHeader>
        <CardContent>
          {assets.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t('pages.maintenance.noAssetHierarchy') || 'No asset hierarchy available.'}</p>
          ) : (
            <div className="space-y-3">
              {renderAssetTree(null)}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function WorkOrdersTab() {
  const { t } = useI18n();
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
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.woNumber') || 'WO #'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('common.type') || 'Type'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.approval') || 'Approval'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('common.priority') || 'Priority'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.assignedTo') || 'Assigned To'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('common.created') || 'Created'}</th>
              <th className="py-3 px-4 w-10"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingWorkOrders') || 'Loading work orders...'}</td></tr>
            ) : workOrders.length === 0 ? (
              <tr><td colSpan={8} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noWorkOrdersFound') || 'No work orders found.'}</td></tr>
            ) : (
              workOrders.map((wo) => (
                <tr key={wo.id} className="border-b hover:bg-muted/50 transition-colors">
                  <td className="py-3 px-4 font-medium">{wo.work_order_number}</td>
                  <td className="py-3 px-4 capitalize">{wo.work_order_type}</td>
                  <td className="py-3 px-4 capitalize">{wo.status}</td>
                  <td className="py-3 px-4">
                    <Badge variant={wo.approval_status === 'approved' ? 'success' : wo.approval_status === 'rejected' ? 'danger' : wo.approval_status === 'pending' ? 'warning' : 'secondary'}>
                      {wo.approval_status || 'n/a'}
                    </Badge>
                  </td>
                  <td className="py-3 px-4">{wo.priority}</td>
                  <td className="py-3 px-4 text-muted-foreground">{wo.assigned_to || t('common.unassigned') || 'Unassigned'}</td>
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

function PMSchedulesTab() {
  const { t } = useI18n();
  const { pmSchedules, pmRoute, loading, fetchPMSchedules, fetchPMRoute } = useMaintenanceStore();

  useEffect(() => {
    fetchPMSchedules();
    fetchPMRoute(7);
  }, [fetchPMSchedules, fetchPMRoute]);

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.maintenance.upcomingPMSchedules') || 'Upcoming PM Schedules'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">{t('common.name') || 'Name'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.frequency') || 'Frequency'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.nextDue') || 'Next Due'}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={3} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingSchedules') || 'Loading schedules...'}</td></tr>
              ) : pmSchedules.length === 0 ? (
                <tr><td colSpan={3} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noPMSchedulesFound') || 'No PM schedules found.'}</td></tr>
              ) : (
                pmSchedules.map((pm) => (
                  <tr key={pm.id} className="border-b hover:bg-muted/50 transition-colors">
                    <td className="py-3 px-4 font-medium">{pm.name}</td>
                    <td className="py-3 px-4 text-muted-foreground">{pm.frequency_value} {pm.frequency_unit}</td>
                    <td className="py-3 px-4 text-muted-foreground">{pm.next_due ? formatDate(new Date(pm.next_due)) : (t('common.na') || 'N/A')}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.maintenance.optimizedPMRoute') || 'Optimized PM Route (7 days)'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">{t('common.asset') || 'Asset'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('common.task') || 'Task'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('common.due') || 'Due'}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={3} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingRoute') || 'Loading route...'}</td></tr>
              ) : pmRoute.length === 0 ? (
                <tr><td colSpan={3} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noPMRouteItems') || 'No PM route items.'}</td></tr>
              ) : (
                pmRoute.map((item) => (
                  <tr key={item.pm_id} className="border-b hover:bg-muted/50 transition-colors">
                    <td className="py-3 px-4 text-muted-foreground">{item.asset_id.slice(0, 8)}</td>
                    <td className="py-3 px-4 font-medium">{item.name}</td>
                    <td className="py-3 px-4 text-muted-foreground">{item.next_due ? formatDate(new Date(item.next_due)) : (t('common.na') || 'N/A')}</td>
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

function LotoTab() {
  const { t } = useI18n();
  const { lotoProcedures, activeLotoLocks, loading, fetchLotoProcedures, fetchActiveLotoLocks } = useMaintenanceStore();

  useEffect(() => {
    fetchLotoProcedures();
    fetchActiveLotoLocks();
  }, [fetchLotoProcedures, fetchActiveLotoLocks]);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldAlert className="h-4 w-4 text-rams-orange" />
              {t('pages.maintenance.lotoProcedures') || 'LOTO Procedures'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('common.title') || 'Title'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.asset') || 'Asset'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.version') || 'Version'}</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingProcedures') || 'Loading procedures...'}</td></tr>
                ) : lotoProcedures.length === 0 ? (
                  <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noLotoProceduresFound') || 'No LOTO procedures found.'}</td></tr>
                ) : (
                  lotoProcedures.map((proc) => (
                    <tr key={proc.id} className="border-b hover:bg-muted/50 transition-colors">
                      <td className="py-3 px-4 font-medium">{proc.title}</td>
                      <td className="py-3 px-4 text-muted-foreground">{proc.asset_id.slice(0, 8)}</td>
                      <td className="py-3 px-4">
                        <Badge variant={proc.status === 'active' ? 'success' : 'secondary'}>
                          {proc.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{proc.version}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Lock className="h-4 w-4 text-rams-red" />
              {t('pages.maintenance.activeLocks') || 'Active Locks'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.lockNumber') || 'Lock #'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.asset') || 'Asset'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.applied') || 'Applied'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingLocks') || 'Loading locks...'}</td></tr>
                ) : activeLotoLocks.length === 0 ? (
                  <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noActiveLocks') || 'No active locks.'}</td></tr>
                ) : (
                  activeLotoLocks.map((lock) => (
                    <tr key={lock.id} className="border-b hover:bg-muted/50 transition-colors">
                      <td className="py-3 px-4 font-medium">{lock.lock_number}</td>
                      <td className="py-3 px-4 text-muted-foreground">{lock.asset_id.slice(0, 8)}</td>
                      <td className="py-3 px-4 text-muted-foreground">{formatDate(new Date(lock.applied_at))}</td>
                      <td className="py-3 px-4">
                        <Badge variant="danger">active</Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ToolCribTab() {
  const { t } = useI18n();
  const { tools, activeToolCheckouts, loading, fetchTools, fetchActiveToolCheckouts } = useMaintenanceStore();

  useEffect(() => {
    fetchTools();
    fetchActiveToolCheckouts();
  }, [fetchTools, fetchActiveToolCheckouts]);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Hammer className="h-4 w-4 text-rams-orange" />
              {t('pages.maintenance.toolInventory') || 'Tool Inventory'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.toolNumber') || 'Tool #'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.name') || 'Name'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.qty') || 'Qty'}</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingTools') || 'Loading tools...'}</td></tr>
                ) : tools.length === 0 ? (
                  <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noToolsFound') || 'No tools found.'}</td></tr>
                ) : (
                  tools.map((tool) => (
                    <tr key={tool.id} className="border-b hover:bg-muted/50 transition-colors">
                      <td className="py-3 px-4 font-medium">{tool.tool_number}</td>
                      <td className="py-3 px-4">{tool.name}</td>
                      <td className="py-3 px-4">
                        <Badge variant={tool.status === 'available' ? 'success' : tool.status === 'checked_out' ? 'warning' : 'secondary'}>
                          {tool.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{tool.quantity_on_hand}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Wrench className="h-4 w-4 text-rams-orange" />
              {t('pages.maintenance.activeCheckouts') || 'Active Checkouts'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.tool') || 'Tool'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.checkedOut') || 'Checked Out'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.dueBack') || 'Due Back'}</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={3} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingCheckouts') || 'Loading checkouts...'}</td></tr>
                ) : activeToolCheckouts.length === 0 ? (
                  <tr><td colSpan={3} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noActiveCheckouts') || 'No active checkouts.'}</td></tr>
                ) : (
                  activeToolCheckouts.map((checkout) => (
                    <tr key={checkout.id} className="border-b hover:bg-muted/50 transition-colors">
                      <td className="py-3 px-4 font-medium">{checkout.tool_id.slice(0, 8)}</td>
                      <td className="py-3 px-4 text-muted-foreground">{formatDate(new Date(checkout.checked_out_at))}</td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {checkout.due_back_at ? formatDate(new Date(checkout.due_back_at)) : (t('common.na') || 'N/A')}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function WarrantyTab() {
  const { t } = useI18n();
  const { warranties, loading, fetchWarranties } = useMaintenanceStore();

  useEffect(() => {
    fetchWarranties();
  }, [fetchWarranties]);

  return (
    <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck className="h-4 w-4 text-rams-green" />
          {t('pages.maintenance.assetWarranties') || 'Asset Warranties'}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="py-3 px-4 text-left font-medium">{t('common.asset') || 'Asset'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('common.type') || 'Type'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.coverage') || 'Coverage'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.claims') || 'Claims'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.ends') || 'Ends'}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingWarranties') || 'Loading warranties...'}</td></tr>
            ) : warranties.length === 0 ? (
              <tr><td colSpan={6} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noWarrantiesFound') || 'No warranties found.'}</td></tr>
            ) : (
              warranties.map((warranty) => (
                <tr key={warranty.id} className="border-b hover:bg-muted/50 transition-colors">
                  <td className="py-3 px-4 text-muted-foreground">{warranty.asset_id.slice(0, 8)}</td>
                  <td className="py-3 px-4 capitalize">{warranty.warranty_type}</td>
                  <td className="py-3 px-4 text-muted-foreground">{warranty.coverage_type}</td>
                  <td className="py-3 px-4">
                    <Badge variant={warranty.status === 'active' ? 'success' : 'secondary'}>
                      {warranty.status}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-muted-foreground">{warranty.claims?.length ?? 0}</td>
                  <td className="py-3 px-4 text-muted-foreground">{formatDate(new Date(warranty.end_date))}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function FieldReturnsTab() {
  const { t } = useI18n();
  const { fieldReturns, loading, fetchFieldReturns } = useMaintenanceStore();

  useEffect(() => {
    fetchFieldReturns();
  }, [fetchFieldReturns]);

  return (
    <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertTriangle className="h-4 w-4 text-rams-orange" />
          {t('pages.maintenance.fieldReturns') || 'Field Returns'}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.returnNumber') || 'Return #'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('common.asset') || 'Asset'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.failureMode') || 'Failure Mode'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.costImpact') || 'Cost Impact'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.received') || 'Received'}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingFieldReturns') || 'Loading field returns...'}</td></tr>
            ) : fieldReturns.length === 0 ? (
              <tr><td colSpan={6} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noFieldReturnsFound') || 'No field returns found.'}</td></tr>
            ) : (
              fieldReturns.map((fieldReturn) => (
                <tr key={fieldReturn.id} className="border-b hover:bg-muted/50 transition-colors">
                  <td className="py-3 px-4 font-medium">{fieldReturn.return_number}</td>
                  <td className="py-3 px-4 text-muted-foreground">{fieldReturn.asset_id.slice(0, 8)}</td>
                  <td className="py-3 px-4">
                    <Badge variant={fieldReturn.status === 'closed' ? 'success' : 'warning'}>
                      {fieldReturn.status}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-muted-foreground">{fieldReturn.failure_mode || '—'}</td>
                  <td className="py-3 px-4 text-muted-foreground">
                    {fieldReturn.cost_impact ? `${fieldReturn.cost_impact}` : '—'}
                  </td>
                  <td className="py-3 px-4 text-muted-foreground">{formatDate(new Date(fieldReturn.received_at))}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function BudgetTab() {
  const { t } = useI18n();
  const { budgets, loading, fetchBudgets } = useMaintenanceStore();

  useEffect(() => {
    fetchBudgets();
  }, [fetchBudgets]);

  return (
    <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
      <CardHeader>
        <CardTitle className="text-base">{t('pages.maintenance.maintenanceBudget') || 'Maintenance Budget'}</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.period') || 'Period'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.budget') || 'Budget'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.actual') || 'Actual'}</th>
              <th className="py-3 px-4 text-left font-medium">{t('pages.maintenance.table.variance') || 'Variance'}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.loadingBudgets') || 'Loading budgets...'}</td></tr>
            ) : budgets.length === 0 ? (
              <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.maintenance.noBudgetsFound') || 'No budgets found.'}</td></tr>
            ) : (
              budgets.map((budget) => (
                <tr key={budget.id} className="border-b hover:bg-muted/50 transition-colors">
                  <td className="py-3 px-4 text-muted-foreground">
                    {formatDate(new Date(budget.period_start))} - {formatDate(new Date(budget.period_end))}
                  </td>
                  <td className="py-3 px-4 font-medium">{budget.currency} {budget.budget_amount}</td>
                  <td className="py-3 px-4 text-muted-foreground">{budget.currency} {budget.actual_amount}</td>
                  <td className="py-3 px-4">
                    <Badge variant={budget.variance_amount <= 0 ? 'success' : 'warning'}>
                      {budget.currency} {budget.variance_amount}
                    </Badge>
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
  const { t } = useI18n();
  const [activeTab, setActiveTab] = React.useState<TabType>('assets');
  const { fetchStats } = useMaintenanceStore();
  const router = useRouter();

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="maintenance-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.maintenance.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.maintenance.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.maintenance.station') || 'STATION: FACILITY-01'}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm" onClick={() => router.push('/maintenance/mobile')}>
            {t('pages.maintenance.mobileMode') || 'MOBILE_MODE'}
          </Button>
          <Button variant="outline" size="default" className="rounded-rams-sm" onClick={() => {}}>
            <History className="h-3.5 w-3.5 mr-2" />
            {t('common.history') || 'History'}
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase" onClick={() => {}}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            {t('pages.maintenance.initializeAsset') || 'Initialize Asset'}
          </Button>
        </div>
      </div>

      <MaintenanceStats t={t} />

      {/* Main Content (Modular Rack) */}
      <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
        <CardHeader className="p-0 border-b border-rams-line bg-rams-panel/20">
          <div className="flex overflow-x-auto scrollbar-hide">
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative',
                activeTab === 'assets'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('assets')}
            >
              {t('pages.maintenance.tabs.assets') || 'Assets'}
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative border-l border-rams-line',
                activeTab === 'work-orders'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('work-orders')}
            >
              {t('pages.maintenance.tabs.workOrders') || 'Work Orders'}
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative border-l border-rams-line',
                activeTab === 'pm-schedules'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('pm-schedules')}
            >
              {t('pages.maintenance.tabs.pmSchedules') || 'PM Schedules'}
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative border-l border-rams-line',
                activeTab === 'loto'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('loto')}
            >
              {t('pages.maintenance.tabs.loto') || 'LOTO'}
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative border-l border-rams-line',
                activeTab === 'tool-crib'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('tool-crib')}
            >
              {t('pages.maintenance.tabs.toolCrib') || 'Tool Crib'}
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative border-l border-rams-line',
                activeTab === 'warranty'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('warranty')}
            >
              {t('pages.maintenance.tabs.warranty') || 'Warranty'}
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none whitespace-nowrap relative border-l border-rams-line',
                activeTab === 'budget'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('budget')}
            >
              {t('pages.maintenance.tabs.budget') || 'Budget'}
            </button>
          </div>
        </CardHeader>
        <CardContent className="p-6 bg-rams-module">
          <div className="animate-in fade-in duration-300">
            {activeTab === 'assets' && <AssetsTab />}
            {activeTab === 'work-orders' && <WorkOrdersTab />}
            {activeTab === 'pm-schedules' && <PMSchedulesTab />}
            {activeTab === 'loto' && <LotoTab />}
            {activeTab === 'tool-crib' && <ToolCribTab />}
            {activeTab === 'warranty' && <WarrantyTab />}
            {activeTab === 'field-returns' && <FieldReturnsTab />}
            {activeTab === 'budget' && <BudgetTab />}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function MaintenancePage() {
  const { t } = useI18n();
  return (
    <Suspense fallback={<div>{t('pages.maintenance.loading') || 'Loading Maintenance...'}</div>}>
      <MaintenancePageContent />
    </Suspense>
  );
}
