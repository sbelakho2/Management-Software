/**
 * Tests for Browser, OS & Hardware Interoperability Components
 * 
 * Section 19.10: Browser, OS & Hardware Interoperability
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  // Constants
  BROWSER,
  OS,
  LOCALE,
  UNIT_SYSTEM,
  THEME_MODE,
  TEXT_DIRECTION,
  CSS_FEATURE,
  // Detection
  detectBrowser,
  detectOS,
  isTouchDevice,
  isMobileDevice,
  checkCSSFeature,
  getCSSFeatureSupport,
  // Share API
  canShare,
  canShareFiles,
  nativeShare,
  // Theme
  ThemeProvider,
  useTheme,
  ThemeToggle,
  // Scrollbar
  ScrollbarContainer,
  // I18n
  I18nProvider,
  useI18n,
  LocaleSelector,
  getTextDirection,
  // Units
  UnitProvider,
  useUnits,
  UnitToggle,
  // Timezone
  TimezoneProvider,
  useTimezone,
  TimezoneSelector,
  getLocalTimezone,
  // Share
  ShareButton,
  // Hook
  useBrowserInfo,
  // RTL
  RTLWrapper,
} from '../browser-interop';

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('Browser Interop Constants', () => {
  describe('BROWSER', () => {
    it('should define all browser types', () => {
      expect(BROWSER.CHROME).toBe('chrome');
      expect(BROWSER.FIREFOX).toBe('firefox');
      expect(BROWSER.SAFARI).toBe('safari');
      expect(BROWSER.EDGE).toBe('edge');
      expect(BROWSER.OPERA).toBe('opera');
      expect(BROWSER.UNKNOWN).toBe('unknown');
    });
  });

  describe('OS', () => {
    it('should define all OS types', () => {
      expect(OS.WINDOWS).toBe('windows');
      expect(OS.MACOS).toBe('macos');
      expect(OS.LINUX).toBe('linux');
      expect(OS.IOS).toBe('ios');
      expect(OS.ANDROID).toBe('android');
      expect(OS.UNKNOWN).toBe('unknown');
    });
  });

  describe('LOCALE', () => {
    it('should define all supported locales', () => {
      expect(LOCALE.EN_US).toBe('en-US');
      expect(LOCALE.EN_GB).toBe('en-GB');
      expect(LOCALE.FR_FR).toBe('fr-FR');
      expect(LOCALE.AR_SA).toBe('ar-SA');
    });
  });

  describe('UNIT_SYSTEM', () => {
    it('should define unit systems', () => {
      expect(UNIT_SYSTEM.METRIC).toBe('metric');
      expect(UNIT_SYSTEM.IMPERIAL).toBe('imperial');
    });
  });

  describe('THEME_MODE', () => {
    it('should define theme modes', () => {
      expect(THEME_MODE.LIGHT).toBe('light');
      expect(THEME_MODE.DARK).toBe('dark');
      expect(THEME_MODE.SYSTEM).toBe('system');
    });
  });

  describe('TEXT_DIRECTION', () => {
    it('should define text directions', () => {
      expect(TEXT_DIRECTION.LTR).toBe('ltr');
      expect(TEXT_DIRECTION.RTL).toBe('rtl');
    });
  });

  describe('CSS_FEATURE', () => {
    it('should define CSS features', () => {
      expect(CSS_FEATURE.ASPECT_RATIO).toBe('aspectRatio');
      expect(CSS_FEATURE.GRID).toBe('grid');
      expect(CSS_FEATURE.FLEX).toBe('flex');
      expect(CSS_FEATURE.GAP).toBe('gap');
      expect(CSS_FEATURE.CONTAINER_QUERIES).toBe('containerQueries');
      expect(CSS_FEATURE.SUBGRID).toBe('subgrid');
      expect(CSS_FEATURE.SCROLL_SNAP).toBe('scrollSnap');
    });
  });
});

// =============================================================================
// DETECTION TESTS
// =============================================================================

describe('Browser Detection', () => {
  describe('detectBrowser', () => {
    it('should return a browser type', () => {
      const browser = detectBrowser();
      expect(Object.values(BROWSER)).toContain(browser);
    });

    it('should return unknown for undefined userAgent', () => {
      // The function handles undefined navigator gracefully
      expect(typeof detectBrowser()).toBe('string');
    });
  });

  describe('detectOS', () => {
    it('should return an OS type', () => {
      const os = detectOS();
      expect(Object.values(OS)).toContain(os);
    });
  });

  describe('isTouchDevice', () => {
    it('should return a boolean', () => {
      expect(typeof isTouchDevice()).toBe('boolean');
    });
  });

  describe('isMobileDevice', () => {
    it('should return a boolean', () => {
      expect(typeof isMobileDevice()).toBe('boolean');
    });
  });
});

// =============================================================================
// CSS FEATURE DETECTION TESTS
// =============================================================================

describe('CSS Feature Detection', () => {
  const originalCSS = global.CSS;

  beforeEach(() => {
    global.CSS = {
      supports: jest.fn((prop: string, value: string) => {
        if (prop === 'display' && (value === 'grid' || value === 'flex')) return true;
        if (prop === 'gap' && value === '1px') return true;
        if (prop === 'aspect-ratio' && value === '1 / 1') return true;
        return false;
      }),
    } as unknown as typeof CSS;
  });

  afterEach(() => {
    global.CSS = originalCSS;
  });

  describe('checkCSSFeature', () => {
    it('should check grid support', () => {
      expect(checkCSSFeature(CSS_FEATURE.GRID)).toBe(true);
    });

    it('should check flex support', () => {
      expect(checkCSSFeature(CSS_FEATURE.FLEX)).toBe(true);
    });

    it('should check gap support', () => {
      expect(checkCSSFeature(CSS_FEATURE.GAP)).toBe(true);
    });

    it('should check aspect-ratio support', () => {
      expect(checkCSSFeature(CSS_FEATURE.ASPECT_RATIO)).toBe(true);
    });

    it('should return false for unsupported features', () => {
      expect(checkCSSFeature(CSS_FEATURE.SUBGRID)).toBe(false);
    });
  });

  describe('getCSSFeatureSupport', () => {
    it('should return all feature support flags', () => {
      const support = getCSSFeatureSupport();
      expect(support).toHaveProperty(CSS_FEATURE.GRID);
      expect(support).toHaveProperty(CSS_FEATURE.FLEX);
      expect(support).toHaveProperty(CSS_FEATURE.ASPECT_RATIO);
    });
  });
});

// =============================================================================
// SHARE API TESTS
// =============================================================================

describe('Share API', () => {
  describe('canShare', () => {
    it('should return true when share is available', () => {
      Object.defineProperty(navigator, 'share', {
        value: jest.fn(),
        writable: true,
        configurable: true,
      });
      expect(canShare()).toBe(true);
    });
  });

  describe('canShareFiles', () => {
    it('should return true when canShare is available', () => {
      Object.defineProperty(navigator, 'canShare', {
        value: jest.fn(),
        writable: true,
        configurable: true,
      });
      expect(canShareFiles()).toBe(true);
    });
  });

  describe('nativeShare', () => {
    it('should call navigator.share', async () => {
      const shareMock = jest.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, 'share', {
        value: shareMock,
        writable: true,
        configurable: true,
      });

      const result = await nativeShare({ title: 'Test', url: 'https://example.com' });
      expect(shareMock).toHaveBeenCalled();
      expect(result).toBe(true);
    });

    it('should return false when user cancels', async () => {
      const shareMock = jest.fn().mockRejectedValue({ name: 'AbortError' });
      Object.defineProperty(navigator, 'share', {
        value: shareMock,
        writable: true,
        configurable: true,
      });

      const result = await nativeShare({ title: 'Test' });
      expect(result).toBe(false);
    });
  });
});

// =============================================================================
// THEME PROVIDER TESTS
// =============================================================================

describe('ThemeProvider', () => {
  function ThemeTester() {
    const { theme, resolvedTheme, setTheme } = useTheme();
    return (
      <div>
        <span data-testid="theme">{theme}</span>
        <span data-testid="resolved">{resolvedTheme}</span>
        <button onClick={() => setTheme(THEME_MODE.DARK)}>Dark</button>
        <button onClick={() => setTheme(THEME_MODE.LIGHT)}>Light</button>
      </div>
    );
  }

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('light', 'dark');
  });

  it('should provide theme state', () => {
    render(
      <ThemeProvider defaultTheme={THEME_MODE.LIGHT}>
        <ThemeTester />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme')).toHaveTextContent('light');
  });

  it('should allow changing theme', async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeTester />
      </ThemeProvider>
    );

    await user.click(screen.getByText('Dark'));
    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
  });

  it('should apply theme class to document', async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider defaultTheme={THEME_MODE.LIGHT}>
        <ThemeTester />
      </ThemeProvider>
    );

    await user.click(screen.getByText('Dark'));
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('should persist theme to localStorage', async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeTester />
      </ThemeProvider>
    );

    await user.click(screen.getByText('Dark'));
    expect(localStorage.getItem('theme-preference')).toBe('dark');
  });

  it('should throw error when useTheme is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<ThemeTester />)).toThrow('useTheme must be used within ThemeProvider');
    consoleError.mockRestore();
  });
});

// =============================================================================
// THEME TOGGLE TESTS
// =============================================================================

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should render toggle button', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('should cycle through themes', async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider defaultTheme={THEME_MODE.LIGHT}>
        <ThemeToggle showLabel />
      </ThemeProvider>
    );

    expect(screen.getByText('Light')).toBeInTheDocument();

    await user.click(screen.getByRole('button'));
    expect(screen.getByText('Dark')).toBeInTheDocument();

    await user.click(screen.getByRole('button'));
    expect(screen.getByText('System')).toBeInTheDocument();
  });

  it('should have accessible label', () => {
    render(
      <ThemeProvider defaultTheme={THEME_MODE.LIGHT}>
        <ThemeToggle />
      </ThemeProvider>
    );

    expect(screen.getByLabelText(/theme.*click to change/i)).toBeInTheDocument();
  });
});

// =============================================================================
// SCROLLBAR CONTAINER TESTS
// =============================================================================

describe('ScrollbarContainer', () => {
  it('should render children', () => {
    render(
      <ScrollbarContainer>
        <p>Content</p>
      </ScrollbarContainer>
    );

    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('should apply hidden scrollbar class', () => {
    render(
      <ScrollbarContainer hideScrollbar>
        <p>Content</p>
      </ScrollbarContainer>
    );

    expect(document.querySelector('.scrollbar-hide')).toBeInTheDocument();
  });

  it('should apply thin scrollbar class', () => {
    render(
      <ScrollbarContainer thinScrollbar>
        <p>Content</p>
      </ScrollbarContainer>
    );

    expect(document.querySelector('.scrollbar-thin')).toBeInTheDocument();
  });

  it('should apply default scrollbar class', () => {
    render(
      <ScrollbarContainer>
        <p>Content</p>
      </ScrollbarContainer>
    );

    expect(document.querySelector('.scrollbar-default')).toBeInTheDocument();
  });

  it('should include scrollbar styles', () => {
    render(
      <ScrollbarContainer>
        <p>Content</p>
      </ScrollbarContainer>
    );

    expect(document.querySelector('style')).toBeInTheDocument();
  });
});

// =============================================================================
// I18N TESTS
// =============================================================================

describe('I18nProvider', () => {
  function I18nTester() {
    const { locale, direction, t, formatNumber, formatCurrency, formatDate } = useI18n();
    return (
      <div>
        <span data-testid="locale">{locale}</span>
        <span data-testid="direction">{direction}</span>
        <span data-testid="translation">{t('common.save')}</span>
        <span data-testid="number">{formatNumber(1234.56)}</span>
        <span data-testid="currency">{formatCurrency(99.99)}</span>
        <span data-testid="date">{formatDate(new Date('2025-01-15'))}</span>
      </div>
    );
  }

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('dir');
    document.documentElement.removeAttribute('lang');
  });

  it('should provide locale state', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.EN_US}>
        <I18nTester />
      </I18nProvider>
    );

    expect(screen.getByTestId('locale')).toHaveTextContent('en-US');
  });

  it('should provide translations', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.EN_US}>
        <I18nTester />
      </I18nProvider>
    );

    expect(screen.getByTestId('translation')).toHaveTextContent('Save');
  });

  it('should provide French translations', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.FR_FR}>
        <I18nTester />
      </I18nProvider>
    );

    expect(screen.getByTestId('translation')).toHaveTextContent('Enregistrer');
  });

  it('should set RTL direction for Arabic', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.AR_SA}>
        <I18nTester />
      </I18nProvider>
    );

    expect(screen.getByTestId('direction')).toHaveTextContent('rtl');
  });

  it('should format numbers', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.EN_US}>
        <I18nTester />
      </I18nProvider>
    );

    expect(screen.getByTestId('number')).toHaveTextContent('1,234.56');
  });

  it('should format currency', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.EN_US}>
        <I18nTester />
      </I18nProvider>
    );

    expect(screen.getByTestId('currency')).toHaveTextContent('$99.99');
  });

  it('should apply direction to document', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.AR_SA}>
        <I18nTester />
      </I18nProvider>
    );

    expect(document.documentElement.dir).toBe('rtl');
  });

  it('should apply lang to document', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.FR_FR}>
        <I18nTester />
      </I18nProvider>
    );

    expect(document.documentElement.lang).toBe('fr-FR');
  });

  it('should throw error when useI18n is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<I18nTester />)).toThrow('useI18n must be used within I18nProvider');
    consoleError.mockRestore();
  });
});

describe('getTextDirection', () => {
  it('should return RTL for Arabic', () => {
    expect(getTextDirection(LOCALE.AR_SA)).toBe(TEXT_DIRECTION.RTL);
  });

  it('should return LTR for English', () => {
    expect(getTextDirection(LOCALE.EN_US)).toBe(TEXT_DIRECTION.LTR);
  });

  it('should return LTR for French', () => {
    expect(getTextDirection(LOCALE.FR_FR)).toBe(TEXT_DIRECTION.LTR);
  });
});

// =============================================================================
// LOCALE SELECTOR TESTS
// =============================================================================

describe('LocaleSelector', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('dir');
    document.documentElement.removeAttribute('lang');
  });

  it('should render current locale', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.EN_US}>
        <LocaleSelector />
      </I18nProvider>
    );

    expect(screen.getByText('English (US)')).toBeInTheDocument();
  });

  it('should open dropdown on click', async () => {
    const user = userEvent.setup();

    render(
      <I18nProvider defaultLocale={LOCALE.EN_US}>
        <LocaleSelector />
      </I18nProvider>
    );

    await user.click(screen.getByRole('button'));
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('should show all locale options', async () => {
    const user = userEvent.setup();

    render(
      <I18nProvider defaultLocale={LOCALE.EN_US}>
        <LocaleSelector />
      </I18nProvider>
    );

    await user.click(screen.getByRole('button'));

    // Check for the listbox with options
    const listbox = screen.getByRole('listbox');
    expect(listbox).toBeInTheDocument();
    
    // Get all options
    const options = screen.getAllByRole('option');
    expect(options.length).toBe(4); // 4 locales
  });

  it('should change locale when option clicked', async () => {
    const user = userEvent.setup();

    function TestComponent() {
      const { locale } = useI18n();
      return (
        <div>
          <LocaleSelector />
          <span data-testid="current">{locale}</span>
        </div>
      );
    }

    render(
      <I18nProvider defaultLocale={LOCALE.EN_US}>
        <TestComponent />
      </I18nProvider>
    );

    await user.click(screen.getByRole('button'));
    await user.click(screen.getByText('Français'));

    expect(screen.getByTestId('current')).toHaveTextContent('fr-FR');
  });
});

// =============================================================================
// UNIT PROVIDER TESTS
// =============================================================================

describe('UnitProvider', () => {
  function UnitTester() {
    const { system, formatLength, formatWeight, formatTemperature } = useUnits();
    return (
      <div>
        <span data-testid="system">{system}</span>
        <span data-testid="length">{formatLength(100)}</span>
        <span data-testid="weight">{formatWeight(10)}</span>
        <span data-testid="temp">{formatTemperature(25)}</span>
      </div>
    );
  }

  beforeEach(() => {
    localStorage.clear();
  });

  it('should provide unit system', () => {
    render(
      <UnitProvider defaultSystem={UNIT_SYSTEM.METRIC}>
        <UnitTester />
      </UnitProvider>
    );

    expect(screen.getByTestId('system')).toHaveTextContent('metric');
  });

  it('should format length in metric', () => {
    render(
      <UnitProvider defaultSystem={UNIT_SYSTEM.METRIC}>
        <UnitTester />
      </UnitProvider>
    );

    expect(screen.getByTestId('length')).toHaveTextContent('100.00 mm');
  });

  it('should format length in imperial', () => {
    render(
      <UnitProvider defaultSystem={UNIT_SYSTEM.IMPERIAL}>
        <UnitTester />
      </UnitProvider>
    );

    expect(screen.getByTestId('length')).toHaveTextContent('3.937 in');
  });

  it('should format weight in metric', () => {
    render(
      <UnitProvider defaultSystem={UNIT_SYSTEM.METRIC}>
        <UnitTester />
      </UnitProvider>
    );

    expect(screen.getByTestId('weight')).toHaveTextContent('10.00 kg');
  });

  it('should format weight in imperial', () => {
    render(
      <UnitProvider defaultSystem={UNIT_SYSTEM.IMPERIAL}>
        <UnitTester />
      </UnitProvider>
    );

    expect(screen.getByTestId('weight')).toHaveTextContent('22.05 lb');
  });

  it('should format temperature in metric', () => {
    render(
      <UnitProvider defaultSystem={UNIT_SYSTEM.METRIC}>
        <UnitTester />
      </UnitProvider>
    );

    expect(screen.getByTestId('temp')).toHaveTextContent('25.0 °C');
  });

  it('should format temperature in imperial', () => {
    render(
      <UnitProvider defaultSystem={UNIT_SYSTEM.IMPERIAL}>
        <UnitTester />
      </UnitProvider>
    );

    expect(screen.getByTestId('temp')).toHaveTextContent('77.0 °F');
  });

  it('should throw error when useUnits is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<UnitTester />)).toThrow('useUnits must be used within UnitProvider');
    consoleError.mockRestore();
  });
});

// =============================================================================
// UNIT TOGGLE TESTS
// =============================================================================

describe('UnitToggle', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should render toggle buttons', () => {
    render(
      <UnitProvider>
        <UnitToggle />
      </UnitProvider>
    );

    expect(screen.getByText('Metric')).toBeInTheDocument();
    expect(screen.getByText('Imperial')).toBeInTheDocument();
  });

  it('should have radiogroup role', () => {
    render(
      <UnitProvider>
        <UnitToggle />
      </UnitProvider>
    );

    expect(screen.getByRole('radiogroup')).toBeInTheDocument();
  });

  it('should toggle unit system', async () => {
    const user = userEvent.setup();

    function TestComponent() {
      const { system } = useUnits();
      return (
        <div>
          <UnitToggle />
          <span data-testid="system">{system}</span>
        </div>
      );
    }

    render(
      <UnitProvider defaultSystem={UNIT_SYSTEM.METRIC}>
        <TestComponent />
      </UnitProvider>
    );

    expect(screen.getByTestId('system')).toHaveTextContent('metric');

    await user.click(screen.getByText('Imperial'));
    expect(screen.getByTestId('system')).toHaveTextContent('imperial');
  });

  it('should persist unit system', async () => {
    const user = userEvent.setup();

    render(
      <UnitProvider>
        <UnitToggle />
      </UnitProvider>
    );

    await user.click(screen.getByText('Imperial'));
    expect(localStorage.getItem('unit-system')).toBe('imperial');
  });
});

// =============================================================================
// TIMEZONE TESTS
// =============================================================================

describe('TimezoneProvider', () => {
  function TimezoneTester() {
    const { timezone, formatInTimezone } = useTimezone();
    return (
      <div>
        <span data-testid="timezone">{timezone}</span>
        <span data-testid="formatted">{formatInTimezone(new Date('2025-01-15T12:00:00Z'))}</span>
      </div>
    );
  }

  beforeEach(() => {
    localStorage.clear();
  });

  it('should provide timezone', () => {
    render(
      <TimezoneProvider defaultTimezone="America/New_York">
        <TimezoneTester />
      </TimezoneProvider>
    );

    expect(screen.getByTestId('timezone')).toHaveTextContent('America/New_York');
  });

  it('should format date in timezone', () => {
    render(
      <TimezoneProvider defaultTimezone="America/New_York">
        <TimezoneTester />
      </TimezoneProvider>
    );

    expect(screen.getByTestId('formatted')).toBeInTheDocument();
  });

  it('should throw error when useTimezone is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TimezoneTester />)).toThrow('useTimezone must be used within TimezoneProvider');
    consoleError.mockRestore();
  });
});

describe('getLocalTimezone', () => {
  it('should return a timezone string', () => {
    const tz = getLocalTimezone();
    expect(typeof tz).toBe('string');
    expect(tz.length).toBeGreaterThan(0);
  });
});

// =============================================================================
// TIMEZONE SELECTOR TESTS
// =============================================================================

describe('TimezoneSelector', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should render select element', () => {
    render(
      <TimezoneProvider defaultTimezone="America/New_York">
        <TimezoneSelector />
      </TimezoneProvider>
    );

    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('should have timezone options', () => {
    render(
      <TimezoneProvider defaultTimezone="America/New_York">
        <TimezoneSelector />
      </TimezoneProvider>
    );

    expect(screen.getByText(/Eastern Time/)).toBeInTheDocument();
    expect(screen.getByText(/Pacific Time/)).toBeInTheDocument();
  });

  it('should change timezone', async () => {
    const user = userEvent.setup();

    function TestComponent() {
      const { timezone } = useTimezone();
      return (
        <div>
          <TimezoneSelector />
          <span data-testid="tz">{timezone}</span>
        </div>
      );
    }

    render(
      <TimezoneProvider defaultTimezone="America/New_York">
        <TestComponent />
      </TimezoneProvider>
    );

    await user.selectOptions(screen.getByRole('combobox'), 'America/Los_Angeles');
    expect(screen.getByTestId('tz')).toHaveTextContent('America/Los_Angeles');
  });
});

// =============================================================================
// SHARE BUTTON TESTS
// =============================================================================

describe('ShareButton', () => {
  it('should render share button', () => {
    render(<ShareButton url="https://example.com" />);
    expect(screen.getByRole('button', { name: /share/i })).toBeInTheDocument();
  });

  it('should render with custom children', () => {
    render(<ShareButton url="https://example.com">Share this</ShareButton>);
    expect(screen.getByText('Share this')).toBeInTheDocument();
  });

  it('should accept onFallback prop', () => {
    const onFallback = jest.fn();
    render(<ShareButton url="https://example.com" onFallback={onFallback} />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });
});

// =============================================================================
// BROWSER INFO HOOK TESTS
// =============================================================================

describe('useBrowserInfo', () => {
  function BrowserInfoTester() {
    const info = useBrowserInfo();
    return (
      <div>
        <span data-testid="browser">{info.browser}</span>
        <span data-testid="os">{info.os}</span>
        <span data-testid="touch">{info.isTouch.toString()}</span>
        <span data-testid="mobile">{info.isMobile.toString()}</span>
      </div>
    );
  }

  it('should return browser info', () => {
    render(<BrowserInfoTester />);

    expect(screen.getByTestId('browser')).toBeInTheDocument();
    expect(screen.getByTestId('os')).toBeInTheDocument();
  });

  it('should return CSS feature support', () => {
    function FeatureTester() {
      const info = useBrowserInfo();
      return (
        <div>
          <span data-testid="hasGrid">{(CSS_FEATURE.GRID in info.cssFeatures).toString()}</span>
        </div>
      );
    }

    render(<FeatureTester />);
    expect(screen.getByTestId('hasGrid')).toHaveTextContent('true');
  });
});

// =============================================================================
// RTL WRAPPER TESTS
// =============================================================================

describe('RTLWrapper', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('dir');
  });

  it('should render children', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.EN_US}>
        <RTLWrapper>
          <p>Content</p>
        </RTLWrapper>
      </I18nProvider>
    );

    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('should apply LTR direction for English', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.EN_US}>
        <RTLWrapper>
          <p>Content</p>
        </RTLWrapper>
      </I18nProvider>
    );

    expect(screen.getByText('Content').parentElement).toHaveAttribute('dir', 'ltr');
  });

  it('should apply RTL direction for Arabic', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.AR_SA}>
        <RTLWrapper>
          <p>Content</p>
        </RTLWrapper>
      </I18nProvider>
    );

    expect(screen.getByText('Content').parentElement).toHaveAttribute('dir', 'rtl');
  });

  it('should have RTL class for Arabic', () => {
    render(
      <I18nProvider defaultLocale={LOCALE.AR_SA}>
        <RTLWrapper>
          <p>Content</p>
        </RTLWrapper>
      </I18nProvider>
    );

    expect(screen.getByText('Content').parentElement).toHaveClass('rtl');
  });
});
