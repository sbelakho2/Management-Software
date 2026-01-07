'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
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
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge, BadgeProps } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn, formatDate } from '@/lib/utils';

type AlertSeverity = 'critical' | 'warning' | 'info';
type AlertStatus = 'active' | 'acknowledged' | 'resolved';
type WorkCenterStatus = 'running' | 'stopped' | 'maintenance' | 'changeover';

interface AndonAlert {
  id: string;
  workCenterId: string;
  workCenterName: string;
  type: 'quality' | 'safety' | 'material' | 'equipment' | 'support';
  severity: AlertSeverity;
  status: AlertStatus;
  message: string;
  createdAt: string;
  acknowledgedAt?: string;
  acknowledgedBy?: string;
  resolvedAt?: string;
  resolvedBy?: string;
  escalationLevel: number;
}

interface WorkCenter {
  id: string;
  name: string;
  status: WorkCenterStatus;
  operator?: string;
  currentJob?: string;
  targetCount: number;
  actualCount: number;
  efficiency: number;
  activeAlerts: number;
  lastUpdate: string;
}

const mockAlerts: AndonAlert[] = [
  { id: '1', workCenterId: 'WC-001', workCenterName: 'CNC Machine #1', type: 'quality', severity: 'critical', status: 'active', message: 'Surface finish out of tolerance', createdAt: '2024-01-15T14:25:00Z', escalationLevel: 2 },
  { id: '2', workCenterId: 'WC-003', workCenterName: 'CNC Machine #3', type: 'material', severity: 'warning', status: 'acknowledged', message: 'Raw material running low', createdAt: '2024-01-15T14:10:00Z', acknowledgedAt: '2024-01-15T14:15:00Z', acknowledgedBy: 'John Doe', escalationLevel: 1 },
  { id: '3', workCenterId: 'WC-002', workCenterName: 'CNC Machine #2', type: 'equipment', severity: 'warning', status: 'active', message: 'Tool wear warning - replace soon', createdAt: '2024-01-15T13:45:00Z', escalationLevel: 1 },
  { id: '4', workCenterId: 'WC-004', workCenterName: 'Inspection Station', type: 'support', severity: 'info', status: 'active', message: 'Requesting quality support', createdAt: '2024-01-15T14:20:00Z', escalationLevel: 0 },
];

const mockWorkCenters: WorkCenter[] = [
  { id: 'WC-001', name: 'CNC Machine #1', status: 'stopped', operator: 'Sarah Chen', currentJob: 'WO-2024-001', targetCount: 100, actualCount: 45, efficiency: 92, activeAlerts: 1, lastUpdate: '2024-01-15T14:25:00Z' },
  { id: 'WC-002', name: 'CNC Machine #2', status: 'running', operator: 'David Lee', currentJob: 'WO-2024-002', targetCount: 50, actualCount: 38, efficiency: 95, activeAlerts: 1, lastUpdate: '2024-01-15T14:30:00Z' },
  { id: 'WC-003', name: 'CNC Machine #3', status: 'running', operator: 'Maria Garcia', currentJob: 'WO-2024-003', targetCount: 75, actualCount: 70, efficiency: 88, activeAlerts: 1, lastUpdate: '2024-01-15T14:30:00Z' },
  { id: 'WC-004', name: 'Inspection Station', status: 'running', operator: 'Emily Rodriguez', targetCount: 200, actualCount: 185, efficiency: 96, activeAlerts: 1, lastUpdate: '2024-01-15T14:28:00Z' },
  { id: 'WC-005', name: 'Assembly Line 1', status: 'changeover', operator: 'Mike Brown', targetCount: 40, actualCount: 40, efficiency: 100, activeAlerts: 0, lastUpdate: '2024-01-15T14:20:00Z' },
  { id: 'WC-006', name: 'Packaging', status: 'running', operator: 'Lisa Wang', targetCount: 120, actualCount: 115, efficiency: 94, activeAlerts: 0, lastUpdate: '2024-01-15T14:30:00Z' },
];

const severityConfig: Record<AlertSeverity, { label: string; color: string; bgColor: string; borderColor: string }> = {
  critical: { label: 'Critical', color: 'text-white', bgColor: 'bg-danger', borderColor: 'border-danger' },
  warning: { label: 'Warning', color: 'text-warning-foreground', bgColor: 'bg-warning', borderColor: 'border-warning' },
  info: { label: 'Info', color: 'text-primary-foreground', bgColor: 'bg-primary', borderColor: 'border-primary' },
};

const alertTypeConfig: Record<string, { label: string; icon: typeof AlertTriangle; color: string }> = {
  quality: { label: 'Quality', icon: AlertTriangle, color: 'text-danger' },
  safety: { label: 'Safety', icon: AlertTriangle, color: 'text-danger' },
  material: { label: 'Material', icon: Package, color: 'text-warning' },
  equipment: { label: 'Equipment', icon: Wrench, color: 'text-warning' },
  support: { label: 'Support', icon: Users, color: 'text-primary' },
};

const workCenterStatusConfig: Record<WorkCenterStatus, { label: string; color: string; icon: typeof Play }> = {
  running: { label: 'Running', color: 'bg-success', icon: Play },
  stopped: { label: 'Stopped', color: 'bg-danger', icon: Pause },
  maintenance: { label: 'Maintenance', color: 'bg-warning', icon: Wrench },
  changeover: { label: 'Changeover', color: 'bg-primary', icon: RefreshCw },
};

function formatElapsedTime(timestamp: string): string {
  const elapsed = Date.now() - new Date(timestamp).getTime();
  const minutes = Math.floor(elapsed / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m ago`;
}

function AlertCard({ alert, onAcknowledge, onEscalate }: { alert: AndonAlert; onAcknowledge: () => void; onEscalate: () => void }) {
  const severity = severityConfig[alert.severity];
  const typeConfig = alertTypeConfig[alert.type];
  const TypeIcon = typeConfig.icon;
  const isActive = alert.status === 'active';

  return (
    <Card className={cn(
      'relative overflow-hidden transition-all',
      isActive && alert.severity === 'critical' && 'animate-pulse border-danger',
      severity.borderColor,
      'border-l-4'
    )}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className={cn('p-1.5 rounded', severity.bgColor)}>
              <TypeIcon className={cn('h-4 w-4', severity.color)} />
            </span>
            <div>
              <p className="font-semibold">{alert.workCenterName}</p>
              <p className="text-xs text-muted-foreground">{typeConfig.label}</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {alert.escalationLevel > 0 && (
              <Badge variant="outline" size="sm" className="gap-1">
                <ArrowUp className="h-3 w-3" />
                L{alert.escalationLevel}
              </Badge>
            )}
            <Badge variant={alert.status === 'active' ? 'danger' : alert.status === 'acknowledged' ? 'warning' : 'success'} size="sm">
              {alert.status === 'active' ? 'Active' : alert.status === 'acknowledged' ? 'Ack' : 'Resolved'}
            </Badge>
          </div>
        </div>
        
        <p className="text-sm mb-3">{alert.message}</p>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            {formatElapsedTime(alert.createdAt)}
            {alert.acknowledgedBy && (
              <span className="ml-2">• Ack by {alert.acknowledgedBy}</span>
            )}
          </div>
          
          {isActive && (
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={onAcknowledge}>
                <CheckCircle className="mr-1 h-3 w-3" />
                Ack
              </Button>
              <Button size="sm" variant="outline" onClick={onEscalate}>
                <ArrowUp className="mr-1 h-3 w-3" />
                Escalate
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function WorkCenterCard({ workCenter }: { workCenter: WorkCenter }) {
  const status = workCenterStatusConfig[workCenter.status];
  const StatusIcon = status.icon;
  const progressPercent = (workCenter.actualCount / workCenter.targetCount) * 100;
  const isAheadOfTarget = progressPercent >= 100;
  const isBehind = workCenter.efficiency < 90;

  return (
    <Card className={cn(
      'relative overflow-hidden',
      workCenter.activeAlerts > 0 && 'border-warning'
    )}>
      <div className={cn('absolute top-0 left-0 w-1 h-full', status.color)} />
      <CardContent className="p-4 pl-5">
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="font-semibold">{workCenter.name}</p>
            <p className="text-xs text-muted-foreground">{workCenter.operator}</p>
          </div>
          <div className="flex items-center gap-2">
            {workCenter.activeAlerts > 0 && (
              <Badge variant="danger" size="sm">{workCenter.activeAlerts} Alert</Badge>
            )}
            <Badge variant={workCenter.status === 'running' ? 'success' : 'secondary'} size="sm" className="gap-1">
              <StatusIcon className="h-3 w-3" />
              {status.label}
            </Badge>
          </div>
        </div>

        {workCenter.currentJob && (
          <p className="text-xs text-muted-foreground mb-2">Job: {workCenter.currentJob}</p>
        )}

        {/* Progress Bar */}
        <div className="mb-2">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted-foreground">Progress</span>
            <span className={cn('font-medium', isAheadOfTarget ? 'text-success' : isBehind ? 'text-danger' : '')}>
              {workCenter.actualCount} / {workCenter.targetCount}
            </span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div 
              className={cn(
                'h-full rounded-full transition-all',
                isAheadOfTarget ? 'bg-success' : isBehind ? 'bg-warning' : 'bg-primary'
              )}
              style={{ width: `${Math.min(progressPercent, 100)}%` }}
            />
          </div>
        </div>

        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Efficiency</span>
          <span className={cn(
            'font-medium',
            workCenter.efficiency >= 95 ? 'text-success' : 
            workCenter.efficiency >= 85 ? 'text-warning' : 'text-danger'
          )}>
            {workCenter.efficiency}%
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AndonBoardPage() {
  const router = useRouter();
  const [soundEnabled, setSoundEnabled] = React.useState(true);
  const [isFullscreen, setIsFullscreen] = React.useState(false);
  const [lastRefresh, setLastRefresh] = React.useState(new Date());

  const activeAlerts = mockAlerts.filter(a => a.status === 'active');
  const criticalAlerts = activeAlerts.filter(a => a.severity === 'critical');
  const runningMachines = mockWorkCenters.filter(w => w.status === 'running').length;
  const averageEfficiency = Math.round(
    mockWorkCenters.reduce((sum, wc) => sum + wc.efficiency, 0) / mockWorkCenters.length
  );

  const handleAcknowledge = (alertId: string) => {
    // Would acknowledge via API
    console.log('Acknowledging alert:', alertId);
  };

  const handleEscalate = (alertId: string) => {
    // Would escalate via API
    console.log('Escalating alert:', alertId);
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

  // Auto-refresh every 30 seconds
  React.useEffect(() => {
    const interval = setInterval(() => {
      setLastRefresh(new Date());
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="h-6 w-6 text-warning" />
            Andon Board
          </h1>
          <p className="text-muted-foreground">
            Real-time production monitoring • Last updated {formatDate(lastRefresh, { hour: 'numeric', minute: 'numeric', second: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => setSoundEnabled(!soundEnabled)}
            title={soundEnabled ? 'Mute alerts' : 'Enable alert sounds'}
          >
            {soundEnabled ? <Volume2 className="h-5 w-5" /> : <VolumeX className="h-5 w-5" />}
          </Button>
          <Button 
            variant="ghost" 
            size="icon"
            onClick={toggleFullscreen}
            title="Toggle fullscreen"
          >
            <Maximize2 className="h-5 w-5" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setLastRefresh(new Date())}>
            <RefreshCw className="h-5 w-5" />
          </Button>
          <Button variant="outline" onClick={() => router.push('/andon/settings')}>
            <Settings className="mr-2 h-4 w-4" />
            Configure
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className={cn(criticalAlerts.length > 0 && 'border-danger bg-danger/5')}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-bold">{activeAlerts.length}</p>
                <p className="text-sm text-muted-foreground">Active Alerts</p>
              </div>
              <AlertTriangle className={cn('h-8 w-8', criticalAlerts.length > 0 ? 'text-danger' : 'text-muted-foreground')} />
            </div>
            {criticalAlerts.length > 0 && (
              <Badge variant="danger" className="mt-2">{criticalAlerts.length} Critical</Badge>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-bold">{runningMachines}/{mockWorkCenters.length}</p>
                <p className="text-sm text-muted-foreground">Machines Running</p>
              </div>
              <Play className="h-8 w-8 text-success" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className={cn(
                  'text-3xl font-bold',
                  averageEfficiency >= 95 ? 'text-success' : 
                  averageEfficiency >= 85 ? 'text-warning' : 'text-danger'
                )}>
                  {averageEfficiency}%
                </p>
                <p className="text-sm text-muted-foreground">Avg Efficiency</p>
              </div>
              <Zap className="h-8 w-8 text-primary" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-bold">
                  {mockWorkCenters.reduce((sum, wc) => sum + wc.actualCount, 0)}
                </p>
                <p className="text-sm text-muted-foreground">Units Produced</p>
              </div>
              <Package className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Active Alerts */}
        <div className="lg:col-span-1">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            Active Alerts ({activeAlerts.length})
          </h2>
          <div className="space-y-3">
            {activeAlerts.length === 0 ? (
              <Card className="border-success bg-success/5">
                <CardContent className="p-6 text-center">
                  <CheckCircle className="h-12 w-12 text-success mx-auto mb-2" />
                  <p className="font-medium text-success">All Clear</p>
                  <p className="text-sm text-muted-foreground">No active alerts</p>
                </CardContent>
              </Card>
            ) : (
              mockAlerts
                .filter(a => a.status !== 'resolved')
                .sort((a, b) => {
                  const severityOrder = { critical: 0, warning: 1, info: 2 };
                  return severityOrder[a.severity] - severityOrder[b.severity];
                })
                .map((alert) => (
                  <AlertCard 
                    key={alert.id} 
                    alert={alert}
                    onAcknowledge={() => handleAcknowledge(alert.id)}
                    onEscalate={() => handleEscalate(alert.id)}
                  />
                ))
            )}
          </div>
        </div>

        {/* Work Centers */}
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Wrench className="h-5 w-5" />
            Work Centers
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {mockWorkCenters.map((workCenter) => (
              <WorkCenterCard key={workCenter.id} workCenter={workCenter} />
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm">
              <PhoneCall className="mr-2 h-4 w-4" />
              Call Supervisor
            </Button>
            <Button variant="outline" size="sm">
              <MessageSquare className="mr-2 h-4 w-4" />
              Broadcast Message
            </Button>
            <Button variant="outline" size="sm">
              <Wrench className="mr-2 h-4 w-4" />
              Request Maintenance
            </Button>
            <Button variant="outline" size="sm">
              <Package className="mr-2 h-4 w-4" />
              Request Material
            </Button>
            <Button variant="outline" size="sm">
              <AlertTriangle className="mr-2 h-4 w-4" />
              Report Issue
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
