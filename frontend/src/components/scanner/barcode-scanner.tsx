'use client';

import * as React from 'react';
import {
  useCameraScanner,
  parseManufacturingBarcode,
  type BarcodeResult,
  type ScannerConfig,
  type BarcodeFormat,
} from '@/hooks/use-camera-scanner';
import { cn } from '@/lib/utils';

interface BarcodeScannerProps {
  className?: string;
  onScan?: (result: BarcodeResult, parsed: ReturnType<typeof parseManufacturingBarcode>) => void;
  onError?: (error: string) => void;
  config?: ScannerConfig;
  showControls?: boolean;
  showLastResult?: boolean;
  autoStart?: boolean;
  continuousMode?: boolean;
  scanCooldown?: number;
}

/**
 * Camera-based barcode/QR code scanner component
 */
export function BarcodeScanner({
  className,
  onScan,
  onError,
  config,
  showControls = true,
  showLastResult = true,
  autoStart = false,
  continuousMode = false,
  scanCooldown = 2000,
}: BarcodeScannerProps) {
  const {
    state,
    videoRef,
    canvasRef,
    start,
    stop,
    switchCamera,
    captureFrame,
  } = useCameraScanner(config);

  const lastScanTimeRef = React.useRef<number>(0);
  const [isPaused, setIsPaused] = React.useState(false);

  // Auto-start if enabled
  React.useEffect(() => {
    if (autoStart && state.isSupported) {
      start();
    }
  }, [autoStart, state.isSupported, start]);

  // Handle new scan results
  React.useEffect(() => {
    if (!state.lastResult) return;

    const now = Date.now();
    if (now - lastScanTimeRef.current < scanCooldown) {
      return;
    }
    lastScanTimeRef.current = now;

    const parsed = parseManufacturingBarcode(state.lastResult.rawValue);
    onScan?.(state.lastResult, parsed);

    // If not in continuous mode, pause after scan
    if (!continuousMode) {
      setIsPaused(true);
    }
  }, [state.lastResult, onScan, continuousMode, scanCooldown]);

  // Handle errors
  React.useEffect(() => {
    if (state.error) {
      onError?.(state.error);
    }
  }, [state.error, onError]);

  const handleStart = async () => {
    setIsPaused(false);
    await start();
  };

  const handleStop = () => {
    setIsPaused(false);
    stop();
  };

  const handleResume = () => {
    setIsPaused(false);
  };

  const handleCapture = () => {
    const frame = captureFrame();
    if (frame) {
      // Create download link
      const link = document.createElement('a');
      link.href = frame;
      link.download = `scan-${Date.now()}.jpg`;
      link.click();
    }
  };

  if (!state.isSupported) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 p-8',
          className
        )}
      >
        <CameraOffIcon className="mb-4 h-12 w-12 text-gray-400" />
        <h3 className="text-lg font-medium text-gray-900">
          Scanner Not Supported
        </h3>
        <p className="mt-2 text-center text-sm text-gray-500">
          Your browser doesn't support the Barcode Detection API.
          <br />
          Please use Chrome, Edge, or Opera on Android.
        </p>
      </div>
    );
  }

  if (state.hasPermission === false) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center rounded-lg border border-dashed border-red-300 bg-red-50 p-8',
          className
        )}
      >
        <LockIcon className="mb-4 h-12 w-12 text-red-400" />
        <h3 className="text-lg font-medium text-red-900">
          Camera Access Denied
        </h3>
        <p className="mt-2 text-center text-sm text-red-500">
          Please allow camera access in your browser settings to use the scanner.
        </p>
        <button
          onClick={handleStart}
          className="mt-4 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Camera viewfinder */}
      <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-black">
        <video
          ref={videoRef as React.RefObject<HTMLVideoElement>}
          className={cn(
            'h-full w-full object-cover',
            isPaused && 'opacity-50'
          )}
          playsInline
          muted
          autoPlay
        />
        
        {/* Hidden canvas for processing */}
        <canvas ref={canvasRef as React.RefObject<HTMLCanvasElement>} className="hidden" />

        {/* Scanning overlay */}
        {state.isScanning && !isPaused && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="relative h-48 w-48">
              {/* Corner brackets */}
              <div className="absolute left-0 top-0 h-8 w-8 border-l-4 border-t-4 border-white" />
              <div className="absolute right-0 top-0 h-8 w-8 border-r-4 border-t-4 border-white" />
              <div className="absolute bottom-0 left-0 h-8 w-8 border-b-4 border-l-4 border-white" />
              <div className="absolute bottom-0 right-0 h-8 w-8 border-b-4 border-r-4 border-white" />
              
              {/* Scanning line animation */}
              <div className="absolute inset-x-0 top-1/2 h-0.5 animate-pulse bg-green-400" />
            </div>
          </div>
        )}

        {/* Paused overlay */}
        {isPaused && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/50">
            <CheckCircleIcon className="mb-2 h-12 w-12 text-green-400" />
            <p className="text-lg font-medium text-white">Scan Complete</p>
            <button
              onClick={handleResume}
              className="mt-4 rounded-md bg-white px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-100"
            >
              Scan Another
            </button>
          </div>
        )}

        {/* Not scanning state */}
        {!state.isScanning && !state.error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900/80">
            <CameraIcon className="mb-4 h-12 w-12 text-gray-400" />
            <p className="text-gray-300">Camera not active</p>
            <button
              onClick={handleStart}
              className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Start Scanner
            </button>
          </div>
        )}

        {/* Error state */}
        {state.error && !state.isScanning && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-red-900/80">
            <AlertIcon className="mb-4 h-12 w-12 text-red-400" />
            <p className="text-red-200">{state.error}</p>
            <button
              onClick={handleStart}
              className="mt-4 rounded-md bg-white px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-100"
            >
              Try Again
            </button>
          </div>
        )}
      </div>

      {/* Controls */}
      {showControls && state.isScanning && (
        <div className="mt-4 flex items-center justify-center gap-4">
          <button
            onClick={switchCamera}
            className="flex items-center gap-2 rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200"
            title="Switch Camera"
          >
            <FlipCameraIcon className="h-5 w-5" />
            <span className="hidden sm:inline">Switch</span>
          </button>

          <button
            onClick={handleCapture}
            className="flex items-center gap-2 rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200"
            title="Capture Frame"
          >
            <CameraIcon className="h-5 w-5" />
            <span className="hidden sm:inline">Capture</span>
          </button>

          <button
            onClick={handleStop}
            className="flex items-center gap-2 rounded-md bg-red-100 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-200"
            title="Stop Scanner"
          >
            <StopIcon className="h-5 w-5" />
            <span className="hidden sm:inline">Stop</span>
          </button>
        </div>
      )}

      {/* Last result */}
      {showLastResult && state.lastResult && (
        <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium uppercase text-gray-500">
                Last Scanned
              </p>
              <p className="mt-1 break-all font-mono text-sm text-gray-900">
                {state.lastResult.rawValue}
              </p>
              <p className="mt-1 text-xs text-gray-500">
                Format: {state.lastResult.format} •{' '}
                {new Date(state.lastResult.timestamp).toLocaleTimeString()}
              </p>
            </div>
            <span className="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700">
              {state.lastResult.format.replace('_', ' ')}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

interface ScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onScan: (result: BarcodeResult, parsed: ReturnType<typeof parseManufacturingBarcode>) => void;
  title?: string;
  description?: string;
  formats?: BarcodeFormat[];
}

/**
 * Modal wrapper for the barcode scanner
 */
export function ScannerModal({
  isOpen,
  onClose,
  onScan,
  title = 'Scan Barcode',
  description = 'Point your camera at a barcode or QR code',
  formats,
}: ScannerModalProps) {
  const handleScan = (
    result: BarcodeResult,
    parsed: ReturnType<typeof parseManufacturingBarcode>
  ) => {
    onScan(result, parsed);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            <p className="text-sm text-gray-500">{description}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <XIcon className="h-5 w-5" />
          </button>
        </div>

        <BarcodeScanner
          onScan={handleScan}
          autoStart
          config={{ formats }}
          showControls
          showLastResult={false}
        />
      </div>
    </div>
  );
}

interface ScanButtonProps {
  onScan: (result: BarcodeResult, parsed: ReturnType<typeof parseManufacturingBarcode>) => void;
  className?: string;
  label?: string;
  formats?: BarcodeFormat[];
}

/**
 * Button that opens a scanner modal
 */
export function ScanButton({
  onScan,
  className,
  label = 'Scan',
  formats,
}: ScanButtonProps) {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className={cn(
          'inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700',
          className
        )}
      >
        <QRCodeIcon className="h-5 w-5" />
        {label}
      </button>

      <ScannerModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onScan={onScan}
        formats={formats}
      />
    </>
  );
}

// Icon components
function CameraIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/>
      <circle cx="12" cy="13" r="3"/>
    </svg>
  );
}

function CameraOffIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="2" y1="2" x2="22" y2="22"/>
      <path d="M9.5 4h5l2.5 3h3a2 2 0 0 1 2 2v9.5"/>
      <path d="M6.5 6.5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h11"/>
      <path d="M9.172 9.172a3 3 0 0 0 4.656 4.656"/>
    </svg>
  );
}

function LockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  );
}

function FlipCameraIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 3h5v5"/>
      <path d="M8 21H3v-5"/>
      <path d="M21 3l-6.5 6.5"/>
      <path d="M3 21l6.5-6.5"/>
    </svg>
  );
}

function StopIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
    </svg>
  );
}

function AlertIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="8" x2="12" y2="12"/>
      <line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="9 12 12 15 16 10"/>
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/>
      <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  );
}

function QRCodeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="6" height="6"/>
      <rect x="15" y="3" width="6" height="6"/>
      <rect x="3" y="15" width="6" height="6"/>
      <path d="M15 15h.01"/>
      <path d="M21 15h.01"/>
      <path d="M15 21h.01"/>
      <path d="M21 21h.01"/>
      <path d="M18 18h.01"/>
    </svg>
  );
}
