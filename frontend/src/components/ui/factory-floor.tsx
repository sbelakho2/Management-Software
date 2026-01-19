/**
 * Factory-Floor UX Components
 * 
 * Section 19.6: Factory-Floor UX (Specifics)
 * 
 * Provides specialized components and utilities for shop-floor environments:
 * - High-contrast themes for bright/glare environments
 * - Glove-friendly large touch targets
 * - Barcode/QR scanning integration
 * - Voice command support
 * - Hardware HID scanner integration
 * - Low-power and battery-saver mode awareness
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  ReactNode,
} from 'react';
import { useI18n } from '@/contexts/i18n-context';

// =============================================================================
// CONSTANTS
// =============================================================================

/**
 * Shop floor theme modes
 */
export const SHOP_FLOOR_THEME = {
  /** Standard theme */
  STANDARD: 'standard',
  /** High contrast for bright/glare environments */
  HIGH_GLARE: 'high-glare',
  /** Night/dark mode for low-light */
  NIGHT: 'night',
} as const;

export type ShopFloorTheme = (typeof SHOP_FLOOR_THEME)[keyof typeof SHOP_FLOOR_THEME];

/**
 * Touch target sizes
 */
export const TOUCH_TARGET = {
  /** Standard touch target (44px) */
  STANDARD: 44,
  /** Glove-friendly touch target (48px minimum) */
  GLOVE_FRIENDLY: 48,
  /** Extra large for shop floor (56px) */
  EXTRA_LARGE: 56,
} as const;

/**
 * Barcode types
 */
export const BARCODE_TYPE = {
  QR: 'qr',
  CODE128: 'code128',
  CODE39: 'code39',
  EAN13: 'ean13',
  UPC: 'upc',
  DATAMATRIX: 'datamatrix',
  PDF417: 'pdf417',
  UNKNOWN: 'unknown',
} as const;

export type BarcodeType = (typeof BARCODE_TYPE)[keyof typeof BARCODE_TYPE];

/**
 * Voice command states
 */
export const VOICE_STATE = {
  IDLE: 'idle',
  LISTENING: 'listening',
  PROCESSING: 'processing',
  SUCCESS: 'success',
  ERROR: 'error',
} as const;

export type VoiceState = (typeof VOICE_STATE)[keyof typeof VOICE_STATE];

// =============================================================================
// TYPES
// =============================================================================

interface ShopFloorContextValue {
  theme: ShopFloorTheme;
  setTheme: (theme: ShopFloorTheme) => void;
  isGloveFriendlyMode: boolean;
  setGloveFriendlyMode: (enabled: boolean) => void;
  touchTargetSize: number;
  isLowPowerMode: boolean;
  batteryLevel: number | null;
}

interface BarcodeScanResult {
  value: string;
  type: BarcodeType;
  rawValue: string;
  timestamp: Date;
}

interface VoiceCommand {
  command: string;
  confidence: number;
  timestamp: Date;
}

// Speech Recognition Types for browsers that support it
interface SpeechRecognitionEvent extends Event {
  results: {
    length: number;
    [key: number]: {
      length: number;
      [key: number]: {
        transcript: string;
        confidence: number;
      };
    };
  };
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: () => void;
  onresult: (event: SpeechRecognitionEvent) => void;
  onerror: (event: SpeechRecognitionErrorEvent) => void;
  onend: () => void;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

// =============================================================================
// SHOP FLOOR CONTEXT
// =============================================================================

const ShopFloorContext = createContext<ShopFloorContextValue | null>(null);

export interface ShopFloorProviderProps {
  children: ReactNode;
  defaultTheme?: ShopFloorTheme;
  defaultGloveFriendly?: boolean;
}

/**
 * Provider for shop floor mode settings
 */
export function ShopFloorProvider({
  children,
  defaultTheme = SHOP_FLOOR_THEME.STANDARD,
  defaultGloveFriendly = false,
}: ShopFloorProviderProps) {
  const [theme, setTheme] = useState<ShopFloorTheme>(defaultTheme);
  const [isGloveFriendlyMode, setGloveFriendlyMode] = useState(defaultGloveFriendly);
  const [isLowPowerMode, setIsLowPowerMode] = useState(false);
  const [batteryLevel, setBatteryLevel] = useState<number | null>(null);

  // Calculate touch target size based on glove mode
  const touchTargetSize = isGloveFriendlyMode
    ? TOUCH_TARGET.GLOVE_FRIENDLY
    : TOUCH_TARGET.STANDARD;

  // Monitor battery status
  useEffect(() => {
    if (typeof navigator !== 'undefined' && 'getBattery' in navigator) {
      const getBatteryInfo = async () => {
        try {
          // @ts-expect-error - getBattery is not in all TS definitions
          const battery = await navigator.getBattery();
          setBatteryLevel(battery.level * 100);
          setIsLowPowerMode(battery.level < 0.2 || battery.charging === false && battery.level < 0.3);

          battery.addEventListener('levelchange', () => {
            setBatteryLevel(battery.level * 100);
            setIsLowPowerMode(battery.level < 0.2);
          });
        } catch {
          // Battery API not available
        }
      };
      getBatteryInfo();
    }
  }, []);

  const value: ShopFloorContextValue = {
    theme,
    setTheme,
    isGloveFriendlyMode,
    setGloveFriendlyMode,
    touchTargetSize,
    isLowPowerMode,
    batteryLevel,
  };

  return (
    <ShopFloorContext.Provider value={value}>{children}</ShopFloorContext.Provider>
  );
}

/**
 * Hook to access shop floor settings
 */
export function useShopFloor(): ShopFloorContextValue {
  const context = useContext(ShopFloorContext);
  if (!context) {
    throw new Error('useShopFloor must be used within ShopFloorProvider');
  }
  return context;
}

// =============================================================================
// HIGH GLARE THEME COMPONENTS
// =============================================================================

export interface HighGlareContainerProps {
  children: ReactNode;
  enabled?: boolean;
  className?: string;
}

/**
 * Container that applies high-contrast styling for glare environments
 */
export function HighGlareContainer({
  children,
  enabled = true,
  className = '',
}: HighGlareContainerProps) {
  if (!enabled) {
    return <div className={className}>{children}</div>;
  }

  return (
    <div
      className={`
        bg-black text-white
        [&_button]:bg-white [&_button]:text-black [&_button]:border-2 [&_button]:border-white
        [&_button:active]:bg-black [&_button:active]:text-white
        [&_.error]:text-red-500 [&_.error]:bg-black [&_.error]:font-bold
        [&_.success]:text-green-400 [&_.success]:bg-black [&_.success]:font-bold
        [&_.warning]:text-yellow-400 [&_.warning]:bg-black [&_.warning]:font-bold
        [&_input]:bg-black [&_input]:text-white [&_input]:border-2 [&_input]:border-white
        ${className}
      `}
    >
      {children}
    </div>
  );
}

export interface ThemeToggleProps {
  className?: string;
}

/**
 * Toggle button for switching between shop floor themes
 */
export function ShopFloorThemeToggle({ className = '' }: ThemeToggleProps) {
  const { theme, setTheme } = useShopFloor();

  const themes: { value: ShopFloorTheme; label: string; icon: string }[] = [
    { value: SHOP_FLOOR_THEME.STANDARD, label: 'Standard', icon: '☀️' },
    { value: SHOP_FLOOR_THEME.HIGH_GLARE, label: 'High Glare', icon: '🔆' },
    { value: SHOP_FLOOR_THEME.NIGHT, label: 'Night', icon: '🌙' },
  ];

  return (
    <div
      className={`flex gap-1 p-1 bg-gray-100 rounded-lg ${className}`}
      role="radiogroup"
      aria-label="Shop floor theme"
    >
      {themes.map((t) => (
        <button
          key={t.value}
          type="button"
          role="radio"
          aria-checked={theme === t.value}
          onClick={() => setTheme(t.value)}
          className={`
            min-w-[48px] min-h-[48px] px-3 py-2 rounded-md font-medium transition-colors
            ${theme === t.value
              ? 'bg-blue-600 text-white'
              : 'bg-transparent text-gray-700 hover:bg-gray-200'
            }
          `}
        >
          <span className="text-lg mr-1" aria-hidden="true">{t.icon}</span>
          <span className="sr-only">{t.label}</span>
        </button>
      ))}
    </div>
  );
}

// =============================================================================
// GLOVE-FRIENDLY COMPONENTS
// =============================================================================

export interface GloveButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'success';
  size?: 'standard' | 'large' | 'extra-large';
  icon?: ReactNode;
  children: ReactNode;
}

/**
 * Large, glove-friendly button for shop floor use
 */
export function GloveButton({
  variant = 'primary',
  size = 'large',
  icon,
  children,
  className = '',
  disabled,
  ...props
}: GloveButtonProps) {
  const sizeClasses = {
    standard: 'min-w-[44px] min-h-[44px] px-4 py-2 text-base',
    large: 'min-w-[48px] min-h-[48px] px-6 py-3 text-lg',
    'extra-large': 'min-w-[56px] min-h-[56px] px-8 py-4 text-xl',
  };

  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 border-2 border-blue-600',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 active:bg-gray-400 border-2 border-gray-300',
    danger: 'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 border-2 border-red-600',
    success: 'bg-green-600 text-white hover:bg-green-700 active:bg-green-800 border-2 border-green-600',
  };

  return (
    <button
      type="button"
      disabled={disabled}
      className={`
        inline-flex items-center justify-center gap-2 rounded-lg font-bold
        transition-colors focus:outline-none focus:ring-4 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        ${sizeClasses[size]}
        ${variantClasses[variant]}
        ${className}
      `}
      {...props}
    >
      {icon && <span className="text-2xl">{icon}</span>}
      {children}
    </button>
  );
}

export interface GloveTouchTargetProps {
  children: ReactNode;
  onPress: () => void;
  label: string;
  className?: string;
  disabled?: boolean;
}

/**
 * Touch target wrapper ensuring minimum 48px hit area for glove operation
 */
export function GloveTouchTarget({
  children,
  onPress,
  label,
  className = '',
  disabled = false,
}: GloveTouchTargetProps) {
  return (
    <button
      type="button"
      onClick={onPress}
      disabled={disabled}
      aria-label={label}
      className={`
        relative min-w-[48px] min-h-[48px] flex items-center justify-center
        touch-manipulation cursor-pointer
        focus:outline-none focus:ring-4 focus:ring-blue-500 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}
      `}
    >
      {children}
    </button>
  );
}

// =============================================================================
// BARCODE SCANNING
// =============================================================================

export interface BarcodeScannerProps {
  onScan: (result: BarcodeScanResult) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
  scannerType?: 'camera' | 'hardware';
  showPreview?: boolean;
  className?: string;
}

/**
 * Barcode scanner component supporting camera and hardware HID scanners
 */
export function BarcodeScanner({
  onScan,
  onError,
  enabled = true,
  scannerType = 'hardware',
  showPreview = false,
  className = '',
}: BarcodeScannerProps) {
  const [isScanning, setIsScanning] = useState(false);
  const [lastScan, setLastScan] = useState<BarcodeScanResult | null>(null);
  const bufferRef = useRef<string>('');
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Hardware HID scanner integration
  useEffect(() => {
    if (!enabled || scannerType !== 'hardware') return;

    const handleKeyPress = (event: KeyboardEvent) => {
      // Hardware scanners typically send characters rapidly followed by Enter
      if (event.key === 'Enter') {
        if (bufferRef.current.length > 0) {
          const result: BarcodeScanResult = {
            value: bufferRef.current,
            type: detectBarcodeType(bufferRef.current),
            rawValue: bufferRef.current,
            timestamp: new Date(),
          };
          setLastScan(result);
          onScan(result);
          bufferRef.current = '';
        }
      } else if (event.key.length === 1) {
        bufferRef.current += event.key;
        
        // Clear buffer after 100ms of no input (scanner sends characters rapidly)
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        timeoutRef.current = setTimeout(() => {
          bufferRef.current = '';
        }, 100);
      }
    };

    window.addEventListener('keypress', handleKeyPress, true);
    setIsScanning(true);

    return () => {
      window.removeEventListener('keypress', handleKeyPress, true);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      setIsScanning(false);
    };
  }, [enabled, scannerType, onScan]);

  // Camera-based scanning would integrate with a library like @zxing/browser
  // For now, we provide the component structure with camera UI placeholder
  if (scannerType === 'camera' && showPreview) {
    return (
      <div className={`relative ${className}`}>
        <div
          className="w-full aspect-[4/3] bg-gray-900 rounded-lg flex items-center justify-center"
          role="img"
          aria-label="Camera preview for barcode scanning"
        >
          <div className="text-white text-center">
            <span className="text-4xl">📷</span>
            <p className="mt-2 text-sm">Point camera at barcode</p>
          </div>
          {/* Scan area overlay */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-2/3 h-1/3 border-2 border-green-400 rounded-lg" />
          </div>
        </div>
        {lastScan && (
          <div className="mt-2 p-2 bg-green-100 text-green-800 rounded text-sm">
            Last scan: {lastScan.value}
          </div>
        )}
      </div>
    );
  }

  // Hardware scanner indicator
  return (
    <div
      className={`flex items-center gap-2 p-3 bg-gray-100 rounded-lg ${className}`}
      role="status"
      aria-label={isScanning ? 'Barcode scanner active' : 'Barcode scanner inactive'}
    >
      <span className="text-2xl" aria-hidden="true">📊</span>
      <div>
        <p className="font-medium">
          {isScanning ? 'Scanner Ready' : 'Scanner Disabled'}
        </p>
        <p className="text-sm text-gray-600">
          {isScanning ? 'Scan any barcode' : 'Enable scanner to begin'}
        </p>
      </div>
      {lastScan && (
        <div className="ml-auto px-3 py-1 bg-green-500 text-white rounded-full text-sm animate-pulse">
          ✓ Scanned
        </div>
      )}
    </div>
  );
}

/**
 * Detect barcode type from value
 */
function detectBarcodeType(value: string): BarcodeType {
  // Simple heuristic detection
  if (/^[0-9]{13}$/.test(value)) return BARCODE_TYPE.EAN13;
  if (/^[0-9]{12}$/.test(value)) return BARCODE_TYPE.UPC;
  if (/^[A-Z0-9\-. $/+%]+$/.test(value) && value.length <= 43) return BARCODE_TYPE.CODE39;
  if (value.length > 0 && value.length <= 80) return BARCODE_TYPE.CODE128;
  return BARCODE_TYPE.UNKNOWN;
}

export interface ScanFeedbackProps {
  visible: boolean;
  success?: boolean;
  message?: string;
}

/**
 * Visual feedback overlay for successful/failed scans
 */
export function ScanFeedback({ visible, success = true, message }: ScanFeedbackProps) {
  if (!visible) return null;

  return (
    <div
      className={`
        fixed inset-0 z-50 flex items-center justify-center pointer-events-none
        animate-pulse
      `}
      role="alert"
      aria-live="assertive"
    >
      <div
        className={`
          absolute inset-0
          ${success ? 'bg-green-500/20' : 'bg-red-500/20'}
        `}
      />
      <div
        className={`
          p-8 rounded-2xl text-center
          ${success ? 'bg-green-500 text-white' : 'bg-red-500 text-white'}
        `}
      >
        <span className="text-6xl block mb-4">
          {success ? '✓' : '✗'}
        </span>
        {message && <p className="text-xl font-bold">{message}</p>}
      </div>
    </div>
  );
}

// =============================================================================
// VOICE COMMANDS
// =============================================================================

export interface VoiceCommandListenerProps {
  onCommand: (command: VoiceCommand) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
  wakeWord?: string;
  className?: string;
}

/**
 * Voice command listener component
 */
export function VoiceCommandListener({
  onCommand,
  onError,
  enabled = true,
  wakeWord = 'Sensei',
  className = '',
}: VoiceCommandListenerProps) {
  const [state, setState] = useState<VoiceState>(VOICE_STATE.IDLE);
  const [lastCommand, setLastCommand] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (!enabled) return;

    // Check for browser support
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      onError?.(new Error('Speech recognition not supported'));
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setState(VOICE_STATE.LISTENING);
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[event.results.length - 1][0].transcript.trim();
      const confidence = event.results[event.results.length - 1][0].confidence;

      // Check for wake word
      if (transcript.toLowerCase().startsWith(wakeWord.toLowerCase())) {
        const command = transcript.substring(wakeWord.length).trim();
        setState(VOICE_STATE.PROCESSING);
        
        const voiceCommand: VoiceCommand = {
          command,
          confidence,
          timestamp: new Date(),
        };
        
        setLastCommand(command);
        onCommand(voiceCommand);
        setState(VOICE_STATE.SUCCESS);
        
        setTimeout(() => setState(VOICE_STATE.LISTENING), 1500);
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      setState(VOICE_STATE.ERROR);
      onError?.(new Error(event.error));
      setTimeout(() => setState(VOICE_STATE.LISTENING), 2000);
    };

    recognition.onend = () => {
      // Restart if still enabled
      if (enabled) {
        try {
          recognition.start();
        } catch {
          // Already started
        }
      }
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
    } catch {
      // Already started or error
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
    };
  }, [enabled, wakeWord, onCommand, onError]);

  const stateColors = {
    [VOICE_STATE.IDLE]: 'bg-gray-300',
    [VOICE_STATE.LISTENING]: 'bg-blue-500 animate-pulse',
    [VOICE_STATE.PROCESSING]: 'bg-yellow-500',
    [VOICE_STATE.SUCCESS]: 'bg-green-500',
    [VOICE_STATE.ERROR]: 'bg-red-500',
  };

  return (
    <div
      className={`flex items-center gap-3 p-3 rounded-lg bg-gray-100 ${className}`}
      role="status"
      aria-label={`Voice command ${state}`}
    >
      <div
        className={`w-4 h-4 rounded-full ${stateColors[state]}`}
        aria-hidden="true"
      />
      <div className="flex-1">
        <p className="font-medium">
          {state === VOICE_STATE.LISTENING && `Say "${wakeWord}" + command`}
          {state === VOICE_STATE.PROCESSING && 'Processing...'}
          {state === VOICE_STATE.SUCCESS && 'Command received'}
          {state === VOICE_STATE.ERROR && 'Error occurred'}
          {state === VOICE_STATE.IDLE && 'Voice commands disabled'}
        </p>
        {lastCommand && state === VOICE_STATE.SUCCESS && (
          <p className="text-sm text-gray-600">"{lastCommand}"</p>
        )}
      </div>
      <span className="text-2xl" aria-hidden="true">🎤</span>
    </div>
  );
}

// =============================================================================
// LARGE STATUS INDICATORS
// =============================================================================

export interface LargeStatusIndicatorProps {
  status: 'ok' | 'warning' | 'error' | 'info';
  label: string;
  sublabel?: string;
  visible?: boolean;
  className?: string;
}

/**
 * Large status indicator visible from a distance (5+ meters)
 */
export function LargeStatusIndicator({
  status,
  label,
  sublabel,
  visible = true,
  className = '',
}: LargeStatusIndicatorProps) {
  if (!visible) return null;

  const statusConfig = {
    ok: {
      bg: 'bg-green-500',
      text: 'text-white',
      icon: '✓',
    },
    warning: {
      bg: 'bg-yellow-400',
      text: 'text-black',
      icon: '⚠',
    },
    error: {
      bg: 'bg-red-600',
      text: 'text-white',
      icon: '✗',
    },
    info: {
      bg: 'bg-blue-500',
      text: 'text-white',
      icon: 'ℹ',
    },
  };

  const config = statusConfig[status];

  return (
    <div
      className={`
        ${config.bg} ${config.text}
        min-w-[200px] min-h-[200px]
        flex flex-col items-center justify-center
        rounded-2xl shadow-2xl
        ${className}
      `}
      role="status"
      aria-label={`${status}: ${label}`}
    >
      <span className="text-8xl font-bold" aria-hidden="true">
        {config.icon}
      </span>
      <p className="text-3xl font-bold mt-4 text-center px-4">{label}</p>
      {sublabel && (
        <p className="text-xl mt-2 opacity-80 text-center px-4">{sublabel}</p>
      )}
    </div>
  );
}

// =============================================================================
// ANDON SYSTEM COMPONENTS
// =============================================================================

export interface AndonButtonProps {
  onTrigger: () => void;
  label?: string;
  color?: 'red' | 'yellow' | 'green' | 'blue';
  disabled?: boolean;
  className?: string;
}

/**
 * Large Andon-style emergency/status button
 */
export function AndonButton({
  onTrigger,
  label = 'STOP',
  color = 'red',
  disabled = false,
  className = '',
}: AndonButtonProps) {
  const colorClasses = {
    red: 'bg-red-600 hover:bg-red-700 active:bg-red-800 border-red-800 shadow-red-900/50',
    yellow: 'bg-yellow-400 hover:bg-yellow-500 active:bg-yellow-600 border-yellow-600 shadow-yellow-800/50 text-black',
    green: 'bg-green-600 hover:bg-green-700 active:bg-green-800 border-green-800 shadow-green-900/50',
    blue: 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 border-blue-800 shadow-blue-900/50',
  };

  return (
    <button
      type="button"
      onClick={onTrigger}
      disabled={disabled}
      className={`
        min-w-[120px] min-h-[120px]
        rounded-full border-8 shadow-lg
        text-white font-black text-2xl
        transition-all duration-100
        active:scale-95 active:shadow-inner
        disabled:opacity-50 disabled:cursor-not-allowed
        ${colorClasses[color]}
        ${className}
      `}
      aria-label={label}
    >
      {label}
    </button>
  );
}

export interface AndonAlertProps {
  type: 'production' | 'quality' | 'safety' | 'maintenance';
  active: boolean;
  message?: string;
  onAcknowledge?: () => void;
  className?: string;
}

/**
 * Andon alert display component
 */
export function AndonAlert({
  type,
  active,
  message,
  onAcknowledge,
  className = '',
}: AndonAlertProps) {
  const { t } = useI18n();
  if (!active) return null;

  const typeConfig = {
    production: { color: 'bg-yellow-500', icon: '⚙️', labelKey: 'components.factoryFloor.machineStatus.productionIssue' },
    quality: { color: 'bg-red-600', icon: '⚠️', labelKey: 'components.factoryFloor.machineStatus.qualityAlert' },
    safety: { color: 'bg-red-700', icon: '🛑', labelKey: 'components.factoryFloor.machineStatus.safetyAlert' },
    maintenance: { color: 'bg-blue-600', icon: '🔧', labelKey: 'components.factoryFloor.machineStatus.maintenanceRequired' },
  };

  const config = typeConfig[type];

  return (
    <div
      className={`
        ${config.color} text-white
        p-6 rounded-xl shadow-2xl
        animate-pulse
        ${className}
      `}
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-center gap-4">
        <span className="text-5xl">{config.icon}</span>
        <div className="flex-1">
          <h3 className="text-2xl font-bold">{t(config.labelKey)}</h3>
          {message && <p className="text-lg mt-1">{message}</p>}
        </div>
        {onAcknowledge && (
          <GloveButton
            variant="secondary"
            size="large"
            onClick={onAcknowledge}
          >
            Acknowledge
          </GloveButton>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// BATTERY & POWER AWARENESS
// =============================================================================

export interface BatteryIndicatorProps {
  showWarning?: boolean;
  className?: string;
}

/**
 * Battery level indicator with low power warning
 */
export function BatteryIndicator({ showWarning = true, className = '' }: BatteryIndicatorProps) {
  const { batteryLevel, isLowPowerMode } = useShopFloor();

  if (batteryLevel === null) {
    return null;
  }

  const getBatteryIcon = () => {
    if (batteryLevel > 75) return '🔋';
    if (batteryLevel > 50) return '🔋';
    if (batteryLevel > 25) return '🪫';
    return '🪫';
  };

  return (
    <div
      className={`
        flex items-center gap-2 px-3 py-2 rounded-lg
        ${isLowPowerMode ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}
        ${className}
      `}
      role="status"
      aria-label={`Battery ${Math.round(batteryLevel)}%`}
    >
      <span className="text-xl">{getBatteryIcon()}</span>
      <span className="font-medium">{Math.round(batteryLevel)}%</span>
      {showWarning && isLowPowerMode && (
        <span className="text-sm text-red-600 font-medium ml-2">
          Low Power Mode
        </span>
      )}
    </div>
  );
}

// =============================================================================
// GLOVE MODE TOGGLE
// =============================================================================

export interface GloveModeToggleProps {
  className?: string;
}

/**
 * Toggle for enabling/disabling glove-friendly mode
 */
export function GloveModeToggle({ className = '' }: GloveModeToggleProps) {
  const { isGloveFriendlyMode, setGloveFriendlyMode } = useShopFloor();

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isGloveFriendlyMode}
      onClick={() => setGloveFriendlyMode(!isGloveFriendlyMode)}
      className={`
        min-w-[48px] min-h-[48px]
        flex items-center gap-3 px-4 py-3 rounded-lg
        transition-colors font-medium
        ${isGloveFriendlyMode
          ? 'bg-blue-600 text-white'
          : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
        }
        ${className}
      `}
    >
      <span className="text-2xl" aria-hidden="true">🧤</span>
      <span>Glove Mode</span>
      <span
        className={`
          ml-auto w-12 h-6 rounded-full relative transition-colors
          ${isGloveFriendlyMode ? 'bg-blue-300' : 'bg-gray-400'}
        `}
        aria-hidden="true"
      >
        <span
          className={`
            absolute top-1 w-4 h-4 rounded-full bg-white transition-transform
            ${isGloveFriendlyMode ? 'translate-x-6' : 'translate-x-1'}
          `}
        />
      </span>
    </button>
  );
}

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Hook for hardware barcode scanner integration
 */
export function useHardwareScanner(
  onScan: (result: BarcodeScanResult) => void,
  options: { enabled?: boolean; debounceMs?: number } = {}
): { isActive: boolean; lastScan: BarcodeScanResult | null } {
  const { enabled = true, debounceMs = 100 } = options;
  const [isActive, setIsActive] = useState(false);
  const [lastScan, setLastScan] = useState<BarcodeScanResult | null>(null);
  const bufferRef = useRef<string>('');
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.key === 'Enter') {
        if (bufferRef.current.length > 0) {
          const result: BarcodeScanResult = {
            value: bufferRef.current,
            type: detectBarcodeType(bufferRef.current),
            rawValue: bufferRef.current,
            timestamp: new Date(),
          };
          setLastScan(result);
          onScan(result);
          bufferRef.current = '';
        }
      } else if (event.key.length === 1) {
        bufferRef.current += event.key;
        
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        timeoutRef.current = setTimeout(() => {
          bufferRef.current = '';
        }, debounceMs);
      }
    };

    window.addEventListener('keypress', handleKeyPress, true);
    setIsActive(true);

    return () => {
      window.removeEventListener('keypress', handleKeyPress, true);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      setIsActive(false);
    };
  }, [enabled, debounceMs, onScan]);

  return { isActive, lastScan };
}

/**
 * Hook for monitoring device capabilities and performance
 */
export function useDeviceCapabilities(): {
  isLowEndDevice: boolean;
  supportsVibration: boolean;
  supportsSpeechRecognition: boolean;
  hasTouchScreen: boolean;
  deviceMemory: number | null;
  hardwareConcurrency: number;
} {
  const [capabilities, setCapabilities] = useState({
    isLowEndDevice: false,
    supportsVibration: false,
    supportsSpeechRecognition: false,
    hasTouchScreen: false,
    deviceMemory: null as number | null,
    hardwareConcurrency: 1,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const nav = navigator as Navigator & {
      deviceMemory?: number;
    };

    const deviceMemory = nav.deviceMemory ?? null;
    const hardwareConcurrency = navigator.hardwareConcurrency || 1;
    const isLowEndDevice = (deviceMemory !== null && deviceMemory < 4) || hardwareConcurrency < 4;
    const supportsVibration = 'vibrate' in navigator;
    const supportsSpeechRecognition = 
      'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
    const hasTouchScreen = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

    setCapabilities({
      isLowEndDevice,
      supportsVibration,
      supportsSpeechRecognition,
      hasTouchScreen,
      deviceMemory,
      hardwareConcurrency,
    });
  }, []);

  return capabilities;
}

/**
 * Hook for ambient light detection (if sensor available)
 */
export function useAmbientLight(): {
  illuminance: number | null;
  isHighGlare: boolean;
  isLowLight: boolean;
} {
  const [illuminance, setIlluminance] = useState<number | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !('AmbientLightSensor' in window)) {
      return;
    }

    try {
      // @ts-expect-error - AmbientLightSensor is not in all TS definitions
      const sensor = new AmbientLightSensor();
      sensor.addEventListener('reading', () => {
        setIlluminance(sensor.illuminance);
      });
      sensor.start();

      return () => {
        sensor.stop();
      };
    } catch {
      // Sensor not available
    }
  }, []);

  return {
    illuminance,
    isHighGlare: illuminance !== null && illuminance > 1000,
    isLowLight: illuminance !== null && illuminance < 50,
  };
}

// =============================================================================
// EXPORTS
// =============================================================================

export type { BarcodeScanResult, VoiceCommand };
