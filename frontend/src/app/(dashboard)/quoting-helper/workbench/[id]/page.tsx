'use client';

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  FileText, 
  Activity, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  User, 
  Calculator, 
  ShieldAlert,
  ChevronRight,
  Send,
  Download
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { useI18n } from '@/contexts/i18n-context';
import { useQuotingHelperStore } from '@/stores/quoting-helper';
import { usePipelineStore } from '@/stores/pipeline';
import { formatCurrency, formatDate, cn } from '@/lib/utils';
import { PageGuard } from '@/components/layout/page-guard';

export default function QuotingWorkbenchPage() {
  return <QuotingWorkbenchContent />;
}

function QuotingWorkbenchContent() {
  const { id: rfqId } = useParams();
  const router = useRouter();
  const { t } = useI18n();
  const { 
    workPackets, 
    fetchWorkPackets, 
    generateWorkPackets, 
    isLoading,
    quoteMemory,
    fetchQuoteMemory
  } = useQuotingHelperStore();
  const { currentRfq, fetchRfqDetails } = usePipelineStore();

  React.useEffect(() => {
    if (rfqId) {
      fetchWorkPackets(rfqId as string);
      fetchRfqDetails(rfqId as string);
      fetchQuoteMemory(rfqId as string);
    }
  }, [rfqId, fetchWorkPackets, fetchRfqDetails, fetchQuoteMemory]);

  const doneCount = workPackets.filter(p => p.status === 'done' || p.status === 'done_with_risks').length;
  const progress = workPackets.length > 0 ? (doneCount / workPackets.length) * 100 : 0;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <Clock className="h-8 w-8 animate-spin text-rams-orange" />
          <p className="text-[10px] font-mono font-black uppercase tracking-widest">{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-[1600px] mx-auto">
      {/* Header Section */}
      <div className="flex items-center justify-between bg-rams-panel p-6 border border-rams-line">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono font-bold text-rams-orange bg-rams-orange/10 px-2 py-0.5 border border-rams-orange/20 uppercase tracking-widest">
              {t('common.quotingHelper.workbench.title')}
            </span>
            <span className="text-muted-foreground/30">/</span>
            <span className="text-[10px] font-mono text-muted-foreground uppercase">{currentRfq?.rfq_number}</span>
          </div>
          <h1 className="text-2xl font-black uppercase tracking-tight italic">
            {currentRfq?.title || t('common.quotingHelper.workbench.title')}
          </h1>
          <p className="text-xs text-muted-foreground uppercase tracking-wider">
            {t('common.quotingHelper.workbench.subtitle')} — {currentRfq?.customer?.name}
          </p>
        </div>

        <div className="flex items-center gap-4">
          <Button variant="outline" className="h-10 border-rams-line bg-rams-module hover:bg-rams-panel-hover text-[10px] uppercase font-black tracking-widest">
            <Download className="mr-2 h-3.5 w-3.5" /> {t('common.quotingHelper.workbench.exportPackage')}
          </Button>
          <Button className="h-10 bg-rams-orange hover:bg-rams-orange/90 text-white text-[10px] uppercase font-black tracking-widest px-8">
            <Send className="mr-2 h-3.5 w-3.5" /> {t('common.quotingHelper.workbench.generateQuote')}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Left Column - RFQ Details & Files */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          <Card className="bg-rams-module border-rams-line shadow-none">
            <CardHeader className="border-b border-rams-line/50 pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-[11px] font-black uppercase tracking-[0.2em] flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-rams-orange" />
                  {t('common.quotingHelper.workbench.rfqPackage')}
                </CardTitle>
                <Badge variant="outline" className="text-[9px] font-mono border-rams-line">
                  {currentRfq?.revision ? `v${currentRfq.revision}.0` : 'v1.0'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <p className="text-[9px] text-muted-foreground uppercase font-bold tracking-widest">{t('common.quotingHelper.workbench.received')}</p>
                  <p className="text-[11px] font-mono">{formatDate(currentRfq?.received_date)}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-[9px] text-muted-foreground uppercase font-bold tracking-widest">{t('common.quotingHelper.workbench.deadline')}</p>
                  <p className="text-[11px] font-mono text-rams-red">{formatDate(currentRfq?.due_date)}</p>
                </div>
              </div>
              
              <Separator className="bg-rams-line/30" />
              
              <div className="space-y-3">
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">{t('common.quotingHelper.workbench.attachedFiles')}</p>
                <div className="space-y-1">
                  {currentRfq?.attachments && currentRfq.attachments.length > 0 ? (
                    currentRfq.attachments.map(file => (
                      <div key={file.id} className="flex items-center justify-between p-2 bg-rams-panel border border-rams-line hover:border-rams-orange/30 group cursor-pointer transition-colors">
                        <span className="text-[10px] font-mono text-foreground/70 group-hover:text-foreground">{file.filename}</span>
                        <ChevronRight className="h-3 w-3 text-muted-foreground/30 group-hover:text-rams-orange" />
                      </div>
                    ))
                  ) : (
                    <p className="text-[9px] text-muted-foreground italic uppercase px-2">{t('common.noData')}</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-rams-module border-rams-line shadow-none">
            <CardHeader className="border-b border-rams-line/50 pb-4">
              <CardTitle className="text-[11px] font-black uppercase tracking-[0.2em] flex items-center gap-2">
                <ShieldAlert className="h-3.5 w-3.5 text-rams-red" />
                {t('common.quotingHelper.workbench.activeRisks')}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-2">
                <div className="p-3 bg-rams-red/5 border border-rams-red/20 flex gap-3">
                  <AlertCircle className="h-4 w-4 text-rams-red shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[10px] font-black uppercase text-rams-red">{t('common.quotingHelper.workbench.risks.missingCentroid.title', 'Missing Centroid Data')}</p>
                    <p className="text-[9px] text-muted-foreground mt-1 uppercase leading-relaxed">{t('common.quotingHelper.workbench.risks.missingCentroid.desc', 'Blocked Stage 2A (EE Review). Required for placement estimation.')}</p>
                  </div>
                </div>
                <div className="p-3 bg-rams-orange/5 border border-rams-orange/20 flex gap-3">
                  <AlertCircle className="h-4 w-4 text-rams-orange shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[10px] font-black uppercase text-rams-orange">{t('common.quotingHelper.workbench.risks.longLead.title', 'Long Lead Material')}</p>
                    <p className="text-[9px] text-muted-foreground mt-1 uppercase leading-relaxed">{t('common.quotingHelper.workbench.risks.longLead.desc', 'U45 (MCU) has 26-week lead time. Sourcing alternate recommended.')}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Center Column - Stage Gates & Work Packets */}
        <div className="col-span-12 lg:col-span-8 space-y-6">
          <Card className="bg-rams-module border-rams-line shadow-none">
            <CardHeader className="border-b border-rams-line/50 pb-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-[11px] font-black uppercase tracking-[0.2em] flex items-center gap-2">
                    <Activity className="h-3.5 w-3.5 text-rams-orange" />
                    {t('common.quotingHelper.workbench.stageGateWorkflow')}
                  </CardTitle>
                  <CardDescription className="text-[9px] uppercase tracking-wider">{t('common.quotingHelper.workbench.parallelContribution')}</CardDescription>
                </div>
                <div className="text-right space-y-1">
                  <p className="text-[10px] font-mono font-bold">{t('common.quotingHelper.workbench.gatesComplete', { done: doneCount, total: workPackets.length })}</p>
                  <Progress value={progress} className="h-1 w-32 bg-rams-line" />
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              {workPackets.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-rams-line">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-4">{t('common.quotingHelper.workbench.noPackets')}</p>
                  <Button 
                    onClick={() => generateWorkPackets(rfqId as string)}
                    className="bg-rams-orange hover:bg-rams-orange/90 text-white text-[10px] uppercase font-black tracking-widest"
                  >
                    {t('common.quotingHelper.workbench.initialize')}
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {workPackets.map(packet => (
                    <div 
                      key={packet.id} 
                      className={cn(
                        "p-4 border bg-rams-panel group hover:border-rams-orange/40 transition-all cursor-pointer",
                        packet.status === 'done' || packet.status === 'done_with_risks' ? "border-rams-green/30" : "border-rams-line"
                      )}
                      onClick={() => router.push(`/quoting-helper/packet/${packet.id}`)}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <Badge variant="outline" className="text-[9px] font-mono uppercase bg-rams-module border-rams-line text-foreground/60">
                          {packet.discipline}
                        </Badge>
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] font-mono text-muted-foreground">{packet.status.toUpperCase().replace('_', ' ')}</span>
                          {packet.status === 'done' ? (
                            <CheckCircle2 className="h-3.5 w-3.5 text-rams-green" />
                          ) : packet.status === 'blocked' ? (
                            <AlertCircle className="h-3.5 w-3.5 text-rams-red" />
                          ) : (
                            <Clock className="h-3.5 w-3.5 text-muted-foreground/30" />
                          )}
                        </div>
                      </div>
                      <h4 className="text-[11px] font-black uppercase tracking-tight mb-2">
                        {t(`common.disciplines.${packet.discipline}.title`)} {t('common.quotingHelper.workbench.review')}
                      </h4>
                      <div className="flex items-center justify-between mt-4">
                        <div className="flex items-center gap-2">
                          <div className="h-5 w-5 rounded-full bg-rams-line flex items-center justify-center">
                            <User className="h-3 w-3 text-muted-foreground" />
                          </div>
                          <span className="text-[10px] text-muted-foreground uppercase">{packet.owner_id ? t('common.quotingHelper.workbench.assigned') : t('common.quotingHelper.workbench.unassigned')}</span>
                        </div>
                        <Button variant="ghost" size="sm" className="h-7 text-[9px] uppercase font-black hover:text-rams-orange">
                          {t('common.quotingHelper.workbench.openPacket')} <ChevronRight className="ml-1 h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Tabs defaultValue="costing" className="w-full">
            <TabsList className="bg-rams-panel border border-rams-line p-1 h-12 w-full justify-start rounded-none">
              <TabsTrigger value="costing" className="data-[state=active]:bg-rams-orange data-[state=active]:text-white text-[10px] uppercase font-black tracking-widest px-6 h-full rounded-none">
                <Calculator className="mr-2 h-3.5 w-3.5" /> {t('common.quotingHelper.workbench.costBuild')}
              </TabsTrigger>
              <TabsTrigger value="memory" className="data-[state=active]:bg-rams-orange data-[state=active]:text-white text-[10px] uppercase font-black tracking-widest px-6 h-full rounded-none">
                <Activity className="mr-2 h-3.5 w-3.5" /> {t('common.quotingHelper.workbench.quoteMemory')}
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="costing" className="mt-4">
              <Card className="bg-rams-module border-rams-line shadow-none">
                <CardContent className="p-6">
                  <div className="space-y-6">
                    <div className="grid grid-cols-4 gap-4">
                      {[
                        { label: t('common.quotingHelper.workbench.material'), value: 12450.50, color: 'text-foreground' },
                        { label: t('common.quotingHelper.workbench.labor'), value: 3200.00, color: 'text-foreground' },
                        { label: t('common.quotingHelper.workbench.nreTooling'), value: 1500.00, color: 'text-foreground' },
                        { label: t('common.quotingHelper.workbench.estimatedTotal'), value: 17150.50, color: 'text-rams-orange font-bold' },
                      ].map(item => (
                        <div key={item.label} className="p-4 bg-rams-panel border border-rams-line">
                          <p className="text-[9px] text-muted-foreground uppercase font-bold tracking-widest mb-1">{item.label}</p>
                          <p className={cn("text-lg font-mono tracking-tighter", item.color)}>
                            {formatCurrency(item.value, currentRfq?.currency || 'MAD')}
                          </p>
                        </div>
                      ))}
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">{t('common.quotingHelper.workbench.marginAnalysis')}</p>
                        <Badge className="bg-rams-green/10 text-rams-green border-rams-green/20 text-[9px] font-mono uppercase">{t('common.quotingHelper.workbench.healthy')}</Badge>
                      </div>
                      <div className="p-4 bg-rams-panel border border-rams-line flex items-center justify-between">
                        <div className="space-y-1">
                          <p className="text-[9px] text-muted-foreground uppercase font-bold tracking-widest">{t('common.quotingHelper.workbench.grossMargin')}</p>
                          <p className="text-xl font-black italic">28.5%</p>
                        </div>
                        <div className="h-10 w-[1px] bg-rams-line" />
                        <div className="space-y-1">
                          <p className="text-[9px] text-muted-foreground uppercase font-bold tracking-widest">{t('common.quotingHelper.workbench.targetMargin')}</p>
                          <p className="text-xl font-black italic text-muted-foreground/40">25.0%</p>
                        </div>
                        <div className="h-10 w-[1px] bg-rams-line" />
                        <div className="space-y-1">
                          <p className="text-[9px] text-muted-foreground uppercase font-bold tracking-widest">{t('common.quotingHelper.workbench.variance')}</p>
                          <p className="text-xl font-black italic text-rams-green">+3.5%</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="memory" className="mt-4">
              <Card className="bg-rams-module border-rams-line shadow-none">
                <CardContent className="p-6">
                  <div className="space-y-4">
                    {quoteMemory.length > 0 ? (
                      quoteMemory.map((mem, idx) => (
                        <div key={idx} className="space-y-4 border-b border-rams-line/30 pb-4 last:border-0 last:pb-0">
                          <div className="flex items-center gap-3 p-3 bg-rams-orange/5 border border-rams-orange/20 rounded-sm">
                            <ShieldAlert className="h-4 w-4 text-rams-orange" />
                            <p className="text-[10px] uppercase font-bold text-foreground/80 tracking-tight">
                              {t('common.quotingHelper.workbench.aiMatch', { 
                                percent: Math.round(mem.similarity * 100), 
                                job: `${mem.rfq_number} (${mem.title})` 
                              })}
                            </p>
                          </div>
                          
                          <div className="space-y-2">
                            <p className="text-[9px] text-muted-foreground uppercase font-bold tracking-widest">{t('common.quotingHelper.workbench.historicalAssumptions')}</p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                              {mem.past_assumptions && mem.past_assumptions.length > 0 ? (
                                mem.past_assumptions.map((note: string, nIdx: number) => (
                                  <div key={nIdx} className="p-2 bg-rams-panel border border-rams-line text-[10px] font-mono uppercase text-foreground/60">
                                    {note}
                                  </div>
                                ))
                              ) : (
                                <p className="text-[9px] text-muted-foreground italic">{t('common.noData')}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-8">
                        <p className="text-[10px] text-muted-foreground uppercase tracking-widest">{t('common.noResults')}</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
