'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LucideIcon, ChevronRight } from 'lucide-react';

/**
 * Sensei Modern 2.0 - Quick Action Item Component
 * 
 * Premium quick action items with:
 * - Icon in colored container
 * - Hover reveal pattern (arrow appears on hover)
 * - Staggered animation support
 */

export interface QuickActionItemProps {
  /** Icon component to display */
  icon: LucideIcon;
  /** Action label */
  label: string;
  /** Optional description */
  description?: string;
  /** Click handler */
  onClick?: () => void;
  /** Link href (alternative to onClick) */
  href?: string;
  /** Icon color variant */
  iconColor?: 'primary' | 'success' | 'warning' | 'danger' | 'info';
  /** Show badge/count */
  badge?: number | string;
  /** Disabled state */
  disabled?: boolean;
  /** Additional class names */
  className?: string;
}

const iconColorMap = {
  primary: 'bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground',
  success: 'bg-emerald-500/10 text-emerald-600 group-hover:bg-emerald-500 group-hover:text-white',
  warning: 'bg-amber-500/10 text-amber-600 group-hover:bg-amber-500 group-hover:text-white',
  danger: 'bg-red-500/10 text-red-600 group-hover:bg-red-500 group-hover:text-white',
  info: 'bg-blue-500/10 text-blue-600 group-hover:bg-blue-500 group-hover:text-white',
};

export function QuickActionItem({
  icon: Icon,
  label,
  description,
  onClick,
  href,
  iconColor = 'primary',
  badge,
  disabled = false,
  className,
}: QuickActionItemProps) {
  const Wrapper = href ? 'a' : 'button';
  const wrapperProps = href ? { href } : { onClick, type: 'button' as const };

  return (
    <Wrapper
      {...wrapperProps}
      disabled={disabled}
      className={cn(
        'quick-action-item',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      <div className="flex items-center gap-3">
        <div className={cn('quick-action-icon', iconColorMap[iconColor])}>
          <Icon className="h-4 w-4" />
        </div>
        <div className="text-left">
          <span className="text-sm font-medium text-foreground">{label}</span>
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {badge !== undefined && (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-primary/10 text-primary">
            {badge}
          </span>
        )}
        <ChevronRight className="h-4 w-4 text-muted-foreground hover-reveal" />
      </div>
    </Wrapper>
  );
}

/**
 * Quick Action List - Container with staggered animation
 */
export interface QuickActionListProps {
  /** Child quick action items */
  children: React.ReactNode;
  /** Additional class names */
  className?: string;
}

export function QuickActionList({ children, className }: QuickActionListProps) {
  return (
    <div className={cn('stagger-list space-y-2', className)}>
      {children}
    </div>
  );
}

export default QuickActionItem;
