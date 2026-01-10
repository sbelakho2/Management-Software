import React, { useRef } from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import {
  // Constants
  COLOR_TOKENS,
  SPACING_TOKENS,
  TYPOGRAPHY_TOKENS,
  RADIUS_TOKENS,
  SHADOW_TOKENS,
  ANIMATION_TOKENS,
  BREAKPOINT_TOKENS,
  VISUAL_WEIGHTS,
  INTERACTION_PATTERNS,
  CLS_THRESHOLDS,
  GOLD_STANDARD_STATES,
  // Types
  ColorToken,
  SpacingToken,
  FontSizeToken,
  RadiusToken,
  ShadowToken,
  // Functions
  validateCssVariable,
  auditColorTokens,
  getTokenValue,
  createComponentAudit,
  buildInteractionClasses,
  observeCLS,
  generateVisualSnapshotTest,
  generateVisualRegressionTestFile,
  checkDesignConsistency,
  // Hooks
  useDesignSystem,
  useVisualWeight,
  useCLSMonitor,
  useDesignConsistencyCheck,
  // Components
  DesignSystemProvider,
  ColorSwatch,
  SpacingScale,
  TypographyScale,
  TokenDocumentation,
  DesignAuditPanel,
  CLSIndicator,
} from '../design-system';

// =============================================================================
// TEST UTILITIES
// =============================================================================

function TestWrapper({ children }: { children: React.ReactNode }) {
  return <DesignSystemProvider>{children}</DesignSystemProvider>;
}

// Helper to use hooks in tests
function TestHookComponent({ hook, onResult }: { hook: () => unknown; onResult: (result: unknown) => void }) {
  const result = hook();
  React.useEffect(() => {
    onResult(result);
  }, [result, onResult]);
  return null;
}

// =============================================================================
// CONSTANT TESTS
// =============================================================================

describe('Design Token Constants', () => {
  describe('COLOR_TOKENS', () => {
    it('should define all semantic color tokens', () => {
      expect(COLOR_TOKENS.background).toBe('--background');
      expect(COLOR_TOKENS.foreground).toBe('--foreground');
      expect(COLOR_TOKENS.primary).toBe('--primary');
      expect(COLOR_TOKENS.secondary).toBe('--secondary');
      expect(COLOR_TOKENS.muted).toBe('--muted');
      expect(COLOR_TOKENS.accent).toBe('--accent');
      expect(COLOR_TOKENS.destructive).toBe('--destructive');
    });

    it('should define all status color tokens', () => {
      expect(COLOR_TOKENS.success).toBe('--success');
      expect(COLOR_TOKENS.warning).toBe('--warning');
      expect(COLOR_TOKENS.danger).toBe('--danger');
    });

    it('should define foreground variants for colors', () => {
      expect(COLOR_TOKENS['primary-foreground']).toBe('--primary-foreground');
      expect(COLOR_TOKENS['secondary-foreground']).toBe('--secondary-foreground');
      expect(COLOR_TOKENS['card-foreground']).toBe('--card-foreground');
    });

    it('should define UI element tokens', () => {
      expect(COLOR_TOKENS.border).toBe('--border');
      expect(COLOR_TOKENS.input).toBe('--input');
      expect(COLOR_TOKENS.ring).toBe('--ring');
    });
  });

  describe('SPACING_TOKENS', () => {
    it('should define base spacing values', () => {
      expect(SPACING_TOKENS[0]).toBe('0px');
      expect(SPACING_TOKENS[1]).toBe('0.25rem');
      expect(SPACING_TOKENS[2]).toBe('0.5rem');
      expect(SPACING_TOKENS[4]).toBe('1rem');
    });

    it('should define larger spacing values', () => {
      expect(SPACING_TOKENS[8]).toBe('2rem');
      expect(SPACING_TOKENS[16]).toBe('4rem');
      expect(SPACING_TOKENS[32]).toBe('8rem');
      expect(SPACING_TOKENS[64]).toBe('16rem');
    });

    it('should define custom spacing values', () => {
      expect(SPACING_TOKENS[4.5]).toBe('1.125rem');
      expect(SPACING_TOKENS[5.5]).toBe('1.375rem');
      expect(SPACING_TOKENS[18]).toBe('4.5rem');
      expect(SPACING_TOKENS[22]).toBe('5.5rem');
    });

    it('should define pixel spacing', () => {
      expect(SPACING_TOKENS.px).toBe('1px');
    });
  });

  describe('TYPOGRAPHY_TOKENS', () => {
    it('should define font families', () => {
      expect(TYPOGRAPHY_TOKENS.fontFamily.sans).toContain('var(--font-sans)');
      expect(TYPOGRAPHY_TOKENS.fontFamily.mono).toContain('var(--font-mono)');
    });

    it('should define font sizes', () => {
      expect(TYPOGRAPHY_TOKENS.fontSize['2xs']).toBe('0.625rem');
      expect(TYPOGRAPHY_TOKENS.fontSize.xs).toBe('0.75rem');
      expect(TYPOGRAPHY_TOKENS.fontSize.sm).toBe('0.875rem');
      expect(TYPOGRAPHY_TOKENS.fontSize.base).toBe('1rem');
      expect(TYPOGRAPHY_TOKENS.fontSize.lg).toBe('1.125rem');
    });

    it('should define font weights', () => {
      expect(TYPOGRAPHY_TOKENS.fontWeight.normal).toBe('400');
      expect(TYPOGRAPHY_TOKENS.fontWeight.medium).toBe('500');
      expect(TYPOGRAPHY_TOKENS.fontWeight.semibold).toBe('600');
      expect(TYPOGRAPHY_TOKENS.fontWeight.bold).toBe('700');
    });

    it('should define line heights', () => {
      expect(TYPOGRAPHY_TOKENS.lineHeight.none).toBe('1');
      expect(TYPOGRAPHY_TOKENS.lineHeight.normal).toBe('1.5');
      expect(TYPOGRAPHY_TOKENS.lineHeight.loose).toBe('2');
    });
  });

  describe('RADIUS_TOKENS', () => {
    it('should define border radius values', () => {
      expect(RADIUS_TOKENS.none).toBe('0px');
      expect(RADIUS_TOKENS.sm).toBe('calc(var(--radius) - 4px)');
      expect(RADIUS_TOKENS.md).toBe('calc(var(--radius) - 2px)');
      expect(RADIUS_TOKENS.lg).toBe('var(--radius)');
      expect(RADIUS_TOKENS.full).toBe('9999px');
    });
  });

  describe('SHADOW_TOKENS', () => {
    it('should define elevation shadows', () => {
      expect(SHADOW_TOKENS['elevation-1']).toContain('0 1px 2px');
      expect(SHADOW_TOKENS['elevation-2']).toContain('0 1px 3px');
      expect(SHADOW_TOKENS['elevation-3']).toContain('0 4px 6px');
    });

    it('should define semantic shadows', () => {
      expect(SHADOW_TOKENS.sm).toBeDefined();
      expect(SHADOW_TOKENS.DEFAULT).toBeDefined();
      expect(SHADOW_TOKENS.md).toBeDefined();
      expect(SHADOW_TOKENS.lg).toBeDefined();
      expect(SHADOW_TOKENS.xl).toBeDefined();
    });

    it('should define special shadows', () => {
      expect(SHADOW_TOKENS.inner).toContain('inset');
      expect(SHADOW_TOKENS.none).toBe('0 0 #0000');
    });
  });

  describe('ANIMATION_TOKENS', () => {
    it('should define durations', () => {
      expect(ANIMATION_TOKENS.duration.fast).toBe('100ms');
      expect(ANIMATION_TOKENS.duration.normal).toBe('200ms');
      expect(ANIMATION_TOKENS.duration.slow).toBe('300ms');
      expect(ANIMATION_TOKENS.duration.slower).toBe('500ms');
    });

    it('should define easings', () => {
      expect(ANIMATION_TOKENS.easing.linear).toBe('linear');
      expect(ANIMATION_TOKENS.easing.in).toContain('cubic-bezier');
      expect(ANIMATION_TOKENS.easing.out).toContain('cubic-bezier');
      expect(ANIMATION_TOKENS.easing['in-out']).toContain('cubic-bezier');
    });
  });

  describe('BREAKPOINT_TOKENS', () => {
    it('should define responsive breakpoints', () => {
      expect(BREAKPOINT_TOKENS.sm).toBe('640px');
      expect(BREAKPOINT_TOKENS.md).toBe('768px');
      expect(BREAKPOINT_TOKENS.lg).toBe('1024px');
      expect(BREAKPOINT_TOKENS.xl).toBe('1280px');
      expect(BREAKPOINT_TOKENS['2xl']).toBe('1536px');
    });
  });

  describe('VISUAL_WEIGHTS', () => {
    it('should define small visual weight', () => {
      expect(VISUAL_WEIGHTS.small.padding).toBe(2);
      expect(VISUAL_WEIGHTS.small.fontSize).toBe('sm');
      expect(VISUAL_WEIGHTS.small.fontWeight).toBe('medium');
    });

    it('should define medium visual weight', () => {
      expect(VISUAL_WEIGHTS.medium.padding).toBe(4);
      expect(VISUAL_WEIGHTS.medium.fontSize).toBe('base');
    });

    it('should define large visual weight', () => {
      expect(VISUAL_WEIGHTS.large.padding).toBe(6);
      expect(VISUAL_WEIGHTS.large.fontSize).toBe('lg');
      expect(VISUAL_WEIGHTS.large.fontWeight).toBe('semibold');
    });
  });

  describe('INTERACTION_PATTERNS', () => {
    it('should define button patterns', () => {
      expect(INTERACTION_PATTERNS.button.hover).toContain('hover:');
      expect(INTERACTION_PATTERNS.button.active).toContain('active:');
      expect(INTERACTION_PATTERNS.button.focus).toContain('focus-visible:');
      expect(INTERACTION_PATTERNS.button.disabled).toContain('disabled:');
    });

    it('should define input patterns', () => {
      expect(INTERACTION_PATTERNS.input.hover).toContain('hover:');
      expect(INTERACTION_PATTERNS.input.focus).toContain('focus:');
      expect(INTERACTION_PATTERNS.input.error).toContain('destructive');
    });

    it('should define card patterns', () => {
      expect(INTERACTION_PATTERNS.card.hover).toContain('hover:');
      expect(INTERACTION_PATTERNS.card.transition).toContain('transition');
    });

    it('should define link patterns', () => {
      expect(INTERACTION_PATTERNS.link.hover).toContain('underline');
    });
  });

  describe('CLS_THRESHOLDS', () => {
    it('should define good threshold at 0.1', () => {
      expect(CLS_THRESHOLDS.good).toBe(0.1);
    });

    it('should define needs improvement threshold at 0.25', () => {
      expect(CLS_THRESHOLDS.needsImprovement).toBe(0.25);
    });
  });

  describe('GOLD_STANDARD_STATES', () => {
    it('should define gold standard states for visual regression', () => {
      expect(GOLD_STANDARD_STATES.length).toBeGreaterThan(0);
      
      const dashboardState = GOLD_STANDARD_STATES.find(s => s.name === 'dashboard-default');
      expect(dashboardState).toBeDefined();
      expect(dashboardState?.route).toBe('/');
    });

    it('should include mobile and dark mode variants', () => {
      const mobileState = GOLD_STANDARD_STATES.find(s => s.name.includes('mobile'));
      const darkState = GOLD_STANDARD_STATES.find(s => s.name.includes('dark'));
      
      expect(mobileState).toBeDefined();
      expect(darkState).toBeDefined();
      expect(darkState?.config.theme).toBe('dark');
    });
  });
});

// =============================================================================
// FUNCTION TESTS
// =============================================================================

describe('Token Validation Functions', () => {
  describe('validateCssVariable', () => {
    beforeEach(() => {
      // Set up CSS variables for testing
      document.documentElement.style.setProperty('--test-color', '221 83% 53%');
      document.documentElement.style.setProperty('--background', '0 0% 100%');
    });

    afterEach(() => {
      document.documentElement.style.removeProperty('--test-color');
      document.documentElement.style.removeProperty('--background');
    });

    it('should validate existing CSS variable', () => {
      const result = validateCssVariable('--test-color');
      expect(result.isValid).toBe(true);
      expect(result.value).toBe('221 83% 53%');
      expect(result.error).toBeUndefined();
    });

    it('should return invalid for undefined variable', () => {
      const result = validateCssVariable('--nonexistent-var');
      expect(result.isValid).toBe(false);
      expect(result.value).toBeNull();
      expect(result.error).toContain('not defined');
    });
  });

  describe('auditColorTokens', () => {
    beforeEach(() => {
      // Set up required CSS variables
      Object.values(COLOR_TOKENS).forEach(variable => {
        document.documentElement.style.setProperty(variable, '0 0% 50%');
      });
    });

    afterEach(() => {
      Object.values(COLOR_TOKENS).forEach(variable => {
        document.documentElement.style.removeProperty(variable);
      });
    });

    it('should return a complete audit report', () => {
      const report = auditColorTokens();
      
      expect(report.timestamp).toBeInstanceOf(Date);
      expect(report.totalTokens).toBe(Object.keys(COLOR_TOKENS).length);
      expect(report.results).toHaveLength(Object.keys(COLOR_TOKENS).length);
    });

    it('should count valid and invalid tokens', () => {
      const report = auditColorTokens();
      
      expect(report.validTokens + report.invalidTokens).toBe(report.totalTokens);
    });

    it('should list missing tokens', () => {
      // Remove one token
      document.documentElement.style.removeProperty('--primary');
      
      const report = auditColorTokens();
      expect(report.missingTokens).toContain('primary');
    });
  });

  describe('getTokenValue', () => {
    beforeEach(() => {
      document.documentElement.style.setProperty('--primary', '221 83% 53%');
    });

    afterEach(() => {
      document.documentElement.style.removeProperty('--primary');
    });

    it('should return token value for defined token', () => {
      const value = getTokenValue('primary');
      expect(value).toBe('221 83% 53%');
    });

    it('should return null for undefined token', () => {
      document.documentElement.style.removeProperty('--primary');
      const value = getTokenValue('primary');
      expect(value).toBeNull();
    });
  });
});

describe('Component Audit Functions', () => {
  describe('createComponentAudit', () => {
    it('should create audit item with no issues when all flags true', () => {
      const audit = createComponentAudit({
        name: 'Button',
        path: '/components/ui/button.tsx',
        category: 'primitive',
        hasTokens: true,
        hasAccessibility: true,
        hasResponsive: true,
        hasAnimation: true,
      });

      expect(audit.name).toBe('Button');
      expect(audit.issues).toHaveLength(0);
    });

    it('should add issue for missing tokens', () => {
      const audit = createComponentAudit({
        name: 'Card',
        path: '/components/ui/card.tsx',
        category: 'composite',
        hasTokens: false,
        hasAccessibility: true,
        hasResponsive: true,
        hasAnimation: false,
      });

      expect(audit.issues).toContain('Component does not use design tokens for styling');
    });

    it('should add issue for missing accessibility', () => {
      const audit = createComponentAudit({
        name: 'Modal',
        path: '/components/ui/modal.tsx',
        category: 'feedback',
        hasTokens: true,
        hasAccessibility: false,
        hasResponsive: true,
        hasAnimation: true,
      });

      expect(audit.issues).toContain('Component lacks proper accessibility attributes');
    });

    it('should add issue for missing responsive design', () => {
      const audit = createComponentAudit({
        name: 'Table',
        path: '/components/ui/table.tsx',
        category: 'data-display',
        hasTokens: true,
        hasAccessibility: true,
        hasResponsive: false,
        hasAnimation: false,
      });

      expect(audit.issues).toContain('Component does not have responsive design');
    });
  });
});

describe('Interaction Pattern Functions', () => {
  describe('buildInteractionClasses', () => {
    it('should build all button classes by default', () => {
      const classes = buildInteractionClasses('button');
      
      expect(classes).toContain('hover:opacity-90');
      expect(classes).toContain('active:scale-[0.98]');
      expect(classes).toContain('focus-visible:');
      expect(classes).toContain('disabled:');
      expect(classes).toContain('transition-');
    });

    it('should exclude hover when disabled', () => {
      const classes = buildInteractionClasses('button', { hover: false });
      
      expect(classes).not.toContain('hover:opacity-90');
    });

    it('should exclude focus when disabled', () => {
      const classes = buildInteractionClasses('input', { focus: false });
      
      expect(classes).not.toContain('focus:');
    });

    it('should build link classes', () => {
      const classes = buildInteractionClasses('link');
      
      expect(classes).toContain('hover:underline');
    });

    it('should build card classes', () => {
      const classes = buildInteractionClasses('card');
      
      expect(classes).toContain('hover:shadow-elevation-2');
    });
  });
});

describe('Visual Regression Functions', () => {
  describe('generateVisualSnapshotTest', () => {
    it('should generate Playwright test code', () => {
      const state = GOLD_STANDARD_STATES[0];
      const testCode = generateVisualSnapshotTest(state);
      
      expect(testCode).toContain('test(');
      expect(testCode).toContain('await page.goto');
      expect(testCode).toContain('toHaveScreenshot');
    });

    it('should include viewport settings when specified', () => {
      const state = GOLD_STANDARD_STATES.find(s => s.config.viewport);
      const testCode = generateVisualSnapshotTest(state!);
      
      expect(testCode).toContain('setViewportSize');
    });

    it('should include theme when specified', () => {
      const darkState = GOLD_STANDARD_STATES.find(s => s.config.theme === 'dark');
      const testCode = generateVisualSnapshotTest(darkState!);
      
      expect(testCode).toContain("emulateMedia");
      expect(testCode).toContain("colorScheme: 'dark'");
    });
  });

  describe('generateVisualRegressionTestFile', () => {
    it('should generate complete test file', () => {
      const fileContent = generateVisualRegressionTestFile();
      
      expect(fileContent).toContain("import { test, expect } from '@playwright/test'");
      expect(fileContent).toContain('Visual Regression Tests');
      GOLD_STANDARD_STATES.forEach(state => {
        expect(fileContent).toContain(state.name);
      });
    });
  });
});

describe('Design Consistency Functions', () => {
  describe('checkDesignConsistency', () => {
    it('should detect hardcoded colors', () => {
      const element = document.createElement('div');
      element.style.backgroundColor = '#ff0000';
      
      const issues = checkDesignConsistency(element);
      
      expect(issues.some(i => i.type === 'hardcoded-color')).toBe(true);
    });

    it('should detect hardcoded spacing', () => {
      const element = document.createElement('div');
      element.style.padding = '15px';
      
      const issues = checkDesignConsistency(element);
      
      expect(issues.some(i => i.type === 'non-token-spacing')).toBe(true);
    });

    it('should not flag CSS variable usage', () => {
      const element = document.createElement('div');
      element.style.backgroundColor = 'hsl(var(--primary))';
      
      const issues = checkDesignConsistency(element);
      
      expect(issues.filter(i => i.type === 'hardcoded-color')).toHaveLength(0);
    });

    it('should check children recursively', () => {
      const parent = document.createElement('div');
      const child = document.createElement('span');
      child.style.color = '#00ff00';
      parent.appendChild(child);
      
      const issues = checkDesignConsistency(parent);
      
      expect(issues.some(i => i.type === 'hardcoded-color')).toBe(true);
    });

    it('should return no issues for clean elements', () => {
      const element = document.createElement('div');
      element.className = 'bg-primary p-4 text-foreground';
      
      const issues = checkDesignConsistency(element);
      
      expect(issues).toHaveLength(0);
    });
  });
});

// =============================================================================
// HOOK TESTS
// =============================================================================

describe('Design System Hooks', () => {
  describe('useDesignSystem', () => {
    it('should throw error when used outside provider', () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      expect(() => {
        render(<TestHookComponent hook={useDesignSystem} onResult={() => {}} />);
      }).toThrow('useDesignSystem must be used within a DesignSystemProvider');
      
      consoleError.mockRestore();
    });

    it('should return design system context', () => {
      let result: ReturnType<typeof useDesignSystem> | undefined;
      
      render(
        <TestWrapper>
          <TestHookComponent
            hook={useDesignSystem}
            onResult={(r) => { result = r as ReturnType<typeof useDesignSystem>; }}
          />
        </TestWrapper>
      );
      
      expect(result).toBeDefined();
      expect(result?.tokens).toBeDefined();
      expect(result?.tokens.colors).toBe(COLOR_TOKENS);
      expect(result?.setTheme).toBeInstanceOf(Function);
    });

    it('should provide theme state', () => {
      let result: ReturnType<typeof useDesignSystem> | undefined;
      
      render(
        <DesignSystemProvider defaultTheme="dark">
          <TestHookComponent
            hook={useDesignSystem}
            onResult={(r) => { result = r as ReturnType<typeof useDesignSystem>; }}
          />
        </DesignSystemProvider>
      );
      
      expect(result?.theme).toBe('dark');
    });
  });

  describe('useVisualWeight', () => {
    it('should return small visual weight', () => {
      let result: ReturnType<typeof useVisualWeight> | undefined;
      
      render(
        <TestHookComponent
          hook={() => useVisualWeight('small')}
          onResult={(r) => { result = r as ReturnType<typeof useVisualWeight>; }}
        />
      );
      
      expect(result).toEqual(VISUAL_WEIGHTS.small);
    });

    it('should return medium visual weight', () => {
      let result: ReturnType<typeof useVisualWeight> | undefined;
      
      render(
        <TestHookComponent
          hook={() => useVisualWeight('medium')}
          onResult={(r) => { result = r as ReturnType<typeof useVisualWeight>; }}
        />
      );
      
      expect(result).toEqual(VISUAL_WEIGHTS.medium);
    });

    it('should return large visual weight', () => {
      let result: ReturnType<typeof useVisualWeight> | undefined;
      
      render(
        <TestHookComponent
          hook={() => useVisualWeight('large')}
          onResult={(r) => { result = r as ReturnType<typeof useVisualWeight>; }}
        />
      );
      
      expect(result).toEqual(VISUAL_WEIGHTS.large);
    });
  });

  describe('useCLSMonitor', () => {
    it('should return null initially (PerformanceObserver may not be available)', () => {
      let result: ReturnType<typeof useCLSMonitor> | undefined;
      
      render(
        <TestHookComponent
          hook={useCLSMonitor}
          onResult={(r) => { result = r as ReturnType<typeof useCLSMonitor>; }}
        />
      );
      
      // In JSDOM, PerformanceObserver for layout-shift is not supported
      expect(result).toBeNull();
    });
  });

  describe('useDesignConsistencyCheck', () => {
    function TestComponent() {
      const ref = useRef<HTMLDivElement>(null);
      const issues = useDesignConsistencyCheck(ref);
      
      return (
        <div>
          <div ref={ref} style={{ backgroundColor: '#ff0000' }} data-testid="test-element" />
          <div data-testid="issue-count">{issues.length}</div>
        </div>
      );
    }

    it('should detect issues in development mode', () => {
      const originalEnv = process.env.NODE_ENV;
      Object.defineProperty(process.env, 'NODE_ENV', { value: 'development', configurable: true });
      
      render(<TestComponent />);
      
      // Note: The hook runs on mount, issues should be detected
      expect(screen.getByTestId('issue-count')).toBeInTheDocument();
      
      Object.defineProperty(process.env, 'NODE_ENV', { value: originalEnv, configurable: true });
    });
  });
});

// =============================================================================
// COMPONENT TESTS
// =============================================================================

describe('ColorSwatch Component', () => {
  beforeEach(() => {
    document.documentElement.style.setProperty('--primary', '221 83% 53%');
  });

  afterEach(() => {
    document.documentElement.style.removeProperty('--primary');
  });

  it('should render color swatch', () => {
    render(<ColorSwatch token="primary" />);
    
    expect(screen.getByRole('img', { name: /color swatch for primary/i })).toBeInTheDocument();
    expect(screen.getByText('primary')).toBeInTheDocument();
  });

  it('should show value when showValue is true', async () => {
    render(<ColorSwatch token="primary" showValue />);
    
    await waitFor(() => {
      expect(screen.getByText('221 83% 53%')).toBeInTheDocument();
    });
  });

  it('should render different sizes', () => {
    const { rerender } = render(<ColorSwatch token="primary" size="sm" />);
    expect(screen.getByRole('img')).toHaveClass('w-6', 'h-6');
    
    rerender(<ColorSwatch token="primary" size="md" />);
    expect(screen.getByRole('img')).toHaveClass('w-10', 'h-10');
    
    rerender(<ColorSwatch token="primary" size="lg" />);
    expect(screen.getByRole('img')).toHaveClass('w-16', 'h-16');
  });

  it('should apply custom className', () => {
    render(<ColorSwatch token="primary" className="custom-class" />);
    
    expect(screen.getByText('primary').parentElement?.parentElement).toHaveClass('custom-class');
  });
});

describe('SpacingScale Component', () => {
  it('should render default spacing tokens', () => {
    render(<SpacingScale />);
    
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('16')).toBeInTheDocument();
  });

  it('should render custom tokens', () => {
    render(<SpacingScale tokens={[2, 8, 24]} />);
    
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('24')).toBeInTheDocument();
  });

  it('should render horizontal direction', () => {
    render(<SpacingScale direction="horizontal" />);
    
    const container = screen.getByText('1').parentElement?.parentElement;
    expect(container).toHaveClass('flex-row');
  });

  it('should render vertical direction', () => {
    render(<SpacingScale direction="vertical" />);
    
    const container = screen.getByText('1').parentElement?.parentElement;
    expect(container).toHaveClass('flex-col');
  });
});

describe('TypographyScale Component', () => {
  it('should render default font sizes', () => {
    render(<TypographyScale />);
    
    expect(screen.getByText('xs')).toBeInTheDocument();
    expect(screen.getByText('base')).toBeInTheDocument();
    expect(screen.getByText('lg')).toBeInTheDocument();
  });

  it('should render custom sample text', () => {
    render(<TypographyScale sampleText="Test" />);
    
    const samples = screen.getAllByText('Test');
    expect(samples.length).toBeGreaterThan(0);
  });

  it('should render custom sizes', () => {
    render(<TypographyScale sizes={['sm', 'base', 'xl']} />);
    
    expect(screen.getByText('sm')).toBeInTheDocument();
    expect(screen.getByText('base')).toBeInTheDocument();
    expect(screen.getByText('xl')).toBeInTheDocument();
    expect(screen.queryByText('2xs')).not.toBeInTheDocument();
  });
});

describe('TokenDocumentation Component', () => {
  beforeEach(() => {
    // Set up required CSS variables
    Object.values(COLOR_TOKENS).forEach(variable => {
      document.documentElement.style.setProperty(variable, '0 0% 50%');
    });
  });

  afterEach(() => {
    Object.values(COLOR_TOKENS).forEach(variable => {
      document.documentElement.style.removeProperty(variable);
    });
  });

  it('should render colors documentation', () => {
    render(<TokenDocumentation category="colors" />);
    
    expect(screen.getByText('colors')).toBeInTheDocument();
    expect(screen.getByText('primary')).toBeInTheDocument();
    expect(screen.getByText('secondary')).toBeInTheDocument();
  });

  it('should render spacing documentation', () => {
    render(<TokenDocumentation category="spacing" />);
    
    expect(screen.getByText('spacing')).toBeInTheDocument();
    expect(screen.getByText('Horizontal Scale')).toBeInTheDocument();
    expect(screen.getByText('Vertical Scale')).toBeInTheDocument();
  });

  it('should render typography documentation', () => {
    render(<TokenDocumentation category="typography" />);
    
    expect(screen.getByText('typography')).toBeInTheDocument();
    expect(screen.getByText('Font Sizes')).toBeInTheDocument();
    expect(screen.getByText('Font Weights')).toBeInTheDocument();
  });

  it('should render radius documentation', () => {
    render(<TokenDocumentation category="radius" />);
    
    expect(screen.getByText('radius')).toBeInTheDocument();
    expect(screen.getByText('none')).toBeInTheDocument();
    expect(screen.getByText('full')).toBeInTheDocument();
  });

  it('should render shadows documentation', () => {
    render(<TokenDocumentation category="shadows" />);
    
    expect(screen.getByText('shadows')).toBeInTheDocument();
    expect(screen.getByText('elevation-1')).toBeInTheDocument();
  });

  it('should render animations documentation', () => {
    render(<TokenDocumentation category="animations" />);
    
    expect(screen.getByText('animations')).toBeInTheDocument();
    expect(screen.getByText('Durations')).toBeInTheDocument();
    expect(screen.getByText('Easings')).toBeInTheDocument();
  });
});

describe('DesignAuditPanel Component', () => {
  beforeEach(() => {
    Object.values(COLOR_TOKENS).forEach(variable => {
      document.documentElement.style.setProperty(variable, '0 0% 50%');
    });
  });

  afterEach(() => {
    Object.values(COLOR_TOKENS).forEach(variable => {
      document.documentElement.style.removeProperty(variable);
    });
  });

  it('should render audit button initially', () => {
    render(<DesignAuditPanel />);
    
    expect(screen.getByRole('button', { name: /open design system audit/i })).toBeInTheDocument();
  });

  it('should open panel on button click', async () => {
    render(<DesignAuditPanel />);
    
    fireEvent.click(screen.getByRole('button', { name: /open design system audit/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /design system audit/i })).toBeInTheDocument();
    });
  });

  it('should show audit results when open', async () => {
    render(<DesignAuditPanel />);
    
    fireEvent.click(screen.getByRole('button', { name: /open design system audit/i }));
    
    await waitFor(() => {
      expect(screen.getByText('Total')).toBeInTheDocument();
      expect(screen.getByText('Valid')).toBeInTheDocument();
      expect(screen.getByText('Invalid')).toBeInTheDocument();
    });
  });

  it('should close panel on close button click', async () => {
    render(<DesignAuditPanel />);
    
    fireEvent.click(screen.getByRole('button', { name: /open design system audit/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByRole('button', { name: /close audit panel/i }));
    
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('should have re-run audit button', async () => {
    render(<DesignAuditPanel />);
    
    fireEvent.click(screen.getByRole('button', { name: /open design system audit/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /re-run audit/i })).toBeInTheDocument();
    });
  });

  it('should show missing tokens when some are undefined', async () => {
    document.documentElement.style.removeProperty('--primary');
    
    render(<DesignAuditPanel />);
    
    fireEvent.click(screen.getByRole('button', { name: /open design system audit/i }));
    
    await waitFor(() => {
      expect(screen.getByText('Missing Tokens')).toBeInTheDocument();
      expect(screen.getByText('• primary')).toBeInTheDocument();
    });
  });
});

describe('CLSIndicator Component', () => {
  it('should render nothing when PerformanceObserver not available', () => {
    const { container } = render(<CLSIndicator />);
    
    // In JSDOM, layout-shift PerformanceObserver is not available
    expect(container.firstChild).toBeNull();
  });
});

describe('DesignSystemProvider Component', () => {
  it('should provide default theme', () => {
    let capturedTheme: string | undefined;
    
    function Consumer() {
      const { theme } = useDesignSystem();
      capturedTheme = theme;
      return null;
    }
    
    render(
      <DesignSystemProvider>
        <Consumer />
      </DesignSystemProvider>
    );
    
    expect(capturedTheme).toBe('system');
  });

  it('should provide custom default theme', () => {
    let capturedTheme: string | undefined;
    
    function Consumer() {
      const { theme } = useDesignSystem();
      capturedTheme = theme;
      return null;
    }
    
    render(
      <DesignSystemProvider defaultTheme="dark">
        <Consumer />
      </DesignSystemProvider>
    );
    
    expect(capturedTheme).toBe('dark');
  });

  it('should allow theme changes', async () => {
    let setThemeFn: ((theme: 'light' | 'dark' | 'system') => void) | undefined;
    let currentTheme: string | undefined;
    
    function Consumer() {
      const { theme, setTheme } = useDesignSystem();
      currentTheme = theme;
      setThemeFn = setTheme;
      return <button onClick={() => setTheme('light')}>Switch</button>;
    }
    
    render(
      <DesignSystemProvider defaultTheme="dark">
        <Consumer />
      </DesignSystemProvider>
    );
    
    expect(currentTheme).toBe('dark');
    
    await act(async () => {
      setThemeFn?.('light');
    });
    
    expect(currentTheme).toBe('light');
  });

  it('should apply theme class to document', async () => {
    function Consumer() {
      const { setTheme } = useDesignSystem();
      return <button onClick={() => setTheme('dark')}>Dark</button>;
    }
    
    render(
      <DesignSystemProvider defaultTheme="light">
        <Consumer />
      </DesignSystemProvider>
    );
    
    expect(document.documentElement.classList.contains('light')).toBe(true);
    
    await act(async () => {
      fireEvent.click(screen.getByText('Dark'));
    });
    
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('should provide all token collections', () => {
    let tokens: typeof COLOR_TOKENS | undefined;
    
    function Consumer() {
      const ds = useDesignSystem();
      tokens = ds.tokens.colors;
      return null;
    }
    
    render(
      <DesignSystemProvider>
        <Consumer />
      </DesignSystemProvider>
    );
    
    expect(tokens).toBe(COLOR_TOKENS);
  });

  it('should provide getTokenValue function', () => {
    let getTokenValueFn: ((token: ColorToken) => string | null) | undefined;
    
    function Consumer() {
      const { getTokenValue } = useDesignSystem();
      getTokenValueFn = getTokenValue;
      return null;
    }
    
    document.documentElement.style.setProperty('--primary', '221 83% 53%');
    
    render(
      <DesignSystemProvider>
        <Consumer />
      </DesignSystemProvider>
    );
    
    expect(getTokenValueFn?.('primary')).toBe('221 83% 53%');
    
    document.documentElement.style.removeProperty('--primary');
  });

  it('should provide auditTokens function', () => {
    let auditFn: (() => ReturnType<typeof auditColorTokens>) | undefined;
    
    function Consumer() {
      const { auditTokens } = useDesignSystem();
      auditFn = auditTokens;
      return null;
    }
    
    render(
      <DesignSystemProvider>
        <Consumer />
      </DesignSystemProvider>
    );
    
    const report = auditFn?.();
    expect(report).toBeDefined();
    expect(report?.timestamp).toBeInstanceOf(Date);
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Design System Integration', () => {
  beforeEach(() => {
    // Set up all CSS variables
    Object.values(COLOR_TOKENS).forEach(variable => {
      document.documentElement.style.setProperty(variable, '0 0% 50%');
    });
    // Clear theme class from previous tests
    document.documentElement.classList.remove('light', 'dark');
    // Clear localStorage
    localStorage.clear();
  });

  afterEach(() => {
    Object.values(COLOR_TOKENS).forEach(variable => {
      document.documentElement.style.removeProperty(variable);
    });
    document.documentElement.classList.remove('light', 'dark');
    localStorage.clear();
  });

  it('should work with full design system flow', async () => {
    function DesignSystemDemo() {
      const { theme, setTheme, auditTokens } = useDesignSystem();
      const [report, setReport] = React.useState<ReturnType<typeof auditColorTokens> | null>(null);
      
      return (
        <div>
          <div data-testid="current-theme">{theme}</div>
          <button onClick={() => setTheme('dark')}>Dark Mode</button>
          <button onClick={() => setReport(auditTokens())}>Run Audit</button>
          {report && <div data-testid="audit-valid">{report.validTokens}</div>}
        </div>
      );
    }
    
    render(
      <DesignSystemProvider defaultTheme="light">
        <DesignSystemDemo />
      </DesignSystemProvider>
    );
    
    expect(screen.getByTestId('current-theme')).toHaveTextContent('light');
    
    await act(async () => {
      fireEvent.click(screen.getByText('Dark Mode'));
    });
    
    expect(screen.getByTestId('current-theme')).toHaveTextContent('dark');
    
    await act(async () => {
      fireEvent.click(screen.getByText('Run Audit'));
    });
    
    expect(screen.getByTestId('audit-valid')).toBeInTheDocument();
  });

  it('should correctly identify token compliance', () => {
    const report = auditColorTokens();
    
    expect(report.validTokens).toBe(Object.keys(COLOR_TOKENS).length);
    expect(report.invalidTokens).toBe(0);
    expect(report.missingTokens).toHaveLength(0);
  });

  it('should build consistent interaction classes', () => {
    const buttonClasses = buildInteractionClasses('button');
    const inputClasses = buildInteractionClasses('input');
    
    // Both should have transitions
    expect(buttonClasses).toContain('transition');
    expect(inputClasses).toContain('transition');
    
    // Both should have focus states
    expect(buttonClasses).toContain('focus');
    expect(inputClasses).toContain('focus');
  });
});
