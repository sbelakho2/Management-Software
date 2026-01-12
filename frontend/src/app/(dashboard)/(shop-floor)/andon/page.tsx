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

export default function AndonBoardPage() {
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
    <div className="space-y-6" data-testid="andon-page">
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
            variant="outline"
            className="gap-2"
            onClick={() => router.push('/andon/analytics')}
          >
            <TrendingUp className="h-4 w-4" />
            Analytics
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
                <p className="text-3xl font-bold">{activeEvents.length}</p>
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
                <p className="text-3xl font-bold">{runningMachines}/{workCenters.size}</p>
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
                  metrics.avgResponseTime < 300 ? 'text-success' : 'text-warning'
                )}>
                  {Math.round(metrics.avgResponseTime / 60)}m
                </p>
                <p className="text-sm text-muted-foreground">Avg Response</p>
              </div>
              <Zap className="h-8 w-8 text-primary" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-bold">{metrics.totalResolved}</p>
                <p className="text-sm text-muted-foreground">Resolved Today</p>
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
            Active Alerts ({activeEvents.length})
          </h2>
          <div className="space-y-3">
            {activeEvents.length === 0 ? (
              <Card className="border-success bg-success/5">
                <CardContent className="p-6 text-center">
                  <CheckCircle className="h-12 w-12 text-success mx-auto mb-2" />
                  <p className="font-medium text-success">All Clear</p>
                  <p className="text-sm text-muted-foreground">No active alerts</p>
                </CardContent>
              </Card>
            ) : (
              activeEvents.map((alert) => (
                <Card key={alert.id} className={cn('border-l-4', alert.severity === 'critical' ? 'border-danger' : 'border-warning')}>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-semibold">{alert.work_center_id}</div>
                      <Badge variant={alert.severity === 'critical' ? 'danger' : 'warning'}>{alert.severity}</Badge>
                    </div>
                    <p className="text-sm mb-3">{alert.description}</p>
                    <div className="flex justify-between items-center text-xs text-muted-foreground">
                      <span>{formatElapsedTime(alert.created_at)}</span>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => handleAcknowledge(alert.id)}>Ack</Button>
                        <Button size="sm" variant="outline" onClick={() => handleEscalate(alert.id)}>Escalate</Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
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
            {Array.from(workCenters.values()).map((wc) => (
              <Card key={wc.id} className="relative overflow-hidden">
                <div className={cn('absolute top-0 left-0 w-1 h-full', wc.status === 'running' ? 'bg-success' : 'bg-danger')} />
                <CardContent className="p-4 pl-5">
                  <div className="flex justify-between mb-2">
                    <span className="font-medium">{wc.name}</span>
                    <Badge variant={wc.status === 'running' ? 'success' : 'secondary'}>{wc.status}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mb-4">OEE: {wc.oee}%</div>
                  <Progress value={wc.efficiency} className="h-1.5" />
                </CardContent>
              </Card>
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
