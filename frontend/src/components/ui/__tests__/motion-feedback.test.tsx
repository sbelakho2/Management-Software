/**
 * Tests for Motion, Feedback & Perceived Performance Components
 * 
 * Section 19.4: Motion, Feedback & Perceived Performance
 * 
 * Tests:
 * - Skeleton components
 * - Progress indicators
 * - Animated success/error indicators
 * - Loading spinners
 * - Micro-interaction wrappers
 * - Optimistic UI utilities
 * - Progressive image loading
 * - Transition components
 */

import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  ANIMATION_DURATION,
  EASING,
  HAPTIC_PATTERN,
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonTableRow,
  SkeletonAvatar,
  ProgressBar,
  StepProgress,
  AnimatedCheckmark,
  AnimatedCross,
  Spinner,
  PulsingDots,
  Pressable,
  HoverScale,
  OptimisticUIProvider,
  useOptimisticUI,
  SyncStatus,
  ProgressiveImage,
  AspectRatioBox,
  ReservedSpace,
  useHapticFeedback,
  FadeTransition,
  SlideTransition,
  REQUIRED_KEYFRAMES,
} from '../motion-feedback';

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('Motion Constants', () => {
  describe('ANIMATION_DURATION', () => {
    it('should have all required duration values', () => {
      expect(ANIMATION_DURATION.INSTANT).toBe(50);
      expect(ANIMATION_DURATION.FAST).toBe(150);
      expect(ANIMATION_DURATION.NORMAL).toBe(300);
      expect(ANIMATION_DURATION.SLOW).toBe(500);
      expect(ANIMATION_DURATION.PAGE).toBe(700);
    });
  });

  describe('EASING', () => {
    it('should have all required easing curves', () => {
      expect(EASING.STANDARD).toContain('cubic-bezier');
      expect(EASING.DECELERATE).toContain('cubic-bezier');
      expect(EASING.ACCELERATE).toContain('cubic-bezier');
      expect(EASING.BOUNCE).toContain('cubic-bezier');
      expect(EASING.SPRING).toContain('cubic-bezier');
    });
  });

  describe('HAPTIC_PATTERN', () => {
    it('should have all required haptic patterns', () => {
      expect(HAPTIC_PATTERN.LIGHT).toBe('light');
      expect(HAPTIC_PATTERN.MEDIUM).toBe('medium');
      expect(HAPTIC_PATTERN.HEAVY).toBe('heavy');
      expect(HAPTIC_PATTERN.SUCCESS).toBe('success');
      expect(HAPTIC_PATTERN.WARNING).toBe('warning');
      expect(HAPTIC_PATTERN.ERROR).toBe('error');
    });
  });

  describe('REQUIRED_KEYFRAMES', () => {
    it('should define shimmer keyframe', () => {
      expect(REQUIRED_KEYFRAMES.shimmer).toBeDefined();
      expect(REQUIRED_KEYFRAMES.shimmer['100%']).toEqual({ transform: 'translateX(100%)' });
    });

    it('should define indeterminate keyframe', () => {
      expect(REQUIRED_KEYFRAMES.indeterminate).toBeDefined();
      expect(REQUIRED_KEYFRAMES.indeterminate['0%']).toEqual({ left: '-50%' });
      expect(REQUIRED_KEYFRAMES.indeterminate['100%']).toEqual({ left: '100%' });
    });
  });
});

// =============================================================================
// SKELETON TESTS
// =============================================================================

describe('Skeleton Components', () => {
  describe('Skeleton', () => {
    it('renders with default props', () => {
      render(<Skeleton />);
      
      const skeleton = screen.getByRole('status');
      expect(skeleton).toHaveAttribute('aria-label', 'Loading');
    });

    it('renders with custom dimensions', () => {
      render(<Skeleton width={100} height={50} />);
      
      const skeleton = screen.getByRole('status', { name: 'Loading' });
      expect(skeleton).toHaveStyle({ width: '100px', height: '50px' });
    });

    it('renders with string dimensions', () => {
      render(<Skeleton width="50%" height="2rem" />);
      
      const skeleton = screen.getByRole('status', { name: 'Loading' });
      expect(skeleton).toHaveStyle({ width: '50%', height: '2rem' });
    });

    it('has animate-pulse class when animated', () => {
      render(<Skeleton animate />);
      
      const skeleton = screen.getByRole('status', { name: 'Loading' });
      expect(skeleton.className).toContain('animate-pulse');
    });

    it('does not have animate-pulse when not animated', () => {
      render(<Skeleton animate={false} />);
      
      const skeleton = screen.getByRole('status', { name: 'Loading' });
      expect(skeleton.className).not.toContain('animate-pulse');
    });

    it('applies rounded classes', () => {
      const { rerender } = render(<Skeleton rounded="sm" />);
      expect(screen.getByRole('status', { name: 'Loading' }).className).toContain('rounded-sm');

      rerender(<Skeleton rounded="full" />);
      expect(screen.getByRole('status', { name: 'Loading' }).className).toContain('rounded-full');
    });
  });

  describe('SkeletonText', () => {
    it('renders single line by default', () => {
      render(<SkeletonText />);
      
      // Parent has role="status", child Skeletons don't duplicate the role
      const container = screen.getByRole('status', { name: 'Loading text' });
      const lines = container.querySelectorAll('.animate-pulse');
      expect(lines).toHaveLength(1);
    });

    it('renders multiple lines', () => {
      render(<SkeletonText lines={3} />);
      
      const container = screen.getByRole('status', { name: 'Loading text' });
      const lines = container.querySelectorAll('.animate-pulse');
      expect(lines).toHaveLength(3);
    });

    it('has aria-label for accessibility', () => {
      render(<SkeletonText />);
      
      expect(screen.getByRole('status', { name: 'Loading text' })).toBeInTheDocument();
    });
  });

  describe('SkeletonCard', () => {
    it('renders without image by default', () => {
      render(<SkeletonCard />);
      
      const card = screen.getByRole('status', { name: 'Loading card' });
      expect(card).toBeInTheDocument();
    });

    it('renders with image placeholder', () => {
      render(<SkeletonCard hasImage imageHeight={200} />);
      
      // Should have multiple skeleton elements (image + text lines)
      const skeletons = screen.getAllByRole('status');
      expect(skeletons.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('SkeletonTableRow', () => {
    it('renders with default columns', () => {
      render(
        <table>
          <tbody>
            <SkeletonTableRow />
          </tbody>
        </table>
      );
      
      const cells = screen.getAllByRole('cell');
      expect(cells).toHaveLength(4);
    });

    it('renders with custom column count', () => {
      render(
        <table>
          <tbody>
            <SkeletonTableRow columns={6} />
          </tbody>
        </table>
      );
      
      const cells = screen.getAllByRole('cell');
      expect(cells).toHaveLength(6);
    });
  });

  describe('SkeletonAvatar', () => {
    it('renders with default size', () => {
      render(<SkeletonAvatar />);
      
      const skeleton = screen.getByRole('status');
      expect(skeleton).toHaveStyle({ width: '40px', height: '40px' });
    });

    it('renders with custom size', () => {
      render(<SkeletonAvatar size={64} />);
      
      const skeleton = screen.getByRole('status');
      expect(skeleton).toHaveStyle({ width: '64px', height: '64px' });
    });
  });
});

// =============================================================================
// PROGRESS TESTS
// =============================================================================

describe('Progress Components', () => {
  describe('ProgressBar', () => {
    it('renders with value', () => {
      render(<ProgressBar value={50} />);
      
      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '50');
      expect(progressbar).toHaveAttribute('aria-valuemin', '0');
      expect(progressbar).toHaveAttribute('aria-valuemax', '100');
    });

    it('shows label when showLabel is true', () => {
      render(<ProgressBar value={75} showLabel />);
      
      expect(screen.getByText('75%')).toBeInTheDocument();
      expect(screen.getByText('Progress')).toBeInTheDocument();
    });

    it('shows custom label', () => {
      render(<ProgressBar value={30} label="Uploading" showLabel />);
      
      expect(screen.getByText('Uploading')).toBeInTheDocument();
    });

    it('clamps value between 0 and 100', () => {
      const { rerender } = render(<ProgressBar value={-10} showLabel />);
      expect(screen.getByText('0%')).toBeInTheDocument();

      rerender(<ProgressBar value={150} showLabel />);
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('supports indeterminate mode', () => {
      render(<ProgressBar value={50} indeterminate />);
      
      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).not.toHaveAttribute('aria-valuenow');
    });

    it('applies size variants', () => {
      const { rerender } = render(<ProgressBar value={50} size="sm" />);
      expect(screen.getByRole('progressbar').className).toContain('h-1');

      rerender(<ProgressBar value={50} size="lg" />);
      expect(screen.getByRole('progressbar').className).toContain('h-4');
    });

    it('applies variant colors', () => {
      render(<ProgressBar value={50} variant="success" />);
      
      const bar = screen.getByRole('progressbar').querySelector('div');
      expect(bar?.className).toContain('bg-green-500');
    });
  });

  describe('StepProgress', () => {
    it('renders correct number of steps', () => {
      render(<StepProgress currentStep={0} totalSteps={4} />);
      
      // At step 0, all steps should show their numbers (none completed)
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('4')).toBeInTheDocument();
    });

    it('marks completed steps with checkmark', () => {
      render(<StepProgress currentStep={2} totalSteps={4} />);
      
      // Steps 0 and 1 should be completed (show ✓)
      const checkmarks = screen.getAllByText('✓');
      expect(checkmarks).toHaveLength(2);
    });

    it('marks current step with aria-current', () => {
      render(<StepProgress currentStep={1} totalSteps={3} />);
      
      // Step 2 (index 1) should be current
      const currentStep = screen.getByText('2').closest('div');
      expect(currentStep).toHaveAttribute('aria-current', 'step');
    });

    it('renders step labels', () => {
      const labels = ['Info', 'Review', 'Confirm'];
      render(<StepProgress currentStep={0} totalSteps={3} labels={labels} />);
      
      labels.forEach((label) => {
        expect(screen.getByText(label)).toBeInTheDocument();
      });
    });
  });
});

// =============================================================================
// ANIMATED INDICATOR TESTS
// =============================================================================

describe('Animated Indicators', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('AnimatedCheckmark', () => {
    it('renders with status role', () => {
      render(<AnimatedCheckmark />);
      
      expect(screen.getByRole('status', { name: 'Success' })).toBeInTheDocument();
    });

    it('has default size of 48px', () => {
      render(<AnimatedCheckmark />);
      
      const container = screen.getByRole('status');
      expect(container).toHaveStyle({ width: '48px', height: '48px' });
    });

    it('respects custom size', () => {
      render(<AnimatedCheckmark size={64} />);
      
      const container = screen.getByRole('status');
      expect(container).toHaveStyle({ width: '64px', height: '64px' });
    });

    it('respects delay prop', () => {
      render(<AnimatedCheckmark delay={500} />);
      
      // Animation starts after delay - check the SVG has the transition class
      const container = screen.getByRole('status');
      expect(container).toBeInTheDocument();
      // After timer, the animation triggers
      act(() => {
        jest.advanceTimersByTime(600);
      });
      // Component still renders
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

  describe('AnimatedCross', () => {
    it('renders with status role', () => {
      render(<AnimatedCross />);
      
      expect(screen.getByRole('status', { name: 'Error' })).toBeInTheDocument();
    });

    it('has default size of 48px', () => {
      render(<AnimatedCross />);
      
      const container = screen.getByRole('status');
      expect(container).toHaveStyle({ width: '48px', height: '48px' });
    });
  });
});

// =============================================================================
// SPINNER TESTS
// =============================================================================

describe('Loading Spinners', () => {
  describe('Spinner', () => {
    it('renders with status role', () => {
      render(<Spinner />);
      
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has sr-only label', () => {
      render(<Spinner label="Loading data" />);
      
      expect(screen.getByText('Loading data')).toBeInTheDocument();
    });

    it('applies size variants', () => {
      const { rerender } = render(<Spinner size="sm" />);
      expect(screen.getByRole('status')).toHaveStyle({ width: '16px', height: '16px' });

      rerender(<Spinner size="xl" />);
      expect(screen.getByRole('status')).toHaveStyle({ width: '48px', height: '48px' });
    });

    it('has animate-spin class', () => {
      render(<Spinner />);
      
      expect(screen.getByRole('status').className).toContain('animate-spin');
    });
  });

  describe('PulsingDots', () => {
    it('renders with status role', () => {
      render(<PulsingDots />);
      
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('renders three dots', () => {
      render(<PulsingDots />);
      
      const dots = screen.getByRole('status').querySelectorAll('.animate-pulse');
      expect(dots).toHaveLength(3);
    });

    it('has sr-only label', () => {
      render(<PulsingDots label="Processing" />);
      
      expect(screen.getByText('Processing')).toBeInTheDocument();
    });
  });
});

// =============================================================================
// MICRO-INTERACTION TESTS
// =============================================================================

describe('Micro-Interaction Components', () => {
  describe('Pressable', () => {
    it('renders children', () => {
      render(<Pressable>Click me</Pressable>);
      
      expect(screen.getByText('Click me')).toBeInTheDocument();
    });

    it('calls onClick on click', async () => {
      const onClick = jest.fn();
      const user = userEvent.setup();
      render(<Pressable onClick={onClick}>Click me</Pressable>);
      
      await act(async () => {
        await user.click(screen.getByText('Click me'));
      });
      expect(onClick).toHaveBeenCalled();
    });

    it('calls onPress on click', async () => {
      const onPress = jest.fn();
      const user = userEvent.setup();
      render(<Pressable onPress={onPress}>Click me</Pressable>);
      
      await act(async () => {
        await user.click(screen.getByText('Click me'));
      });
      expect(onPress).toHaveBeenCalled();
    });

    it('does not call handlers when disabled', async () => {
      const onClick = jest.fn();
      const user = userEvent.setup();
      render(<Pressable onClick={onClick} disabled>Click me</Pressable>);
      
      await act(async () => {
        await user.click(screen.getByText('Click me'));
      });
      expect(onClick).not.toHaveBeenCalled();
    });

    it('has cursor-not-allowed when disabled', () => {
      render(<Pressable disabled>Click me</Pressable>);
      
      expect(screen.getByRole('button').className).toContain('cursor-not-allowed');
    });

    it('triggers on Enter/Space keydown', async () => {
      const onClick = jest.fn();
      render(<Pressable onClick={onClick}>Click me</Pressable>);
      
      fireEvent.keyDown(screen.getByRole('button'), { key: 'Enter' });
      expect(onClick).toHaveBeenCalledTimes(1);

      fireEvent.keyDown(screen.getByRole('button'), { key: ' ' });
      expect(onClick).toHaveBeenCalledTimes(2);
    });

    it('triggers haptic feedback when enabled', async () => {
      const mockVibrate = jest.fn();
      Object.defineProperty(navigator, 'vibrate', { value: mockVibrate, writable: true });

      const user = userEvent.setup();

      render(<Pressable haptic>Click me</Pressable>);
      
      await act(async () => {
        await user.click(screen.getByText('Click me'));
      });
      expect(mockVibrate).toHaveBeenCalled();
    });
  });

  describe('HoverScale', () => {
    it('renders children', () => {
      render(<HoverScale>Content</HoverScale>);
      
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('applies lift shadow class when enabled', () => {
      render(<HoverScale lift><span>Content</span></HoverScale>);
      
      // The HoverScale div itself has the class
      const content = screen.getByText('Content');
      const container = content.closest('.transition-all');
      expect(container?.className).toContain('hover:shadow-lg');
    });
  });
});

// =============================================================================
// OPTIMISTIC UI TESTS
// =============================================================================

describe('Optimistic UI', () => {
  function TestComponent() {
    const { actions, addAction, confirmAction, rollbackAction, hasPendingActions, pendingCount } =
      useOptimisticUI();

    return (
      <div>
        <button
          onClick={() =>
            addAction({ id: 'test-1', type: 'create', status: 'pending', rollback: jest.fn() })
          }
        >
          Add Action
        </button>
        <button onClick={() => confirmAction('test-1')}>Confirm</button>
        <button onClick={() => rollbackAction('test-1')}>Rollback</button>
        <div data-testid="pending">{hasPendingActions ? 'pending' : 'none'}</div>
        <div data-testid="count">{pendingCount}</div>
        <div data-testid="actions">{JSON.stringify(actions)}</div>
      </div>
    );
  }

  it('throws error when used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => render(<TestComponent />)).toThrow(
      'useOptimisticUI must be used within OptimisticUIProvider'
    );

    consoleError.mockRestore();
  });

  it('adds actions', async () => {
    const user = userEvent.setup();
    render(
      <OptimisticUIProvider>
        <TestComponent />
      </OptimisticUIProvider>
    );

    expect(screen.getByTestId('pending')).toHaveTextContent('none');
    expect(screen.getByTestId('count')).toHaveTextContent('0');

    await act(async () => {
      await user.click(screen.getByText('Add Action'));
    });

    expect(screen.getByTestId('pending')).toHaveTextContent('pending');
    expect(screen.getByTestId('count')).toHaveTextContent('1');
  });

  it('confirms actions', async () => {
    render(
      <OptimisticUIProvider>
        <TestComponent />
      </OptimisticUIProvider>
    );

    fireEvent.click(screen.getByText('Add Action'));
    expect(screen.getByTestId('pending')).toHaveTextContent('pending');

    fireEvent.click(screen.getByText('Confirm'));

    // Action status should change to confirmed
    const actions = JSON.parse(screen.getByTestId('actions').textContent || '[]');
    expect(actions[0]?.status).toBe('confirmed');
  });

  it('rolls back actions', async () => {
    render(
      <OptimisticUIProvider>
        <TestComponent />
      </OptimisticUIProvider>
    );

    fireEvent.click(screen.getByText('Add Action'));
    fireEvent.click(screen.getByText('Rollback'));

    const actions = JSON.parse(screen.getByTestId('actions').textContent || '[]');
    expect(actions[0]?.status).toBe('failed');
  });
});

// =============================================================================
// SYNC STATUS TESTS
// =============================================================================

describe('SyncStatus', () => {
  it('shows syncing state', () => {
    render(<SyncStatus syncing detailed />);
    
    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('Syncing...');
  });

  it('shows pending count when syncing', () => {
    render(<SyncStatus syncing pendingCount={5} detailed />);
    
    expect(screen.getByRole('status')).toHaveTextContent('Syncing (5)...');
  });

  it('shows error state', () => {
    render(<SyncStatus syncing={false} error detailed />);
    
    expect(screen.getByRole('status')).toHaveTextContent('Sync failed');
    expect(screen.getByRole('status').className).toContain('text-red-500');
  });

  it('shows synced state with timestamp', () => {
    const now = new Date();
    render(<SyncStatus syncing={false} lastSynced={now} detailed />);
    
    expect(screen.getByRole('status')).toHaveTextContent('Just synced');
  });

  it('shows time ago for older syncs', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    render(<SyncStatus syncing={false} lastSynced={fiveMinutesAgo} detailed />);
    
    expect(screen.getByRole('status')).toHaveTextContent('Synced 5m ago');
  });

  it('shows spinner icon when syncing', () => {
    render(<SyncStatus syncing />);
    
    const icon = screen.getByText('↻');
    expect(icon.className).toContain('animate-spin');
  });
});

// =============================================================================
// PROGRESSIVE IMAGE TESTS
// =============================================================================

describe('ProgressiveImage', () => {
  it('renders with alt text', () => {
    render(<ProgressiveImage src="/test.jpg" alt="Test image" />);
    
    // Initially shows skeleton or placeholder
    expect(screen.getByRole('status', { name: 'Loading' })).toBeInTheDocument();
  });

  it('shows skeleton when no placeholder', () => {
    render(<ProgressiveImage src="/test.jpg" alt="Test image" />);
    
    expect(screen.getByRole('status', { name: 'Loading' })).toBeInTheDocument();
  });
});

// =============================================================================
// LAYOUT SHIFT PREVENTION TESTS
// =============================================================================

describe('Layout Shift Prevention', () => {
  describe('AspectRatioBox', () => {
    it('renders with correct padding for 16:9', () => {
      render(
        <AspectRatioBox ratio={16 / 9}>
          <div>Content</div>
        </AspectRatioBox>
      );
      
      const container = screen.getByText('Content').parentElement?.parentElement;
      const paddingBottom = (1 / (16 / 9)) * 100;
      expect(container).toHaveStyle({ paddingBottom: `${paddingBottom}%` });
    });

    it('renders with correct padding for 1:1', () => {
      render(
        <AspectRatioBox ratio={1}>
          <div>Content</div>
        </AspectRatioBox>
      );
      
      const container = screen.getByText('Content').parentElement?.parentElement;
      expect(container).toHaveStyle({ paddingBottom: '100%' });
    });
  });

  describe('ReservedSpace', () => {
    it('sets min-height', () => {
      render(
        <ReservedSpace height={200}>
          <div>Content</div>
        </ReservedSpace>
      );
      
      const container = screen.getByText('Content').parentElement;
      expect(container).toHaveStyle({ minHeight: '200px' });
    });

    it('sets width when provided', () => {
      render(
        <ReservedSpace height={100} width={300}>
          <div>Content</div>
        </ReservedSpace>
      );
      
      const container = screen.getByText('Content').parentElement;
      expect(container).toHaveStyle({ width: '300px' });
    });

    it('supports string values', () => {
      render(
        <ReservedSpace height="50vh" width="100%">
          <div>Content</div>
        </ReservedSpace>
      );
      
      const container = screen.getByText('Content').parentElement;
      expect(container).toHaveStyle({ minHeight: '50vh', width: '100%' });
    });
  });
});

// =============================================================================
// HAPTIC FEEDBACK HOOK TESTS
// =============================================================================

describe('useHapticFeedback', () => {
  function TestHaptic({ pattern, enabled }: { pattern?: string; enabled?: boolean }) {
    const { trigger, isSupported } = useHapticFeedback({ 
      pattern: pattern as any || 'light', 
      enabled 
    });
    
    return (
      <div>
        <button onClick={trigger}>Trigger</button>
        <div data-testid="supported">{isSupported ? 'yes' : 'no'}</div>
      </div>
    );
  }

  it('returns isSupported based on navigator.vibrate', () => {
    const mockVibrate = jest.fn();
    Object.defineProperty(navigator, 'vibrate', { value: mockVibrate, writable: true });

    render(<TestHaptic />);
    
    expect(screen.getByTestId('supported')).toHaveTextContent('yes');
  });

  it('calls navigator.vibrate on trigger', () => {
    const mockVibrate = jest.fn();
    Object.defineProperty(navigator, 'vibrate', { value: mockVibrate, writable: true });

    render(<TestHaptic />);
    
    fireEvent.click(screen.getByText('Trigger'));
    expect(mockVibrate).toHaveBeenCalledWith(10); // light pattern
  });

  it('uses different patterns', () => {
    const mockVibrate = jest.fn();
    Object.defineProperty(navigator, 'vibrate', { value: mockVibrate, writable: true });

    const { rerender } = render(<TestHaptic pattern="heavy" />);
    
    fireEvent.click(screen.getByText('Trigger'));
    expect(mockVibrate).toHaveBeenCalledWith(50);

    rerender(<TestHaptic pattern="success" />);
    fireEvent.click(screen.getByText('Trigger'));
    expect(mockVibrate).toHaveBeenCalledWith([10, 30, 10]);
  });

  it('does not trigger when disabled', () => {
    const mockVibrate = jest.fn();
    Object.defineProperty(navigator, 'vibrate', { value: mockVibrate, writable: true });

    render(<TestHaptic enabled={false} />);
    
    fireEvent.click(screen.getByText('Trigger'));
    expect(mockVibrate).not.toHaveBeenCalled();
  });
});

// =============================================================================
// TRANSITION TESTS
// =============================================================================

describe('Transition Components', () => {
  describe('FadeTransition', () => {
    it('renders children', () => {
      render(
        <FadeTransition show>
          <div>Content</div>
        </FadeTransition>
      );
      
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('has opacity 1 when shown', () => {
      render(
        <FadeTransition show data-testid="fade">
          <div>Content</div>
        </FadeTransition>
      );
      
      const container = screen.getByText('Content').parentElement;
      expect(container).toHaveStyle({ opacity: '1' });
    });

    it('has opacity 0 when hidden', () => {
      render(
        <FadeTransition show={false}>
          <div>Content</div>
        </FadeTransition>
      );
      
      const container = screen.getByText('Content').parentElement;
      expect(container).toHaveStyle({ opacity: '0' });
    });

    it('unmounts when hidden with unmountOnHide', async () => {
      jest.useFakeTimers();

      const { rerender } = render(
        <FadeTransition show unmountOnHide>
          <div>Content</div>
        </FadeTransition>
      );

      expect(screen.getByText('Content')).toBeInTheDocument();

      rerender(
        <FadeTransition show={false} unmountOnHide>
          <div>Content</div>
        </FadeTransition>
      );

      act(() => {
        jest.advanceTimersByTime(ANIMATION_DURATION.NORMAL + 100);
      });

      expect(screen.queryByText('Content')).not.toBeInTheDocument();

      jest.useRealTimers();
    });
  });

  describe('SlideTransition', () => {
    it('renders children', () => {
      render(
        <SlideTransition show>
          <div>Content</div>
        </SlideTransition>
      );
      
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('has translate(0,0) when shown', () => {
      render(
        <SlideTransition show>
          <div>Content</div>
        </SlideTransition>
      );
      
      const container = screen.getByText('Content').parentElement;
      expect(container).toHaveStyle({ transform: 'translate(0, 0)' });
    });

    it('translates based on direction when hidden', () => {
      const { rerender } = render(
        <SlideTransition show={false} direction="up">
          <div>Content</div>
        </SlideTransition>
      );
      
      let container = screen.getByText('Content').parentElement;
      expect(container).toHaveStyle({ transform: 'translate(0, 20px)' });

      rerender(
        <SlideTransition show={false} direction="left">
          <div>Content</div>
        </SlideTransition>
      );

      container = screen.getByText('Content').parentElement;
      expect(container).toHaveStyle({ transform: 'translate(20px, 0)' });
    });
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Motion Feedback Integration', () => {
  it('skeleton to content transition', async () => {
    function LoadingContent() {
      const [loading, setLoading] = React.useState(true);

      React.useEffect(() => {
        const timer = setTimeout(() => setLoading(false), 100);
        return () => clearTimeout(timer);
      }, []);

      return loading ? (
        <SkeletonText lines={3} />
      ) : (
        <FadeTransition show>
          <p>Loaded content</p>
        </FadeTransition>
      );
    }

    jest.useFakeTimers();
    render(<LoadingContent />);

    // Initially shows skeleton
    expect(screen.getByRole('status', { name: 'Loading text' })).toBeInTheDocument();

    // After loading
    act(() => {
      jest.advanceTimersByTime(200);
    });

    expect(screen.getByText('Loaded content')).toBeInTheDocument();

    jest.useRealTimers();
  });

  it('step progress with optimistic UI', async () => {
    const user = userEvent.setup();
    function MultiStepForm() {
      const [step, setStep] = React.useState(0);

      return (
        <OptimisticUIProvider>
          <div>
            <StepProgress currentStep={step} totalSteps={3} labels={['Info', 'Review', 'Done']} />
            <button onClick={() => setStep(Math.min(2, step + 1))}>Next</button>
            <button onClick={() => setStep(Math.max(0, step - 1))}>Back</button>
          </div>
        </OptimisticUIProvider>
      );
    }

    render(<MultiStepForm />);

    // Start at step 0
    expect(screen.getByText('1').closest('div')).toHaveAttribute('aria-current', 'step');

    // Move to step 1
    await act(async () => {
      await user.click(screen.getByText('Next'));
    });
    expect(screen.getByText('2').closest('div')).toHaveAttribute('aria-current', 'step');
    expect(screen.getAllByText('✓')).toHaveLength(1);

    // Move to step 2
    await act(async () => {
      await user.click(screen.getByText('Next'));
    });
    expect(screen.getByText('3').closest('div')).toHaveAttribute('aria-current', 'step');
    expect(screen.getAllByText('✓')).toHaveLength(2);
  });
});
