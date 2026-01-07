/**
 * PDF Preview Component
 * 
 * Inline PDF preview modal for viewing quote, qualification, and snapshot PDFs.
 * Supports version history, zoom, rotation, and fullscreen mode.
 */

'use client';

import React, { useEffect, useRef, useCallback, useState } from 'react';
import { 
  usePDFPreviewStore, 
  PDFVersion,
  formatFileSize,
  formatVersionLabel,
  getDocumentTypeLabel,
  getDocumentTypeIcon,
  selectSelectedVersion,
  selectCanGoNext,
  selectCanGoPrevious,
  selectCanZoomIn,
  selectCanZoomOut,
  selectZoomPercentage,
  selectPDFUrl,
  ZOOM_LEVELS,
} from '@/stores/pdf-preview-store';
import { cn } from '@/lib/utils';

// =============================================================================
// Icons
// =============================================================================

const Icons = {
  x: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  chevronLeft: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
    </svg>
  ),
  chevronRight: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
  zoomIn: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
    </svg>
  ),
  zoomOut: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
    </svg>
  ),
  rotateCw: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  download: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
  printer: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
    </svg>
  ),
  maximize: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
    </svg>
  ),
  minimize: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V5m0 4H5m0 0l4-4m6 9v4m0-4h4m0 0l-4 4M5 15l4 4m0-4v4m10-4l-4 4m4-4h-4" />
    </svg>
  ),
  clock: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  fileText: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  sidebar: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
    </svg>
  ),
  info: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  checkCircle: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  lock: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>
  ),
  alertCircle: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  loader: (
    <svg className="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  ),
};

// =============================================================================
// Sub-components
// =============================================================================

interface ToolbarButtonProps {
  onClick: () => void;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
  active?: boolean;
}

function ToolbarButton({ onClick, disabled, title, children, active }: ToolbarButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        'p-2 rounded-lg transition-colors duration-150',
        'hover:bg-muted focus:outline-none focus:ring-2 focus:ring-primary/50',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        active && 'bg-primary/10 text-primary'
      )}
    >
      {children}
    </button>
  );
}

interface VersionItemProps {
  version: PDFVersion;
  isSelected: boolean;
  onSelect: () => void;
}

function VersionItem({ version, isSelected, onSelect }: VersionItemProps) {
  const date = new Date(version.createdAt);
  
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'w-full text-left p-3 rounded-lg transition-colors duration-150',
        'hover:bg-muted focus:outline-none focus:ring-2 focus:ring-primary/50',
        isSelected && 'bg-primary/10 border-l-2 border-primary'
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium text-sm">
          {formatVersionLabel(version)}
        </span>
        {version.isImmutable && (
          <span className="text-primary" title="Immutable version">
            {Icons.lock}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
        {Icons.clock}
        <span>{date.toLocaleDateString()} {date.toLocaleTimeString()}</span>
      </div>
      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
        <span>by {version.createdBy}</span>
        {version.fileSize && (
          <>
            <span>•</span>
            <span>{formatFileSize(version.fileSize)}</span>
          </>
        )}
      </div>
      {isSelected && (
        <div className="flex items-center gap-1 mt-2 text-xs text-primary">
          {Icons.checkCircle}
          <span>Currently viewing</span>
        </div>
      )}
    </button>
  );
}

interface ZoomSelectorProps {
  zoom: number;
  onZoomChange: (zoom: number) => void;
}

function ZoomSelector({ zoom, onZoomChange }: ZoomSelectorProps) {
  return (
    <select
      value={zoom}
      onChange={(e) => onZoomChange(parseFloat(e.target.value))}
      className={cn(
        'px-2 py-1 rounded-lg bg-muted text-sm',
        'focus:outline-none focus:ring-2 focus:ring-primary/50'
      )}
    >
      {ZOOM_LEVELS.map((level) => (
        <option key={level} value={level}>
          {Math.round(level * 100)}%
        </option>
      ))}
    </select>
  );
}

// =============================================================================
// Loading State
// =============================================================================

interface LoadingOverlayProps {
  progress: number;
}

function LoadingOverlay({ progress }: LoadingOverlayProps) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm z-10">
      {Icons.loader}
      <div className="mt-4 text-sm text-muted-foreground">Loading PDF...</div>
      {progress > 0 && (
        <div className="mt-2 w-48">
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-1 text-xs text-center text-muted-foreground">
            {Math.round(progress)}%
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Error State
// =============================================================================

interface ErrorOverlayProps {
  error: string;
  onRetry?: () => void;
}

function ErrorOverlay({ error, onRetry }: ErrorOverlayProps) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-background z-10">
      <div className="text-destructive">
        {Icons.alertCircle}
      </div>
      <div className="mt-4 text-sm text-muted-foreground">{error}</div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

// =============================================================================
// PDF Viewer (iframe-based)
// =============================================================================

interface PDFViewerProps {
  url: string;
  zoom: number;
  rotation: number;
  onLoad: () => void;
  onError: (error: string) => void;
}

function PDFViewer({ url, zoom, rotation, onLoad, onError }: PDFViewerProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  
  // Build URL with viewer parameters
  const viewerUrl = `${url}#zoom=${Math.round(zoom * 100)}&view=FitH`;
  
  return (
    <div 
      className="w-full h-full overflow-hidden"
      style={{
        transform: `rotate(${rotation}deg) scale(${rotation % 180 !== 0 ? zoom * 0.7 : zoom})`,
        transformOrigin: 'center center',
      }}
    >
      <iframe
        ref={iframeRef}
        src={viewerUrl}
        className="w-full h-full border-0"
        title="PDF Preview"
        onLoad={onLoad}
        onError={() => onError('Failed to load PDF')}
      />
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export interface PDFPreviewProps {
  className?: string;
  onDownload?: (url: string, filename: string) => void;
  onPrint?: (url: string) => void;
}

export function PDFPreview({ className, onDownload, onPrint }: PDFPreviewProps) {
  const {
    isOpen,
    document,
    selectedVersionId,
    status,
    error,
    loadingProgress,
    currentPage,
    totalPages,
    zoom,
    rotation,
    fitMode,
    showSidebar,
    showVersionHistory,
    showMetadata,
    isFullscreen,
    isDownloading,
    isPrinting,
    close,
    selectVersion,
    setStatus,
    nextPage,
    previousPage,
    goToPage,
    setZoom,
    zoomIn,
    zoomOut,
    rotateClockwise,
    setFitMode,
    toggleSidebar,
    toggleVersionHistory,
    toggleMetadata,
    toggleFullscreen,
    setIsDownloading,
    setIsPrinting,
  } = usePDFPreviewStore();
  
  const containerRef = useRef<HTMLDivElement>(null);
  const [pageInput, setPageInput] = useState('');
  
  // Get current state
  const state = usePDFPreviewStore.getState();
  const selectedVersion = selectSelectedVersion(state);
  const canGoNext = selectCanGoNext(state);
  const canGoPrevious = selectCanGoPrevious(state);
  const canZoomIn = selectCanZoomIn(state);
  const canZoomOut = selectCanZoomOut(state);
  const zoomPercentage = selectZoomPercentage(state);
  const pdfUrl = selectPDFUrl(state);
  
  // Update page input when page changes
  useEffect(() => {
    setPageInput(currentPage.toString());
  }, [currentPage]);
  
  // Handle keyboard shortcuts
  useEffect(() => {
    if (!isOpen) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip if in input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      
      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          if (isFullscreen) {
            toggleFullscreen();
          } else {
            close();
          }
          break;
        case 'ArrowLeft':
        case 'PageUp':
          e.preventDefault();
          previousPage();
          break;
        case 'ArrowRight':
        case 'PageDown':
        case ' ':
          e.preventDefault();
          nextPage();
          break;
        case '+':
        case '=':
          if (e.metaKey || e.ctrlKey) {
            e.preventDefault();
            zoomIn();
          }
          break;
        case '-':
          if (e.metaKey || e.ctrlKey) {
            e.preventDefault();
            zoomOut();
          }
          break;
        case '0':
          if (e.metaKey || e.ctrlKey) {
            e.preventDefault();
            setFitMode('page');
          }
          break;
        case 'f':
          if (e.metaKey || e.ctrlKey) {
            e.preventDefault();
            toggleFullscreen();
          }
          break;
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isFullscreen, close, previousPage, nextPage, zoomIn, zoomOut, setFitMode, toggleFullscreen]);
  
  // Handle fullscreen
  useEffect(() => {
    if (!containerRef.current) return;
    
    if (isFullscreen && !document.fullscreenElement) {
      containerRef.current.requestFullscreen?.().catch(() => {
        // Fullscreen not supported, ignore
      });
    } else if (!isFullscreen && document.fullscreenElement) {
      document.exitFullscreen?.().catch(() => {
        // Ignore
      });
    }
  }, [isFullscreen]);
  
  // Handle page input
  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPageInput(e.target.value);
  };
  
  const handlePageInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const page = parseInt(pageInput, 10);
    if (!isNaN(page) && page >= 1 && page <= totalPages) {
      goToPage(page);
    } else {
      setPageInput(currentPage.toString());
    }
  };
  
  // Handle download
  const handleDownload = useCallback(async () => {
    if (!document || !pdfUrl) return;
    
    setIsDownloading(true);
    try {
      if (onDownload) {
        onDownload(pdfUrl, `${document.title}.pdf`);
      } else {
        // Default download behavior
        const a = document.createElement('a');
        a.href = pdfUrl;
        a.download = `${document.title}.pdf`;
        a.click();
      }
    } finally {
      setIsDownloading(false);
    }
  }, [document, pdfUrl, onDownload, setIsDownloading]);
  
  // Handle print
  const handlePrint = useCallback(async () => {
    if (!pdfUrl) return;
    
    setIsPrinting(true);
    try {
      if (onPrint) {
        onPrint(pdfUrl);
      } else {
        // Default print behavior - open in new window and print
        const printWindow = window.open(pdfUrl, '_blank');
        printWindow?.print();
      }
    } finally {
      setIsPrinting(false);
    }
  }, [pdfUrl, onPrint, setIsPrinting]);
  
  // Handle PDF load
  const handlePDFLoad = useCallback(() => {
    setStatus('ready');
  }, [setStatus]);
  
  // Handle PDF error
  const handlePDFError = useCallback((errorMsg: string) => {
    setStatus('error', errorMsg);
  }, [setStatus]);
  
  if (!isOpen || !document) {
    return null;
  }
  
  return (
    <div
      ref={containerRef}
      className={cn(
        'fixed inset-0 z-50 flex flex-col bg-background',
        isFullscreen && 'bg-black',
        className
      )}
      role="dialog"
      aria-modal="true"
      aria-label="PDF Preview"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-background">
        <div className="flex items-center gap-3">
          <span className="text-primary">{Icons.fileText}</span>
          <div>
            <h2 className="font-semibold text-lg">{document.title}</h2>
            <p className="text-sm text-muted-foreground">
              {getDocumentTypeLabel(document.type)}
              {selectedVersion && ` • ${formatVersionLabel(selectedVersion)}`}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <ToolbarButton
            onClick={toggleVersionHistory}
            title="Version History"
            active={showVersionHistory}
          >
            {Icons.clock}
          </ToolbarButton>
          <ToolbarButton
            onClick={toggleMetadata}
            title="Metadata"
            active={showMetadata}
          >
            {Icons.info}
          </ToolbarButton>
          <div className="w-px h-6 bg-border mx-2" />
          <ToolbarButton
            onClick={close}
            title="Close (Escape)"
          >
            {Icons.x}
          </ToolbarButton>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Version History Sidebar */}
        {showVersionHistory && (
          <div className="w-72 border-r border-border bg-muted/30 overflow-y-auto">
            <div className="p-4">
              <h3 className="font-semibold mb-3">Version History</h3>
              <div className="space-y-2">
                {document.versions.map((version) => (
                  <VersionItem
                    key={version.id}
                    version={version}
                    isSelected={version.id === selectedVersionId}
                    onSelect={() => selectVersion(version.id)}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        
        {/* PDF Viewer */}
        <div className="flex-1 flex flex-col relative">
          {/* Toolbar */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/30">
            {/* Navigation */}
            <div className="flex items-center gap-2">
              <ToolbarButton
                onClick={previousPage}
                disabled={!canGoPrevious}
                title="Previous Page (Left Arrow)"
              >
                {Icons.chevronLeft}
              </ToolbarButton>
              
              <form onSubmit={handlePageInputSubmit} className="flex items-center gap-1">
                <input
                  type="text"
                  value={pageInput}
                  onChange={handlePageInputChange}
                  className="w-12 px-2 py-1 text-center text-sm bg-background border border-border rounded"
                  aria-label="Current page"
                />
                <span className="text-sm text-muted-foreground">
                  of {totalPages || '?'}
                </span>
              </form>
              
              <ToolbarButton
                onClick={nextPage}
                disabled={!canGoNext}
                title="Next Page (Right Arrow)"
              >
                {Icons.chevronRight}
              </ToolbarButton>
            </div>
            
            {/* Zoom Controls */}
            <div className="flex items-center gap-2">
              <ToolbarButton
                onClick={zoomOut}
                disabled={!canZoomOut}
                title="Zoom Out (Cmd+-)"
              >
                {Icons.zoomOut}
              </ToolbarButton>
              
              <ZoomSelector zoom={zoom} onZoomChange={setZoom} />
              
              <ToolbarButton
                onClick={zoomIn}
                disabled={!canZoomIn}
                title="Zoom In (Cmd++)"
              >
                {Icons.zoomIn}
              </ToolbarButton>
              
              <div className="w-px h-6 bg-border mx-2" />
              
              <ToolbarButton
                onClick={rotateClockwise}
                title="Rotate"
              >
                {Icons.rotateCw}
              </ToolbarButton>
              
              <ToolbarButton
                onClick={toggleFullscreen}
                title="Fullscreen (Cmd+F)"
              >
                {isFullscreen ? Icons.minimize : Icons.maximize}
              </ToolbarButton>
            </div>
            
            {/* Actions */}
            <div className="flex items-center gap-2">
              <ToolbarButton
                onClick={handleDownload}
                disabled={isDownloading}
                title="Download"
              >
                {Icons.download}
              </ToolbarButton>
              
              <ToolbarButton
                onClick={handlePrint}
                disabled={isPrinting}
                title="Print"
              >
                {Icons.printer}
              </ToolbarButton>
            </div>
          </div>
          
          {/* PDF Content */}
          <div className="flex-1 relative overflow-auto bg-muted/50">
            {status === 'loading' && (
              <LoadingOverlay progress={loadingProgress} />
            )}
            
            {status === 'error' && error && (
              <ErrorOverlay 
                error={error} 
                onRetry={() => selectedVersion && selectVersion(selectedVersion.id)}
              />
            )}
            
            {pdfUrl && (
              <PDFViewer
                url={pdfUrl}
                zoom={fitMode === 'actual' ? zoom : 1}
                rotation={rotation}
                onLoad={handlePDFLoad}
                onError={handlePDFError}
              />
            )}
          </div>
        </div>
        
        {/* Metadata Sidebar */}
        {showMetadata && (
          <div className="w-72 border-l border-border bg-muted/30 overflow-y-auto">
            <div className="p-4">
              <h3 className="font-semibold mb-3">Document Info</h3>
              
              <div className="space-y-4">
                <div>
                  <dt className="text-xs text-muted-foreground uppercase tracking-wider">Title</dt>
                  <dd className="mt-1 text-sm">{document.title}</dd>
                </div>
                
                <div>
                  <dt className="text-xs text-muted-foreground uppercase tracking-wider">Type</dt>
                  <dd className="mt-1 text-sm">{getDocumentTypeLabel(document.type)}</dd>
                </div>
                
                {document.description && (
                  <div>
                    <dt className="text-xs text-muted-foreground uppercase tracking-wider">Description</dt>
                    <dd className="mt-1 text-sm">{document.description}</dd>
                  </div>
                )}
                
                <div>
                  <dt className="text-xs text-muted-foreground uppercase tracking-wider">Entity</dt>
                  <dd className="mt-1 text-sm">
                    {document.entityType}: {document.entityId}
                  </dd>
                </div>
                
                {selectedVersion && (
                  <>
                    <div className="border-t border-border pt-4 mt-4">
                      <h4 className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
                        Current Version
                      </h4>
                      
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Version</span>
                          <span>{formatVersionLabel(selectedVersion)}</span>
                        </div>
                        
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Created</span>
                          <span>{new Date(selectedVersion.createdAt).toLocaleDateString()}</span>
                        </div>
                        
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Created By</span>
                          <span>{selectedVersion.createdBy}</span>
                        </div>
                        
                        {selectedVersion.fileSize && (
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Size</span>
                            <span>{formatFileSize(selectedVersion.fileSize)}</span>
                          </div>
                        )}
                        
                        {selectedVersion.pageCount && (
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Pages</span>
                            <span>{selectedVersion.pageCount}</span>
                          </div>
                        )}
                        
                        {selectedVersion.isImmutable && (
                          <div className="flex items-center gap-2 text-sm text-primary mt-2">
                            {Icons.lock}
                            <span>Immutable version</span>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {selectedVersion.hash && (
                      <div>
                        <dt className="text-xs text-muted-foreground uppercase tracking-wider">Hash</dt>
                        <dd className="mt-1 text-xs font-mono break-all">{selectedVersion.hash}</dd>
                      </div>
                    )}
                  </>
                )}
                
                {document.metadata && Object.keys(document.metadata).length > 0 && (
                  <div className="border-t border-border pt-4 mt-4">
                    <h4 className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
                      Metadata
                    </h4>
                    <div className="space-y-2">
                      {Object.entries(document.metadata).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-sm">
                          <span className="text-muted-foreground capitalize">{key}</span>
                          <span>{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-2 border-t border-border bg-background text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>
            Page {currentPage} of {totalPages || '?'}
          </span>
          <span>•</span>
          <span>{zoomPercentage}%</span>
          {rotation !== 0 && (
            <>
              <span>•</span>
              <span>Rotated {rotation}°</span>
            </>
          )}
        </div>
        
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-muted rounded border border-border">←</kbd>
            <kbd className="px-1.5 py-0.5 bg-muted rounded border border-border">→</kbd>
            <span className="ml-1">Navigate</span>
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-muted rounded border border-border">Esc</kbd>
            <span className="ml-1">Close</span>
          </span>
        </div>
      </div>
    </div>
  );
}

export default PDFPreview;
