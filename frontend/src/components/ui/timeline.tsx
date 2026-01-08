import * as React from 'react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/utils';

/**
 * Premium Timeline Component
 * 
 * Features:
 * - Audit trail visualization
 * - Approval workflow timeline
 * - Activity feed display
 * - Flexible item types (events, milestones, actions)
 * - Responsive design
 * - Icon support
 * - Timestamps with relative time
 * - Collapsible details
 * - Empty states
 */

// =============================================================================
// Timeline Types
// =============================================================================

export interface TimelineItemData {
  id: string;
  timestamp: Date | string;
  title: string;
  description?: string;
  user?: {
    name: string;
    avatar?: string;
  };
  type?: 'event' | 'milestone' | 'action' | 'approval' | 'rejection';
  icon?: React.ReactNode;
  metadata?: Record<string, any>;
  details?: React.ReactNode;
}

// =============================================================================
// Base Timeline Components
// =============================================================================

interface TimelineProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'default' | 'compact' | 'detailed';
}

const Timeline = React.forwardRef<HTMLDivElement, TimelineProps>(
  ({ className, children, variant = 'default', ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'relative space-y-4',
        {
          default: 'space-y-6',
          compact: 'space-y-3',
          detailed: 'space-y-8',
        }[variant],
        className
      )}
      role="list"
      {...props}
    >
      {children}
    </div>
  )
);
Timeline.displayName = 'Timeline';

interface TimelineItemProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  active?: boolean;
  last?: boolean;
}

const TimelineItem = React.forwardRef<HTMLDivElement, TimelineItemProps>(
  ({ className, children, active = false, last = false, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('relative flex gap-4 pb-8', last && 'pb-0', className)}
      role="listitem"
      {...props}
    >
      {/* Timeline line */}
      {!last && (
        <div
          className={cn(
            'absolute left-4 top-10 h-full w-0.5 -translate-x-1/2',
            active ? 'bg-primary' : 'bg-border'
          )}
        />
      )}
      {children}
    </div>
  )
);
TimelineItem.displayName = 'TimelineItem';

interface TimelineIconProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  active?: boolean;
}

const TimelineIcon = React.forwardRef<HTMLDivElement, TimelineIconProps>(
  ({ className, children, variant = 'default', active = false, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2',
        {
          default: active
            ? 'border-primary bg-primary text-primary-foreground'
            : 'border-muted-foreground bg-background text-muted-foreground',
          success: 'border-green-500 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
          warning: 'border-yellow-500 bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
          danger: 'border-red-500 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
          info: 'border-blue-500 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
        }[variant],
        className
      )}
      {...props}
    >
      {children || (
        <div className={cn('h-3 w-3 rounded-full', active ? 'bg-current' : 'bg-muted-foreground')} />
      )}
    </div>
  )
);
TimelineIcon.displayName = 'TimelineIcon';

interface TimelineContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const TimelineContent = React.forwardRef<HTMLDivElement, TimelineContentProps>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn('flex-1 space-y-2', className)} {...props}>
      {children}
    </div>
  )
);
TimelineContent.displayName = 'TimelineContent';

interface TimelineHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const TimelineHeader = React.forwardRef<HTMLDivElement, TimelineHeaderProps>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-start justify-between gap-2', className)}
      {...props}
    >
      {children}
    </div>
  )
);
TimelineHeader.displayName = 'TimelineHeader';

interface TimelineTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
}

const TimelineTitle = React.forwardRef<HTMLHeadingElement, TimelineTitleProps>(
  ({ className, children, ...props }, ref) => (
    <h4
      ref={ref}
      className={cn('text-sm font-semibold leading-none', className)}
      {...props}
    >
      {children}
    </h4>
  )
);
TimelineTitle.displayName = 'TimelineTitle';

interface TimelineDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode;
}

const TimelineDescription = React.forwardRef<HTMLParagraphElement, TimelineDescriptionProps>(
  ({ className, children, ...props }, ref) => (
    <p
      ref={ref}
      className={cn('text-sm text-muted-foreground', className)}
      {...props}
    >
      {children}
    </p>
  )
);
TimelineDescription.displayName = 'TimelineDescription';

interface TimelineTimestampProps extends React.HTMLAttributes<HTMLSpanElement> {
  timestamp: Date | string;
  relative?: boolean;
}

const TimelineTimestamp = React.forwardRef<HTMLSpanElement, TimelineTimestampProps>(
  ({ className, timestamp, relative = true, ...props }, ref) => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    const displayText = relative
      ? formatRelativeTime(date)
      : date.toLocaleDateString(undefined, {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });

    return (
      <span
        ref={ref}
        className={cn('text-xs text-muted-foreground', className)}
        title={date.toLocaleString()}
        {...props}
      >
        {displayText}
      </span>
    );
  }
);
TimelineTimestamp.displayName = 'TimelineTimestamp';

interface TimelineDetailsProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
}

const TimelineDetails = React.forwardRef<HTMLDivElement, TimelineDetailsProps>(
  ({ className, children, collapsible = false, defaultOpen = false, ...props }, ref) => {
    const [isOpen, setIsOpen] = React.useState(defaultOpen);

    if (collapsible) {
      return (
        <div ref={ref} className={cn('mt-2', className)} {...props}>
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="text-xs text-primary hover:underline"
          >
            {isOpen ? 'Hide details' : 'Show details'}
          </button>
          {isOpen && (
            <div className="mt-2 rounded-md border bg-muted/30 p-3 text-sm">
              {children}
            </div>
          )}
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn('mt-2 rounded-md border bg-muted/30 p-3 text-sm', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);
TimelineDetails.displayName = 'TimelineDetails';

interface TimelineUserProps extends React.HTMLAttributes<HTMLDivElement> {
  name: string;
  avatar?: string;
}

const TimelineUser = React.forwardRef<HTMLDivElement, TimelineUserProps>(
  ({ className, name, avatar, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center gap-2', className)} {...props}>
      {avatar ? (
        <img
          src={avatar}
          alt={name}
          className="h-5 w-5 rounded-full border"
        />
      ) : (
        <div className="flex h-5 w-5 items-center justify-center rounded-full bg-muted text-[10px] font-medium">
          {name.charAt(0).toUpperCase()}
        </div>
      )}
      <span className="text-sm font-medium">{name}</span>
    </div>
  )
);
TimelineUser.displayName = 'TimelineUser';

// =============================================================================
// Enhanced Timeline Components
// =============================================================================

interface TimelineEmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

const TimelineEmptyState = React.forwardRef<HTMLDivElement, TimelineEmptyStateProps>(
  (
    {
      title = 'No activity yet',
      description = 'Activity will appear here as actions are taken',
      icon,
      action,
      className,
    },
    ref
  ) => (
    <div
      ref={ref}
      className={cn(
        'flex min-h-[300px] flex-col items-center justify-center gap-4 rounded-lg border border-dashed p-8 text-center',
        className
      )}
    >
      {icon && <div className="text-muted-foreground opacity-50">{icon}</div>}
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
);
TimelineEmptyState.displayName = 'TimelineEmptyState';

interface TimelineLoadingStateProps {
  items?: number;
  className?: string;
}

const TimelineLoadingState = React.forwardRef<HTMLDivElement, TimelineLoadingStateProps>(
  ({ items = 3, className }, ref) => (
    <div ref={ref} className={cn('space-y-6', className)}>
      {Array.from({ length: items }).map((_, index) => (
        <div key={index} className="flex gap-4">
          <div className="h-8 w-8 shrink-0 animate-pulse rounded-full bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-1/3 animate-pulse rounded bg-muted" />
            <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
            <div className="h-3 w-1/4 animate-pulse rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  )
);
TimelineLoadingState.displayName = 'TimelineLoadingState';

interface TimelineGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  children: React.ReactNode;
}

const TimelineGroup = React.forwardRef<HTMLDivElement, TimelineGroupProps>(
  ({ className, label, children, ...props }, ref) => (
    <div ref={ref} className={cn('space-y-4', className)} {...props}>
      <div className="sticky top-0 z-20 bg-background py-2">
        <h3 className="text-sm font-semibold text-muted-foreground">{label}</h3>
      </div>
      {children}
    </div>
  )
);
TimelineGroup.displayName = 'TimelineGroup';

// =============================================================================
// Convenience Component: TimelineItemCard
// =============================================================================

interface TimelineItemCardProps extends TimelineItemData {
  active?: boolean;
  last?: boolean;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  collapsibleDetails?: boolean;
}

const TimelineItemCard = React.forwardRef<HTMLDivElement, TimelineItemCardProps>(
  (
    {
      id,
      timestamp,
      title,
      description,
      user,
      type = 'event',
      icon,
      details,
      active = false,
      last = false,
      variant = 'default',
      collapsibleDetails = false,
    },
    ref
  ) => {
    // Determine icon variant based on type if not explicitly set
    const iconVariant = variant !== 'default' ? variant : type === 'approval' ? 'success' : type === 'rejection' ? 'danger' : 'default';

    return (
      <TimelineItem ref={ref} active={active} last={last}>
        <TimelineIcon variant={iconVariant} active={active}>
          {icon}
        </TimelineIcon>
        <TimelineContent>
          <TimelineHeader>
            <div className="flex-1">
              <TimelineTitle>{title}</TimelineTitle>
              {user && <TimelineUser name={user.name} avatar={user.avatar} className="mt-1" />}
            </div>
            <TimelineTimestamp timestamp={timestamp} />
          </TimelineHeader>
          {description && <TimelineDescription>{description}</TimelineDescription>}
          {details && (
            <TimelineDetails collapsible={collapsibleDetails}>
              {details}
            </TimelineDetails>
          )}
        </TimelineContent>
      </TimelineItem>
    );
  }
);
TimelineItemCard.displayName = 'TimelineItemCard';

// =============================================================================
// Exports
// =============================================================================

export {
  Timeline,
  TimelineItem,
  TimelineIcon,
  TimelineContent,
  TimelineHeader,
  TimelineTitle,
  TimelineDescription,
  TimelineTimestamp,
  TimelineDetails,
  TimelineUser,
  TimelineEmptyState,
  TimelineLoadingState,
  TimelineGroup,
  TimelineItemCard,
};
