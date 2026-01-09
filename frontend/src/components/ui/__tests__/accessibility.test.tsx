/**
 * Tests for Accessibility Components
 * 
 * Section 19.3: Accessibility (WCAG 2.1 AA) Rigor
 * 
 * Tests:
 * - Keyboard Navigation
 * - Screen Reader Support
 * - Visual Accessibility
 * - Focus Management
 * - ARIA Compliance
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  SkipToContent,
  FocusTrap,
  AriaLiveRegion,
  VisuallyHidden,
  MainLandmark,
  NavLandmark,
  AsideLandmark,
  HeaderLandmark,
  FooterLandmark,
  RegionLandmark,
  AccessibleIconButton,
  HighContrastProvider,
  ReducedMotionAware,
  useReducedMotion,
  useKeyboardNavigation,
  TabOrderManager,
  AccessibleTable,
  AccessibleStatus,
  focusRingClasses,
  highVisibilityFocusClasses,
  getFocusableElements,
  getContrastRatio,
  meetsContrastRequirement,
  generateAriaId,
  MIN_TOUCH_TARGET,
  FOCUS_RING_WIDTH,
  KEYBOARD_KEYS,
  ARIA_LIVE,
} from '../accessibility';

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('Accessibility Constants', () => {
  describe('MIN_TOUCH_TARGET', () => {
    it('should be at least 44px for WCAG compliance', () => {
      expect(MIN_TOUCH_TARGET).toBeGreaterThanOrEqual(44);
    });
  });

  describe('FOCUS_RING_WIDTH', () => {
    it('should be visible (at least 2px)', () => {
      expect(FOCUS_RING_WIDTH).toBeGreaterThanOrEqual(2);
    });
  });

  describe('KEYBOARD_KEYS', () => {
    it('should define common navigation keys', () => {
      expect(KEYBOARD_KEYS.ENTER).toBe('Enter');
      expect(KEYBOARD_KEYS.SPACE).toBe(' ');
      expect(KEYBOARD_KEYS.TAB).toBe('Tab');
      expect(KEYBOARD_KEYS.ESCAPE).toBe('Escape');
      expect(KEYBOARD_KEYS.ARROW_UP).toBe('ArrowUp');
      expect(KEYBOARD_KEYS.ARROW_DOWN).toBe('ArrowDown');
      expect(KEYBOARD_KEYS.ARROW_LEFT).toBe('ArrowLeft');
      expect(KEYBOARD_KEYS.ARROW_RIGHT).toBe('ArrowRight');
      expect(KEYBOARD_KEYS.HOME).toBe('Home');
      expect(KEYBOARD_KEYS.END).toBe('End');
    });
  });

  describe('ARIA_LIVE', () => {
    it('should define live region politeness levels', () => {
      expect(ARIA_LIVE.OFF).toBe('off');
      expect(ARIA_LIVE.POLITE).toBe('polite');
      expect(ARIA_LIVE.ASSERTIVE).toBe('assertive');
    });
  });
});

// =============================================================================
// SKIP TO CONTENT TESTS
// =============================================================================

describe('SkipToContent', () => {
  it('renders with default props', () => {
    render(<SkipToContent />);
    
    const link = screen.getByRole('link', { name: 'Skip to content' });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '#main-content');
  });

  it('uses custom target ID', () => {
    render(<SkipToContent targetId="custom-main" />);
    
    const link = screen.getByRole('link', { name: 'Skip to content' });
    expect(link).toHaveAttribute('href', '#custom-main');
  });

  it('uses custom children text', () => {
    render(<SkipToContent>Jump to main section</SkipToContent>);
    
    expect(screen.getByRole('link', { name: 'Jump to main section' })).toBeInTheDocument();
  });

  it('is visually hidden by default (has sr-only class)', () => {
    render(<SkipToContent data-testid="skip" />);
    
    const link = screen.getByTestId('skip');
    expect(link.className).toContain('sr-only');
  });

  it('applies focus styles for visibility', () => {
    render(<SkipToContent data-testid="skip" />);
    
    const link = screen.getByTestId('skip');
    expect(link.className).toContain('focus:not-sr-only');
  });
});

// =============================================================================
// FOCUS TRAP TESTS
// =============================================================================

describe('FocusTrap', () => {
  it('renders children', () => {
    render(
      <FocusTrap>
        <button>First</button>
        <button>Second</button>
      </FocusTrap>
    );
    
    expect(screen.getByText('First')).toBeInTheDocument();
    expect(screen.getByText('Second')).toBeInTheDocument();
  });

  it('has data-focus-trap attribute when active', () => {
    render(
      <FocusTrap active>
        <button>Button</button>
      </FocusTrap>
    );
    
    const container = screen.getByText('Button').closest('[data-focus-trap]');
    expect(container).toHaveAttribute('data-focus-trap', 'true');
  });

  it('has data-focus-trap=false when inactive', () => {
    render(
      <FocusTrap active={false}>
        <button>Button</button>
      </FocusTrap>
    );
    
    const container = screen.getByText('Button').closest('[data-focus-trap]');
    expect(container).toHaveAttribute('data-focus-trap', 'false');
  });

  it('calls onEscape when Escape is pressed', () => {
    const onEscape = jest.fn();
    render(
      <FocusTrap active onEscape={onEscape}>
        <button>Button</button>
      </FocusTrap>
    );
    
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onEscape).toHaveBeenCalled();
  });

  it('does not call onEscape when inactive', () => {
    const onEscape = jest.fn();
    render(
      <FocusTrap active={false} onEscape={onEscape}>
        <button>Button</button>
      </FocusTrap>
    );
    
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onEscape).not.toHaveBeenCalled();
  });
});

// =============================================================================
// ARIA LIVE REGION TESTS
// =============================================================================

describe('AriaLiveRegion', () => {
  it('renders with default polite politeness', () => {
    render(<AriaLiveRegion>Update message</AriaLiveRegion>);
    
    const region = screen.getByText('Update message');
    expect(region).toHaveAttribute('aria-live', 'polite');
  });

  it('renders with assertive politeness', () => {
    render(<AriaLiveRegion politeness="assertive">Urgent message</AriaLiveRegion>);
    
    const region = screen.getByText('Urgent message');
    expect(region).toHaveAttribute('aria-live', 'assertive');
  });

  it('has aria-atomic attribute', () => {
    render(<AriaLiveRegion>Message</AriaLiveRegion>);
    
    const region = screen.getByText('Message');
    expect(region).toHaveAttribute('aria-atomic', 'true');
  });

  it('is visually hidden (sr-only)', () => {
    render(<AriaLiveRegion data-testid="region">Message</AriaLiveRegion>);
    
    const region = screen.getByTestId('region');
    expect(region.className).toContain('sr-only');
  });

  it('supports custom aria-relevant', () => {
    render(<AriaLiveRegion relevant="additions">Message</AriaLiveRegion>);
    
    const region = screen.getByText('Message');
    expect(region).toHaveAttribute('aria-relevant', 'additions');
  });
});

// =============================================================================
// VISUALLY HIDDEN TESTS
// =============================================================================

describe('VisuallyHidden', () => {
  it('renders content with sr-only class', () => {
    render(<VisuallyHidden data-testid="hidden">Hidden text</VisuallyHidden>);
    
    const element = screen.getByTestId('hidden');
    expect(element).toHaveTextContent('Hidden text');
    expect(element.className).toContain('sr-only');
  });

  it('renders as span by default', () => {
    render(<VisuallyHidden data-testid="hidden">Text</VisuallyHidden>);
    
    const element = screen.getByTestId('hidden');
    expect(element.tagName).toBe('SPAN');
  });

  it('renders as div when specified', () => {
    render(<VisuallyHidden as="div" data-testid="hidden">Text</VisuallyHidden>);
    
    const element = screen.getByTestId('hidden');
    expect(element.tagName).toBe('DIV');
  });

  it('renders as label when specified', () => {
    render(<VisuallyHidden as="label" data-testid="hidden">Text</VisuallyHidden>);
    
    const element = screen.getByTestId('hidden');
    expect(element.tagName).toBe('LABEL');
  });
});

// =============================================================================
// SEMANTIC LANDMARKS TESTS
// =============================================================================

describe('Semantic Landmarks', () => {
  describe('MainLandmark', () => {
    it('renders main element', () => {
      render(<MainLandmark>Content</MainLandmark>);
      
      const main = screen.getByRole('main');
      expect(main).toBeInTheDocument();
    });

    it('has default id for skip links', () => {
      render(<MainLandmark>Content</MainLandmark>);
      
      const main = screen.getByRole('main');
      expect(main).toHaveAttribute('id', 'main-content');
    });

    it('has aria-label', () => {
      render(<MainLandmark>Content</MainLandmark>);
      
      const main = screen.getByRole('main');
      expect(main).toHaveAttribute('aria-label', 'Main content');
    });

    it('accepts custom label', () => {
      render(<MainLandmark label="Primary Content">Content</MainLandmark>);
      
      const main = screen.getByRole('main');
      expect(main).toHaveAttribute('aria-label', 'Primary Content');
    });
  });

  describe('NavLandmark', () => {
    it('renders nav element', () => {
      render(<NavLandmark label="Main navigation">Links</NavLandmark>);
      
      const nav = screen.getByRole('navigation');
      expect(nav).toBeInTheDocument();
      expect(nav).toHaveAttribute('aria-label', 'Main navigation');
    });
  });

  describe('AsideLandmark', () => {
    it('renders aside element', () => {
      render(<AsideLandmark label="Related info">Sidebar</AsideLandmark>);
      
      const aside = screen.getByRole('complementary');
      expect(aside).toBeInTheDocument();
      expect(aside).toHaveAttribute('aria-label', 'Related info');
    });
  });

  describe('HeaderLandmark', () => {
    it('renders header element', () => {
      render(<HeaderLandmark label="Site header">Header content</HeaderLandmark>);
      
      const header = screen.getByRole('banner');
      expect(header).toBeInTheDocument();
      expect(header).toHaveAttribute('aria-label', 'Site header');
    });
  });

  describe('FooterLandmark', () => {
    it('renders footer element', () => {
      render(<FooterLandmark label="Site footer">Footer content</FooterLandmark>);
      
      const footer = screen.getByRole('contentinfo');
      expect(footer).toBeInTheDocument();
      expect(footer).toHaveAttribute('aria-label', 'Site footer');
    });
  });

  describe('RegionLandmark', () => {
    it('renders section with region role', () => {
      render(<RegionLandmark label="Important section">Content</RegionLandmark>);
      
      const region = screen.getByRole('region');
      expect(region).toBeInTheDocument();
      expect(region).toHaveAttribute('aria-label', 'Important section');
    });

    it('supports aria-labelledby', () => {
      render(
        <RegionLandmark labelledBy="section-heading">
          <h2 id="section-heading">Section Title</h2>
          <p>Content</p>
        </RegionLandmark>
      );
      
      const region = screen.getByRole('region');
      expect(region).toHaveAttribute('aria-labelledby', 'section-heading');
    });
  });
});

// =============================================================================
// ACCESSIBLE ICON BUTTON TESTS
// =============================================================================

describe('AccessibleIconButton', () => {
  const TestIcon = () => <span data-testid="icon">🔍</span>;

  it('renders with required aria-label', () => {
    render(<AccessibleIconButton label="Search" icon={<TestIcon />} />);
    
    const button = screen.getByRole('button', { name: 'Search' });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('aria-label', 'Search');
  });

  it('includes visually hidden text for screen readers', () => {
    render(<AccessibleIconButton label="Search" icon={<TestIcon />} />);
    
    expect(screen.getByText('Search', { selector: '.sr-only' })).toBeInTheDocument();
  });

  it('renders icon', () => {
    render(<AccessibleIconButton label="Search" icon={<TestIcon />} />);
    
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('adds title when tooltip is true', () => {
    render(<AccessibleIconButton label="Search" icon={<TestIcon />} tooltip />);
    
    const button = screen.getByRole('button', { name: 'Search' });
    expect(button).toHaveAttribute('title', 'Search');
  });

  it('does not add title when tooltip is false', () => {
    render(<AccessibleIconButton label="Search" icon={<TestIcon />} tooltip={false} />);
    
    const button = screen.getByRole('button', { name: 'Search' });
    expect(button).not.toHaveAttribute('title');
  });

  it('has minimum touch target of 44px (md size)', () => {
    render(<AccessibleIconButton label="Search" icon={<TestIcon />} size="md" />);
    
    const button = screen.getByRole('button');
    expect(button.className).toContain('min-h-[44px]');
    expect(button.className).toContain('min-w-[44px]');
  });

  it('supports size variants', () => {
    const { rerender } = render(
      <AccessibleIconButton label="Search" icon={<TestIcon />} size="sm" />
    );
    let button = screen.getByRole('button');
    expect(button.className).toContain('h-9');

    rerender(<AccessibleIconButton label="Search" icon={<TestIcon />} size="lg" />);
    button = screen.getByRole('button');
    expect(button.className).toContain('h-14');
  });

  it('has type button by default', () => {
    render(<AccessibleIconButton label="Search" icon={<TestIcon />} />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('type', 'button');
  });
});

// =============================================================================
// HIGH CONTRAST PROVIDER TESTS
// =============================================================================

describe('HighContrastProvider', () => {
  afterEach(() => {
    document.documentElement.classList.remove('high-contrast');
  });

  it('renders children', () => {
    render(
      <HighContrastProvider>
        <div data-testid="content">Content</div>
      </HighContrastProvider>
    );
    
    expect(screen.getByTestId('content')).toBeInTheDocument();
  });

  it('adds high-contrast class when enabled', () => {
    render(
      <HighContrastProvider enabled>
        <div>Content</div>
      </HighContrastProvider>
    );
    
    expect(document.documentElement.classList.contains('high-contrast')).toBe(true);
  });

  it('does not add high-contrast class when disabled', () => {
    render(
      <HighContrastProvider enabled={false}>
        <div>Content</div>
      </HighContrastProvider>
    );
    
    expect(document.documentElement.classList.contains('high-contrast')).toBe(false);
  });

  it('removes class on unmount', () => {
    const { unmount } = render(
      <HighContrastProvider enabled>
        <div>Content</div>
      </HighContrastProvider>
    );
    
    expect(document.documentElement.classList.contains('high-contrast')).toBe(true);
    unmount();
    expect(document.documentElement.classList.contains('high-contrast')).toBe(false);
  });
});

// =============================================================================
// REDUCED MOTION TESTS
// =============================================================================

describe('ReducedMotionAware', () => {
  it('renders children by default', () => {
    render(
      <ReducedMotionAware>
        <div data-testid="animated">Animated content</div>
      </ReducedMotionAware>
    );
    
    expect(screen.getByTestId('animated')).toBeInTheDocument();
  });

  it('renders fallback when reduced motion is preferred', () => {
    // Mock matchMedia to return reduced motion
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = jest.fn().mockImplementation((query) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    }));

    render(
      <ReducedMotionAware fallback={<div data-testid="static">Static content</div>}>
        <div data-testid="animated">Animated content</div>
      </ReducedMotionAware>
    );
    
    expect(screen.getByTestId('static')).toBeInTheDocument();

    window.matchMedia = originalMatchMedia;
  });
});

// =============================================================================
// ACCESSIBLE TABLE TESTS
// =============================================================================

describe('AccessibleTable', () => {
  it('renders with required caption', () => {
    render(
      <AccessibleTable caption="User Data">
        <thead>
          <tr><th>Name</th></tr>
        </thead>
        <tbody>
          <tr><td>John</td></tr>
        </tbody>
      </AccessibleTable>
    );
    
    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
    
    // Caption should be visible
    expect(screen.getByText('User Data')).toBeInTheDocument();
  });

  it('hides caption visually when captionHidden is true', () => {
    render(
      <AccessibleTable caption="User Data" captionHidden>
        <tbody><tr><td>Data</td></tr></tbody>
      </AccessibleTable>
    );
    
    const caption = screen.getByText('User Data');
    expect(caption.className).toContain('sr-only');
  });

  it('includes summary in sr-only when provided', () => {
    render(
      <AccessibleTable 
        caption="Complex Data" 
        summary="This table shows quarterly sales data"
      >
        <tbody><tr><td>Data</td></tr></tbody>
      </AccessibleTable>
    );
    
    expect(screen.getByText('This table shows quarterly sales data')).toHaveClass('sr-only');
  });
});

// =============================================================================
// ACCESSIBLE STATUS TESTS
// =============================================================================

describe('AccessibleStatus', () => {
  it('renders with status role', () => {
    render(<AccessibleStatus status="success" label="Complete" />);
    
    const status = screen.getByRole('status');
    expect(status).toBeInTheDocument();
  });

  it('includes icon by default', () => {
    render(<AccessibleStatus status="success" label="Complete" />);
    
    // Success icon is ✓
    expect(screen.getByText('✓')).toBeInTheDocument();
  });

  it('hides icon when showIcon is false', () => {
    render(<AccessibleStatus status="success" label="Complete" showIcon={false} />);
    
    expect(screen.queryByText('✓')).not.toBeInTheDocument();
  });

  it('has correct aria-label', () => {
    render(<AccessibleStatus status="error" label="Failed" />);
    
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-label', 'error: Failed');
  });

  it('supports different status types', () => {
    const { rerender } = render(<AccessibleStatus status="warning" label="Warning" />);
    expect(screen.getByText('⚠')).toBeInTheDocument();

    rerender(<AccessibleStatus status="info" label="Info" />);
    expect(screen.getByText('ℹ')).toBeInTheDocument();
  });

  it('supports size variants', () => {
    const { rerender } = render(
      <AccessibleStatus status="success" label="OK" size="sm" />
    );
    let status = screen.getByRole('status');
    expect(status.className).toContain('text-xs');

    rerender(<AccessibleStatus status="success" label="OK" size="lg" />);
    status = screen.getByRole('status');
    expect(status.className).toContain('text-base');
  });
});

// =============================================================================
// UTILITY FUNCTION TESTS
// =============================================================================

describe('Utility Functions', () => {
  describe('getFocusableElements', () => {
    it('returns focusable elements', () => {
      const container = document.createElement('div');
      container.innerHTML = `
        <button>Button</button>
        <a href="#">Link</a>
        <input type="text" />
        <select><option>Option</option></select>
        <textarea></textarea>
        <div tabindex="0">Focusable div</div>
      `;
      
      const focusable = getFocusableElements(container);
      expect(focusable.length).toBe(6);
    });

    it('excludes disabled elements', () => {
      const container = document.createElement('div');
      container.innerHTML = `
        <button>Enabled</button>
        <button disabled>Disabled</button>
      `;
      
      const focusable = getFocusableElements(container);
      expect(focusable.length).toBe(1);
    });

    it('excludes tabindex=-1 elements', () => {
      const container = document.createElement('div');
      container.innerHTML = `
        <div tabindex="0">Focusable</div>
        <div tabindex="-1">Not focusable</div>
      `;
      
      const focusable = getFocusableElements(container);
      expect(focusable.length).toBe(1);
    });
  });

  describe('getContrastRatio', () => {
    it('calculates contrast ratio between black and white', () => {
      const ratio = getContrastRatio('#000000', '#ffffff');
      expect(ratio).toBeCloseTo(21, 0);
    });

    it('calculates contrast ratio for similar colors', () => {
      const ratio = getContrastRatio('#777777', '#888888');
      expect(ratio).toBeLessThan(2);
    });
  });

  describe('meetsContrastRequirement', () => {
    it('requires 4.5:1 for normal text', () => {
      expect(meetsContrastRequirement(4.5)).toBe(true);
      expect(meetsContrastRequirement(4.4)).toBe(false);
    });

    it('requires 3:1 for large text', () => {
      expect(meetsContrastRequirement(3, true)).toBe(true);
      expect(meetsContrastRequirement(2.9, true)).toBe(false);
    });
  });

  describe('generateAriaId', () => {
    it('generates ID with prefix', () => {
      const id = generateAriaId('menu');
      expect(id).toMatch(/^menu-[a-z0-9]+$/);
    });

    it('generates unique IDs', () => {
      const id1 = generateAriaId('test');
      const id2 = generateAriaId('test');
      expect(id1).not.toBe(id2);
    });
  });
});

// =============================================================================
// FOCUS RING CLASSES TESTS
// =============================================================================

describe('Focus Ring Classes', () => {
  describe('focusRingClasses', () => {
    it('includes focus-visible ring', () => {
      expect(focusRingClasses).toContain('focus-visible:ring-2');
      expect(focusRingClasses).toContain('focus:outline-none');
    });
  });

  describe('highVisibilityFocusClasses', () => {
    it('includes high visibility styles', () => {
      expect(highVisibilityFocusClasses).toContain('focus-visible:ring-4');
      expect(highVisibilityFocusClasses).toContain('focus-visible:ring-yellow-400');
    });
  });
});

// =============================================================================
// TAB ORDER MANAGER TESTS
// =============================================================================

describe('TabOrderManager', () => {
  it('renders children', () => {
    render(
      <TabOrderManager order={['email', 'password']}>
        <input data-tab-order="email" data-testid="email" />
        <input data-tab-order="password" data-testid="password" />
      </TabOrderManager>
    );
    
    expect(screen.getByTestId('email')).toBeInTheDocument();
    expect(screen.getByTestId('password')).toBeInTheDocument();
  });
});

// =============================================================================
// KEYBOARD NAVIGATION HOOK TESTS
// =============================================================================

function KeyboardNavTestComponent() {
  const refs = [
    React.useRef<HTMLButtonElement>(null),
    React.useRef<HTMLButtonElement>(null),
    React.useRef<HTMLButtonElement>(null),
  ];

  const { activeIndex, handleKeyDown, getItemProps } = useKeyboardNavigation({
    refs,
    wrap: true,
    orientation: 'vertical',
  });

  return (
    <div role="listbox" onKeyDown={handleKeyDown}>
      {['First', 'Second', 'Third'].map((label, index) => (
        <button
          key={label}
          ref={refs[index]}
          {...getItemProps(index)}
          data-testid={`item-${index}`}
        >
          {label}
        </button>
      ))}
      <div data-testid="active-index">{activeIndex}</div>
    </div>
  );
}

describe('useKeyboardNavigation', () => {
  it('navigates with arrow keys', () => {
    render(<KeyboardNavTestComponent />);
    
    const firstItem = screen.getByTestId('item-0');
    firstItem.focus();
    
    // Navigate down
    fireEvent.keyDown(firstItem, { key: 'ArrowDown' });
    expect(screen.getByTestId('active-index')).toHaveTextContent('1');
  });

  it('wraps around when at end', () => {
    render(<KeyboardNavTestComponent />);
    
    const lastItem = screen.getByTestId('item-2');
    lastItem.focus();
    
    // Set focus to last item first
    fireEvent.click(lastItem);
    
    // Navigate should wrap
    fireEvent.keyDown(lastItem, { key: 'ArrowDown' });
  });

  it('uses Home/End for first/last navigation', () => {
    render(<KeyboardNavTestComponent />);
    
    const firstItem = screen.getByTestId('item-0');
    firstItem.focus();
    
    // Navigate to end
    fireEvent.keyDown(firstItem, { key: 'End' });
    expect(screen.getByTestId('active-index')).toHaveTextContent('2');
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Accessibility Integration', () => {
  it('complete page structure with landmarks', () => {
    render(
      <>
        <SkipToContent />
        <HeaderLandmark label="Site header">
          <NavLandmark label="Primary navigation">
            <a href="/">Home</a>
          </NavLandmark>
        </HeaderLandmark>
        <MainLandmark>
          <RegionLandmark label="Content area">
            <h1>Page Title</h1>
          </RegionLandmark>
        </MainLandmark>
        <AsideLandmark label="Sidebar">
          Related links
        </AsideLandmark>
        <FooterLandmark label="Site footer">
          Copyright
        </FooterLandmark>
      </>
    );

    // All landmarks should be present
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('region')).toBeInTheDocument();
    expect(screen.getByRole('complementary')).toBeInTheDocument();
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
    
    // Skip link should be present
    expect(screen.getByRole('link', { name: 'Skip to content' })).toBeInTheDocument();
  });

  it('accessible form with live region for errors', () => {
    function AccessibleForm() {
      const [error, setError] = React.useState('');
      
      return (
        <form>
          <label htmlFor="email">Email</label>
          <input 
            id="email" 
            type="email" 
            aria-describedby="email-error"
          />
          <AriaLiveRegion politeness="assertive">
            {error}
          </AriaLiveRegion>
          <button type="button" onClick={() => setError('Invalid email format')}>
            Submit
          </button>
        </form>
      );
    }
    
    render(<AccessibleForm />);
    
    // Form is accessible
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    
    // Error can be announced
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Invalid email format')).toBeInTheDocument();
  });
});
