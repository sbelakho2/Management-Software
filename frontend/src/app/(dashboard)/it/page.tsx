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
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';

// Demo data
const systemStatus = {
  apiHealth: 'healthy',
  dbHealth: 'healthy',
  cacheHealth: 'healthy',
  queueHealth: 'degraded',
  uptime: '99.98%',
  lastIncident: '12 days ago',
};

const serverStats = {
  cpuUsage: 42,
  memoryUsage: 68,
  diskUsage: 54,
  activeConnections: 234,
};

const recentAlerts = [
  { id: 1, type: 'warning', message: 'High memory usage on worker-3', time: '15 min ago', resolved: false },
  { id: 2, type: 'info', message: 'Scheduled backup completed', time: '2 hours ago', resolved: true },
  { id: 3, type: 'error', message: 'Failed login attempt detected', time: '4 hours ago', resolved: true },
  { id: 4, type: 'info', message: 'SSL certificate renewed', time: '1 day ago', resolved: true },
];

const activeUsers = [
  { id: 1, name: 'Operations Team', count: 45, trend: 'up' },
  { id: 2, name: 'Sales Team', count: 23, trend: 'stable' },
  { id: 3, name: 'Quality Team', count: 12, trend: 'up' },
  { id: 4, name: 'Admin Users', count: 8, trend: 'stable' },
];

const services = [
  { name: 'API Gateway', status: 'healthy', latency: '45ms' },
  { name: 'Database Primary', status: 'healthy', latency: '12ms' },
  { name: 'Database Replica', status: 'healthy', latency: '15ms' },
  { name: 'Redis Cache', status: 'healthy', latency: '2ms' },
  { name: 'Message Queue', status: 'degraded', latency: '156ms' },
  { name: 'ML Service', status: 'healthy', latency: '89ms' },
];

function StatusIndicator({ status }: { status: 'healthy' | 'degraded' | 'down' }) {
  const styles = {
    healthy: 'bg-emerald-500',
    degraded: 'bg-amber-500',
    down: 'bg-destructive',
  };

  return (
    <span className={`inline-block h-2 w-2 rounded-full ${styles[status]}`} />
  );
}

export default function ITDashboard() {
  const { t } = useI18n();
  return (
    <div className="space-y-8 page-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight ">
            {t('pages.it.title')}
          </h1>
          <p className="text-muted-foreground font-medium">
            {t('pages.it.subtitle')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <AmbientStatus 
            status={systemStatus.queueHealth === 'degraded' ? 'warning' : 'operational'} 
            label={systemStatus.queueHealth === 'degraded' ? 'Message Queue Degraded' : 'All Systems Nominal'}
          />
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh Status
          </Button>
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            <Terminal className="mr-2 h-4 w-4" />
            Live Logs
          </Button>
        </div>
      </div>

      {/* System Status Banner */}
      <Card className="bg-emerald-500/[0.03] dark:bg-emerald-500/[0.02] border-emerald-500/20 rounded-[2.5rem] shadow-glow backdrop-blur-md overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500/50 to-transparent" />
        <CardContent className="py-6 px-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
            <div className="flex items-center gap-5">
              <div className="p-4 rounded-[1.5rem] bg-emerald-500/10 text-emerald-600 shadow-inner-soft">
                <CheckCircle2 className="h-8 w-8" />
              </div>
              <div>
                <p className="font-heading font-bold text-xl tracking-tight text-emerald-800 dark:text-emerald-200">Global Infrastructure Synchronized</p>
                <p className="text-xs font-bold uppercase tracking-widest text-emerald-600/60 mt-1">
                  Uptime: {systemStatus.uptime} • Continuous Pulse established {systemStatus.lastIncident}
                </p>
              </div>
            </div>
            <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 px-4 py-1.5 rounded-xl font-bold uppercase tracking-[0.2em] text-[10px]">
              <Activity className="h-3 w-3 mr-2 animate-pulse" />
              Real-time Node
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Resource Usage - Using Shared StatCard */}
      <StatSection label="Resource Metrics" columns={4}>
        <StatCard
          value={serverStats.cpuUsage}
          label="CPU Usage"
          icon={Server}
          iconColor={serverStats.cpuUsage > 80 ? 'danger' : serverStats.cpuUsage > 60 ? 'warning' : 'success'}
          goal={{ current: serverStats.cpuUsage, target: 100 }}
        />
        <StatCard
          value={serverStats.memoryUsage}
          label="Memory Usage"
          icon={HardDrive}
          iconColor={serverStats.memoryUsage > 80 ? 'danger' : serverStats.memoryUsage > 60 ? 'warning' : 'success'}
          goal={{ current: serverStats.memoryUsage, target: 100 }}
          critical={serverStats.memoryUsage > 80}
        />
        <StatCard
          value={serverStats.diskUsage}
          label="Disk Usage"
          icon={HardDrive}
          iconColor={serverStats.diskUsage > 80 ? 'danger' : serverStats.diskUsage > 60 ? 'warning' : 'success'}
          goal={{ current: serverStats.diskUsage, target: 100 }}
        />
        <StatCard
          value={serverStats.activeConnections}
          label="Active Connections"
          icon={Wifi}
          iconColor="primary"
        />
      </StatSection>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Service Status */}
        <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden shadow-premium">
          <CardHeader className="border-b border-border/5 bg-muted/5 p-6">
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary shadow-sm">
                <Server className="h-5 w-5" />
              </div>
              Intelligence Node Status
            </CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 pl-11">Distributed service protocol health</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border/5">
              {services.map((service) => (
                <div key={service.name} className="flex items-center justify-between p-5 transition-all hover:bg-primary/5 group">
                  <div className="flex items-center gap-4">
                    <div className="p-2.5 rounded-xl bg-background shadow-sm transition-transform group-hover:scale-110">
                      <StatusIndicator status={service.status as any} />
                    </div>
                    <div>
                      <p className="font-heading font-bold text-sm tracking-tight text-foreground/80">{service.name}</p>
                      <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">LATENCY: {service.latency}</p>
                    </div>
                  </div>
                  <Badge variant={service.status === 'healthy' ? 'success' : 'warning'} className="rounded-md px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest">
                    {service.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Alerts */}
        <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden shadow-premium">
          <CardHeader className="border-b border-border/5 bg-muted/5 p-6">
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <div className="p-2 rounded-xl bg-danger/10 text-danger shadow-sm">
                <AlertTriangle className="h-5 w-5" />
              </div>
              Telemetry Alerts
            </CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 pl-11">Real-time anomalous activity stream</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border/5">
              {recentAlerts.map((alert) => (
                <div key={alert.id} className="p-5 flex items-start gap-4 hover:bg-danger/[0.02] transition-all group">
                  <div className={cn(
                    "p-2 rounded-xl bg-background shadow-sm transition-transform group-hover:scale-110",
                    alert.type === 'error' ? 'text-danger' : alert.type === 'warning' ? 'text-warning' : 'text-primary'
                  )}>
                    {alert.type === 'error' ? <XCircle className="h-4 w-4" /> : 
                     alert.type === 'warning' ? <AlertTriangle className="h-4 w-4" /> : 
                     <Activity className="h-4 w-4" />}
                  </div>
                  <div className="flex-1">
                    <p className={cn("text-sm font-medium leading-relaxed", !alert.resolved && 'font-heading font-bold text-foreground/90')}>
                      {alert.message}
                    </p>
                    <div className="flex items-center gap-3 mt-1.5">
                      <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40">{alert.time}</span>
                      {alert.resolved ? (
                        <Badge variant="success" className="bg-emerald-500/5 text-emerald-600 border-none text-[8px] h-4 font-black uppercase tracking-widest">RESOLVED</Badge>
                      ) : (
                        <Badge variant="destructive" className="animate-pulse text-[8px] h-4 font-black uppercase tracking-widest">ACTIVE</Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Active Users */}
        <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden shadow-premium">
          <CardHeader className="border-b border-border/5 bg-muted/5 p-6">
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary shadow-sm">
                <Users className="h-5 w-5" />
              </div>
              Connected Operatives
            </CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 pl-11">Distributed service engagement by node group</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border/5">
              {activeUsers.map((group) => (
                <div key={group.id} className="p-5 flex items-center justify-between transition-all hover:bg-primary/5 group">
                  <div className="flex items-center gap-4">
                    <div className="p-2.5 rounded-xl bg-background shadow-sm transition-transform group-hover:scale-110">
                      <Users className="h-5 w-5 text-muted-foreground/40" />
                    </div>
                    <div>
                      <p className="font-heading font-bold text-sm tracking-tight text-foreground/80">{group.name}</p>
                      <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{group.count} ACTIVE NODES</p>
                    </div>
                  </div>
                  {group.trend === 'up' ? (
                    <Badge variant="success" className="bg-emerald-500/5 text-emerald-600 border-none text-[8px] h-4 font-black uppercase tracking-widest">VOLATILE UP</Badge>
                  ) : (
                    <Badge variant="secondary" className="bg-muted/10 text-muted-foreground/60 border-none text-[8px] h-4 font-black uppercase tracking-widest">{group.trend}</Badge>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Security Overview */}
        <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden shadow-premium text-left">
          <CardHeader className="border-b border-border/5 bg-muted/5 p-6">
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary shadow-sm">
                <Shield className="h-5 w-5" />
              </div>
              Security Protocol
            </CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 pl-11">Distributed firewall and compliance nodes</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border/5">
              <div className="flex items-center justify-between p-5 transition-all hover:bg-primary/5 group">
                <div className="flex items-center gap-4">
                  <div className="p-2.5 rounded-xl bg-background shadow-sm transition-transform group-hover:scale-110">
                    <Lock className="h-4 w-4 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-heading font-bold text-sm tracking-tight text-foreground/80">SSL Certificate</p>
                    <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">RSA 4096-BIT SYNCHRONIZED</p>
                  </div>
                </div>
                <Badge variant="outline" className="bg-emerald-500/5 text-emerald-600 border-none text-[8px] h-4 font-black uppercase tracking-widest">VALID NODE</Badge>
              </div>
              <div className="flex items-center justify-between p-5 transition-all hover:bg-primary/5 group">
                <div className="flex items-center gap-4">
                  <div className="p-2.5 rounded-xl bg-background shadow-sm transition-transform group-hover:scale-110">
                    <Shield className="h-4 w-4 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-heading font-bold text-sm tracking-tight text-foreground/80">Firewall Architecture</p>
                    <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">DISTRIBUTED WAF ACTIVE</p>
                  </div>
                </div>
                <Badge variant="outline" className="bg-emerald-500/5 text-emerald-600 border-none text-[8px] h-4 font-black uppercase tracking-widest">ACTIVE</Badge>
              </div>
              <div className="p-5">
                <Button variant="outline" className="w-full rounded-xl border-primary/20 hover:bg-primary/5 text-primary h-11">
                  Update Security Policies
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
