/**
 * Tests for Design Tokens Context and Hooks
 */
import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  DesignTokensProvider,
  useDesignTokens,
  useTheme,
  useDensity,
  useSpacing,
  useRadius,
  useShadow,
  useColors,
  useComponentSizes,
  useStatusColors,
  useBadgeVariants,
  useElevation,
  useCssVar,
  getInitialTheme,
  themeScript,
  ThemeToggle,
  DensityToggle,
} from '@/lib/design-tokens-context';
import { lightTheme, darkTheme, spacing, radii, shadows } from '@/lib/design-tokens';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] ?? null),
    setItem: jest.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: jest.fn((key: string) => { delete store[key]; }),
    clear: jest.fn(() => { store = {}; }),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock matchMedia
const matchMediaMock = jest.fn().mockImplementation((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: jest.fn(),
  removeListener: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  dispatchEvent: jest.fn(),
}));

Object.defineProperty(window, 'matchMedia', { value: matchMediaMock });

// Reset mocks before each test
beforeEach(() => {
  localStorageMock.clear();
  jest.clearAllMocks();
  document.documentElement.className = '';
  document.documentElement.style.cssText = '';
});

// =============================================================================
// Test Components
// =============================================================================

function TestComponent() {
  const { theme, colors, density } = useDesignTokens();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="background">{colors.background}</span>
      <span data-testid="density">{density}</span>
    </div>
  );
}

function ThemeTestComponent() {
  const { theme, themeMode, setThemeMode, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="themeMode">{themeMode}</span>
      <button data-testid="toggle" onClick={toggleTheme}>Toggle</button>
      <button data-testid="setLight" onClick={() => setThemeMode('light')}>Light</button>
      <button data-testid="setDark" onClick={() => setThemeMode('dark')}>Dark</button>
      <button data-testid="setSystem" onClick={() => setThemeMode('system')}>System</button>
    </div>
  );
}

function DensityTestComponent() {
  const { density, setDensity, getDensity } = useDensity();
  const densityTokens = getDensity();
  return (
    <div>
      <span data-testid="density">{density}</span>
      <span data-testid="rowHeight">{densityTokens.rowHeight}</span>
      <button data-testid="setComfortable" onClick={() => setDensity('comfortable')}>Comfortable</button>
      <button data-testid="setCompact" onClick={() => setDensity('compact')}>Compact</button>
    </div>
  );
}

function TokenAccessTestComponent() {
  const getSpacing = useSpacing();
  const getRadius = useRadius();
  const getShadow = useShadow();
  const { getColor, themeColors } = useColors();
  const getComponentSize = useComponentSizes();
  const getStatusColors = useStatusColors();
  const getBadgeVariant = useBadgeVariants();
  const getElevation = useElevation();
  const cssVar = useCssVar();
  
  return (
    <div>
      <span data-testid="spacing4">{getSpacing(4)}</span>
      <span data-testid="radiusLg">{getRadius('lg')}</span>
      <span data-testid="shadowMd">{getShadow('md')}</span>
      <span data-testid="primaryColor">{getColor('primary', 500)}</span>
      <span data-testid="themeBackground">{themeColors.background}</span>
      <span data-testid="componentMd">{getComponentSize('md').height}</span>
      <span data-testid="statusSuccess">{getStatusColors('success').background}</span>
      <span data-testid="badgePrimary">{getBadgeVariant('primary').background}</span>
      <span data-testid="elevationRaised">{getElevation('raised').zIndex}</span>
      <span data-testid="cssVarBackground">{cssVar('background')}</span>
    </div>
  );
}

// =============================================================================
// Provider Tests
// =============================================================================

describe('DesignTokensProvider', () => {
  it('should provide default theme and density', () => {
    render(
      <DesignTokensProvider>
        <TestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('theme')).toHaveTextContent('light');
    expect(screen.getByTestId('density')).toHaveTextContent('comfortable');
  });
  
  it('should accept defaultTheme prop', async () => {
    render(
      <DesignTokensProvider defaultTheme="dark">
        <TestComponent />
      </DesignTokensProvider>
    );
    
    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    });
  });
  
  it('should accept defaultDensity prop', () => {
    render(
      <DesignTokensProvider defaultDensity="compact">
        <TestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('density')).toHaveTextContent('compact');
  });
  
  it('should load theme from localStorage', async () => {
    localStorageMock.setItem('sensei-theme', 'dark');
    
    render(
      <DesignTokensProvider>
        <TestComponent />
      </DesignTokensProvider>
    );
    
    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    });
  });
  
  it('should use custom storage key', async () => {
    localStorageMock.setItem('custom-theme', 'dark');
    
    render(
      <DesignTokensProvider storageKey="custom-theme">
        <TestComponent />
      </DesignTokensProvider>
    );
    
    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    });
  });
  
  it('should throw error when hooks used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => {
      render(<TestComponent />);
    }).toThrow('useDesignTokens must be used within a DesignTokensProvider');
    
    consoleSpy.mockRestore();
  });
});

// =============================================================================
// useTheme Tests
// =============================================================================

describe('useTheme', () => {
  it('should provide theme state', () => {
    render(
      <DesignTokensProvider>
        <ThemeTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('theme')).toHaveTextContent('light');
    expect(screen.getByTestId('themeMode')).toHaveTextContent('system');
  });
  
  it('should toggle theme', async () => {
    const user = userEvent.setup();
    
    render(
      <DesignTokensProvider defaultTheme="light">
        <ThemeTestComponent />
      </DesignTokensProvider>
    );
    
    await user.click(screen.getByTestId('toggle'));
    
    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    });
  });
  
  it('should set theme mode', async () => {
    const user = userEvent.setup();
    
    render(
      <DesignTokensProvider>
        <ThemeTestComponent />
      </DesignTokensProvider>
    );
    
    await user.click(screen.getByTestId('setDark'));
    
    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('dark');
      expect(screen.getByTestId('themeMode')).toHaveTextContent('dark');
    });
  });
  
  it('should save theme to localStorage', async () => {
    const user = userEvent.setup();
    
    render(
      <DesignTokensProvider>
        <ThemeTestComponent />
      </DesignTokensProvider>
    );
    
    await user.click(screen.getByTestId('setDark'));
    
    expect(localStorageMock.setItem).toHaveBeenCalledWith('sensei-theme', 'dark');
  });
  
  it('should apply theme class to document', async () => {
    render(
      <DesignTokensProvider defaultTheme="dark">
        <TestComponent />
      </DesignTokensProvider>
    );
    
    await waitFor(() => {
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });
  });
});

// =============================================================================
// useDensity Tests
// =============================================================================

describe('useDensity', () => {
  it('should provide density state', () => {
    render(
      <DesignTokensProvider>
        <DensityTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('density')).toHaveTextContent('comfortable');
    expect(screen.getByTestId('rowHeight')).toHaveTextContent('3rem');
  });
  
  it('should set density', async () => {
    const user = userEvent.setup();
    
    render(
      <DesignTokensProvider>
        <DensityTestComponent />
      </DesignTokensProvider>
    );
    
    await user.click(screen.getByTestId('setCompact'));
    
    expect(screen.getByTestId('density')).toHaveTextContent('compact');
    expect(screen.getByTestId('rowHeight')).toHaveTextContent('2.25rem');
  });
  
  it('should save density to localStorage', async () => {
    const user = userEvent.setup();
    
    render(
      <DesignTokensProvider>
        <DensityTestComponent />
      </DesignTokensProvider>
    );
    
    await user.click(screen.getByTestId('setCompact'));
    
    expect(localStorageMock.setItem).toHaveBeenCalledWith('sensei-theme-density', 'compact');
  });
});

// =============================================================================
// Token Access Hooks Tests
// =============================================================================

describe('Token Access Hooks', () => {
  it('should provide spacing values', () => {
    render(
      <DesignTokensProvider>
        <TokenAccessTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('spacing4')).toHaveTextContent(spacing[4]);
  });
  
  it('should provide radius values', () => {
    render(
      <DesignTokensProvider>
        <TokenAccessTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('radiusLg')).toHaveTextContent(radii.lg);
  });
  
  it('should provide shadow values', () => {
    render(
      <DesignTokensProvider>
        <TokenAccessTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('shadowMd')).toHaveTextContent(shadows.md);
  });
  
  it('should provide color values', () => {
    render(
      <DesignTokensProvider>
        <TokenAccessTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('primaryColor')).toBeTruthy();
    expect(screen.getByTestId('themeBackground')).toHaveTextContent(lightTheme.background);
  });
  
  it('should provide component sizes', () => {
    render(
      <DesignTokensProvider>
        <TokenAccessTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('componentMd')).toHaveTextContent('2.5rem');
  });
  
  it('should provide status colors', () => {
    render(
      <DesignTokensProvider>
        <TokenAccessTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('statusSuccess')).toBeTruthy();
  });
  
  it('should provide badge variants', () => {
    render(
      <DesignTokensProvider>
        <TokenAccessTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('badgePrimary')).toBeTruthy();
  });
  
  it('should provide elevation values', () => {
    render(
      <DesignTokensProvider>
        <TokenAccessTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('elevationRaised')).toHaveTextContent('10');
  });
  
  it('should provide CSS variable references', () => {
    render(
      <DesignTokensProvider>
        <TokenAccessTestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('cssVarBackground')).toHaveTextContent('var(--background)');
  });
});

// =============================================================================
// ThemeToggle Component Tests
// =============================================================================

describe('ThemeToggle', () => {
  it('should render toggle button', () => {
    render(
      <DesignTokensProvider>
        <ThemeToggle />
      </DesignTokensProvider>
    );
    
    expect(screen.getByRole('button')).toBeInTheDocument();
  });
  
  it('should have accessible label', () => {
    render(
      <DesignTokensProvider defaultTheme="light">
        <ThemeToggle />
      </DesignTokensProvider>
    );
    
    expect(screen.getByLabelText(/switch to dark mode/i)).toBeInTheDocument();
  });
  
  it('should toggle theme on click', async () => {
    const user = userEvent.setup();
    
    render(
      <DesignTokensProvider defaultTheme="light">
        <ThemeToggle />
        <TestComponent />
      </DesignTokensProvider>
    );
    
    await user.click(screen.getByRole('button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    });
  });
  
  it('should accept className prop', () => {
    render(
      <DesignTokensProvider>
        <ThemeToggle className="custom-class" />
      </DesignTokensProvider>
    );
    
    expect(screen.getByRole('button')).toHaveClass('custom-class');
  });
});

// =============================================================================
// DensityToggle Component Tests
// =============================================================================

describe('DensityToggle', () => {
  it('should render toggle button', () => {
    render(
      <DesignTokensProvider>
        <DensityToggle />
      </DesignTokensProvider>
    );
    
    expect(screen.getByRole('button')).toBeInTheDocument();
  });
  
  it('should have accessible label', () => {
    render(
      <DesignTokensProvider defaultDensity="comfortable">
        <DensityToggle />
      </DesignTokensProvider>
    );
    
    expect(screen.getByLabelText(/switch to compact density/i)).toBeInTheDocument();
  });
  
  it('should toggle density on click', async () => {
    const user = userEvent.setup();
    
    render(
      <DesignTokensProvider defaultDensity="comfortable">
        <DensityToggle />
        <TestComponent />
      </DesignTokensProvider>
    );
    
    await user.click(screen.getByRole('button'));
    
    expect(screen.getByTestId('density')).toHaveTextContent('compact');
  });
});

// =============================================================================
// Utility Function Tests
// =============================================================================

describe('Utility Functions', () => {
  describe('getInitialTheme', () => {
    it('should return light by default', () => {
      expect(getInitialTheme()).toBe('light');
    });
    
    it('should return stored theme', () => {
      localStorageMock.setItem('sensei-theme', 'dark');
      expect(getInitialTheme()).toBe('dark');
    });
    
    it('should detect system preference when set to system', () => {
      localStorageMock.setItem('sensei-theme', 'system');
      matchMediaMock.mockImplementationOnce(() => ({
        matches: true, // Dark mode
        media: '',
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      }));
      
      expect(getInitialTheme()).toBe('dark');
    });
  });
  
  describe('themeScript', () => {
    it('should be a non-empty string', () => {
      expect(typeof themeScript).toBe('string');
      expect(themeScript.length).toBeGreaterThan(0);
    });
    
    it('should contain localStorage check', () => {
      expect(themeScript).toContain('localStorage');
      expect(themeScript).toContain('sensei-theme');
    });
    
    it('should contain matchMedia check', () => {
      expect(themeScript).toContain('matchMedia');
      expect(themeScript).toContain('prefers-color-scheme');
    });
  });
});

// =============================================================================
// Theme Colors by Mode Tests
// =============================================================================

describe('Theme Colors by Mode', () => {
  it('should provide light theme colors in light mode', () => {
    render(
      <DesignTokensProvider defaultTheme="light">
        <TestComponent />
      </DesignTokensProvider>
    );
    
    expect(screen.getByTestId('background')).toHaveTextContent(lightTheme.background);
  });
  
  it('should provide dark theme colors in dark mode', async () => {
    render(
      <DesignTokensProvider defaultTheme="dark">
        <TestComponent />
      </DesignTokensProvider>
    );
    
    await waitFor(() => {
      expect(screen.getByTestId('background')).toHaveTextContent(darkTheme.background);
    });
  });
});

// =============================================================================
// CSS Variables Application Tests
// =============================================================================

describe('CSS Variables Application', () => {
  it('should apply CSS variables to document root', async () => {
    render(
      <DesignTokensProvider defaultTheme="light">
        <TestComponent />
      </DesignTokensProvider>
    );
    
    await waitFor(() => {
      const root = document.documentElement;
      expect(root.style.getPropertyValue('--background')).toBe(lightTheme.background);
    });
  });
  
  it('should apply density CSS variables', async () => {
    render(
      <DesignTokensProvider defaultDensity="comfortable">
        <TestComponent />
      </DesignTokensProvider>
    );
    
    await waitFor(() => {
      const root = document.documentElement;
      expect(root.style.getPropertyValue('--row-height')).toBe('3rem');
    });
  });
});
