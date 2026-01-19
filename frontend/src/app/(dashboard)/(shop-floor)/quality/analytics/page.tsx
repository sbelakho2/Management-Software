'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  ClipboardCheck,
  TrendingUp,
  AlertTriangle,
  Shield,
  Download,
  Calendar,
  CheckCircle,
  XCircle,
  Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useQualityStore, useAnalyticsStore } from '@/stores';
import { cn } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

export default function QualityAnalyticsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { totalInspections, totalNcrs, totalCapas, fetchInspections, fetchNCRs, fetchCAPAs } = useQualityStore();
  const { trends, fetchTrends, loading: analyticsLoading } = useAnalyticsStore();

  React.useEffect(() => {
    fetchInspections();
    fetchNCRs();
    fetchCAPAs();
    fetchTrends();
  }, [fetchInspections, fetchNCRs, fetchCAPAs, fetchTrends]);

  const fpyTrend = trends.find(t => t.metric === 'First Pass Yield');

  return (
    <div className="space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('quality.analytics.title') || 'Quality Intelligence'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('quality.analytics.subtitle') || 'Performance Metrics & Prescriptive Insights'}</span>
              <span className="opacity-30">|</span>
              <span>STATION: QUALITY-ANALYTICS-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line">
            <Calendar className="mr-2 h-3.5 w-3.5" />
            {t('quality.analytics.strategicWindow') || 'STRATEGIC_WINDOW'}
          </Button>
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line">
            <Download className="mr-2 h-3.5 w-3.5" />
            {t('quality.analytics.exportIntel') || 'EXPORT_INTEL'}
          </Button>
        </div>
      </div>

      <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-line bg-rams-line">
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('quality.analytics.firstPassYield') || 'First Pass Yield'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{fpyTrend?.current_value || '94.2'}%</div>
          <p className={cn(
            "text-[9px] font-mono font-bold uppercase tracking-widest mt-2 flex items-center gap-1",
            (fpyTrend?.change_percent || 0) >= 0 ? "text-rams-green" : "text-rams-red"
          )}>
            {fpyTrend?.trend === 'up' ? <TrendingUp className="h-3 w-3" /> : <TrendingUp className="h-3 w-3 rotate-180" />}
            {Math.abs(fpyTrend?.change_percent || 1.5)}% {t('quality.analytics.vsLastCycle') || 'vs LAST_CYCLE'}
          </p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('quality.analytics.activeAnomalies') || 'Active Anomalies (NCR)'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-red tabular-nums">{totalNcrs}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('quality.analytics.awaitingDisposition') || 'AWAITING_DISPOSITION'}</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('quality.analytics.resolutionProtocols') || 'Resolution Protocols (CAPA)'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{totalCapas}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('quality.analytics.implementationPhase') || 'IMPLEMENTATION_PHASE'}</p>
        </div>
        <div className="bg-rams-module p-6 border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('quality.analytics.meanInspectionPulse') || 'Mean Inspection Pulse'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">18.5M</div>
          <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2 flex items-center gap-1">
            <TrendingUp className="h-3 w-3 rotate-180" /> -2.4% {t('quality.analytics.velocityGain') || 'VELOCITY_GAIN'}
          </p>
        </div>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-3">
              <ClipboardCheck className="h-4 w-4 text-rams-orange" />
              {t('quality.analytics.inspectionGateOutcomes') || 'Inspection Gate Outcomes'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-8 space-y-8 bg-rams-module">
            {[
              { label: 'Gate Passed', count: 412, color: 'bg-rams-green' },
              { label: 'Gate Failed', count: 24, color: 'bg-rams-red' },
              { label: 'Conditional Authorization', count: 12, color: 'bg-rams-orange' },
            ].map((item) => (
              <div key={item.label} className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-widest text-foreground/70">{item.label}</span>
                  <span className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase">{item.count} NODES ({Math.round(item.count / 448 * 100)}%)</span>
                </div>
                <div className="h-1 bg-rams-panel border border-rams-line overflow-hidden">
                  <div className={cn("h-full transition-all duration-1000", item.color)} style={{ width: `${(item.count / 448) * 100}%` }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-3">
              <AlertTriangle className="h-4 w-4 text-rams-orange" />
              {t('quality.analytics.ncrRootCause') || 'NCR Root Cause Clusters'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 bg-rams-module">
            <div className="divide-y divide-rams-line/30">
               {[
                { label: 'Machine Calibration Sync', count: 15, impact: 'High' },
                { label: 'Material Node Defect', count: 8, impact: 'Medium' },
                { label: 'Operator Protocol Error', count: 5, impact: 'Medium' },
                { label: 'Tooling Wear Threshold', count: 3, impact: 'Low' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between p-5 hover:bg-rams-panel transition-none group cursor-help">
                  <div className="flex items-center gap-4">
                    <div className="p-2 rounded-none bg-rams-panel border border-rams-line text-muted-foreground/40 group-hover:border-rams-orange transition-none">
                      <AlertTriangle className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{item.label}</div>
                      <div className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-0.5">{item.count} ANOMALOUS_EVENTS</div>
                    </div>
                  </div>
                  <Badge variant={item.impact === 'High' ? 'danger' : item.impact === 'Medium' ? 'warning' : 'secondary'} size="sm" className="h-4 px-1 rounded-none font-black text-[8px] uppercase tracking-widest">
                    {item.impact.toUpperCase()}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-rams-sm border border-rams-orange/30 bg-rams-orange/5 overflow-hidden">
        <CardHeader className="bg-rams-orange/10 border-b border-rams-orange/20 p-6">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-3">
            <Shield className="h-4 w-4 text-rams-orange" />
              {t('quality.analytics.predictiveIntelligence') || 'Predictive Quality Intelligence (Sensei AI)'}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-8">
          <div className="flex flex-col md:flex-row gap-8 items-start">
            <div className="p-4 bg-rams-orange/10 border border-rams-orange/30 text-rams-orange rounded-none shadow-[2px_2px_0_0_rgba(255,190,0,0.1)]">
              <Shield className="h-8 w-8" />
            </div>
            <div className="space-y-6 flex-1">
              <div>
                <h4 className="font-sans font-black text-sm uppercase tracking-tight text-foreground/90">HIGH_RISK_SYNC: Part #882-C // Line 04</h4>
                <p className="text-xs font-medium text-muted-foreground/80 uppercase leading-relaxed mt-2">
                  Current humidity and tool vibration levels on Line 04 suggest a 22% increase in surface finish defects over the next 4-hour temporal horizon.
                </p>
              </div>
              <div className="flex gap-3">
                <Button size="sm" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[9px] h-9 px-6 transition-none">
                  {t('quality.analytics.adjustParameters') || 'ADJUST_PARAMETERS'}
                </Button>
                <Button variant="outline" size="sm" className="rounded-rams-sm border-rams-line text-[9px] font-black uppercase tracking-widest h-9 px-6 transition-none">
                  {t('quality.analytics.ignoreRisk') || 'IGNORE_RISK'}
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
