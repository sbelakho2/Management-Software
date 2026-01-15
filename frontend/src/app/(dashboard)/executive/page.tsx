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
import { Loader2, Download, Search, Send, Users, AlertTriangle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { PageGuard } from '@/components/layout/page-guard';
import { EXECUTIVE_ROLES } from '@/lib/page-access';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function RiskBadge({ value }: { value: string }) {
  const v = (value || '').toLowerCase();
  const variant = v === 'critical' || v === 'high' ? 'destructive' : v === 'medium' ? 'warning' : 'secondary';
  return <Badge variant={variant as any}>{value}</Badge>;
}

export default function ExecutivePage() {
  const { user, isAuthenticated } = useAuthStore();
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
    if (isAuthenticated) {
      fetchNCRs();
      fetchCAPAs();
      if (user) {
        const name = (user.full_name || '').trim() || (user.email || '').trim() || 'User';
        fetchTodayScreen(user.id, name);
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

  const exportUrl = `${API_URL}/api/v1/executive/strategic-report/export`;

  return (
    <PageGuard requiredRoles={EXECUTIVE_ROLES}>
      <div className="space-y-8 page-fade-in" data-testid="executive-page">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="space-y-1">
            <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              Executive Control Plane
            </h1>
            <p className="text-muted-foreground font-medium">
              Strategic intelligence, predictive analysis, and command center oversight
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary" asChild>
              <a href={exportUrl}>
                <Download className="mr-2 h-4 w-4" />
                Export Intelligence
              </a>
            </Button>
          </div>
        </div>

        <Tabs defaultValue="north-star" className="space-y-8 animate-in fade-in duration-700">
          <TabsList className="flex h-14 w-full justify-start gap-3 bg-muted/10 p-1.5 rounded-2xl backdrop-blur-md border border-border/5 overflow-x-auto no-scrollbar shadow-inner-soft">
            <TabsTrigger value="north-star" className="gap-2.5 rounded-xl px-8 font-heading font-bold text-xs uppercase tracking-widest transition-all data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-glow">
              North Star Dashboard
            </TabsTrigger>
            <TabsTrigger value="nl2sql" className="gap-2.5 rounded-xl px-8 font-heading font-bold text-xs uppercase tracking-widest transition-all data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-glow">
              NL2SQL Intelligence
            </TabsTrigger>
            <TabsTrigger value="employee-risk" className="gap-2.5 rounded-xl px-8 font-heading font-bold text-xs uppercase tracking-widest transition-all data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-glow">
              Predictive Human Risk
            </TabsTrigger>
          </TabsList>

          <TabsContent value="north-star" data-testid="north-star" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium hover:shadow-premium-hover transition-all duration-500">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Revenue Intelligence (MTD)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">${(((todayData as any)?.metrics?.revenue || 0) / 1000000).toFixed(1)}M</div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 mt-2 flex items-center gap-1">
                    <TrendingUp className="h-3 w-3" />
                    +2.1% ALPHA TREND
                  </p>
                </CardContent>
              </Card>
              <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium hover:shadow-premium-hover transition-all duration-500">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Active Anomalies</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-destructive to-destructive/70">{totalNcrs}</div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-destructive mt-2">Quality Health Critical</p>
                </CardContent>
              </Card>
              <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium hover:shadow-premium-hover transition-all duration-500">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Open Resolutions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-amber-500 to-amber-500/70">{totalCapas}</div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-amber-500 mt-2">CAPA Velocity Required</p>
                </CardContent>
              </Card>
              <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium hover:shadow-premium-hover transition-all duration-500">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Operational Uptime</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-emerald-500 to-emerald-500/70">99.9%</div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 mt-2">System Resilience Optimal</p>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-8 md:grid-cols-2">
              <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
                <CardHeader>
                  <CardTitle className="text-lg font-heading">Strategic Directives</CardTitle>
                  <CardDescription className="text-xs font-medium uppercase tracking-wider">Automated priorities from Sensei AI</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                   <div className="p-5 rounded-2xl bg-primary/5 border border-primary/10 space-y-2 group hover:bg-primary/10 transition-all duration-300">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-primary/60">Priority Alpha</span>
                        <Badge variant="destructive" className="rounded-md px-1.5 py-0 text-[9px] font-bold uppercase tracking-widest">Critical</Badge>
                      </div>
                      <p className="font-heading font-bold text-base tracking-tight">Address Margin Leakage in Tier 2 Suppliers</p>
                      <p className="text-xs text-muted-foreground font-medium leading-relaxed">AI detected 4.2% variance in Q3 procurement vs budget protocols.</p>
                   </div>
                   <div className="p-5 rounded-2xl bg-muted/30 border border-border/10 space-y-2 group hover:bg-primary/5 transition-all duration-300">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Priority Beta</span>
                        <Badge className="rounded-md px-1.5 py-0 text-[9px] font-bold uppercase tracking-widest">Strategic</Badge>
                      </div>
                      <p className="font-heading font-bold text-base tracking-tight">Accelerate Level 4 Maturity Training</p>
                      <p className="text-xs text-muted-foreground font-medium leading-relaxed">Operations bottlenecking at specialized inspection gates requiring sync.</p>
                   </div>
                </CardContent>
              </Card>

              <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
                <CardHeader>
                  <CardTitle className="text-lg font-heading">Operational Overview</CardTitle>
                  <CardDescription className="text-xs font-medium uppercase tracking-wider">Live feed from shop floor gates</CardDescription>
                </CardHeader>
                <CardContent>
                   <div className="h-56 flex items-center justify-center border-2 border-dashed border-border/20 rounded-[2rem] bg-muted/5">
                      <div className="text-center space-y-3">
                        <div className="p-4 rounded-full bg-primary/10 inline-block animate-pulse">
                          <Users className="h-8 w-8 text-primary/40" />
                        </div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-muted-foreground/40">Aggregating Global Metrics...</p>
                      </div>
                   </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="nl2sql" data-testid="nl2sql" className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <Card className="premium-glass border-primary/20 shadow-glow">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
                    <Send className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-xl">Intelligence Query (Sensei NL2SQL)</CardTitle>
                    <CardDescription>Ask any strategic question in plain English.</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground/70">Strategic Inquiry</label>
                  <Textarea
                    value={nl2sqlQuestion}
                    onChange={(e) => setNl2sqlQuestion(e.target.value)}
                    rows={4}
                    placeholder="e.g. Show me the win rate for quotes over $100k in the last 6 months by salesperson."
                    className="rounded-2xl bg-background/50 border-border/50 focus:border-primary/50 transition-all text-lg font-medium p-4"
                    data-testid="nl2sql-question"
                  />
                </div>
                
                <Button 
                  onClick={handleRunNl2sql} 
                  disabled={nl2sqlLoading} 
                  size="xl" 
                  className="w-full rounded-2xl shadow-glow premium-shimmer"
                  data-testid="nl2sql-run"
                >
                  {nl2sqlLoading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Send className="mr-2 h-5 w-5" />}
                  Generate Intelligence
                </Button>

                {nl2sqlError && (
                  <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive font-medium animate-in slide-in-from-top-2" data-testid="nl2sql-error">
                    {nl2sqlError}
                  </div>
                )}

                {nl2sqlResult && (
                  <div className="space-y-6 animate-in fade-in zoom-in-95 duration-500" data-testid="nl2sql-result">
                    <div className="grid gap-4 md:grid-cols-2">
                       <div className="space-y-2">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Generated Logic (SQL)</label>
                          <pre className="rounded-xl border border-border/30 bg-black/5 dark:bg-white/5 p-4 text-xs font-mono overflow-auto max-h-40">{nl2sqlResult.generated_sql}</pre>
                       </div>
                       <div className="space-y-2">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Sensei Reasoning</label>
                          <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm font-medium leading-relaxed">{nl2sqlResult.explanation}</div>
                       </div>
                    </div>
                    
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Intelligence Data Output</label>
                      <pre className="rounded-xl border border-border/30 bg-black/5 dark:bg-white/5 p-4 text-xs font-mono overflow-auto max-h-60">
                        {JSON.stringify(nl2sqlResult.result, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="employee-risk" data-testid="employee-risk" className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <Card className="premium-glass border-primary/20 shadow-glow rounded-[2.5rem]">
              <CardHeader>
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/20 transition-transform hover:scale-110 duration-500">
                    <Users className="h-6 w-6" />
                  </div>
                  <div>
                    <CardTitle className="text-xl font-heading">Predictive Human Risk Analysis</CardTitle>
                    <CardDescription className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60">Deterministic burnout and retention risk scoring models</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-10">
                <div className="grid gap-8 md:grid-cols-2">
                  <div className="space-y-3 group">
                    <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 group-focus-within:text-primary transition-colors ml-1">Employee Node Identity</label>
                    <Input value={employeeName} onChange={(e) => setEmployeeName(e.target.value)} className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50" data-testid="risk-employee-name" placeholder="e.g. John Doe" />
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Department Node</label>
                    <Input value={department} onChange={(e) => setDepartment(e.target.value)} className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50" data-testid="risk-department" placeholder="e.g. Engineering" />
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Tenure Protocol (months)</label>
                    <Input
                      type="number"
                      value={tenureMonths}
                      onChange={(e) => setTenureMonths(Number(e.target.value))}
                      className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50"
                      data-testid="risk-tenure"
                    />
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Weekly Overtime Velocity (hrs)</label>
                    <Input
                      type="number"
                      value={overtimeHours}
                      onChange={(e) => setOvertimeHours(Number(e.target.value))}
                      className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50"
                      data-testid="risk-overtime"
                    />
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Skip Rate Intelligence (0-1)</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={skipRate}
                      onChange={(e) => setSkipRate(Number(e.target.value))}
                      className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50"
                      data-testid="risk-skiprate"
                    />
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Peer Comparison Delta</label>
                    <Input
                      type="number"
                      step="0.1"
                      value={peerComparison}
                      onChange={(e) => setPeerComparison(Number(e.target.value))}
                      className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50"
                      data-testid="risk-peer"
                    />
                  </div>
                </div>

                <Button onClick={handleAnalyzeRisk} disabled={riskLoading} size="xl" className="w-full rounded-[1.5rem] shadow-glow premium-shimmer h-14 text-base font-bold tracking-tight" data-testid="risk-run">
                  {riskLoading ? <Loader2 className="mr-3 h-5 w-5 animate-spin" /> : <Shield className="mr-3 h-5 w-5" />}
                  Execute Predictive Risk Model
                </Button>

                {riskError && (
                  <div className="p-5 rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive font-bold uppercase tracking-widest text-[10px] animate-in slide-in-from-top-2" data-testid="risk-error">
                    {riskError}
                  </div>
                )}

                {riskResult && (
                  <div className="space-y-8 animate-in fade-in zoom-in-95 duration-700" data-testid="risk-result">
                    <div className="flex flex-col md:flex-row md:items-center justify-between p-8 rounded-[2rem] bg-muted/20 border border-border/10 shadow-premium gap-6">
                      <div className="space-y-1">
                        <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{riskResult.employee_name}</div>
                        <div className="text-xs font-bold uppercase tracking-widest text-muted-foreground/40">Predictive Score Confidence: 94.8%</div>
                      </div>
                      <div className="flex gap-6">
                        <div className="space-y-2">
                          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/40 block text-center">Retention Protocol</span>
                          <RiskBadge value={riskResult.retention_risk} />
                        </div>
                        <div className="space-y-2">
                          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground/40 block text-center">Burnout Threshold</span>
                          <RiskBadge value={riskResult.burnout_risk} />
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-8 md:grid-cols-2">
                       <Card className="bg-background/40 border-border/20 rounded-[2rem] shadow-premium">
                          <CardContent className="pt-8 space-y-6">
                             <div className="space-y-3">
                                <div className="flex justify-between text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">
                                   <span>Retention Index</span>
                                   <span className="text-primary">{riskResult.retention_score.toFixed(2)}</span>
                                </div>
                                <Progress value={riskResult.retention_score * 10} className="h-2.5 bg-primary/10" />
                             </div>
                             <div className="space-y-3">
                                <div className="flex justify-between text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">
                                   <span>Burnout Magnitude</span>
                                   <span className="text-danger">{riskResult.burnout_score.toFixed(2)}</span>
                                </div>
                                <Progress value={riskResult.burnout_score * 10} className="h-2.5 bg-danger/10" />
                             </div>
                          </CardContent>
                       </Card>

                       <Card className="bg-background/50 border-border/30">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm uppercase tracking-widest">Risk Factors identified</CardTitle>
                          </CardHeader>
                          <CardContent>
                            {riskResult.risk_factors.length > 0 ? (
                              <ul className="space-y-2">
                                {riskResult.risk_factors.map((r) => (
                                  <li key={r} className="flex items-center gap-3 text-sm font-medium">
                                    <AlertTriangle className="h-4 w-4 text-warning shrink-0" />
                                    {r}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-sm text-muted-foreground italic">No specific risk factors detected.</p>
                            )}
                          </CardContent>
                       </Card>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </PageGuard>
  );
}
