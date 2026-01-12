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
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { useAndonStore } from '@/stores/andon-store';

export default function AndonAnalyticsPage() {
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Andon Analytics</h1>
            <p className="text-muted-foreground">Operational performance and response time trends</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline">
            <Calendar className="mr-2 h-4 w-4" />
            Last {days} Days
          </Button>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Download
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg. Response Time</CardDescription>
            <CardTitle className="text-2xl">{analytics?.avg_response_time_minutes || 0}m</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground flex items-center gap-1 font-medium">
              Time to acknowledge
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg. Resolution Time</CardDescription>
            <CardTitle className="text-2xl">{analytics?.avg_resolution_time_minutes || 0}m</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground flex items-center gap-1 font-medium">
              Time to resolve
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Signals</CardDescription>
            <CardTitle className="text-2xl">{signals}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground font-medium">
              Across all categories
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Uptime Impact</CardDescription>
            <CardTitle className="text-2xl">-{analytics?.uptime_impact_percent || 0}%</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground font-medium">
              Estimated production loss
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Signals by Category</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(analytics?.signals_by_category || {}).map(([label, count]) => (
              <div key={label} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium capitalize">{label}</span>
                  <span className="text-muted-foreground">{count} events ({signals > 0 ? Math.round(count / signals * 100) : 0}%)</span>
                </div>
                <Progress value={signals > 0 ? (count / signals) * 100 : 0} className="h-2" />
              </div>
            ))}
            {(!analytics || Object.keys(analytics.signals_by_category).length === 0) && (
              <p className="text-sm text-muted-foreground py-4 text-center">No data available for this period</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Problem Stations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(analytics?.top_problem_stations || []).map((item) => (
              <div key={item.station_id} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded bg-muted flex items-center justify-center font-bold text-xs uppercase">
                    {item.station_id.substring(0, 5)}
                  </div>
                  <div>
                    <div className="text-sm font-medium">{item.count} Total Signals</div>
                    <div className="text-xs text-muted-foreground">Cumulative downtime</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-red-600">{item.downtime_hours}h</div>
                </div>
              </div>
            ))}
            {(!analytics || analytics.top_problem_stations.length === 0) && (
              <p className="text-sm text-muted-foreground py-4 text-center">No problematic stations found</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
