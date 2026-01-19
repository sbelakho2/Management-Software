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
  Edit,
  Trash2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useQualityStore } from '@/stores/quality';
import { cn, formatDate } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

export default function CAPADetailsPage() {
  const { t } = useI18n();
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
        <div className="animate-spin h-8 w-8 border-2 border-rams-orange border-t-transparent"></div>
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
    low: { label: 'Low', class: 'bg-rams-panel text-muted-foreground' },
    medium: { label: 'Medium', class: 'bg-rams-steel/10 text-rams-steel' },
    high: { label: 'High', class: 'bg-rams-orange/10 text-rams-orange' },
    urgent: { label: 'Urgent', class: 'bg-rams-red/10 text-rams-red' },
  };

  return (
    <div className="space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.push('/quality?tab=capas')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{capa.capa_number}</h1>
              <Badge variant={statusConfig[capa.status as keyof typeof statusConfig]?.variant || 'secondary'} size="sm" className="h-4 px-1 rounded-none font-black text-[8px] uppercase tracking-widest">
                {(statusConfig[capa.status as keyof typeof statusConfig]?.label || capa.status).toUpperCase()}
              </Badge>
              <Badge variant="outline" className={cn("rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel", priorityConfig[(capa as any).priority as keyof typeof priorityConfig]?.class.replace('bg-', 'border-').split(' ')[0])}>
                {(priorityConfig[(capa as any).priority as keyof typeof priorityConfig]?.label || (capa as any).priority).toUpperCase()}
              </Badge>
            </div>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2 mt-1">
              <span>{t('quality.capa.detail.subtitle') || 'Corrective & Preventive Intelligence'}</span>
              <span className="opacity-30">|</span>
              <span>STATION: QUALITY-PLANNING-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none">
            {t('quality.capa.detail.exportProtocol') || 'EXPORT_PROTOCOL'}
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            {t('quality.capa.detail.commitAction') || 'COMMIT_ACTION'}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-10 w-10 border border-rams-line rounded-rams-sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Edit className="mr-2 h-3.5 w-3.5" /> {t('quality.capa.detail.refineCapa') || 'REFINE_CAPA'}
              </DropdownMenuItem>
              <DropdownMenuItem>
                <ShieldCheck className="mr-2 h-3.5 w-3.5" /> {t('quality.capa.detail.verifyEffectiveness') || 'VERIFY_EFFECTIVENESS'}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-rams-red">
                <Trash2 className="mr-2 h-3.5 w-3.5" /> {t('quality.capa.detail.terminateNode') || 'TERMINATE_NODE'}
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
                {t('quality.capa.detail.implementationMagnitude') || 'Implementation Magnitude'}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-8 space-y-10 bg-rams-module">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground/60">
                  <span>{t('quality.capa.detail.syncPulse') || 'Implementation Synchronization Pulse'}</span>
                  <span className="text-rams-orange">65%</span>
                </div>
                <div className="h-1 bg-rams-panel border border-rams-line overflow-hidden">
                  <div className="h-full bg-rams-orange transition-all duration-1000" style={{ width: '65%' }} />
                </div>
              </div>
              <div className="grid gap-8 sm:grid-cols-2">
                <div className="space-y-4">
                  <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40 mb-2">{t('quality.capa.detail.problemStatement') || 'Problem Statement'}</div>
                  <p className="text-xs font-medium text-foreground/70 uppercase leading-relaxed">{capa.description || 'Recurring misalignment issues in CNC production line Bravo.'}</p>
                </div>
                <div className="space-y-4">
                  <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40 mb-2">{t('quality.capa.detail.rootCauseAnalysis') || 'Root Cause Analysis'}</div>
                  <p className="text-xs font-medium text-foreground/70 uppercase leading-relaxed">Worn vibration dampeners on CNC-04 and outdated calibration schedule synchronization.</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="actions" className="animate-in fade-in duration-500">
            <TabsList className="bg-rams-panel border border-rams-line p-1 rounded-rams-sm w-fit">
              <TabsTrigger value="actions">{t('quality.capa.detail.tabs.actionProtocol') || 'ACTION_PROTOCOL'}</TabsTrigger>
              <TabsTrigger value="verification">{t('quality.capa.detail.tabs.effectivenessSync') || 'EFFECTIVENESS_SYNC'}</TabsTrigger>
              <TabsTrigger value="related">{t('quality.capa.detail.tabs.relatedAnomalies') || 'RELATED_ANOMALIES'}</TabsTrigger>
            </TabsList>
            <TabsContent value="actions" className="mt-6 space-y-4">
              <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between border-b border-rams-line bg-rams-panel/20 p-6">
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('quality.capa.detail.countermeasureNodes') || 'Countermeasure Nodes'}</CardTitle>
                  <Button variant="outline" size="sm" className="rounded-rams-sm border-rams-line h-8 text-[9px] font-black uppercase tracking-widest">
                    <Plus className="mr-2 h-3.5 w-3.5" />
                    {t('quality.capa.detail.addNode') || 'ADD_NODE'}
                  </Button>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="divide-y divide-rams-line/30">
                    {[
                      { title: 'Replace vibration dampeners on CNC-04', assignee: 'MIKE TECH', due: '2024-02-15', status: 'completed' },
                      { title: 'Update preventive maintenance schedule for all CNC machines', assignee: 'SARAH OPS', due: '2024-02-20', status: 'in_progress' },
                      { title: 'Conduct refresher training for CNC operators', assignee: 'JOHN TRAIN', due: '2024-03-01', status: 'pending' },
                    ].map((action, i) => (
                      <div key={i} className="p-5 flex items-center justify-between hover:bg-rams-panel transition-none group cursor-help">
                        <div className="flex items-center gap-6">
                          <div className={cn(
                            "h-10 w-10 border flex items-center justify-center transition-none",
                            action.status === 'completed' ? "bg-rams-green/5 border-rams-green/20 text-rams-green" :
                            action.status === 'in_progress' ? "bg-rams-orange/10 border-rams-orange text-rams-orange animate-pulse" :
                            "bg-rams-panel border-rams-line text-muted-foreground/20"
                          )}>
                            {action.status === 'completed' ? <CheckCircle2 className="h-5 w-5" /> : 
                             action.status === 'in_progress' ? <Zap className="h-5 w-5" /> : 
                             <Clock className="h-5 w-5" />}
                          </div>
                          <div>
                            <div className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{action.title}</div>
                            <div className="flex items-center gap-6 mt-1.5 text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">
                              <span className="flex items-center gap-2">
                                <User className="h-3 w-3" />
                                {action.assignee}
                              </span>
                              <span className="flex items-center gap-2">
                                <Calendar className="h-3 w-3" />
                                {action.due}
                              </span>
                            </div>
                          </div>
                        </div>
                        <Badge variant={action.status === 'completed' ? 'success' : action.status === 'in_progress' ? 'warning' : 'secondary'} size="sm" className="h-4 px-1 rounded-none font-black text-[8px] uppercase tracking-widest">
                          {action.status.toUpperCase()}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">Management Protocols</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <div className="flex items-center gap-3">
                  <Calendar className="h-3.5 w-3.5 opacity-40" />
                  <span>Target Horizon</span>
                </div>
                <span className="font-mono font-bold text-rams-red tabular-nums">{capa.due_date ? formatDate(capa.due_date).toUpperCase() : '—'}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 border-t border-rams-line pt-4">
                <div className="flex items-center gap-3">
                  <User className="h-3.5 w-3.5 opacity-40" />
                  <span>Capa Owner</span>
                </div>
                <span className="font-bold text-foreground/80">SARAH JOHNSON</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 border-t border-rams-line pt-4">
                <div className="flex items-center gap-3">
                  <ShieldCheck className="h-3.5 w-3.5 opacity-40" />
                  <span>Sync Verification</span>
                </div>
                <span className="font-bold text-muted-foreground/30">PENDING_SYNC</span>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden relative">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">Impact Intelligence</CardTitle>
            </CardHeader>
            <CardContent className="p-8 space-y-8 relative z-10">
              <div className="space-y-2">
                <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Quality Deviation Index</span>
                <div className="text-xs font-medium text-foreground/70 uppercase leading-snug">Reduction in surface defects by estimated 15%</div>
              </div>
              <div className="space-y-2 border-t border-rams-line pt-6">
                <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Fiscal Delta (Monthly)</span>
                <div className="text-sm font-mono font-bold text-rams-green tabular-nums">+$2,400.00 SAVINGS</div>
              </div>
            </CardContent>
            <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
          </Card>
        </div>
      </div>
    </div>
  );
}
