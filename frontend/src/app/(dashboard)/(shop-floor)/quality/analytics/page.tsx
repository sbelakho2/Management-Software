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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Quality Analytics</h1>
            <p className="text-muted-foreground">Quality performance metrics and predictive insights</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline">
            <Calendar className="mr-2 h-4 w-4" />
            Last 30 Days
          </Button>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export Data
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>First Pass Yield</CardDescription>
            <CardTitle className="text-2xl">{fpyTrend?.current_value || '94.2'}%</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-xs flex items-center gap-1 font-medium",
              (fpyTrend?.change_percent || 0) >= 0 ? "text-green-600" : "text-red-600"
            )}>
              {fpyTrend?.trend === 'up' ? <TrendingUp className="h-3 w-3" /> : <TrendingUp className="h-3 w-3 rotate-180" />}
              {Math.abs(fpyTrend?.change_percent || 1.5)}% vs last month
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Open NCRs</CardDescription>
            <CardTitle className="text-2xl">{totalNcrs}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground font-medium">
              Awaiting disposition
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active CAPAs</CardDescription>
            <CardTitle className="text-2xl">{totalCapas}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground font-medium">
              In implementation/verification
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg Inspection Time</CardDescription>
            <CardTitle className="text-2xl">18.5m</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-green-600 flex items-center gap-1 font-medium">
              <TrendingUp className="h-3 w-3 rotate-180" />
              -2.4% vs last week
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
