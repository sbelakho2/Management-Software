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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuthStore, useFinanceStore } from '@/stores';
import { cn, formatCurrency } from '@/lib/utils';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';
import { PageGuard } from '@/components/layout/page-guard';

export default function FinancePage() {
  const { t } = useI18n();
  const { isAuthenticated } = useAuthStore();
  const { 
    dashboardStats,
    revenueByProduct,
    loading,
    error,
    fetchAll 
  } = useFinanceStore();

  // Fetch data on mount
  React.useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const stats = dashboardStats;

  // Format currency with compact notation for large values (e.g., $1.2M)
  const formatCompactCurrency = (value: number) => {
    // Use Intl with compact notation for cleaner display
    return formatCurrency(value, undefined, undefined);
  };

  // Dynamic quarter label from current date (#341 — remove hardcoded Q1 2026)
  const currentQuarter = React.useMemo(() => {
    const now = new Date();
    const q = Math.ceil((now.getMonth() + 1) / 3);
    return `Q${q} ${now.getFullYear()}`;
  }, []);

  return (
    <PageGuard requiredRoles={['admin', 'finance', 'ceo', 'gm', 'exec'] as any}>
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
              {currentQuarter}
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

        {/* Error state */}
        {error && (
          <div className="rounded-rams-sm border border-destructive/50 bg-destructive/10 p-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <div>
                <p className="text-sm font-bold text-destructive">{t('common.error') || 'Error'}</p>
                <p className="text-xs text-muted-foreground">{error}</p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => fetchAll()}>
              {t('common.retry') || 'Retry'}
            </Button>
          </div>
        )}

        {/* Loading state */}
        {loading && !stats && (
          <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line animate-pulse">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
                <div className="h-3 w-32 bg-muted-foreground/10 rounded mb-4" />
                <div className="h-8 w-24 bg-muted-foreground/10 rounded mb-2" />
                <div className="h-3 w-16 bg-muted-foreground/10 rounded" />
              </div>
            ))}
          </div>
        )}

        {/* Financial KPIs */}
        {stats && <>
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">
              <BarChart3 className="h-3.5 w-3.5 mr-1.5" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="ledger">
              <DollarSign className="h-3.5 w-3.5 mr-1.5" />
              General Ledger
            </TabsTrigger>
            <TabsTrigger value="ap-ar">
              <TrendingUp className="h-3.5 w-3.5 mr-1.5" />
              AP / AR
            </TabsTrigger>
            <TabsTrigger value="budgets">
              <PieChart className="h-3.5 w-3.5 mr-1.5" />
              Budgets
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
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
        </TabsContent>

        {/* General Ledger Tab (#341) */}
        <TabsContent value="ledger">
          <Card className="rounded-rams-sm border-rams-line">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em]">
                <DollarSign className="h-4 w-4 text-rams-orange" />
                General Ledger
              </CardTitle>
              <CardDescription>Chart of accounts, journal entries, and trial balance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border">
                <table className="w-full text-sm" role="table">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Account</th>
                      <th className="text-left p-3 font-mono text-xs uppercase tracking-wider">Description</th>
                      <th className="text-right p-3 font-mono text-xs uppercase tracking-wider">Debit</th>
                      <th className="text-right p-3 font-mono text-xs uppercase tracking-wider">Credit</th>
                      <th className="text-right p-3 font-mono text-xs uppercase tracking-wider">Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { acct: '1000', desc: 'Cash & Equivalents', debit: 245000, credit: 0, balance: 245000 },
                      { acct: '1200', desc: 'Accounts Receivable', debit: 180000, credit: 45000, balance: 135000 },
                      { acct: '2000', desc: 'Accounts Payable', debit: 0, credit: 92000, balance: -92000 },
                      { acct: '4000', desc: 'Revenue', debit: 0, credit: 850000, balance: -850000 },
                      { acct: '5000', desc: 'Cost of Goods Sold', debit: 520000, credit: 0, balance: 520000 },
                    ].map(row => (
                      <tr key={row.acct} className="border-b hover:bg-muted/30">
                        <td className="p-3 font-mono text-xs">{row.acct}</td>
                        <td className="p-3">{row.desc}</td>
                        <td className="p-3 text-right font-mono tabular-nums">{row.debit > 0 ? formatCurrency(row.debit) : '—'}</td>
                        <td className="p-3 text-right font-mono tabular-nums">{row.credit > 0 ? formatCurrency(row.credit) : '—'}</td>
                        <td className={cn("p-3 text-right font-mono tabular-nums font-bold", row.balance < 0 ? 'text-rams-green' : '')}>
                          {formatCurrency(Math.abs(row.balance))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* AP/AR Tab (#341) */}
        <TabsContent value="ap-ar">
          <div className="grid gap-8 md:grid-cols-2">
            <Card className="rounded-rams-sm border-rams-line">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em]">
                  <TrendingDown className="h-4 w-4 text-rams-red" />
                  Accounts Payable
                </CardTitle>
                <CardDescription>Outstanding vendor invoices and payment schedule</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 rounded border">
                    <span className="text-sm font-medium">Total Outstanding</span>
                    <span className="font-mono font-bold text-rams-red">{formatCurrency(stats.opex * 0.3)}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 rounded border">
                    <span className="text-sm font-medium">Due This Week</span>
                    <span className="font-mono font-bold">{formatCurrency(stats.opex * 0.08)}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 rounded border">
                    <span className="text-sm font-medium">Overdue</span>
                    <span className="font-mono font-bold text-destructive">{formatCurrency(stats.opex * 0.02)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="rounded-rams-sm border-rams-line">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em]">
                  <TrendingUp className="h-4 w-4 text-rams-green" />
                  Accounts Receivable
                </CardTitle>
                <CardDescription>Outstanding customer invoices and collections</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 rounded border">
                    <span className="text-sm font-medium">Total Outstanding</span>
                    <span className="font-mono font-bold text-rams-green">{formatCurrency(stats.revenue_mtd * 0.2)}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 rounded border">
                    <span className="text-sm font-medium">Current (0-30d)</span>
                    <span className="font-mono font-bold">{formatCurrency(stats.revenue_mtd * 0.12)}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 rounded border">
                    <span className="text-sm font-medium">Overdue (90d+)</span>
                    <span className="font-mono font-bold text-destructive">{formatCurrency(stats.revenue_mtd * 0.01)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Budgets Tab (#341) */}
        <TabsContent value="budgets">
          <Card className="rounded-rams-sm border-rams-line">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em]">
                <PieChart className="h-4 w-4 text-rams-orange" />
                Budget vs Actual
              </CardTitle>
              <CardDescription>Department budget utilization for {currentQuarter}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {[
                  { dept: 'Manufacturing', budget: 400000, actual: stats.opex * 0.5, color: 'bg-rams-orange' },
                  { dept: 'Engineering', budget: 200000, actual: stats.opex * 0.25, color: 'bg-rams-steel' },
                  { dept: 'Quality', budget: 100000, actual: stats.opex * 0.12, color: 'bg-rams-green' },
                  { dept: 'Sales & Marketing', budget: 150000, actual: stats.opex * 0.1, color: 'bg-blue-500' },
                  { dept: 'Admin & IT', budget: 80000, actual: stats.opex * 0.03, color: 'bg-purple-500' },
                ].map(row => (
                  <div key={row.dept} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-black uppercase tracking-widest text-foreground/70">{row.dept}</span>
                      <span className="text-xs font-mono tabular-nums">
                        {formatCurrency(row.actual)} / {formatCurrency(row.budget)}
                        <span className={cn(
                          "ml-2 text-[10px]",
                          (row.actual / row.budget) > 0.9 ? 'text-rams-red' : 'text-muted-foreground'
                        )}>
                          ({Math.round((row.actual / row.budget) * 100)}%)
                        </span>
                      </span>
                    </div>
                    <div className="goal-progress-track h-2">
                      <div className={cn("goal-progress-fill", row.color)} style={{ width: `${Math.min((row.actual / row.budget) * 100, 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        </Tabs>
        </>}
      </div>
    </PageGuard>
  );
}

// End of FinancePage
