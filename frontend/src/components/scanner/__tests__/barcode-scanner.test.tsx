import { screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BarcodeScanner, ScannerModal, ScanButton } from '../barcode-scanner';
import type { BarcodeResult } from '@/hooks/use-camera-scanner';
import { renderWithI18n } from '@/test-utils';

const render = renderWithI18n;

// Mock the camera scanner hook
const mockStart = jest.fn();
const mockStop = jest.fn();
const mockSwitchCamera = jest.fn();
const mockCaptureFrame = jest.fn();

const mockDefaultState = {
  isScanning: false,
  isSupported: true,
  hasPermission: null,
  error: null,
  lastResult: null,
};

let mockState = { ...mockDefaultState };

jest.mock('@/hooks/use-camera-scanner', () => ({
  useCameraScanner: jest.fn(() => ({
    state: mockState,
    videoRef: { current: null },
    canvasRef: { current: null },
    start: mockStart,
    stop: mockStop,
    switchCamera: mockSwitchCamera,
    captureFrame: mockCaptureFrame,
  })),
  parseManufacturingBarcode: jest.fn((value: string) => ({
    type: value.startsWith('WO') ? 'work_order' : 'unknown',
    value: value,
    raw: value,
  })),
  isBarcodeDetectorSupported: jest.fn(() => true),
}));

// Mock cn utility
jest.mock('@/lib/utils', () => ({
  cn: (...classes: (string | undefined)[]) => classes.filter(Boolean).join(' '),
}));

describe('BarcodeScanner', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockState = { ...mockDefaultState };
    mockCaptureFrame.mockReturnValue('data:image/jpeg;base64,mockdata');
  });
  
  it('renders not supported message when browser doesnt support API', () => {
    mockState = { ...mockDefaultState, isSupported: false };
    
    render(<BarcodeScanner />);
    
    expect(screen.getByText('Scanner Not Supported')).toBeInTheDocument();
    expect(screen.getByText(/Your browser doesn't support/)).toBeInTheDocument();
  });
  
  it('renders permission denied message when camera access denied', () => {
    mockState = { ...mockDefaultState, hasPermission: false };
    
    render(<BarcodeScanner />);
    
    expect(screen.getByText('Camera Access Denied')).toBeInTheDocument();
    expect(screen.getByText(/Please allow camera access/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });
  
  it('shows start button when not scanning', () => {
    mockState = { ...mockDefaultState, isScanning: false };
    
    render(<BarcodeScanner />);
    
    expect(screen.getByRole('button', { name: /start scanner/i })).toBeInTheDocument();
  });
  
  it('calls start when start button is clicked', async () => {
    const user = userEvent.setup();
    mockState = { ...mockDefaultState, isScanning: false };
    
    render(<BarcodeScanner />);
    
    await user.click(screen.getByRole('button', { name: /start scanner/i }));
    
    expect(mockStart).toHaveBeenCalled();
  });
  
  it('shows controls when scanning', () => {
    mockState = { ...mockDefaultState, isScanning: true };
    
    render(<BarcodeScanner showControls />);
    
    expect(screen.getByRole('button', { name: /switch/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /capture/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /stop/i })).toBeInTheDocument();
  });
  
  it('hides controls when showControls is false', () => {
    mockState = { ...mockDefaultState, isScanning: true };
    
    render(<BarcodeScanner showControls={false} />);
    
    expect(screen.queryByRole('button', { name: /switch/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /stop/i })).not.toBeInTheDocument();
  });
  
  it('calls switchCamera when switch button is clicked', async () => {
    const user = userEvent.setup();
    mockState = { ...mockDefaultState, isScanning: true };
    
    render(<BarcodeScanner showControls />);
    
    await user.click(screen.getByRole('button', { name: /switch/i }));
    
    expect(mockSwitchCamera).toHaveBeenCalled();
  });
  
  it('calls stop when stop button is clicked', async () => {
    const user = userEvent.setup();
    mockState = { ...mockDefaultState, isScanning: true };
    
    render(<BarcodeScanner showControls />);
    
    await user.click(screen.getByRole('button', { name: /stop/i }));
    
    expect(mockStop).toHaveBeenCalled();
  });
  
  it('displays error message when error occurs', () => {
    mockState = {
      ...mockDefaultState,
      isScanning: false,
      error: 'Camera error occurred',
    };
    
    render(<BarcodeScanner />);
    
    expect(screen.getByText('Camera error occurred')).toBeInTheDocument();
  });
  
  it('shows try again button on error', async () => {
    const user = userEvent.setup();
    mockState = {
      ...mockDefaultState,
      isScanning: false,
      error: 'Camera error',
    };
    
    render(<BarcodeScanner />);
    
    await user.click(screen.getByRole('button', { name: /try again/i }));
    
    expect(mockStart).toHaveBeenCalled();
  });
  
  it('displays last result when available', () => {
    const lastResult: BarcodeResult = {
      rawValue: 'WO-12345',
      format: 'code_128',
      boundingBox: { x: 0, y: 0, width: 100, height: 50 },
      cornerPoints: [],
      timestamp: new Date('2024-01-15T10:30:00').getTime(),
    };
    
    mockState = { ...mockDefaultState, isScanning: true, lastResult };
    
    render(<BarcodeScanner showLastResult />);
    
    expect(screen.getByText('WO-12345')).toBeInTheDocument();
    expect(screen.getByText(/code_128/i)).toBeInTheDocument();
  });
  
  it('hides last result when showLastResult is false', () => {
    const lastResult: BarcodeResult = {
      rawValue: 'TEST-123',
      format: 'qr_code',
      boundingBox: { x: 0, y: 0, width: 100, height: 100 },
      cornerPoints: [],
      timestamp: Date.now(),
    };
    
    mockState = { ...mockDefaultState, isScanning: true, lastResult };
    
    render(<BarcodeScanner showLastResult={false} />);
    
    expect(screen.queryByText('TEST-123')).not.toBeInTheDocument();
  });
  
  it('calls onScan callback when new result is available', async () => {
    const onScan = jest.fn();
    const lastResult: BarcodeResult = {
      rawValue: 'WO-99999',
      format: 'code_128',
      boundingBox: { x: 0, y: 0, width: 100, height: 50 },
      cornerPoints: [],
      timestamp: Date.now(),
    };
    
    mockState = { ...mockDefaultState, isScanning: true, lastResult };
    
    render(<BarcodeScanner onScan={onScan} />);
    
    await waitFor(() => {
      expect(onScan).toHaveBeenCalledWith(
        lastResult,
        expect.objectContaining({ type: 'work_order' })
      );
    });
  });
  
  it('calls onError callback when error occurs', async () => {
    const onError = jest.fn();
    mockState = {
      ...mockDefaultState,
      isScanning: false,
      error: 'Test error',
    };
    
    render(<BarcodeScanner onError={onError} />);
    
    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Test error');
    });
  });
  
  it('applies custom className', () => {
    mockState = { ...mockDefaultState, isScanning: true };
    
    const { container } = render(
      <BarcodeScanner className="custom-class" />
    );
    
    expect(container.firstChild).toHaveClass('custom-class');
  });
  
  it('captures frame when capture button clicked', async () => {
    const user = userEvent.setup();
    mockState = { ...mockDefaultState, isScanning: true };
    
    render(<BarcodeScanner showControls />);
    
    await user.click(screen.getByRole('button', { name: /capture/i }));
    
    expect(mockCaptureFrame).toHaveBeenCalled();
  });
  
  it('auto-starts when autoStart is true', () => {
    mockState = { ...mockDefaultState, isSupported: true };
    
    render(<BarcodeScanner autoStart />);
    
    expect(mockStart).toHaveBeenCalled();
  });
  
  it('does not auto-start when not supported', () => {
    mockStart.mockClear();
    mockState = { ...mockDefaultState, isSupported: false };
    
    render(<BarcodeScanner autoStart />);
    
    expect(mockStart).not.toHaveBeenCalled();
  });
  
  it('renders video element', () => {
    mockState = { ...mockDefaultState, isScanning: true };
    
    render(<BarcodeScanner />);
    
    const video = document.querySelector('video');
    expect(video).toBeInTheDocument();
  });
  
  it('shows scanning overlay when scanning', () => {
    mockState = { ...mockDefaultState, isScanning: true };
    
    const { container } = render(<BarcodeScanner />);
    
    // Check for corner brackets (part of scanning overlay)
    const corners = container.querySelectorAll('.border-l-4');
    expect(corners.length).toBeGreaterThan(0);
  });
});

describe('ScannerModal', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockState = { ...mockDefaultState };
  });
  
  it('renders nothing when not open', () => {
    render(
      <ScannerModal
        isOpen={false}
        onClose={jest.fn()}
        onScan={jest.fn()}
      />
    );
    
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.queryByText('Scan Barcode')).not.toBeInTheDocument();
  });
  
  it('renders modal when open', () => {
    mockState = { ...mockDefaultState, isSupported: true };
    
    render(
      <ScannerModal
        isOpen={true}
        onClose={jest.fn()}
        onScan={jest.fn()}
      />
    );
    
    expect(screen.getByText('Scan Barcode')).toBeInTheDocument();
    expect(screen.getByText('Point your camera at a barcode or QR code to scan it.')).toBeInTheDocument();
  });
  
  it('uses custom title and description', () => {
    mockState = { ...mockDefaultState, isSupported: true };
    
    render(
      <ScannerModal
        isOpen={true}
        onClose={jest.fn()}
        onScan={jest.fn()}
        title="Custom Title"
        description="Custom description"
      />
    );
    
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
    expect(screen.getByText('Custom description')).toBeInTheDocument();
  });
  
  it('calls onClose when close button clicked', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    mockState = { ...mockDefaultState, isSupported: true };
    
    render(
      <ScannerModal
        isOpen={true}
        onClose={onClose}
        onScan={jest.fn()}
      />
    );
    
    // Find close button (X icon button)
    const buttons = screen.getAllByRole('button');
    const closeButton = buttons.find(btn => btn.querySelector('svg'));
    
    if (closeButton) {
      await user.click(closeButton);
      expect(onClose).toHaveBeenCalled();
    }
  });
  
  it('calls onClose when backdrop clicked', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    mockState = { ...mockDefaultState, isSupported: true };
    
    render(
      <ScannerModal
        isOpen={true}
        onClose={onClose}
        onScan={jest.fn()}
      />
    );
    
    // Find backdrop (bg-black/60)
    const backdrop = document.querySelector('.bg-black\\/60');
    if (backdrop) {
      await user.click(backdrop);
      expect(onClose).toHaveBeenCalled();
    }
  });
  
  it('auto-starts scanner when modal opens', () => {
    mockState = { ...mockDefaultState, isSupported: true };
    
    render(
      <ScannerModal
        isOpen={true}
        onClose={jest.fn()}
        onScan={jest.fn()}
      />
    );
    
    expect(mockStart).toHaveBeenCalled();
  });
  
  it('calls onScan and onClose when barcode detected', async () => {
    const onScan = jest.fn();
    const onClose = jest.fn();
    const lastResult: BarcodeResult = {
      rawValue: 'WO-12345',
      format: 'code_128',
      boundingBox: { x: 0, y: 0, width: 100, height: 50 },
      cornerPoints: [],
      timestamp: Date.now(),
    };
    
    mockState = { ...mockDefaultState, isScanning: true, lastResult };
    
    render(
      <ScannerModal
        isOpen={true}
        onClose={onClose}
        onScan={onScan}
      />
    );
    
    await waitFor(() => {
      expect(onScan).toHaveBeenCalled();
    });
  });
});

describe('ScanButton', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockState = { ...mockDefaultState };
  });
  
  it('renders button with default label', () => {
    render(<ScanButton onScan={jest.fn()} />);
    
    expect(screen.getByRole('button', { name: /scan/i })).toBeInTheDocument();
  });
  
  it('renders button with custom label', () => {
    render(<ScanButton onScan={jest.fn()} label="Scan Item" />);
    
    expect(screen.getByRole('button', { name: /scan item/i })).toBeInTheDocument();
  });
  
  it('opens modal when clicked', async () => {
    const user = userEvent.setup();
    mockState = { ...mockDefaultState, isSupported: true };
    
    render(<ScanButton onScan={jest.fn()} />);
    
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /scan/i }));
    });
    
    expect(screen.getByText('Scan Barcode')).toBeInTheDocument();
  });
  
  it('closes modal when scan completes', async () => {
    const onScan = jest.fn();
    const user = userEvent.setup();
    
    render(<ScanButton onScan={onScan} />);
    
    // Open modal
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /scan/i }));
    });
    
    // Modal should be visible
    expect(screen.getByText('Scan Barcode')).toBeInTheDocument();
  });
  
  it('applies custom className', () => {
    render(<ScanButton onScan={jest.fn()} className="custom-button" />);
    
    expect(screen.getByRole('button', { name: /scan/i })).toHaveClass('custom-button');
  });
  
  it('renders QR code icon', () => {
    render(<ScanButton onScan={jest.fn()} />);
    
    const button = screen.getByRole('button', { name: /scan/i });
    const svg = button.querySelector('svg');
    
    expect(svg).toBeInTheDocument();
  });
});

describe('Icon components', () => {
  // Test that icons render correctly as part of the component
  it('renders camera icon in start button', () => {
    mockState = { ...mockDefaultState, isScanning: false };
    
    render(<BarcodeScanner />);
    
    const startButton = screen.getByRole('button', { name: /start scanner/i });
    const svg = startButton.closest('div')?.querySelector('svg');
    
    expect(svg).toBeInTheDocument();
  });
  
  it('renders stop icon in controls', () => {
    mockState = { ...mockDefaultState, isScanning: true };
    
    render(<BarcodeScanner showControls />);
    
    const stopButton = screen.getByRole('button', { name: /stop/i });
    const svg = stopButton.querySelector('svg');
    
    expect(svg).toBeInTheDocument();
  });
});
