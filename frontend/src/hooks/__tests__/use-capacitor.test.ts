/**
 * Tests for Capacitor Native Wrapper Hooks
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import {
  isNativeApp,
  getPlatform,
  useNativeCapabilities,
  useCamera,
  useFileSystem,
  usePushNotifications,
  useHaptics,
  useShare,
  useClipboard,
  useStatusBar,
  useBiometricAuth,
  useAppState,
} from '../use-capacitor';

// =============================================================================
// Mocks
// =============================================================================

// Mock window.Capacitor
const mockCapacitor = (isNative: boolean, platform = 'ios') => {
  (window as Window & { Capacitor?: { isNative: boolean; platform: string } }).Capacitor = {
    isNative,
    platform,
  };
};

const clearCapacitor = () => {
  delete (window as Window & { Capacitor?: unknown }).Capacitor;
};

// Store original createElement to restore after mocking
const originalCreateElement = document.createElement.bind(document);

beforeEach(() => {
  clearCapacitor();
  jest.clearAllMocks();
  
  // Restore createElement
  document.createElement = originalCreateElement;
  
  // Setup navigator mocks safely
  Object.defineProperty(navigator, 'permissions', {
    value: {
      query: jest.fn().mockResolvedValue({ state: 'prompt' }),
    },
    writable: true,
    configurable: true,
  });
  
  Object.defineProperty(navigator, 'vibrate', {
    value: jest.fn().mockReturnValue(true),
    writable: true,
    configurable: true,
  });
  
  Object.defineProperty(navigator, 'clipboard', {
    value: {
      writeText: jest.fn().mockResolvedValue(undefined),
      readText: jest.fn().mockResolvedValue('pasted text'),
    },
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  clearCapacitor();
  document.createElement = originalCreateElement;
});

// =============================================================================
// Platform Detection Tests
// =============================================================================

describe('isNativeApp', () => {
  it('should return false when Capacitor is not present', () => {
    clearCapacitor();
    expect(isNativeApp()).toBe(false);
  });

  it('should return true when Capacitor.isNative is true', () => {
    mockCapacitor(true, 'ios');
    expect(isNativeApp()).toBe(true);
  });

  it('should return false when Capacitor.isNative is false', () => {
    mockCapacitor(false, 'web');
    expect(isNativeApp()).toBe(false);
  });
});

describe('getPlatform', () => {
  it('should return "web" when Capacitor is not present', () => {
    clearCapacitor();
    expect(getPlatform()).toBe('web');
  });

  it('should return "ios" for iOS platform', () => {
    mockCapacitor(true, 'ios');
    expect(getPlatform()).toBe('ios');
  });

  it('should return "android" for Android platform', () => {
    mockCapacitor(true, 'android');
    expect(getPlatform()).toBe('android');
  });

  it('should return "web" for web platform', () => {
    mockCapacitor(false, 'web');
    expect(getPlatform()).toBe('web');
  });
});

// =============================================================================
// useNativeCapabilities Tests
// =============================================================================

describe('useNativeCapabilities', () => {
  it('should detect web capabilities', async () => {
    clearCapacitor();
    
    const { result } = renderHook(() => useNativeCapabilities());

    await waitFor(() => {
      expect(result.current.isNative).toBe(false);
      expect(result.current.platform).toBe('web');
    });
  });

  it('should detect native iOS capabilities', async () => {
    mockCapacitor(true, 'ios');

    const { result } = renderHook(() => useNativeCapabilities());

    await waitFor(() => {
      expect(result.current.isNative).toBe(true);
      expect(result.current.platform).toBe('ios');
      expect(result.current.hasCamera).toBe(true);
      expect(result.current.hasPushNotifications).toBe(true);
      expect(result.current.hasHaptics).toBe(true);
      expect(result.current.hasBiometrics).toBe(true);
    });
  });

  it('should detect native Android capabilities', async () => {
    mockCapacitor(true, 'android');

    const { result } = renderHook(() => useNativeCapabilities());

    await waitFor(() => {
      expect(result.current.isNative).toBe(true);
      expect(result.current.platform).toBe('android');
      expect(result.current.hasCamera).toBe(true);
    });
  });
});

// =============================================================================
// useCamera Tests
// =============================================================================

describe('useCamera', () => {
  it('should provide camera functions', () => {
    const { result } = renderHook(() => useCamera());

    expect(typeof result.current.takePhoto).toBe('function');
    expect(typeof result.current.pickPhoto).toBe('function');
    expect(typeof result.current.requestPermission).toBe('function');
    expect(typeof result.current.hasPermission).toBe('boolean');
  });

  it('should request camera permission on web', async () => {
    const mockStream = {
      getTracks: () => [{ stop: jest.fn() }],
    };
    Object.defineProperty(navigator, 'mediaDevices', {
      value: {
        getUserMedia: jest.fn().mockResolvedValue(mockStream),
      },
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useCamera());

    await act(async () => {
      const granted = await result.current.requestPermission();
      expect(granted).toBe(true);
    });

    expect(result.current.hasPermission).toBe(true);
  });

  it('should handle permission denial on web', async () => {
    Object.defineProperty(navigator, 'mediaDevices', {
      value: {
        getUserMedia: jest.fn().mockRejectedValue(new Error('Permission denied')),
      },
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useCamera());

    await act(async () => {
      const granted = await result.current.requestPermission();
      expect(granted).toBe(false);
    });

    expect(result.current.hasPermission).toBe(false);
  });

  it('should grant permission automatically on native', async () => {
    mockCapacitor(true, 'ios');

    const { result } = renderHook(() => useCamera());

    await act(async () => {
      const granted = await result.current.requestPermission();
      expect(granted).toBe(true);
    });
  });

  it('should return photo object on native takePhoto', async () => {
    mockCapacitor(true, 'ios');

    const { result } = renderHook(() => useCamera());

    await act(async () => {
      const photo = await result.current.takePhoto();
      expect(photo).not.toBeNull();
      expect(photo?.dataUrl).toContain('data:image/png;base64');
      expect(photo?.format).toBe('png');
    });
  });
});

// =============================================================================
// useFileSystem Tests
// =============================================================================

describe('useFileSystem', () => {
  it('should provide file system functions', () => {
    const { result } = renderHook(() => useFileSystem());

    expect(typeof result.current.pickFile).toBe('function');
    expect(typeof result.current.pickFiles).toBe('function');
    expect(typeof result.current.saveFile).toBe('function');
    expect(typeof result.current.readFile).toBe('function');
    expect(typeof result.current.deleteFile).toBe('function');
  });

  it('should save file with web download', async () => {
    // Mock URL functions
    const mockUrl = 'blob:http://localhost/mock-url';
    global.URL.createObjectURL = jest.fn().mockReturnValue(mockUrl);
    global.URL.revokeObjectURL = jest.fn();

    const { result } = renderHook(() => useFileSystem());

    await act(async () => {
      const success = await result.current.saveFile('test.txt', 'Hello World', 'text/plain');
      expect(success).toBe(true);
    });

    expect(global.URL.revokeObjectURL).toHaveBeenCalledWith(mockUrl);
  });

  it('should delete file by revoking URL on web', async () => {
    global.URL.revokeObjectURL = jest.fn();

    const { result } = renderHook(() => useFileSystem());

    await act(async () => {
      const success = await result.current.deleteFile('blob:http://localhost/test');
      expect(success).toBe(true);
    });

    expect(global.URL.revokeObjectURL).toHaveBeenCalled();
  });

  it('should save file on native', async () => {
    mockCapacitor(true, 'ios');

    const { result } = renderHook(() => useFileSystem());

    await act(async () => {
      const success = await result.current.saveFile('test.txt', 'Hello Native');
      expect(success).toBe(true);
    });
  });
});

// =============================================================================
// usePushNotifications Tests
// =============================================================================

describe('usePushNotifications', () => {
  beforeEach(() => {
    // Mock Notification API
    Object.defineProperty(window, 'Notification', {
      value: class {
        static permission = 'granted';
        static requestPermission = jest.fn().mockResolvedValue('granted');
        constructor(public title: string, public options?: NotificationOptions) {}
      },
      writable: true,
      configurable: true,
    });
  });

  it('should provide notification functions', () => {
    const { result } = renderHook(() => usePushNotifications());

    expect(typeof result.current.requestPermission).toBe('function');
    expect(typeof result.current.registerToken).toBe('function');
    expect(typeof result.current.scheduleLocal).toBe('function');
    expect(typeof result.current.cancelLocal).toBe('function');
    expect(typeof result.current.clearNotifications).toBe('function');
    expect(Array.isArray(result.current.notifications)).toBe(true);
  });

  it('should request notification permission on web', async () => {
    const mockRequest = jest.fn().mockResolvedValue('granted');
    Object.defineProperty(window, 'Notification', {
      value: class {
        static permission = 'default';
        static requestPermission = mockRequest;
      },
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => usePushNotifications());

    await act(async () => {
      const granted = await result.current.requestPermission();
      expect(granted).toBe(true);
    });

    expect(mockRequest).toHaveBeenCalled();
  });

  it('should register push token on native', async () => {
    mockCapacitor(true, 'android');

    const { result } = renderHook(() => usePushNotifications());

    await act(async () => {
      const token = await result.current.registerToken();
      expect(token).toBe('mock-device-token-for-testing');
    });
  });

  it('should schedule local notification on native', async () => {
    mockCapacitor(true, 'ios');

    const { result } = renderHook(() => usePushNotifications());

    await act(async () => {
      const id = await result.current.scheduleLocal({
        id: 123,
        title: 'Test',
        body: 'Test notification',
      });
      expect(id).toBe(123);
    });
  });

  it('should cancel local notification', async () => {
    mockCapacitor(true, 'ios');

    const { result } = renderHook(() => usePushNotifications());

    await act(async () => {
      const success = await result.current.cancelLocal(123);
      expect(success).toBe(true);
    });
  });

  it('should clear notifications array', () => {
    const { result } = renderHook(() => usePushNotifications());

    act(() => {
      result.current.clearNotifications();
    });

    expect(result.current.notifications).toEqual([]);
  });
});

// =============================================================================
// useHaptics Tests
// =============================================================================

describe('useHaptics', () => {
  it('should provide haptic functions', () => {
    const { result } = renderHook(() => useHaptics());

    expect(typeof result.current.impact).toBe('function');
    expect(typeof result.current.notification).toBe('function');
    expect(typeof result.current.selectionStart).toBe('function');
    expect(typeof result.current.selectionChanged).toBe('function');
    expect(typeof result.current.selectionEnd).toBe('function');
  });

  it('should call web vibrate API for impact', () => {
    const vibrateMock = jest.fn();
    Object.defineProperty(navigator, 'vibrate', {
      value: vibrateMock,
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useHaptics());

    act(() => {
      result.current.impact('medium');
    });

    expect(vibrateMock).toHaveBeenCalledWith(25);
  });

  it('should use different patterns for different styles', () => {
    const vibrateMock = jest.fn();
    Object.defineProperty(navigator, 'vibrate', {
      value: vibrateMock,
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useHaptics());

    act(() => {
      result.current.impact('light');
    });
    expect(vibrateMock).toHaveBeenCalledWith(10);

    act(() => {
      result.current.impact('heavy');
    });
    expect(vibrateMock).toHaveBeenCalledWith(50);

    act(() => {
      result.current.impact('success');
    });
    expect(vibrateMock).toHaveBeenCalledWith([10, 50, 10]);
  });

  it('should use notification helper', () => {
    const vibrateMock = jest.fn();
    Object.defineProperty(navigator, 'vibrate', {
      value: vibrateMock,
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useHaptics());

    act(() => {
      result.current.notification('error');
    });

    expect(vibrateMock).toHaveBeenCalledWith([50, 25, 50]);
  });

  it('should handle selection haptics', () => {
    const vibrateMock = jest.fn();
    Object.defineProperty(navigator, 'vibrate', {
      value: vibrateMock,
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useHaptics());

    act(() => {
      result.current.selectionStart();
      result.current.selectionChanged();
      result.current.selectionEnd();
    });

    expect(vibrateMock).toHaveBeenCalledWith(5);
    expect(vibrateMock).toHaveBeenCalledTimes(3);
  });
});

// =============================================================================
// useShare Tests
// =============================================================================

describe('useShare', () => {
  it('should provide share functions', () => {
    const { result } = renderHook(() => useShare());

    expect(typeof result.current.share).toBe('function');
    expect(typeof result.current.canShare).toBe('boolean');
  });

  it('should detect web share capability', async () => {
    Object.defineProperty(navigator, 'share', {
      value: jest.fn(),
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useShare());

    await waitFor(() => {
      expect(result.current.canShare).toBe(true);
    });
  });

  it('should share using web API', async () => {
    const mockShare = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'share', {
      value: mockShare,
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useShare());

    await act(async () => {
      const success = await result.current.share({
        title: 'Test Title',
        text: 'Test content',
        url: 'https://example.com',
      });
      expect(success).toBe(true);
    });

    expect(mockShare).toHaveBeenCalledWith({
      title: 'Test Title',
      text: 'Test content',
      url: 'https://example.com',
    });
  });

  it('should share on native platform', async () => {
    mockCapacitor(true, 'ios');

    const { result } = renderHook(() => useShare());

    await act(async () => {
      const success = await result.current.share({
        title: 'Test',
        url: 'https://example.com',
      });
      expect(success).toBe(true);
    });
  });
});

// =============================================================================
// useClipboard Tests
// =============================================================================

describe('useClipboard', () => {
  it('should provide clipboard functions', () => {
    const { result } = renderHook(() => useClipboard());

    expect(typeof result.current.copy).toBe('function');
    expect(typeof result.current.paste).toBe('function');
  });

  it('should copy text using web API', async () => {
    const writeTextMock = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: writeTextMock,
        readText: jest.fn(),
      },
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useClipboard());

    await act(async () => {
      const success = await result.current.copy('Hello World');
      expect(success).toBe(true);
    });

    expect(writeTextMock).toHaveBeenCalledWith('Hello World');
  });

  it('should paste text using web API', async () => {
    const readTextMock = jest.fn().mockResolvedValue('Pasted text');
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: jest.fn(),
        readText: readTextMock,
      },
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useClipboard());

    await act(async () => {
      const text = await result.current.paste();
      expect(text).toBe('Pasted text');
    });
  });

  it('should copy on native platform', async () => {
    mockCapacitor(true, 'ios');

    const { result } = renderHook(() => useClipboard());

    await act(async () => {
      const success = await result.current.copy('Native copy');
      expect(success).toBe(true);
    });
  });

  it('should handle clipboard copy failure gracefully', async () => {
    // Make clipboard.writeText fail
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: jest.fn().mockRejectedValue(new Error('Failed')),
        readText: jest.fn(),
      },
      writable: true,
      configurable: true,
    });
    
    // Also make the fallback fail
    document.execCommand = jest.fn().mockImplementation(() => {
      throw new Error('execCommand not supported');
    });

    const { result } = renderHook(() => useClipboard());

    await act(async () => {
      const success = await result.current.copy('Test');
      expect(success).toBe(false);
    });
  });
});

// =============================================================================
// useStatusBar Tests
// =============================================================================

describe('useStatusBar', () => {
  beforeEach(() => {
    // Clear any existing meta tags
    document.querySelectorAll('meta[name="theme-color"]').forEach((el) => el.remove());
  });

  it('should provide status bar functions', () => {
    const { result } = renderHook(() => useStatusBar());

    expect(typeof result.current.setStyle).toBe('function');
    expect(typeof result.current.setBackgroundColor).toBe('function');
    expect(typeof result.current.show).toBe('function');
    expect(typeof result.current.hide).toBe('function');
  });

  it('should set theme-color meta for dark style', () => {
    const { result } = renderHook(() => useStatusBar());

    act(() => {
      result.current.setStyle('dark');
    });

    const meta = document.querySelector('meta[name="theme-color"]');
    expect(meta).not.toBeNull();
    expect(meta?.getAttribute('content')).toBe('#000000');
  });

  it('should set theme-color meta for light style', () => {
    const { result } = renderHook(() => useStatusBar());

    act(() => {
      result.current.setStyle('light');
    });

    const meta = document.querySelector('meta[name="theme-color"]');
    expect(meta?.getAttribute('content')).toBe('#ffffff');
  });

  it('should set custom background color', () => {
    const { result } = renderHook(() => useStatusBar());

    // First set style to create meta tag
    act(() => {
      result.current.setStyle('default');
    });

    act(() => {
      result.current.setBackgroundColor('#3366CC');
    });

    const meta = document.querySelector('meta[name="theme-color"]');
    expect(meta?.getAttribute('content')).toBe('#3366CC');
  });

  it('should call show and hide without error on native', () => {
    mockCapacitor(true, 'ios');

    const { result } = renderHook(() => useStatusBar());

    expect(() => {
      act(() => {
        result.current.show();
        result.current.hide();
      });
    }).not.toThrow();
  });
});

// =============================================================================
// useBiometricAuth Tests
// =============================================================================

describe('useBiometricAuth', () => {
  it('should provide biometric functions', () => {
    const { result } = renderHook(() => useBiometricAuth());

    expect(typeof result.current.authenticate).toBe('function');
    expect(typeof result.current.isAvailable).toBe('boolean');
  });

  it('should check WebAuthn availability', async () => {
    (window as Window & { 
      PublicKeyCredential?: { 
        isUserVerifyingPlatformAuthenticatorAvailable: () => Promise<boolean> 
      } 
    }).PublicKeyCredential = {
      isUserVerifyingPlatformAuthenticatorAvailable: jest.fn().mockResolvedValue(true),
    };

    const { result } = renderHook(() => useBiometricAuth());

    await waitFor(() => {
      expect(result.current.isAvailable).toBe(true);
    });
  });

  it('should return unavailable when WebAuthn not supported', async () => {
    delete (window as Window & { PublicKeyCredential?: unknown }).PublicKeyCredential;

    const { result } = renderHook(() => useBiometricAuth());

    await waitFor(() => {
      expect(result.current.isAvailable).toBe(false);
    });
  });

  it('should authenticate on native', async () => {
    mockCapacitor(true, 'ios');

    const { result } = renderHook(() => useBiometricAuth());

    await act(async () => {
      const authResult = await result.current.authenticate('Confirm your identity');
      expect(authResult.verified).toBe(true);
      expect(authResult.method).toBe('fingerprint');
    });
  });

  it('should fail authentication on web', async () => {
    clearCapacitor();

    const { result } = renderHook(() => useBiometricAuth());

    await act(async () => {
      const authResult = await result.current.authenticate();
      expect(authResult.verified).toBe(false);
      expect(authResult.error).toBeDefined();
    });
  });
});

// =============================================================================
// useAppState Tests
// =============================================================================

describe('useAppState', () => {
  it('should provide app state values', () => {
    const { result } = renderHook(() => useAppState());

    expect(typeof result.current.isActive).toBe('boolean');
    expect(typeof result.current.isForeground).toBe('boolean');
  });

  it('should default to active state', () => {
    const { result } = renderHook(() => useAppState());

    expect(result.current.isActive).toBe(true);
    expect(result.current.isForeground).toBe(true);
  });

  it('should update state on visibility change', () => {
    const { result } = renderHook(() => useAppState());

    // Simulate going to background
    Object.defineProperty(document, 'visibilityState', {
      value: 'hidden',
      writable: true,
      configurable: true,
    });

    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    expect(result.current.isActive).toBe(false);
    expect(result.current.isForeground).toBe(false);
  });

  it('should return to active on visibility restore', () => {
    const { result } = renderHook(() => useAppState());

    // First hide
    Object.defineProperty(document, 'visibilityState', {
      value: 'hidden',
      writable: true,
      configurable: true,
    });
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    // Then show
    Object.defineProperty(document, 'visibilityState', {
      value: 'visible',
      writable: true,
      configurable: true,
    });
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    expect(result.current.isActive).toBe(true);
    expect(result.current.isForeground).toBe(true);
  });

  it('should cleanup event listener on unmount', () => {
    const removeEventListenerSpy = jest.spyOn(document, 'removeEventListener');

    const { unmount } = renderHook(() => useAppState());

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      'visibilitychange',
      expect.any(Function)
    );

    removeEventListenerSpy.mockRestore();
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('Integration: Multiple Hooks Together', () => {
  it('should work together on native platform', async () => {
    mockCapacitor(true, 'ios');

    const { result: capsResult } = renderHook(() => useNativeCapabilities());
    const { result: cameraResult } = renderHook(() => useCamera());
    const { result: hapticsResult } = renderHook(() => useHaptics());

    await waitFor(() => {
      expect(capsResult.current.isNative).toBe(true);
      expect(capsResult.current.hasCamera).toBe(true);
    });

    // Take photo and trigger haptic
    await act(async () => {
      const photo = await cameraResult.current.takePhoto();
      if (photo) {
        hapticsResult.current.notification('success');
      }
    });
  });

  it('should gracefully degrade on web', async () => {
    clearCapacitor();

    const { result: capsResult } = renderHook(() => useNativeCapabilities());
    const { result: shareResult } = renderHook(() => useShare());
    const { result: clipboardResult } = renderHook(() => useClipboard());

    await waitFor(() => {
      expect(capsResult.current.isNative).toBe(false);
      expect(capsResult.current.platform).toBe('web');
    });

    // Should still work with web fallbacks
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: jest.fn().mockResolvedValue(undefined),
        readText: jest.fn(),
      },
      writable: true,
      configurable: true,
    });
    
    await act(async () => {
      const success = await clipboardResult.current.copy('Web copy');
      expect(success).toBe(true);
    });
  });
});
