/**
 * Accessibility Components and Utilities
 * 
 * Section 19.3: Accessibility (WCAG 2.1 AA) Rigor
 * 
 * Provides:
 * - Skip to content link
 * - Focus trap for modals
 * - Aria-live regions for notifications
 * - Semantic landmarks
 * - Screen reader only content
 * - High contrast mode support
 * - Reduced motion support
 * - Keyboard navigation utilities
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

// =============================================================================
// CONSTANTS
// =============================================================================

/**
 * Minimum touch target size for industrial/accessibility requirements
 * WCAG 2.1 AAA recommends 44x44px minimum
 */
export const MIN_TOUCH_TARGET = 44;

/**
 * High-visibility focus ring width
 */
export const FOCUS_RING_WIDTH = 3;

/**
 * Keyboard keys for navigation
 */
export const KEYBOARD_KEYS = {
  ENTER: 'Enter',
  SPACE: ' ',
  TAB: 'Tab',
  ESCAPE: 'Escape',
  ARROW_UP: 'ArrowUp',
  ARROW_DOWN: 'ArrowDown',
  ARROW_LEFT: 'ArrowLeft',
  ARROW_RIGHT: 'ArrowRight',
  HOME: 'Home',
  END: 'End',
} as const;

/**
 * ARIA live politeness levels
 */
export const ARIA_LIVE = {
  OFF: 'off',
  POLITE: 'polite',
  ASSERTIVE: 'assertive',
} as const;

// =============================================================================
// SKIP TO CONTENT
// =============================================================================

export interface SkipToContentProps extends React.HTMLAttributes<HTMLAnchorElement> {
  /** Target element ID to skip to */
  targetId?: string;
  /** Link text for screen readers */
  children?: React.ReactNode;
}

/**
 * Skip to content link for keyboard/screen reader users
 * Becomes visible only on focus
 */
export const SkipToContent = React.forwardRef<HTMLAnchorElement, SkipToContentProps>(
  ({ targetId = 'main-content', children = 'Skip to content', className, ...props }, ref) => {
    return (
      <a
        ref={ref}
        href={`#${targetId}`}
        className={cn(
          // Hidden by default, visible on focus
          'sr-only focus:not-sr-only',
          // When visible, position at top-left
          'focus:absolute focus:left-4 focus:top-4 focus:z-50',
          // Styling when visible
          'focus:rounded-md focus:bg-primary focus:px-4 focus:py-2',
          'focus:text-primary-foreground focus:shadow-lg',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
          // High visibility
          'focus:font-semibold',
          className
        )}
        {...props}
      >
        {children}
      </a>
    );
  }
);
SkipToContent.displayName = 'SkipToContent';

// =============================================================================
// FOCUS TRAP
// =============================================================================

export interface FocusTrapProps {
  /** Whether the focus trap is active */
  active?: boolean;
  /** Children to trap focus within */
  children: React.ReactNode;
  /** Callback when escape is pressed */
  onEscape?: () => void;
  /** Whether to restore focus when trap deactivates */
  restoreFocus?: boolean;
  /** Initial focus element selector */
  initialFocus?: string;
}

/**
 * Focus trap component for modals and dialogs
 * Ensures focus remains within the component until closed
 */
export function FocusTrap({
  active = true,
  children,
  onEscape,
  restoreFocus = true,
  initialFocus,
}: FocusTrapProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const previousFocusRef = React.useRef<HTMLElement | null>(null);

  // Store previous focus element
  React.useEffect(() => {
    if (active && restoreFocus) {
      previousFocusRef.current = document.activeElement as HTMLElement;
    }
    return () => {
      if (restoreFocus && previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [active, restoreFocus]);

  // Set initial focus
  React.useEffect(() => {
    if (!active || !containerRef.current) return;

    const element = initialFocus
      ? containerRef.current.querySelector<HTMLElement>(initialFocus)
      : getFocusableElements(containerRef.current)[0];

    if (element) {
      element.focus();
    }
  }, [active, initialFocus]);

  // Handle keyboard navigation
  React.useEffect(() => {
    if (!active) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === KEYBOARD_KEYS.ESCAPE) {
        onEscape?.();
        return;
      }

      if (event.key !== KEYBOARD_KEYS.TAB || !containerRef.current) return;

      const focusableElements = getFocusableElements(containerRef.current);
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [active, onEscape]);

  return (
    <div ref={containerRef} data-focus-trap={active ? 'true' : 'false'}>
      {children}
    </div>
  );
}

// =============================================================================
// ARIA LIVE REGION
// =============================================================================

export interface AriaLiveRegionProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Politeness level */
  politeness?: 'off' | 'polite' | 'assertive';
  /** Whether updates are atomic */
  atomic?: boolean;
  /** Which parts changed */
  relevant?: 'additions' | 'removals' | 'text' | 'all';
  /** Content to announce */
  children: React.ReactNode;
}

/**
 * ARIA live region for announcing dynamic content changes
 * Use for notifications, status updates, and error messages
 */
export const AriaLiveRegion = React.forwardRef<HTMLDivElement, AriaLiveRegionProps>(
  (
    { 
      politeness = 'polite', 
      atomic = true, 
      relevant = 'additions text', 
      children, 
      className,
      ...props 
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        aria-live={politeness}
        aria-atomic={atomic}
        aria-relevant={relevant}
        className={cn('sr-only', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);
AriaLiveRegion.displayName = 'AriaLiveRegion';

// =============================================================================
// VISUALLY HIDDEN (Screen Reader Only)
// =============================================================================

export interface VisuallyHiddenProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Content only visible to screen readers */
  children: React.ReactNode;
  /** Render as different element */
  as?: 'span' | 'div' | 'label';
}

/**
 * Visually hidden content that remains accessible to screen readers
 * Use for icon-only buttons, additional context, etc.
 */
export const VisuallyHidden = React.forwardRef<HTMLSpanElement, VisuallyHiddenProps>(
  ({ children, as: Component = 'span', className, ...props }, ref) => {
    return (
      <Component
        ref={ref as React.Ref<HTMLSpanElement>}
        className={cn('sr-only', className)}
        {...props}
      >
        {children}
      </Component>
    );
  }
);
VisuallyHidden.displayName = 'VisuallyHidden';

// =============================================================================
// SEMANTIC LANDMARKS
// =============================================================================

export interface LandmarkProps extends React.HTMLAttributes<HTMLElement> {
  /** Landmark label for screen readers */
  label?: string;
  /** Children content */
  children: React.ReactNode;
}

/**
 * Main content landmark
 */
export const MainLandmark = React.forwardRef<HTMLElement, LandmarkProps>(
  ({ label = 'Main content', children, id = 'main-content', ...props }, ref) => {
    return (
      <main ref={ref} id={id} aria-label={label} {...props}>
        {children}
      </main>
    );
  }
);
MainLandmark.displayName = 'MainLandmark';

/**
 * Navigation landmark
 */
export const NavLandmark = React.forwardRef<HTMLElement, LandmarkProps>(
  ({ label, children, ...props }, ref) => {
    return (
      <nav ref={ref} aria-label={label} {...props}>
        {children}
      </nav>
    );
  }
);
NavLandmark.displayName = 'NavLandmark';

/**
 * Aside/complementary content landmark
 */
export const AsideLandmark = React.forwardRef<HTMLElement, LandmarkProps>(
  ({ label, children, ...props }, ref) => {
    return (
      <aside ref={ref} aria-label={label} {...props}>
        {children}
      </aside>
    );
  }
);
AsideLandmark.displayName = 'AsideLandmark';

/**
 * Header landmark
 */
export const HeaderLandmark = React.forwardRef<HTMLElement, LandmarkProps>(
  ({ label, children, ...props }, ref) => {
    return (
      <header ref={ref} aria-label={label} {...props}>
        {children}
      </header>
    );
  }
);
HeaderLandmark.displayName = 'HeaderLandmark';

/**
 * Footer landmark
 */
export const FooterLandmark = React.forwardRef<HTMLElement, LandmarkProps>(
  ({ label, children, ...props }, ref) => {
    return (
      <footer ref={ref} aria-label={label} {...props}>
        {children}
      </footer>
    );
  }
);
FooterLandmark.displayName = 'FooterLandmark';

/**
 * Region landmark for significant content areas
 */
export const RegionLandmark = React.forwardRef<HTMLElement, LandmarkProps & { labelledBy?: string }>(
  ({ label, labelledBy, children, ...props }, ref) => {
    return (
      <section
        ref={ref}
        role="region"
        aria-label={label}
        aria-labelledby={labelledBy}
        {...props}
      >
        {children}
      </section>
    );
  }
);
RegionLandmark.displayName = 'RegionLandmark';

// =============================================================================
// ACCESSIBLE ICON BUTTON
// =============================================================================

export interface AccessibleIconButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Screen reader label (required for icon-only buttons) */
  label: string;
  /** Icon to display */
  icon: React.ReactNode;
  /** Additional visible tooltip */
  tooltip?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

/**
 * Accessible icon-only button with required aria-label
 * Meets WCAG 2.1 AA minimum touch target of 44x44px
 */
export const AccessibleIconButton = React.forwardRef<
  HTMLButtonElement,
  AccessibleIconButtonProps
>(({ label, icon, tooltip = false, size = 'md', className, ...props }, ref) => {
  const sizeClasses = {
    sm: 'h-9 w-9 min-h-[36px] min-w-[36px]',
    md: 'h-11 w-11 min-h-[44px] min-w-[44px]',
    lg: 'h-14 w-14 min-h-[56px] min-w-[56px]',
  };

  return (
    <button
      ref={ref}
      type="button"
      aria-label={label}
      title={tooltip ? label : undefined}
      className={cn(
        // Base styles
        'inline-flex items-center justify-center rounded-md',
        // Focus styles (high visibility)
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        // Size
        sizeClasses[size],
        // Interactive states
        'transition-colors hover:bg-accent hover:text-accent-foreground',
        'disabled:pointer-events-none disabled:opacity-50',
        className
      )}
      {...props}
    >
      {icon}
      <VisuallyHidden>{label}</VisuallyHidden>
    </button>
  );
});
AccessibleIconButton.displayName = 'AccessibleIconButton';

// =============================================================================
// HIGH CONTRAST MODE
// =============================================================================

export interface HighContrastProps {
  /** Whether high contrast is enabled */
  enabled?: boolean;
  /** Children content */
  children: React.ReactNode;
}

/**
 * High contrast mode wrapper
 * Applies high contrast styles when enabled
 */
export function HighContrastProvider({ enabled = false, children }: HighContrastProps) {
  React.useEffect(() => {
    if (enabled) {
      document.documentElement.classList.add('high-contrast');
    } else {
      document.documentElement.classList.remove('high-contrast');
    }
    return () => {
      document.documentElement.classList.remove('high-contrast');
    };
  }, [enabled]);

  return <>{children}</>;
}

// =============================================================================
// REDUCED MOTION
// =============================================================================

/**
 * Hook to detect user's reduced motion preference
 */
export function useReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = React.useState(false);

  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setReducedMotion(event.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return reducedMotion;
}

/**
 * Component that respects reduced motion preferences
 */
export function ReducedMotionAware({
  children,
  fallback,
}: {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const reducedMotion = useReducedMotion();
  return <>{reducedMotion && fallback ? fallback : children}</>;
}

// =============================================================================
// KEYBOARD NAVIGATION HOOK
// =============================================================================

export interface UseKeyboardNavigationOptions {
  /** List of refs to navigate between */
  refs: React.RefObject<HTMLElement>[];
  /** Whether navigation wraps around */
  wrap?: boolean;
  /** Orientation of navigation */
  orientation?: 'horizontal' | 'vertical' | 'both';
  /** Callback when selection changes */
  onSelect?: (index: number) => void;
}

/**
 * Hook for keyboard arrow navigation between elements
 */
export function useKeyboardNavigation({
  refs,
  wrap = true,
  orientation = 'both',
  onSelect,
}: UseKeyboardNavigationOptions) {
  const [activeIndex, setActiveIndex] = React.useState(0);

  const handleKeyDown = React.useCallback(
    (event: React.KeyboardEvent) => {
      const { key } = event;
      const canNavigateHorizontal = orientation === 'horizontal' || orientation === 'both';
      const canNavigateVertical = orientation === 'vertical' || orientation === 'both';

      let newIndex = activeIndex;
      const maxIndex = refs.length - 1;

      if (
        (canNavigateVertical && key === KEYBOARD_KEYS.ARROW_DOWN) ||
        (canNavigateHorizontal && key === KEYBOARD_KEYS.ARROW_RIGHT)
      ) {
        event.preventDefault();
        newIndex = wrap
          ? (activeIndex + 1) % refs.length
          : Math.min(activeIndex + 1, maxIndex);
      } else if (
        (canNavigateVertical && key === KEYBOARD_KEYS.ARROW_UP) ||
        (canNavigateHorizontal && key === KEYBOARD_KEYS.ARROW_LEFT)
      ) {
        event.preventDefault();
        newIndex = wrap
          ? (activeIndex - 1 + refs.length) % refs.length
          : Math.max(activeIndex - 1, 0);
      } else if (key === KEYBOARD_KEYS.HOME) {
        event.preventDefault();
        newIndex = 0;
      } else if (key === KEYBOARD_KEYS.END) {
        event.preventDefault();
        newIndex = maxIndex;
      }

      if (newIndex !== activeIndex) {
        setActiveIndex(newIndex);
        refs[newIndex]?.current?.focus();
        onSelect?.(newIndex);
      }
    },
    [activeIndex, refs, wrap, orientation, onSelect]
  );

  return {
    activeIndex,
    setActiveIndex,
    handleKeyDown,
    getItemProps: (index: number) => ({
      tabIndex: index === activeIndex ? 0 : -1,
      'aria-selected': index === activeIndex,
      onKeyDown: handleKeyDown,
    }),
  };
}

// =============================================================================
// TAB ORDER MANAGER
// =============================================================================

/**
 * Ensure logical tab order for complex forms
 */
export function TabOrderManager({
  children,
  order,
}: {
  children: React.ReactNode;
  order: string[];
}) {
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!containerRef.current) return;

    const elements = containerRef.current.querySelectorAll('[data-tab-order]');
    elements.forEach((element) => {
      const orderKey = element.getAttribute('data-tab-order');
      if (orderKey) {
        const index = order.indexOf(orderKey);
        if (index >= 0) {
          (element as HTMLElement).tabIndex = index + 1;
        }
      }
    });
  }, [order]);

  return <div ref={containerRef}>{children}</div>;
}

// =============================================================================
// ACCESSIBLE TABLE
// =============================================================================

export interface AccessibleTableProps extends React.TableHTMLAttributes<HTMLTableElement> {
  /** Caption for the table (required for accessibility) */
  caption: string;
  /** Whether caption is visually hidden */
  captionHidden?: boolean;
  /** Summary for complex tables */
  summary?: string;
}

/**
 * Accessible table with proper caption and structure
 */
export const AccessibleTable = React.forwardRef<HTMLTableElement, AccessibleTableProps>(
  ({ caption, captionHidden = false, summary, children, className, ...props }, ref) => {
    return (
      <table ref={ref} className={className} aria-describedby={summary ? `${caption}-summary` : undefined} {...props}>
        <caption className={captionHidden ? 'sr-only' : undefined}>{caption}</caption>
        {summary && (
          <caption id={`${caption}-summary`} className="sr-only">
            {summary}
          </caption>
        )}
        {children}
      </table>
    );
  }
);
AccessibleTable.displayName = 'AccessibleTable';

// =============================================================================
// COLOR CONTRAST UTILITIES
// =============================================================================

/**
 * Status indicator with color AND icon for colorblind accessibility
 */
export interface AccessibleStatusProps {
  /** Status type */
  status: 'success' | 'warning' | 'error' | 'info';
  /** Label text */
  label: string;
  /** Show icon */
  showIcon?: boolean;
  /** Size */
  size?: 'sm' | 'md' | 'lg';
}

const STATUS_ICONS = {
  success: '✓',
  warning: '⚠',
  error: '✕',
  info: 'ℹ',
};

const STATUS_CLASSES = {
  success: 'bg-green-100 text-green-800 border-green-300',
  warning: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  error: 'bg-red-100 text-red-800 border-red-300',
  info: 'bg-blue-100 text-blue-800 border-blue-300',
};

export function AccessibleStatus({
  status,
  label,
  showIcon = true,
  size = 'md',
}: AccessibleStatusProps) {
  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1',
    lg: 'text-base px-3 py-1.5',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border font-medium',
        STATUS_CLASSES[status],
        sizeClasses[size]
      )}
      role="status"
      aria-label={`${status}: ${label}`}
    >
      {showIcon && (
        <span aria-hidden="true" className="font-bold">
          {STATUS_ICONS[status]}
        </span>
      )}
      {label}
    </span>
  );
}

// =============================================================================
// FOCUS INDICATOR
// =============================================================================

/**
 * Custom focus ring that meets WCAG requirements
 */
export const focusRingClasses = cn(
  'focus:outline-none',
  'focus-visible:ring-2',
  'focus-visible:ring-ring',
  'focus-visible:ring-offset-2',
  'focus-visible:ring-offset-background'
);

/**
 * High visibility focus classes for factory floor use
 */
export const highVisibilityFocusClasses = cn(
  'focus:outline-none',
  'focus-visible:ring-4',
  'focus-visible:ring-yellow-400',
  'focus-visible:ring-offset-4',
  'focus-visible:ring-offset-black'
);

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Get all focusable elements within a container
 */
export function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const focusableSelectors = [
    'button:not([disabled])',
    'a[href]',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable]',
  ].join(', ');

  return Array.from(container.querySelectorAll<HTMLElement>(focusableSelectors));
}

/**
 * Calculate contrast ratio between two colors
 */
export function getContrastRatio(foreground: string, background: string): number {
  const getLuminance = (rgb: number[]): number => {
    const [r, g, b] = rgb.map((c) => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };

  const parseColor = (color: string): number[] => {
    const hex = color.replace('#', '');
    return [
      parseInt(hex.slice(0, 2), 16),
      parseInt(hex.slice(2, 4), 16),
      parseInt(hex.slice(4, 6), 16),
    ];
  };

  const l1 = getLuminance(parseColor(foreground));
  const l2 = getLuminance(parseColor(background));

  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);

  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if contrast ratio meets WCAG AA requirements
 * 4.5:1 for normal text, 3:1 for large text
 */
export function meetsContrastRequirement(
  ratio: number,
  isLargeText: boolean = false
): boolean {
  return isLargeText ? ratio >= 3 : ratio >= 4.5;
}

/**
 * Generate an ID for aria relationships
 */
export function generateAriaId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).substring(2, 9)}`;
}
