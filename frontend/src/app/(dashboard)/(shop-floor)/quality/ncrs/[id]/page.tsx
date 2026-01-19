'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  AlertTriangle,
  Clock,
  User,
  CheckCircle2,
  AlertCircle,
  FileText,
  History,
  MessageSquare,
  ShieldAlert,
  Save,
  MoreHorizontal,
  Search,
  Edit,
  Trash2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useQualityStore } from '@/stores/quality';
import { cn, formatDate } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

export default function NCRDetailsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useParams();
  const { ncrs, fetchNCRs } = useQualityStore();

  const ncr = React.useMemo(() => 
    ncrs.find(n => n.id === params?.id) || ncrs[0], 
    [ncrs, params?.id]
  );

  React.useEffect(() => {
    if (ncrs.length === 0) {
      fetchNCRs();
    }
  }, [ncrs.length, fetchNCRs]);

  if (!ncr) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <div className="animate-spin h-8 w-8 border-2 border-rams-orange border-t-transparent"></div>
      </div>
    );
  }

  const statusConfig = {
    open: { label: 'Open', variant: 'warning' as const, icon: AlertCircle },
    investigating: { label: 'Investigating', variant: 'default' as const, icon: Search },
    disposed: { label: 'Disposed', variant: 'success' as const, icon: CheckCircle2 },
    closed: { label: 'Closed', variant: 'secondary' as const, icon: ShieldAlert },
  };

  const severityConfig = {
    minor: { label: 'Minor', class: 'bg-rams-panel text-muted-foreground' },
    major: { label: 'Major', class: 'bg-rams-orange/10 text-rams-orange' },
    critical: { label: 'Critical', class: 'bg-rams-red/10 text-rams-red' },
  };

  return (
    <div className="space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.push('/quality?tab=ncrs')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{ncr.ncr_number}</h1>
              <Badge variant={statusConfig[ncr.status as keyof typeof statusConfig]?.variant || 'secondary'} size="sm" className="h-4 px-1 rounded-none font-black text-[8px] uppercase tracking-widest">
                {(statusConfig[ncr.status as keyof typeof statusConfig]?.label || ncr.status).toUpperCase()}
              </Badge>
              <Badge variant="outline" className={cn("rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel", severityConfig[ncr.severity as keyof typeof severityConfig]?.class.replace('bg-', 'border-').split(' ')[0])}>
                {(severityConfig[ncr.severity as keyof typeof severityConfig]?.label || ncr.severity).toUpperCase()}
              </Badge>
            </div>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2 mt-1">
              <span>{t('quality.ncr.detail.subtitle') || 'Non-Conformance Intelligence Node'}</span>
              <span className="opacity-30">|</span>
              <span>STATION: QUALITY-CONTROL-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none">
            <MessageSquare className="h-3.5 w-3.5 mr-2" />
            {t('quality.ncr.detail.comment') || 'COMMENT'}
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            {t('quality.ncr.detail.assignCapa') || 'ASSIGN_CAPA'}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-10 w-10 border border-rams-line rounded-rams-sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Edit className="mr-2 h-3.5 w-3.5" /> {t('quality.ncr.detail.refineProtocol') || 'REFINE_PROTOCOL'}
              </DropdownMenuItem>
              <DropdownMenuItem>
                <History className="mr-2 h-3.5 w-3.5" /> {t('quality.ncr.detail.viewLogs') || 'VIEW_LOGS'}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-rams-red">
                <Trash2 className="mr-2 h-3.5 w-3.5" /> {t('quality.ncr.detail.terminateNode') || 'TERMINATE_NODE'}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('quality.ncr.detail.discrepancyIntelligence') || 'Discrepancy Intelligence'}</CardTitle>
            </CardHeader>
            <CardContent className="p-8 space-y-8">
              <div className="grid gap-8 sm:grid-cols-2">
                <div className="space-y-4">
                  <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40 mb-2">{t('quality.ncr.detail.subjectiveData') || 'Subjective Data'}</div>
                  <p className="text-xs font-medium text-foreground/70 uppercase leading-relaxed">{ncr.description || t('quality.ncr.detail.noDescription') || 'No description provided.'}</p>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between items-center border-b border-rams-line pb-3 text-[10px] font-black uppercase tracking-widest">
                    <span className="text-muted-foreground/40">Product Node</span>
                    <span className="text-foreground/80">Precision Bracket Type Alpha</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-rams-line pb-3 text-[10px] font-black uppercase tracking-widest">
                    <span className="text-muted-foreground/40">Work Order Sync</span>
                    <span className="text-foreground/80 font-mono">WO-2024-001</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-rams-line pb-3 text-[10px] font-black uppercase tracking-widest">
                    <span className="text-muted-foreground/40">Magnitude Affected</span>
                    <span className="text-foreground/80 font-mono">12 PCS</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="investigation" className="animate-in fade-in duration-500">
            <TabsList className="bg-rams-panel border border-rams-line p-1 rounded-rams-sm w-fit">
              <TabsTrigger value="investigation">{t('quality.ncr.detail.tabs.rootCause') || 'ROOT_CAUSE_ANALYSIS'}</TabsTrigger>
              <TabsTrigger value="disposition">{t('quality.ncr.detail.tabs.disposition') || 'DISPOSITION_NODE'}</TabsTrigger>
              <TabsTrigger value="attachments">{t('quality.ncr.detail.tabs.evidence') || 'EVIDENCE_NODES'}</TabsTrigger>
              <TabsTrigger value="history">{t('quality.ncr.detail.tabs.eventLog') || 'EVENT_LOG'}</TabsTrigger>
            </TabsList>
            <TabsContent value="investigation" className="mt-6 space-y-4">
              <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
                <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('quality.ncr.detail.investigationProtocol') || 'Investigation Protocol'}</CardTitle>
                </CardHeader>
                <CardContent className="p-8 space-y-8 bg-rams-module">
                  <div className="p-6 bg-rams-panel/40 border border-rams-line relative overflow-hidden group">
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-rams-orange mb-4">Finding Entry [LOG_01]</h4>
                    <p className="text-xs font-medium text-foreground/70 uppercase leading-relaxed relative z-10">
                      Initial investigation suggests a misalignment in the fixture during the secondary milling operation.
                      The coolant flow was also found to be partially blocked, leading to heat buildup within the machining cluster.
                    </p>
                    <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
                  </div>
                  <div className="grid gap-8 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">Anomalous Category</Label>
                      <div className="p-3 bg-rams-panel border border-rams-line text-[11px] font-bold text-foreground/80 uppercase">Machine Failure</div>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">Investigated By</Label>
                      <div className="flex items-center gap-3 p-3 bg-rams-panel border border-rams-line">
                        <Avatar className="h-5 w-5 rounded-none border border-rams-line">
                          <AvatarFallback className="text-[8px] font-mono">SJ</AvatarFallback>
                        </Avatar>
                        <span className="text-[11px] font-bold text-foreground/80 uppercase">Sarah Johnson</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">Telemetry Metadata</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <div className="flex items-center gap-3">
                  <Clock className="h-3.5 w-3.5 opacity-40" />
                  <span>Reported Pulse</span>
                </div>
                <span className="font-mono font-bold text-foreground/80">{formatDate(ncr.created_at).toUpperCase()}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 border-t border-rams-line pt-4">
                <div className="flex items-center gap-3">
                  <User className="h-3.5 w-3.5 opacity-40" />
                  <span>Reporter Node</span>
                </div>
                <span className="font-bold text-foreground/80">JOHN SMITH</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 border-t border-rams-line pt-4">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-3.5 w-3.5 opacity-40" />
                  <span>Dept_Node</span>
                </div>
                <span className="font-bold text-foreground/80">PRODUCTION</span>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-rams-red" />
                Containment Protocols
              </CardTitle>
            </CardHeader>
            <CardContent className="p-1 space-y-1 bg-rams-module">
              {[
                { label: 'Isolate affected batch', status: 'completed' },
                { label: 'Stop machine station CNC-04', status: 'completed' },
                { label: 'Inspect previous 10 units', status: 'in_progress' },
              ].map((action, i) => (
                <div key={i} className="flex items-center gap-4 p-4 bg-rams-panel/40 border border-rams-line transition-none group hover:bg-rams-panel">
                  <div className={cn(
                    "h-6 w-6 border flex items-center justify-center transition-none",
                    action.status === 'completed' ? "bg-rams-green/5 border-rams-green/20 text-rams-green" : "bg-rams-orange/5 border-rams-orange/20 text-rams-orange animate-pulse"
                  )}>
                    {action.status === 'completed' ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
                  </div>
                  <span className={cn(
                    "text-[11px] font-bold uppercase transition-none",
                    action.status === 'completed' ? "text-muted-foreground/40 line-through" : "text-foreground/70"
                  )}>
                    {action.label}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
