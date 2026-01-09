/**
 * Motion, Feedback & Perceived Performance Components
 * 
 * Section 19.4: Motion, Feedback & Perceived Performance
 * 
 * Features:
 * - Micro-interactions (hover, active, loading states)
 * - Progress bars for long-running actions
 * - Animated success/error indicators
 * - Skeleton screens
 * - Optimistic UI utilities
 * - Haptic feedback integration
 */

'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { cn } from '@/lib/utils';

// =============================================================================
// CONSTANTS
// =============================================================================

/** Animation duration constants (in ms) */
export const ANIMATION_DURATION = {
  /** Instant feedback (50ms) - for micro-interactions */
  INSTANT: 50,
  /** Fast transitions (150ms) - for hover/active states */
  FAST: 150,
  /** Normal transitions (300ms) - for modals/drawers */
  NORMAL: 300,
  /** Slow transitions (500ms) - for complex animations */
  SLOW: 500,
  /** Page transitions (700ms) - for route changes */
  PAGE: 700,
} as const;

/** Easing function presets */
export const EASING = {
  /** Standard easing for most animations */
  STANDARD: 'cubic-bezier(0.4, 0, 0.2, 1)',
  /** Deceleration curve - entering screen */
  DECELERATE: 'cubic-bezier(0, 0, 0.2, 1)',
  /** Acceleration curve - leaving screen */
  ACCELERATE: 'cubic-bezier(0.4, 0, 1, 1)',
  /** Bounce effect for success states */
  BOUNCE: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  /** Spring effect for interactive elements */
  SPRING: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
} as const;

/** Haptic feedback patterns */
export const HAPTIC_PATTERN = {
  /** Light tap - for selections */
  LIGHT: 'light',
  /** Medium tap - for confirmations */
  MEDIUM: 'medium',
  /** Heavy tap - for important actions */
  HEAVY: 'heavy',
  /** Success pattern - for completed actions */
  SUCCESS: 'success',
  /** Warning pattern - for alerts */
  WARNING: 'warning',
  /** Error pattern - for failures */
  ERROR: 'error',
} as const;

export type HapticPattern = typeof HAPTIC_PATTERN[keyof typeof HAPTIC_PATTERN];

// =============================================================================
// SKELETON COMPONENTS
// =============================================================================

interface SkeletonBaseProps {
  className?: string;
  /** Skeleton width */
  width?: string | number;
  /** Skeleton height */
  height?: string | number;
  /** Enable shimmer animation */
  animate?: boolean;
  /** Border radius */
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'full';
}

interface SkeletonProps extends SkeletonBaseProps {
  /** When true, doesn't add role="status" (for use in compound skeletons) */
  asChild?: boolean;
}

/**
 * Internal skeleton element without ARIA role
 */
function SkeletonElement({
  className,
  width,
  height,
  animate = true,
  rounded = 'md',
}: SkeletonBaseProps) {
  const roundedClasses = {
    none: 'rounded-none',
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    full: 'rounded-full',
  };

  return (
    <div
      className={cn(
        'bg-muted relative overflow-hidden',
        roundedClasses[rounded],
        animate && 'animate-pulse',
        className
      )}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    >
      {animate && (
        <div
          className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent"
          aria-hidden="true"
        />
      )}
    </div>
  );
}

/**
 * Base skeleton component with shimmer animation
 */
export function Skeleton({
  className,
  width,
  height,
  animate = true,
  rounded = 'md',
  asChild = false,
}: SkeletonProps) {
  if (asChild) {
    return (
      <SkeletonElement
        className={className}
        width={width}
        height={height}
        animate={animate}
        rounded={rounded}
      />
    );
  }

  const roundedClasses = {
    none: 'rounded-none',
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    full: 'rounded-full',
  };

  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn(
        'bg-muted relative overflow-hidden',
        roundedClasses[rounded],
        animate && 'animate-pulse',
        className
      )}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    >
      {animate && (
        <div
          className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent"
          aria-hidden="true"
        />
      )}
    </div>
  );
}

/**
 * Skeleton for text content
 */
export function SkeletonText({
  lines = 1,
  className,
  lineClassName,
}: {
  lines?: number;
  className?: string;
  lineClassName?: string;
}) {
  return (
    <div className={cn('space-y-2', className)} role="status" aria-label="Loading text">
      {Array.from({ length: lines }).map((_, index) => (
        <SkeletonElement
          key={index}
          height={16}
          width={index === lines - 1 && lines > 1 ? '80%' : '100%'}
          className={lineClassName}
        />
      ))}
    </div>
  );
}

/**
 * Skeleton for card components
 */
export function SkeletonCard({
  className,
  hasImage = false,
  imageHeight = 150,
}: {
  className?: string;
  hasImage?: boolean;
  imageHeight?: number;
}) {
  return (
    <div
      className={cn('rounded-lg border p-4 space-y-4', className)}
      role="status"
      aria-label="Loading card"
    >
      {hasImage && (
        <SkeletonElement height={imageHeight} className="w-full" rounded="md" />
      )}
      <div className="space-y-2">
        <SkeletonElement height={20} width="60%" />
        <SkeletonElement height={16} width="100%" />
        <SkeletonElement height={16} width="80%" />
      </div>
    </div>
  );
}

/**
 * Skeleton for table rows
 */
export function SkeletonTableRow({
  columns = 4,
  className,
}: {
  columns?: number;
  className?: string;
}) {
  return (
    <tr className={cn('animate-pulse', className)} role="status" aria-label="Loading row">
      {Array.from({ length: columns }).map((_, index) => (
        <td key={index} className="px-4 py-3">
          <SkeletonElement height={16} width={index === 0 ? '70%' : '50%'} />
        </td>
      ))}
    </tr>
  );
}

/**
 * Skeleton for avatar
 */
export function SkeletonAvatar({
  size = 40,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <Skeleton
      width={size}
      height={size}
      rounded="full"
      className={className}
    />
  );
}

// =============================================================================
// PROGRESS COMPONENTS
// =============================================================================

interface ProgressBarProps {
  /** Progress value (0-100) */
  value: number;
  /** Maximum value */
  max?: number;
  /** Show percentage text */
  showLabel?: boolean;
  /** Custom label */
  label?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Color variant */
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  /** Enable animation */
  animate?: boolean;
  /** Indeterminate mode (no specific progress) */
  indeterminate?: boolean;
  className?: string;
}

/**
 * Animated progress bar with multiple variants
 */
export function ProgressBar({
  value,
  max = 100,
  showLabel = false,
  label,
  size = 'md',
  variant = 'default',
  animate = true,
  indeterminate = false,
  className,
}: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-4',
  };

  const variantClasses = {
    default: 'bg-primary',
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500',
    info: 'bg-blue-500',
  };

  return (
    <div className={cn('space-y-1', className)}>
      {(showLabel || label) && (
        <div className="flex justify-between text-sm">
          <span>{label || 'Progress'}</span>
          {!indeterminate && <span>{Math.round(percentage)}%</span>}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label || 'Progress'}
        className={cn(
          'relative overflow-hidden rounded-full bg-muted',
          sizeClasses[size]
        )}
      >
        <div
          className={cn(
            'h-full rounded-full',
            variantClasses[variant],
            animate && 'transition-all duration-300 ease-out',
            indeterminate && 'animate-[indeterminate_1.5s_ease-in-out_infinite]'
          )}
          style={{
            width: indeterminate ? '50%' : `${percentage}%`,
            ...(indeterminate && {
              position: 'absolute',
              left: 0,
            }),
          }}
        />
      </div>
    </div>
  );
}

interface StepProgressProps {
  /** Current step (0-indexed) */
  currentStep: number;
  /** Total number of steps */
  totalSteps: number;
  /** Step labels */
  labels?: string[];
  /** Completed step color */
  completedColor?: string;
  className?: string;
}

/**
 * Step progress indicator for multi-step workflows
 */
export function StepProgress({
  currentStep,
  totalSteps,
  labels,
  className,
}: StepProgressProps) {
  return (
    <div className={cn('flex items-center', className)} role="group" aria-label="Progress steps">
      {Array.from({ length: totalSteps }).map((_, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;
        
        return (
          <React.Fragment key={index}>
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-medium transition-all duration-300',
                  isCompleted && 'border-primary bg-primary text-primary-foreground',
                  isCurrent && 'border-primary bg-background text-primary',
                  !isCompleted && !isCurrent && 'border-muted bg-muted text-muted-foreground'
                )}
                aria-current={isCurrent ? 'step' : undefined}
                aria-label={labels?.[index] || `Step ${index + 1}`}
              >
                {isCompleted ? (
                  <span aria-hidden="true">✓</span>
                ) : (
                  index + 1
                )}
              </div>
              {labels?.[index] && (
                <span className="mt-1 text-xs text-muted-foreground">
                  {labels[index]}
                </span>
              )}
            </div>
            {index < totalSteps - 1 && (
              <div
                className={cn(
                  'mx-2 h-0.5 flex-1 transition-all duration-300',
                  index < currentStep ? 'bg-primary' : 'bg-muted'
                )}
                aria-hidden="true"
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// =============================================================================
// SUCCESS/ERROR INDICATORS
// =============================================================================

interface AnimatedCheckmarkProps {
  /** Size in pixels */
  size?: number;
  /** Animation delay in ms */
  delay?: number;
  /** Color */
  color?: string;
  className?: string;
}

/**
 * Animated checkmark for success states
 */
export function AnimatedCheckmark({
  size = 48,
  delay = 0,
  color = 'currentColor',
  className,
}: AnimatedCheckmarkProps) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShow(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div
      className={cn('relative', className)}
      style={{ width: size, height: size }}
      role="status"
      aria-label="Success"
    >
      <svg
        viewBox="0 0 52 52"
        className={cn(
          'stroke-current transition-all duration-500',
          show ? 'opacity-100 scale-100' : 'opacity-0 scale-75'
        )}
        style={{ color, transition: `all ${ANIMATION_DURATION.SLOW}ms ${EASING.BOUNCE}` }}
      >
        <circle
          cx="26"
          cy="26"
          r="24"
          fill="none"
          strokeWidth="2"
          strokeDasharray="150"
          strokeDashoffset={show ? 0 : 150}
          style={{ transition: `stroke-dashoffset ${ANIMATION_DURATION.SLOW}ms ${EASING.DECELERATE}` }}
        />
        <path
          fill="none"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M14 27l8 8 16-16"
          strokeDasharray="40"
          strokeDashoffset={show ? 0 : 40}
          style={{ 
            transition: `stroke-dashoffset ${ANIMATION_DURATION.NORMAL}ms ${EASING.STANDARD}`,
            transitionDelay: `${ANIMATION_DURATION.FAST}ms`,
          }}
        />
      </svg>
    </div>
  );
}

interface AnimatedCrossProps {
  /** Size in pixels */
  size?: number;
  /** Animation delay in ms */
  delay?: number;
  /** Color */
  color?: string;
  className?: string;
}

/**
 * Animated cross for error states
 */
export function AnimatedCross({
  size = 48,
  delay = 0,
  color = 'currentColor',
  className,
}: AnimatedCrossProps) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShow(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div
      className={cn('relative', className)}
      style={{ width: size, height: size }}
      role="status"
      aria-label="Error"
    >
      <svg
        viewBox="0 0 52 52"
        className={cn(
          'stroke-current transition-all duration-500',
          show ? 'opacity-100 scale-100' : 'opacity-0 scale-75'
        )}
        style={{ color, transition: `all ${ANIMATION_DURATION.SLOW}ms ${EASING.BOUNCE}` }}
      >
        <circle
          cx="26"
          cy="26"
          r="24"
          fill="none"
          strokeWidth="2"
          strokeDasharray="150"
          strokeDashoffset={show ? 0 : 150}
          style={{ transition: `stroke-dashoffset ${ANIMATION_DURATION.SLOW}ms ${EASING.DECELERATE}` }}
        />
        <path
          fill="none"
          strokeWidth="3"
          strokeLinecap="round"
          d="M18 18l16 16M34 18l-16 16"
          strokeDasharray="45"
          strokeDashoffset={show ? 0 : 45}
          style={{ 
            transition: `stroke-dashoffset ${ANIMATION_DURATION.NORMAL}ms ${EASING.STANDARD}`,
            transitionDelay: `${ANIMATION_DURATION.FAST}ms`,
          }}
        />
      </svg>
    </div>
  );
}

// =============================================================================
// LOADING SPINNER COMPONENTS
// =============================================================================

interface SpinnerProps {
  /** Size variant */
  size?: 'sm' | 'md' | 'lg' | 'xl';
  /** Color */
  color?: string;
  /** Label for screen readers */
  label?: string;
  className?: string;
}

/**
 * Animated loading spinner
 */
export function Spinner({
  size = 'md',
  color = 'currentColor',
  label = 'Loading',
  className,
}: SpinnerProps) {
  const sizeMap = {
    sm: 16,
    md: 24,
    lg: 32,
    xl: 48,
  };

  const pixelSize = sizeMap[size];

  return (
    <div
      role="status"
      aria-label={label}
      className={cn('animate-spin', className)}
      style={{ width: pixelSize, height: pixelSize }}
    >
      <svg viewBox="0 0 24 24" fill="none" className="w-full h-full">
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray="60"
          strokeDashoffset="45"
          opacity="0.25"
        />
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray="60"
          strokeDashoffset="45"
        />
      </svg>
      <span className="sr-only">{label}</span>
    </div>
  );
}

/**
 * Pulsing dots loading indicator
 */
export function PulsingDots({
  size = 'md',
  color = 'currentColor',
  label = 'Loading',
  className,
}: SpinnerProps) {
  const sizeMap = {
    sm: 4,
    md: 6,
    lg: 8,
    xl: 10,
  };

  const dotSize = sizeMap[size];

  return (
    <div
      role="status"
      aria-label={label}
      className={cn('flex items-center gap-1', className)}
    >
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className="animate-pulse rounded-full"
          style={{
            width: dotSize,
            height: dotSize,
            backgroundColor: color,
            animationDelay: `${index * 150}ms`,
          }}
        />
      ))}
      <span className="sr-only">{label}</span>
    </div>
  );
}

// =============================================================================
// MICRO-INTERACTION WRAPPERS
// =============================================================================

interface PressableProps {
  children: React.ReactNode;
  /** Scale on press */
  pressScale?: number;
  /** Enable haptic feedback */
  haptic?: boolean;
  /** Haptic pattern to use */
  hapticPattern?: HapticPattern;
  /** Disabled state */
  disabled?: boolean;
  className?: string;
  onClick?: (e: React.MouseEvent | React.KeyboardEvent) => void;
  onPress?: () => void;
}

/**
 * Wrapper for pressable elements with scale feedback
 */
export function Pressable({
  children,
  pressScale = 0.98,
  haptic = false,
  hapticPattern = 'light',
  disabled = false,
  className,
  onClick,
  onPress,
}: PressableProps) {
  const [isPressed, setIsPressed] = useState(false);

  const triggerHaptic = useCallback(() => {
    if (haptic && 'vibrate' in navigator) {
      const patterns: Record<HapticPattern, number | number[]> = {
        light: 10,
        medium: 25,
        heavy: 50,
        success: [10, 30, 10],
        warning: [25, 50, 25],
        error: [50, 25, 50],
      };
      navigator.vibrate(patterns[hapticPattern]);
    }
  }, [haptic, hapticPattern]);

  const handlePress = useCallback((e: React.MouseEvent | React.KeyboardEvent) => {
    if (disabled) return;
    triggerHaptic();
    onClick?.(e);
    onPress?.();
  }, [disabled, triggerHaptic, onClick, onPress]);

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      className={cn(
        'transition-transform cursor-pointer',
        disabled && 'cursor-not-allowed opacity-50',
        className
      )}
      style={{
        transform: isPressed && !disabled ? `scale(${pressScale})` : 'scale(1)',
        transition: `transform ${ANIMATION_DURATION.INSTANT}ms ${EASING.STANDARD}`,
      }}
      onMouseDown={() => !disabled && setIsPressed(true)}
      onMouseUp={() => setIsPressed(false)}
      onMouseLeave={() => setIsPressed(false)}
      onTouchStart={() => !disabled && setIsPressed(true)}
      onTouchEnd={() => setIsPressed(false)}
      onClick={handlePress}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handlePress(e);
        }
      }}
      aria-disabled={disabled}
    >
      {children}
    </div>
  );
}

interface HoverScaleProps {
  children: React.ReactNode;
  /** Scale on hover */
  scale?: number;
  /** Lift shadow on hover */
  lift?: boolean;
  className?: string;
}

/**
 * Wrapper for hover scale effect
 */
export function HoverScale({
  children,
  scale = 1.02,
  lift = false,
  className,
}: HoverScaleProps) {
  return (
    <div
      className={cn(
        'transition-all duration-200',
        lift && 'hover:shadow-lg',
        className
      )}
      style={{
        ['--hover-scale' as string]: scale,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = `scale(${scale})`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'scale(1)';
      }}
    >
      {children}
    </div>
  );
}

// =============================================================================
// OPTIMISTIC UI CONTEXT
// =============================================================================

interface OptimisticAction {
  id: string;
  type: string;
  timestamp: number;
  status: 'pending' | 'confirmed' | 'failed';
  rollback?: () => void;
  data?: unknown;
}

interface OptimisticUIContextValue {
  actions: OptimisticAction[];
  addAction: (action: Omit<OptimisticAction, 'timestamp'>) => void;
  confirmAction: (id: string) => void;
  rollbackAction: (id: string) => void;
  hasPendingActions: boolean;
  pendingCount: number;
}

const OptimisticUIContext = createContext<OptimisticUIContextValue | null>(null);

/**
 * Provider for optimistic UI state management
 */
export function OptimisticUIProvider({ children }: { children: React.ReactNode }) {
  const [actions, setActions] = useState<OptimisticAction[]>([]);

  const addAction = useCallback((action: Omit<OptimisticAction, 'timestamp'>) => {
    setActions((prev) => [...prev, { ...action, timestamp: Date.now() }]);
  }, []);

  const confirmAction = useCallback((id: string) => {
    setActions((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: 'confirmed' as const } : a))
    );
    // Remove confirmed actions after a short delay
    setTimeout(() => {
      setActions((prev) => prev.filter((a) => a.id !== id));
    }, 1000);
  }, []);

  const rollbackAction = useCallback((id: string) => {
    setActions((prev) => {
      const action = prev.find((a) => a.id === id);
      if (action?.rollback) {
        action.rollback();
      }
      return prev.map((a) => (a.id === id ? { ...a, status: 'failed' as const } : a));
    });
  }, []);

  const hasPendingActions = useMemo(
    () => actions.some((a) => a.status === 'pending'),
    [actions]
  );

  const pendingCount = useMemo(
    () => actions.filter((a) => a.status === 'pending').length,
    [actions]
  );

  const value = useMemo(
    () => ({
      actions,
      addAction,
      confirmAction,
      rollbackAction,
      hasPendingActions,
      pendingCount,
    }),
    [actions, addAction, confirmAction, rollbackAction, hasPendingActions, pendingCount]
  );

  return (
    <OptimisticUIContext.Provider value={value}>
      {children}
    </OptimisticUIContext.Provider>
  );
}

/**
 * Hook to use optimistic UI context
 */
export function useOptimisticUI() {
  const context = useContext(OptimisticUIContext);
  if (!context) {
    throw new Error('useOptimisticUI must be used within OptimisticUIProvider');
  }
  return context;
}

// =============================================================================
// SYNC STATUS INDICATOR
// =============================================================================

interface SyncStatusProps {
  /** Whether syncing is in progress */
  syncing: boolean;
  /** Number of pending items */
  pendingCount?: number;
  /** Error state */
  error?: boolean;
  /** Last synced timestamp */
  lastSynced?: Date;
  /** Show detailed status */
  detailed?: boolean;
  className?: string;
}

/**
 * Sync status indicator for background operations
 */
export function SyncStatus({
  syncing,
  pendingCount = 0,
  error = false,
  lastSynced,
  detailed = false,
  className,
}: SyncStatusProps) {
  const getStatusIcon = () => {
    if (error) return '⚠';
    if (syncing) return '↻';
    return '✓';
  };

  const getStatusText = () => {
    if (error) return 'Sync failed';
    if (syncing) return `Syncing${pendingCount > 0 ? ` (${pendingCount})` : ''}...`;
    if (lastSynced) {
      const diff = Date.now() - lastSynced.getTime();
      if (diff < 60000) return 'Just synced';
      if (diff < 3600000) return `Synced ${Math.floor(diff / 60000)}m ago`;
      return `Synced ${Math.floor(diff / 3600000)}h ago`;
    }
    return 'Synced';
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex items-center gap-2 text-sm',
        error ? 'text-red-500' : syncing ? 'text-blue-500' : 'text-green-500',
        className
      )}
    >
      <span
        className={cn('inline-block', syncing && 'animate-spin')}
        aria-hidden="true"
      >
        {getStatusIcon()}
      </span>
      {detailed && <span>{getStatusText()}</span>}
      <span className="sr-only">{getStatusText()}</span>
    </div>
  );
}

// =============================================================================
// PROGRESSIVE IMAGE LOADING
// =============================================================================

interface ProgressiveImageProps {
  /** Low-quality placeholder URL */
  placeholder?: string;
  /** Full-quality image URL */
  src: string;
  /** Alt text */
  alt: string;
  /** Width */
  width?: number | string;
  /** Height */
  height?: number | string;
  /** Object fit */
  objectFit?: 'cover' | 'contain' | 'fill' | 'none';
  className?: string;
}

/**
 * Progressive image loading with placeholder
 */
export function ProgressiveImage({
  placeholder,
  src,
  alt,
  width,
  height,
  objectFit = 'cover',
  className,
}: ProgressiveImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [currentSrc, setCurrentSrc] = useState(placeholder || '');
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      setCurrentSrc(src);
      setIsLoaded(true);
    };
    img.src = src;

    return () => {
      img.onload = null;
    };
  }, [src]);

  const objectFitClasses = {
    cover: 'object-cover',
    contain: 'object-contain',
    fill: 'object-fill',
    none: 'object-none',
  };

  return (
    <div
      className={cn('relative overflow-hidden', className)}
      style={{ width, height }}
    >
      {!isLoaded && !placeholder && (
        <Skeleton className="absolute inset-0" />
      )}
      {currentSrc && (
        <img
          ref={imgRef}
          src={currentSrc}
          alt={alt}
          className={cn(
            'w-full h-full transition-all duration-500',
            objectFitClasses[objectFit],
            isLoaded ? 'opacity-100 blur-0' : 'opacity-50 blur-sm'
          )}
          loading="lazy"
        />
      )}
    </div>
  );
}

// =============================================================================
// LAYOUT SHIFT PREVENTION
// =============================================================================

interface AspectRatioBoxProps {
  /** Aspect ratio (width / height) */
  ratio: number;
  /** Content to render */
  children: React.ReactNode;
  className?: string;
}

/**
 * Container that maintains aspect ratio to prevent layout shifts
 */
export function AspectRatioBox({
  ratio,
  children,
  className,
}: AspectRatioBoxProps) {
  return (
    <div
      className={cn('relative w-full', className)}
      style={{ paddingBottom: `${(1 / ratio) * 100}%` }}
    >
      <div className="absolute inset-0">{children}</div>
    </div>
  );
}

/**
 * Reserved space placeholder to prevent CLS
 */
export function ReservedSpace({
  height,
  width,
  children,
  className,
}: {
  height: number | string;
  width?: number | string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn('relative', className)}
      style={{
        minHeight: typeof height === 'number' ? `${height}px` : height,
        width: typeof width === 'number' ? `${width}px` : width,
      }}
    >
      {children}
    </div>
  );
}

// =============================================================================
// HAPTIC FEEDBACK HOOK
// =============================================================================

interface HapticOptions {
  pattern: HapticPattern;
  /** Enable haptic feedback */
  enabled?: boolean;
}

/**
 * Hook for triggering haptic feedback
 */
export function useHapticFeedback(options: HapticOptions = { pattern: 'light', enabled: true }) {
  const { pattern, enabled = true } = options;

  const trigger = useCallback(() => {
    if (!enabled || !('vibrate' in navigator)) return;

    const patterns: Record<HapticPattern, number | number[]> = {
      light: 10,
      medium: 25,
      heavy: 50,
      success: [10, 30, 10],
      warning: [25, 50, 25],
      error: [50, 25, 50],
    };

    navigator.vibrate(patterns[pattern]);
  }, [pattern, enabled]);

  return { trigger, isSupported: 'vibrate' in navigator };
}

// =============================================================================
// TRANSITION GROUP
// =============================================================================

interface FadeTransitionProps {
  /** Whether element is visible */
  show: boolean;
  /** Children to render */
  children: React.ReactNode;
  /** Duration in ms */
  duration?: number;
  /** Unmount when hidden */
  unmountOnHide?: boolean;
  className?: string;
}

/**
 * Simple fade transition wrapper
 */
export function FadeTransition({
  show,
  children,
  duration = ANIMATION_DURATION.NORMAL,
  unmountOnHide = false,
  className,
}: FadeTransitionProps) {
  const [shouldRender, setShouldRender] = useState(show);

  useEffect(() => {
    if (show) {
      setShouldRender(true);
    } else if (unmountOnHide) {
      const timer = setTimeout(() => setShouldRender(false), duration);
      return () => clearTimeout(timer);
    }
  }, [show, unmountOnHide, duration]);

  if (!shouldRender && unmountOnHide) return null;

  return (
    <div
      className={cn('transition-opacity', className)}
      style={{
        opacity: show ? 1 : 0,
        transitionDuration: `${duration}ms`,
      }}
    >
      {children}
    </div>
  );
}

interface SlideTransitionProps {
  /** Whether element is visible */
  show: boolean;
  /** Children to render */
  children: React.ReactNode;
  /** Direction of slide */
  direction?: 'up' | 'down' | 'left' | 'right';
  /** Duration in ms */
  duration?: number;
  className?: string;
}

/**
 * Slide transition wrapper
 */
export function SlideTransition({
  show,
  children,
  direction = 'up',
  duration = ANIMATION_DURATION.NORMAL,
  className,
}: SlideTransitionProps) {
  const getTransform = () => {
    if (show) return 'translate(0, 0)';
    
    const transforms: Record<string, string> = {
      up: 'translate(0, 20px)',
      down: 'translate(0, -20px)',
      left: 'translate(20px, 0)',
      right: 'translate(-20px, 0)',
    };
    return transforms[direction];
  };

  return (
    <div
      className={cn('transition-all', className)}
      style={{
        opacity: show ? 1 : 0,
        transform: getTransform(),
        transitionDuration: `${duration}ms`,
        transitionTimingFunction: EASING.DECELERATE,
      }}
    >
      {children}
    </div>
  );
}

// =============================================================================
// CSS KEYFRAMES (for tailwind.config.js)
// =============================================================================

/**
 * CSS keyframes that need to be added to tailwind.config.js:
 * 
 * @keyframes shimmer {
 *   100% {
 *     transform: translateX(100%);
 *   }
 * }
 * 
 * @keyframes indeterminate {
 *   0% {
 *     left: -50%;
 *   }
 *   100% {
 *     left: 100%;
 *   }
 * }
 */
export const REQUIRED_KEYFRAMES = {
  shimmer: {
    '100%': { transform: 'translateX(100%)' },
  },
  indeterminate: {
    '0%': { left: '-50%' },
    '100%': { left: '100%' },
  },
} as const;
