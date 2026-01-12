'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { useExecutiveStore, useQualityStore, useTodayStore } from '@/stores';
import { Loader2, Download, Search, Send, Users } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const ALLOWED_ROLES = ['admin', 'exec', 'ceo', 'gm'];

function RiskBadge({ value }: { value: string }) {
  const v = (value || '').toLowerCase();
  const variant = v === 'critical' || v === 'high' ? 'destructive' : v === 'medium' ? 'warning' : 'secondary';
  return <Badge variant={variant as any}>{value}</Badge>;
}

export default function ExecutivePage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuthStore();
  const router = useRouter();
  const [nl2sqlQuestion, setNl2sqlQuestion] = React.useState('How many open CAPAs are there?');
  
  const { 
    nl2sqlResult, 
    riskResult, 
    nl2sqlLoading, 
    nl2sqlError,
    riskLoading,
    riskError,
    runNl2sql,
    analyzeRisk 
  } = useExecutiveStore();

  const { totalNcrs, totalCapas, fetchNCRs, fetchCAPAs } = useQualityStore();
  const { data: todayData, fetchTodayScreen } = useTodayStore();

  React.useEffect(() => {
    if (!authLoading && isAuthenticated && user && !ALLOWED_ROLES.includes(user.role)) {
      router.push('/today');
    }
  }, [user, isAuthenticated, authLoading, router]);

  React.useEffect(() => {
    if (isAuthenticated) {
      fetchNCRs();
      fetchCAPAs();
      if (user) {
        fetchTodayScreen(user.id, user.full_name);
      }
    }
  }, [fetchNCRs, fetchCAPAs, fetchTodayScreen, user, isAuthenticated]);

  const [employeeName, setEmployeeName] = React.useState('Alice Example');
  const [department, setDepartment] = React.useState('Operations');
  const [tenureMonths, setTenureMonths] = React.useState(3);
  const [overtimeHours, setOvertimeHours] = React.useState(20);
  const [skipRate, setSkipRate] = React.useState(0.25);
  const [peerComparison, setPeerComparison] = React.useState(1.4);

  const handleRunNl2sql = () => {
    runNl2sql({ question: nl2sqlQuestion });
  };

  const handleAnalyzeRisk = () => {
    analyzeRisk({
      employee_name: employeeName,
      department,
      tenure_months: tenureMonths,
      overtime_hours_weekly: overtimeHours,
      skip_rate: skipRate,
      peer_comparison: peerComparison,
    });
  };

  if (authLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated || (user && !ALLOWED_ROLES.includes(user.role))) {
    return null;
  }

  const exportUrl = `${API_URL}/api/v1/executive/strategic-report/export`;

  return (
    <div className="space-y-6" data-testid="executive-page">
      <div>
        <h1 className="text-2xl font-bold">Executive Control Plane</h1>
        <p className="text-muted-foreground">
          Strategic overview, predictive analysis, and report generation
        </p>
      </div>

      <Tabs defaultValue="north-star">
        <TabsList>
          <TabsTrigger value="north-star">North Star Dashboard</TabsTrigger>
          <TabsTrigger value="nl2sql">NL2SQL Query</TabsTrigger>
          <TabsTrigger value="employee-risk">Employee Risk Analysis</TabsTrigger>
          <TabsTrigger value="export">Strategic Report Export</TabsTrigger>
        </TabsList>

        <TabsContent value="north-star" data-testid="north-star" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Revenue (Forecast)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">${(((todayData as any)?.metrics?.revenue || 0) / 1000000).toFixed(1)}M</div>
                <p className="text-xs text-muted-foreground">+2.1% from last month</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Open NCs</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{totalNcrs}</div>
                <p className="text-xs text-muted-foreground">Quality health status</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Open CAPAs</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{totalCapas}</div>
                <p className="text-xs text-muted-foreground">Action required</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">System Health</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">99.9%</div>
                <p className="text-xs text-muted-foreground">Production ready</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="nl2sql" data-testid="nl2sql" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Executive NL2SQL (Restricted)</CardTitle>
              <CardDescription>Allowlisted read-only questions only.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                value={nl2sqlQuestion}
                onChange={(e) => setNl2sqlQuestion(e.target.value)}
                rows={3}
                data-testid="nl2sql-question"
              />
              <Button onClick={handleRunNl2sql} disabled={nl2sqlLoading} data-testid="nl2sql-run">
                {nl2sqlLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Run Query
              </Button>

              {nl2sqlError && (
                <div className="text-sm text-destructive" data-testid="nl2sql-error">
                  {nl2sqlError}
                </div>
              )}

              {nl2sqlResult && (
                <div className="space-y-2" data-testid="nl2sql-result">
                  <div className="text-sm">
                    <span className="font-medium">Generated SQL:</span>
                  </div>
                  <pre className="rounded-md border bg-muted p-3 text-xs overflow-auto">{nl2sqlResult.generated_sql}</pre>
                  <div className="text-sm text-muted-foreground">{nl2sqlResult.explanation}</div>
                  <pre className="rounded-md border bg-muted p-3 text-xs overflow-auto">
                    {JSON.stringify(nl2sqlResult.result, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="employee-risk" data-testid="employee-risk" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Employee Risk Analysis</CardTitle>
              <CardDescription>Deterministic retention + burnout risk scoring.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Employee Name</label>
                  <Input value={employeeName} onChange={(e) => setEmployeeName(e.target.value)} data-testid="risk-employee-name" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Department</label>
                  <Input value={department} onChange={(e) => setDepartment(e.target.value)} data-testid="risk-department" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Tenure (months)</label>
                  <Input
                    type="number"
                    value={tenureMonths}
                    onChange={(e) => setTenureMonths(Number(e.target.value))}
                    data-testid="risk-tenure"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Overtime (hrs/week)</label>
                  <Input
                    type="number"
                    value={overtimeHours}
                    onChange={(e) => setOvertimeHours(Number(e.target.value))}
                    data-testid="risk-overtime"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Skip rate (0-1)</label>
                  <Input
                    type="number"
                    step="0.01"
                    value={skipRate}
                    onChange={(e) => setSkipRate(Number(e.target.value))}
                    data-testid="risk-skiprate"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Peer comparison</label>
                  <Input
                    type="number"
                    step="0.1"
                    value={peerComparison}
                    onChange={(e) => setPeerComparison(Number(e.target.value))}
                    data-testid="risk-peer"
                  />
                </div>
              </div>

              <Button onClick={handleAnalyzeRisk} disabled={riskLoading} data-testid="risk-run">
                {riskLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Analyze
              </Button>

              {riskError && (
                <div className="text-sm text-destructive" data-testid="risk-error">
                  {riskError}
                </div>
              )}

              {riskResult && (
                <div className="space-y-2" data-testid="risk-result">
                  <div className="flex items-center gap-2">
                    <div className="font-medium">{riskResult.employee_name}</div>
                    <RiskBadge value={riskResult.retention_risk} />
                    <RiskBadge value={riskResult.burnout_risk} />
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Retention score: {riskResult.retention_score.toFixed(2)} • Burnout score: {riskResult.burnout_score.toFixed(2)}
                  </div>
                  {riskResult.risk_factors.length > 0 && (
                    <div className="text-sm">
                      <div className="font-medium">Risk factors</div>
                      <ul className="list-disc pl-6">
                        {riskResult.risk_factors.map((r) => (
                          <li key={r}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="export" data-testid="strategic-export" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Strategic Report Export</CardTitle>
              <CardDescription>Download a restricted strategic report pack.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button asChild data-testid="export-download">
                <a href={exportUrl}>Download Strategic Report (JSON)</a>
              </Button>
              <div className="text-xs text-muted-foreground">Includes open NC + CAPA counts.</div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
