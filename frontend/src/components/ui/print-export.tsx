/**
 * Printing, Labeling & Export UX Components
 * 
 * Section 19.9: Printing, Labeling & Export UX
 * 
 * Provides components for:
 * - Print stylesheets and optimized print layouts
 * - Document export with progress indicators
 * - Label printing for thermal printers
 * - Consistent filename conventions
 */

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
  ReactNode,
} from 'react';

// =============================================================================
// CONSTANTS
// =============================================================================

/**
 * Export formats supported
 */
export const EXPORT_FORMAT = {
  PDF: 'pdf',
  EXCEL: 'excel',
  CSV: 'csv',
  PRINT: 'print',
  LABEL: 'label',
} as const;

export type ExportFormatType = (typeof EXPORT_FORMAT)[keyof typeof EXPORT_FORMAT];

/**
 * Export states
 */
export const EXPORT_STATE = {
  IDLE: 'idle',
  PREPARING: 'preparing',
  GENERATING: 'generating',
  DOWNLOADING: 'downloading',
  COMPLETE: 'complete',
  ERROR: 'error',
} as const;

export type ExportState = (typeof EXPORT_STATE)[keyof typeof EXPORT_STATE];

/**
 * Label sizes for thermal printing
 */
export const LABEL_SIZE = {
  '4x6': { width: 4, height: 6, unit: 'in' },
  '4x4': { width: 4, height: 4, unit: 'in' },
  '3x2': { width: 3, height: 2, unit: 'in' },
  '2x1': { width: 2, height: 1, unit: 'in' },
  '1.5x1': { width: 1.5, height: 1, unit: 'in' },
} as const;

export type LabelSizeKey = keyof typeof LABEL_SIZE;

/**
 * Document types for naming conventions
 */
export const DOCUMENT_TYPE = {
  RFQ: 'RFQ',
  QUOTE: 'Quote',
  WORK_ORDER: 'WorkOrder',
  INSPECTION: 'Inspection',
  NC_REPORT: 'NCR',
  CAPA: 'CAPA',
  PART_LABEL: 'PartLabel',
  SHIPPING_LABEL: 'ShipLabel',
} as const;

export type DocumentType = (typeof DOCUMENT_TYPE)[keyof typeof DOCUMENT_TYPE];

// =============================================================================
// TYPES
// =============================================================================

export interface ExportConfig {
  format: ExportFormatType;
  documentType: DocumentType;
  documentId: string;
  title?: string;
  includeMetadata?: boolean;
  highContrast?: boolean;
}

export interface ExportProgress {
  state: ExportState;
  progress: number;
  message: string;
  filename?: string;
  error?: string;
}

export interface LabelConfig {
  size: LabelSizeKey;
  quantity: number;
  barcode?: string;
  barcodeType?: 'CODE128' | 'QR' | 'DATAMATRIX';
  fields: LabelField[];
}

export interface LabelField {
  key: string;
  label: string;
  value: string;
  bold?: boolean;
  fontSize?: 'sm' | 'md' | 'lg';
}

// =============================================================================
// FILENAME UTILITIES
// =============================================================================

/**
 * Generate consistent filename for exports
 */
export function generateFilename(config: {
  documentType: DocumentType;
  documentId: string;
  date?: Date;
  extension: string;
}): string {
  const date = config.date || new Date();
  const dateStr = date.toISOString().slice(0, 10).replace(/-/g, '');
  const sanitizedId = config.documentId.replace(/[^a-zA-Z0-9-]/g, '_');
  
  return `${config.documentType}_${sanitizedId}_${dateStr}.${config.extension}`;
}

/**
 * Parse filename to extract metadata
 */
export function parseFilename(filename: string): {
  documentType: string | null;
  documentId: string | null;
  date: string | null;
  extension: string;
} {
  const match = filename.match(/^([A-Za-z]+)_([^_]+)_(\d{8})\.(\w+)$/);
  
  if (match) {
    return {
      documentType: match[1],
      documentId: match[2],
      date: match[3],
      extension: match[4],
    };
  }
  
  // Fallback for non-matching filenames
  const ext = filename.split('.').pop() || '';
  return {
    documentType: null,
    documentId: null,
    date: null,
    extension: ext,
  };
}

// =============================================================================
// PRINT CONTEXT
// =============================================================================

interface PrintContextValue {
  isPrinting: boolean;
  startPrint: () => void;
  cancelPrint: () => void;
}

const PrintContext = createContext<PrintContextValue | null>(null);

export interface PrintProviderProps {
  children: ReactNode;
}

/**
 * Provider for print state management
 */
export function PrintProvider({ children }: PrintProviderProps) {
  const [isPrinting, setIsPrinting] = useState(false);

  const startPrint = useCallback(() => {
    setIsPrinting(true);
    // Small delay to allow print styles to apply
    setTimeout(() => {
      window.print();
      setIsPrinting(false);
    }, 100);
  }, []);

  const cancelPrint = useCallback(() => {
    setIsPrinting(false);
  }, []);

  // Listen for beforeprint and afterprint events
  useEffect(() => {
    const handleBeforePrint = () => setIsPrinting(true);
    const handleAfterPrint = () => setIsPrinting(false);

    window.addEventListener('beforeprint', handleBeforePrint);
    window.addEventListener('afterprint', handleAfterPrint);

    return () => {
      window.removeEventListener('beforeprint', handleBeforePrint);
      window.removeEventListener('afterprint', handleAfterPrint);
    };
  }, []);

  const value: PrintContextValue = {
    isPrinting,
    startPrint,
    cancelPrint,
  };

  return (
    <PrintContext.Provider value={value}>{children}</PrintContext.Provider>
  );
}

/**
 * Hook to access print context
 */
export function usePrint(): PrintContextValue {
  const context = useContext(PrintContext);
  if (!context) {
    throw new Error('usePrint must be used within PrintProvider');
  }
  return context;
}

// =============================================================================
// PRINT-FRIENDLY WRAPPER
// =============================================================================

export interface PrintableDocumentProps {
  children: ReactNode;
  title?: string;
  showHeader?: boolean;
  showFooter?: boolean;
  pageBreaks?: boolean;
  forceBlackWhite?: boolean;
  className?: string;
}

/**
 * Wrapper for print-optimized document rendering
 */
export function PrintableDocument({
  children,
  title,
  showHeader = true,
  showFooter = true,
  pageBreaks = true,
  forceBlackWhite = false,
  className = '',
}: PrintableDocumentProps) {
  return (
    <div
      className={`
        printable-document
        ${forceBlackWhite ? 'print-bw' : ''}
        ${className}
      `}
      data-title={title}
    >
      {/* Print-only styles */}
      <style>{`
        @media print {
          .printable-document {
            background: white !important;
            color: black !important;
          }
          
          .printable-document.print-bw * {
            color: black !important;
            background: white !important;
            border-color: black !important;
          }
          
          .no-print {
            display: none !important;
          }
          
          .print-only {
            display: block !important;
          }
          
          /* Hide navigation and sidebars */
          nav, aside, header:not(.print-header), footer:not(.print-footer) {
            display: none !important;
          }
          
          /* Page break handling */
          ${pageBreaks ? `
            .page-break {
              page-break-before: always;
            }
            .avoid-break {
              page-break-inside: avoid;
            }
            tr {
              page-break-inside: avoid;
            }
            thead {
              display: table-header-group;
            }
          ` : ''}
          
          /* Print margins */
          @page {
            margin: 0.75in;
          }
        }
        
        @media screen {
          .print-only {
            display: none !important;
          }
        }
      `}</style>
      
      {showHeader && (
        <header className="print-header hidden print:block mb-4 pb-2 border-b border-gray-300">
          <div className="flex justify-between items-center">
            <h1 className="text-xl font-bold">{title || 'Document'}</h1>
            <span className="text-sm text-gray-500">
              Printed: {new Date().toLocaleDateString()}
            </span>
          </div>
        </header>
      )}
      
      <main className="printable-content">
        {children}
      </main>
      
      {showFooter && (
        <footer className="print-footer hidden print:block mt-4 pt-2 border-t border-gray-300 text-center text-sm text-gray-500">
          Page <span className="page-number" /> of <span className="page-count" />
        </footer>
      )}
    </div>
  );
}

// =============================================================================
// PRINT BUTTON
// =============================================================================

export interface PrintButtonProps {
  label?: string;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

/**
 * Print trigger button
 */
export function PrintButton({
  label = 'Print',
  variant = 'secondary',
  size = 'md',
  className = '',
}: PrintButtonProps) {
  const { isPrinting, startPrint } = usePrint();

  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300',
    ghost: 'text-gray-600 hover:text-gray-900 hover:bg-gray-100',
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2',
    lg: 'px-5 py-2.5 text-lg',
  };

  return (
    <button
      type="button"
      onClick={startPrint}
      disabled={isPrinting}
      className={`
        inline-flex items-center gap-2 rounded-lg transition-colors
        no-print
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${isPrinting ? 'opacity-50 cursor-not-allowed' : ''}
        ${className}
      `}
      aria-label={isPrinting ? 'Printing...' : label}
    >
      <span aria-hidden="true">🖨️</span>
      <span>{isPrinting ? 'Printing...' : label}</span>
    </button>
  );
}

// =============================================================================
// EXPORT PROGRESS INDICATOR
// =============================================================================

export interface ExportProgressIndicatorProps {
  progress: ExportProgress;
  onCancel?: () => void;
  className?: string;
}

/**
 * Progress indicator for document exports
 */
export function ExportProgressIndicator({
  progress,
  onCancel,
  className = '',
}: ExportProgressIndicatorProps) {
  if (progress.state === EXPORT_STATE.IDLE || progress.state === EXPORT_STATE.COMPLETE) {
    return null;
  }

  const stateIcons = {
    [EXPORT_STATE.PREPARING]: '📋',
    [EXPORT_STATE.GENERATING]: '⚙️',
    [EXPORT_STATE.DOWNLOADING]: '📥',
    [EXPORT_STATE.ERROR]: '❌',
    [EXPORT_STATE.IDLE]: '',
    [EXPORT_STATE.COMPLETE]: '✅',
  };

  return (
    <div
      className={`
        fixed bottom-4 right-4 bg-white rounded-lg shadow-xl border border-gray-200
        p-4 min-w-[300px] z-50
        ${className}
      `}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3 mb-3">
        <span className="text-xl" aria-hidden="true">
          {stateIcons[progress.state]}
        </span>
        <div className="flex-1">
          <p className="font-medium text-gray-900">{progress.message}</p>
          {progress.filename && (
            <p className="text-sm text-gray-500 truncate">{progress.filename}</p>
          )}
        </div>
        {onCancel && progress.state !== EXPORT_STATE.ERROR && (
          <button
            type="button"
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Cancel export"
          >
            ✕
          </button>
        )}
      </div>

      {progress.state !== EXPORT_STATE.ERROR && (
        <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="absolute inset-y-0 left-0 bg-blue-600 rounded-full transition-all duration-300"
            style={{ width: `${progress.progress}%` }}
            role="progressbar"
            aria-valuenow={progress.progress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      )}

      {progress.state === EXPORT_STATE.ERROR && progress.error && (
        <p className="text-sm text-red-600 mt-2">{progress.error}</p>
      )}
    </div>
  );
}

// =============================================================================
// EXPORT BUTTON WITH FORMATS
// =============================================================================

export interface ExportButtonProps {
  documentType: DocumentType;
  documentId: string;
  title?: string;
  formats?: ExportFormatType[];
  onExport: (format: ExportFormatType) => Promise<void>;
  className?: string;
}

/**
 * Export button with format dropdown
 */
export function ExportButton({
  documentType,
  documentId,
  title,
  formats = [EXPORT_FORMAT.PDF, EXPORT_FORMAT.EXCEL, EXPORT_FORMAT.CSV],
  onExport,
  className = '',
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [progress, setProgress] = useState<ExportProgress>({
    state: EXPORT_STATE.IDLE,
    progress: 0,
    message: '',
  });

  const formatLabels: Record<ExportFormatType, { label: string; icon: string }> = {
    [EXPORT_FORMAT.PDF]: { label: 'Download as PDF', icon: '📄' },
    [EXPORT_FORMAT.EXCEL]: { label: 'Download as Excel', icon: '📊' },
    [EXPORT_FORMAT.CSV]: { label: 'Download as CSV', icon: '📋' },
    [EXPORT_FORMAT.PRINT]: { label: 'Print', icon: '🖨️' },
    [EXPORT_FORMAT.LABEL]: { label: 'Print Label', icon: '🏷️' },
  };

  const handleExport = async (format: ExportFormatType) => {
    setIsOpen(false);
    
    const filename = generateFilename({
      documentType,
      documentId,
      extension: format === EXPORT_FORMAT.EXCEL ? 'xlsx' : format,
    });

    try {
      setProgress({
        state: EXPORT_STATE.PREPARING,
        progress: 10,
        message: 'Preparing document...',
        filename,
      });

      setProgress({
        state: EXPORT_STATE.GENERATING,
        progress: 50,
        message: `Generating ${format.toUpperCase()}...`,
        filename,
      });

      await onExport(format);

      setProgress({
        state: EXPORT_STATE.DOWNLOADING,
        progress: 90,
        message: 'Downloading...',
        filename,
      });

      // Short delay to show download state
      await new Promise((resolve) => setTimeout(resolve, 500));

      setProgress({
        state: EXPORT_STATE.COMPLETE,
        progress: 100,
        message: 'Download complete',
        filename,
      });

      // Auto-hide after completion
      setTimeout(() => {
        setProgress({ state: EXPORT_STATE.IDLE, progress: 0, message: '' });
      }, 2000);
    } catch (error) {
      setProgress({
        state: EXPORT_STATE.ERROR,
        progress: 0,
        message: 'Export failed',
        filename,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      setTimeout(() => {
        setProgress({ state: EXPORT_STATE.IDLE, progress: 0, message: '' });
      }, 5000);
    }
  };

  return (
    <>
      <div className={`relative no-print ${className}`}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300 rounded-lg"
          aria-expanded={isOpen}
          aria-haspopup="true"
        >
          <span aria-hidden="true">📥</span>
          Export
          <span aria-hidden="true">▾</span>
        </button>

        {isOpen && (
          <div
            className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-[200px]"
            role="menu"
          >
            {formats.map((format) => (
              <button
                key={format}
                type="button"
                onClick={() => handleExport(format)}
                className="flex items-center gap-2 w-full px-4 py-2 text-left hover:bg-gray-100 first:rounded-t-lg last:rounded-b-lg"
                role="menuitem"
              >
                <span aria-hidden="true">{formatLabels[format].icon}</span>
                {formatLabels[format].label}
              </button>
            ))}
          </div>
        )}
      </div>

      <ExportProgressIndicator
        progress={progress}
        onCancel={() => setProgress({ state: EXPORT_STATE.IDLE, progress: 0, message: '' })}
      />
    </>
  );
}

// =============================================================================
// LABEL PREVIEW
// =============================================================================

export interface LabelPreviewProps {
  config: LabelConfig;
  className?: string;
}

/**
 * Preview component for label printing
 */
export function LabelPreview({ config, className = '' }: LabelPreviewProps) {
  const size = LABEL_SIZE[config.size];
  const scale = 96; // 96 DPI for preview

  return (
    <div
      className={`inline-block border-2 border-dashed border-gray-300 bg-white ${className}`}
      style={{
        width: size.width * scale,
        height: size.height * scale,
      }}
      role="img"
      aria-label={`Label preview ${config.size}`}
    >
      <div className="p-2 h-full flex flex-col">
        {/* Barcode area */}
        {config.barcode && (
          <div className="flex-shrink-0 flex justify-center py-2 border-b border-gray-200 mb-2">
            <div
              className="bg-gray-900 text-white text-xs px-2 py-1 font-mono"
              aria-label={`Barcode: ${config.barcode}`}
            >
              {config.barcodeType === 'QR' ? (
                <span className="text-lg">▦</span>
              ) : (
                <span>||||| {config.barcode} |||||</span>
              )}
            </div>
          </div>
        )}

        {/* Label fields */}
        <div className="flex-1 overflow-hidden space-y-1">
          {config.fields.map((field, index) => {
            const fontSizeClass = {
              sm: 'text-xs',
              md: 'text-sm',
              lg: 'text-base',
            }[field.fontSize || 'md'];

            return (
              <div key={index} className={fontSizeClass}>
                {field.label && (
                  <span className="text-gray-500 mr-1">{field.label}:</span>
                )}
                <span className={field.bold ? 'font-bold' : ''}>{field.value}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// LABEL PRINTER DIALOG
// =============================================================================

export interface LabelPrinterDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onPrint: (config: LabelConfig) => Promise<void>;
  initialConfig?: Partial<LabelConfig>;
  className?: string;
}

/**
 * Dialog for configuring and printing labels
 */
export function LabelPrinterDialog({
  isOpen,
  onClose,
  onPrint,
  initialConfig,
  className = '',
}: LabelPrinterDialogProps) {
  const [config, setConfig] = useState<LabelConfig>({
    size: '4x6',
    quantity: 1,
    barcode: '',
    barcodeType: 'CODE128',
    fields: [],
    ...initialConfig,
  });
  const [isPrinting, setIsPrinting] = useState(false);

  if (!isOpen) {
    return null;
  }

  const handlePrint = async () => {
    setIsPrinting(true);
    try {
      await onPrint(config);
      onClose();
    } catch (error) {
      console.error('Label print failed:', error);
    } finally {
      setIsPrinting(false);
    }
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/50 ${className}`}
      role="dialog"
      aria-labelledby="label-dialog-title"
      aria-modal="true"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h2 id="label-dialog-title" className="text-lg font-bold">
            Print Labels
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="p-4 grid grid-cols-2 gap-6">
          {/* Configuration */}
          <div className="space-y-4">
            <div>
              <label htmlFor="label-size" className="block text-sm font-medium text-gray-700 mb-1">
                Label Size
              </label>
              <select
                id="label-size"
                value={config.size}
                onChange={(e) =>
                  setConfig({ ...config, size: e.target.value as LabelSizeKey })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                {Object.keys(LABEL_SIZE).map((size) => (
                  <option key={size} value={size}>
                    {size} inches
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="label-quantity" className="block text-sm font-medium text-gray-700 mb-1">
                Quantity
              </label>
              <input
                id="label-quantity"
                type="number"
                min={1}
                max={100}
                value={config.quantity}
                onChange={(e) =>
                  setConfig({ ...config, quantity: parseInt(e.target.value) || 1 })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>

            <div>
              <label htmlFor="label-barcode" className="block text-sm font-medium text-gray-700 mb-1">
                Barcode Value
              </label>
              <input
                id="label-barcode"
                type="text"
                value={config.barcode || ''}
                onChange={(e) => setConfig({ ...config, barcode: e.target.value })}
                placeholder="Enter barcode value"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>

            <div>
              <label htmlFor="barcode-type" className="block text-sm font-medium text-gray-700 mb-1">
                Barcode Type
              </label>
              <select
                id="barcode-type"
                value={config.barcodeType}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    barcodeType: e.target.value as 'CODE128' | 'QR' | 'DATAMATRIX',
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="CODE128">Code 128</option>
                <option value="QR">QR Code</option>
                <option value="DATAMATRIX">Data Matrix</option>
              </select>
            </div>
          </div>

          {/* Preview */}
          <div className="flex flex-col items-center">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Preview</h3>
            <LabelPreview config={config} />
          </div>
        </div>

        <div className="p-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handlePrint}
            disabled={isPrinting}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isPrinting ? 'Printing...' : `Print ${config.quantity} Label${config.quantity > 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// TABLE PRINT HELPER
// =============================================================================

export interface PrintableTableProps {
  children: ReactNode;
  caption?: string;
  repeatHeader?: boolean;
  className?: string;
}

/**
 * Table wrapper optimized for printing with repeating headers
 */
export function PrintableTable({
  children,
  caption,
  repeatHeader = true,
  className = '',
}: PrintableTableProps) {
  return (
    <>
      <style>{`
        @media print {
          .printable-table thead {
            ${repeatHeader ? 'display: table-header-group;' : ''}
          }
          .printable-table tr {
            page-break-inside: avoid;
          }
          .printable-table {
            border-collapse: collapse;
          }
          .printable-table td,
          .printable-table th {
            border: 1px solid #000 !important;
            padding: 4px 8px;
          }
        }
      `}</style>
      <table className={`printable-table w-full ${className}`}>
        {caption && <caption className="text-left font-bold mb-2">{caption}</caption>}
        {children}
      </table>
    </>
  );
}

// =============================================================================
// USE EXPORT HOOK
// =============================================================================

/**
 * Hook for document export functionality
 */
export function useExport() {
  const [progress, setProgress] = useState<ExportProgress>({
    state: EXPORT_STATE.IDLE,
    progress: 0,
    message: '',
  });

  const exportDocument = useCallback(
    async (
      config: ExportConfig,
      generator: () => Promise<Blob>
    ): Promise<void> => {
      const filename = generateFilename({
        documentType: config.documentType,
        documentId: config.documentId,
        extension: config.format === EXPORT_FORMAT.EXCEL ? 'xlsx' : config.format,
      });

      try {
        setProgress({
          state: EXPORT_STATE.PREPARING,
          progress: 10,
          message: 'Preparing document...',
          filename,
        });

        setProgress({
          state: EXPORT_STATE.GENERATING,
          progress: 40,
          message: `Generating ${config.format.toUpperCase()}...`,
          filename,
        });

        const blob = await generator();

        setProgress({
          state: EXPORT_STATE.DOWNLOADING,
          progress: 80,
          message: 'Downloading...',
          filename,
        });

        // Trigger download
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        setProgress({
          state: EXPORT_STATE.COMPLETE,
          progress: 100,
          message: 'Download complete',
          filename,
        });

        setTimeout(() => {
          setProgress({ state: EXPORT_STATE.IDLE, progress: 0, message: '' });
        }, 2000);
      } catch (error) {
        setProgress({
          state: EXPORT_STATE.ERROR,
          progress: 0,
          message: 'Export failed',
          filename,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },
    []
  );

  const reset = useCallback(() => {
    setProgress({ state: EXPORT_STATE.IDLE, progress: 0, message: '' });
  }, []);

  return {
    progress,
    exportDocument,
    reset,
  };
}

// =============================================================================
// EXPORTS
// =============================================================================
