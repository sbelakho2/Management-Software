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
import { useAuthStore } from '@/stores';
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

  const { user } = useAuthStore();

  const [soundEnabled, setSoundEnabled] = React.useState(true);
  const [isFullscreen, setIsFullscreen] = React.useState(false);
  const [lastRefresh, setLastRefresh] = React.useState(new Date());

  const criticalAlerts = activeEvents.filter(a => a.severity === 'critical');
  const runningMachines = Array.from(workCenters.values()).filter(w => w.status === 'running').length;
  
  const handleAcknowledge = (alertId: string) => {
    acknowledgeEvent(alertId, user?.full_name || user?.email || 'Unknown');
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
    <div className="space-y-8 page-fade-in pb-12" data-testid="andon-page">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90 flex items-center gap-3">
            <div className="flex flex-col gap-0.5">
              <div className="h-1.5 w-4 bg-rams-red" />
              <div className="h-1.5 w-4 bg-rams-orange" />
              <div className="h-1.5 w-4 bg-rams-green" />
            </div>
            {t('pages.andon.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-none bg-rams-green animate-pulse" />
            <span>{t('andon.realTimeStream') || 'REAL-TIME_STREAM'}</span>
            <span className="opacity-30">|</span>
            <span>{t('andon.station') || 'STATION: ANDON-01'}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            variant="ghost" 
            size="icon"
            className="rounded-rams-sm h-10 w-10 border border-rams-line hover:bg-rams-panel transition-none"
            onClick={() => setSoundEnabled(!soundEnabled)}
            title={soundEnabled ? 'Mute alerts' : 'Enable alert sounds'}
          >
            {soundEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
          </Button>
          <Button
            variant="outline"
            size="default"
            className="rounded-rams-sm border-rams-line"
            onClick={() => router.push('/andon/analytics')}
          >
            <TrendingUp className="h-3.5 w-3.5 mr-2" />
            {t('andon.analytics') || 'Analytics'}
          </Button>
          <Button 
            variant="ghost" 
            size="icon"
            className="rounded-rams-sm h-10 w-10 border border-rams-line hover:bg-rams-panel transition-none"
            onClick={toggleFullscreen}
            title="Toggle fullscreen"
          >
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            className="rounded-rams-sm h-10 w-10 border border-rams-line hover:bg-rams-panel transition-none" 
            onClick={() => setLastRefresh(new Date())}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button 
            size="default" 
            className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]" 
            onClick={() => router.push('/andon/settings')}
          >
            <Settings className="mr-2 h-3.5 w-3.5" />
            {t('andon.controlStation') || 'Control Station'}
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
        <div className={cn("bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group", criticalAlerts.length > 0 && 'bg-rams-red/5')}>
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('andon.stats.activeSignals') || 'Active Signals'}</p>
          <div className="flex items-end justify-between">
            <div className={cn("text-3xl font-mono font-bold tracking-tight tabular-nums", criticalAlerts.length > 0 ? "text-rams-red" : "text-foreground/90")}>
              {activeEvents.length}
            </div>
            {criticalAlerts.length > 0 && (
              <Badge variant="danger" size="sm" className="mb-1">{criticalAlerts.length} {t('common.priority.critical').toUpperCase() || 'CRITICAL'}</Badge>
            )}
          </div>
        </div>

        <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('andon.stats.operationalPulse') || 'Operational Pulse'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{runningMachines}/{workCenters.size}</div>
          <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">{t('andon.stats.activeNodes') || 'ACTIVE_NODES'}</p>
        </div>

        <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0 group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('andon.stats.meanResponse') || 'Mean Response'}</p>
          <div className={cn(
            "text-3xl font-mono font-bold tracking-tight tabular-nums",
            metrics.avgResponseTime < 300 ? "text-rams-green" : "text-rams-orange"
          )}>
            {Math.round(metrics.avgResponseTime / 60)}m
          </div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('andon.stats.protocolVelocity') || 'PROTOCOL_VELOCITY'}</p>
        </div>

        <div className="bg-rams-module p-6 border-b border-rams-line group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('andon.stats.resolvedNodes') || 'Resolved Nodes'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{metrics.totalResolved}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('andon.stats.totalCycles') || 'TOTAL_CYCLES'}</p>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Active Alerts */}
        <div className="lg:col-span-1 space-y-6">
          <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-muted-foreground/60 flex items-center gap-3 px-1">
            <div className="h-1.5 w-1.5 bg-rams-orange" />
            {t('andon.sections.activeSignals') || 'Active Signals'} ({activeEvents.length})
          </h2>
          <div className="space-y-1">
            {activeEvents.length === 0 ? (
              <div className="py-12 text-center industrial-panel bg-rams-panel/20 border-dashed">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-rams-module border border-rams-line mb-4">
                  <CheckCircle className="h-8 w-8 text-rams-green/20" />
                </div>
                <p className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-muted-foreground/40">{t('andon.empty.protocolStable') || 'Protocol Stable'}</p>
                <p className="text-[9px] text-muted-foreground/30 mt-1 uppercase tracking-[0.2em]">{t('andon.empty.noActiveAnomalies') || 'No active anomalies identified'}</p>
              </div>
            ) : (
              activeEvents.map((alert) => (
                <Card key={alert.id} className="rounded-none border-rams-line bg-rams-module group relative overflow-hidden">
                  <div className={cn('absolute top-0 left-0 w-1 h-full', alert.severity === 'critical' ? 'bg-rams-red' : 'bg-rams-orange')} />
                  <CardContent className="p-5 space-y-4">
                    <div className="flex justify-between items-start">
                      <div className="font-mono text-[10px] font-black text-muted-foreground/40 uppercase tracking-widest">{t('andon.stationPrefix') || 'STATION:'} {alert.work_center_id}</div>
                      <Badge variant={alert.severity === 'critical' ? 'danger' : 'warning'} size="sm" className="h-4">{alert.severity.toUpperCase()}</Badge>
                    </div>
                    <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 leading-snug">{alert.description}</p>
                    <div className="flex justify-between items-center pt-4 border-t border-rams-line">
                      <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/30">{formatElapsedTime(alert.created_at)}</span>
                      <div className="flex gap-1">
                        <Button size="sm" variant="outline" className="h-7 px-3 text-[8px] font-black uppercase tracking-widest rounded-none" onClick={() => handleAcknowledge(alert.id)}>{t('andon.actions.sync') || 'SYNC'}</Button>
                        <Button size="sm" variant="outline" className="h-7 px-3 text-[8px] font-black uppercase tracking-widest rounded-none" onClick={() => handleEscalate(alert.id)}>{t('andon.actions.escalate') || 'ESCALATE'}</Button>
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
          <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-muted-foreground/60 flex items-center gap-3 px-1">
            <div className="h-1.5 w-1.5 bg-rams-orange" />
            {t('andon.sections.intelligenceNodes') || 'Intelligence Nodes'}
          </h2>
          <div className="grid gap-px border border-rams-line bg-rams-line">
            {Array.from(workCenters.values()).map((wc) => (
              <div key={wc.id} className="bg-rams-module p-6 group">
                <div className="flex justify-between items-center mb-6">
                  <span className="font-sans font-black text-sm uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{wc.name}</span>
                  <Badge variant={wc.status === 'running' ? 'success' : 'danger'} size="sm" className="h-4">{wc.status.toUpperCase()}</Badge>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                    <span>{t('andon.workCenter.oeePulse') || 'OEE Pulse'}</span>
                    <span className="text-foreground/60">{wc.oee}%</span>
                  </div>
                  <div className="h-1 bg-rams-panel border border-rams-line overflow-hidden">
                    <div 
                      className={cn(
                        "h-full transition-all duration-1000",
                        wc.status === 'running' ? 'bg-rams-green' : 'bg-rams-red'
                      )} 
                      style={{ width: `${wc.efficiency}%` }} 
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
        <CardHeader className="p-4 border-b border-rams-line bg-rams-panel/20">
          <CardTitle className="text-[10px] font-black uppercase tracking-[0.3em] text-muted-foreground/60">{t('andon.sections.strategicControls') || 'Strategic Operational Controls'}</CardTitle>
        </CardHeader>
        <CardContent className="p-6 bg-rams-module">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" className="rounded-none border-rams-line hover:bg-rams-panel transition-none">
              <PhoneCall className="mr-2 h-3.5 w-3.5" />
              {t('andon.actions.syncSupervisor') || 'Sync Supervisor'}
            </Button>
            <Button variant="outline" className="rounded-none border-rams-line hover:bg-rams-panel transition-none">
              <MessageSquare className="mr-2 h-3.5 w-3.5" />
              {t('andon.actions.globalBroadcast') || 'Global Broadcast'}
            </Button>
            <Button variant="outline" className="rounded-none border-rams-line hover:bg-rams-panel transition-none">
              <Wrench className="mr-2 h-3.5 w-3.5" />
              {t('andon.actions.technicianNode') || 'Technician Node'}
            </Button>
            <Button variant="outline" className="rounded-none border-rams-line hover:bg-rams-panel transition-none">
              <Package className="mr-2 h-3.5 w-3.5" />
              {t('andon.actions.logisticsSync') || 'Logistics Sync'}
            </Button>
            <Button variant="outline" className="rounded-none border-rams-red/20 text-rams-red hover:bg-rams-red/5 transition-none">
              <AlertTriangle className="mr-2 h-3.5 w-3.5" />
              {t('andon.actions.protocolException') || 'Protocol Exception'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
