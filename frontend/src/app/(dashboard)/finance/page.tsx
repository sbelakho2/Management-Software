'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  PieChart, 
  Calendar,
  Download,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useAuthStore } from '@/stores';
import { PageGuard } from '@/components/layout/page-guard';
import { FINANCE_ROLES } from '@/lib/page-access';
import { cn } from '@/lib/utils';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';

export default function FinancePage() {
  const { t } = useI18n();
  const { isAuthenticated } = useAuthStore();

  return (
    <PageGuard requiredRoles={FINANCE_ROLES}>
      <div className="space-y-8 page-fade-in pb-12" data-testid="finance-page">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              Finance Control Plane
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>Revenue forecasting and margin intelligence</span>
              <span className="opacity-30">|</span>
              <span>STATION: FINANCE-01</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <AmbientStatus status="operational" label="All Systems Nominal" />
            <Button variant="outline" size="default" className="rounded-rams-sm border-rams-border">
              <Calendar className="mr-2 h-3.5 w-3.5" />
              Q1 2026
            </Button>
            <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]">
              <Download className="mr-2 h-3.5 w-3.5" />
              Export Intel
            </Button>
          </div>
        </div>

        {/* Financial KPIs */}
        <div className="grid gap-0 md:grid-cols-4 border border-rams-border bg-rams-border">
          <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0 group">
            <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Aggregated Revenue (MTD)</p>
            <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">$1.24M</div>
            <div className="flex items-center gap-1 text-[9px] font-mono font-bold uppercase tracking-tighter text-rams-green mt-2">
              <TrendingUp className="h-3 w-3" /> +8.2% ALPHA
            </div>
          </div>
          <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0 group">
            <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Gross Margin KPI</p>
            <div className="text-3xl font-mono font-bold tracking-tight text-rams-red tabular-nums">32.4%</div>
            <div className="flex items-center gap-1 text-[9px] font-mono font-bold uppercase tracking-tighter text-rams-red mt-2">
              <TrendingDown className="h-3 w-3" /> -1.5% DELTA
            </div>
          </div>
          <div className="bg-rams-module p-6 border-r border-b border-rams-border last:border-r-0 group">
            <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">OpEx Synchronization</p>
            <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">$420K</div>
            <div className="mt-4 space-y-1.5">
              <div className="goal-progress-track">
                <div className="goal-progress-fill bg-rams-orange" style={{ width: '92%' }} />
              </div>
              <div className="flex justify-between text-[8px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                <span>BUDGET_UTILIZATION</span>
                <span>92%</span>
              </div>
            </div>
          </div>
          <div className="bg-rams-module p-6 border-b border-rams-border group">
            <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Liquidity Reserve</p>
            <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">$2.8M</div>
            <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">OPTIMAL_STATE</p>
          </div>
        </div>

        <div className="grid gap-8 md:grid-cols-2">
          <Card className="rounded-rams-sm overflow-hidden border-rams-border">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-border">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-rams-orange" />
                Revenue by Product Line
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              {[
                { label: 'Precision Components', value: 580000, color: 'bg-rams-orange' },
                { label: 'Assembly Systems', value: 420000, color: 'bg-rams-steel' },
                { label: 'Aftermarket Services', value: 240000, color: 'bg-rams-green' },
              ].map((item) => (
                <div key={item.label} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase tracking-widest text-foreground/70">{item.label}</span>
                    <span className="text-sm font-mono font-bold tabular-nums">${(item.value / 1000).toFixed(0)}K</span>
                  </div>
                  <div className="goal-progress-track h-1.5">
                    <div className={cn("goal-progress-fill", item.color)} style={{ width: `${(item.value / 1240000) * 100}%` }} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="rounded-rams-sm overflow-hidden border-rams-border">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-border">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                <PieChart className="h-4 w-4 text-rams-orange" />
                Top Cost Drivers
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-rams-border/30">
                {[
                  { label: 'Raw Materials (Steel/Aluminum)', trend: 'up', impact: 'High' },
                  { label: 'Energy Consumption', trend: 'up', impact: 'Medium' },
                  { label: 'Overtime Labor', trend: 'down', impact: 'Medium' },
                  { label: 'Logistics/Freight', trend: 'stable', impact: 'Low' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between p-4 hover:bg-rams-panel transition-none group">
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "p-2 rounded-rams-sm border border-rams-border",
                        item.trend === 'up' ? "bg-rams-red/5 text-rams-red border-rams-red/20" : 
                        item.trend === 'down' ? "bg-rams-green/5 text-rams-green border-rams-green/20" : 
                        "bg-rams-panel text-muted-foreground"
                      )}>
                        {item.trend === 'up' ? <TrendingUp className="h-4 w-4" /> : 
                        item.trend === 'down' ? <TrendingDown className="h-4 w-4" /> :
                        <BarChart3 className="h-4 w-4" />}
                      </div>
                      <div>
                        <div className="text-[11px] font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{item.label}</div>
                        <div className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{item.impact} IMPACT_ON_MARGIN</div>
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-1 transition-all" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageGuard>
  );
}

function cn_legacy(...classes: any[]) {
  return classes.filter(Boolean).join(' ');
}
