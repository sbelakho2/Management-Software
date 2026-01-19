'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  BarChart3,
  TrendingUp,
  Clock,
  AlertTriangle,
  Download,
  Calendar,
  Loader2,
  Brain,
  Target,
  Activity,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useAndonStore } from '@/stores/andon-store';
import { useI18n } from '@/contexts/i18n-context';

export default function AndonAnalyticsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { analytics, analyticsLoading, fetchAnalytics } = useAndonStore();
  const [days, setDays] = React.useState(30);

  React.useEffect(() => {
    fetchAnalytics(days);
  }, [fetchAnalytics, days]);

  if (analyticsLoading && !analytics) {
    return (
      <div className="flex h-[400px] w-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const signals = analytics?.total_signals || 0;

  return (
    <div className="space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">{t('andon.analytics.title') || 'Signal Intelligence'}</h1>
            <p className="text-muted-foreground font-medium text-sm">{t('andon.analytics.subtitle') || 'Operational performance telemetry and predictive response trends'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-rams-sm border-rams-line hover:bg-rams-panel transition-none">
            <Calendar className="mr-2 h-4 w-4" />
            {t('andon.analytics.lastDays', { days }) || `Last ${days} Days`}
          </Button>
          <Button variant="outline" size="lg" className="rounded-rams-sm border-rams-line hover:bg-rams-panel transition-none">
            <Download className="mr-2 h-4 w-4" />
            {t('andon.analytics.exportIntel') || 'Export Intel'}
          </Button>
        </div>
      </div>

      <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
        <Card className="rounded-none border-0 bg-rams-module border-r border-b border-rams-line">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{t('andon.analytics.stats.meanAcknowledgePulse') || 'Mean Acknowledge Pulse'}</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight ">{analytics?.avg_response_time_minutes || 0}m</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
              {t('andon.analytics.stats.temporalGap') || 'Temporal gap to engagement'}
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-none border-0 bg-rams-module border-r border-b border-rams-line">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{t('andon.analytics.stats.meanResolutionVelocity') || 'Mean Resolution Velocity'}</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight ">{analytics?.avg_resolution_time_minutes || 0}m</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
              {t('andon.analytics.stats.fullProtocolLifecycle') || 'Full protocol lifecycle'}
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-none border-0 bg-rams-module border-r border-b border-rams-line">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{t('andon.analytics.stats.totalIntelligenceSignals') || 'Total Intelligence Signals'}</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight ">{signals}</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
              {t('andon.analytics.stats.aggregatedAcrossNodes') || 'Aggregated across all nodes'}
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-none border-0 bg-rams-module border-b border-rams-line">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{t('andon.analytics.stats.globalUptimeImpact') || 'Global Uptime Impact'}</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight text-red-600 dark:text-red-500">-{analytics?.uptime_impact_percent || 0}%</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-danger/40">
              {t('andon.analytics.stats.estimatedOperationalLeakage') || 'Estimated operational leakage'}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden shadow-none">
          <CardHeader className="border-b border-border/5 bg-muted/5 p-6">
            <CardTitle className="font-heading font-bold text-lg tracking-tight">{t('andon.analytics.signalTaxonomy.title') || 'Signal Taxonomy'}</CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{t('andon.analytics.signalTaxonomy.subtitle') || 'Distribution by categorical node'}</CardDescription>
          </CardHeader>
          <CardContent className="p-8 space-y-8">
            {Object.entries(analytics?.signals_by_category || {}).map(([label, count]) => (
              <div key={label} className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-widest text-foreground/70 capitalize">{label} Protocols</span>
                  <span className="text-[10px] font-mono font-bold text-rams-orange/60 bg-rams-panel px-2 py-0.5 border border-rams-line\">{count} EVENTS ({signals > 0 ? Math.round(count / signals * 100) : 0}%)</span>
                </div>
                <div className="h-1 bg-rams-panel border border-rams-line overflow-hidden">
                  <div 
                    className="h-full bg-rams-orange transition-all duration-500" 
                    style={{ width: `${signals > 0 ? (count / signals) * 100 : 0}%` }} 
                  />
                </div>
              </div>
            ))}
            {(!analytics || Object.keys(analytics.signals_by_category).length === 0) && (
              <div className="text-center py-12 text-muted-foreground/40 italic font-medium">{t('andon.analytics.signalTaxonomy.empty') || 'No signals identified in current window.'}</div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden shadow-none">
          <CardHeader className="border-b border-rams-line bg-rams-panel/20 p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('andon.analytics.anomalousNodes.title') || 'Anomalous Nodes'}</CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{t('andon.analytics.anomalousNodes.subtitle') || 'Highest frequency disruption points'}</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border/5">
              {(analytics?.top_problem_stations || []).map((item) => (
                <div key={item.station_id} className="flex items-center justify-between p-6 transition-none hover:bg-rams-panel group">
                  <div className="flex items-center gap-5">
                    <div className="h-10 w-10 bg-rams-panel border border-rams-line flex items-center justify-center font-mono font-bold text-xs text-rams-red/60">
                      {item.station_id.substring(0, 5)}
                    </div>
                    <div>
                      <p className="font-heading font-bold text-sm tracking-tight text-foreground/80">{item.count} {t('andon.analytics.anomalousNodes.strategicSignals') || 'Strategic Signals'}</p>
                      <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{t('andon.analytics.anomalousNodes.cumulativeDelay') || 'Cumulative Operational Delay'}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-heading font-bold text-danger text-red-600 dark:text-red-500">{item.downtime_hours}h</div>
                  </div>
                </div>
              ))}
              {(!analytics || analytics.top_problem_stations.length === 0) && (
                <div className="text-center py-24 text-muted-foreground/40 italic font-medium">{t('andon.analytics.anomalousNodes.empty') || 'No problematic nodes identified.'}</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
