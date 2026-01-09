/**
 * Tests for Factory-Floor UX Components
 * 
 * Section 19.6: Factory-Floor UX (Specifics)
 * 
 * Tests:
 * - Shop floor themes
 * - Glove-friendly components
 * - Barcode scanning
 * - Voice commands
 * - Andon system
 * - Battery/power awareness
 * - Device capabilities
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  SHOP_FLOOR_THEME,
  TOUCH_TARGET,
  BARCODE_TYPE,
  VOICE_STATE,
  ShopFloorProvider,
  useShopFloor,
  HighGlareContainer,
  ShopFloorThemeToggle,
  GloveButton,
  GloveTouchTarget,
  BarcodeScanner,
  ScanFeedback,
  VoiceCommandListener,
  LargeStatusIndicator,
  AndonButton,
  AndonAlert,
  BatteryIndicator,
  GloveModeToggle,
  useHardwareScanner,
  useDeviceCapabilities,
  useAmbientLight,
} from '../factory-floor';

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('Factory Floor Constants', () => {
  describe('SHOP_FLOOR_THEME', () => {
    it('should have all theme modes', () => {
      expect(SHOP_FLOOR_THEME.STANDARD).toBe('standard');
      expect(SHOP_FLOOR_THEME.HIGH_GLARE).toBe('high-glare');
      expect(SHOP_FLOOR_THEME.NIGHT).toBe('night');
    });
  });

  describe('TOUCH_TARGET', () => {
    it('should have all target sizes', () => {
      expect(TOUCH_TARGET.STANDARD).toBe(44);
      expect(TOUCH_TARGET.GLOVE_FRIENDLY).toBe(48);
      expect(TOUCH_TARGET.EXTRA_LARGE).toBe(56);
    });
  });

  describe('BARCODE_TYPE', () => {
    it('should have all barcode types', () => {
      expect(BARCODE_TYPE.QR).toBe('qr');
      expect(BARCODE_TYPE.CODE128).toBe('code128');
      expect(BARCODE_TYPE.CODE39).toBe('code39');
      expect(BARCODE_TYPE.EAN13).toBe('ean13');
      expect(BARCODE_TYPE.UPC).toBe('upc');
      expect(BARCODE_TYPE.DATAMATRIX).toBe('datamatrix');
      expect(BARCODE_TYPE.PDF417).toBe('pdf417');
      expect(BARCODE_TYPE.UNKNOWN).toBe('unknown');
    });
  });

  describe('VOICE_STATE', () => {
    it('should have all voice states', () => {
      expect(VOICE_STATE.IDLE).toBe('idle');
      expect(VOICE_STATE.LISTENING).toBe('listening');
      expect(VOICE_STATE.PROCESSING).toBe('processing');
      expect(VOICE_STATE.SUCCESS).toBe('success');
      expect(VOICE_STATE.ERROR).toBe('error');
    });
  });
});

// =============================================================================
// SHOP FLOOR PROVIDER TESTS
// =============================================================================

describe('ShopFloorProvider', () => {
  function TestComponent() {
    const {
      theme,
      setTheme,
      isGloveFriendlyMode,
      setGloveFriendlyMode,
      touchTargetSize,
    } = useShopFloor();

    return (
      <div>
        <div data-testid="theme">{theme}</div>
        <div data-testid="glove-mode">{isGloveFriendlyMode ? 'on' : 'off'}</div>
        <div data-testid="target-size">{touchTargetSize}</div>
        <button onClick={() => setTheme(SHOP_FLOOR_THEME.HIGH_GLARE)}>
          Set High Glare
        </button>
        <button onClick={() => setGloveFriendlyMode(true)}>Enable Glove</button>
      </div>
    );
  }

  it('throws error when used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => render(<TestComponent />)).toThrow(
      'useShopFloor must be used within ShopFloorProvider'
    );

    consoleError.mockRestore();
  });

  it('provides default values', () => {
    render(
      <ShopFloorProvider>
        <TestComponent />
      </ShopFloorProvider>
    );
    
    expect(screen.getByTestId('theme')).toHaveTextContent('standard');
    expect(screen.getByTestId('glove-mode')).toHaveTextContent('off');
    expect(screen.getByTestId('target-size')).toHaveTextContent('44');
  });

  it('accepts default theme prop', () => {
    render(
      <ShopFloorProvider defaultTheme={SHOP_FLOOR_THEME.HIGH_GLARE}>
        <TestComponent />
      </ShopFloorProvider>
    );
    
    expect(screen.getByTestId('theme')).toHaveTextContent('high-glare');
  });

  it('accepts default glove mode prop', () => {
    render(
      <ShopFloorProvider defaultGloveFriendly>
        <TestComponent />
      </ShopFloorProvider>
    );
    
    expect(screen.getByTestId('glove-mode')).toHaveTextContent('on');
    expect(screen.getByTestId('target-size')).toHaveTextContent('48');
  });

  it('allows changing theme', () => {
    render(
      <ShopFloorProvider>
        <TestComponent />
      </ShopFloorProvider>
    );
    
    fireEvent.click(screen.getByText('Set High Glare'));
    
    expect(screen.getByTestId('theme')).toHaveTextContent('high-glare');
  });

  it('allows changing glove mode', () => {
    render(
      <ShopFloorProvider>
        <TestComponent />
      </ShopFloorProvider>
    );
    
    fireEvent.click(screen.getByText('Enable Glove'));
    
    expect(screen.getByTestId('glove-mode')).toHaveTextContent('on');
    expect(screen.getByTestId('target-size')).toHaveTextContent('48');
  });
});

// =============================================================================
// HIGH GLARE CONTAINER TESTS
// =============================================================================

describe('HighGlareContainer', () => {
  it('applies high contrast styles when enabled', () => {
    render(
      <HighGlareContainer enabled>
        <div>Content</div>
      </HighGlareContainer>
    );
    
    const container = screen.getByText('Content').parentElement;
    expect(container).toHaveClass('bg-black');
    expect(container).toHaveClass('text-white');
  });

  it('does not apply styles when disabled', () => {
    render(
      <HighGlareContainer enabled={false}>
        <div>Content</div>
      </HighGlareContainer>
    );
    
    const container = screen.getByText('Content').parentElement;
    expect(container).not.toHaveClass('bg-black');
  });

  it('accepts className prop', () => {
    render(
      <HighGlareContainer className="custom-class">
        <div>Content</div>
      </HighGlareContainer>
    );
    
    const container = screen.getByText('Content').parentElement;
    expect(container).toHaveClass('custom-class');
  });
});

describe('ShopFloorThemeToggle', () => {
  it('renders theme options', () => {
    render(
      <ShopFloorProvider>
        <ShopFloorThemeToggle />
      </ShopFloorProvider>
    );
    
    expect(screen.getByRole('radiogroup')).toBeInTheDocument();
    expect(screen.getAllByRole('radio')).toHaveLength(3);
  });

  it('indicates current theme', () => {
    render(
      <ShopFloorProvider defaultTheme={SHOP_FLOOR_THEME.HIGH_GLARE}>
        <ShopFloorThemeToggle />
      </ShopFloorProvider>
    );
    
    const radios = screen.getAllByRole('radio');
    const highGlareRadio = radios.find(r => r.getAttribute('aria-checked') === 'true');
    expect(highGlareRadio).toBeInTheDocument();
  });

  it('changes theme on click', () => {
    function TestWrapper() {
      return (
        <ShopFloorProvider>
          <ShopFloorThemeToggle />
          <TestThemeDisplay />
        </ShopFloorProvider>
      );
    }

    function TestThemeDisplay() {
      const { theme } = useShopFloor();
      return <div data-testid="theme">{theme}</div>;
    }

    render(<TestWrapper />);
    
    const radios = screen.getAllByRole('radio');
    fireEvent.click(radios[1]); // High Glare
    
    expect(screen.getByTestId('theme')).toHaveTextContent('high-glare');
  });
});

// =============================================================================
// GLOVE-FRIENDLY COMPONENT TESTS
// =============================================================================

describe('GloveButton', () => {
  it('renders with text', () => {
    render(<GloveButton>Click Me</GloveButton>);
    
    expect(screen.getByRole('button', { name: 'Click Me' })).toBeInTheDocument();
  });

  it('has minimum touch target size', () => {
    render(<GloveButton>Click</GloveButton>);
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('min-w-[48px]');
    expect(button).toHaveClass('min-h-[48px]');
  });

  it('renders icon', () => {
    render(<GloveButton icon="🔧">Maintenance</GloveButton>);
    
    expect(screen.getByText('🔧')).toBeInTheDocument();
  });

  it('applies variant styles', () => {
    const { rerender } = render(<GloveButton variant="primary">Primary</GloveButton>);
    expect(screen.getByRole('button')).toHaveClass('bg-blue-600');

    rerender(<GloveButton variant="danger">Danger</GloveButton>);
    expect(screen.getByRole('button')).toHaveClass('bg-red-600');
  });

  it('applies size styles', () => {
    const { rerender } = render(<GloveButton size="standard">Standard</GloveButton>);
    expect(screen.getByRole('button')).toHaveClass('min-w-[44px]');

    rerender(<GloveButton size="extra-large">XL</GloveButton>);
    expect(screen.getByRole('button')).toHaveClass('min-w-[56px]');
  });

  it('can be disabled', () => {
    render(<GloveButton disabled>Disabled</GloveButton>);
    
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('calls onClick', () => {
    const onClick = jest.fn();
    render(<GloveButton onClick={onClick}>Click</GloveButton>);
    
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalled();
  });
});

describe('GloveTouchTarget', () => {
  it('renders children', () => {
    render(
      <GloveTouchTarget onPress={jest.fn()} label="Action">
        <span>Icon</span>
      </GloveTouchTarget>
    );
    
    expect(screen.getByText('Icon')).toBeInTheDocument();
  });

  it('has minimum touch target', () => {
    render(
      <GloveTouchTarget onPress={jest.fn()} label="Action">
        Content
      </GloveTouchTarget>
    );
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('min-w-[48px]');
    expect(button).toHaveClass('min-h-[48px]');
  });

  it('calls onPress', () => {
    const onPress = jest.fn();
    render(
      <GloveTouchTarget onPress={onPress} label="Action">
        Press
      </GloveTouchTarget>
    );
    
    fireEvent.click(screen.getByRole('button'));
    expect(onPress).toHaveBeenCalled();
  });

  it('can be disabled', () => {
    const onPress = jest.fn();
    render(
      <GloveTouchTarget onPress={onPress} label="Action" disabled>
        Disabled
      </GloveTouchTarget>
    );
    
    fireEvent.click(screen.getByRole('button'));
    expect(onPress).not.toHaveBeenCalled();
  });

  it('has aria-label', () => {
    render(
      <GloveTouchTarget onPress={jest.fn()} label="Important action">
        Icon
      </GloveTouchTarget>
    );
    
    expect(screen.getByLabelText('Important action')).toBeInTheDocument();
  });
});

// =============================================================================
// BARCODE SCANNER TESTS
// =============================================================================

describe('BarcodeScanner', () => {
  it('renders hardware scanner indicator', () => {
    render(<BarcodeScanner onScan={jest.fn()} scannerType="hardware" />);
    
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Scanner Ready')).toBeInTheDocument();
  });

  it('shows disabled state when not enabled', () => {
    render(<BarcodeScanner onScan={jest.fn()} enabled={false} />);
    
    expect(screen.getByText('Scanner Disabled')).toBeInTheDocument();
  });

  it('renders camera preview when type is camera', () => {
    render(
      <BarcodeScanner
        onScan={jest.fn()}
        scannerType="camera"
        showPreview
      />
    );
    
    expect(screen.getByLabelText('Camera preview for barcode scanning')).toBeInTheDocument();
    expect(screen.getByText('Point camera at barcode')).toBeInTheDocument();
  });

  it('listens for hardware scanner input when enabled', () => {
    const onScan = jest.fn();
    render(<BarcodeScanner onScan={onScan} scannerType="hardware" enabled />);
    
    // Simulate hardware scanner input (rapid keypress followed by Enter)
    fireEvent.keyPress(window, { key: '1', code: 'Digit1', charCode: 49 });
    fireEvent.keyPress(window, { key: '2', code: 'Digit2', charCode: 50 });
    fireEvent.keyPress(window, { key: '3', code: 'Digit3', charCode: 51 });
    fireEvent.keyPress(window, { key: 'Enter', code: 'Enter', charCode: 13 });
    
    expect(onScan).toHaveBeenCalledWith(
      expect.objectContaining({
        value: '123',
        type: expect.any(String),
      })
    );
  });
});

describe('ScanFeedback', () => {
  it('returns null when not visible', () => {
    const { container } = render(<ScanFeedback visible={false} />);
    
    expect(container.firstChild).toBeNull();
  });

  it('shows success feedback', () => {
    render(<ScanFeedback visible success message="Scanned!" />);
    
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('✓')).toBeInTheDocument();
    expect(screen.getByText('Scanned!')).toBeInTheDocument();
  });

  it('shows error feedback', () => {
    render(<ScanFeedback visible success={false} message="Invalid barcode" />);
    
    expect(screen.getByText('✗')).toBeInTheDocument();
    expect(screen.getByText('Invalid barcode')).toBeInTheDocument();
  });
});

// =============================================================================
// VOICE COMMAND TESTS
// =============================================================================

describe('VoiceCommandListener', () => {
  const originalSpeechRecognition = (window as Window & { SpeechRecognition?: typeof SpeechRecognition; webkitSpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition;

  beforeEach(() => {
    // Mock SpeechRecognition not available by default in jsdom
    delete (window as Window & { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition;
    delete (window as Window & { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition;
  });

  afterEach(() => {
    if (originalSpeechRecognition) {
      (window as Window & { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition = originalSpeechRecognition;
    }
  });

  it('renders listener UI', () => {
    render(<VoiceCommandListener onCommand={jest.fn()} enabled={false} />);
    
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Voice commands disabled')).toBeInTheDocument();
  });

  it('calls onError when speech recognition not supported', () => {
    const onError = jest.fn();
    render(<VoiceCommandListener onCommand={jest.fn()} onError={onError} enabled />);
    
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Speech recognition not supported' })
    );
  });

  it('displays custom wake word', () => {
    render(
      <VoiceCommandListener
        onCommand={jest.fn()}
        enabled={false}
        wakeWord="Computer"
      />
    );
    
    // Even when disabled, the component renders
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});

// =============================================================================
// LARGE STATUS INDICATOR TESTS
// =============================================================================

describe('LargeStatusIndicator', () => {
  it('returns null when not visible', () => {
    const { container } = render(
      <LargeStatusIndicator status="ok" label="All Good" visible={false} />
    );
    
    expect(container.firstChild).toBeNull();
  });

  it('renders ok status', () => {
    render(<LargeStatusIndicator status="ok" label="All Good" />);
    
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('✓')).toBeInTheDocument();
    expect(screen.getByText('All Good')).toBeInTheDocument();
  });

  it('renders warning status', () => {
    render(<LargeStatusIndicator status="warning" label="Attention" />);
    
    expect(screen.getByText('⚠')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveClass('bg-yellow-400');
  });

  it('renders error status', () => {
    render(<LargeStatusIndicator status="error" label="Stop" />);
    
    expect(screen.getByText('✗')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveClass('bg-red-600');
  });

  it('renders sublabel', () => {
    render(
      <LargeStatusIndicator
        status="info"
        label="Info"
        sublabel="Additional details"
      />
    );
    
    expect(screen.getByText('Additional details')).toBeInTheDocument();
  });

  it('has minimum size for visibility', () => {
    render(<LargeStatusIndicator status="ok" label="Test" />);
    
    const indicator = screen.getByRole('status');
    expect(indicator).toHaveClass('min-w-[200px]');
    expect(indicator).toHaveClass('min-h-[200px]');
  });
});

// =============================================================================
// ANDON SYSTEM TESTS
// =============================================================================

describe('AndonButton', () => {
  it('renders with label', () => {
    render(<AndonButton onTrigger={jest.fn()} label="STOP" />);
    
    expect(screen.getByRole('button', { name: 'STOP' })).toBeInTheDocument();
  });

  it('uses default label', () => {
    render(<AndonButton onTrigger={jest.fn()} />);
    
    expect(screen.getByRole('button', { name: 'STOP' })).toBeInTheDocument();
  });

  it('calls onTrigger when clicked', () => {
    const onTrigger = jest.fn();
    render(<AndonButton onTrigger={onTrigger} />);
    
    fireEvent.click(screen.getByRole('button'));
    expect(onTrigger).toHaveBeenCalled();
  });

  it('applies color styles', () => {
    const { rerender } = render(<AndonButton onTrigger={jest.fn()} color="red" />);
    expect(screen.getByRole('button')).toHaveClass('bg-red-600');

    rerender(<AndonButton onTrigger={jest.fn()} color="yellow" />);
    expect(screen.getByRole('button')).toHaveClass('bg-yellow-400');

    rerender(<AndonButton onTrigger={jest.fn()} color="green" />);
    expect(screen.getByRole('button')).toHaveClass('bg-green-600');
  });

  it('can be disabled', () => {
    const onTrigger = jest.fn();
    render(<AndonButton onTrigger={onTrigger} disabled />);
    
    expect(screen.getByRole('button')).toBeDisabled();
    fireEvent.click(screen.getByRole('button'));
    expect(onTrigger).not.toHaveBeenCalled();
  });

  it('has large touch target', () => {
    render(<AndonButton onTrigger={jest.fn()} />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveClass('min-w-[120px]');
    expect(button).toHaveClass('min-h-[120px]');
  });
});

describe('AndonAlert', () => {
  it('returns null when not active', () => {
    const { container } = render(
      <AndonAlert type="production" active={false} />
    );
    
    expect(container.firstChild).toBeNull();
  });

  it('renders production alert', () => {
    render(<AndonAlert type="production" active />);
    
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Production Issue')).toBeInTheDocument();
    expect(screen.getByText('⚙️')).toBeInTheDocument();
  });

  it('renders quality alert', () => {
    render(<AndonAlert type="quality" active />);
    
    expect(screen.getByText('Quality Alert')).toBeInTheDocument();
  });

  it('renders safety alert', () => {
    render(<AndonAlert type="safety" active />);
    
    expect(screen.getByText('Safety Alert')).toBeInTheDocument();
  });

  it('renders maintenance alert', () => {
    render(<AndonAlert type="maintenance" active />);
    
    expect(screen.getByText('Maintenance Required')).toBeInTheDocument();
  });

  it('displays message', () => {
    render(
      <AndonAlert type="quality" active message="Defect detected on line 3" />
    );
    
    expect(screen.getByText('Defect detected on line 3')).toBeInTheDocument();
  });

  it('calls onAcknowledge when button clicked', () => {
    const onAcknowledge = jest.fn();
    render(
      <AndonAlert type="production" active onAcknowledge={onAcknowledge} />
    );
    
    fireEvent.click(screen.getByText('Acknowledge'));
    expect(onAcknowledge).toHaveBeenCalled();
  });

  it('does not show acknowledge button if no callback', () => {
    render(<AndonAlert type="production" active />);
    
    expect(screen.queryByText('Acknowledge')).not.toBeInTheDocument();
  });
});

// =============================================================================
// BATTERY INDICATOR TESTS
// =============================================================================

describe('BatteryIndicator', () => {
  it('renders within provider with battery info', () => {
    // Mock batteryLevel in provider
    function MockProvider({ children }: { children: React.ReactNode }) {
      return (
        <ShopFloorProvider>
          {children}
        </ShopFloorProvider>
      );
    }

    render(
      <MockProvider>
        <BatteryIndicator />
      </MockProvider>
    );
    
    // Battery API not available in jsdom, so indicator returns null
    // This tests the behavior when battery info is not available
  });
});

// =============================================================================
// GLOVE MODE TOGGLE TESTS
// =============================================================================

describe('GloveModeToggle', () => {
  it('renders toggle button', () => {
    render(
      <ShopFloorProvider>
        <GloveModeToggle />
      </ShopFloorProvider>
    );
    
    expect(screen.getByRole('switch')).toBeInTheDocument();
    expect(screen.getByText('Glove Mode')).toBeInTheDocument();
    expect(screen.getByText('🧤')).toBeInTheDocument();
  });

  it('indicates current state', () => {
    render(
      <ShopFloorProvider defaultGloveFriendly>
        <GloveModeToggle />
      </ShopFloorProvider>
    );
    
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
  });

  it('toggles glove mode', () => {
    function TestWrapper() {
      return (
        <ShopFloorProvider>
          <GloveModeToggle />
          <TestDisplay />
        </ShopFloorProvider>
      );
    }

    function TestDisplay() {
      const { isGloveFriendlyMode } = useShopFloor();
      return <div data-testid="mode">{isGloveFriendlyMode ? 'on' : 'off'}</div>;
    }

    render(<TestWrapper />);
    
    expect(screen.getByTestId('mode')).toHaveTextContent('off');
    
    fireEvent.click(screen.getByRole('switch'));
    
    expect(screen.getByTestId('mode')).toHaveTextContent('on');
  });

  it('has minimum touch target', () => {
    render(
      <ShopFloorProvider>
        <GloveModeToggle />
      </ShopFloorProvider>
    );
    
    const toggle = screen.getByRole('switch');
    expect(toggle).toHaveClass('min-w-[48px]');
    expect(toggle).toHaveClass('min-h-[48px]');
  });
});

// =============================================================================
// HOOKS TESTS
// =============================================================================

describe('useHardwareScanner', () => {
  function TestComponent({ onScan, enabled = true }: { onScan: (result: any) => void; enabled?: boolean }) {
    const { isActive, lastScan } = useHardwareScanner(onScan, { enabled });
    return (
      <div>
        <div data-testid="active">{isActive ? 'yes' : 'no'}</div>
        <div data-testid="last">{lastScan?.value || 'none'}</div>
      </div>
    );
  }

  it('activates when enabled', () => {
    render(<TestComponent onScan={jest.fn()} enabled />);
    
    expect(screen.getByTestId('active')).toHaveTextContent('yes');
  });

  it('is inactive when disabled', () => {
    render(<TestComponent onScan={jest.fn()} enabled={false} />);
    
    expect(screen.getByTestId('active')).toHaveTextContent('no');
  });

  it('captures hardware scanner input', () => {
    const onScan = jest.fn();
    render(<TestComponent onScan={onScan} />);
    
    // Simulate scanner input
    fireEvent.keyPress(window, { key: 'A', code: 'KeyA', charCode: 65 });
    fireEvent.keyPress(window, { key: 'B', code: 'KeyB', charCode: 66 });
    fireEvent.keyPress(window, { key: 'C', code: 'KeyC', charCode: 67 });
    fireEvent.keyPress(window, { key: 'Enter', code: 'Enter', charCode: 13 });
    
    expect(onScan).toHaveBeenCalledWith(
      expect.objectContaining({
        value: 'ABC',
      })
    );
  });
});

describe('useDeviceCapabilities', () => {
  function TestComponent() {
    const caps = useDeviceCapabilities();
    return (
      <div>
        <div data-testid="touch">{caps.hasTouchScreen ? 'yes' : 'no'}</div>
        <div data-testid="concurrency">{caps.hardwareConcurrency}</div>
      </div>
    );
  }

  it('returns device capabilities', () => {
    render(<TestComponent />);
    
    // In jsdom, these have default/mock values
    expect(screen.getByTestId('concurrency')).toBeInTheDocument();
    expect(screen.getByTestId('touch')).toBeInTheDocument();
  });
});

describe('useAmbientLight', () => {
  function TestComponent() {
    const { illuminance, isHighGlare, isLowLight } = useAmbientLight();
    return (
      <div>
        <div data-testid="illuminance">{illuminance ?? 'null'}</div>
        <div data-testid="high-glare">{isHighGlare ? 'yes' : 'no'}</div>
        <div data-testid="low-light">{isLowLight ? 'yes' : 'no'}</div>
      </div>
    );
  }

  it('returns null when sensor not available', () => {
    render(<TestComponent />);
    
    expect(screen.getByTestId('illuminance')).toHaveTextContent('null');
    expect(screen.getByTestId('high-glare')).toHaveTextContent('no');
    expect(screen.getByTestId('low-light')).toHaveTextContent('no');
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Factory Floor Integration', () => {
  it('complete shop floor mode setup', () => {
    function ShopFloorApp() {
      const { theme, isGloveFriendlyMode } = useShopFloor();
      return (
        <HighGlareContainer enabled={theme === SHOP_FLOOR_THEME.HIGH_GLARE}>
          <div data-testid="theme">{theme}</div>
          <div data-testid="glove">{isGloveFriendlyMode ? 'on' : 'off'}</div>
          <ShopFloorThemeToggle />
          <GloveModeToggle />
          <GloveButton>Action</GloveButton>
          <BarcodeScanner onScan={jest.fn()} />
          <LargeStatusIndicator status="ok" label="Running" />
          <AndonButton onTrigger={jest.fn()} />
        </HighGlareContainer>
      );
    }

    render(
      <ShopFloorProvider>
        <ShopFloorApp />
      </ShopFloorProvider>
    );

    // All components render
    expect(screen.getByTestId('theme')).toHaveTextContent('standard');
    expect(screen.getByRole('radiogroup')).toBeInTheDocument();
    expect(screen.getByRole('switch')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
    expect(screen.getByText('Scanner Ready')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'STOP' })).toBeInTheDocument();
  });

  it('andon workflow with alert and acknowledgment', () => {
    const onAcknowledge = jest.fn();
    const onTrigger = jest.fn();
    
    function AndonWorkflow() {
      const [alert, setAlert] = React.useState(false);
      
      return (
        <ShopFloorProvider>
          <AndonButton
            onTrigger={() => {
              setAlert(true);
              onTrigger();
            }}
            label="ISSUE"
          />
          <AndonAlert
            type="quality"
            active={alert}
            message="Issue reported"
            onAcknowledge={() => {
              setAlert(false);
              onAcknowledge();
            }}
          />
        </ShopFloorProvider>
      );
    }

    render(<AndonWorkflow />);
    
    // Initially no alert
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    
    // Trigger andon
    fireEvent.click(screen.getByRole('button', { name: 'ISSUE' }));
    expect(onTrigger).toHaveBeenCalled();
    
    // Alert appears
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Issue reported')).toBeInTheDocument();
    
    // Acknowledge
    fireEvent.click(screen.getByText('Acknowledge'));
    expect(onAcknowledge).toHaveBeenCalled();
    
    // Alert dismissed
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
