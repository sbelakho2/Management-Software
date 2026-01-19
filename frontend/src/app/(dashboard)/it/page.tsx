'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';
import { 
  Server, 
  Shield, 
  AlertTriangle, 
  Activity,
  HardDrive,
  Wifi,
  Users,
  Lock,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Terminal,
  Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';
import { useITStore } from '@/stores';
import { PageGuard } from '@/components/layout/page-guard';
import { IT_ROLES } from '@/lib/page-access';

// Fallback demo data when API is not available
const fallbackSystemHealth = {
  api_health: 'healthy',
  db_health: 'healthy',
  cache_health: 'healthy',
  queue_health: 'healthy',
  uptime: '99.98%',
  last_incident: '12 days ago',
};

const fallbackServerStats = {
  cpu_usage: 42,
  memory_usage: 68,
  disk_usage: 54,
  active_connections: 234,
};

const fallbackAlerts = [
  { id: '1', type: 'warning' as const, message: 'High memory usage on worker-3', time: '15 min ago', resolved: false },
  { id: '2', type: 'info' as const, message: 'Scheduled backup completed', time: '2 hours ago', resolved: true },
  { id: '3', type: 'error' as const, message: 'Failed login attempt detected', time: '4 hours ago', resolved: true },
  { id: '4', type: 'info' as const, message: 'SSL certificate renewed', time: '1 day ago', resolved: true },
];

const fallbackActiveUsers = [
  { name: 'Operations Team', count: 45, trend: 'up' as const },
  { name: 'Sales Team', count: 23, trend: 'stable' as const },
  { name: 'Quality Team', count: 12, trend: 'up' as const },
  { name: 'Admin Users', count: 8, trend: 'stable' as const },
];

const fallbackServices = [
  { name: 'API Gateway', status: 'healthy' as const, latency: '45ms' },
  { name: 'Database Primary', status: 'healthy' as const, latency: '12ms' },
  { name: 'Database Replica', status: 'healthy' as const, latency: '15ms' },
  { name: 'Redis Cache', status: 'healthy' as const, latency: '2ms' },
  { name: 'Message Queue', status: 'healthy' as const, latency: '23ms' },
  { name: 'ML Service', status: 'healthy' as const, latency: '89ms' },
];

function StatusIndicator({ status }: { status: 'healthy' | 'degraded' | 'down' }) {
  const styles = {
    healthy: 'bg-rams-green',
    degraded: 'bg-rams-orange',
    down: 'bg-rams-red',
  };

  return (
    <span className={`inline-block h-2 w-2 ${styles[status]}`} />
  );
}

export default function ITDashboard() {
  const { t } = useI18n();
  const { 
    systemHealth,
    serverStats: apiServerStats,
    services: apiServices,
    alerts: apiAlerts,
    activeUsers: apiActiveUsers,
    isLoading,
    fetchAll
  } = useITStore();

  // Fetch data on mount
  React.useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Use API data or fallback to demo data
  const systemStatus = systemHealth || fallbackSystemHealth;
  const serverStats = apiServerStats || fallbackServerStats;
  const services = apiServices.length > 0 ? apiServices : fallbackServices;
  const recentAlerts = apiAlerts.length > 0 ? apiAlerts : fallbackAlerts;
  const activeUsers = apiActiveUsers.length > 0 ? apiActiveUsers : fallbackActiveUsers;
  return (
    <PageGuard requiredRoles={IT_ROLES}>
    <div className="space-y-8 page-fade-in pb-12" data-testid="it-dashboard">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90 flex items-center gap-3">
            <Server className="h-6 w-6 text-rams-orange" />
            {t('pages.it.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.it.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.it.station')}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <AmbientStatus 
            status={systemStatus.queue_health === 'degraded' ? 'warning' : 'operational'} 
            label={systemStatus.queue_health === 'degraded' ? t('pages.it.messageQueueDegraded') : t('pages.it.allSystemsNominal')}
          />
          <Button 
            variant="outline" 
            size="default" 
            className="rounded-rams-sm border-rams-line"
            onClick={() => fetchAll()}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-3.5 w-3.5" />
            )}
            {t('pages.it.refreshSync') || 'Refresh Sync'}
          </Button>
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line">
            <Terminal className="mr-2 h-3.5 w-3.5" />
            {t('pages.it.liveLogs') || 'Live Logs'}
          </Button>
        </div>
      </div>

      {/* System Status Banner */}
      <Card className="rounded-rams-sm bg-rams-module border border-rams-line overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-1 bg-rams-green/20" />
        <CardContent className="py-8 px-10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-8">
            <div className="flex items-center gap-6">
              <div className="p-4 rounded-none bg-rams-panel border border-rams-line text-rams-green group">
                <CheckCircle2 className="h-10 w-10" />
              </div>
              <div>
                <p className="font-sans font-black text-2xl uppercase tracking-tight text-foreground/90">{t('pages.it.globalInfrastructureSynchronized') || 'Global Infrastructure Synchronized'}</p>
                <p className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-muted-foreground/40 mt-2">
                  {t('pages.it.uptime') || 'Uptime'}: {systemStatus.uptime} • {t('pages.it.continuousPulseEstablished') || 'Continuous Pulse established'} {systemStatus.last_incident.toUpperCase()}
                </p>
              </div>
            </div>
            <Badge variant="outline" className="rounded-none border-rams-green/20 bg-rams-green/5 text-rams-green px-4 py-1 h-8 font-black uppercase tracking-[0.2em] text-[10px]">
              <Activity className="h-3 w-3 mr-2 animate-pulse" />
              {t('pages.it.activeComputeNode')}
            </Badge>
          </div>
        </CardContent>
        <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
      </Card>

      {/* Resource Usage */}
      <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-line bg-rams-line">
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group hover:bg-rams-panel transition-none">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.it.cpuUtilization') || 'CPU Utilization'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{serverStats.cpu_usage}%</div>
          <div className="mt-4 h-1 bg-rams-panel border border-rams-line overflow-hidden">
            <div className={cn("h-full bg-rams-orange", serverStats.cpu_usage > 80 && "bg-rams-red")} style={{ width: `${serverStats.cpu_usage}%` }} />
          </div>
        </div>
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group hover:bg-rams-panel transition-none">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.it.memoryPulse') || 'Memory Pulse'}</p>
          <div className={cn("text-3xl font-mono font-bold tracking-tight tabular-nums", serverStats.memory_usage > 80 ? "text-rams-red" : "text-foreground/90")}>{serverStats.memory_usage}%</div>
          <div className="mt-4 h-1 bg-rams-panel border border-rams-line overflow-hidden">
            <div className={cn("h-full bg-rams-orange", serverStats.memory_usage > 80 && "bg-rams-red")} style={{ width: `${serverStats.memory_usage}%` }} />
          </div>
        </div>
        <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.it.diskSaturation') || 'Disk Saturation'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{serverStats.disk_usage}%</div>
          <div className="mt-4 h-1 bg-rams-panel border border-rams-line overflow-hidden">
            <div className="h-full bg-rams-steel" style={{ width: `${serverStats.disk_usage}%` }} />
          </div>
        </div>
        <div className="bg-rams-module p-6 border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.it.activeSockets') || 'Active Sockets'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{serverStats.active_connections}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.it.connectionsSynced')}</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid gap-8 lg:grid-cols-2">
        {/* Service Status */}
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden shadow-none">
          <CardHeader className="border-b border-rams-line bg-rams-panel/20 p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Server className="h-4 w-4 text-rams-orange" />
              {t('pages.it.intelligenceNodeCluster') || 'Intelligence Node Cluster'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-line/30">
              {services.map((service) => (
                <div key={service.name} className="flex items-center justify-between p-5 transition-none hover:bg-rams-panel group">
                  <div className="flex items-center gap-4">
                    <div className="p-2 rounded-none bg-rams-panel border border-rams-line text-foreground/20 group-hover:border-rams-orange/40 transition-none">
                      <StatusIndicator status={service.status as any} />
                    </div>
                    <div>
                      <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{service.name}</p>
                      <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{t('pages.it.latency')}: {service.latency.toUpperCase()}</p>
                    </div>
                  </div>
                  <Badge variant={service.status === 'healthy' ? 'success' : 'warning'} size="sm" className="h-4 px-1">
                    {service.status.toUpperCase()}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Alerts */}
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden shadow-none">
          <CardHeader className="border-b border-rams-line bg-rams-panel/20 p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2 text-rams-red">
              <AlertTriangle className="h-4 w-4" />
              {t('pages.it.telemetryAnomalies') || 'Telemetry Anomalies'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-line/30">
              {recentAlerts.map((alert) => (
                <div key={alert.id} className="p-5 flex items-start gap-4 hover:bg-rams-panel transition-none group">
                  <div className={cn(
                    "mt-0.5 p-2 rounded-none bg-rams-panel border border-rams-line transition-none",
                    alert.type === 'error' ? 'text-rams-red border-rams-red/20' : alert.type === 'warning' ? 'text-rams-orange border-rams-orange/20' : 'text-muted-foreground'
                  )}>
                    {alert.type === 'error' ? <XCircle className="h-4 w-4" /> : 
                     alert.type === 'warning' ? <AlertTriangle className="h-4 w-4" /> : 
                     <Activity className="h-4 w-4" />}
                  </div>
                  <div className="flex-1">
                    <p className={cn("text-xs font-medium uppercase leading-relaxed text-foreground/70 group-hover:text-foreground transition-none")}>
                      {alert.message}
                    </p>
                    <div className="flex items-center gap-4 mt-2">
                      <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/30">{alert.time.toUpperCase()}</span>
                      {alert.resolved ? (
                        <Badge variant="outline" className="rounded-none border-rams-green/20 bg-rams-green/5 text-rams-green text-[8px] h-4 font-black uppercase tracking-widest px-1">{t('pages.it.resolved')}</Badge>
                      ) : (
                        <Badge variant="destructive" className="animate-pulse rounded-none text-[8px] h-4 font-black uppercase tracking-widest px-1">{t('pages.it.activeBreach')}</Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Active Users */}
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden shadow-none">
          <CardHeader className="border-b border-rams-line bg-rams-panel/20 p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Users className="h-4 w-4 text-rams-orange" />
              {t('pages.it.connectedOperatives') || 'Connected Operatives'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-line/30">
              {activeUsers.map((group, index) => (
                <div key={group.name || index} className="p-5 flex items-center justify-between transition-none hover:bg-rams-panel group">
                  <div className="flex items-center gap-4">
                    <div className="p-2 rounded-none bg-rams-panel border border-rams-line text-muted-foreground/20 group-hover:border-rams-orange/40 transition-none">
                      <Users className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{group.name}</p>
                      <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{group.count} {t('pages.it.activeNodes')}</p>
                    </div>
                  </div>
                  {group.trend === 'up' ? (
                    <Badge variant="outline" className="rounded-none border-rams-green/20 bg-rams-green/5 text-rams-green text-[8px] h-4 font-black uppercase tracking-widest px-1">{t('pages.it.trafficUp')}</Badge>
                  ) : (
                    <Badge variant="secondary" className="rounded-none bg-rams-panel text-muted-foreground/40 border-rams-line text-[8px] h-4 font-black uppercase tracking-widest px-1">{t('pages.it.stable')}</Badge>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Security Overview */}
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden shadow-none text-left">
          <CardHeader className="border-b border-rams-line bg-rams-panel/20 p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Shield className="h-4 w-4 text-rams-orange" />
              {t('pages.it.securitySyncProtocol') || 'Security Sync Protocol'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-line/30">
              <div className="flex items-center justify-between p-5 transition-none hover:bg-rams-panel group">
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded-none bg-rams-panel border border-rams-line text-rams-green/40 group-hover:border-rams-orange/40 transition-none">
                    <Lock className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t('pages.it.sslCertificate')}</p>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{t('pages.it.rsaSynchronized')}</p>
                  </div>
                </div>
                <Badge variant="outline" className="rounded-none border-rams-green/20 bg-rams-green/5 text-rams-green text-[8px] h-4 font-black uppercase tracking-widest px-1">{t('pages.it.validNode')}</Badge>
              </div>
              <div className="flex items-center justify-between p-5 transition-none hover:bg-rams-panel group">
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded-none bg-rams-panel border border-rams-line text-rams-green/40 group-hover:border-rams-orange/40 transition-none">
                    <Shield className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t('pages.it.firewallArchitecture')}</p>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{t('pages.it.distributedWafActive')}</p>
                  </div>
                </div>
                <Badge variant="outline" className="rounded-none border-rams-green/20 bg-rams-green/5 text-rams-green text-[8px] h-4 font-black uppercase tracking-widest px-1">{t('pages.it.active')}</Badge>
              </div>
              <div className="p-6 bg-rams-panel/10">
                <Button variant="outline" className="w-full rounded-rams-sm border-rams-line text-[9px] font-black uppercase tracking-widest h-10 transition-none">
                  {t('pages.it.updateSecurityPolicies')}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
    </PageGuard>
  );
}
