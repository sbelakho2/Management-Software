'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  Calendar,
  ClipboardCheck,
  FileText,
  AlertTriangle,
  ChevronRight,
  Plus,
  Trash2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useQualityStore } from '@/stores/quality';
import { cn, formatDate } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

export default function InspectionDetailsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useParams();
  const { inspections, fetchInspections } = useQualityStore();

  const inspection = React.useMemo(() => 
    inspections.find(i => i.id === params?.id) || inspections[0], 
    [inspections, params?.id]
  );

  React.useEffect(() => {
    if (inspections.length === 0) {
      fetchInspections();
    }
  }, [inspections.length, fetchInspections]);

  if (!inspection) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const statusConfig = {
    passed: { label: 'Passed', variant: 'success' as const, icon: CheckCircle2 },
    failed: { label: 'Failed', variant: 'destructive' as const, icon: XCircle },
    pending: { label: 'Pending', variant: 'warning' as const, icon: Clock },
    in_progress: { label: 'In Progress', variant: 'default' as const, icon: Clock },
  };

  const typeConfig = {
    incoming: 'Incoming Material',
    in_process: 'In-Process',
    final: 'Final Inspection',
    first_article: 'First Article (FAI)',
  };

  return (
    <div className="space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-heading font-bold tracking-tight ">{inspection.inspection_number}</h1>
              <Badge variant={statusConfig[inspection.status as keyof typeof statusConfig]?.variant || 'default'} className="rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                {statusConfig[inspection.status as keyof typeof statusConfig]?.label || inspection.status}
              </Badge>
            </div>
            <p className="text-muted-foreground font-medium text-sm">{typeConfig[inspection.type as keyof typeof typeConfig] || inspection.type} Protocol</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            Print Evidence
          </Button>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine">
            Commit Synchronization
          </Button>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader>
              <CardTitle className="text-lg font-heading">Inspection Intelligence</CardTitle>
              <CardDescription className="text-xs font-medium uppercase tracking-wider">Core parameters and entity relationships</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-8 sm:grid-cols-2">
                <div className="space-y-4">
                  <div className="flex justify-between border-b border-border/10 pb-3 text-sm">
                    <span className="text-muted-foreground font-medium">Product Node</span>
                    <span className="font-bold tracking-tight">{inspection.product?.name || 'Unknown'}</span>
                  </div>
                  <div className="flex justify-between border-b border-border/10 pb-3 text-sm">
                    <span className="text-muted-foreground font-medium">Work Order Context</span>
                    <span className="font-bold tracking-tight">{inspection.work_order?.work_order_number || 'None'}</span>
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between border-b border-border/10 pb-3 text-sm">
                    <span className="text-muted-foreground">Station</span>
                    <span className="font-medium">QC-01</span>
                  </div>
                  <div className="flex justify-between border-b pb-2 text-sm">
                    <span className="text-muted-foreground">Sample Size</span>
                    <span className="font-medium">5 units</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center justify-between">
                Inspection Checklist
                <Badge variant="outline">3/5 Completed</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y">
                {[
                  { id: 1, task: 'Verify material certification matches batch', status: 'passed' },
                  { id: 2, task: 'Dimensional check: Overall length (150mm ±0.05)', status: 'passed' },
                  { id: 3, task: 'Dimensional check: Bore diameter (25mm +0.02/-0.00)', status: 'passed' },
                  { id: 4, task: 'Visual check: Surface finish for burrs or scratches', status: 'pending' },
                  { id: 5, task: 'Hardness test: Rockwell C 30-35', status: 'pending' },
                ].map((item) => (
                  <div key={item.id} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "h-6 w-6 rounded border flex items-center justify-center",
                        item.status === 'passed' ? "bg-green-100 border-green-200 text-green-600" : "bg-white border-slate-300"
                      )}>
                        {item.status === 'passed' && <CheckCircle2 className="h-4 w-4" />}
                      </div>
                      <span className="text-sm font-medium">{item.task}</span>
                    </div>
                    {item.status === 'passed' ? (
                      <Badge variant="success">Pass</Badge>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" className="h-8 text-green-600 hover:text-green-700">Pass</Button>
                        <Button variant="outline" size="sm" className="h-8 text-red-600 hover:text-red-700">Fail</Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Schedule & Assignment</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  <span>Scheduled Date</span>
                </div>
                <span className="font-medium">{inspection.inspection_date ? formatDate(inspection.inspection_date) : '-'}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <User className="h-4 w-4" />
                  <span>Inspector</span>
                </div>
                <span className="font-medium">{inspection.inspector?.full_name || 'Unassigned'}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Results Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 text-center py-4">
                <div className="flex justify-center">
                  <div className="p-3 bg-primary/10 rounded-full">
                    <ClipboardCheck className="h-10 w-10 text-primary" />
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="font-bold text-2xl">0.0% Defect Rate</p>
                  <p className="text-sm text-muted-foreground">Based on current checks</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
