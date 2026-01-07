'use client';

import * as React from 'react';
import { Download, RefreshCw, X, Wifi, WifiOff } from 'lucide-react';
import { usePWA, useIsPWA } from '@/hooks/use-pwa';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

/**
 * PWA Provider component
 * Handles service worker registration and displays update notifications
 */
export function PWAProvider({ children }: { children: React.ReactNode }) {
  const { 
    isSupported, 
    isOnline, 
    isUpdateAvailable, 
    register, 
    skipWaiting 
  } = usePWA();
  
  const [showOfflineToast, setShowOfflineToast] = React.useState(false);
  const [showUpdateToast, setShowUpdateToast] = React.useState(false);
  const [showInstallPrompt, setShowInstallPrompt] = React.useState(false);
  const [deferredPrompt, setDeferredPrompt] = React.useState<any>(null);

  // Register service worker on mount
  React.useEffect(() => {
    if (isSupported && process.env.NODE_ENV === 'production') {
      register();
    }
  }, [isSupported, register]);

  // Show offline toast when going offline
  React.useEffect(() => {
    if (!isOnline) {
      setShowOfflineToast(true);
    } else {
      // Hide after a brief moment when coming back online
      const timer = setTimeout(() => setShowOfflineToast(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [isOnline]);

  // Show update toast when update is available
  React.useEffect(() => {
    if (isUpdateAvailable) {
      setShowUpdateToast(true);
    }
  }, [isUpdateAvailable]);

  // Listen for beforeinstallprompt event
  React.useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      // Show install prompt after a delay
      setTimeout(() => setShowInstallPrompt(true), 30000); // 30 seconds
    };

    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;

    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
      console.log('[PWA] App installed');
    }
    
    setDeferredPrompt(null);
    setShowInstallPrompt(false);
  };

  const handleUpdate = () => {
    skipWaiting();
    setShowUpdateToast(false);
  };

  return (
    <>
      {children}

      {/* Offline Toast */}
      <Toast
        show={showOfflineToast}
        onClose={() => setShowOfflineToast(false)}
        variant={isOnline ? 'success' : 'warning'}
      >
        <div className="flex items-center gap-3">
          {isOnline ? (
            <>
              <Wifi className="h-5 w-5" />
              <span>You're back online</span>
            </>
          ) : (
            <>
              <WifiOff className="h-5 w-5" />
              <span>You're offline. Some features may be unavailable.</span>
            </>
          )}
        </div>
      </Toast>

      {/* Update Toast */}
      <Toast
        show={showUpdateToast}
        onClose={() => setShowUpdateToast(false)}
        variant="info"
        persistent
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <RefreshCw className="h-5 w-5" />
            <span>A new version is available</span>
          </div>
          <Button size="sm" onClick={handleUpdate}>
            Update Now
          </Button>
        </div>
      </Toast>

      {/* Install Prompt */}
      <Toast
        show={showInstallPrompt && !!deferredPrompt}
        onClose={() => setShowInstallPrompt(false)}
        variant="default"
        persistent
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Download className="h-5 w-5" />
            <div>
              <p className="font-medium">Install SENSEI</p>
              <p className="text-sm text-muted-foreground">Get the app for a better experience</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setShowInstallPrompt(false)}>
              Later
            </Button>
            <Button size="sm" onClick={handleInstall}>
              Install
            </Button>
          </div>
        </div>
      </Toast>
    </>
  );
}

/**
 * Toast component for PWA notifications
 */
interface ToastProps {
  show: boolean;
  onClose: () => void;
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'info';
  persistent?: boolean;
}

function Toast({ show, onClose, children, variant = 'default', persistent = false }: ToastProps) {
  React.useEffect(() => {
    if (show && !persistent) {
      const timer = setTimeout(onClose, 5000);
      return () => clearTimeout(timer);
    }
  }, [show, persistent, onClose]);

  if (!show) return null;

  const variantClasses = {
    default: 'bg-background border',
    success: 'bg-success text-success-foreground',
    warning: 'bg-warning text-warning-foreground',
    info: 'bg-primary text-primary-foreground',
  };

  return (
    <div
      className={cn(
        'fixed bottom-4 left-1/2 -translate-x-1/2 z-50',
        'px-4 py-3 rounded-lg shadow-lg',
        'animate-in slide-in-from-bottom-5 fade-in duration-300',
        variantClasses[variant]
      )}
    >
      <div className="flex items-center gap-2">
        {children}
        {persistent && (
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-white/20 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Hook to detect if app should show install prompt
 */
export function useInstallPrompt() {
  const isPWA = useIsPWA();
  const [canInstall, setCanInstall] = React.useState(false);
  const [deferredPrompt, setDeferredPrompt] = React.useState<any>(null);

  React.useEffect(() => {
    if (isPWA) return; // Already installed

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setCanInstall(true);
    };

    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, [isPWA]);

  const install = async () => {
    if (!deferredPrompt) return false;

    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    
    setDeferredPrompt(null);
    setCanInstall(false);
    
    return outcome === 'accepted';
  };

  return { canInstall, install, isPWA };
}
