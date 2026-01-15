'use client';

import * as React from 'react';
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  PieChart, 
  Calendar,
  Download,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useAuthStore } from '@/stores';
import { PageGuard } from '@/components/layout/page-guard';
import { FINANCE_ROLES } from '@/lib/page-access';
import { cn } from '@/lib/utils';

export default function FinancePage() {
  const { isAuthenticated } = useAuthStore();

  return (
    <PageGuard requiredRoles={FINANCE_ROLES}>
      <div className="space-y-8 page-fade-in" data-testid="finance-page">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="space-y-1">
            <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              Finance Control Plane
            </h1>
            <p className="text-muted-foreground font-medium">Revenue forecasting, operational expenditures, and margin intelligence</p>
          </div>
          <div className="flex items-center gap-3">
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

        <div className="grid gap-4 md:grid-cols-4">
          {[
            { label: 'Total Revenue (MTD)', value: '$1.24M', trend: '+8.2% vs last month', icon: TrendingUp, status: 'success' },
            { label: 'Gross Margin', value: '32.4%', trend: '-1.5% vs target', icon: TrendingDown, status: 'danger' },
            { label: 'OpEx (Actual vs Budget)', value: '$420K', trend: '92% of quarterly budget used', icon: DollarSign, status: 'default' },
            { label: 'Cash on Hand', value: '$2.8M', trend: 'Strong liquidity position', icon: CheckCircle2, status: 'success' },
          ].map((stat, i) => (
            <Card key={i} className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{stat.label}</p>
                  <stat.icon className={cn("h-4 w-4", stat.status === 'success' ? "text-emerald-500" : stat.status === 'danger' ? "text-danger" : "text-primary")} />
                </div>
                <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{stat.value}</div>
                <div className={cn("text-[10px] font-bold uppercase tracking-widest mt-2", stat.status === 'success' ? "text-emerald-600" : stat.status === 'danger' ? "text-danger" : "text-muted-foreground")}>
                  {stat.trend}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium">
            <CardHeader>
              <CardTitle className="text-xl font-heading font-bold flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-primary" />
                Revenue by Product Line
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
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
                  <Progress value={(item.value / 1240000) * 100} className="h-2.5" indicatorClassName={item.color} />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium">
            <CardHeader>
              <CardTitle className="text-xl font-heading font-bold flex items-center gap-2">
                <PieChart className="h-5 w-5 text-primary" />
                Top Cost Drivers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { label: 'Raw Materials (Steel/Aluminum)', trend: 'up', impact: 'High' },
                  { label: 'Energy Consumption', trend: 'up', impact: 'Medium' },
                  { label: 'Overtime Labor', trend: 'down', impact: 'Medium' },
                  { label: 'Logistics/Freight', trend: 'stable', impact: 'Low' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between p-4 rounded-2xl bg-muted/20 border border-border/10 hover:bg-muted/30 transition-colors">
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
