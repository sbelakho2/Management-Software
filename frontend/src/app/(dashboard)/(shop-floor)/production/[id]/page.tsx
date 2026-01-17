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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const statusConfig = {
    planned: { label: 'Planned', color: 'bg-blue-100 text-blue-800', icon: Calendar },
    in_progress: { label: 'In Progress', color: 'bg-green-100 text-green-800', icon: Play },
    on_hold: { label: 'On Hold', color: 'bg-yellow-100 text-yellow-800', icon: Pause },
    completed: { label: 'Completed', color: 'bg-slate-100 text-slate-800', icon: CheckCircle },
    cancelled: { label: 'Cancelled', color: 'bg-red-100 text-red-800', icon: AlertTriangle },
    released: { label: 'Released', color: 'bg-indigo-100 text-indigo-800', icon: Calendar },
  };

  const StatusIcon = statusConfig[workOrder.status as keyof typeof statusConfig]?.icon || Clock;

  const canStart = ['planned', 'released', 'on_hold'].includes(workOrder.status);

  return (
    <div className="space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-heading font-bold tracking-tight ">{workOrder.work_order_number}</h1>
              <Badge className={cn('rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider', statusConfig[workOrder.status as keyof typeof statusConfig]?.color)}>
                {statusConfig[workOrder.status as keyof typeof statusConfig]?.label}
              </Badge>
            </div>
            <p className="text-muted-foreground font-medium text-sm">{(workOrder as any).product?.name || 'Unknown Product'} Node</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {canStart ? (
            <Button size="lg" className="rounded-xl bg-emerald-600 hover:bg-emerald-700 shadow-glow subtle-shine text-white">
              <Play className="h-4 w-4 mr-2" />
              Initiate Execution
            </Button>
          ) : (
            <Button variant="outline" size="lg" className="rounded-xl border-amber-200 bg-amber-50 hover:bg-amber-100 text-amber-700">
              <Pause className="h-4 w-4 mr-2" />
              Suspend Protocol
            </Button>
          )}
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader>
              <CardTitle className="text-lg font-heading">Production Velocity</CardTitle>
              <CardDescription className="text-xs font-medium uppercase tracking-wider">Real-time execution status and synchronization</CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-bold uppercase tracking-widest text-muted-foreground/60">
                  <span>Overall Completion Pulse</span>
                  <span className="text-primary">0%</span>
                </div>
                <Progress value={0} className="h-3 rounded-full bg-primary/10" />
              </div>

              <div className="grid gap-6 sm:grid-cols-3">
                <div className="p-5 rounded-2xl bg-primary/5 border border-primary/10 text-center">
                  <p className="text-3xl font-heading font-bold tracking-tight ">{(workOrder as any).quantity}</p>
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 mt-2">Target Units</p>
                </div>
                <div className="p-5 rounded-2xl bg-emerald-500/5 border border-emerald-500/10 text-center">
                  <div className="text-3xl font-heading font-bold tracking-tight text-emerald-600 dark:text-emerald-500">{(workOrder as any).quantity_completed}</div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 mt-2">Passed Gate</p>
                </div>
                <div className="p-5 rounded-2xl bg-rose-500/5 border border-rose-500/10 text-center">
                  <div className="text-3xl font-heading font-bold tracking-tight text-red-600 dark:text-red-500">0</div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 mt-2">Rejected</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="operations">
            <TabsList>
              <TabsTrigger value="operations">Operations</TabsTrigger>
              <TabsTrigger value="bom">BOM / Parts</TabsTrigger>
              <TabsTrigger value="quality">Quality Checks</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>
            <TabsContent value="operations" className="mt-4">
              <Card>
                <CardContent className="p-0">
                  <div className="divide-y">
                    {/* Mock operations since they aren't in the base store model yet */}
                    {[
                      { id: '1', name: 'Material Preparation', station: 'ST-01', status: 'completed', time: '2h 15m' },
                      { id: '2', name: 'CNC Machining', station: 'CNC-04', status: 'in_progress', time: '1h 45m' },
                      { id: '3', name: 'Surface Grinding', station: 'GR-02', status: 'pending', time: '0m' },
                      { id: '4', name: 'Final Inspection', station: 'QC-01', status: 'pending', time: '0m' },
                    ].map((op) => (
                      <div key={op.id} className="p-4 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className={cn(
                            "h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold",
                            op.status === 'completed' ? "bg-green-100 text-green-700" :
                            op.status === 'in_progress' ? "bg-blue-100 text-blue-700 animate-pulse" :
                            "bg-muted text-muted-foreground"
                          )}>
                            {op.id}
                          </div>
                          <div>
                            <div className="font-medium">{op.name}</div>
                            <div className="text-xs text-muted-foreground">Station: {op.station}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-sm text-muted-foreground">{op.time}</div>
                          <Badge variant={op.status === 'completed' ? 'success' : op.status === 'in_progress' ? 'default' : 'secondary' as any}>
                            {op.status.replace('_', ' ')}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="bom" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">Required Materials</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-8 text-muted-foreground">
                    <Package className="h-8 w-8 mx-auto mb-2 opacity-20" />
                    <p>Bill of Materials information will be loaded here.</p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Schedule</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Start Date</span>
                <span className="font-medium">{workOrder.scheduled_start ? formatDate(workOrder.scheduled_start) : '-'}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">End Date</span>
                <span className="font-medium">{workOrder.scheduled_end ? formatDate(workOrder.scheduled_end) : '-'}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Lead Time</span>
                <span className="font-medium">5 Days</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Assigned Resources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <Users className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <div className="text-sm font-medium">Operations Team A</div>
                  <div className="text-xs text-muted-foreground">3 Operators assigned</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <div className="text-sm font-medium">Standard Work</div>
                  <div className="text-xs text-muted-foreground">SW-WO-2024-V2</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
