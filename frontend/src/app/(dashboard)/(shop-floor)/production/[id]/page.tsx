'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  Settings,
  MoreHorizontal,
  Play,
  Pause,
  CheckCircle,
  AlertTriangle,
  Clock,
  Calendar,
  Users,
  Package,
  FileText,
  History,
  Activity,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useProductionStore } from '@/stores/production';
import { cn, formatDate, formatCurrency } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

export default function WorkOrderDetailsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useParams();
  const { workOrders, fetchWorkOrders } = useProductionStore();
  
  const workOrder = React.useMemo(() =>
    workOrders.find(wo => String(wo.id) === String(params?.id)),
    [workOrders, params?.id]
  );

  React.useEffect(() => {
    if (workOrders.length === 0) {
      fetchWorkOrders();
    }
  }, [workOrders.length, fetchWorkOrders]);

  if (!workOrder) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <div className="h-8 w-8 border border-rams-line bg-rams-panel animate-pulse"></div>
      </div>
    );
  }

  const statusConfig = {
    planned: { label: t('modules.production.status.planned'), color: 'bg-blue-100 text-blue-800', icon: Calendar, variant: 'secondary' as const },
    in_progress: { label: t('modules.production.status.inProgress'), color: 'bg-green-100 text-green-800', icon: Play, variant: 'success' as const },
    on_hold: { label: t('modules.production.status.onHold'), color: 'bg-yellow-100 text-yellow-800', icon: Pause, variant: 'warning' as const },
    completed: { label: t('modules.production.status.completed'), color: 'bg-slate-100 text-slate-800', icon: CheckCircle, variant: 'default' as const },
    cancelled: { label: t('modules.production.status.cancelled'), color: 'bg-red-100 text-red-800', icon: AlertTriangle, variant: 'destructive' as const },
    released: { label: t('modules.production.status.released'), color: 'bg-indigo-100 text-indigo-800', icon: Calendar, variant: 'secondary' as const },
  };

  const StatusIcon = statusConfig[workOrder.status as keyof typeof statusConfig]?.icon || Clock;

  const canStart = ['planned', 'released', 'on_hold'].includes(workOrder.status);

  return (
    <div className="space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{workOrder.work_order_number}</h1>
              <Badge variant={statusConfig[workOrder.status as keyof typeof statusConfig]?.variant} size="sm" className="h-4 px-1 rounded-none font-black text-[8px] uppercase tracking-widest">
                {statusConfig[workOrder.status as keyof typeof statusConfig]?.label.toUpperCase()}
              </Badge>
            </div>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2 mt-1">
              <span>{(workOrder as any).product?.name || t('modules.production.detail.unknownProduct')} {t('modules.production.detail.node')}</span>
              <span className="opacity-30">|</span>
              <span>{t('modules.production.detail.station')}: PRODUCTION-SYNC-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {canStart ? (
            <Button size="default" className="rounded-rams-sm bg-rams-green text-white font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none hover:bg-rams-green/90">
              <Play className="h-3.5 w-3.5 mr-2" />
              {t('modules.production.detail.initiateExecution')}
            </Button>
          ) : (
            <Button variant="outline" size="default" className="rounded-rams-sm border-rams-orange/30 bg-rams-orange/5 text-rams-orange font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none hover:bg-rams-orange/10">
              <Pause className="h-3.5 w-3.5 mr-2" />
              {t('modules.production.detail.suspendProtocol')}
            </Button>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-10 w-10 border border-rams-line rounded-rams-sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <FileText className="mr-2 h-3.5 w-3.5" /> {t('modules.production.detail.exportSpec')}
              </DropdownMenuItem>
              <DropdownMenuItem>
                <History className="mr-2 h-3.5 w-3.5" /> {t('modules.production.detail.viewHistory')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-rams-red">
                <AlertTriangle className="mr-2 h-3.5 w-3.5" /> {t('modules.production.detail.escalateAnomaly')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-3">
                <Activity className="h-4 w-4 text-rams-orange" />
                {t('modules.production.detail.executionVelocity')}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-8 space-y-8">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground/60">
                  <span>{t('modules.production.detail.aggregationPulse')}</span>
                  <span className="text-rams-orange">0%</span>
                </div>
                <div className="h-1 bg-rams-panel border border-rams-line overflow-hidden">
                  <div className="h-full bg-rams-orange transition-all duration-1000" style={{ width: '0%' }} />
                </div>
              </div>

              <div className="grid gap-px border border-rams-line bg-rams-line sm:grid-cols-3">
                <div className="bg-rams-module p-6 text-center group hover:bg-rams-panel/50 transition-none cursor-help">
                  <p className="text-[24px] font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{(workOrder as any).quantity}</p>
                  <p className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/40 mt-2">{t('modules.production.detail.targetMagnitude')}</p>
                </div>
                <div className="bg-rams-module p-6 text-center group hover:bg-rams-panel/50 transition-none cursor-help">
                  <p className="text-[24px] font-mono font-bold tracking-tight text-rams-green tabular-nums">{(workOrder as any).quantity_completed}</p>
                  <p className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/40 mt-2">{t('modules.production.detail.gateVerified')}</p>
                </div>
                <div className="bg-rams-module p-6 text-center group hover:bg-rams-panel/50 transition-none cursor-help">
                  <p className="text-[24px] font-mono font-bold tracking-tight text-rams-red tabular-nums">0</p>
                  <p className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/40 mt-2">{t('modules.production.detail.scrapDeviation')}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="operations" className="animate-in fade-in duration-500">
            <TabsList className="bg-rams-panel border border-rams-line p-1 rounded-rams-sm w-fit">
              <TabsTrigger value="operations">{t('modules.production.detail.tabs.operations')}</TabsTrigger>
              <TabsTrigger value="bom">{t('modules.production.detail.tabs.bom')}</TabsTrigger>
              <TabsTrigger value="quality">{t('modules.production.detail.tabs.quality')}</TabsTrigger>
              <TabsTrigger value="history">{t('modules.production.detail.tabs.history')}</TabsTrigger>
            </TabsList>
            <TabsContent value="operations" className="mt-6 space-y-4">
              <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden">
                <CardContent className="p-0">
                  <div className="divide-y divide-rams-line/30">
                    {[
                      { id: '1', name: 'Material Ingestion', station: 'ST-01', status: 'completed', time: '2H 15M' },
                      { id: '2', name: 'CNC Precision Routing', station: 'CNC-04', status: 'in_progress', time: '1H 45M' },
                      { id: '3', name: 'Surface Hardening', station: 'GR-02', status: 'pending', time: '—' },
                      { id: '4', name: 'Final Sync Inspection', station: 'QC-01', status: 'pending', time: '—' },
                    ].map((op) => (
                      <div key={op.id} className="p-5 flex items-center justify-between hover:bg-rams-panel transition-none group cursor-help">
                        <div className="flex items-center gap-6">
                          <div className={cn(
                            "h-10 w-10 border flex items-center justify-center text-[10px] font-mono font-black tabular-nums transition-none",
                            op.status === 'completed' ? "bg-rams-green/5 border-rams-green/20 text-rams-green" :
                            op.status === 'in_progress' ? "bg-rams-orange/10 border-rams-orange text-rams-orange animate-pulse shadow-[0_0_10px_rgba(255,190,0,0.1)]" :
                            "bg-rams-panel border-rams-line text-muted-foreground/20"
                          )}>
                            {op.id.padStart(2, '0')}
                          </div>
                          <div>
                            <div className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{op.name}</div>
                            <div className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-0.5">{t('modules.production.detail.station')}: {op.station}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-8">
                          <div className="text-[10px] font-mono font-bold text-muted-foreground/30 tabular-nums uppercase">{op.time}</div>
                          <Badge variant={op.status === 'completed' ? 'success' : op.status === 'in_progress' ? 'warning' : 'secondary'} size="sm" className="h-4 px-1 rounded-none font-black text-[8px] uppercase tracking-widest">
                            {op.status.toUpperCase()}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="bom" className="mt-6">
              <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
                <CardContent className="p-12 text-center">
                  <Package className="h-12 w-12 mx-auto mb-4 opacity-10" />
                  <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">{t('modules.production.detail.loadingBom')}</p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('modules.production.detail.temporalSchedule')}</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <span>{t('modules.production.detail.startHorizon')}</span>
                <span className="font-mono font-bold text-foreground/80">{workOrder.scheduled_start ? formatDate(workOrder.scheduled_start).toUpperCase() : '—'}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <span>{t('modules.production.detail.targetTerminal')}</span>
                <span className="font-mono font-bold text-foreground/80">{workOrder.scheduled_end ? formatDate(workOrder.scheduled_end).toUpperCase() : '—'}</span>
              </div>
              <div className="border-t border-rams-line pt-4">
                <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">
                  <span>{t('modules.production.detail.standardLeadTime')}</span>
                  <span className="font-mono font-bold text-foreground/60 uppercase">05 {t('modules.production.detail.days')}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('modules.production.detail.resourceAllocation')}</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="flex items-center gap-4 group">
                <div className="h-10 w-10 rounded-none bg-rams-panel border border-rams-line flex items-center justify-center text-muted-foreground/40 group-hover:border-rams-orange transition-none">
                  <Users className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-[11px] font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t('modules.production.detail.operationsTeamAlpha')}</div>
                  <div className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase mt-0.5">03 {t('modules.production.detail.activeOperativesAssigned')}</div>
                </div>
              </div>
              <div className="flex items-center gap-4 group">
                <div className="h-10 w-10 rounded-none bg-rams-panel border border-rams-line flex items-center justify-center text-muted-foreground/40 group-hover:border-rams-orange transition-none">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-[11px] font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t('modules.production.detail.standardWorkProtocol')}</div>
                  <div className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase mt-0.5">SW-WO-2024-V2 // {t('modules.production.detail.synced')}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
