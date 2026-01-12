/**
 * Tests for Printing, Labeling & Export UX Components
 * 
 * Section 19.9: Printing, Labeling & Export UX
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  // Constants
  EXPORT_FORMAT,
  EXPORT_STATE,
  LABEL_SIZE,
  DOCUMENT_TYPE,
  // Utilities
  generateFilename,
  parseFilename,
  // Print Context
  PrintProvider,
  usePrint,
  PrintableDocument,
  PrintButton,
  // Export
  ExportProgressIndicator,
  ExportButton,
  // Labels
  LabelPreview,
  LabelPrinterDialog,
  // Table
  PrintableTable,
  // Hook
  useExport,
  // Types
  ExportProgress,
  LabelConfig,
} from '../print-export';

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('Print Export Constants', () => {
  describe('EXPORT_FORMAT', () => {
    it('should define all export formats', () => {
      expect(EXPORT_FORMAT.PDF).toBe('pdf');
      expect(EXPORT_FORMAT.EXCEL).toBe('excel');
      expect(EXPORT_FORMAT.CSV).toBe('csv');
      expect(EXPORT_FORMAT.PRINT).toBe('print');
      expect(EXPORT_FORMAT.LABEL).toBe('label');
    });
  });

  describe('EXPORT_STATE', () => {
    it('should define all export states', () => {
      expect(EXPORT_STATE.IDLE).toBe('idle');
      expect(EXPORT_STATE.PREPARING).toBe('preparing');
      expect(EXPORT_STATE.GENERATING).toBe('generating');
      expect(EXPORT_STATE.DOWNLOADING).toBe('downloading');
      expect(EXPORT_STATE.COMPLETE).toBe('complete');
      expect(EXPORT_STATE.ERROR).toBe('error');
    });
  });

  describe('LABEL_SIZE', () => {
    it('should define label sizes with dimensions', () => {
      expect(LABEL_SIZE['4x6']).toEqual({ width: 4, height: 6, unit: 'in' });
      expect(LABEL_SIZE['4x4']).toEqual({ width: 4, height: 4, unit: 'in' });
      expect(LABEL_SIZE['3x2']).toEqual({ width: 3, height: 2, unit: 'in' });
      expect(LABEL_SIZE['2x1']).toEqual({ width: 2, height: 1, unit: 'in' });
      expect(LABEL_SIZE['1.5x1']).toEqual({ width: 1.5, height: 1, unit: 'in' });
    });
  });

  describe('DOCUMENT_TYPE', () => {
    it('should define document types', () => {
      expect(DOCUMENT_TYPE.RFQ).toBe('RFQ');
      expect(DOCUMENT_TYPE.QUOTE).toBe('Quote');
      expect(DOCUMENT_TYPE.WORK_ORDER).toBe('WorkOrder');
      expect(DOCUMENT_TYPE.INSPECTION).toBe('Inspection');
      expect(DOCUMENT_TYPE.NC_REPORT).toBe('NCR');
      expect(DOCUMENT_TYPE.CAPA).toBe('CAPA');
      expect(DOCUMENT_TYPE.PART_LABEL).toBe('PartLabel');
      expect(DOCUMENT_TYPE.SHIPPING_LABEL).toBe('ShipLabel');
    });
  });
});

// =============================================================================
// FILENAME UTILITIES TESTS
// =============================================================================

describe('Filename Utilities', () => {
  describe('generateFilename', () => {
    it('should generate consistent filename format', () => {
      const date = new Date('2025-01-15');
      const filename = generateFilename({
        documentType: DOCUMENT_TYPE.RFQ,
        documentId: 'RFQ-001',
        date,
        extension: 'pdf',
      });

      expect(filename).toBe('RFQ_RFQ-001_20250115.pdf');
    });

    it('should use current date if not provided', () => {
      const filename = generateFilename({
        documentType: DOCUMENT_TYPE.QUOTE,
        documentId: 'Q-123',
        extension: 'xlsx',
      });

      const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      expect(filename).toContain(today);
      expect(filename).toMatch(/Quote_Q-123_\d{8}\.xlsx/);
    });

    it('should sanitize document ID', () => {
      const filename = generateFilename({
        documentType: DOCUMENT_TYPE.WORK_ORDER,
        documentId: 'WO/123#special',
        date: new Date('2025-01-15'),
        extension: 'pdf',
      });

      expect(filename).toBe('WorkOrder_WO_123_special_20250115.pdf');
    });
  });

  describe('parseFilename', () => {
    it('should parse valid filename', () => {
      const result = parseFilename('RFQ_RFQ-001_20250115.pdf');

      expect(result).toEqual({
        documentType: 'RFQ',
        documentId: 'RFQ-001',
        date: '20250115',
        extension: 'pdf',
      });
    });

    it('should handle non-matching filename', () => {
      const result = parseFilename('random-file.pdf');

      expect(result).toEqual({
        documentType: null,
        documentId: null,
        date: null,
        extension: 'pdf',
      });
    });

    it('should extract extension from any filename', () => {
      const result = parseFilename('document.xlsx');

      expect(result.extension).toBe('xlsx');
    });
  });
});

// =============================================================================
// PRINT PROVIDER TESTS
// =============================================================================

describe('PrintProvider', () => {
  function PrintTester() {
    const { isPrinting, startPrint } = usePrint();
    return (
      <div>
        <span data-testid="printing">{isPrinting.toString()}</span>
        <button onClick={startPrint}>Print</button>
      </div>
    );
  }

  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should provide isPrinting state', () => {
    render(
      <PrintProvider>
        <PrintTester />
      </PrintProvider>
    );

    expect(screen.getByTestId('printing')).toHaveTextContent('false');
  });

  it('should set isPrinting to true when startPrint is called', async () => {
    // Mock window.print
    const printSpy = jest.spyOn(window, 'print').mockImplementation(() => {});

    render(
      <PrintProvider>
        <PrintTester />
      </PrintProvider>
    );

    fireEvent.click(screen.getByText('Print'));
    expect(screen.getByTestId('printing')).toHaveTextContent('true');

    printSpy.mockRestore();
  });

  it('should throw error when usePrint is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<PrintTester />);
    }).toThrow('usePrint must be used within PrintProvider');

    consoleError.mockRestore();
  });
});

// =============================================================================
// PRINTABLE DOCUMENT TESTS
// =============================================================================

describe('PrintableDocument', () => {
  it('should render children', () => {
    render(
      <PrintProvider>
        <PrintableDocument>
          <p>Document content</p>
        </PrintableDocument>
      </PrintProvider>
    );

    expect(screen.getByText('Document content')).toBeInTheDocument();
  });

  it('should apply title as data attribute', () => {
    render(
      <PrintProvider>
        <PrintableDocument title="Test Document">
          <p>Content</p>
        </PrintableDocument>
      </PrintProvider>
    );

    expect(document.querySelector('[data-title="Test Document"]')).toBeInTheDocument();
  });

  it('should apply black-white class when forceBlackWhite is true', () => {
    render(
      <PrintProvider>
        <PrintableDocument forceBlackWhite>
          <p>Content</p>
        </PrintableDocument>
      </PrintProvider>
    );

    expect(document.querySelector('.print-bw')).toBeInTheDocument();
  });

  it('should include print styles', () => {
    render(
      <PrintProvider>
        <PrintableDocument>
          <p>Content</p>
        </PrintableDocument>
      </PrintProvider>
    );

    expect(document.querySelector('style')).toBeInTheDocument();
  });
});

// =============================================================================
// PRINT BUTTON TESTS
// =============================================================================

describe('PrintButton', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.spyOn(window, 'print').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should render with default label', () => {
    render(
      <PrintProvider>
        <PrintButton />
      </PrintProvider>
    );

    expect(screen.getByRole('button', { name: /print/i })).toBeInTheDocument();
  });

  it('should render with custom label', () => {
    render(
      <PrintProvider>
        <PrintButton label="Print Document" />
      </PrintProvider>
    );

    expect(screen.getByText('Print Document')).toBeInTheDocument();
  });

  it('should have no-print class', () => {
    render(
      <PrintProvider>
        <PrintButton />
      </PrintProvider>
    );

    expect(screen.getByRole('button')).toHaveClass('no-print');
  });

  it('should apply variant classes', () => {
    render(
      <PrintProvider>
        <PrintButton variant="primary" />
      </PrintProvider>
    );

    expect(screen.getByRole('button')).toHaveClass('bg-blue-600');
  });

  it('should apply size classes', () => {
    render(
      <PrintProvider>
        <PrintButton size="lg" />
      </PrintProvider>
    );

    expect(screen.getByRole('button')).toHaveClass('text-lg');
  });
});

// =============================================================================
// EXPORT PROGRESS INDICATOR TESTS
// =============================================================================

describe('ExportProgressIndicator', () => {
  it('should not render when idle', () => {
    const progress: ExportProgress = {
      state: EXPORT_STATE.IDLE,
      progress: 0,
      message: '',
    };

    render(<ExportProgressIndicator progress={progress} />);

    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('should not render when complete', () => {
    const progress: ExportProgress = {
      state: EXPORT_STATE.COMPLETE,
      progress: 100,
      message: 'Done',
    };

    render(<ExportProgressIndicator progress={progress} />);

    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('should render when preparing', () => {
    const progress: ExportProgress = {
      state: EXPORT_STATE.PREPARING,
      progress: 10,
      message: 'Preparing document...',
    };

    render(<ExportProgressIndicator progress={progress} />);

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Preparing document...')).toBeInTheDocument();
  });

  it('should render progress bar', () => {
    const progress: ExportProgress = {
      state: EXPORT_STATE.GENERATING,
      progress: 50,
      message: 'Generating...',
    };

    render(<ExportProgressIndicator progress={progress} />);

    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50');
  });

  it('should display filename', () => {
    const progress: ExportProgress = {
      state: EXPORT_STATE.DOWNLOADING,
      progress: 90,
      message: 'Downloading...',
      filename: 'RFQ_001_20250115.pdf',
    };

    render(<ExportProgressIndicator progress={progress} />);

    expect(screen.getByText('RFQ_001_20250115.pdf')).toBeInTheDocument();
  });

  it('should display error message', () => {
    const progress: ExportProgress = {
      state: EXPORT_STATE.ERROR,
      progress: 0,
      message: 'Export failed',
      error: 'Network timeout',
    };

    render(<ExportProgressIndicator progress={progress} />);

    expect(screen.getByText('Network timeout')).toBeInTheDocument();
  });

  it('should call onCancel when close button clicked', async () => {
    const onCancel = jest.fn();
    const user = userEvent.setup();
    const progress: ExportProgress = {
      state: EXPORT_STATE.GENERATING,
      progress: 50,
      message: 'Generating...',
    };

    render(<ExportProgressIndicator progress={progress} onCancel={onCancel} />);

    await act(async () => {
      await user.click(screen.getByLabelText('Cancel export'));
    });
    expect(onCancel).toHaveBeenCalled();
  });
});

// =============================================================================
// EXPORT BUTTON TESTS
// =============================================================================

describe('ExportButton', () => {
  it('should render export button', () => {
    render(
      <ExportButton
        documentType={DOCUMENT_TYPE.RFQ}
        documentId="RFQ-001"
        onExport={async () => {}}
      />
    );

    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
  });

  it('should open dropdown on click', async () => {
    const user = userEvent.setup();

    render(
      <ExportButton
        documentType={DOCUMENT_TYPE.RFQ}
        documentId="RFQ-001"
        onExport={async () => {}}
      />
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /export/i }));
    });

    expect(screen.getByRole('menu')).toBeInTheDocument();
  });

  it('should show format options in dropdown', async () => {
    const user = userEvent.setup();

    render(
      <ExportButton
        documentType={DOCUMENT_TYPE.RFQ}
        documentId="RFQ-001"
        formats={[EXPORT_FORMAT.PDF, EXPORT_FORMAT.EXCEL]}
        onExport={async () => {}}
      />
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /export/i }));
    });

    expect(screen.getByRole('menuitem', { name: /pdf/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /excel/i })).toBeInTheDocument();
  });

  it('should call onExport when format is selected', async () => {
    const onExport = jest.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(
      <ExportButton
        documentType={DOCUMENT_TYPE.RFQ}
        documentId="RFQ-001"
        formats={[EXPORT_FORMAT.PDF]}
        onExport={onExport}
      />
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /export/i }));
    });
    await act(async () => {
      await user.click(screen.getByRole('menuitem', { name: /pdf/i }));
    });

    await waitFor(() => {
      expect(onExport).toHaveBeenCalledWith(EXPORT_FORMAT.PDF);
    });
  });

  it('should have aria-expanded attribute', async () => {
    const user = userEvent.setup();

    render(
      <ExportButton
        documentType={DOCUMENT_TYPE.RFQ}
        documentId="RFQ-001"
        onExport={async () => {}}
      />
    );

    const button = screen.getByRole('button', { name: /export/i });
    expect(button).toHaveAttribute('aria-expanded', 'false');

    await act(async () => {
      await user.click(button);
    });
    expect(button).toHaveAttribute('aria-expanded', 'true');
  });

  it('should have no-print class', () => {
    render(
      <ExportButton
        documentType={DOCUMENT_TYPE.RFQ}
        documentId="RFQ-001"
        onExport={async () => {}}
      />
    );

    expect(document.querySelector('.no-print')).toBeInTheDocument();
  });
});

// =============================================================================
// LABEL PREVIEW TESTS
// =============================================================================

describe('LabelPreview', () => {
  const baseConfig: LabelConfig = {
    size: '4x6',
    quantity: 1,
    fields: [
      { key: 'part', label: 'Part', value: 'WIDGET-001' },
      { key: 'qty', label: 'Qty', value: '100' },
    ],
  };

  it('should render with correct dimensions', () => {
    render(<LabelPreview config={baseConfig} />);

    const preview = screen.getByRole('img');
    expect(preview).toHaveStyle({ width: '384px', height: '576px' }); // 4*96, 6*96
  });

  it('should display fields', () => {
    render(<LabelPreview config={baseConfig} />);

    expect(screen.getByText('Part:')).toBeInTheDocument();
    expect(screen.getByText('WIDGET-001')).toBeInTheDocument();
    expect(screen.getByText('Qty:')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('should display barcode when provided', () => {
    const configWithBarcode: LabelConfig = {
      ...baseConfig,
      barcode: '123456789',
      barcodeType: 'CODE128',
    };

    render(<LabelPreview config={configWithBarcode} />);

    expect(screen.getByLabelText('Barcode: 123456789')).toBeInTheDocument();
  });

  it('should display QR icon for QR barcodes', () => {
    const configWithQR: LabelConfig = {
      ...baseConfig,
      barcode: 'QR123',
      barcodeType: 'QR',
    };

    render(<LabelPreview config={configWithQR} />);

    expect(screen.getByText('▦')).toBeInTheDocument();
  });

  it('should have accessible label', () => {
    render(<LabelPreview config={{ ...baseConfig, size: '3x2' }} />);

    expect(screen.getByRole('img')).toHaveAttribute('aria-label', 'Label preview 3x2');
  });
});

// =============================================================================
// LABEL PRINTER DIALOG TESTS
// =============================================================================

describe('LabelPrinterDialog', () => {
  it('should not render when closed', () => {
    render(
      <LabelPrinterDialog
        isOpen={false}
        onClose={() => {}}
        onPrint={async () => {}}
      />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should render when open', () => {
    render(
      <LabelPrinterDialog
        isOpen
        onClose={() => {}}
        onPrint={async () => {}}
      />
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Print Labels')).toBeInTheDocument();
  });

  it('should have label size selector', () => {
    render(
      <LabelPrinterDialog
        isOpen
        onClose={() => {}}
        onPrint={async () => {}}
      />
    );

    expect(screen.getByLabelText('Label Size')).toBeInTheDocument();
  });

  it('should have quantity input', () => {
    render(
      <LabelPrinterDialog
        isOpen
        onClose={() => {}}
        onPrint={async () => {}}
      />
    );

    expect(screen.getByLabelText('Quantity')).toBeInTheDocument();
  });

  it('should have barcode input', () => {
    render(
      <LabelPrinterDialog
        isOpen
        onClose={() => {}}
        onPrint={async () => {}}
      />
    );

    expect(screen.getByLabelText('Barcode Value')).toBeInTheDocument();
  });

  it('should have barcode type selector', () => {
    render(
      <LabelPrinterDialog
        isOpen
        onClose={() => {}}
        onPrint={async () => {}}
      />
    );

    expect(screen.getByLabelText('Barcode Type')).toBeInTheDocument();
  });

  it('should have preview section', () => {
    render(
      <LabelPrinterDialog
        isOpen
        onClose={() => {}}
        onPrint={async () => {}}
      />
    );

    expect(screen.getByText('Preview')).toBeInTheDocument();
  });

  it('should call onClose when close button clicked', async () => {
    const onClose = jest.fn();
    const user = userEvent.setup();

    render(
      <LabelPrinterDialog
        isOpen
        onClose={onClose}
        onPrint={async () => {}}
      />
    );

    await act(async () => {
      await user.click(screen.getByLabelText('Close'));
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('should call onClose when cancel button clicked', async () => {
    const onClose = jest.fn();
    const user = userEvent.setup();

    render(
      <LabelPrinterDialog
        isOpen
        onClose={onClose}
        onPrint={async () => {}}
      />
    );

    await act(async () => {
      await user.click(screen.getByText('Cancel'));
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('should call onPrint when print button clicked', async () => {
    const onPrint = jest.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(
      <LabelPrinterDialog
        isOpen
        onClose={() => {}}
        onPrint={onPrint}
      />
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /print 1 label/i }));
    });

    await waitFor(() => {
      expect(onPrint).toHaveBeenCalled();
    });
  });

  it('should update print button text with quantity', async () => {
    render(
      <LabelPrinterDialog
        isOpen
        onClose={() => {}}
        onPrint={async () => {}}
      />
    );

    const quantityInput = screen.getByLabelText('Quantity') as HTMLInputElement;
    // Change quantity by setting value directly then triggering change
    fireEvent.change(quantityInput, { target: { value: '5' } });

    expect(screen.getByRole('button', { name: /print 5 labels/i })).toBeInTheDocument();
  });
});

// =============================================================================
// PRINTABLE TABLE TESTS
// =============================================================================

describe('PrintableTable', () => {
  it('should render table with children', () => {
    render(
      <PrintableTable>
        <thead>
          <tr>
            <th>Header</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Data</td>
          </tr>
        </tbody>
      </PrintableTable>
    );

    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('Header')).toBeInTheDocument();
    expect(screen.getByText('Data')).toBeInTheDocument();
  });

  it('should render caption when provided', () => {
    render(
      <PrintableTable caption="Sales Report">
        <tbody>
          <tr>
            <td>Data</td>
          </tr>
        </tbody>
      </PrintableTable>
    );

    expect(screen.getByText('Sales Report')).toBeInTheDocument();
  });

  it('should have printable-table class', () => {
    render(
      <PrintableTable>
        <tbody>
          <tr>
            <td>Data</td>
          </tr>
        </tbody>
      </PrintableTable>
    );

    expect(screen.getByRole('table')).toHaveClass('printable-table');
  });

  it('should include print styles', () => {
    render(
      <PrintableTable>
        <tbody>
          <tr>
            <td>Data</td>
          </tr>
        </tbody>
      </PrintableTable>
    );

    expect(document.querySelector('style')).toBeInTheDocument();
  });
});

// =============================================================================
// USE EXPORT HOOK TESTS
// =============================================================================

describe('useExport', () => {
  function ExportHookTester() {
    const { progress, exportDocument, reset } = useExport();
    return (
      <div>
        <span data-testid="state">{progress.state}</span>
        <span data-testid="progress">{progress.progress}</span>
        <span data-testid="message">{progress.message}</span>
        <button
          onClick={() =>
            exportDocument(
              {
                format: EXPORT_FORMAT.PDF,
                documentType: DOCUMENT_TYPE.RFQ,
                documentId: 'RFQ-001',
              },
              async () => new Blob(['test'], { type: 'application/pdf' })
            )
          }
        >
          Export
        </button>
        <button onClick={reset}>Reset</button>
      </div>
    );
  }

  beforeEach(() => {
    // Mock URL.createObjectURL and URL.revokeObjectURL
    global.URL.createObjectURL = jest.fn(() => 'blob:test');
    global.URL.revokeObjectURL = jest.fn();
  });

  it('should start with idle state', () => {
    render(<ExportHookTester />);

    expect(screen.getByTestId('state')).toHaveTextContent('idle');
    expect(screen.getByTestId('progress')).toHaveTextContent('0');
  });

  it('should update progress during export', async () => {
    const user = userEvent.setup();

    render(<ExportHookTester />);

    await act(async () => {
      await user.click(screen.getByText('Export'));
    });

    // Should eventually complete
    await waitFor(() => {
      expect(screen.getByTestId('state')).toHaveTextContent('complete');
    });
  });

  it('should reset to idle state', async () => {
    const user = userEvent.setup();

    render(<ExportHookTester />);

    await act(async () => {
      await user.click(screen.getByText('Export'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('state')).not.toHaveTextContent('idle');
    });

    await act(async () => {
      await user.click(screen.getByText('Reset'));
    });

    expect(screen.getByTestId('state')).toHaveTextContent('idle');
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Print Export Integration', () => {
  it('should work with print provider and button', () => {
    render(
      <PrintProvider>
        <PrintableDocument title="Test Document">
          <p>Content here</p>
        </PrintableDocument>
        <PrintButton />
      </PrintProvider>
    );

    expect(screen.getByText('Content here')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /print/i })).toBeInTheDocument();
  });

  it('should show export flow', async () => {
    const user = userEvent.setup();

    render(
      <ExportButton
        documentType={DOCUMENT_TYPE.QUOTE}
        documentId="Q-123"
        formats={[EXPORT_FORMAT.PDF]}
        onExport={async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
        }}
      />
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /export/i }));
    });

    await act(async () => {
      await user.click(screen.getByRole('menuitem', { name: /pdf/i }));
    });

    // Should show progress indicator
    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });
});
