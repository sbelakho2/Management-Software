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
        <div className="animate-spin h-8 w-8 border-2 border-rams-orange border-t-transparent"></div>
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
    <div className="space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{inspection.inspection_number}</h1>
              <Badge variant={statusConfig[inspection.status as keyof typeof statusConfig]?.variant || 'secondary'} size="sm" className="h-4 px-1 rounded-none font-black text-[8px] uppercase tracking-widest">
                {statusConfig[inspection.status as keyof typeof statusConfig]?.label.toUpperCase() || inspection.status.toUpperCase()}
              </Badge>
            </div>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2 mt-1">
              <span>{typeConfig[inspection.type as keyof typeof typeConfig] || inspection.type} Protocol</span>
              <span className="opacity-30">|</span>
              <span>STATION: QUALITY-GATE-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none">
            {t('quality.inspection.detail.printEvidence') || 'PRINT_EVIDENCE'}
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            {t('quality.inspection.detail.commitSync') || 'COMMIT_SYNCHRONIZATION'}
          </Button>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-3">
                <ClipboardCheck className="h-4 w-4 text-rams-orange" />
                {t('quality.inspection.detail.inspectionIntelligence') || 'Inspection Intelligence'}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-8 space-y-8">
              <div className="grid gap-8 sm:grid-cols-2">
                <div className="space-y-4">
                  <div className="flex justify-between items-center border-b border-rams-line pb-3 text-[10px] font-black uppercase tracking-widest">
                    <span className="text-muted-foreground/40">Product Node</span>
                    <span className="text-foreground/80">{inspection.product?.name || 'UNKNOWN'}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-rams-line pb-3 text-[10px] font-black uppercase tracking-widest">
                    <span className="text-muted-foreground/40">Work Order Context</span>
                    <span className="text-foreground/80 font-mono">{inspection.work_order?.work_order_number || 'NONE'}</span>
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between items-center border-b border-rams-line pb-3 text-[10px] font-black uppercase tracking-widest">
                    <span className="text-muted-foreground/40">Active Station</span>
                    <span className="text-foreground/80 font-mono">QC-01</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-rams-line pb-3 text-[10px] font-black uppercase tracking-widest">
                    <span className="text-muted-foreground/40">Sample Magnitude</span>
                    <span className="text-foreground/80">05 UNITS</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b border-rams-line bg-rams-panel/20 p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('quality.inspection.detail.checklist') || 'Inspection Checklist'}</CardTitle>
              <Badge variant="outline" className="rounded-none border-rams-orange/20 bg-rams-orange/5 text-rams-orange text-[8px] font-black uppercase h-4 px-1">3/5_COMPLETED</Badge>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-rams-line/30">
                {[
                  { id: 1, task: 'Verify material certification matches batch', status: 'passed' },
                  { id: 2, task: 'Dimensional check: Overall length (150mm ±0.05)', status: 'passed' },
                  { id: 3, task: 'Dimensional check: Bore diameter (25mm +0.02/-0.00)', status: 'passed' },
                  { id: 4, task: 'Visual check: Surface finish for burrs or scratches', status: 'pending' },
                  { id: 5, task: 'Hardness test: Rockwell C 30-35', status: 'pending' },
                ].map((item) => (
                  <div key={item.id} className="p-5 flex items-center justify-between hover:bg-rams-panel transition-none group">
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "h-8 w-8 border flex items-center justify-center transition-none",
                        item.status === 'passed' ? "bg-rams-green/5 border-rams-green/20 text-rams-green" : "bg-rams-panel border-rams-line text-muted-foreground/20"
                      )}>
                        {item.status === 'passed' && <CheckCircle2 className="h-4 w-4" />}
                      </div>
                      <span className="text-xs font-medium text-foreground/70 uppercase leading-snug">{item.task}</span>
                    </div>
                    {item.status === 'passed' ? (
                      <Badge variant="success" size="sm" className="rounded-none text-[8px] font-black h-4">PASS</Badge>
                    ) : (
                      <div className="flex items-center gap-1">
                        <Button variant="outline" size="sm" className="h-7 px-3 text-[8px] font-black uppercase rounded-none border-rams-green/20 text-rams-green hover:bg-rams-green/5 transition-none">PASS</Button>
                        <Button variant="outline" size="sm" className="h-7 px-3 text-[8px] font-black uppercase rounded-none border-rams-red/20 text-rams-red hover:bg-rams-red/5 transition-none">FAIL</Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('quality.inspection.detail.assignmentTelemetry') || 'Assignment Telemetry'}</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <div className="flex items-center gap-3">
                  <Calendar className="h-3.5 w-3.5 opacity-40" />
                  <span>{t('quality.inspection.detail.scheduledSync') || 'Scheduled Sync'}</span>
                </div>
                <span className="font-mono font-bold text-foreground/80">{inspection.inspection_date ? formatDate(inspection.inspection_date).toUpperCase() : '—'}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 border-t border-rams-line pt-4">
                <div className="flex items-center gap-3">
                  <User className="h-3.5 w-3.5 opacity-40" />
                  <span>{t('quality.inspection.detail.leadInspector') || 'Lead Inspector'}</span>
                </div>
                <span className="font-bold text-foreground/80">{inspection.inspector?.full_name.toUpperCase() || t('common.unassigned') || 'UNASSIGNED'}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden relative">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('quality.inspection.detail.resultsAnalytics') || 'Results Analytics'}</CardTitle>
            </CardHeader>
            <CardContent className="p-8 text-center space-y-6 relative z-10">
              <div className="inline-flex p-4 bg-rams-panel border border-rams-line text-rams-orange">
                <ClipboardCheck className="h-10 w-10" />
              </div>
              <div className="space-y-2">
                <p className="font-mono font-bold text-3xl tabular-nums text-foreground/90">0.0%</p>
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">Defect Node Probability</p>
              </div>
              <p className="text-[9px] font-mono text-muted-foreground/20 uppercase tracking-[0.3em] mt-4">Calculated from verified checks</p>
            </CardContent>
            <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
          </Card>
        </div>
      </div>
    </div>
  );
}
