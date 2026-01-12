'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { Button, ButtonProps } from './button';
import {
  FileText,
  Search,
  AlertCircle,
  Clock,
  CheckCircle,
  Package,
  Users,
  Building2,
  Wrench,
  ClipboardList,
  Factory,
  ShieldAlert,
  BookOpen,
  PenTool,
  LucideIcon,
} from 'lucide-react';

// ===== Types =====

export type EmptyStateVariant = 
  | 'default'
  | 'search'
  | 'error'
  | 'filtered'
  | 'success'
  | 'pending';

export interface EmptyStateAction {
  label: string;
  onClick?: () => void;
  href?: string;
  variant?: ButtonProps['variant'];
  icon?: React.ReactNode;
}

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Title text */
  title?: string;
  /** Description text */
  description?: string;
  /** Icon to display */
  icon?: React.ReactNode;
  /** Visual variant */
  variant?: EmptyStateVariant;
  /** Primary action button */
  primaryAction?: EmptyStateAction;
  /** Secondary action button */
  secondaryAction?: EmptyStateAction;
  /** Additional actions */
  actions?: EmptyStateAction[];
  /** Educational tooltip/hint text */
  hint?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to show in a bordered container */
  bordered?: boolean;
  /** Whether to center the content */
  centered?: boolean;
}

// ===== Helper Functions =====

const getVariantIcon = (variant: EmptyStateVariant): React.ReactNode => {
  switch (variant) {
    case 'search':
      return <Search className="h-12 w-12" />;
    case 'error':
      return <AlertCircle className="h-12 w-12" />;
    case 'filtered':
      return <Search className="h-12 w-12" />;
    case 'success':
      return <CheckCircle className="h-12 w-12" />;
    case 'pending':
      return <Clock className="h-12 w-12" />;
    default:
      return <FileText className="h-12 w-12" />;
  }
};

const getVariantStyles = (variant: EmptyStateVariant): string => {
  switch (variant) {
    case 'error':
      return 'text-destructive';
    case 'success':
      return 'text-green-500';
    case 'pending':
      return 'text-yellow-500';
    default:
      return 'text-muted-foreground';
  }
};

const getSizeStyles = (size: 'sm' | 'md' | 'lg') => {
  switch (size) {
    case 'sm':
      return {
        container: 'py-6 px-4',
        icon: 'h-8 w-8',
        title: 'text-sm font-medium',
        description: 'text-xs',
        gap: 'gap-2',
      };
    case 'lg':
      return {
        container: 'py-16 px-8',
        icon: 'h-16 w-16',
        title: 'text-2xl font-semibold',
        description: 'text-base',
        gap: 'gap-6',
      };
    default:
      return {
        container: 'py-12 px-6',
        icon: 'h-12 w-12',
        title: 'text-lg font-medium',
        description: 'text-sm',
        gap: 'gap-4',
      };
  }
};

// ===== Main Component =====

export const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  (
    {
      title = 'No items found',
      description,
      icon,
      variant = 'default',
      primaryAction,
      secondaryAction,
      actions = [],
      hint,
      size = 'md',
      bordered = true,
      centered = true,
      className,
      ...props
    },
    ref
  ) => {
    const sizeStyles = getSizeStyles(size);
    const variantStyles = getVariantStyles(variant);
    const displayIcon = icon || getVariantIcon(variant);

    const renderAction = (action: EmptyStateAction, index: number, isPrimary = false) => {
      if (action.href) {
        return (
          <Button
            key={index}
            variant={action.variant || (isPrimary ? 'default' : 'outline')}
            asChild
          >
            <a href={action.href}>
              {action.icon}
              {action.label}
            </a>
          </Button>
        );
      }

      return (
        <Button
          key={index}
          variant={action.variant || (isPrimary ? 'default' : 'outline')}
          onClick={action.onClick}
        >
          {action.icon}
          {action.label}
        </Button>
      );
    };

    return (
      <div
        ref={ref}
        role="status"
        aria-label={title}
        className={cn(
          'flex flex-col items-center justify-center',
          sizeStyles.container,
          sizeStyles.gap,
          bordered && 'rounded-lg border border-dashed border-border bg-muted/30',
          centered && 'text-center',
          className
        )}
        {...props}
      >
        {/* Icon */}
        <div className={cn('transition-transform', variantStyles)}>
          {React.isValidElement(displayIcon)
            ? React.cloneElement(displayIcon as React.ReactElement, {
                className: cn(
                  (displayIcon as React.ReactElement).props.className,
                  sizeStyles.icon
                ),
              })
            : displayIcon}
        </div>

        {/* Text Content */}
        <div className="space-y-1">
          <h3 className={cn(sizeStyles.title, 'text-foreground')}>{title}</h3>
          {description && (
            <p className={cn(sizeStyles.description, 'text-muted-foreground max-w-md')}>
              {description}
            </p>
          )}
        </div>

        {/* Actions */}
        {(primaryAction || secondaryAction || actions.length > 0) && (
          <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
            {primaryAction && renderAction(primaryAction, -1, true)}
            {secondaryAction && renderAction(secondaryAction, -2)}
            {actions.map((action, i) => renderAction(action, i))}
          </div>
        )}

        {/* Hint/Tooltip */}
        {hint && (
          <p className="text-xs text-muted-foreground/70 italic max-w-sm mt-2">{hint}</p>
        )}
      </div>
    );
  }
);

EmptyState.displayName = 'EmptyState';

// ===== Entity-Specific Empty States =====

interface EntityEmptyStateProps extends Omit<EmptyStateProps, 'icon' | 'title' | 'description'> {
  title?: string;
  description?: string;
  onCreateClick?: () => void;
  createHref?: string;
}

// RFQ Empty State
export const RFQEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No RFQs found',
  description = "You haven't received any requests for quote yet. RFQs will appear here when customers submit inquiries.",
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<FileText className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Create First RFQ',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="RFQs track customer inquiries from initial request through quoting."
    {...props}
  />
);

// Quote Empty State
export const QuoteEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No quotes found',
  description = 'Start by converting an RFQ to a quote or creating a new quote directly.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<ClipboardList className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Create Quote',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Quotes define pricing and terms for customer orders."
    {...props}
  />
);

// Work Order Empty State
export const WorkOrderEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No work orders found',
  description = 'Work orders are created from approved quotes to track production.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<Factory className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Create Work Order',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Work orders track manufacturing progress from start to completion."
    {...props}
  />
);

// Account Empty State
export const AccountEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No accounts found',
  description = 'Add your first customer or vendor account to get started.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<Building2 className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Add Account',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Accounts represent companies you do business with."
    {...props}
  />
);

// Product Empty State
export const ProductEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No products found',
  description = 'Add products to your catalog to include them in quotes and work orders.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<Package className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Add Product',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Products define what you manufacture and sell."
    {...props}
  />
);

// Contact Empty State
export const ContactEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No contacts found',
  description = 'Add contacts to link them with accounts and track communications.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<Users className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Add Contact',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Contacts are people at customer and vendor organizations."
    {...props}
  />
);

// Andon Empty State
export const AndonEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No andon events',
  description = 'No production issues have been reported. Great job keeping things running smoothly!',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<ShieldAlert className="h-12 w-12" />}
    title={title}
    description={description}
    variant="success"
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Report Issue',
        onClick: onCreateClick,
        href: createHref,
        variant: 'outline',
      } : undefined
    }
    hint="Andon events help track and resolve production issues quickly."
    {...props}
  />
);

// A3 Empty State
export const A3EmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No A3 reports found',
  description = 'A3 reports help solve problems systematically. Create one to document an improvement initiative.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<PenTool className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Create A3 Report',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="A3 is a structured problem-solving methodology."
    {...props}
  />
);

// Training Empty State
export const TrainingEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No training records found',
  description = 'Track employee training and certifications to ensure team readiness.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<BookOpen className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Add Training Record',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Training records ensure compliance and track skill development."
    {...props}
  />
);

// Work Center Empty State
export const WorkCenterEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No work centers found',
  description = 'Define work centers to organize your production floor.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<Wrench className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Add Work Center',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Work centers represent areas where production activities occur."
    {...props}
  />
);

// Search Results Empty State
export const SearchEmptyState: React.FC<
  Omit<EmptyStateProps, 'variant'> & { searchQuery?: string }
> = ({ searchQuery, title, description, ...props }) => (
  <EmptyState
    variant="search"
    title={title || `No results for "${searchQuery || 'your search'}"`}
    description={description || 'Try adjusting your search terms or filters.'}
    hint="Tip: Use broader search terms or remove filters to find more results."
    {...props}
  />
);

// Filter Empty State
export const FilterEmptyState: React.FC<
  Omit<EmptyStateProps, 'variant'> & { onClearFilters?: () => void }
> = ({ onClearFilters, title, description, ...props }) => (
  <EmptyState
    variant="filtered"
    title={title || 'No matches with current filters'}
    description={description || 'Adjust or clear your filters to see more results.'}
    primaryAction={
      onClearFilters ? { label: 'Clear Filters', onClick: onClearFilters, variant: 'outline' } : undefined
    }
    hint="Your current filter combination has no matching items."
    {...props}
  />
);

// Error Empty State
export const ErrorEmptyState: React.FC<
  Omit<EmptyStateProps, 'variant'> & { onRetry?: () => void }
> = ({ onRetry, title, description, ...props }) => (
  <EmptyState
    variant="error"
    title={title || 'Something went wrong'}
    description={description || 'We encountered an error loading this content. Please try again.'}
    primaryAction={
      onRetry ? { label: 'Retry', onClick: onRetry } : undefined
    }
    {...props}
  />
);

// 404 Empty State
export const NotFoundEmptyState: React.FC<
  EntityEmptyStateProps & { backHref?: string; onBackClick?: () => void }
> = ({ backHref, onBackClick, title, description, ...props }) => (
  <EmptyState
    variant="error"
    icon={<Search className="h-12 w-12" />}
    title={title || 'Page not found'}
    description={description || "The page you're looking for doesn't exist or has been moved."}
    primaryAction={
      (backHref || onBackClick) ? { label: 'Go Back', href: backHref, onClick: onBackClick } : undefined
    }
    secondaryAction={{ label: 'Go Home', href: '/' }}
    {...props}
  />
);

// Task Empty State
export const TaskEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No tasks found',
  description = 'You\'re all caught up! Tasks assigned to you will appear here.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<ClipboardList className="h-12 w-12" />}
    title={title}
    description={description}
    variant="success"
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Create Task',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Tasks help you track work items and deadlines."
    {...props}
  />
);

// Exception Empty State  
export const ExceptionEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No exceptions reported',
  description = 'No quality or process exceptions at this time. Keep up the good work!',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<AlertCircle className="h-12 w-12" />}
    title={title}
    description={description}
    variant="success"
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Report Exception',
        onClick: onCreateClick,
        href: createHref,
        variant: 'outline',
      } : undefined
    }
    hint="Exceptions track quality issues and process deviations for resolution."
    {...props}
  />
);

// Obeya Empty State
export const ObeyaEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No obeya rooms configured',
  description = 'Set up an obeya room to visualize key metrics and drive team alignment.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<Building2 className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Create Obeya Room',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Obeya (big room) is a visual management space for project alignment."
    {...props}
  />
);

// Project Empty State
export const ProjectEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No projects found',
  description = 'Create a project to organize and track related work items.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<FileText className="h-12 w-12" />}
    title={title}
    description={description}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Create Project',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Projects group related tasks and deliverables together."
    {...props}
  />
);

// Maintenance Empty State
export const MaintenanceEmptyState: React.FC<EntityEmptyStateProps> = ({
  title = 'No maintenance tasks scheduled',
  description = 'Schedule preventive maintenance to keep equipment running smoothly.',
  onCreateClick,
  createHref,
  ...props
}) => (
  <EmptyState
    icon={<Wrench className="h-12 w-12" />}
    title={title}
    description={description}
    variant="success"
    primaryAction={
      (onCreateClick || createHref) ? {
        label: 'Schedule Maintenance',
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint="Regular maintenance prevents unexpected downtime."
    {...props}
  />
);

export default EmptyState;
