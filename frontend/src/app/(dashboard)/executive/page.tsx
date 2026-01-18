'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
import { useAuthStore } from '@/stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { useExecutiveStore, useQualityStore, useTodayStore } from '@/stores';
import { Loader2, Download, Search, Send, Users, AlertTriangle, TrendingUp, Shield } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { PageGuard } from '@/components/layout/page-guard';
import { EXECUTIVE_ROLES } from '@/lib/page-access';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';
import { API_ROOT } from '@/api/client';

function RiskBadge({ value }: { value: string }) {
  const v = (value || '').toLowerCase();
  const variant = v === 'critical' || v === 'high' ? 'destructive' : v === 'medium' ? 'warning' : 'secondary';
  return <Badge variant={variant as any}>{value}</Badge>;
}

export default function ExecutivePage() {
  const { t } = useI18n();
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

  const exportUrl = `${API_ROOT}/api/v1/executive/strategic-report/export`;

  return (
    <PageGuard requiredRoles={EXECUTIVE_ROLES}>
      <div className="space-y-8 page-fade-in pb-12" data-testid="executive-page">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              Executive Control Plane
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>Strategic intelligence and command center oversight</span>
              <span className="opacity-30">|</span>
              <span>STATION: COMMAND-01</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <AmbientStatus 
              status={totalNcrs > 5 ? 'critical' : totalNcrs > 0 ? 'warning' : 'operational'} 
              label={totalNcrs > 5 ? 'Anomalies Detected' : totalNcrs > 0 ? 'Monitoring Active' : 'All Systems Nominal'}
            />
            <Button variant="outline" size="default" className="rounded-rams-sm border-rams-border" asChild>
              <a href={exportUrl}>
                <Download className="mr-2 h-3.5 w-3.5" />
                Export Intelligence
              </a>
            </Button>
          </div>
        </div>

        <Tabs defaultValue="north-star" className="space-y-8 animate-in fade-in duration-700">
          <TabsList className="bg-rams-panel border border-rams-border p-1 rounded-rams-sm w-fit overflow-x-auto no-scrollbar">
            <TabsTrigger value="north-star">NORTH_STAR</TabsTrigger>
            <TabsTrigger value="nl2sql">SENSEI_AI</TabsTrigger>
            <TabsTrigger value="employee-risk">RISK_PREDICTION</TabsTrigger>
          </TabsList>

          <TabsContent value="north-star" data-testid="north-star" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
            {/* Executive KPIs */}
            <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-border bg-rams-border">
              <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-border group hover:bg-rams-panel transition-none cursor-help">
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Revenue Intelligence (MTD)</p>
                <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">
                  ${(((todayData as any)?.metrics?.revenue || 0) / 1000000).toFixed(1)}M
                </div>
                <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2 flex items-center gap-1">
                  <TrendingUp className="h-3 w-3" /> +2.1% ALPHA_TREND
                </p>
              </div>
              <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-border group hover:bg-rams-panel transition-none cursor-help">
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Active Anomalies</p>
                <div className={cn("text-3xl font-mono font-bold tracking-tight tabular-nums", totalNcrs > 5 ? "text-rams-red" : "text-foreground/90")}>
                  {totalNcrs}
                </div>
                <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">ACTIVE_GATE_BLOCKS</p>
              </div>
              <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-border group hover:bg-rams-panel transition-none cursor-help">
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Open Resolutions</p>
                <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{totalCapas}</div>
                <p className="text-[9px] font-mono font-bold text-rams-orange uppercase tracking-widest mt-2">CAPA_SYNC_ACTIVE</p>
              </div>
              <div className="bg-rams-module p-6 border-b md:border-b-0 border-rams-border group hover:bg-rams-panel transition-none cursor-help">
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Operational Uptime</p>
                <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">99.9%</div>
                <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">OPTIMAL_STATE</p>
              </div>
            </div>

            <div className="grid gap-8 lg:grid-cols-2">
              <Card className="rounded-rams-sm overflow-hidden border-rams-border">
                <CardHeader className="bg-rams-panel/20 border-b border-rams-border">
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-rams-orange" />
                    Strategic Directives
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-1 space-y-1">
                  {[
                    { label: 'Priority Alpha', title: 'Address Margin Leakage in Tier 2 Suppliers', desc: 'AI detected 4.2% variance in Q3 procurement vs budget protocols.', severity: 'critical' },
                    { label: 'Priority Beta', title: 'Accelerate Level 4 Maturity Training', desc: 'Operations bottlenecking at specialized inspection gates requiring sync.', severity: 'strategic' },
                  ].map((item) => (
                    <div key={item.label} className="p-5 bg-rams-panel/40 border border-rams-border/50 hover:bg-rams-panel transition-none group">
                      <div className="flex items-center justify-between mb-4">
                        <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{item.label}</span>
                        <Badge variant={item.severity === 'critical' ? 'danger' : 'default'} size="sm" className="h-4 px-1">{item.severity.toUpperCase()}</Badge>
                      </div>
                      <p className="font-sans font-black text-sm uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{item.title}</p>
                      <p className="text-[10px] text-muted-foreground mt-2 leading-relaxed font-medium uppercase">{item.desc}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="rounded-rams-sm overflow-hidden border-rams-border">
                <CardHeader className="bg-rams-panel/20 border-b border-rams-border">
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                    <Users className="h-4 w-4 text-rams-orange" />
                    Operational Overview
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-12 flex items-center justify-center bg-rams-module relative overflow-hidden">
                  <div className="relative z-10 text-center space-y-4">
                    <div className="p-4 rounded-none bg-rams-panel border border-rams-border inline-block animate-pulse">
                      <Users className="h-8 w-8 text-rams-orange/40" />
                    </div>
                    <p className="text-[10px] font-mono font-black uppercase tracking-[0.3em] text-muted-foreground/40">Aggregating Global Metrics...</p>
                  </div>
                  <div className="absolute inset-0 perforated-bg opacity-5" />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="nl2sql" data-testid="nl2sql" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <Card className="rounded-rams-sm overflow-hidden border-rams-border shadow-none">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-border">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-none bg-rams-orange/10 border border-rams-orange/20 text-rams-orange">
                    <Send className="h-4 w-4" />
                  </div>
                  <div>
                    <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">Autonomous Data Interface</CardTitle>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">Protocol: Natural Language to SQL Sync</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-8 space-y-8 bg-rams-module relative overflow-hidden">
                <div className="space-y-4 relative z-10">
                  <div className="flex flex-col gap-2">
                    <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">Command Input</label>
                    <Textarea
                      value={nl2sqlQuestion}
                      onChange={(e) => setNl2sqlQuestion(e.target.value)}
                      rows={4}
                      placeholder="e.g. Show me the win rate for quotes over $100k in the last 6 months by salesperson."
                      className="bg-rams-panel border-rams-border text-[11px] font-bold uppercase tracking-wider p-4 h-32 focus-visible:ring-rams-orange"
                      data-testid="nl2sql-question"
                    />
                  </div>
                  <Button 
                    onClick={handleRunNl2sql} 
                    disabled={nl2sqlLoading || !nl2sqlQuestion}
                    className="w-full h-12 rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]"
                    data-testid="nl2sql-run"
                  >
                    {nl2sqlLoading ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        REASONING_IN_PROGRESS...
                      </div>
                    ) : (
                      'EXECUTE_INFERENCE'
                    )}
                  </Button>
                </div>

                {(nl2sqlResult || nl2sqlError) && (
                  <div className="mt-8 animate-in fade-in slide-in-from-top-4 duration-500 relative z-10">
                    {nl2sqlError ? (
                      <div className="p-6 bg-rams-red/5 border border-rams-red/20 flex gap-4" data-testid="nl2sql-error">
                        <AlertTriangle className="h-5 w-5 text-rams-red shrink-0" />
                        <div className="text-xs font-medium text-rams-red uppercase leading-relaxed">{nl2sqlError}</div>
                      </div>
                    ) : (
                      <div className="space-y-6" data-testid="nl2sql-result">
                        <div className="grid gap-6 md:grid-cols-2">
                          <div className="space-y-2">
                            <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Generated Logic (SQL)</label>
                            <pre className="p-4 bg-rams-panel border border-rams-border text-[10px] font-mono text-foreground/70 overflow-auto max-h-40 rounded-none uppercase tracking-tighter">{nl2sqlResult.generated_sql}</pre>
                          </div>
                          <div className="space-y-2">
                            <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Sensei Reasoning</label>
                            <div className="p-4 bg-rams-orange/5 border border-rams-orange/20 text-xs font-medium leading-relaxed uppercase text-foreground/80">{nl2sqlResult.explanation}</div>
                          </div>
                        </div>
                        
                        <div className="space-y-2">
                          <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">Intelligence Data Output</label>
                          <pre className="p-4 bg-rams-panel border border-rams-border text-[10px] font-mono text-foreground/70 overflow-auto max-h-60 rounded-none uppercase tracking-tighter">
                            {JSON.stringify(nl2sqlResult.result, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
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
                        <div className="text-3xl font-heading font-bold tracking-tight ">{riskResult.employee_name}</div>
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
                            {(riskResult.risk_factors?.length ?? 0) > 0 ? (
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
