'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';
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
      title,
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
    const { t } = useI18n();
    const resolvedTitle = title ?? t('components.emptyState.defaultTitle');
    const sizeStyles = getSizeStyles(size);
    const variantStyles = getVariantStyles(variant);
    const displayIcon = icon || getVariantIcon(variant);

    const renderAction = (action: EmptyStateAction, isPrimary = false) => {
      if (action.href) {
        return (
          <Button
            key={action.label}
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
          key={action.label}
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
        aria-label={resolvedTitle}
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
          <h3 className={cn(sizeStyles.title, 'text-foreground')}>{resolvedTitle}</h3>
          {description && (
            <p className={cn(sizeStyles.description, 'text-muted-foreground max-w-md')}>
              {description}
            </p>
          )}
        </div>

        {/* Actions */}
        {(primaryAction || secondaryAction || actions.length > 0) && (
          <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
            {primaryAction && renderAction(primaryAction, true)}
            {secondaryAction && renderAction(secondaryAction)}
            {actions.map((action) => renderAction(action))}
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
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<FileText className="h-12 w-12" />}
    title={title ?? t('components.emptyState.rfq.title')}
    description={description ?? t('components.emptyState.rfq.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.rfq.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.rfq.hint')}
    {...props}
  />
  );
};

// Quote Empty State
export const QuoteEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<ClipboardList className="h-12 w-12" />}
    title={title ?? t('components.emptyState.quote.title')}
    description={description ?? t('components.emptyState.quote.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.quote.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.quote.hint')}
    {...props}
  />
  );
};

// Work Order Empty State
export const WorkOrderEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<Factory className="h-12 w-12" />}
    title={title ?? t('components.emptyState.workOrder.title')}
    description={description ?? t('components.emptyState.workOrder.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.workOrder.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.workOrder.hint')}
    {...props}
  />
  );
};

// Account Empty State
export const AccountEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<Building2 className="h-12 w-12" />}
    title={title ?? t('components.emptyState.account.title')}
    description={description ?? t('components.emptyState.account.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.account.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.account.hint')}
    {...props}
  />
  );
};

// Product Empty State
export const ProductEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<Package className="h-12 w-12" />}
    title={title ?? t('components.emptyState.product.title')}
    description={description ?? t('components.emptyState.product.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.product.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.product.hint')}
    {...props}
  />
  );
};

// Contact Empty State
export const ContactEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<Users className="h-12 w-12" />}
    title={title ?? t('components.emptyState.contact.title')}
    description={description ?? t('components.emptyState.contact.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.contact.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.contact.hint')}
    {...props}
  />
  );
};

// Andon Empty State
export const AndonEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<ShieldAlert className="h-12 w-12" />}
    title={title ?? t('components.emptyState.andon.title')}
    description={description ?? t('components.emptyState.andon.description')}
    variant="success"
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.andon.action'),
        onClick: onCreateClick,
        href: createHref,
        variant: 'outline',
      } : undefined
    }
    hint={t('components.emptyState.andon.hint')}
    {...props}
  />
  );
};

// A3 Empty State
export const A3EmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<PenTool className="h-12 w-12" />}
    title={title ?? t('components.emptyState.a3.title')}
    description={description ?? t('components.emptyState.a3.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.a3.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.a3.hint')}
    {...props}
  />
  );
};

// Training Empty State
export const TrainingEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<BookOpen className="h-12 w-12" />}
    title={title ?? t('components.emptyState.training.title')}
    description={description ?? t('components.emptyState.training.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.training.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.training.hint')}
    {...props}
  />
  );
};

// Work Center Empty State
export const WorkCenterEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<Wrench className="h-12 w-12" />}
    title={title ?? t('components.emptyState.workCenter.title')}
    description={description ?? t('components.emptyState.workCenter.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.workCenter.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.workCenter.hint')}
    {...props}
  />
  );
};

// Search Results Empty State
export const SearchEmptyState: React.FC<
  Omit<EmptyStateProps, 'variant'> & { searchQuery?: string }
> = ({ searchQuery, title, description, ...props }) => {
  const { t } = useI18n();
  return (
  <EmptyState
    variant="search"
    title={title || `${t('components.emptyState.search.noResultsFor')} "${searchQuery || t('components.emptyState.search.yourSearch')}"`}
    description={description || t('components.emptyState.search.adjustSearch')}
    hint={t('components.emptyState.search.hint')}
    {...props}
  />
  );
};

// Filter Empty State
export const FilterEmptyState: React.FC<
  Omit<EmptyStateProps, 'variant'> & { onClearFilters?: () => void }
> = ({ onClearFilters, title, description, ...props }) => {
  const { t } = useI18n();
  return (
  <EmptyState
    variant="filtered"
    title={title || t('components.emptyState.filter.title')}
    description={description || t('components.emptyState.filter.description')}
    primaryAction={
      onClearFilters ? { label: t('components.emptyState.filter.action'), onClick: onClearFilters, variant: 'outline' } : undefined
    }
    hint={t('components.emptyState.filter.hint')}
    {...props}
  />
  );
};

// Error Empty State
export const ErrorEmptyState: React.FC<
  Omit<EmptyStateProps, 'variant'> & { onRetry?: () => void }
> = ({ onRetry, title, description, ...props }) => {
  const { t } = useI18n();
  return (
  <EmptyState
    variant="error"
    title={title || t('components.emptyState.error.title')}
    description={description || t('components.emptyState.error.description')}
    primaryAction={
      onRetry ? { label: t('components.emptyState.error.action'), onClick: onRetry } : undefined
    }
    {...props}
  />
  );
};

// 404 Empty State
export const NotFoundEmptyState: React.FC<
  EntityEmptyStateProps & { backHref?: string; onBackClick?: () => void }
> = ({ backHref, onBackClick, title, description, ...props }) => {
  const { t } = useI18n();
  return (
  <EmptyState
    variant="error"
    icon={<Search className="h-12 w-12" />}
    title={title || t('components.emptyState.notFound.title')}
    description={description || t('components.emptyState.notFound.description')}
    primaryAction={
      (backHref || onBackClick) ? { label: t('components.emptyState.notFound.goBack'), href: backHref, onClick: onBackClick } : undefined
    }
    secondaryAction={{ label: t('components.emptyState.notFound.goHome'), href: '/' }}
    {...props}
  />
  );
};

// Task Empty State
export const TaskEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<ClipboardList className="h-12 w-12" />}
    title={title ?? t('components.emptyState.task.title')}
    description={description ?? t('components.emptyState.task.description')}
    variant="success"
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.task.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.task.hint')}
    {...props}
  />
  );
};

// Exception Empty State  
export const ExceptionEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<AlertCircle className="h-12 w-12" />}
    title={title ?? t('components.emptyState.exception.title')}
    description={description ?? t('components.emptyState.exception.description')}
    variant="success"
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.exception.action'),
        onClick: onCreateClick,
        href: createHref,
        variant: 'outline',
      } : undefined
    }
    hint={t('components.emptyState.exception.hint')}
    {...props}
  />
  );
};

// Obeya Empty State
export const ObeyaEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<Building2 className="h-12 w-12" />}
    title={title ?? t('components.emptyState.obeya.title')}
    description={description ?? t('components.emptyState.obeya.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.obeya.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.obeya.hint')}
    {...props}
  />
  );
};

// Project Empty State
export const ProjectEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<FileText className="h-12 w-12" />}
    title={title ?? t('components.emptyState.project.title')}
    description={description ?? t('components.emptyState.project.description')}
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.project.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.project.hint')}
    {...props}
  />
  );
};

// Maintenance Empty State
export const MaintenanceEmptyState: React.FC<EntityEmptyStateProps> = ({
  title,
  description,
  onCreateClick,
  createHref,
  ...props
}) => {
  const { t } = useI18n();
  return (
  <EmptyState
    icon={<Wrench className="h-12 w-12" />}
    title={title ?? t('components.emptyState.maintenance.title')}
    description={description ?? t('components.emptyState.maintenance.description')}
    variant="success"
    primaryAction={
      (onCreateClick || createHref) ? {
        label: t('components.emptyState.maintenance.action'),
        onClick: onCreateClick,
        href: createHref,
      } : undefined
    }
    hint={t('components.emptyState.maintenance.hint')}
    {...props}
  />
  );
};

export default EmptyState;
