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
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">Signal Intelligence</h1>
            <p className="text-muted-foreground font-medium text-sm">Operational performance telemetry and predictive response trends</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            <Calendar className="mr-2 h-4 w-4" />
            Last {days} Days
          </Button>
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            <Download className="mr-2 h-4 w-4" />
            Export Intel
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Mean Acknowledge Pulse</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight ">{analytics?.avg_response_time_minutes || 0}m</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
              Temporal gap to engagement
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Mean Resolution Velocity</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight ">{analytics?.avg_resolution_time_minutes || 0}m</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
              Full protocol lifecycle
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Total Intelligence Signals</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight ">{signals}</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
              Aggregated across all nodes
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Global Uptime Impact</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight text-red-600 dark:text-red-500">-{analytics?.uptime_impact_percent || 0}%</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-danger/40">
              Estimated operational leakage
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden shadow-premium">
          <CardHeader className="border-b border-border/5 bg-muted/5 p-6">
            <CardTitle className="font-heading font-bold text-lg tracking-tight">Signal Taxonomy</CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Distribution by categorical node</CardDescription>
          </CardHeader>
          <CardContent className="p-8 space-y-8">
            {Object.entries(analytics?.signals_by_category || {}).map(([label, count]) => (
              <div key={label} className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-widest text-foreground/70 capitalize">{label} Protocols</span>
                  <span className="text-[10px] font-mono font-bold text-primary/60 bg-primary/5 px-2 py-0.5 rounded-full">{count} EVENTS ({signals > 0 ? Math.round(count / signals * 100) : 0}%)</span>
                </div>
                <div className="h-2 rounded-full bg-muted/20 overflow-hidden shadow-inner-soft">
                  <div 
                    className="h-full bg-gradient-to-r from-primary to-primary/60 transition-all duration-1000" 
                    style={{ width: `${signals > 0 ? (count / signals) * 100 : 0}%` }} 
                  />
                </div>
              </div>
            ))}
            {(!analytics || Object.keys(analytics.signals_by_category).length === 0) && (
              <div className="text-center py-12 text-muted-foreground/40 italic font-medium">No signals identified in current window.</div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden shadow-premium">
          <CardHeader className="border-b border-border/5 bg-muted/5 p-6">
            <CardTitle className="font-heading font-bold text-lg tracking-tight">Anomalous Nodes</CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Highest frequency disruption points</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border/5">
              {(analytics?.top_problem_stations || []).map((item) => (
                <div key={item.station_id} className="flex items-center justify-between p-6 transition-all hover:bg-danger/[0.02] group">
                  <div className="flex items-center gap-5">
                    <div className="h-12 w-12 rounded-2xl bg-danger/5 border border-danger/10 flex items-center justify-center font-mono font-bold text-xs text-danger/60 group-hover:scale-110 transition-transform duration-500 shadow-sm">
                      {item.station_id.substring(0, 5)}
                    </div>
                    <div>
                      <p className="font-heading font-bold text-sm tracking-tight text-foreground/80">{item.count} Strategic Signals</p>
                      <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">Cumulative Operational Delay</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-heading font-bold text-danger text-red-600 dark:text-red-500">{item.downtime_hours}h</div>
                  </div>
                </div>
              ))}
              {(!analytics || analytics.top_problem_stations.length === 0) && (
                <div className="text-center py-24 text-muted-foreground/40 italic font-medium">No problematic nodes identified.</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
