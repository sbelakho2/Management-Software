'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  AlertCircle,
  Calendar,
  User,
  ShieldCheck,
  Zap,
  FileText,
  Activity,
  MoreHorizontal,
  Plus,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useQualityStore } from '@/stores/quality';
import { cn, formatDate } from '@/lib/utils';

export default function CAPADetailsPage() {
  const router = useRouter();
  const params = useParams();
  const { capas, fetchCAPAs } = useQualityStore();

  const capa = React.useMemo(() => 
    capas.find(c => c.id === params?.id) || capas[0], 
    [capas, params?.id]
  );

  React.useEffect(() => {
    if (capas.length === 0) {
      fetchCAPAs();
    }
  }, [capas.length, fetchCAPAs]);

  if (!capa) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const statusConfig = {
    open: { label: 'Open', variant: 'warning' as const },
    in_progress: { label: 'In Progress', variant: 'default' as const },
    verifying: { label: 'Verifying', variant: 'secondary' as const },
    closed: { label: 'Closed', variant: 'success' as const },
  };

  const priorityConfig = {
    low: { label: 'Low', class: 'bg-slate-100 text-slate-800' },
    medium: { label: 'Medium', class: 'bg-blue-100 text-blue-800' },
    high: { label: 'High', class: 'bg-orange-100 text-orange-800' },
    urgent: { label: 'Urgent', class: 'bg-red-100 text-red-800' },
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{capa.capa_number}</h1>
              <Badge variant={statusConfig[capa.status as keyof typeof statusConfig]?.variant || 'default'}>
                {statusConfig[capa.status as keyof typeof statusConfig]?.label || capa.status}
              </Badge>
              <Badge className={priorityConfig[(capa as any).priority as keyof typeof priorityConfig]?.class}>
                {priorityConfig[(capa as any).priority as keyof typeof priorityConfig]?.label || (capa as any).priority}
              </Badge>
            </div>
            <p className="text-muted-foreground">{capa.title}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline">
            Export Report
          </Button>
          <Button>
            Complete Action
          </Button>
          <Button variant="outline" size="icon">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>CAPA Overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Implementation Progress</span>
                  <span className="font-medium">65%</span>
                </div>
                <Progress value={65} className="h-2" />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1">
                  <span className="text-sm text-muted-foreground font-medium">Problem Statement</span>
                  <p className="text-sm leading-relaxed">{capa.description || 'Recurring misalignment issues in CNC production line B.'}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-sm text-muted-foreground font-medium">Root Cause</span>
                  <p className="text-sm leading-relaxed">Worn vibration dampeners on CNC-04 and outdated calibration schedule.</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="actions">
            <TabsList>
              <TabsTrigger value="actions">Action Plan</TabsTrigger>
              <TabsTrigger value="verification">Effectiveness Verification</TabsTrigger>
              <TabsTrigger value="related">Related NCRs</TabsTrigger>
            </TabsList>
            <TabsContent value="actions" className="mt-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base">Corrective & Preventive Actions</CardTitle>
                  <Button variant="outline" size="sm">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Action
                  </Button>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="divide-y">
                    {[
                      { title: 'Replace vibration dampeners on CNC-04', assignee: 'Mike Tech', due: '2024-02-15', status: 'completed' },
                      { title: 'Update preventive maintenance schedule for all CNC machines', assignee: 'Sarah Ops', due: '2024-02-20', status: 'in_progress' },
                      { title: 'Conduct refresher training for CNC operators', assignee: 'John Train', due: '2024-03-01', status: 'pending' },
                    ].map((action, i) => (
                      <div key={i} className="p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {action.status === 'completed' ? (
                            <CheckCircle2 className="h-5 w-5 text-green-500" />
                          ) : action.status === 'in_progress' ? (
                            <Zap className="h-5 w-5 text-blue-500" />
                          ) : (
                            <Clock className="h-5 w-5 text-muted-foreground" />
                          )}
                          <div>
                            <div className="font-medium text-sm">{action.title}</div>
                            <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                              <span className="flex items-center gap-1">
                                <User className="h-3 w-3" />
                                {action.assignee}
                              </span>
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {action.due}
                              </span>
                            </div>
                          </div>
                        </div>
                        <Badge variant={action.status === 'completed' ? 'success' : action.status === 'in_progress' ? 'default' : 'secondary' as any}>
                          {action.status.replace('_', ' ')}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Management</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  <span>Due Date</span>
                </div>
                <span className="font-medium text-red-600">{capa.due_date ? formatDate(capa.due_date) : '-'}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <User className="h-4 w-4" />
                  <span>Owner</span>
                </div>
                <span className="font-medium">Sarah Johnson</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <ShieldCheck className="h-4 w-4" />
                  <span>Verified By</span>
                </div>
                <span className="font-medium">Pending</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Impact Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider">Quality Impact</span>
                  <div className="text-sm font-medium">Reduction in surface defects by estimated 15%</div>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider">Financial Impact</span>
                  <div className="text-sm font-medium">Potential savings of $2,400/month in scrap reduction</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
