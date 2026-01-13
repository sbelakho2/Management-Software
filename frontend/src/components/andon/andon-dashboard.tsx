'use client';

import * as React from 'react';
import {
  useAndonStore,
  getSeverityColor,
  getSeverityLabel,
  getAndonTypeLabel,
  getAndonTypeIcon,
  getStatusLabel,
  getStatusColor,
  formatElapsedTime,
  formatDuration,
} from '@/stores/andon-store';
import type { AndonEvent, AndonType, AndonStatus, Severity } from '@/types';
import { cn } from '@/lib/utils';

// ============================================================================
// Icons
// ============================================================================

function AlertTriangleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22,4 12,14.01 9,11.01" />
    </svg>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12,6 12,12 16,14" />
    </svg>
  );
}

function ArrowUpIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}

function VolumeIcon({ className, muted }: { className?: string; muted?: boolean }) {
  if (muted) {
    return (
      <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="11,5 6,9 2,9 2,15 6,15 11,19 11,5" />
        <line x1="23" y1="9" x2="17" y2="15" />
        <line x1="17" y1="9" x2="23" y2="15" />
      </svg>
    );
  }
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="11,5 6,9 2,9 2,15 6,15 11,19 11,5" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    </svg>
  );
}

function MaximizeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15,3 21,3 21,9" />
      <polyline points="9,21 3,21 3,15" />
      <line x1="21" y1="3" x2="14" y2="10" />
      <line x1="3" y1="21" x2="10" y2="14" />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23,4 23,10 17,10" />
      <polyline points="1,20 1,14 7,14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

function BellIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

function WifiIcon({ className, connected }: { className?: string; connected?: boolean }) {
  return (
    <svg className={cn(className, connected ? 'text-green-500' : 'text-red-500')} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12.55a11 11 0 0 1 14.08 0" />
      <path d="M1.42 9a16 16 0 0 1 21.16 0" />
      <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
      <line x1="12" y1="20" x2="12.01" y2="20" />
    </svg>
  );
}

// ============================================================================
// Dashboard Header
// ============================================================================

export interface AndonDashboardHeaderProps {
  title?: string;
  onRefresh?: () => void;
  showConnectionStatus?: boolean;
}

export function AndonDashboardHeader({
  title = 'Andon Dashboard',
  onRefresh,
  showConnectionStatus = true,
}: AndonDashboardHeaderProps) {
  const { config, isConnected, toggleSound, toggleFullscreen, criticalCount, unacknowledgedCount, lastHeartbeat } = useAndonStore();

  return (
    <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4 dark:border-gray-700 dark:bg-gray-900">
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{title}</h1>
        
        {/* Alert counts */}
        <div className="flex items-center gap-2">
          {criticalCount > 0 && (
            <span className="flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-sm font-semibold text-red-700 animate-pulse">
              <AlertTriangleIcon className="h-4 w-4" />
              {criticalCount} Critical
            </span>
          )}
          {unacknowledgedCount > 0 && (
            <span className="flex items-center gap-1 rounded-full bg-orange-100 px-3 py-1 text-sm font-semibold text-orange-700">
              <BellIcon className="h-4 w-4" />
              {unacknowledgedCount} Active
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Connection status */}
        {showConnectionStatus && (
          <div className="flex items-center gap-2 rounded-md border border-gray-200 px-3 py-2 text-sm dark:border-gray-600">
            <WifiIcon className="h-4 w-4" connected={isConnected} />
            <span className={cn('font-medium', isConnected ? 'text-green-600' : 'text-red-600')}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
            {lastHeartbeat && (
              <span className="text-xs text-gray-400">
                {formatElapsedTime(lastHeartbeat)}
              </span>
            )}
          </div>
        )}

        {/* Refresh */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="rounded-md border border-gray-200 p-2 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            title="Refresh"
          >
            <RefreshIcon className="h-5 w-5" />
          </button>
        )}

        {/* Sound toggle */}
        <button
          onClick={toggleSound}
          className={cn(
            'rounded-md border p-2',
            config.soundEnabled
              ? 'border-green-200 bg-green-50 text-green-600'
              : 'border-gray-200 text-gray-400'
          )}
          title={config.soundEnabled ? 'Mute alerts' : 'Enable alert sounds'}
        >
          <VolumeIcon className="h-5 w-5" muted={!config.soundEnabled} />
        </button>

        {/* Fullscreen toggle */}
        <button
          onClick={toggleFullscreen}
          className="rounded-md border border-gray-200 p-2 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          title="Toggle fullscreen"
        >
          <MaximizeIcon className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
}

// ============================================================================
// Metrics Bar
// ============================================================================

export function AndonMetricsBar() {
  const { metrics } = useAndonStore();

  return (
    <div className="grid grid-cols-2 gap-4 border-b border-gray-200 bg-gray-50 px-6 py-4 dark:border-gray-700 dark:bg-gray-800 md:grid-cols-4 lg:grid-cols-6">
      <MetricCard
        label="Active Alerts"
        value={metrics.totalActive}
        color={metrics.totalActive > 0 ? 'red' : 'gray'}
        trend={metrics.totalActive > 0 ? 'up' : undefined}
      />
      <MetricCard
        label="Acknowledged"
        value={metrics.totalAcknowledged}
        color="yellow"
      />
      <MetricCard
        label="Resolved Today"
        value={metrics.totalResolved}
        color="green"
      />
      <MetricCard
        label="Avg Response"
        value={formatDuration(metrics.avgResponseTime)}
        color="blue"
      />
      <MetricCard
        label="Avg Resolution"
        value={formatDuration(metrics.avgResolutionTime)}
        color="purple"
      />
      <MetricCard
        label="By Type"
        value={
          <div className="flex gap-2 text-xs">
            {Object.entries(metrics.byType).map(([type, count]) => (
              count > 0 && (
                <span key={type} className="flex items-center gap-1">
                  {getAndonTypeIcon(type as AndonType)} {count}
                </span>
              )
            ))}
          </div>
        }
        color="gray"
      />
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: React.ReactNode;
  color: 'red' | 'yellow' | 'green' | 'blue' | 'purple' | 'gray';
  trend?: 'up' | 'down';
}

function MetricCard({ label, value, color, trend }: MetricCardProps) {
  const colorClasses = {
    red: 'text-red-600',
    yellow: 'text-yellow-600',
    green: 'text-green-600',
    blue: 'text-blue-600',
    purple: 'text-purple-600',
    gray: 'text-gray-600',
  };

  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
      <div className="flex items-center gap-1">
        <span className={cn('text-lg font-semibold', colorClasses[color])}>
          {value}
        </span>
        {trend === 'up' && <ArrowUpIcon className="h-4 w-4 text-red-500" />}
        {trend === 'down' && <ArrowUpIcon className="h-4 w-4 rotate-180 text-green-500" />}
      </div>
    </div>
  );
}

// ============================================================================
// Event Card
// ============================================================================

export interface AndonEventCardProps {
  event: AndonEvent;
  onAcknowledge?: () => void;
  onEscalate?: () => void;
  onResolve?: () => void;
  onClick?: () => void;
  isSelected?: boolean;
  compact?: boolean;
}

export function AndonEventCard({
  event,
  onAcknowledge,
  onEscalate,
  onResolve,
  onClick,
  isSelected,
  compact,
}: AndonEventCardProps) {
  const isActive = event.status !== 'resolved';
  const isTriggeredOrEscalated = event.status === 'triggered' || event.status === 'escalated';
  const isCritical = event.severity === 'critical';
  const severityColor = getSeverityColor(event.severity);

  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          onClick();
        }
      }}
      className={cn(
        'relative overflow-hidden rounded-lg border bg-white shadow-sm transition-all dark:bg-gray-900',
        isTriggeredOrEscalated && isCritical && 'animate-pulse',
        isSelected && 'ring-2 ring-blue-500',
        onClick && 'cursor-pointer hover:shadow-md',
        compact ? 'p-3' : 'p-4'
      )}
      style={{ borderLeftWidth: 4, borderLeftColor: severityColor }}
    >
      {/* Header */}
      <div className="mb-2 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{getAndonTypeIcon(event.type)}</span>
          <div>
            <p className="font-semibold text-gray-900 dark:text-white">
              {event.work_center?.name || 'Unknown Work Center'}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {getAndonTypeLabel(event.type)} • {event.andon_number}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {event.escalation_level > 0 && (
            <span className="flex items-center gap-1 rounded-full border border-orange-200 bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700">
              <ArrowUpIcon className="h-3 w-3" />
              L{event.escalation_level}
            </span>
          )}
          <span
            className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
            style={{ backgroundColor: getStatusColor(event.status) }}
          >
            {getStatusLabel(event.status)}
          </span>
        </div>
      </div>

      {/* Description */}
      <p className={cn('text-gray-700 dark:text-gray-300', compact ? 'text-sm mb-2' : 'mb-3')}>
        {event.description}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1">
            <ClockIcon className="h-3 w-3" />
            {formatElapsedTime(event.created_at)}
          </span>
          {event.acknowledged_by && (
            <span>Ack by {event.acknowledged_by}</span>
          )}
          {event.triggered_user && (
            <span>Triggered by {event.triggered_user.full_name}</span>
          )}
        </div>

        {/* Actions */}
        {isActive && !compact && (
          <div className="flex gap-2">
            {onAcknowledge && event.status === 'triggered' && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAcknowledge();
                }}
                className="flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
              >
                <CheckCircleIcon className="h-3 w-3" />
                Acknowledge
              </button>
            )}
            {onEscalate && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onEscalate();
                }}
                className="flex items-center gap-1 rounded-md border border-orange-300 bg-orange-50 px-3 py-1.5 text-xs font-medium text-orange-700 hover:bg-orange-100"
              >
                <ArrowUpIcon className="h-3 w-3" />
                Escalate
              </button>
            )}
            {onResolve && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onResolve();
                }}
                className="flex items-center gap-1 rounded-md border border-green-300 bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100"
              >
                <CheckCircleIcon className="h-3 w-3" />
                Resolve
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Event List
// ============================================================================

export interface AndonEventListProps {
  events: AndonEvent[];
  onEventClick?: (event: AndonEvent) => void;
  onAcknowledge?: (eventId: string) => void;
  onEscalate?: (eventId: string) => void;
  onResolve?: (eventId: string) => void;
  selectedEventId?: string | null;
  compact?: boolean;
  emptyMessage?: string;
}

export function AndonEventList({
  events,
  onEventClick,
  onAcknowledge,
  onEscalate,
  onResolve,
  selectedEventId,
  compact,
  emptyMessage = 'No active alerts',
}: AndonEventListProps) {
  if (events.length === 0) {
    return (
      <div className="flex h-48 flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600">
        <CheckCircleIcon className="mb-2 h-12 w-12 text-green-500" />
        <p className="text-gray-500 dark:text-gray-400">{emptyMessage}</p>
        <p className="text-sm text-gray-400 dark:text-gray-500">All systems operating normally</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <AndonEventCard
          key={event.id}
          event={event}
          onClick={onEventClick ? () => onEventClick(event) : undefined}
          onAcknowledge={onAcknowledge ? () => onAcknowledge(event.id) : undefined}
          onEscalate={onEscalate ? () => onEscalate(event.id) : undefined}
          onResolve={onResolve ? () => onResolve(event.id) : undefined}
          isSelected={selectedEventId === event.id}
          compact={compact}
        />
      ))}
    </div>
  );
}

// ============================================================================
// Work Center Status Card
// ============================================================================

export interface WorkCenterStatusCardProps {
  workCenter: {
    id: string;
    name: string;
    status: 'running' | 'stopped' | 'maintenance' | 'changeover' | 'idle';
    operator?: string;
    currentJob?: string;
    targetCount: number;
    actualCount: number;
    efficiency: number;
    oee: number;
    activeAndonCount: number;
    lastUpdate: string;
  };
  onClick?: () => void;
  isSelected?: boolean;
}

export function WorkCenterStatusCard({
  workCenter,
  onClick,
  isSelected,
}: WorkCenterStatusCardProps) {
  const statusColors = {
    running: { bg: 'bg-green-500', text: 'Running', icon: '▶️' },
    stopped: { bg: 'bg-red-500', text: 'Stopped', icon: '⏸️' },
    maintenance: { bg: 'bg-yellow-500', text: 'Maintenance', icon: '🔧' },
    changeover: { bg: 'bg-blue-500', text: 'Changeover', icon: '🔄' },
    idle: { bg: 'bg-gray-400', text: 'Idle', icon: '💤' },
  };

  const status = statusColors[workCenter.status];
  const progressPercent = (workCenter.actualCount / workCenter.targetCount) * 100;
  const isBehind = progressPercent < 90;

  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          onClick();
        }
      }}
      className={cn(
        'relative overflow-hidden rounded-lg border bg-white shadow-sm transition-all dark:bg-gray-900',
        workCenter.activeAndonCount > 0 && 'border-red-300',
        isSelected && 'ring-2 ring-blue-500',
        onClick && 'cursor-pointer hover:shadow-md'
      )}
    >
      {/* Status bar */}
      <div className={cn('h-1.5', status.bg)} />

      <div className="p-4">
        {/* Header */}
        <div className="mb-3 flex items-start justify-between">
          <div>
            <p className="font-semibold text-gray-900 dark:text-white">{workCenter.name}</p>
            {workCenter.operator && (
              <p className="text-xs text-gray-500 dark:text-gray-400">{workCenter.operator}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {workCenter.activeAndonCount > 0 && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white animate-pulse">
                {workCenter.activeAndonCount}
              </span>
            )}
            <span className="flex items-center gap-1 text-xs">
              <span>{status.icon}</span>
              <span className="font-medium">{status.text}</span>
            </span>
          </div>
        </div>

        {/* Progress */}
        <div className="mb-3">
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Progress</span>
            <span className={cn('font-medium', isBehind ? 'text-red-600' : 'text-gray-900 dark:text-white')}>
              {workCenter.actualCount}/{workCenter.targetCount}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
            <div
              className={cn(
                'h-full rounded-full transition-all',
                progressPercent >= 100 ? 'bg-green-500' : isBehind ? 'bg-red-500' : 'bg-blue-500'
              )}
              style={{ width: `${Math.min(progressPercent, 100)}%` }}
            />
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-1 xs:grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-gray-500 dark:text-gray-400">Efficiency</span>
            <p className={cn('font-semibold', workCenter.efficiency >= 90 ? 'text-green-600' : 'text-red-600')}>
              {workCenter.efficiency}%
            </p>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">OEE</span>
            <p className={cn('font-semibold', workCenter.oee >= 80 ? 'text-green-600' : 'text-yellow-600')}>
              {workCenter.oee}%
            </p>
          </div>
        </div>

        {/* Current Job */}
        {workCenter.currentJob && (
          <div className="mt-2 rounded-md bg-gray-50 px-2 py-1 text-xs dark:bg-gray-800">
            <span className="text-gray-500 dark:text-gray-400">Job: </span>
            <span className="font-medium text-gray-700 dark:text-gray-300">{workCenter.currentJob}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Filter Bar
// ============================================================================

export interface AndonFilterBarProps {
  currentType: AndonType | 'all';
  currentSeverity: Severity | 'all';
  onTypeChange: (type: AndonType | 'all') => void;
  onSeverityChange: (severity: Severity | 'all') => void;
}

export function AndonFilterBar({
  currentType,
  currentSeverity,
  onTypeChange,
  onSeverityChange,
}: AndonFilterBarProps) {
  const types: (AndonType | 'all')[] = ['all', 'quality', 'safety', 'material', 'equipment', 'assistance'];
  const severities: (Severity | 'all')[] = ['all', 'critical', 'major', 'minor'];

  return (
    <div className="flex flex-wrap items-center gap-4 border-b border-gray-200 bg-white px-6 py-3 dark:border-gray-700 dark:bg-gray-900">
      {/* Type filter */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Type:</span>
        <div className="flex gap-1">
          {types.map((type) => (
            <button
              key={type}
              onClick={() => onTypeChange(type)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                currentType === type
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
              )}
            >
              {type === 'all' ? 'All' : getAndonTypeLabel(type)}
            </button>
          ))}
        </div>
      </div>

      {/* Severity filter */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Severity:</span>
        <div className="flex gap-1">
          {severities.map((severity) => (
            <button
              key={severity}
              onClick={() => onSeverityChange(severity)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                currentSeverity === severity
                  ? 'text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
              )}
              style={
                currentSeverity === severity
                  ? { backgroundColor: severity === 'all' ? '#3B82F6' : getSeverityColor(severity) }
                  : undefined
              }
            >
              {severity === 'all' ? 'All' : getSeverityLabel(severity)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Dashboard Component
// ============================================================================

export interface AndonDashboardProps {
  className?: string;
  onEventClick?: (event: AndonEvent) => void;
  onRefresh?: () => void;
}

export function AndonDashboard({
  className,
  onEventClick,
  onRefresh,
}: AndonDashboardProps) {
  const {
    activeEvents,
    acknowledgedEvents,
    workCenters,
    config,
    filterType,
    filterSeverity,
    selectedEventId,
    setFilterType,
    setFilterSeverity,
    selectEvent,
    acknowledgeEvent,
    escalateEvent,
    resolveEvent,
    getFilteredEvents,
  } = useAndonStore();

  const filteredEvents = getFilteredEvents();
  const workCenterList = Array.from(workCenters.values());

  return (
    <div className={cn('flex h-full flex-col bg-gray-100 dark:bg-gray-950', className)}>
      <AndonDashboardHeader onRefresh={onRefresh} />
      <AndonMetricsBar />
      <AndonFilterBar
        currentType={filterType}
        currentSeverity={filterSeverity}
        onTypeChange={setFilterType}
        onSeverityChange={setFilterSeverity}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Events panel */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Active Alerts ({filteredEvents.length})
            </h2>
          </div>
          <AndonEventList
            events={filteredEvents}
            onEventClick={(event) => {
              selectEvent(event.id);
              onEventClick?.(event);
            }}
            onAcknowledge={(eventId) => acknowledgeEvent(eventId, 'Current User')}
            onEscalate={(eventId) => escalateEvent(eventId)}
            onResolve={(eventId) => resolveEvent(eventId, 'Issue resolved')}
            selectedEventId={selectedEventId}
          />
        </div>

        {/* Work centers panel */}
        <div className="w-96 border-l border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-900">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
            Work Centers
          </h2>
          <div className="space-y-4">
            {workCenterList.map((workCenter) => (
              <WorkCenterStatusCard
                key={workCenter.id}
                workCenter={workCenter}
              />
            ))}
            {workCenterList.length === 0 && (
              <p className="text-center text-gray-500 dark:text-gray-400">
                No work centers configured
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
