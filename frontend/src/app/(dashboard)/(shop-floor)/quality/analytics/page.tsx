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

export default function QualityAnalyticsPage() {
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
    <div className="space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">Quality Intelligence</h1>
            <p className="text-muted-foreground font-medium text-sm">Performance metrics and prescriptive organizational insights</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            <Calendar className="mr-2 h-4 w-4" />
            Strategic Window
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
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">First Pass Yield</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-success to-success/70">{fpyTrend?.current_value || '94.2'}%</div>
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-[10px] font-bold uppercase tracking-widest flex items-center gap-1",
              (fpyTrend?.change_percent || 0) >= 0 ? "text-success" : "text-danger"
            )}>
              {fpyTrend?.trend === 'up' ? <TrendingUp className="h-3 w-3" /> : <TrendingUp className="h-3 w-3 rotate-180" />}
              {Math.abs(fpyTrend?.change_percent || 1.5)}% vs LAST CYCLE
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Active NCRs</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-danger to-danger/70">{totalNcrs}</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
              Awaiting Disposition
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Active CAPAs</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-warning to-warning/70">{totalCapas}</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
              In Implementation Phase
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Mean Inspection Time</CardDescription>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">18.5m</div>
          </CardHeader>
          <CardContent>
            <div className="text-[10px] font-bold uppercase tracking-widest text-success flex items-center gap-1">
              <TrendingUp className="h-3 w-3 rotate-180" />
              -2.4% VELOCITY GAIN
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Inspection Outcomes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: 'Passed', count: 412, color: 'bg-green-500' },
              { label: 'Failed', count: 24, color: 'bg-red-500' },
              { label: 'Conditional', count: 12, color: 'bg-yellow-500' },
            ].map((item) => (
              <div key={item.label} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{item.label}</span>
                  <span className="text-muted-foreground">{item.count} ({Math.round(item.count / 448 * 100)}%)</span>
                </div>
                <Progress value={(item.count / 448) * 100} className={cn("h-2", item.color)} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>NCR Root Causes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
             {[
              { label: 'Machine Calibration', count: 15, impact: 'High' },
              { label: 'Material Defect', count: 8, impact: 'Medium' },
              { label: 'Operator Error', count: 5, impact: 'Medium' },
              { label: 'Tooling Wear', count: 3, impact: 'Low' },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-muted">
                    <AlertTriangle className="h-4 w-4 text-warning" />
                  </div>
                  <div>
                    <div className="text-sm font-medium">{item.label}</div>
                    <div className="text-xs text-muted-foreground">{item.count} occurrences</div>
                  </div>
                </div>
                <Badge variant={item.impact === 'High' ? 'danger' : item.impact === 'Medium' ? 'warning' : 'secondary'}>
                  {item.impact}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Predictive Quality (ML Insight)</CardTitle>
          <CardDescription>Models predict likely quality issues based on current production parameters</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex gap-4">
            <div className="p-3 bg-amber-100 rounded-full h-fit">
              <Shield className="h-6 w-6 text-amber-700" />
            </div>
            <div className="space-y-1">
              <h4 className="font-bold text-amber-900">High Risk: Part #882-C Line 4</h4>
              <p className="text-sm text-amber-800">
                Current humidity and tool vibration levels on Line 4 suggest a 22% increase in surface finish defects over the next 4 hours.
              </p>
              <div className="pt-2">
                <Button size="sm" variant="outline" className="border-amber-300 text-amber-900 hover:bg-amber-100">
                  Adjust Parameters
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
