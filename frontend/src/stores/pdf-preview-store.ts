/**
 * PDF Preview Store
 * 
 * State management for the inline PDF preview modal.
 * Handles loading, display, navigation, and version tracking.
 */

import { create } from 'zustand';

// =============================================================================
// Types
// =============================================================================

export type PDFDocumentType =
  | 'quote'
  | 'qualification_report'
  | 'today_snapshot'
  | 'obeya_snapshot'
  | 'week_in_review'
  | '8d_report'
  | 'rfq_summary'
  | 'a3_report'
  | 'training_certificate';

export type PDFStatus = 'idle' | 'loading' | 'ready' | 'error';

export interface PDFVersion {
  id: string;
  versionNumber: number;
  createdAt: string;
  createdBy: string;
  label?: string; // e.g., "Rev A", "Final", "Draft 2"
  isImmutable: boolean;
  fileSize?: number; // bytes
  pageCount?: number;
  hash?: string; // SHA-256 hash for integrity
}

export interface PDFDocument {
  id: string;
  type: PDFDocumentType;
  title: string;
  description?: string;
  entityId: string; // ID of the related entity (quote, rfq, etc.)
  entityType: string; // Type of the related entity
  currentVersion: PDFVersion;
  versions: PDFVersion[];
  url: string; // URL to fetch the PDF
  thumbnailUrl?: string;
  metadata?: Record<string, unknown>;
}

export interface PDFPreviewState {
  // Display state
  isOpen: boolean;
  document: PDFDocument | null;
  selectedVersionId: string | null;
  
  // Loading state
  status: PDFStatus;
  error: string | null;
  loadingProgress: number;
  
  // View state
  currentPage: number;
  totalPages: number;
  zoom: number;
  rotation: number;
  fitMode: 'page' | 'width' | 'height' | 'actual';
  
  // UI state
  showSidebar: boolean;
  showVersionHistory: boolean;
  showMetadata: boolean;
  isFullscreen: boolean;
  
  // Download/print state
  isDownloading: boolean;
  isPrinting: boolean;
  
  // Actions
  open: (document: PDFDocument, versionId?: string) => void;
  close: () => void;
  selectVersion: (versionId: string) => void;
  setStatus: (status: PDFStatus, error?: string) => void;
  setLoadingProgress: (progress: number) => void;
  setCurrentPage: (page: number) => void;
  setTotalPages: (pages: number) => void;
  nextPage: () => void;
  previousPage: () => void;
  goToPage: (page: number) => void;
  setZoom: (zoom: number) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  setRotation: (rotation: number) => void;
  rotateClockwise: () => void;
  rotateCounterClockwise: () => void;
  setFitMode: (mode: PDFPreviewState['fitMode']) => void;
  toggleSidebar: () => void;
  toggleVersionHistory: () => void;
  toggleMetadata: () => void;
  toggleFullscreen: () => void;
  setIsDownloading: (downloading: boolean) => void;
  setIsPrinting: (printing: boolean) => void;
  reset: () => void;
}

// =============================================================================
// Constants
// =============================================================================

export const ZOOM_LEVELS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0];
export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 4.0;
export const DEFAULT_ZOOM = 1.0;
export const ZOOM_STEP = 0.25;

// =============================================================================
// Store
// =============================================================================

const initialState = {
  isOpen: false,
  document: null,
  selectedVersionId: null,
  status: 'idle' as PDFStatus,
  error: null,
  loadingProgress: 0,
  currentPage: 1,
  totalPages: 0,
  zoom: DEFAULT_ZOOM,
  rotation: 0,
  fitMode: 'page' as PDFPreviewState['fitMode'],
  showSidebar: false,
  showVersionHistory: false,
  showMetadata: false,
  isFullscreen: false,
  isDownloading: false,
  isPrinting: false,
};

export const usePDFPreviewStore = create<PDFPreviewState>((set, get) => ({
  ...initialState,
  
  open: (document: PDFDocument, versionId?: string) => {
    const version = versionId 
      ? document.versions.find(v => v.id === versionId)
      : document.currentVersion;
    
    set({
      isOpen: true,
      document,
      selectedVersionId: version?.id || document.currentVersion.id,
      status: 'loading',
      error: null,
      loadingProgress: 0,
      currentPage: 1,
      totalPages: version?.pageCount || 0,
      zoom: DEFAULT_ZOOM,
      rotation: 0,
      fitMode: 'page',
    });
  },
  
  close: () => {
    set({
      isOpen: false,
      status: 'idle',
      error: null,
      loadingProgress: 0,
    });
  },
  
  selectVersion: (versionId: string) => {
    const { document } = get();
    if (!document) return;
    
    const version = document.versions.find(v => v.id === versionId);
    if (!version) return;
    
    set({
      selectedVersionId: versionId,
      status: 'loading',
      error: null,
      loadingProgress: 0,
      currentPage: 1,
      totalPages: version.pageCount || 0,
    });
  },
  
  setStatus: (status: PDFStatus, error?: string) => {
    set({ status, error: error || null });
  },
  
  setLoadingProgress: (progress: number) => {
    set({ loadingProgress: Math.max(0, Math.min(100, progress)) });
  },
  
  setCurrentPage: (page: number) => {
    const { totalPages } = get();
    set({ currentPage: Math.max(1, Math.min(page, totalPages || 1)) });
  },
  
  setTotalPages: (pages: number) => {
    set({ totalPages: pages });
  },
  
  nextPage: () => {
    const { currentPage, totalPages } = get();
    if (currentPage < totalPages) {
      set({ currentPage: currentPage + 1 });
    }
  },
  
  previousPage: () => {
    const { currentPage } = get();
    if (currentPage > 1) {
      set({ currentPage: currentPage - 1 });
    }
  },
  
  goToPage: (page: number) => {
    const { totalPages } = get();
    set({ currentPage: Math.max(1, Math.min(page, totalPages || 1)) });
  },
  
  setZoom: (zoom: number) => {
    set({ 
      zoom: Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom)),
      fitMode: 'actual', // Exit fit mode when manually zooming
    });
  },
  
  zoomIn: () => {
    const { zoom } = get();
    const nextLevel = ZOOM_LEVELS.find(l => l > zoom) || MAX_ZOOM;
    set({ 
      zoom: nextLevel,
      fitMode: 'actual',
    });
  },
  
  zoomOut: () => {
    const { zoom } = get();
    const prevLevels = ZOOM_LEVELS.filter(l => l < zoom);
    const prevLevel = prevLevels[prevLevels.length - 1] || MIN_ZOOM;
    set({ 
      zoom: prevLevel,
      fitMode: 'actual',
    });
  },
  
  setRotation: (rotation: number) => {
    set({ rotation: rotation % 360 });
  },
  
  rotateClockwise: () => {
    const { rotation } = get();
    set({ rotation: (rotation + 90) % 360 });
  },
  
  rotateCounterClockwise: () => {
    const { rotation } = get();
    set({ rotation: (rotation - 90 + 360) % 360 });
  },
  
  setFitMode: (mode: PDFPreviewState['fitMode']) => {
    set({ fitMode: mode });
    // Zoom will be adjusted by the component based on container size
  },
  
  toggleSidebar: () => {
    set(state => ({ showSidebar: !state.showSidebar }));
  },
  
  toggleVersionHistory: () => {
    set(state => ({ showVersionHistory: !state.showVersionHistory }));
  },
  
  toggleMetadata: () => {
    set(state => ({ showMetadata: !state.showMetadata }));
  },
  
  toggleFullscreen: () => {
    set(state => ({ isFullscreen: !state.isFullscreen }));
  },
  
  setIsDownloading: (downloading: boolean) => {
    set({ isDownloading: downloading });
  },
  
  setIsPrinting: (printing: boolean) => {
    set({ isPrinting: printing });
  },
  
  reset: () => {
    set(initialState);
  },
}));

// =============================================================================
// Selectors
// =============================================================================

export const selectSelectedVersion = (state: PDFPreviewState): PDFVersion | null => {
  if (!state.document || !state.selectedVersionId) return null;
  return state.document.versions.find(v => v.id === state.selectedVersionId) || null;
};

export const selectVersionCount = (state: PDFPreviewState): number => {
  return state.document?.versions.length || 0;
};

export const selectCanGoNext = (state: PDFPreviewState): boolean => {
  return state.currentPage < state.totalPages;
};

export const selectCanGoPrevious = (state: PDFPreviewState): boolean => {
  return state.currentPage > 1;
};

export const selectCanZoomIn = (state: PDFPreviewState): boolean => {
  return state.zoom < MAX_ZOOM;
};

export const selectCanZoomOut = (state: PDFPreviewState): boolean => {
  return state.zoom > MIN_ZOOM;
};

export const selectZoomPercentage = (state: PDFPreviewState): number => {
  return Math.round(state.zoom * 100);
};

export const selectPDFUrl = (state: PDFPreviewState): string | null => {
  if (!state.document) return null;
  
  const version = selectSelectedVersion(state);
  if (!version) return state.document.url;
  
  // Append version ID to URL if needed
  const baseUrl = state.document.url;
  const separator = baseUrl.includes('?') ? '&' : '?';
  return `${baseUrl}${separator}version=${version.id}`;
};

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Format file size in human-readable format
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

/**
 * Format version label
 */
export function formatVersionLabel(version: PDFVersion): string {
  if (version.label) return version.label;
  return `Version ${version.versionNumber}`;
}

/**
 * Get document type display name
 */
export function getDocumentTypeLabel(type: PDFDocumentType): string {
  const labels: Record<PDFDocumentType, string> = {
    quote: 'Quote',
    qualification_report: 'Qualification Report',
    today_snapshot: 'Today Snapshot',
    obeya_snapshot: 'Obeya Snapshot',
    week_in_review: 'Week in Review',
    '8d_report': '8D Report',
    rfq_summary: 'RFQ Summary',
    a3_report: 'A3 Report',
    training_certificate: 'Training Certificate',
  };
  
  return labels[type] || type;
}

/**
 * Get document type icon name
 */
export function getDocumentTypeIcon(type: PDFDocumentType): string {
  const icons: Record<PDFDocumentType, string> = {
    quote: 'file-text',
    qualification_report: 'check-circle',
    today_snapshot: 'calendar',
    obeya_snapshot: 'layout',
    week_in_review: 'bar-chart',
    '8d_report': 'alert-circle',
    rfq_summary: 'clipboard',
    a3_report: 'file',
    training_certificate: 'award',
  };
  
  return icons[type] || 'file';
}
