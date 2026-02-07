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
  CheckCircle2,
  Loader2,
  ArrowRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useAuthStore, useFinanceStore } from '@/stores';
import { cn, formatCurrency } from '@/lib/utils';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';

// Fallback data when API is not available
const fallbackStats = {
  revenue_mtd: 1240000,
  revenue_change: 8.2,
  gross_margin: 32.4,
  margin_change: -1.5,
  opex: 420000,
  budget_utilization: 92,
  liquidity_reserve: 2800000,
  liquidity_status: 'optimal',
};

export default function FinancePage() {
  const { t } = useI18n();
  const { isAuthenticated } = useAuthStore();
  const { 
    dashboardStats,
    revenueByProduct,
    loading,
    fetchAll 
  } = useFinanceStore();

  // Fetch data on mount
  React.useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Use API data or fallback to demo data
  const stats = dashboardStats || fallbackStats;

  // Format currency with compact notation for large values (e.g., $1.2M)
  const formatCompactCurrency = (value: number) => {
    // Use Intl with compact notation for cleaner display
    return formatCurrency(value, undefined, undefined);
  };

  return (
      <div className="space-y-8 page-fade-in pb-12" data-testid="finance-page">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              {t('pages.finance.title') || 'Finance Control Plane'}
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('pages.finance.subtitle') || 'Revenue forecasting and margin intelligence'}</span>
              <span className="opacity-30">|</span>
              <span>{t('pages.finance.station') || 'STATION: FINANCE-01'}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <AmbientStatus status="operational" label={t('pages.finance.allSystemsNominal') || 'All Systems Nominal'} />
            <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line">
              <Calendar className="mr-2 h-3.5 w-3.5" />
              {t('pages.finance.quarter') || 'Q1 2026'}
            </Button>
            <Button 
              size="default" 
              className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]"
              disabled={loading}
              onClick={() => {
                // Export finance dashboard stats as JSON download
                const data = JSON.stringify(stats, null, 2);
                const blob = new Blob([data], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `finance-intel-${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                URL.revokeObjectURL(url);
                document.body.removeChild(a);
              }}
            >
              {loading ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <Download className="mr-2 h-3.5 w-3.5" />}
              {t('pages.finance.exportIntel') || 'Export Intel'}
            </Button>
          </div>
        </div>

        {/* Financial KPIs */}
        <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
          <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group">
            <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.finance.kpi.revenue') || 'Aggregated Revenue (MTD)'}</p>
            <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{formatCurrency(stats.revenue_mtd)}</div>
            <div className={cn(
              "flex items-center gap-1 text-[9px] font-mono font-bold uppercase tracking-tighter mt-2",
              stats.revenue_change >= 0 ? "text-rams-green" : "text-rams-red"
            )}>
              {stats.revenue_change >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {stats.revenue_change >= 0 ? '+' : ''}{stats.revenue_change}% {t('pages.finance.kpi.alpha') || 'ALPHA'}
            </div>
          </div>
          <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group">
            <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.finance.kpi.grossMargin') || 'Gross Margin KPI'}</p>
            <div className={cn(
              "text-3xl font-mono font-bold tracking-tight tabular-nums",
              stats.margin_change >= 0 ? "text-rams-green" : "text-rams-red"
            )}>{stats.gross_margin}%</div>
            <div className={cn(
              "flex items-center gap-1 text-[9px] font-mono font-bold uppercase tracking-tighter mt-2",
              stats.margin_change >= 0 ? "text-rams-green" : "text-rams-red"
            )}>
              {stats.margin_change >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {stats.margin_change >= 0 ? '+' : ''}{stats.margin_change}% {t('pages.finance.kpi.delta') || 'DELTA'}
            </div>
          </div>
          <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group">
            <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.finance.kpi.opex') || 'OpEx Synchronization'}</p>
            <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{formatCurrency(stats.opex)}</div>
            <div className="mt-4 space-y-1.5">
              <div className="goal-progress-track">
                <div className="goal-progress-fill bg-rams-orange" style={{ width: `${stats.budget_utilization}%` }} />
              </div>
              <div className="flex justify-between text-[8px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                <span>{t('pages.finance.kpi.budgetUtilization') || 'BUDGET_UTILIZATION'}</span>
                <span>{stats.budget_utilization}%</span>
              </div>
            </div>
          </div>
          <div className="bg-rams-module p-6 border-b border-rams-line group">
            <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.finance.kpi.liquidity') || 'Liquidity Reserve'}</p>
            <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{formatCurrency(stats.liquidity_reserve)}</div>
            <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">{stats.liquidity_status?.toUpperCase().replace(' ', '_') || 'OPTIMAL_STATE'}</p>
          </div>
        </div>

        <div className="grid gap-8 md:grid-cols-2">
          <Card className="rounded-rams-sm overflow-hidden border-rams-line">
            <CardHeader className="bg-rams-panel border-b border-rams-line">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-rams-orange" />
                {t('pages.finance.revenueByProduct.title') || 'Revenue by Product Line'}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              {[
                { label: t('pages.finance.revenueByProduct.precisionComponents') || 'Precision Components', value: 580000, color: 'bg-rams-orange' },
                { label: t('pages.finance.revenueByProduct.assemblySystems') || 'Assembly Systems', value: 420000, color: 'bg-rams-steel' },
                { label: t('pages.finance.revenueByProduct.aftermarketServices') || 'Aftermarket Services', value: 240000, color: 'bg-rams-green' },
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

          <Card className="rounded-rams-sm overflow-hidden border-rams-line">
            <CardHeader className="bg-rams-panel border-b border-rams-line">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                <PieChart className="h-4 w-4 text-rams-orange" />
                {t('pages.finance.costDrivers.title') || 'Top Cost Drivers'}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-rams-line">
                {[
                  { label: t('pages.finance.costDrivers.rawMaterials') || 'Raw Materials (Steel/Aluminum)', trend: 'up', impact: t('common.high') || 'High' },
                  { label: t('pages.finance.costDrivers.energy') || 'Energy Consumption', trend: 'up', impact: t('common.medium') || 'Medium' },
                  { label: t('pages.finance.costDrivers.overtime') || 'Overtime Labor', trend: 'down', impact: t('common.medium') || 'Medium' },
                  { label: t('pages.finance.costDrivers.logistics') || 'Logistics/Freight', trend: 'stable', impact: t('common.low') || 'Low' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between p-4 hover:bg-rams-panel group">
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "p-2 rounded-rams-sm border border-rams-line",
                        item.trend === 'up' ? "bg-rams-panel text-rams-red border-rams-red" : 
                        item.trend === 'down' ? "bg-rams-panel text-rams-green border-rams-green" : 
                        "bg-rams-panel text-muted-foreground"
                      )}>
                        {item.trend === 'up' ? <TrendingUp className="h-4 w-4" /> : 
                        item.trend === 'down' ? <TrendingDown className="h-4 w-4" /> :
                        <BarChart3 className="h-4 w-4" />}
                      </div>
                      <div>
                        <div className="text-[11px] font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{item.label}</div>
                        <div className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{item.impact} {t('pages.finance.costDrivers.impactOnMargin') || 'IMPACT_ON_MARGIN'}</div>
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/20 group-hover:text-rams-orange" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
  );
}

function cn_legacy(...classes: any[]) {
  return classes.filter(Boolean).join(' ');
}
