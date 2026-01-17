'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Play,
  Pause,
  Users,
  Wrench,
  Package,
  Zap,
  Volume2,
  VolumeX,
  Maximize2,
  RefreshCw,
  ArrowUp,
  Settings,
  MoreHorizontal,
  PhoneCall,
  MessageSquare,
  TrendingUp,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge, BadgeProps } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn, formatDate } from '@/lib/utils';
import { useAndonStore, formatElapsedTime } from '@/stores/andon-store';
import type { AndonEvent, AndonStatus, Severity, WorkCenter } from '@/types';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

export default function AndonBoardPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { 
    activeEvents, 
    workCenters, 
    metrics, 
    isConnected, 
    connect, 
    disconnect,
    acknowledgeEvent,
    escalateEvent
  } = useAndonStore();

  const [soundEnabled, setSoundEnabled] = React.useState(true);
  const [isFullscreen, setIsFullscreen] = React.useState(false);
  const [lastRefresh, setLastRefresh] = React.useState(new Date());

  const criticalAlerts = activeEvents.filter(a => a.severity === 'critical');
  const runningMachines = Array.from(workCenters.values()).filter(w => w.status === 'running').length;
  
  const handleAcknowledge = (alertId: string) => {
    acknowledgeEvent(alertId, 'Current User'); // In real app, get from auth store
  };

  const handleEscalate = (alertId: string) => {
    escalateEvent(alertId);
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  React.useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Auto-refresh every 30 seconds for non-websocket fallback
  React.useEffect(() => {
    const interval = setInterval(() => {
      setLastRefresh(new Date());
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8 page-fade-in" data-testid="andon-page">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight  flex items-center gap-3">
            <Zap className="h-10 w-10 text-primary" />
            {t('pages.andon.title')}
          </h1>
          <p className="text-sm text-muted-foreground font-medium flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            Real-time monitoring • Last updated {formatDate(lastRefresh, { hour: 'numeric', minute: 'numeric', second: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            variant="ghost" 
            size="icon"
            className="rounded-xl hover:bg-primary/10 transition-all"
            onClick={() => setSoundEnabled(!soundEnabled)}
            title={soundEnabled ? 'Mute alerts' : 'Enable alert sounds'}
          >
            {soundEnabled ? <Volume2 className="h-5 w-5" /> : <VolumeX className="h-5 w-5" />}
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary"
            onClick={() => router.push('/andon/analytics')}
          >
            <TrendingUp className="h-4 w-4 mr-2" />
            Analytics
          </Button>
          <Button 
            variant="ghost" 
            size="icon"
            className="rounded-xl hover:bg-primary/10 transition-all"
            onClick={toggleFullscreen}
            title="Toggle fullscreen"
          >
            <Maximize2 className="h-5 w-5" />
          </Button>
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => setLastRefresh(new Date())}>
            <RefreshCw className="h-5 w-5" />
          </Button>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine" onClick={() => router.push('/andon/settings')}>
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className={cn("rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1", criticalAlerts.length > 0 && 'border-danger/20 bg-danger/[0.02]')}>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-heading font-bold tracking-tight ">{activeEvents.length}</p>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">Active Signals</p>
              </div>
              <div className={cn("p-3 rounded-2xl shadow-sm", criticalAlerts.length > 0 ? "bg-danger/10 text-danger animate-pulse" : "bg-muted/10 text-muted-foreground")}>
                <AlertTriangle className="h-5 w-5" />
              </div>
            </div>
            {criticalAlerts.length > 0 && (
              <Badge variant="destructive" className="mt-3 rounded-md px-1.5 py-0 text-[8px] font-black uppercase tracking-widest">
                {criticalAlerts.length} CRITICAL NODES
              </Badge>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-heading font-bold tracking-tight ">{runningMachines}/{workCenters.size}</p>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">Operational Pulse</p>
              </div>
              <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-600 shadow-sm">
                <Play className="h-5 w-5" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className={cn(
                  'text-3xl font-heading font-bold tracking-tight mt-1',
                  metrics.avgResponseTime < 300 ? 'text-emerald-600 dark:text-emerald-500' : 'text-amber-600 dark:text-amber-500'
                )}>
                  {Math.round(metrics.avgResponseTime / 60)}m
                </p>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">Mean Response</p>
              </div>
              <div className="p-3 rounded-2xl bg-primary/10 text-primary shadow-sm">
                <Zap className="h-5 w-5" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-heading font-bold tracking-tight ">{metrics.totalResolved}</p>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">Resolved Nodes</p>
              </div>
              <div className="p-3 rounded-2xl bg-secondary/50 text-foreground shadow-sm">
                <Package className="h-5 w-5" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Active Alerts */}
        <div className="lg:col-span-1 space-y-6">
          <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 flex items-center gap-2 px-2">
            <AlertTriangle className="h-4 w-4 text-warning/60" />
            Active Signals ({activeEvents.length})
          </h2>
          <div className="space-y-4">
            {activeEvents.length === 0 ? (
              <Card className="rounded-[2.5rem] border-emerald-500/20 bg-emerald-500/[0.02] backdrop-blur-md shadow-glow">
                <CardContent className="p-8 text-center space-y-4">
                  <div className="p-4 rounded-full bg-emerald-500/10 inline-block">
                    <CheckCircle className="h-10 w-10 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-heading font-bold text-lg text-emerald-800 dark:text-emerald-200">Protocol Stable</p>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600/60 mt-1">No active anomalies identified</p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              activeEvents.map((alert) => (
                <Card key={alert.id} className={cn('rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden transition-all duration-500 hover:shadow-premium group', alert.severity === 'critical' ? 'border-danger/20' : 'border-warning/20')}>
                  <div className={cn('h-1 w-full', alert.severity === 'critical' ? 'bg-danger' : 'bg-warning')} />
                  <CardContent className="p-6 space-y-4">
                    <div className="flex justify-between items-start">
                      <div className="font-mono text-xs font-bold text-primary/60">{alert.work_center_id}</div>
                      <Badge variant={alert.severity === 'critical' ? 'danger' : 'warning'} className="rounded-md text-[8px] font-black uppercase tracking-widest border-none">{alert.severity}</Badge>
                    </div>
                    <p className="font-heading font-bold text-sm tracking-tight text-foreground/80 leading-snug group-hover:text-primary transition-colors">{alert.description}</p>
                    <div className="flex justify-between items-center pt-4 border-t border-border/10">
                      <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40">{formatElapsedTime(alert.created_at)}</span>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" className="h-8 rounded-lg text-[9px] uppercase tracking-widest font-black" onClick={() => handleAcknowledge(alert.id)}>SYNC</Button>
                        <Button size="sm" variant="outline" className="h-8 rounded-lg text-[9px] uppercase tracking-widest font-black" onClick={() => handleEscalate(alert.id)}>ESCALATE</Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>

        {/* Work Centers */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 flex items-center gap-2 px-2">
            <Wrench className="h-4 w-4 text-primary/60" />
            Intelligence Nodes
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from(workCenters.values()).map((wc) => (
              <Card key={wc.id} className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden hover:shadow-premium-hover transition-all duration-500 group">
                <div className={cn('h-1.5 w-full transition-colors duration-1000', wc.status === 'running' ? 'bg-success shadow-glow' : 'bg-danger animate-pulse')} />
                <CardContent className="p-6 space-y-5">
                  <div className="flex justify-between items-center">
                    <span className="font-heading font-bold text-base tracking-tight text-foreground/80">{wc.name}</span>
                    <Badge variant={wc.status === 'running' ? 'success' : 'secondary'} className="rounded-md text-[8px] font-black uppercase tracking-widest border-none">{wc.status}</Badge>
                  </div>
                  <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
                    <span>OEE Pulse</span>
                    <span className="text-foreground/60">{wc.oee}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted/20 overflow-hidden shadow-inner-soft">
                    <div 
                      className={cn(
                        "h-full transition-all duration-1000",
                        wc.status === 'running' ? 'bg-success' : 'bg-danger'
                      )} 
                      style={{ width: `${wc.efficiency}%` }} 
                    />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium overflow-hidden">
        <CardHeader className="pb-4 border-b border-border/5 bg-muted/5 p-6">
          <CardTitle className="text-[10px] font-bold uppercase tracking-[0.3em] text-muted-foreground/60">Strategic Operational Controls</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
              <PhoneCall className="mr-2 h-4 w-4" />
              Sync Supervisor
            </Button>
            <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
              <MessageSquare className="mr-2 h-4 w-4" />
              Global Broadcast
            </Button>
            <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
              <Wrench className="mr-2 h-4 w-4" />
              Technician Node
            </Button>
            <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
              <Package className="mr-2 h-4 w-4" />
              Logistics Sync
            </Button>
            <Button variant="outline" size="lg" className="rounded-xl border-danger/20 hover:bg-danger/5 text-danger">
              <AlertTriangle className="mr-2 h-4 w-4" />
              Protocol Exception
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
