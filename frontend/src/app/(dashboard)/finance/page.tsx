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
      <div className="space-y-8 page-fade-in" data-testid="finance-page">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="space-y-1">
            <h1 className="text-4xl font-heading font-bold tracking-tight ">
              Finance Control Plane
            </h1>
            <p className="text-muted-foreground font-medium">Revenue forecasting, operational expenditures, and margin intelligence</p>
          </div>
          <div className="flex items-center gap-3">
            <AmbientStatus status="operational" label="All Systems Nominal" />
            <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
              <Calendar className="mr-2 h-4 w-4" />
              Q1 2026
            </Button>
            <Button size="lg" className="rounded-xl shadow-glow subtle-shine">
              <Download className="mr-2 h-4 w-4" />
              Export Reports
            </Button>
          </div>
        </div>

        {/* Financial KPIs - Miller's Law Grouping */}
        <StatSection label="Financial Metrics" columns={4}>
          <StatCard
            value="$1.24M"
            label="Total Revenue (MTD)"
            icon={TrendingUp}
            iconColor="success"
            trend="up"
            trendValue="+8.2% vs last month"
            spotlight
          />
          <StatCard
            value="32.4%"
            label="Gross Margin"
            icon={TrendingDown}
            iconColor="danger"
            trend="down"
            trendValue="-1.5% vs target"
            critical
          />
          <StatCard
            value="$420K"
            label="OpEx (Actual vs Budget)"
            icon={DollarSign}
            iconColor="primary"
            goal={{ current: 92, target: 100 }}
          />
          <StatCard
            value="$2.8M"
            label="Cash on Hand"
            icon={CheckCircle2}
            iconColor="success"
            trend="up"
            trendValue="Strong liquidity"
          />
        </StatSection>

        <div className="grid gap-6 md:grid-cols-2">
          <ContentCard title="Revenue by Product Line" icon={BarChart3}>
            <div className="space-y-6">
              {[
                { label: 'Precision Components', value: 580000, color: 'bg-primary' },
                { label: 'Assembly Systems', value: 420000, color: 'bg-indigo-500' },
                { label: 'Aftermarket Services', value: 240000, color: 'bg-emerald-500' },
              ].map((item) => (
                <div key={item.label} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold uppercase tracking-wider">{item.label}</span>
                    <span className="text-sm font-bold font-heading">${(item.value / 1000).toFixed(0)}K</span>
                  </div>
                  <div className="goal-progress-track">
                    <div className={cn("goal-progress-fill", item.color)} style={{ width: `${(item.value / 1240000) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </ContentCard>

          <ContentCard title="Top Cost Drivers" icon={PieChart}>
            <div className="space-y-4 stagger-list">
              {[
                { label: 'Raw Materials (Steel/Aluminum)', trend: 'up', impact: 'High' },
                { label: 'Energy Consumption', trend: 'up', impact: 'Medium' },
                { label: 'Overtime Labor', trend: 'down', impact: 'Medium' },
                { label: 'Logistics/Freight', trend: 'stable', impact: 'Low' },
              ].map((item, i) => (
                <div key={item.label} className="flex items-center justify-between p-4 rounded-2xl bg-muted/20 border border-border/10 hover:bg-muted/30 transition-colors" style={{ '--stagger-index': i } as React.CSSProperties}>
                  <div className="flex items-center gap-4">
                    <div className={cn("p-2.5 rounded-xl", item.trend === 'up' ? "bg-danger/10 text-danger" : item.trend === 'down' ? "bg-emerald-500/10 text-emerald-600" : "bg-muted text-muted-foreground")}>
                      {item.trend === 'up' ? <TrendingUp className="h-4 w-4" /> : 
                      item.trend === 'down' ? <TrendingDown className="h-4 w-4" /> :
                      <BarChart3 className="h-4 w-4" />}
                    </div>
                    <div>
                      <div className="text-sm font-bold">{item.label}</div>
                      <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{item.impact} impact on margin</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ContentCard>
        </div>
      </div>
    </PageGuard>
  );
}

function cn_legacy(...classes: any[]) {
  return classes.filter(Boolean).join(' ');
}
