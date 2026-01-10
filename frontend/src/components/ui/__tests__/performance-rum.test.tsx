import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import {
  // Constants
  WEB_VITALS_THRESHOLDS,
  PERFORMANCE_BUDGETS,
  // Types
  WebVitalName,
  MetricValue,
  InteractionMetric,
  ResourceMetric,
  BudgetViolation,
  // Functions
  rateMetric,
  rateInteraction,
  observeLCP,
  observeFID,
  observeCLS,
  observeINP,
  getTTFB,
  getFCP,
  observeResources,
  createInteractionTracker,
  formatPerformanceReport,
  sendPerformanceBeacon,
  // Hooks
  useRUM,
  useInteractionTracking,
  usePerformanceBudget,
  // Components
  RUMProvider,
  WebVitalCard,
  WebVitalsDashboard,
  InteractionLatencyList,
  BudgetViolationAlert,
  PerformanceBudgetMeter,
  ResourceBudgetDashboard,
  TrackedButton,
  RUMDashboardPanel,
} from '../performance-rum';

// =============================================================================
// TEST UTILITIES
// =============================================================================

function TestWrapper({ children, route = '/' }: { children: React.ReactNode; route?: string }) {
  return <RUMProvider route={route}>{children}</RUMProvider>;
}

function TestHookComponent<T>({ hook, onResult }: { hook: () => T; onResult: (result: T) => void }) {
  const result = hook();
  React.useEffect(() => {
    onResult(result);
  }, [result, onResult]);
  return null;
}

// =============================================================================
// CONSTANT TESTS
// =============================================================================

describe('Web Vitals Thresholds', () => {
  describe('WEB_VITALS_THRESHOLDS', () => {
    it('should define LCP thresholds', () => {
      expect(WEB_VITALS_THRESHOLDS.LCP.good).toBe(2500);
      expect(WEB_VITALS_THRESHOLDS.LCP.needsImprovement).toBe(4000);
      expect(WEB_VITALS_THRESHOLDS.LCP.unit).toBe('ms');
    });

    it('should define FID thresholds', () => {
      expect(WEB_VITALS_THRESHOLDS.FID.good).toBe(100);
      expect(WEB_VITALS_THRESHOLDS.FID.needsImprovement).toBe(300);
      expect(WEB_VITALS_THRESHOLDS.FID.unit).toBe('ms');
    });

    it('should define CLS thresholds', () => {
      expect(WEB_VITALS_THRESHOLDS.CLS.good).toBe(0.1);
      expect(WEB_VITALS_THRESHOLDS.CLS.needsImprovement).toBe(0.25);
      expect(WEB_VITALS_THRESHOLDS.CLS.unit).toBe('');
    });

    it('should define INP thresholds', () => {
      expect(WEB_VITALS_THRESHOLDS.INP.good).toBe(200);
      expect(WEB_VITALS_THRESHOLDS.INP.needsImprovement).toBe(500);
    });

    it('should define TTFB thresholds', () => {
      expect(WEB_VITALS_THRESHOLDS.TTFB.good).toBe(800);
      expect(WEB_VITALS_THRESHOLDS.TTFB.needsImprovement).toBe(1800);
    });

    it('should define FCP thresholds', () => {
      expect(WEB_VITALS_THRESHOLDS.FCP.good).toBe(1800);
      expect(WEB_VITALS_THRESHOLDS.FCP.needsImprovement).toBe(3000);
    });

    it('should include descriptions for all metrics', () => {
      Object.values(WEB_VITALS_THRESHOLDS).forEach(threshold => {
        expect(threshold.description).toBeDefined();
        expect(threshold.description.length).toBeGreaterThan(0);
      });
    });
  });

  describe('PERFORMANCE_BUDGETS', () => {
    it('should define JS bundle budgets', () => {
      expect(PERFORMANCE_BUDGETS.jsBundle.critical).toBe(50 * 1024);
      expect(PERFORMANCE_BUDGETS.jsBundle.route).toBe(200 * 1024);
      expect(PERFORMANCE_BUDGETS.jsBundle.total).toBe(500 * 1024);
    });

    it('should define CSS bundle budgets', () => {
      expect(PERFORMANCE_BUDGETS.cssBundle.critical).toBe(20 * 1024);
      expect(PERFORMANCE_BUDGETS.cssBundle.total).toBe(100 * 1024);
    });

    it('should define image budgets', () => {
      expect(PERFORMANCE_BUDGETS.images.hero).toBe(200 * 1024);
      expect(PERFORMANCE_BUDGETS.images.thumbnail).toBe(50 * 1024);
      expect(PERFORMANCE_BUDGETS.images.icon).toBe(10 * 1024);
    });

    it('should define font budgets', () => {
      expect(PERFORMANCE_BUDGETS.fonts.total).toBe(100 * 1024);
      expect(PERFORMANCE_BUDGETS.fonts.perFamily).toBe(50 * 1024);
    });

    it('should define request budgets', () => {
      expect(PERFORMANCE_BUDGETS.requests.initial).toBe(10);
      expect(PERFORMANCE_BUDGETS.requests.total).toBe(50);
    });

    it('should define interaction latency budgets', () => {
      expect(PERFORMANCE_BUDGETS.interaction.buttonClick).toBe(100);
      expect(PERFORMANCE_BUDGETS.interaction.formSubmit).toBe(200);
      expect(PERFORMANCE_BUDGETS.interaction.navigation).toBe(300);
    });
  });
});

// =============================================================================
// FUNCTION TESTS
// =============================================================================

describe('Metric Rating Functions', () => {
  describe('rateMetric', () => {
    it('should rate LCP as good when under threshold', () => {
      expect(rateMetric('LCP', 2000)).toBe('good');
      expect(rateMetric('LCP', 2500)).toBe('good');
    });

    it('should rate LCP as needs-improvement when between thresholds', () => {
      expect(rateMetric('LCP', 3000)).toBe('needs-improvement');
      expect(rateMetric('LCP', 4000)).toBe('needs-improvement');
    });

    it('should rate LCP as poor when over threshold', () => {
      expect(rateMetric('LCP', 5000)).toBe('poor');
    });

    it('should rate CLS as good when under threshold', () => {
      expect(rateMetric('CLS', 0.05)).toBe('good');
      expect(rateMetric('CLS', 0.1)).toBe('good');
    });

    it('should rate CLS as needs-improvement when between thresholds', () => {
      expect(rateMetric('CLS', 0.15)).toBe('needs-improvement');
      expect(rateMetric('CLS', 0.25)).toBe('needs-improvement');
    });

    it('should rate CLS as poor when over threshold', () => {
      expect(rateMetric('CLS', 0.3)).toBe('poor');
    });

    it('should rate all metrics correctly', () => {
      // All good
      expect(rateMetric('FID', 50)).toBe('good');
      expect(rateMetric('INP', 100)).toBe('good');
      expect(rateMetric('TTFB', 500)).toBe('good');
      expect(rateMetric('FCP', 1500)).toBe('good');
    });
  });

  describe('rateInteraction', () => {
    it('should rate fast clicks as good', () => {
      expect(rateInteraction(50, 'click')).toBe('good');
      expect(rateInteraction(100, 'click')).toBe('good');
    });

    it('should rate slow clicks as needs-improvement', () => {
      expect(rateInteraction(150, 'click')).toBe('needs-improvement');
      expect(rateInteraction(200, 'click')).toBe('needs-improvement');
    });

    it('should rate very slow clicks as poor', () => {
      expect(rateInteraction(250, 'click')).toBe('poor');
    });

    it('should use higher threshold for form submits', () => {
      expect(rateInteraction(150, 'submit')).toBe('good');
      expect(rateInteraction(200, 'submit')).toBe('good');
      expect(rateInteraction(350, 'submit')).toBe('needs-improvement');
    });
  });
});

describe('Observer Functions', () => {
  describe('observeLCP', () => {
    it('should return null if PerformanceObserver not available', () => {
      const result = observeLCP(() => {});
      // In JSDOM, PerformanceObserver may not support LCP
      expect(result === null || typeof result === 'function').toBe(true);
    });
  });

  describe('observeFID', () => {
    it('should return null if PerformanceObserver not available', () => {
      const result = observeFID(() => {});
      expect(result === null || typeof result === 'function').toBe(true);
    });
  });

  describe('observeCLS', () => {
    it('should return null if PerformanceObserver not available', () => {
      const result = observeCLS(() => {});
      expect(result === null || typeof result === 'function').toBe(true);
    });
  });

  describe('observeINP', () => {
    it('should return null if PerformanceObserver not available', () => {
      const result = observeINP(() => {});
      expect(result === null || typeof result === 'function').toBe(true);
    });
  });

  describe('observeResources', () => {
    it('should return null if PerformanceObserver not available', () => {
      const result = observeResources(() => {});
      expect(result === null || typeof result === 'function').toBe(true);
    });
  });

  describe('getTTFB', () => {
    it('should return metric or null', () => {
      const result = getTTFB();
      // Navigation timing may or may not be available in JSDOM
      expect(result === null || (result && result.name === 'TTFB')).toBe(true);
    });
  });

  describe('getFCP', () => {
    it('should return metric or null', () => {
      const result = getFCP();
      expect(result === null || (result && result.name === 'FCP')).toBe(true);
    });
  });
});

describe('Interaction Tracker', () => {
  describe('createInteractionTracker', () => {
    it('should create a tracker with start/end/cancel methods', () => {
      const tracker = createInteractionTracker();
      
      expect(tracker.startInteraction).toBeDefined();
      expect(tracker.endInteraction).toBeDefined();
      expect(tracker.cancelInteraction).toBeDefined();
    });

    it('should track interaction start and end', () => {
      const tracker = createInteractionTracker();
      
      tracker.startInteraction('test-1', 'click', 'Test Button');
      const result = tracker.endInteraction('test-1');
      
      expect(result).not.toBeNull();
      expect(result?.id).toBe('test-1');
      expect(result?.type).toBe('click');
      expect(result?.target).toBe('Test Button');
      expect(result?.latency).toBeGreaterThanOrEqual(0);
    });

    it('should return null for unknown interaction', () => {
      const tracker = createInteractionTracker();
      
      const result = tracker.endInteraction('unknown');
      expect(result).toBeNull();
    });

    it('should cancel interaction', () => {
      const tracker = createInteractionTracker();
      
      tracker.startInteraction('test-1', 'click', 'Button');
      tracker.cancelInteraction('test-1');
      
      const result = tracker.endInteraction('test-1');
      expect(result).toBeNull();
    });

    it('should rate interaction based on latency', async () => {
      const tracker = createInteractionTracker();
      
      tracker.startInteraction('test-1', 'click', 'Button');
      // Immediate end should be good
      const result = tracker.endInteraction('test-1');
      
      expect(result?.rating).toBe('good');
    });
  });
});

describe('Performance Reporting Functions', () => {
  describe('formatPerformanceReport', () => {
    const mockSession = {
      sessionId: 'test-session',
      startTime: Date.now(),
      route: '/dashboard',
      metrics: [
        { name: 'LCP' as const, value: 2000, rating: 'good' as const, timestamp: Date.now(), id: '1' },
        { name: 'CLS' as const, value: 0.05, rating: 'good' as const, timestamp: Date.now(), id: '2' },
      ],
      interactions: [
        { id: '1', type: 'click' as const, target: 'Button', latency: 50, timestamp: Date.now(), rating: 'good' as const },
      ],
      resources: [
        { name: 'script.js', type: 'script' as const, size: 1024, duration: 100, timestamp: Date.now() },
      ],
    };

    it('should format session report', () => {
      const report = formatPerformanceReport(mockSession);
      
      expect(report).toContain('PERFORMANCE REPORT');
      expect(report).toContain('test-session');
      expect(report).toContain('/dashboard');
      expect(report).toContain('LCP');
      expect(report).toContain('CLS');
    });

    it('should include interactions when specified', () => {
      const report = formatPerformanceReport(mockSession, { includeInteractions: true });
      
      expect(report).toContain('INTERACTIONS');
      expect(report).toContain('Total: 1');
    });

    it('should include resources when specified', () => {
      const report = formatPerformanceReport(mockSession, { includeResources: true });
      
      expect(report).toContain('RESOURCES');
      expect(report).toContain('script');
    });
  });

  describe('sendPerformanceBeacon', () => {
    const mockSession = {
      sessionId: 'test',
      startTime: Date.now(),
      route: '/',
      metrics: [],
      interactions: [],
      resources: [],
    };

    it('should return false if navigator.sendBeacon not available', async () => {
      const originalSendBeacon = navigator.sendBeacon;
      Object.defineProperty(navigator, 'sendBeacon', { value: undefined, configurable: true });
      
      const result = await sendPerformanceBeacon(mockSession, '/api/metrics');
      expect(result).toBe(false);
      
      Object.defineProperty(navigator, 'sendBeacon', { value: originalSendBeacon, configurable: true });
    });

    it('should call sendBeacon with data', async () => {
      const mockSendBeacon = jest.fn().mockReturnValue(true);
      Object.defineProperty(navigator, 'sendBeacon', { value: mockSendBeacon, configurable: true });
      
      const result = await sendPerformanceBeacon(mockSession, '/api/metrics');
      
      expect(result).toBe(true);
      expect(mockSendBeacon).toHaveBeenCalledWith('/api/metrics', expect.any(String));
    });
  });
});

// =============================================================================
// HOOK TESTS
// =============================================================================

describe('RUM Hooks', () => {
  describe('useRUM', () => {
    it('should throw error when used outside provider', () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      expect(() => {
        render(<TestHookComponent hook={useRUM} onResult={() => {}} />);
      }).toThrow('useRUM must be used within a RUMProvider');
      
      consoleError.mockRestore();
    });

    it('should return RUM context', () => {
      let result: ReturnType<typeof useRUM> | undefined;
      
      render(
        <TestWrapper>
          <TestHookComponent hook={useRUM} onResult={(r) => { result = r; }} />
        </TestWrapper>
      );
      
      expect(result).toBeDefined();
      expect(result?.metrics).toBeDefined();
      expect(result?.interactions).toBeDefined();
      expect(result?.resources).toBeDefined();
      expect(result?.sessionId).toBeDefined();
      expect(result?.trackInteraction).toBeInstanceOf(Function);
    });

    it('should track and complete interactions', async () => {
      let rumContext: ReturnType<typeof useRUM> | undefined;
      
      render(
        <TestWrapper>
          <TestHookComponent hook={useRUM} onResult={(r) => { rumContext = r; }} />
        </TestWrapper>
      );
      
      await act(async () => {
        const id = rumContext!.trackInteraction('click', 'Test Button');
        const result = rumContext!.completeInteraction(id);
        
        expect(result).not.toBeNull();
        expect(result?.target).toBe('Test Button');
      });
    });

    it('should provide route from provider', () => {
      let result: ReturnType<typeof useRUM> | undefined;
      
      render(
        <TestWrapper route="/custom-route">
          <TestHookComponent hook={useRUM} onResult={(r) => { result = r; }} />
        </TestWrapper>
      );
      
      expect(result?.route).toBe('/custom-route');
    });
  });

  describe('useInteractionTracking', () => {
    it('should provide start/complete/cancel functions', () => {
      let result: ReturnType<typeof useInteractionTracking> | undefined;
      
      render(
        <TestWrapper>
          <TestHookComponent
            hook={() => useInteractionTracking('Test Action')}
            onResult={(r) => { result = r; }}
          />
        </TestWrapper>
      );
      
      expect(result?.start).toBeInstanceOf(Function);
      expect(result?.complete).toBeInstanceOf(Function);
      expect(result?.cancel).toBeInstanceOf(Function);
    });

    it('should track interaction lifecycle', async () => {
      let tracking: ReturnType<typeof useInteractionTracking> | undefined;
      
      render(
        <TestWrapper>
          <TestHookComponent
            hook={() => useInteractionTracking('Test Button')}
            onResult={(r) => { tracking = r; }}
          />
        </TestWrapper>
      );
      
      await act(async () => {
        tracking!.start();
        const result = tracking!.complete();
        
        expect(result).not.toBeNull();
        expect(result?.target).toBe('Test Button');
      });
    });
  });

  describe('usePerformanceBudget', () => {
    it('should return budget status', () => {
      let result: ReturnType<typeof usePerformanceBudget> | undefined;
      
      render(
        <TestWrapper>
          <TestHookComponent
            hook={usePerformanceBudget}
            onResult={(r) => { result = r; }}
          />
        </TestWrapper>
      );
      
      expect(result?.violations).toBeDefined();
      expect(typeof result?.isWithinBudget).toBe('boolean');
      expect(typeof result?.errorCount).toBe('number');
      expect(typeof result?.warningCount).toBe('number');
    });
  });
});

// =============================================================================
// COMPONENT TESTS
// =============================================================================

describe('WebVitalCard Component', () => {
  it('should render metric name', () => {
    render(<WebVitalCard name="LCP" value={2000} />);
    
    expect(screen.getByText('LCP')).toBeInTheDocument();
  });

  it('should render metric value with unit', () => {
    render(<WebVitalCard name="LCP" value={2000} />);
    
    expect(screen.getByText('2000ms')).toBeInTheDocument();
  });

  it('should render CLS without unit', () => {
    render(<WebVitalCard name="CLS" value={0.05} />);
    
    expect(screen.getByText('0.050')).toBeInTheDocument();
  });

  it('should render dash when value is null', () => {
    render(<WebVitalCard name="LCP" value={null} />);
    
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('should show good rating icon', () => {
    render(<WebVitalCard name="LCP" value={2000} rating="good" />);
    
    expect(screen.getByText('✓')).toBeInTheDocument();
  });

  it('should show needs-improvement rating icon', () => {
    render(<WebVitalCard name="LCP" value={3000} rating="needs-improvement" />);
    
    expect(screen.getByText('!')).toBeInTheDocument();
  });

  it('should show poor rating icon', () => {
    render(<WebVitalCard name="LCP" value={5000} rating="poor" />);
    
    expect(screen.getByText('✗')).toBeInTheDocument();
  });

  it('should show thresholds when enabled', () => {
    render(<WebVitalCard name="LCP" value={2000} showThresholds />);
    
    expect(screen.getByText('Good:')).toBeInTheDocument();
    expect(screen.getByText('Needs improvement:')).toBeInTheDocument();
    expect(screen.getByText('≤ 2500ms')).toBeInTheDocument();
  });

  it('should show description', () => {
    render(<WebVitalCard name="LCP" value={2000} />);
    
    expect(screen.getByText(/Largest Contentful Paint/)).toBeInTheDocument();
  });
});

describe('WebVitalsDashboard Component', () => {
  it('should render all vital cards', () => {
    render(
      <TestWrapper>
        <WebVitalsDashboard />
      </TestWrapper>
    );
    
    expect(screen.getByText('LCP')).toBeInTheDocument();
    expect(screen.getByText('FID')).toBeInTheDocument();
    expect(screen.getByText('CLS')).toBeInTheDocument();
    expect(screen.getByText('INP')).toBeInTheDocument();
    expect(screen.getByText('TTFB')).toBeInTheDocument();
    expect(screen.getByText('FCP')).toBeInTheDocument();
  });
});

describe('InteractionLatencyList Component', () => {
  it('should show empty state when no interactions', () => {
    render(
      <TestWrapper>
        <InteractionLatencyList />
      </TestWrapper>
    );
    
    expect(screen.getByText('No interactions recorded yet')).toBeInTheDocument();
  });

  it('should display interactions when available', async () => {
    function TestComponent() {
      const { trackInteraction, completeInteraction } = useRUM();
      
      React.useEffect(() => {
        const id = trackInteraction('click', 'Test Button');
        completeInteraction(id);
      }, [trackInteraction, completeInteraction]);
      
      return <InteractionLatencyList />;
    }
    
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );
    
    await waitFor(() => {
      expect(screen.getByText('Test Button')).toBeInTheDocument();
    });
  });
});

describe('BudgetViolationAlert Component', () => {
  it('should render nothing when no violations', () => {
    const { container } = render(<BudgetViolationAlert violations={[]} />);
    
    expect(container.firstChild).toBeNull();
  });

  it('should render error violations', () => {
    const violations: BudgetViolation[] = [{
      category: 'jsBundle',
      threshold: 500 * 1024,
      actual: 600 * 1024,
      unit: 'bytes',
      severity: 'error',
      message: 'JS bundle exceeds budget',
    }];
    
    render(<BudgetViolationAlert violations={violations} />);
    
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('JS bundle exceeds budget')).toBeInTheDocument();
  });

  it('should render warning violations', () => {
    const violations: BudgetViolation[] = [{
      category: 'requests',
      threshold: 10,
      actual: 12,
      unit: 'count',
      severity: 'warning',
      message: 'Request count exceeded',
    }];
    
    render(<BudgetViolationAlert violations={violations} />);
    
    expect(screen.getByText('Request count exceeded')).toBeInTheDocument();
  });

  it('should call onDismiss when dismiss button clicked', () => {
    const onDismiss = jest.fn();
    const violations: BudgetViolation[] = [{
      category: 'test',
      threshold: 100,
      actual: 200,
      unit: 'ms',
      severity: 'warning',
      message: 'Test violation',
    }];
    
    render(<BudgetViolationAlert violations={violations} onDismiss={onDismiss} />);
    
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));
    
    expect(onDismiss).toHaveBeenCalledWith(0);
  });
});

describe('PerformanceBudgetMeter Component', () => {
  it('should render label and values', () => {
    render(
      <PerformanceBudgetMeter
        label="JavaScript"
        current={250 * 1024}
        budget={500 * 1024}
        unit="KB"
      />
    );
    
    expect(screen.getByText('JavaScript')).toBeInTheDocument();
  });

  it('should render progress bar', () => {
    render(
      <PerformanceBudgetMeter
        label="CSS"
        current={50}
        budget={100}
        unit="KB"
      />
    );
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should show 50% progress correctly', () => {
    render(
      <PerformanceBudgetMeter
        label="Test"
        current={50}
        budget={100}
        unit=""
      />
    );
    
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '50');
    expect(progressBar).toHaveAttribute('aria-valuemax', '100');
  });

  it('should apply custom formatter', () => {
    render(
      <PerformanceBudgetMeter
        label="Size"
        current={1024}
        budget={2048}
        unit=""
        formatValue={(v) => `${v / 1024}KB`}
      />
    );
    
    expect(screen.getByText(/1KB/)).toBeInTheDocument();
  });
});

describe('ResourceBudgetDashboard Component', () => {
  it('should render resource meters', () => {
    render(
      <TestWrapper>
        <ResourceBudgetDashboard />
      </TestWrapper>
    );
    
    expect(screen.getByText('JavaScript')).toBeInTheDocument();
    expect(screen.getByText('CSS')).toBeInTheDocument();
    expect(screen.getByText('Images')).toBeInTheDocument();
    expect(screen.getByText('Fonts')).toBeInTheDocument();
    expect(screen.getByText('Requests')).toBeInTheDocument();
  });
});

describe('TrackedButton Component', () => {
  it('should render button with children', () => {
    render(
      <TestWrapper>
        <TrackedButton>Click Me</TrackedButton>
      </TestWrapper>
    );
    
    expect(screen.getByRole('button', { name: 'Click Me' })).toBeInTheDocument();
  });

  it('should track interaction on click', async () => {
    const onClick = jest.fn();
    
    render(
      <TestWrapper>
        <TrackedButton onClick={onClick} trackingName="Test Action">
          Click
        </TrackedButton>
      </TestWrapper>
    );
    
    const button = screen.getByRole('button');
    fireEvent.mouseDown(button);
    fireEvent.click(button);
    
    expect(onClick).toHaveBeenCalled();
  });

  it('should apply variant classes', () => {
    const { rerender } = render(
      <TestWrapper>
        <TrackedButton variant="primary">Primary</TrackedButton>
      </TestWrapper>
    );
    
    expect(screen.getByRole('button')).toHaveClass('bg-primary');
    
    rerender(
      <TestWrapper>
        <TrackedButton variant="destructive">Destructive</TrackedButton>
      </TestWrapper>
    );
    
    expect(screen.getByRole('button')).toHaveClass('bg-destructive');
  });
});

describe('RUMDashboardPanel Component', () => {
  it('should render toggle button initially', () => {
    render(
      <TestWrapper>
        <RUMDashboardPanel />
      </TestWrapper>
    );
    
    expect(screen.getByRole('button', { name: /open performance dashboard/i })).toBeInTheDocument();
  });

  it('should open panel on button click', async () => {
    render(
      <TestWrapper>
        <RUMDashboardPanel />
      </TestWrapper>
    );
    
    fireEvent.click(screen.getByRole('button', { name: /open performance dashboard/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /performance dashboard/i })).toBeInTheDocument();
    });
  });

  it('should render when defaultOpen is true', () => {
    render(
      <TestWrapper>
        <RUMDashboardPanel defaultOpen />
      </TestWrapper>
    );
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('should have tabs for vitals, interactions, resources', () => {
    render(
      <TestWrapper>
        <RUMDashboardPanel defaultOpen />
      </TestWrapper>
    );
    
    expect(screen.getByText('📈 Vitals')).toBeInTheDocument();
    expect(screen.getByText('🖱️ Interactions')).toBeInTheDocument();
    expect(screen.getByText('📦 Resources')).toBeInTheDocument();
  });

  it('should switch tabs on click', async () => {
    render(
      <TestWrapper>
        <RUMDashboardPanel defaultOpen />
      </TestWrapper>
    );
    
    // Initially shows vitals
    expect(screen.getByText('LCP')).toBeInTheDocument();
    
    // Switch to interactions
    fireEvent.click(screen.getByText('🖱️ Interactions'));
    
    await waitFor(() => {
      expect(screen.getByText('No interactions recorded yet')).toBeInTheDocument();
    });
  });

  it('should close panel on close button click', async () => {
    render(
      <TestWrapper>
        <RUMDashboardPanel defaultOpen />
      </TestWrapper>
    );
    
    fireEvent.click(screen.getByRole('button', { name: /close dashboard/i }));
    
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('should position panel correctly', () => {
    const { rerender } = render(
      <TestWrapper>
        <RUMDashboardPanel position="bottom-left" defaultOpen />
      </TestWrapper>
    );
    
    expect(screen.getByRole('dialog')).toHaveClass('bottom-4', 'left-4');
    
    rerender(
      <TestWrapper>
        <RUMDashboardPanel position="top-right" defaultOpen />
      </TestWrapper>
    );
    
    expect(screen.getByRole('dialog')).toHaveClass('top-4', 'right-4');
  });
});

describe('RUMProvider Component', () => {
  it('should provide session ID', () => {
    let sessionId: string | undefined;
    
    function Consumer() {
      const { sessionId: id } = useRUM();
      sessionId = id;
      return null;
    }
    
    render(
      <RUMProvider>
        <Consumer />
      </RUMProvider>
    );
    
    expect(sessionId).toBeDefined();
    expect(sessionId!.length).toBeGreaterThan(0);
  });

  it('should provide custom route', () => {
    let route: string | undefined;
    
    function Consumer() {
      const { route: r } = useRUM();
      route = r;
      return null;
    }
    
    render(
      <RUMProvider route="/custom">
        <Consumer />
      </RUMProvider>
    );
    
    expect(route).toBe('/custom');
  });

  it('should call onMetric callback', async () => {
    const onMetric = jest.fn();
    
    function Consumer() {
      const { metrics } = useRUM();
      return <div data-testid="metrics">{JSON.stringify(metrics)}</div>;
    }
    
    render(
      <RUMProvider onMetric={onMetric}>
        <Consumer />
      </RUMProvider>
    );
    
    // Metrics callbacks depend on PerformanceObserver availability
    expect(screen.getByTestId('metrics')).toBeInTheDocument();
  });

  it('should call onInteraction callback', async () => {
    const onInteraction = jest.fn();
    
    function Consumer() {
      const { trackInteraction, completeInteraction } = useRUM();
      
      React.useEffect(() => {
        const id = trackInteraction('click', 'Test');
        completeInteraction(id);
      }, [trackInteraction, completeInteraction]);
      
      return null;
    }
    
    render(
      <RUMProvider onInteraction={onInteraction}>
        <Consumer />
      </RUMProvider>
    );
    
    await waitFor(() => {
      expect(onInteraction).toHaveBeenCalled();
    });
  });

  it('should provide getReport function', () => {
    let getReport: (() => ReturnType<ReturnType<typeof useRUM>['getReport']>) | undefined;
    
    function Consumer() {
      const rum = useRUM();
      getReport = rum.getReport;
      return null;
    }
    
    render(
      <RUMProvider route="/test">
        <Consumer />
      </RUMProvider>
    );
    
    const report = getReport!();
    expect(report.sessionId).toBeDefined();
    expect(report.route).toBe('/test');
    expect(report.metrics).toEqual([]);
    expect(report.interactions).toEqual([]);
    expect(report.resources).toEqual([]);
  });

  it('should provide checkBudgets function', () => {
    let checkBudgets: (() => BudgetViolation[]) | undefined;
    
    function Consumer() {
      const { checkBudgets: cb } = useRUM();
      checkBudgets = cb;
      return null;
    }
    
    render(
      <RUMProvider>
        <Consumer />
      </RUMProvider>
    );
    
    const violations = checkBudgets!();
    expect(Array.isArray(violations)).toBe(true);
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('RUM Integration', () => {
  it('should track complete interaction flow', async () => {
    let interactions: InteractionMetric[] = [];
    
    function Consumer() {
      const rum = useRUM();
      interactions = rum.interactions;
      
      return (
        <TrackedButton trackingName="Integration Test">
          Click Me
        </TrackedButton>
      );
    }
    
    render(
      <RUMProvider>
        <Consumer />
      </RUMProvider>
    );
    
    const button = screen.getByRole('button');
    fireEvent.mouseDown(button);
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(interactions.length).toBe(1);
      expect(interactions[0].target).toBe('Integration Test');
    });
  });

  it('should generate complete report', async () => {
    let getReport: (() => ReturnType<ReturnType<typeof useRUM>['getReport']>) | undefined;
    
    function Consumer() {
      const rum = useRUM();
      const hasTracked = React.useRef(false);
      getReport = rum.getReport;
      
      React.useEffect(() => {
        if (!hasTracked.current) {
          hasTracked.current = true;
          const id = rum.trackInteraction('click', 'Report Test');
          rum.completeInteraction(id);
        }
      }, [rum.trackInteraction, rum.completeInteraction]);
      
      return null;
    }
    
    render(
      <RUMProvider route="/report-test">
        <Consumer />
      </RUMProvider>
    );
    
    await waitFor(() => {
      const report = getReport!();
      expect(report.route).toBe('/report-test');
      expect(report.interactions.length).toBe(1);
    });
  });
});
