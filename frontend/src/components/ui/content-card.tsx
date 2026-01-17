'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';

/**
 * Sensei Modern 2.0 - Content Card Component
 * 
 * Premium content card with:
 * - Glass-morphism effect
 * - Header with optional icon and action
 * - Consistent spacing and borders
 */

export interface ContentCardProps {
  /** Card title */
  title: string;
  /** Optional subtitle */
  subtitle?: string;
  /** Optional icon */
  icon?: LucideIcon;
  /** Optional header action (e.g., "View All" button) */
  action?: React.ReactNode;
  /** Card content */
  children: React.ReactNode;
  /** Remove padding from body */
  noPadding?: boolean;
  /** Additional class names */
  className?: string;
}

export function ContentCard({
  title,
  subtitle,
  icon: Icon,
  action,
  children,
  noPadding = false,
  className,
}: ContentCardProps) {
  return (
    <div className={cn('content-card', className)}>
      <div className="content-card-header">
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="section-header-icon">
              <Icon className="h-4 w-4" />
            </div>
          )}
          <div>
            <h3 className="content-card-title">{title}</h3>
            {subtitle && (
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60 mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
        {action}
      </div>
      <div className={cn(!noPadding && 'content-card-body')}>
        {children}
      </div>
    </div>
  );
}

/**
 * Bento Grid - Asymmetric dashboard layout
 */
export interface BentoGridProps {
  /** Child elements */
  children: React.ReactNode;
  /** Additional class names */
  className?: string;
}

export function BentoGrid({ children, className }: BentoGridProps) {
  return (
    <div className={cn('bento-grid', className)}>
      {children}
    </div>
  );
}

/**
 * Bento Grid Item - Individual cell with span options
 */
export interface BentoItemProps {
  /** Span configuration */
  span?: '1x1' | '2x1' | '1x2' | '2x2';
  /** Child content */
  children: React.ReactNode;
  /** Additional class names */
  className?: string;
}

const spanMap = {
  '1x1': '',
  '2x1': 'bento-span-2x1',
  '1x2': 'bento-span-1x2',
  '2x2': 'bento-span-2x2',
};

export function BentoItem({ span = '1x1', children, className }: BentoItemProps) {
  return (
    <div className={cn(spanMap[span], className)}>
      {children}
    </div>
  );
}

/**
 * Section Header - For organizing dashboard sections
 */
export interface SectionHeaderProps {
  /** Section title */
  title: string;
  /** Optional icon */
  icon?: LucideIcon;
  /** Optional description */
  description?: string;
  /** Optional action (e.g., button) */
  action?: React.ReactNode;
  /** Additional class names */
  className?: string;
}

export function SectionHeader({
  title,
  icon: Icon,
  description,
  action,
  className,
}: SectionHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between mb-6', className)}>
      <div className="flex items-center gap-3">
        {Icon && (
          <div className="section-header-icon">
            <Icon className="h-5 w-5" />
          </div>
        )}
        <div>
          <h2 className="section-header-title">{title}</h2>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
      {action}
    </div>
  );
}

export default ContentCard;
