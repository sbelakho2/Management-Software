/**
 * Tests for PDF Preview Store
 */

import {
  usePDFPreviewStore,
  PDFDocument,
  PDFVersion,
  formatFileSize,
  formatVersionLabel,
  getDocumentTypeLabel,
  getDocumentTypeIcon,
  selectSelectedVersion,
  selectVersionCount,
  selectCanGoNext,
  selectCanGoPrevious,
  selectCanZoomIn,
  selectCanZoomOut,
  selectZoomPercentage,
  selectPDFUrl,
  ZOOM_LEVELS,
  MIN_ZOOM,
  MAX_ZOOM,
  DEFAULT_ZOOM,
} from '../pdf-preview-store';

// Sample test data
const mockVersion1: PDFVersion = {
  id: 'v1',
  versionNumber: 1,
  createdAt: '2024-01-01T10:00:00Z',
  createdBy: 'John Doe',
  label: 'Draft',
  isImmutable: false,
  fileSize: 1024000,
  pageCount: 5,
};

const mockVersion2: PDFVersion = {
  id: 'v2',
  versionNumber: 2,
  createdAt: '2024-01-02T10:00:00Z',
  createdBy: 'Jane Smith',
  label: 'Final',
  isImmutable: true,
  fileSize: 1536000,
  pageCount: 6,
  hash: 'abc123def456',
};

const mockDocument: PDFDocument = {
  id: 'doc1',
  type: 'quote',
  title: 'Quote #12345',
  description: 'Quote for customer XYZ',
  entityId: 'quote-123',
  entityType: 'Quote',
  currentVersion: mockVersion2,
  versions: [mockVersion1, mockVersion2],
  url: 'https://api.example.com/documents/doc1/pdf',
};

// Reset store before each test
beforeEach(() => {
  usePDFPreviewStore.getState().reset();
});

// =============================================================================
// formatFileSize Tests
// =============================================================================

describe('formatFileSize', () => {
  it('should format bytes', () => {
    expect(formatFileSize(0)).toBe('0 B');
    expect(formatFileSize(500)).toBe('500.0 B');
  });

  it('should format kilobytes', () => {
    expect(formatFileSize(1024)).toBe('1.0 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
    expect(formatFileSize(10240)).toBe('10.0 KB');
  });

  it('should format megabytes', () => {
    expect(formatFileSize(1048576)).toBe('1.0 MB');
    expect(formatFileSize(1572864)).toBe('1.5 MB');
  });

  it('should format gigabytes', () => {
    expect(formatFileSize(1073741824)).toBe('1.0 GB');
  });
});

// =============================================================================
// formatVersionLabel Tests
// =============================================================================

describe('formatVersionLabel', () => {
  it('should use label if provided', () => {
    expect(formatVersionLabel(mockVersion1)).toBe('Draft');
    expect(formatVersionLabel(mockVersion2)).toBe('Final');
  });

  it('should fallback to version number', () => {
    const version: PDFVersion = {
      id: 'v3',
      versionNumber: 3,
      createdAt: '2024-01-03T10:00:00Z',
      createdBy: 'Test User',
      isImmutable: false,
    };
    expect(formatVersionLabel(version)).toBe('Version 3');
  });
});

// =============================================================================
// getDocumentTypeLabel Tests
// =============================================================================

describe('getDocumentTypeLabel', () => {
  it('should return correct label for each type', () => {
    expect(getDocumentTypeLabel('quote')).toBe('Quote');
    expect(getDocumentTypeLabel('qualification_report')).toBe('Qualification Report');
    expect(getDocumentTypeLabel('today_snapshot')).toBe('Today Snapshot');
    expect(getDocumentTypeLabel('obeya_snapshot')).toBe('Obeya Snapshot');
    expect(getDocumentTypeLabel('week_in_review')).toBe('Week in Review');
    expect(getDocumentTypeLabel('8d_report')).toBe('8D Report');
    expect(getDocumentTypeLabel('rfq_summary')).toBe('RFQ Summary');
    expect(getDocumentTypeLabel('a3_report')).toBe('A3 Report');
    expect(getDocumentTypeLabel('training_certificate')).toBe('Training Certificate');
  });
});

// =============================================================================
// getDocumentTypeIcon Tests
// =============================================================================

describe('getDocumentTypeIcon', () => {
  it('should return correct icon for each type', () => {
    expect(getDocumentTypeIcon('quote')).toBe('file-text');
    expect(getDocumentTypeIcon('qualification_report')).toBe('check-circle');
    expect(getDocumentTypeIcon('today_snapshot')).toBe('calendar');
    expect(getDocumentTypeIcon('8d_report')).toBe('alert-circle');
  });
});

// =============================================================================
// usePDFPreviewStore Tests
// =============================================================================

describe('usePDFPreviewStore', () => {
  describe('initial state', () => {
    it('should have correct initial values', () => {
      const state = usePDFPreviewStore.getState();
      expect(state.isOpen).toBe(false);
      expect(state.document).toBeNull();
      expect(state.selectedVersionId).toBeNull();
      expect(state.status).toBe('idle');
      expect(state.error).toBeNull();
      expect(state.currentPage).toBe(1);
      expect(state.totalPages).toBe(0);
      expect(state.zoom).toBe(DEFAULT_ZOOM);
      expect(state.rotation).toBe(0);
      expect(state.isFullscreen).toBe(false);
    });
  });

  describe('open', () => {
    it('should open with document', () => {
      usePDFPreviewStore.getState().open(mockDocument);
      
      const state = usePDFPreviewStore.getState();
      expect(state.isOpen).toBe(true);
      expect(state.document).toEqual(mockDocument);
      expect(state.selectedVersionId).toBe('v2'); // current version
      expect(state.status).toBe('loading');
    });

    it('should open with specific version', () => {
      usePDFPreviewStore.getState().open(mockDocument, 'v1');
      
      const state = usePDFPreviewStore.getState();
      expect(state.selectedVersionId).toBe('v1');
      expect(state.totalPages).toBe(5);
    });

    it('should reset view state on open', () => {
      usePDFPreviewStore.getState().setZoom(2);
      usePDFPreviewStore.getState().setRotation(90);
      usePDFPreviewStore.getState().open(mockDocument);
      
      const state = usePDFPreviewStore.getState();
      expect(state.zoom).toBe(DEFAULT_ZOOM);
      expect(state.rotation).toBe(0);
      expect(state.currentPage).toBe(1);
    });
  });

  describe('close', () => {
    it('should close and reset state', () => {
      usePDFPreviewStore.getState().open(mockDocument);
      usePDFPreviewStore.getState().close();
      
      const state = usePDFPreviewStore.getState();
      expect(state.isOpen).toBe(false);
      expect(state.status).toBe('idle');
      expect(state.error).toBeNull();
    });
  });

  describe('selectVersion', () => {
    it('should select a different version', () => {
      usePDFPreviewStore.getState().open(mockDocument);
      usePDFPreviewStore.getState().selectVersion('v1');
      
      const state = usePDFPreviewStore.getState();
      expect(state.selectedVersionId).toBe('v1');
      expect(state.status).toBe('loading');
      expect(state.totalPages).toBe(5);
    });

    it('should do nothing for invalid version', () => {
      usePDFPreviewStore.getState().open(mockDocument);
      usePDFPreviewStore.getState().selectVersion('invalid');
      
      const state = usePDFPreviewStore.getState();
      expect(state.selectedVersionId).toBe('v2');
    });
  });

  describe('setStatus', () => {
    it('should update status', () => {
      usePDFPreviewStore.getState().setStatus('ready');
      expect(usePDFPreviewStore.getState().status).toBe('ready');
    });

    it('should update status with error', () => {
      usePDFPreviewStore.getState().setStatus('error', 'Failed to load');
      
      const state = usePDFPreviewStore.getState();
      expect(state.status).toBe('error');
      expect(state.error).toBe('Failed to load');
    });
  });

  describe('setLoadingProgress', () => {
    it('should update progress', () => {
      usePDFPreviewStore.getState().setLoadingProgress(50);
      expect(usePDFPreviewStore.getState().loadingProgress).toBe(50);
    });

    it('should clamp progress to 0-100', () => {
      usePDFPreviewStore.getState().setLoadingProgress(-10);
      expect(usePDFPreviewStore.getState().loadingProgress).toBe(0);
      
      usePDFPreviewStore.getState().setLoadingProgress(150);
      expect(usePDFPreviewStore.getState().loadingProgress).toBe(100);
    });
  });

  describe('page navigation', () => {
    beforeEach(() => {
      usePDFPreviewStore.getState().open(mockDocument);
      usePDFPreviewStore.getState().setTotalPages(10);
    });

    it('should go to next page', () => {
      usePDFPreviewStore.getState().nextPage();
      expect(usePDFPreviewStore.getState().currentPage).toBe(2);
    });

    it('should go to previous page', () => {
      usePDFPreviewStore.getState().setCurrentPage(5);
      usePDFPreviewStore.getState().previousPage();
      expect(usePDFPreviewStore.getState().currentPage).toBe(4);
    });

    it('should not go below page 1', () => {
      usePDFPreviewStore.getState().previousPage();
      expect(usePDFPreviewStore.getState().currentPage).toBe(1);
    });

    it('should not go above total pages', () => {
      usePDFPreviewStore.getState().setCurrentPage(10);
      usePDFPreviewStore.getState().nextPage();
      expect(usePDFPreviewStore.getState().currentPage).toBe(10);
    });

    it('should go to specific page', () => {
      usePDFPreviewStore.getState().goToPage(5);
      expect(usePDFPreviewStore.getState().currentPage).toBe(5);
    });

    it('should clamp page to valid range', () => {
      usePDFPreviewStore.getState().goToPage(0);
      expect(usePDFPreviewStore.getState().currentPage).toBe(1);
      
      usePDFPreviewStore.getState().goToPage(100);
      expect(usePDFPreviewStore.getState().currentPage).toBe(10);
    });
  });

  describe('zoom controls', () => {
    it('should set zoom', () => {
      usePDFPreviewStore.getState().setZoom(1.5);
      expect(usePDFPreviewStore.getState().zoom).toBe(1.5);
      expect(usePDFPreviewStore.getState().fitMode).toBe('actual');
    });

    it('should clamp zoom to min/max', () => {
      usePDFPreviewStore.getState().setZoom(0.1);
      expect(usePDFPreviewStore.getState().zoom).toBe(MIN_ZOOM);
      
      usePDFPreviewStore.getState().setZoom(10);
      expect(usePDFPreviewStore.getState().zoom).toBe(MAX_ZOOM);
    });

    it('should zoom in to next level', () => {
      usePDFPreviewStore.getState().setZoom(1.0);
      usePDFPreviewStore.getState().zoomIn();
      expect(usePDFPreviewStore.getState().zoom).toBe(1.25);
    });

    it('should zoom out to previous level', () => {
      usePDFPreviewStore.getState().setZoom(1.0);
      usePDFPreviewStore.getState().zoomOut();
      expect(usePDFPreviewStore.getState().zoom).toBe(0.75);
    });

    it('should not zoom beyond limits', () => {
      usePDFPreviewStore.getState().setZoom(MAX_ZOOM);
      usePDFPreviewStore.getState().zoomIn();
      expect(usePDFPreviewStore.getState().zoom).toBe(MAX_ZOOM);
      
      usePDFPreviewStore.getState().setZoom(MIN_ZOOM);
      usePDFPreviewStore.getState().zoomOut();
      expect(usePDFPreviewStore.getState().zoom).toBe(MIN_ZOOM);
    });
  });

  describe('rotation', () => {
    it('should set rotation', () => {
      usePDFPreviewStore.getState().setRotation(90);
      expect(usePDFPreviewStore.getState().rotation).toBe(90);
    });

    it('should wrap rotation at 360', () => {
      usePDFPreviewStore.getState().setRotation(450);
      expect(usePDFPreviewStore.getState().rotation).toBe(90);
    });

    it('should rotate clockwise', () => {
      usePDFPreviewStore.getState().rotateClockwise();
      expect(usePDFPreviewStore.getState().rotation).toBe(90);
      
      usePDFPreviewStore.getState().rotateClockwise();
      expect(usePDFPreviewStore.getState().rotation).toBe(180);
    });

    it('should rotate counter-clockwise', () => {
      usePDFPreviewStore.getState().rotateCounterClockwise();
      expect(usePDFPreviewStore.getState().rotation).toBe(270);
    });

    it('should wrap rotation correctly', () => {
      usePDFPreviewStore.getState().setRotation(270);
      usePDFPreviewStore.getState().rotateClockwise();
      expect(usePDFPreviewStore.getState().rotation).toBe(0);
    });
  });

  describe('fit mode', () => {
    it('should set fit mode', () => {
      usePDFPreviewStore.getState().setFitMode('width');
      expect(usePDFPreviewStore.getState().fitMode).toBe('width');
    });
  });

  describe('UI toggles', () => {
    it('should toggle sidebar', () => {
      expect(usePDFPreviewStore.getState().showSidebar).toBe(false);
      usePDFPreviewStore.getState().toggleSidebar();
      expect(usePDFPreviewStore.getState().showSidebar).toBe(true);
      usePDFPreviewStore.getState().toggleSidebar();
      expect(usePDFPreviewStore.getState().showSidebar).toBe(false);
    });

    it('should toggle version history', () => {
      expect(usePDFPreviewStore.getState().showVersionHistory).toBe(false);
      usePDFPreviewStore.getState().toggleVersionHistory();
      expect(usePDFPreviewStore.getState().showVersionHistory).toBe(true);
    });

    it('should toggle metadata', () => {
      expect(usePDFPreviewStore.getState().showMetadata).toBe(false);
      usePDFPreviewStore.getState().toggleMetadata();
      expect(usePDFPreviewStore.getState().showMetadata).toBe(true);
    });

    it('should toggle fullscreen', () => {
      expect(usePDFPreviewStore.getState().isFullscreen).toBe(false);
      usePDFPreviewStore.getState().toggleFullscreen();
      expect(usePDFPreviewStore.getState().isFullscreen).toBe(true);
    });
  });

  describe('download/print state', () => {
    it('should set downloading state', () => {
      usePDFPreviewStore.getState().setIsDownloading(true);
      expect(usePDFPreviewStore.getState().isDownloading).toBe(true);
    });

    it('should set printing state', () => {
      usePDFPreviewStore.getState().setIsPrinting(true);
      expect(usePDFPreviewStore.getState().isPrinting).toBe(true);
    });
  });

  describe('reset', () => {
    it('should reset to initial state', () => {
      usePDFPreviewStore.getState().open(mockDocument);
      usePDFPreviewStore.getState().setZoom(2);
      usePDFPreviewStore.getState().setRotation(90);
      usePDFPreviewStore.getState().toggleFullscreen();
      
      usePDFPreviewStore.getState().reset();
      
      const state = usePDFPreviewStore.getState();
      expect(state.isOpen).toBe(false);
      expect(state.document).toBeNull();
      expect(state.zoom).toBe(DEFAULT_ZOOM);
      expect(state.rotation).toBe(0);
      expect(state.isFullscreen).toBe(false);
    });
  });
});

// =============================================================================
// Selectors Tests
// =============================================================================

describe('selectors', () => {
  beforeEach(() => {
    usePDFPreviewStore.getState().open(mockDocument);
  });

  describe('selectSelectedVersion', () => {
    it('should return selected version', () => {
      const state = usePDFPreviewStore.getState();
      const version = selectSelectedVersion(state);
      expect(version).toEqual(mockVersion2);
    });

    it('should return null when no document', () => {
      usePDFPreviewStore.getState().reset();
      const state = usePDFPreviewStore.getState();
      expect(selectSelectedVersion(state)).toBeNull();
    });
  });

  describe('selectVersionCount', () => {
    it('should return version count', () => {
      const state = usePDFPreviewStore.getState();
      expect(selectVersionCount(state)).toBe(2);
    });

    it('should return 0 when no document', () => {
      usePDFPreviewStore.getState().reset();
      const state = usePDFPreviewStore.getState();
      expect(selectVersionCount(state)).toBe(0);
    });
  });

  describe('selectCanGoNext/Previous', () => {
    it('should return correct navigation state', () => {
      usePDFPreviewStore.getState().setTotalPages(10);
      usePDFPreviewStore.getState().setCurrentPage(1);
      
      let state = usePDFPreviewStore.getState();
      expect(selectCanGoPrevious(state)).toBe(false);
      expect(selectCanGoNext(state)).toBe(true);
      
      usePDFPreviewStore.getState().setCurrentPage(5);
      state = usePDFPreviewStore.getState();
      expect(selectCanGoPrevious(state)).toBe(true);
      expect(selectCanGoNext(state)).toBe(true);
      
      usePDFPreviewStore.getState().setCurrentPage(10);
      state = usePDFPreviewStore.getState();
      expect(selectCanGoPrevious(state)).toBe(true);
      expect(selectCanGoNext(state)).toBe(false);
    });
  });

  describe('selectCanZoomIn/Out', () => {
    it('should return correct zoom state', () => {
      usePDFPreviewStore.getState().setZoom(1.0);
      
      let state = usePDFPreviewStore.getState();
      expect(selectCanZoomIn(state)).toBe(true);
      expect(selectCanZoomOut(state)).toBe(true);
      
      usePDFPreviewStore.getState().setZoom(MAX_ZOOM);
      state = usePDFPreviewStore.getState();
      expect(selectCanZoomIn(state)).toBe(false);
      expect(selectCanZoomOut(state)).toBe(true);
      
      usePDFPreviewStore.getState().setZoom(MIN_ZOOM);
      state = usePDFPreviewStore.getState();
      expect(selectCanZoomIn(state)).toBe(true);
      expect(selectCanZoomOut(state)).toBe(false);
    });
  });

  describe('selectZoomPercentage', () => {
    it('should return zoom as percentage', () => {
      usePDFPreviewStore.getState().setZoom(1.5);
      const state = usePDFPreviewStore.getState();
      expect(selectZoomPercentage(state)).toBe(150);
    });
  });

  describe('selectPDFUrl', () => {
    it('should return URL with version', () => {
      const state = usePDFPreviewStore.getState();
      const url = selectPDFUrl(state);
      expect(url).toBe('https://api.example.com/documents/doc1/pdf?version=v2');
    });

    it('should handle URL with existing query params', () => {
      const docWithParams = {
        ...mockDocument,
        url: 'https://api.example.com/documents/doc1/pdf?token=abc',
      };
      usePDFPreviewStore.getState().open(docWithParams);
      
      const state = usePDFPreviewStore.getState();
      const url = selectPDFUrl(state);
      expect(url).toBe('https://api.example.com/documents/doc1/pdf?token=abc&version=v2');
    });

    it('should return null when no document', () => {
      usePDFPreviewStore.getState().reset();
      const state = usePDFPreviewStore.getState();
      expect(selectPDFUrl(state)).toBeNull();
    });
  });
});

// =============================================================================
// Constants Tests
// =============================================================================

describe('constants', () => {
  it('should have correct zoom levels', () => {
    expect(ZOOM_LEVELS).toContain(0.5);
    expect(ZOOM_LEVELS).toContain(1.0);
    expect(ZOOM_LEVELS).toContain(2.0);
    expect(ZOOM_LEVELS[0]).toBe(MIN_ZOOM);
    expect(ZOOM_LEVELS[ZOOM_LEVELS.length - 1]).toBe(MAX_ZOOM);
  });

  it('should have consistent zoom bounds', () => {
    expect(MIN_ZOOM).toBeLessThan(DEFAULT_ZOOM);
    expect(DEFAULT_ZOOM).toBeLessThan(MAX_ZOOM);
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('PDF Preview Store Integration', () => {
  it('should handle complete viewing workflow', () => {
    // Open document
    usePDFPreviewStore.getState().open(mockDocument);
    expect(usePDFPreviewStore.getState().isOpen).toBe(true);
    expect(usePDFPreviewStore.getState().status).toBe('loading');
    
    // Load complete
    usePDFPreviewStore.getState().setTotalPages(10);
    usePDFPreviewStore.getState().setStatus('ready');
    expect(usePDFPreviewStore.getState().status).toBe('ready');
    
    // Navigate
    usePDFPreviewStore.getState().goToPage(5);
    expect(usePDFPreviewStore.getState().currentPage).toBe(5);
    
    // Zoom
    usePDFPreviewStore.getState().zoomIn();
    usePDFPreviewStore.getState().zoomIn();
    expect(usePDFPreviewStore.getState().zoom).toBe(1.5);
    
    // Rotate
    usePDFPreviewStore.getState().rotateClockwise();
    expect(usePDFPreviewStore.getState().rotation).toBe(90);
    
    // Switch version
    usePDFPreviewStore.getState().selectVersion('v1');
    expect(usePDFPreviewStore.getState().selectedVersionId).toBe('v1');
    expect(usePDFPreviewStore.getState().currentPage).toBe(1); // Reset on version change
    
    // Close
    usePDFPreviewStore.getState().close();
    expect(usePDFPreviewStore.getState().isOpen).toBe(false);
  });

  it('should handle error recovery', () => {
    usePDFPreviewStore.getState().open(mockDocument);
    usePDFPreviewStore.getState().setStatus('error', 'Network error');
    
    expect(usePDFPreviewStore.getState().status).toBe('error');
    expect(usePDFPreviewStore.getState().error).toBe('Network error');
    
    // Retry by re-selecting version
    usePDFPreviewStore.getState().selectVersion('v2');
    expect(usePDFPreviewStore.getState().status).toBe('loading');
    expect(usePDFPreviewStore.getState().error).toBeNull();
  });

  it('should preserve document while navigating versions', () => {
    usePDFPreviewStore.getState().open(mockDocument);
    
    usePDFPreviewStore.getState().selectVersion('v1');
    expect(usePDFPreviewStore.getState().document).toEqual(mockDocument);
    
    usePDFPreviewStore.getState().selectVersion('v2');
    expect(usePDFPreviewStore.getState().document).toEqual(mockDocument);
  });
});
