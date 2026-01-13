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
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Finance Control Plane</h1>
            <p className="text-muted-foreground">Financial performance, budgeting, and cost analysis</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline">
              <Calendar className="mr-2 h-4 w-4" />
              Q1 2026
            </Button>
            <Button>
              <Download className="mr-2 h-4 w-4" />
              Export Reports
            </Button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Revenue (MTD)</CardDescription>
              <CardTitle className="text-2xl">$1.24M</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-success flex items-center gap-1 font-medium">
                <TrendingUp className="h-3 w-3" />
                +8.2% vs last month
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Gross Margin</CardDescription>
              <CardTitle className="text-2xl">32.4%</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-danger flex items-center gap-1 font-medium">
                <TrendingDown className="h-3 w-3" />
                -1.5% vs target
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>OpEx (Actual vs Budget)</CardDescription>
              <CardTitle className="text-2xl">$420K</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-muted-foreground font-medium">
                92% of quarterly budget used
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Cash on Hand</CardDescription>
              <CardTitle className="text-2xl">$2.8M</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-success font-medium">
                Strong liquidity position
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Revenue by Product Line</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { label: 'Precision Components', value: 580000, color: 'bg-blue-500' },
                { label: 'Assembly Systems', value: 420000, color: 'bg-indigo-500' },
                { label: 'Aftermarket Services', value: 240000, color: 'bg-emerald-500' },
              ].map((item) => (
                <div key={item.label} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{item.label}</span>
                    <span className="text-muted-foreground">${(item.value / 1000).toFixed(0)}K</span>
                  </div>
                  <Progress value={(item.value / 1240000) * 100} className={cn("h-2", item.color)} />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top Cost Drivers</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { label: 'Raw Materials (Steel/Aluminum)', trend: 'up', impact: 'High' },
                  { label: 'Energy Consumption', trend: 'up', impact: 'Medium' },
                  { label: 'Overtime Labor', trend: 'down', impact: 'Medium' },
                  { label: 'Logistics/Freight', trend: 'stable', impact: 'Low' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded bg-muted">
                        {item.trend === 'up' ? <TrendingUp className="h-4 w-4 text-danger" /> : 
                        item.trend === 'down' ? <TrendingDown className="h-4 w-4 text-success" /> :
                        <BarChart3 className="h-4 w-4 text-muted-foreground" />}
                      </div>
                      <div>
                        <div className="text-sm font-medium">{item.label}</div>
                        <div className="text-xs text-muted-foreground">{item.impact} impact on margin</div>
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
