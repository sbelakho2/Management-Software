'use client';

import * as React from 'react';
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
import { Skeleton } from '@/components/ui/skeleton';
import Link from 'next/link';

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

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  unit,
  variant = 'default' 
}: { 
  title: string; 
  value: number; 
  icon: React.ElementType;
  unit?: string;
  variant?: 'default' | 'warning' | 'danger' | 'success';
}) {
  const getVariant = (val: number) => {
    if (val > 80) return 'danger';
    if (val > 60) return 'warning';
    return 'success';
  };

  const actualVariant = variant === 'default' ? getVariant(value) : variant;

  const variantStyles = {
    default: 'bg-primary/10 text-primary',
    warning: 'bg-amber-500/10 text-amber-600',
    danger: 'bg-destructive/10 text-destructive',
    success: 'bg-emerald-500/10 text-emerald-600',
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <div className={`p-2 rounded-full ${variantStyles[actualVariant]}`}>
            <Icon className="h-4 w-4" />
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold">{value}</span>
            {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
          </div>
          <Progress value={value} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function ITDashboard() {
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">IT Dashboard</h1>
          <p className="text-muted-foreground">
            System health, security, and infrastructure monitoring
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh Status
          </Button>
          <Button variant="outline" size="sm">
            <Terminal className="h-4 w-4 mr-2" />
            Logs
          </Button>
        </div>
      </div>

      {/* System Status Banner */}
      <Card className="bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6 text-emerald-600" />
              <div>
                <p className="font-medium text-emerald-800 dark:text-emerald-200">All Systems Operational</p>
                <p className="text-sm text-emerald-600 dark:text-emerald-400">
                  Uptime: {systemStatus.uptime} • Last incident: {systemStatus.lastIncident}
                </p>
              </div>
            </div>
            <Badge variant="outline" className="bg-emerald-100 text-emerald-700 border-emerald-300">
              <Activity className="h-3 w-3 mr-1" />
              Live
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Resource Usage */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="CPU Usage"
          value={serverStats.cpuUsage}
          icon={Server}
          unit="%"
        />
        <StatCard
          title="Memory Usage"
          value={serverStats.memoryUsage}
          icon={HardDrive}
          unit="%"
        />
        <StatCard
          title="Disk Usage"
          value={serverStats.diskUsage}
          icon={HardDrive}
          unit="%"
        />
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Active Connections</p>
                <p className="text-2xl font-bold mt-1">{serverStats.activeConnections}</p>
                <p className="text-xs text-muted-foreground mt-1">Across all services</p>
              </div>
              <div className="p-3 rounded-full bg-primary/10 text-primary">
                <Wifi className="h-5 w-5" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Service Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Service Status
            </CardTitle>
            <CardDescription>Real-time service health</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {services.map((service) => (
                <div
                  key={service.name}
                  className="flex items-center justify-between py-2 border-b last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <StatusIndicator status={service.status as any} />
                    <span className="font-medium text-sm">{service.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">{service.latency}</span>
                    <Badge 
                      variant={service.status === 'healthy' ? 'outline' : 'destructive'}
                      className={service.status === 'degraded' ? 'bg-amber-100 text-amber-700 border-amber-300' : ''}
                    >
                      {service.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Recent Alerts
            </CardTitle>
            <CardDescription>System notifications and incidents</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-start gap-3 py-2 border-b last:border-0"
                >
                  <div className={`mt-0.5 p-1 rounded ${
                    alert.type === 'error' ? 'bg-destructive/10 text-destructive' :
                    alert.type === 'warning' ? 'bg-amber-100 text-amber-600' :
                    'bg-blue-100 text-blue-600'
                  }`}>
                    <AlertTriangle className="h-3 w-3" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{alert.message}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Clock className="h-3 w-3 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">{alert.time}</span>
                      {alert.resolved && (
                        <Badge variant="outline" className="text-xs">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Resolved
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Active Users */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Active Users
            </CardTitle>
            <CardDescription>Current user sessions by team</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {activeUsers.map((group) => (
                <div
                  key={group.id}
                  className="flex items-center justify-between py-2 border-b last:border-0"
                >
                  <span className="font-medium text-sm">{group.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold">{group.count}</span>
                    <Badge variant="outline" className="text-xs">
                      {group.trend}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Security Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Security Overview
            </CardTitle>
            <CardDescription>Security status and compliance</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2 border-b">
                <div className="flex items-center gap-2">
                  <Lock className="h-4 w-4 text-emerald-600" />
                  <span className="text-sm">SSL Certificate</span>
                </div>
                <Badge variant="outline" className="text-emerald-600">Valid</Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-emerald-600" />
                  <span className="text-sm">Firewall Status</span>
                </div>
                <Badge variant="outline" className="text-emerald-600">Active</Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  <span className="text-sm">Last Security Scan</span>
                </div>
                <span className="text-sm text-muted-foreground">2 hours ago</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  <span className="text-sm">Failed Login Attempts</span>
                </div>
                <span className="text-sm font-medium">3 today</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
