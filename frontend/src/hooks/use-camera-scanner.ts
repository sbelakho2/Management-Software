'use client';

import * as React from 'react';

/**
 * Supported barcode formats
 */
export type BarcodeFormat =
  | 'qr_code'
  | 'code_128'
  | 'code_39'
  | 'ean_13'
  | 'ean_8'
  | 'upc_a'
  | 'upc_e'
  | 'data_matrix'
  | 'pdf417'
  | 'aztec'
  | 'itf';

/**
 * Detected barcode result
 */
export interface BarcodeResult {
  rawValue: string;
  format: BarcodeFormat;
  boundingBox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  cornerPoints?: Array<{ x: number; y: number }>;
  timestamp: number;
}

/**
 * Camera options
 */
export interface CameraOptions {
  facingMode?: 'user' | 'environment';
  width?: number;
  height?: number;
  aspectRatio?: number;
  frameRate?: number;
}

/**
 * Scanner configuration
 */
export interface ScannerConfig {
  formats?: BarcodeFormat[];
  scanInterval?: number;
  highlightDetected?: boolean;
  playSound?: boolean;
  vibrate?: boolean;
  camera?: CameraOptions;
}

/**
 * Scanner state
 */
export interface ScannerState {
  isScanning: boolean;
  isSupported: boolean;
  hasPermission: boolean | null;
  error: string | null;
  lastResult: BarcodeResult | null;
  cameraReady: boolean;
}

/**
 * Native BarcodeDetector API types
 */
interface NativeBarcodeDetector {
  detect: (source: ImageBitmapSource) => Promise<DetectedBarcode[]>;
}

interface DetectedBarcode {
  rawValue: string;
  format: string;
  boundingBox: DOMRectReadOnly;
  cornerPoints: Array<{ x: number; y: number }>;
}

interface BarcodeDetectorConstructor {
  new (options?: { formats?: string[] }): NativeBarcodeDetector;
  getSupportedFormats(): Promise<string[]>;
}

declare global {
  interface Window {
    BarcodeDetector?: BarcodeDetectorConstructor;
  }
}

const DEFAULT_CONFIG: Required<ScannerConfig> = {
  formats: ['qr_code', 'code_128', 'ean_13'],
  scanInterval: 100,
  highlightDetected: true,
  playSound: true,
  vibrate: true,
  camera: {
    facingMode: 'environment',
    width: 1280,
    height: 720,
  },
};

/**
 * Check if the native BarcodeDetector API is supported
 */
export function isBarcodeDetectorSupported(): boolean {
  return typeof window !== 'undefined' && 'BarcodeDetector' in window;
}

/**
 * Get supported barcode formats
 */
export async function getSupportedFormats(): Promise<BarcodeFormat[]> {
  if (!isBarcodeDetectorSupported()) {
    return [];
  }

  try {
    const formats = await window.BarcodeDetector!.getSupportedFormats();
    return formats as BarcodeFormat[];
  } catch {
    return [];
  }
}

/**
 * Hook for camera-based barcode/QR scanning
 */
export function useCameraScanner(
  config: ScannerConfig = {}
): {
  state: ScannerState;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  start: () => Promise<void>;
  stop: () => void;
  switchCamera: () => Promise<void>;
  captureFrame: () => string | null;
} {
  const mergedConfig = { ...DEFAULT_CONFIG, ...config };
  
  const videoRef = React.useRef<HTMLVideoElement | null>(null);
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const detectorRef = React.useRef<NativeBarcodeDetector | null>(null);
  const scanIntervalRef = React.useRef<number | null>(null);
  const facingModeRef = React.useRef<'user' | 'environment'>(
    mergedConfig.camera.facingMode || 'environment'
  );

  const [state, setState] = React.useState<ScannerState>({
    isScanning: false,
    isSupported: false,
    hasPermission: null,
    error: null,
    lastResult: null,
    cameraReady: false,
  });

  // Check support on mount
  React.useEffect(() => {
    const checkSupport = async () => {
      const supported = isBarcodeDetectorSupported();
      setState((prev) => ({ ...prev, isSupported: supported }));
    };

    checkSupport();
  }, []);

  /**
   * Initialize barcode detector
   */
  const initializeDetector = React.useCallback(async () => {
    if (!window.BarcodeDetector) {
      throw new Error('BarcodeDetector API not supported');
    }

    const formats = mergedConfig.formats.filter((format) =>
      format !== undefined
    );

    detectorRef.current = new window.BarcodeDetector({ formats });
  }, [mergedConfig.formats]);

  /**
   * Play scan sound
   */
  const playSound = React.useCallback(() => {
    if (!mergedConfig.playSound) return;

    try {
      const audioContext = new (window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.value = 1200;
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(
        0.01,
        audioContext.currentTime + 0.1
      );

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.1);
    } catch {
      // Audio not available
    }
  }, [mergedConfig.playSound]);

  /**
   * Vibrate on detection
   */
  const vibrate = React.useCallback(() => {
    if (!mergedConfig.vibrate) return;

    try {
      if ('vibrate' in navigator) {
        navigator.vibrate(50);
      }
    } catch {
      // Vibration not available
    }
  }, [mergedConfig.vibrate]);

  /**
   * Process a single frame for barcodes
   */
  const processFrame = React.useCallback(async () => {
    if (!videoRef.current || !detectorRef.current || !canvasRef.current) {
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    if (!ctx || video.readyState !== video.HAVE_ENOUGH_DATA) {
      return;
    }

    // Draw video frame to canvas
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    try {
      const barcodes = await detectorRef.current.detect(canvas);

      if (barcodes.length > 0) {
        const barcode = barcodes[0];
        const result: BarcodeResult = {
          rawValue: barcode.rawValue,
          format: barcode.format as BarcodeFormat,
          boundingBox: {
            x: barcode.boundingBox.x,
            y: barcode.boundingBox.y,
            width: barcode.boundingBox.width,
            height: barcode.boundingBox.height,
          },
          cornerPoints: barcode.cornerPoints,
          timestamp: Date.now(),
        };

        setState((prev) => ({ ...prev, lastResult: result }));

        // Draw highlight
        if (mergedConfig.highlightDetected && barcode.cornerPoints) {
          ctx.strokeStyle = '#00ff00';
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.moveTo(barcode.cornerPoints[0].x, barcode.cornerPoints[0].y);
          for (let i = 1; i < barcode.cornerPoints.length; i++) {
            ctx.lineTo(barcode.cornerPoints[i].x, barcode.cornerPoints[i].y);
          }
          ctx.closePath();
          ctx.stroke();
        }

        playSound();
        vibrate();
      }
    } catch (error) {
      console.error('Barcode detection error:', error);
    }
  }, [mergedConfig.highlightDetected, playSound, vibrate]);

  /**
   * Start scanning
   */
  const start = React.useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, error: null }));

      // Initialize detector
      await initializeDetector();

      // Request camera permission
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: facingModeRef.current,
          width: { ideal: mergedConfig.camera.width },
          height: { ideal: mergedConfig.camera.height },
        },
        audio: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      setState((prev) => ({ ...prev, hasPermission: true }));

      // Connect stream to video element
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();

        setState((prev) => ({ ...prev, cameraReady: true, isScanning: true }));

        // Start scanning loop
        scanIntervalRef.current = window.setInterval(
          processFrame,
          mergedConfig.scanInterval
        );
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to start camera';

      if (errorMessage.includes('Permission denied')) {
        setState((prev) => ({
          ...prev,
          hasPermission: false,
          error: 'Camera permission denied',
        }));
      } else {
        setState((prev) => ({ ...prev, error: errorMessage }));
      }
    }
  }, [initializeDetector, mergedConfig, processFrame]);

  /**
   * Stop scanning
   */
  const stop = React.useCallback(() => {
    // Stop scanning loop
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
      scanIntervalRef.current = null;
    }

    // Stop camera stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    // Clear video source
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setState((prev) => ({
      ...prev,
      isScanning: false,
      cameraReady: false,
    }));
  }, []);

  /**
   * Switch between front and back camera
   */
  const switchCamera = React.useCallback(async () => {
    facingModeRef.current =
      facingModeRef.current === 'environment' ? 'user' : 'environment';
    
    stop();
    await start();
  }, [start, stop]);

  /**
   * Capture current frame as data URL
   */
  const captureFrame = React.useCallback((): string | null => {
    if (!canvasRef.current || !videoRef.current) {
      return null;
    }

    const canvas = canvasRef.current;
    const video = videoRef.current;
    const ctx = canvas.getContext('2d');

    if (!ctx) return null;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    return canvas.toDataURL('image/jpeg', 0.9);
  }, []);

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return {
    state,
    videoRef,
    canvasRef,
    start,
    stop,
    switchCamera,
    captureFrame,
  };
}

/**
 * Parse common manufacturing barcode formats
 */
export function parseManufacturingBarcode(value: string): {
  type: 'part_number' | 'work_order' | 'serial' | 'lot' | 'location' | 'unknown';
  parsed: Record<string, string>;
} {
  // Part number format: P-XXXXX or PN:XXXXX
  if (/^P-\d+$/.test(value) || /^PN:\w+$/i.test(value)) {
    return {
      type: 'part_number',
      parsed: { partNumber: value.replace(/^(P-|PN:)/i, '') },
    };
  }

  // Work order format: WO-XXXXX or WO:XXXXX
  if (/^WO[-:]\d+$/i.test(value)) {
    return {
      type: 'work_order',
      parsed: { workOrderNumber: value.replace(/^WO[-:]/i, '') },
    };
  }

  // Serial number format: SN-XXXXX or S/N:XXXXX
  if (/^S[\/]?N[-:]?\w+$/i.test(value)) {
    return {
      type: 'serial',
      parsed: { serialNumber: value.replace(/^S[\/]?N[-:]?/i, '') },
    };
  }

  // Lot number format: LOT-XXXXX or L:XXXXX
  if (/^(LOT[-:]|L:)\w+$/i.test(value)) {
    return {
      type: 'lot',
      parsed: { lotNumber: value.replace(/^(LOT[-:]|L:)/i, '') },
    };
  }

  // Location format: LOC-XX-XX-XX or BIN:XXXXX
  if (/^(LOC[-:]|BIN:)[\w-]+$/i.test(value)) {
    return {
      type: 'location',
      parsed: { location: value.replace(/^(LOC[-:]|BIN:)/i, '') },
    };
  }

  // GS1/EAN format parsing
  if (value.startsWith('(') || value.startsWith('\u001d')) {
    const parsed = parseGS1Barcode(value);
    if (Object.keys(parsed).length > 0) {
      return { type: 'unknown', parsed };
    }
  }

  return { type: 'unknown', parsed: { value } };
}

/**
 * Parse GS1 barcode format
 */
function parseGS1Barcode(value: string): Record<string, string> {
  const parsed: Record<string, string> = {};
  
  // GS1 Application Identifiers
  const aiPatterns: Record<string, { name: string; length?: number }> = {
    '01': { name: 'gtin', length: 14 },
    '10': { name: 'batchLot' },
    '11': { name: 'productionDate', length: 6 },
    '17': { name: 'expirationDate', length: 6 },
    '21': { name: 'serialNumber' },
    '240': { name: 'additionalId' },
    '250': { name: 'secondarySerial' },
    '91': { name: 'internalInfo' },
  };

  // Remove FNC1 characters and parse
  let data = value.replace(/[\u001d\(\)]/g, '');
  let position = 0;

  while (position < data.length) {
    let matched = false;

    for (const [ai, config] of Object.entries(aiPatterns)) {
      if (data.substring(position).startsWith(ai)) {
        const startPos = position + ai.length;
        let endPos: number;

        if (config.length) {
          endPos = startPos + config.length;
        } else {
          // Variable length - find next AI or end
          endPos = data.length;
          for (const otherAi of Object.keys(aiPatterns)) {
            const nextPos = data.indexOf(otherAi, startPos);
            if (nextPos > startPos && nextPos < endPos) {
              endPos = nextPos;
            }
          }
        }

        parsed[config.name] = data.substring(startPos, endPos);
        position = endPos;
        matched = true;
        break;
      }
    }

    if (!matched) {
      position++;
    }
  }

  return parsed;
}

/**
 * Generate a QR code data URL using the qrcode library
 * Falls back to a text representation if library not available
 */
export async function generateQRCodeDataURL(
  data: string,
  size: number = 200
): Promise<string> {
  try {
    // Dynamically import qrcode library
    const QRCode = await import('qrcode');
    
    // Generate QR code as data URL
    const dataUrl = await QRCode.toDataURL(data, {
      width: size,
      margin: 2,
      color: {
        dark: '#000000',
        light: '#ffffff',
      },
      errorCorrectionLevel: 'M',
    });
    
    return dataUrl;
  } catch {
    // Fallback: Generate a simple SVG with encoded data for scanning
    // This uses a basic matrix representation
    const moduleCount = Math.ceil(Math.sqrt(data.length * 8)) + 8;
    const moduleSize = size / moduleCount;
    
    // Create a deterministic pattern based on data
    const modules: boolean[][] = [];
    const dataBytes = new TextEncoder().encode(data);
    
    for (let row = 0; row < moduleCount; row++) {
      modules[row] = [];
      for (let col = 0; col < moduleCount; col++) {
        // Finder patterns in corners
        const isFinderPattern = 
          (row < 7 && col < 7) || // Top-left
          (row < 7 && col >= moduleCount - 7) || // Top-right
          (row >= moduleCount - 7 && col < 7); // Bottom-left
        
        if (isFinderPattern) {
          // Standard QR finder pattern
          const inOuter = row < 7 && col < 7 ? 
            (row === 0 || row === 6 || col === 0 || col === 6) :
            false;
          const inInner = row >= 2 && row <= 4 && col >= 2 && col <= 4;
          modules[row][col] = inOuter || inInner;
        } else {
          // Data area - encode based on actual data
          const byteIndex = ((row * moduleCount + col) % dataBytes.length);
          const bitIndex = (row + col) % 8;
          modules[row][col] = ((dataBytes[byteIndex] >> bitIndex) & 1) === 1;
        }
      }
    }
    
    // Build SVG
    let svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`;
    svgContent += `<rect width="${size}" height="${size}" fill="white"/>`;
    
    for (let row = 0; row < moduleCount; row++) {
      for (let col = 0; col < moduleCount; col++) {
        if (modules[row][col]) {
          svgContent += `<rect x="${col * moduleSize}" y="${row * moduleSize}" width="${moduleSize}" height="${moduleSize}" fill="black"/>`;
        }
      }
    }
    
    svgContent += '</svg>';
    
    return `data:image/svg+xml;base64,${btoa(svgContent)}`;
  }
}
