'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus, LucideIcon } from 'lucide-react';

/**
 * Sensei Modern 2.0 - Stat Card Component
 * 
 * A premium stat card following the authoritative Sensei Modern design pattern:
 * - Icon in colored container on the RIGHT
 * - Glass-morphism with subtle gradients
 * - Goal progress bar support (Goal-Gradient Effect)
 * - Spotlight variant (Von Restorff Effect)
 * - Critical alert state for emergencies
 */

export interface StatCardProps {
  /** The main value to display */
  value: string | number;
  /** Label describing the metric */
  label: string;
  /** Icon component to display */
  icon: LucideIcon;
  /** Color variant for the icon container */
  iconColor?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'muted';
  /** Trend direction */
  trend?: 'up' | 'down' | 'neutral';
  /** Trend value (e.g., "+12%") */
  trendValue?: string;
  /** Optional goal for progress bar */
  goal?: {
    current: number;
    target: number;
    label?: string;
  };
  /** Make this card stand out (Von Restorff Effect) */
  spotlight?: boolean;
  /** Critical alert state */
  critical?: boolean;
  /** Additional class names */
  className?: string;
  /** Click handler */
  onClick?: () => void;
}

const iconColorMap = {
  primary: 'bg-primary/10 text-primary',
  success: 'bg-emerald-500/10 text-emerald-600',
  warning: 'bg-amber-500/10 text-amber-600',
  danger: 'bg-red-500/10 text-red-600',
  info: 'bg-blue-500/10 text-blue-600',
  muted: 'bg-muted text-muted-foreground',
};

const trendColorMap = {
  up: 'text-emerald-600',
  down: 'text-red-600',
  neutral: 'text-muted-foreground',
};

const TrendIcon = {
  up: TrendingUp,
  down: TrendingDown,
  neutral: Minus,
};

export function StatCard({
  value,
  label,
  icon: Icon,
  iconColor = 'primary',
  trend,
  trendValue,
  goal,
  spotlight = false,
  critical = false,
  className,
  onClick,
}: StatCardProps) {
  const TrendIconComponent = trend ? TrendIcon[trend] : null;
  const goalPercentage = goal ? Math.min((goal.current / goal.target) * 100, 100) : 0;

  return (
    <div
      className={cn(
        'stat-card',
        spotlight && 'stat-card-spotlight',
        critical && 'stat-card-critical',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
    >
      <div className="flex items-start justify-between">
        {/* Left: Value and Label */}
        <div className="space-y-1">
          <p className={cn(
            'stat-card-value',
            spotlight && 'text-gradient-primary',
            critical && 'text-gradient-danger'
          )}>
            {value}
          </p>
          <p className="stat-card-label">{label}</p>
          
          {/* Trend indicator */}
          {trend && trendValue && (
            <div className={cn('stat-card-trend', trendColorMap[trend])}>
              {TrendIconComponent && <TrendIconComponent className="h-3 w-3" />}
              <span>{trendValue}</span>
            </div>
          )}
        </div>

        {/* Right: Icon Container */}
        <div className={cn('stat-card-icon', iconColorMap[iconColor])}>
          <Icon className="h-5 w-5" />
        </div>
      </div>

      {/* Goal Progress Bar (Goal-Gradient Effect) */}
      {goal && (
        <div className="mt-4 space-y-1.5">
          <div className="goal-progress-track">
            <div
              className="goal-progress-fill"
              style={{ width: `${goalPercentage}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span>{goal.label || `${goal.current} / ${goal.target}`}</span>
            <span>{Math.round(goalPercentage)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Stat Card Section - Groups related stats with a label (Miller's Law)
 */
export interface StatSectionProps {
  /** Section label */
  label: string;
  /** Child stat cards */
  children: React.ReactNode;
  /** Number of columns (default: 3) */
  columns?: 2 | 3 | 4;
  /** Additional class names */
  className?: string;
}

const columnMap = {
  2: 'grid-cols-1 sm:grid-cols-2',
  3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
};

export function StatSection({
  label,
  children,
  columns = 3,
  className,
}: StatSectionProps) {
  return (
    <section className={className}>
      <h3 className="stat-section-label">{label}</h3>
      <div className={cn('grid gap-4', columnMap[columns])}>
        {children}
      </div>
    </section>
  );
}

/**
 * Ambient Status Indicator
 */
export interface AmbientStatusProps {
  /** Status state */
  status: 'operational' | 'warning' | 'critical' | 'offline';
  /** Optional custom label */
  label?: string;
  /** Additional class names */
  className?: string;
}

const statusConfig = {
  operational: {
    color: 'bg-emerald-400',
    pingColor: 'bg-emerald-400',
    label: 'All Systems Operational',
  },
  warning: {
    color: 'bg-amber-400',
    pingColor: 'bg-amber-400',
    label: 'Minor Issues Detected',
  },
  critical: {
    color: 'bg-red-500',
    pingColor: 'bg-red-500',
    label: 'Critical Alert',
  },
  offline: {
    color: 'bg-gray-400',
    pingColor: 'bg-gray-400',
    label: 'System Offline',
  },
};

export function AmbientStatus({
  status,
  label,
  className,
}: AmbientStatusProps) {
  const config = statusConfig[status];
  const showPing = status !== 'offline';

  return (
    <div className={cn('ambient-status', className)}>
      <span className="ambient-status-dot">
        {showPing && (
          <span className={cn('ambient-status-dot-ping', config.pingColor)} />
        )}
        <span className={cn('ambient-status-dot-solid', config.color)} />
      </span>
      <span className="ambient-status-label">{label || config.label}</span>
    </div>
  );
}

/**
 * Confidence Indicator for AI/ML predictions
 */
export interface ConfidenceIndicatorProps {
  /** Confidence percentage (0-100) */
  confidence: number;
  /** Additional class names */
  className?: string;
}

export function ConfidenceIndicator({
  confidence,
  className,
}: ConfidenceIndicatorProps) {
  return (
    <div className={cn('confidence-indicator', className)}>
      <div className="confidence-bar">
        <div
          className="confidence-fill"
          style={{ width: `${Math.min(confidence, 100)}%` }}
        />
      </div>
      <span className="confidence-label">{Math.round(confidence)}%</span>
    </div>
  );
}

export default StatCard;
