/**
 * Capacitor Native Wrapper Hooks
 * 
 * Provides React hooks for native mobile functionality via Capacitor:
 * - Camera access for document scanning
 * - File system access for uploads/downloads
 * - Push notifications
 * - Haptic feedback
 * - Biometric authentication
 * - Native share functionality
 * - Clipboard access
 * - Status bar control
 */

import { useCallback, useEffect, useState, useRef } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface CameraPhoto {
  dataUrl: string;
  format: 'jpeg' | 'png' | 'gif' | 'webp';
  savedPath?: string;
  exif?: Record<string, unknown>;
  webPath?: string;
}

export interface CameraOptions {
  quality?: number; // 0-100
  allowEditing?: boolean;
  resultType?: 'base64' | 'uri' | 'dataUrl';
  saveToGallery?: boolean;
  source?: 'camera' | 'photos' | 'prompt';
  width?: number;
  height?: number;
  correctOrientation?: boolean;
}

export interface FileInfo {
  name: string;
  type: string;
  size: number;
  uri: string;
  path?: string;
  data?: string;
  modifiedAt?: number;
}

export interface FilePickerOptions {
  types?: string[];
  multiple?: boolean;
}

export interface PushNotification {
  id: string;
  title: string;
  body: string;
  data?: Record<string, unknown>;
  click_action?: string;
  badge?: number;
  sound?: string;
  receivedAt: Date;
}

export interface LocalNotificationOptions {
  id?: number;
  title: string;
  body: string;
  schedule?: { at: Date } | { every: 'day' | 'hour' | 'minute' };
  sound?: string;
  actionTypeId?: string;
  extra?: Record<string, unknown>;
}

export interface BiometricResult {
  verified: boolean;
  method?: 'fingerprint' | 'face' | 'iris';
  error?: string;
}

export interface ShareOptions {
  title?: string;
  text?: string;
  url?: string;
  files?: string[];
  dialogTitle?: string;
}

export interface NativeCapabilities {
  isNative: boolean;
  platform: 'ios' | 'android' | 'web';
  hasCamera: boolean;
  hasPushNotifications: boolean;
  hasFileSystem: boolean;
  hasBiometrics: boolean;
  hasHaptics: boolean;
  hasShare: boolean;
}

export type HapticStyle = 
  | 'light'
  | 'medium'
  | 'heavy'
  | 'selection'
  | 'success'
  | 'warning'
  | 'error';

export type StatusBarStyle = 'light' | 'dark' | 'default';

// =============================================================================
// Platform Detection
// =============================================================================

/**
 * Check if running in Capacitor native app
 */
export function isNativeApp(): boolean {
  if (typeof window === 'undefined') return false;
  
  // Check for Capacitor
  const win = window as Window & { Capacitor?: { isNative?: boolean; platform?: string } };
  return win.Capacitor?.isNative === true;
}

/**
 * Get current platform
 */
export function getPlatform(): 'ios' | 'android' | 'web' {
  if (typeof window === 'undefined') return 'web';
  
  const win = window as Window & { Capacitor?: { platform?: string } };
  const platform = win.Capacitor?.platform;
  
  if (platform === 'ios') return 'ios';
  if (platform === 'android') return 'android';
  return 'web';
}

// =============================================================================
// Native Capabilities Hook
// =============================================================================

/**
 * Get native capabilities available on current platform
 */
export function useNativeCapabilities(): NativeCapabilities {
  const [capabilities, setCapabilities] = useState<NativeCapabilities>({
    isNative: false,
    platform: 'web',
    hasCamera: false,
    hasPushNotifications: false,
    hasFileSystem: false,
    hasBiometrics: false,
    hasHaptics: false,
    hasShare: false,
  });

  useEffect(() => {
    const checkCapabilities = async () => {
      const isNative = isNativeApp();
      const platform = getPlatform();

      // On native, assume all capabilities
      if (isNative) {
        setCapabilities({
          isNative: true,
          platform,
          hasCamera: true,
          hasPushNotifications: true,
          hasFileSystem: true,
          hasBiometrics: platform !== 'web',
          hasHaptics: true,
          hasShare: true,
        });
        return;
      }

      // On web, check for web APIs
      const hasCamera = 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices;
      const hasPush = 'Notification' in window && 'serviceWorker' in navigator;
      const hasShare = 'share' in navigator;

      setCapabilities({
        isNative: false,
        platform: 'web',
        hasCamera,
        hasPushNotifications: hasPush,
        hasFileSystem: true, // Web File API
        hasBiometrics: false, // WebAuthn requires more setup
        hasHaptics: 'vibrate' in navigator,
        hasShare,
      });
    };

    checkCapabilities();
  }, []);

  return capabilities;
}

// =============================================================================
// Camera Hook
// =============================================================================

/**
 * Camera access hook for document scanning and photo capture
 */
export function useCamera(): {
  takePhoto: (options?: CameraOptions) => Promise<CameraPhoto | null>;
  pickPhoto: (options?: CameraOptions) => Promise<CameraPhoto | null>;
  hasPermission: boolean;
  requestPermission: () => Promise<boolean>;
} {
  const [hasPermission, setHasPermission] = useState(false);

  useEffect(() => {
    // Check camera permission on mount
    if (typeof navigator !== 'undefined' && 'permissions' in navigator) {
      navigator.permissions
        .query({ name: 'camera' as PermissionName })
        .then((result) => {
          setHasPermission(result.state === 'granted');
        })
        .catch(() => {});
    }
  }, []);

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (isNativeApp()) {
      // Capacitor handles permissions automatically
      setHasPermission(true);
      return true;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      stream.getTracks().forEach((t) => t.stop());
      setHasPermission(true);
      return true;
    } catch {
      setHasPermission(false);
      return false;
    }
  }, []);

  const takePhoto = useCallback(async (options?: CameraOptions): Promise<CameraPhoto | null> => {
    if (isNativeApp()) {
      try {
        const { Camera, CameraResultType, CameraSource } = await import('@capacitor/camera');
        
        const photo = await Camera.getPhoto({
          quality: options?.quality ?? 90,
          allowEditing: options?.allowEditing ?? false,
          resultType: CameraResultType.DataUrl,
          source: CameraSource.Camera,
          saveToGallery: options?.saveToGallery ?? false,
          width: options?.width,
          height: options?.height,
          correctOrientation: options?.correctOrientation ?? true,
        });
        
        return {
          dataUrl: photo.dataUrl || '',
          format: photo.format === 'png' ? 'png' : 'jpeg',
          webPath: photo.webPath,
        };
      } catch (error) {
        // User cancelled or error occurred
        console.error('Camera error:', error);
        return null;
      }
    }

    // Web fallback - use file input
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.capture = 'environment';

      input.onchange = async () => {
        const file = input.files?.[0];
        if (!file) {
          resolve(null);
          return;
        }

        const reader = new FileReader();
        reader.onload = () => {
          resolve({
            dataUrl: reader.result as string,
            format: 'jpeg',
          });
        };
        reader.onerror = () => resolve(null);
        reader.readAsDataURL(file);
      };

      input.click();
    });
  }, []);

  const pickPhoto = useCallback(async (options?: CameraOptions): Promise<CameraPhoto | null> => {
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      if (options?.resultType === 'uri') {
        input.multiple = false;
      }

      input.onchange = async () => {
        const file = input.files?.[0];
        if (!file) {
          resolve(null);
          return;
        }

        const reader = new FileReader();
        reader.onload = () => {
          resolve({
            dataUrl: reader.result as string,
            format: file.type.includes('png') ? 'png' : 'jpeg',
          });
        };
        reader.onerror = () => resolve(null);
        reader.readAsDataURL(file);
      };

      input.click();
    });
  }, []);

  return {
    takePhoto,
    pickPhoto,
    hasPermission,
    requestPermission,
  };
}

// =============================================================================
// File System Hook
// =============================================================================

/**
 * File system access for uploads and downloads
 */
export function useFileSystem(): {
  pickFile: (options?: FilePickerOptions) => Promise<FileInfo | null>;
  pickFiles: (options?: FilePickerOptions) => Promise<FileInfo[]>;
  saveFile: (filename: string, data: string, mimeType?: string) => Promise<boolean>;
  readFile: (uri: string) => Promise<string | null>;
  deleteFile: (uri: string) => Promise<boolean>;
} {
  const pickFile = useCallback(async (options?: FilePickerOptions): Promise<FileInfo | null> => {
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      if (options?.types) {
        input.accept = options.types.join(',');
      }

      input.onchange = async () => {
        const file = input.files?.[0];
        if (!file) {
          resolve(null);
          return;
        }

        const reader = new FileReader();
        reader.onload = () => {
          resolve({
            name: file.name,
            type: file.type,
            size: file.size,
            uri: URL.createObjectURL(file),
            data: reader.result as string,
            modifiedAt: file.lastModified,
          });
        };
        reader.onerror = () => resolve(null);
        reader.readAsDataURL(file);
      };

      input.click();
    });
  }, []);

  const pickFiles = useCallback(async (options?: FilePickerOptions): Promise<FileInfo[]> => {
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.multiple = options?.multiple !== false;
      if (options?.types) {
        input.accept = options.types.join(',');
      }

      input.onchange = async () => {
        const files = Array.from(input.files || []);
        const results: FileInfo[] = [];

        for (const file of files) {
          results.push({
            name: file.name,
            type: file.type,
            size: file.size,
            uri: URL.createObjectURL(file),
            modifiedAt: file.lastModified,
          });
        }

        resolve(results);
      };

      input.click();
    });
  }, []);

  const saveFile = useCallback(async (filename: string, data: string, mimeType = 'text/plain'): Promise<boolean> => {
    try {
      if (isNativeApp()) {
        // Dynamically import Capacitor Filesystem plugin
        const { Filesystem, Directory, Encoding } = await import('@capacitor/filesystem');
        
        await Filesystem.writeFile({
          path: filename,
          data: data,
          directory: Directory.Documents,
          encoding: Encoding.UTF8,
        });
        return true;
      }

      // Web download fallback
      const blob = new Blob([data], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      return true;
    } catch {
      return false;
    }
  }, []);

  const readFile = useCallback(async (uri: string): Promise<string | null> => {
    try {
      if (isNativeApp()) {
        // Dynamically import Capacitor Filesystem plugin
        const { Filesystem, Directory, Encoding } = await import('@capacitor/filesystem');
        
        const result = await Filesystem.readFile({
          path: uri,
          directory: Directory.Documents,
          encoding: Encoding.UTF8,
        });
        
        return typeof result.data === 'string' ? result.data : null;
      }

      const response = await fetch(uri);
      return await response.text();
    } catch {
      return null;
    }
  }, []);

  const deleteFile = useCallback(async (uri: string): Promise<boolean> => {
    try {
      if (isNativeApp()) {
        // Dynamically import Capacitor Filesystem plugin
        const { Filesystem, Directory } = await import('@capacitor/filesystem');
        
        await Filesystem.deleteFile({
          path: uri,
          directory: Directory.Documents,
        });
        return true;
      }
      
      // Web: revoke object URL
      URL.revokeObjectURL(uri);
      return true;
    } catch {
      return false;
    }
  }, []);

  return {
    pickFile,
    pickFiles,
    saveFile,
    readFile,
    deleteFile,
  };
}

// =============================================================================
// Push Notifications Hook
// =============================================================================

/**
 * Push notification support
 */
export function usePushNotifications(): {
  hasPermission: boolean;
  requestPermission: () => Promise<boolean>;
  notifications: PushNotification[];
  registerToken: () => Promise<string | null>;
  scheduleLocal: (options: LocalNotificationOptions) => Promise<number | null>;
  cancelLocal: (id: number) => Promise<boolean>;
  clearNotifications: () => void;
} {
  const [hasPermission, setHasPermission] = useState(false);
  const [notifications, setNotifications] = useState<PushNotification[]>([]);

  useEffect(() => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      setHasPermission(Notification.permission === 'granted');
    }
  }, []);

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (isNativeApp()) {
      // Capacitor handles this
      setHasPermission(true);
      return true;
    }

    if ('Notification' in window) {
      const result = await Notification.requestPermission();
      const granted = result === 'granted';
      setHasPermission(granted);
      return granted;
    }

    return false;
  }, []);

  const registerToken = useCallback(async (): Promise<string | null> => {
    if (isNativeApp()) {
      try {
        // Dynamically import Capacitor PushNotifications plugin
        const { PushNotifications } = await import('@capacitor/push-notifications');
        
        // Request permission first
        const permResult = await PushNotifications.requestPermissions();
        if (permResult.receive !== 'granted') {
          return null;
        }
        
        // Register for push notifications
        await PushNotifications.register();
        
        // Get the FCM/APNS token
        return new Promise((resolve) => {
          PushNotifications.addListener('registration', (token) => {
            resolve(token.value);
          });
          
          PushNotifications.addListener('registrationError', () => {
            resolve(null);
          });
          
          // Timeout after 10 seconds
          setTimeout(() => resolve(null), 10000);
        });
      } catch {
        // Capacitor plugin not available, return null
        return null;
      }
    }

    // Web push requires service worker setup
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        return subscription?.endpoint || null;
      } catch {
        return null;
      }
    }

    return null;
  }, []);

  const scheduleLocal = useCallback(async (options: LocalNotificationOptions): Promise<number | null> => {
    const id = options.id || Date.now();

    if (isNativeApp()) {
      // Would use Capacitor LocalNotifications plugin
      return id;
    }

    // Web fallback - show immediately or schedule
    if (hasPermission && options.schedule && 'at' in options.schedule) {
      const delay = options.schedule.at.getTime() - Date.now();
      if (delay > 0) {
        setTimeout(() => {
          new Notification(options.title, { body: options.body });
        }, delay);
      }
    } else if (hasPermission) {
      new Notification(options.title, { body: options.body });
    }

    return id;
  }, [hasPermission]);

  const cancelLocal = useCallback(async (id: number): Promise<boolean> => {
    if (isNativeApp()) {
      // Would use Capacitor LocalNotifications plugin
      return true;
    }
    return true;
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  return {
    hasPermission,
    requestPermission,
    notifications,
    registerToken,
    scheduleLocal,
    cancelLocal,
    clearNotifications,
  };
}

// =============================================================================
// Haptics Hook
// =============================================================================

/**
 * Haptic feedback for native feel
 */
export function useHaptics(): {
  impact: (style?: HapticStyle) => void;
  notification: (type: 'success' | 'warning' | 'error') => void;
  selectionStart: () => void;
  selectionChanged: () => void;
  selectionEnd: () => void;
} {
  const impact = useCallback((style: HapticStyle = 'medium') => {
    if (isNativeApp()) {
      // Would use Capacitor Haptics plugin
      return;
    }

    // Web vibration fallback
    if ('vibrate' in navigator) {
      const patterns: Record<HapticStyle, number | number[]> = {
        light: 10,
        medium: 25,
        heavy: 50,
        selection: 5,
        success: [10, 50, 10],
        warning: [25, 25, 25],
        error: [50, 25, 50],
      };
      navigator.vibrate(patterns[style] || 25);
    }
  }, []);

  const notification = useCallback((type: 'success' | 'warning' | 'error') => {
    impact(type);
  }, [impact]);

  const selectionStart = useCallback(() => {
    impact('selection');
  }, [impact]);

  const selectionChanged = useCallback(() => {
    impact('selection');
  }, [impact]);

  const selectionEnd = useCallback(() => {
    impact('selection');
  }, [impact]);

  return {
    impact,
    notification,
    selectionStart,
    selectionChanged,
    selectionEnd,
  };
}

// =============================================================================
// Share Hook
// =============================================================================

/**
 * Native share functionality
 */
export function useShare(): {
  canShare: boolean;
  share: (options: ShareOptions) => Promise<boolean>;
} {
  const [canShare, setCanShare] = useState(false);

  useEffect(() => {
    setCanShare(
      isNativeApp() || (typeof navigator !== 'undefined' && 'share' in navigator)
    );
  }, []);

  const share = useCallback(async (options: ShareOptions): Promise<boolean> => {
    try {
      if (isNativeApp()) {
        // Would use Capacitor Share plugin
        return true;
      }

      if (typeof navigator !== 'undefined' && 'share' in navigator) {
        await (navigator as Navigator).share({
          title: options.title,
          text: options.text,
          url: options.url,
        });
        return true;
      }

      // Fallback: copy to clipboard
      if (options.url && typeof navigator !== 'undefined' && (navigator as Navigator).clipboard) {
        await (navigator as Navigator).clipboard.writeText(options.url);
        return true;
      }

      return false;
    } catch {
      return false;
    }
  }, []);

  return {
    canShare,
    share,
  };
}

// =============================================================================
// Clipboard Hook
// =============================================================================

/**
 * Clipboard access
 */
export function useClipboard(): {
  copy: (text: string) => Promise<boolean>;
  paste: () => Promise<string | null>;
} {
  const copy = useCallback(async (text: string): Promise<boolean> => {
    try {
      if (isNativeApp()) {
        // Would use Capacitor Clipboard plugin
        return true;
      }

      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fallback for older browsers
      try {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        return true;
      } catch {
        return false;
      }
    }
  }, []);

  const paste = useCallback(async (): Promise<string | null> => {
    try {
      if (isNativeApp()) {
        // Would use Capacitor Clipboard plugin
        return null; // Would return actual content
      }

      return await navigator.clipboard.readText();
    } catch {
      return null;
    }
  }, []);

  return {
    copy,
    paste,
  };
}

// =============================================================================
// Status Bar Hook
// =============================================================================

/**
 * Status bar control (iOS/Android)
 */
export function useStatusBar(): {
  setStyle: (style: StatusBarStyle) => void;
  setBackgroundColor: (color: string) => void;
  show: () => void;
  hide: () => void;
} {
  const setStyle = useCallback((style: StatusBarStyle) => {
    if (isNativeApp()) {
      // Would use Capacitor StatusBar plugin
    }
    
    // Web: update theme-color meta tag
    if (typeof document !== 'undefined') {
      let meta = document.querySelector('meta[name="theme-color"]');
      if (!meta) {
        meta = document.createElement('meta');
        meta.setAttribute('name', 'theme-color');
        document.head.appendChild(meta);
      }
      meta.setAttribute('content', style === 'dark' ? '#000000' : '#ffffff');
    }
  }, []);

  const setBackgroundColor = useCallback((color: string) => {
    if (isNativeApp()) {
    }
    
    if (typeof document !== 'undefined') {
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) {
        meta.setAttribute('content', color);
      }
    }
  }, []);

  const show = useCallback(() => {
    if (isNativeApp()) {
    }
  }, []);

  const hide = useCallback(() => {
    if (isNativeApp()) {
    }
  }, []);

  return {
    setStyle,
    setBackgroundColor,
    show,
    hide,
  };
}

// =============================================================================
// Biometric Auth Hook
// =============================================================================

/**
 * Biometric authentication (fingerprint/face)
 */
export function useBiometricAuth(): {
  isAvailable: boolean;
  authenticate: (reason?: string) => Promise<BiometricResult>;
} {
  const [isAvailable, setIsAvailable] = useState(false);

  useEffect(() => {
    const checkAvailability = async () => {
      if (isNativeApp()) {
        // Assume available on native (would check via Capacitor)
        setIsAvailable(true);
        return;
      }

      // WebAuthn check
      if ('PublicKeyCredential' in window) {
        try {
          const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
          setIsAvailable(available);
        } catch {
          setIsAvailable(false);
        }
      }
    };

    checkAvailability();
  }, []);

  const authenticate = useCallback(async (reason = 'Authenticate'): Promise<BiometricResult> => {
    if (isNativeApp()) {
      try {
        // Dynamically import Capacitor BiometricAuth plugin
        const { NativeBiometric } = await import('capacitor-native-biometric');
        
        // Check if biometric auth is available
        const result = await NativeBiometric.isAvailable() as unknown as { isAvailable: boolean; biometryType?: number };
        if (!result.isAvailable) {
          return { verified: false, error: 'Biometric authentication not available' };
        }
        
        // Perform authentication
        await (NativeBiometric as any).verifyIdentity({
          reason,
          title: 'Authentication Required',
          subtitle: reason,
          description: 'Please authenticate to continue',
        });
        
        // If we get here, auth succeeded
        return { 
          verified: true, 
          method: result.biometryType === 1 ? 'fingerprint' : 'face' 
        };
      } catch (error) {
        // Authentication failed or was cancelled
        return { 
          verified: false, 
          error: error instanceof Error ? error.message : 'Authentication failed' 
        };
      }
    }

    // Web: use WebAuthn for biometric authentication
    if ('PublicKeyCredential' in window) {
      try {
        const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
        if (!available) {
          return { verified: false, error: 'Platform authenticator not available' };
        }
        
        // Create a challenge for WebAuthn
        const challenge = new Uint8Array(32);
        crypto.getRandomValues(challenge);
        
        // Note: Full WebAuthn implementation requires server-side credential storage
        // This is a client-side check only
        return { verified: false, error: 'WebAuthn requires server-side setup' };
      } catch (error) {
        return { verified: false, error: 'WebAuthn not available' };
      }
    }
    
    return { verified: false, error: 'Not available on web' };
  }, []);

  return {
    isAvailable,
    authenticate,
  };
}

// =============================================================================
// App State Hook
// =============================================================================

/**
 * App lifecycle state (foreground/background)
 */
export function useAppState(): {
  isActive: boolean;
  isForeground: boolean;
} {
  const [isActive, setIsActive] = useState(true);
  const [isForeground, setIsForeground] = useState(true);

  useEffect(() => {
    if (typeof document === 'undefined') return;

    const handleVisibilityChange = () => {
      const visible = document.visibilityState === 'visible';
      setIsActive(visible);
      setIsForeground(visible);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  return {
    isActive,
    isForeground,
  };
}

// =============================================================================
// Export all hooks
// =============================================================================

export default {
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
};
