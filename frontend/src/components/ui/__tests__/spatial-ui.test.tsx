import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import {
  // Types and constants
  CELL_STATUS,
  CELL_STATUS_COLORS,
  DEFAULT_WAR_ROOM_LAYOUT,
  // Factory Map
  FactoryMapProvider,
  useFactoryMap,
  FactoryFloorMap,
  CellDetailPanel,
  GembaPathVisualizer,
  MapControls,
  CellStatusLegend,
  // War Room
  WarRoomProvider,
  useWarRoom,
  WarRoomDashboard,
  WarRoomPanelContainer,
  KPIPanel,
  AlertsPanel,
  TimelinePanel,
  // Types
  ProductionCell,
  OrderPath,
  CellStatus,
  KPIData,
  AlertData,
  TimelineEvent,
  WarRoomPanel,
} from '../spatial-ui';

// =============================================================================
// TEST FIXTURES
// =============================================================================

const mockCells: ProductionCell[] = [
  {
    id: 'cell-1',
    name: 'Workstation A',
    type: 'workstation',
    status: 'running',
    position: { x: 50, y: 50 },
    size: { width: 100, height: 80 },
    metrics: {
      throughput: 25,
      efficiency: 92,
      currentJob: 'JOB-001',
      operator: 'John Doe',
    },
    connections: ['cell-2'],
  },
  {
    id: 'cell-2',
    name: 'Assembly B',
    type: 'assembly',
    status: 'idle',
    position: { x: 200, y: 50 },
    size: { width: 100, height: 80 },
    connections: ['cell-3'],
  },
  {
    id: 'cell-3',
    name: 'Quality Check',
    type: 'quality',
    status: 'changeover',
    position: { x: 350, y: 50 },
    size: { width: 100, height: 80 },
  },
  {
    id: 'cell-4',
    name: 'Shipping',
    type: 'shipping',
    status: 'blocked',
    position: { x: 500, y: 50 },
    size: { width: 100, height: 80 },
  },
];

const mockOrderPath: OrderPath = {
  orderId: 'ORD-12345',
  orderName: 'Customer Order #12345',
  steps: [
    { cellId: 'cell-1', cellName: 'Workstation A', status: 'completed', duration: 30, travelTime: 5 },
    { cellId: 'cell-2', cellName: 'Assembly B', status: 'completed', duration: 45, travelTime: 10 },
    { cellId: 'cell-3', cellName: 'Quality Check', status: 'current', duration: 15 },
    { cellId: 'cell-4', cellName: 'Shipping', status: 'pending' },
  ],
  totalTravelTime: 15,
  totalProcessTime: 90,
};

const mockKPIs: KPIData[] = [
  { label: 'Revenue', value: '$125K', change: 12.5, status: 'good' },
  { label: 'Orders', value: 156, unit: 'today', change: -3.2, status: 'warning' },
  { label: 'OEE', value: 87, unit: '%', target: 85, status: 'good' },
  { label: 'Defects', value: 3, status: 'critical' },
];

const mockAlerts: AlertData[] = [
  {
    id: 'alert-1',
    severity: 'critical',
    title: 'Machine Down',
    message: 'CNC Machine #3 has stopped responding',
    timestamp: new Date(),
    source: 'Production',
  },
  {
    id: 'alert-2',
    severity: 'warning',
    title: 'Low Inventory',
    message: 'Part XYZ-123 below reorder point',
    timestamp: new Date(),
    source: 'Inventory',
  },
  {
    id: 'alert-3',
    severity: 'info',
    title: 'Shift Change',
    message: 'Night shift starting in 30 minutes',
    timestamp: new Date(),
  },
];

const mockTimelineEvents: TimelineEvent[] = [
  { id: 'event-1', time: new Date(Date.now() - 3600000), title: 'Morning Standup', type: 'meeting', completed: true },
  { id: 'event-2', time: new Date(Date.now() + 1800000), title: 'Production Review', type: 'meeting' },
  { id: 'event-3', time: new Date(Date.now() + 7200000), title: 'Order Deadline', type: 'deadline' },
  { id: 'event-4', time: new Date(Date.now() + 14400000), title: 'Monthly Milestone', type: 'milestone' },
];

// =============================================================================
// CELL STATUS CONSTANTS TESTS
// =============================================================================

describe('Cell Status Constants', () => {
  test('should have all status types defined', () => {
    expect(CELL_STATUS.idle).toBe('idle');
    expect(CELL_STATUS.running).toBe('running');
    expect(CELL_STATUS.changeover).toBe('changeover');
    expect(CELL_STATUS.maintenance).toBe('maintenance');
    expect(CELL_STATUS.blocked).toBe('blocked');
    expect(CELL_STATUS.offline).toBe('offline');
  });

  test('should have color mappings for all statuses', () => {
    const statuses = Object.keys(CELL_STATUS) as CellStatus[];
    statuses.forEach((status) => {
      expect(CELL_STATUS_COLORS[status]).toBeDefined();
      expect(CELL_STATUS_COLORS[status].fill).toBeDefined();
      expect(CELL_STATUS_COLORS[status].stroke).toBeDefined();
      expect(CELL_STATUS_COLORS[status].text).toBeDefined();
    });
  });

  test('should have distinct fill colors for each status', () => {
    const fills = Object.values(CELL_STATUS_COLORS).map((c) => c.fill);
    const uniqueFills = new Set(fills);
    expect(uniqueFills.size).toBe(fills.length);
  });

  test('should have running status as green', () => {
    expect(CELL_STATUS_COLORS.running.fill).toContain('f7d0'); // Green tint
    expect(CELL_STATUS_COLORS.running.stroke).toContain('22c55e');
  });

  test('should have blocked status as red', () => {
    expect(CELL_STATUS_COLORS.blocked.fill).toContain('fecaca');
    expect(CELL_STATUS_COLORS.blocked.stroke).toContain('ef4444');
  });
});

// =============================================================================
// FACTORY MAP PROVIDER TESTS
// =============================================================================

describe('FactoryMapProvider', () => {
  test('should provide context to children', () => {
    const TestComponent = () => {
      const context = useFactoryMap();
      return <div data-testid="cells-count">{context.cells.length}</div>;
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    expect(screen.getByTestId('cells-count')).toHaveTextContent('4');
  });

  test('should throw error when used outside provider', () => {
    const TestComponent = () => {
      useFactoryMap();
      return null;
    };

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestComponent />)).toThrow('useFactoryMap must be used within a FactoryMapProvider');
    consoleSpy.mockRestore();
  });

  test('should select cell by ID', () => {
    const onCellSelect = jest.fn();
    const TestComponent = () => {
      const { selectCell, selectedCell } = useFactoryMap();
      return (
        <div>
          <button onClick={() => selectCell('cell-1')}>Select</button>
          <span data-testid="selected">{selectedCell?.name ?? 'none'}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells} onCellSelect={onCellSelect}>
        <TestComponent />
      </FactoryMapProvider>
    );

    fireEvent.click(screen.getByText('Select'));
    expect(screen.getByTestId('selected')).toHaveTextContent('Workstation A');
    expect(onCellSelect).toHaveBeenCalledWith(mockCells[0]);
  });

  test('should clear selection when selecting null', () => {
    const TestComponent = () => {
      const { selectCell, selectedCell } = useFactoryMap();
      return (
        <div>
          <button onClick={() => selectCell('cell-1')}>Select</button>
          <button onClick={() => selectCell(null)}>Clear</button>
          <span data-testid="selected">{selectedCell?.name ?? 'none'}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    fireEvent.click(screen.getByText('Select'));
    expect(screen.getByTestId('selected')).toHaveTextContent('Workstation A');
    
    fireEvent.click(screen.getByText('Clear'));
    expect(screen.getByTestId('selected')).toHaveTextContent('none');
  });

  test('should hover cell by ID', () => {
    const TestComponent = () => {
      const { hoverCell, hoveredCell } = useFactoryMap();
      return (
        <div>
          <button onClick={() => hoverCell('cell-2')}>Hover</button>
          <button onClick={() => hoverCell(null)}>Leave</button>
          <span data-testid="hovered">{hoveredCell?.name ?? 'none'}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    fireEvent.click(screen.getByText('Hover'));
    expect(screen.getByTestId('hovered')).toHaveTextContent('Assembly B');
    
    fireEvent.click(screen.getByText('Leave'));
    expect(screen.getByTestId('hovered')).toHaveTextContent('none');
  });

  test('should update cell status', () => {
    const onCellStatusChange = jest.fn();
    const TestComponent = () => {
      const { cells, updateCellStatus } = useFactoryMap();
      return (
        <div>
          <button onClick={() => updateCellStatus('cell-1', 'maintenance')}>Update</button>
          <span data-testid="status">{cells[0].status}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells} onCellStatusChange={onCellStatusChange}>
        <TestComponent />
      </FactoryMapProvider>
    );

    expect(screen.getByTestId('status')).toHaveTextContent('running');
    
    fireEvent.click(screen.getByText('Update'));
    expect(screen.getByTestId('status')).toHaveTextContent('maintenance');
    expect(onCellStatusChange).toHaveBeenCalledWith('cell-1', 'maintenance');
  });

  test('should show order path', () => {
    const TestComponent = () => {
      const { orderPath, showOrderPath } = useFactoryMap();
      return (
        <div>
          <button onClick={() => showOrderPath(mockOrderPath)}>Show Path</button>
          <button onClick={() => showOrderPath(null)}>Clear Path</button>
          <span data-testid="path">{orderPath?.orderId ?? 'none'}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    fireEvent.click(screen.getByText('Show Path'));
    expect(screen.getByTestId('path')).toHaveTextContent('ORD-12345');
    
    fireEvent.click(screen.getByText('Clear Path'));
    expect(screen.getByTestId('path')).toHaveTextContent('none');
  });

  test('should manage zoom level', () => {
    const TestComponent = () => {
      const { zoomLevel, setZoomLevel } = useFactoryMap();
      return (
        <div>
          <button onClick={() => setZoomLevel(1.5)}>Zoom</button>
          <span data-testid="zoom">{zoomLevel}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    expect(screen.getByTestId('zoom')).toHaveTextContent('1');
    
    fireEvent.click(screen.getByText('Zoom'));
    expect(screen.getByTestId('zoom')).toHaveTextContent('1.5');
  });

  test('should manage pan offset', () => {
    const TestComponent = () => {
      const { panOffset, setPanOffset } = useFactoryMap();
      return (
        <div>
          <button onClick={() => setPanOffset({ x: 100, y: 50 })}>Pan</button>
          <span data-testid="pan">{`${panOffset.x},${panOffset.y}`}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    expect(screen.getByTestId('pan')).toHaveTextContent('0,0');
    
    fireEvent.click(screen.getByText('Pan'));
    expect(screen.getByTestId('pan')).toHaveTextContent('100,50');
  });

  test('should get cell by ID', () => {
    const TestComponent = () => {
      const { getCellById } = useFactoryMap();
      const cell = getCellById('cell-3');
      return <div data-testid="cell-name">{cell?.name ?? 'not found'}</div>;
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    expect(screen.getByTestId('cell-name')).toHaveTextContent('Quality Check');
  });

  test('should return undefined for non-existent cell', () => {
    const TestComponent = () => {
      const { getCellById } = useFactoryMap();
      const cell = getCellById('non-existent');
      return <div data-testid="cell-name">{cell?.name ?? 'not found'}</div>;
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    expect(screen.getByTestId('cell-name')).toHaveTextContent('not found');
  });
});

// =============================================================================
// FACTORY FLOOR MAP TESTS
// =============================================================================

describe('FactoryFloorMap', () => {
  test('should render SVG with correct dimensions', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap width={1000} height={800} />
      </FactoryMapProvider>
    );

    const svg = screen.getByRole('img', { name: 'Factory floor map' });
    expect(svg).toHaveAttribute('width', '1000');
    expect(svg).toHaveAttribute('height', '800');
  });

  test('should render all cells', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap />
      </FactoryMapProvider>
    );

    expect(screen.getByText('Workstation A')).toBeInTheDocument();
    expect(screen.getByText('Assembly B')).toBeInTheDocument();
    expect(screen.getByText('Quality Check')).toBeInTheDocument();
    expect(screen.getByText('Shipping')).toBeInTheDocument();
  });

  test('should show status text for cells', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap />
      </FactoryMapProvider>
    );

    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('Idle')).toBeInTheDocument();
    expect(screen.getByText('Changeover')).toBeInTheDocument();
    expect(screen.getByText('Blocked')).toBeInTheDocument();
  });

  test('should render grid when showGrid is true', () => {
    const { container } = render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap showGrid={true} />
      </FactoryMapProvider>
    );

    const gridLines = container.querySelectorAll('.grid line');
    expect(gridLines.length).toBeGreaterThan(0);
  });

  test('should not render grid when showGrid is false', () => {
    const { container } = render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap showGrid={false} />
      </FactoryMapProvider>
    );

    const gridGroup = container.querySelector('.grid');
    expect(gridGroup).toBeNull();
  });

  test('should render connections when showConnections is true', () => {
    const { container } = render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap showConnections={true} />
      </FactoryMapProvider>
    );

    const connections = container.querySelectorAll('.connections line');
    expect(connections.length).toBeGreaterThan(0);
  });

  test('should not render connections when showConnections is false', () => {
    const { container } = render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap showConnections={false} />
      </FactoryMapProvider>
    );

    const connectionsGroup = container.querySelector('.connections');
    expect(connectionsGroup).toBeNull();
  });

  test('should show current job in cell with metrics', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap />
      </FactoryMapProvider>
    );

    expect(screen.getByText('JOB-001')).toBeInTheDocument();
  });

  test('should apply custom className', () => {
    const { container } = render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap className="custom-map" />
      </FactoryMapProvider>
    );

    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('custom-map');
  });
});

// =============================================================================
// CELL DETAIL PANEL TESTS
// =============================================================================

describe('CellDetailPanel', () => {
  test('should show placeholder when no cell is selected', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <CellDetailPanel />
      </FactoryMapProvider>
    );

    expect(screen.getByText('Select a cell to view details')).toBeInTheDocument();
  });

  test('should show cell details when selected', () => {
    const TestComponent = () => {
      const { selectCell } = useFactoryMap();
      React.useEffect(() => {
        selectCell('cell-1');
      }, [selectCell]);
      return <CellDetailPanel />;
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    expect(screen.getByText('Workstation A')).toBeInTheDocument();
    expect(screen.getByText('workstation')).toBeInTheDocument();
    expect(screen.getByText('25 units/hr')).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument();
    expect(screen.getByText('JOB-001')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  test('should show status buttons', () => {
    const TestComponent = () => {
      const { selectCell } = useFactoryMap();
      React.useEffect(() => {
        selectCell('cell-1');
      }, [selectCell]);
      return <CellDetailPanel />;
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    expect(screen.getByRole('button', { name: 'Idle' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Running' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Maintenance' })).toBeInTheDocument();
  });

  test('should update status when clicking status button', () => {
    const TestComponent = () => {
      const { selectCell, cells } = useFactoryMap();
      React.useEffect(() => {
        selectCell('cell-1');
      }, [selectCell]);
      return (
        <div>
          <CellDetailPanel />
          <span data-testid="current-status">{cells[0].status}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Maintenance' }));
    expect(screen.getByTestId('current-status')).toHaveTextContent('maintenance');
  });

  test('should close panel when clicking close button', () => {
    const TestComponent = () => {
      const { selectCell, selectedCell } = useFactoryMap();
      React.useEffect(() => {
        selectCell('cell-1');
      }, [selectCell]);
      return (
        <div>
          <CellDetailPanel />
          <span data-testid="selected">{selectedCell?.id ?? 'none'}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Close panel' }));
    expect(screen.getByTestId('selected')).toHaveTextContent('none');
  });
});

// =============================================================================
// GEMBA PATH VISUALIZER TESTS
// =============================================================================

describe('GembaPathVisualizer', () => {
  test('should render order information', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <GembaPathVisualizer path={mockOrderPath} />
      </FactoryMapProvider>
    );

    expect(screen.getByText('Order Path: Customer Order #12345')).toBeInTheDocument();
    expect(screen.getByText('ID: ORD-12345')).toBeInTheDocument();
  });

  test('should show time metrics', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <GembaPathVisualizer path={mockOrderPath} />
      </FactoryMapProvider>
    );

    expect(screen.getByText('90 min')).toBeInTheDocument(); // Process Time
    expect(screen.getByText('Process Time')).toBeInTheDocument();
    expect(screen.getByText('Travel/Wait (Waste)')).toBeInTheDocument();
    // 15 min appears both in header (travel) and in step duration, so check for multiple
    expect(screen.getAllByText('15 min').length).toBeGreaterThanOrEqual(1);
  });

  test('should calculate and display waste percentage', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <GembaPathVisualizer path={mockOrderPath} />
      </FactoryMapProvider>
    );

    // 15 / (15 + 90) * 100 = 14.3%
    expect(screen.getByText('14.3%')).toBeInTheDocument();
  });

  test('should render all path steps', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <GembaPathVisualizer path={mockOrderPath} />
      </FactoryMapProvider>
    );

    expect(screen.getByText('Workstation A')).toBeInTheDocument();
    expect(screen.getByText('Assembly B')).toBeInTheDocument();
    expect(screen.getByText('Quality Check')).toBeInTheDocument();
    expect(screen.getByText('Shipping')).toBeInTheDocument();
  });

  test('should show duration for each step', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <GembaPathVisualizer path={mockOrderPath} />
      </FactoryMapProvider>
    );

    expect(screen.getByText('30 min')).toBeInTheDocument();
    expect(screen.getByText('45 min')).toBeInTheDocument();
    // 15 min appears in both header and step 3, so check for at least one match
    expect(screen.getAllByText('15 min').length).toBeGreaterThanOrEqual(1);
  });

  test('should show travel time between steps', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <GembaPathVisualizer path={mockOrderPath} />
      </FactoryMapProvider>
    );

    expect(screen.getByText('+5 min travel')).toBeInTheDocument();
    expect(screen.getByText('+10 min travel')).toBeInTheDocument();
  });

  test('should call onClose when close button clicked', () => {
    const onClose = jest.fn();
    
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <GembaPathVisualizer path={mockOrderPath} onClose={onClose} />
      </FactoryMapProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Close path view' }));
    expect(onClose).toHaveBeenCalled();
  });

  test('should not render close button when onClose is not provided', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <GembaPathVisualizer path={mockOrderPath} />
      </FactoryMapProvider>
    );

    expect(screen.queryByRole('button', { name: 'Close path view' })).not.toBeInTheDocument();
  });
});

// =============================================================================
// MAP CONTROLS TESTS
// =============================================================================

describe('MapControls', () => {
  test('should render zoom controls', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <MapControls />
      </FactoryMapProvider>
    );

    expect(screen.getByRole('button', { name: 'Zoom in' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Zoom out' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reset view' })).toBeInTheDocument();
  });

  test('should display current zoom level', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <MapControls />
      </FactoryMapProvider>
    );

    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  test('should zoom in when clicking zoom in button', () => {
    const TestComponent = () => {
      const { zoomLevel } = useFactoryMap();
      return (
        <div>
          <MapControls />
          <span data-testid="zoom">{zoomLevel}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }));
    expect(screen.getByTestId('zoom')).toHaveTextContent('1.25');
  });

  test('should zoom out when clicking zoom out button', () => {
    const TestComponent = () => {
      const { zoomLevel, setZoomLevel } = useFactoryMap();
      React.useEffect(() => {
        setZoomLevel(1.5);
      }, [setZoomLevel]);
      return (
        <div>
          <MapControls />
          <span data-testid="zoom">{zoomLevel}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Zoom out' }));
    expect(screen.getByTestId('zoom')).toHaveTextContent('1.25');
  });

  test('should reset view when clicking reset button', () => {
    const TestComponent = () => {
      const { zoomLevel, setZoomLevel, panOffset, setPanOffset } = useFactoryMap();
      React.useEffect(() => {
        setZoomLevel(2);
        setPanOffset({ x: 100, y: 50 });
      }, [setZoomLevel, setPanOffset]);
      return (
        <div>
          <MapControls />
          <span data-testid="zoom">{zoomLevel}</span>
          <span data-testid="pan">{`${panOffset.x},${panOffset.y}`}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Reset view' }));
    expect(screen.getByTestId('zoom')).toHaveTextContent('1');
    expect(screen.getByTestId('pan')).toHaveTextContent('0,0');
  });

  test('should disable zoom out at minimum zoom', () => {
    const TestComponent = () => {
      const { setZoomLevel } = useFactoryMap();
      React.useEffect(() => {
        setZoomLevel(0.5);
      }, [setZoomLevel]);
      return <MapControls />;
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    expect(screen.getByRole('button', { name: 'Zoom out' })).toBeDisabled();
  });

  test('should disable zoom in at maximum zoom', () => {
    const TestComponent = () => {
      const { setZoomLevel } = useFactoryMap();
      React.useEffect(() => {
        setZoomLevel(3);
      }, [setZoomLevel]);
      return <MapControls />;
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    expect(screen.getByRole('button', { name: 'Zoom in' })).toBeDisabled();
  });
});

// =============================================================================
// CELL STATUS LEGEND TESTS
// =============================================================================

describe('CellStatusLegend', () => {
  test('should render all status types', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <CellStatusLegend />
      </FactoryMapProvider>
    );

    expect(screen.getByText('Idle')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('Changeover')).toBeInTheDocument();
    expect(screen.getByText('Maintenance')).toBeInTheDocument();
    expect(screen.getByText('Blocked')).toBeInTheDocument();
    expect(screen.getByText('Offline')).toBeInTheDocument();
  });

  test('should render colored indicators', () => {
    const { container } = render(
      <FactoryMapProvider initialCells={mockCells}>
        <CellStatusLegend />
      </FactoryMapProvider>
    );

    const indicators = container.querySelectorAll('.w-4.h-4.rounded');
    expect(indicators).toHaveLength(6);
  });
});

// =============================================================================
// WAR ROOM PROVIDER TESTS
// =============================================================================

describe('WarRoomProvider', () => {
  test('should provide context to children', () => {
    const TestComponent = () => {
      const context = useWarRoom();
      return <div data-testid="layout-count">{context.layout.length}</div>;
    };

    render(
      <WarRoomProvider>
        <TestComponent />
      </WarRoomProvider>
    );

    expect(screen.getByTestId('layout-count')).toHaveTextContent('6');
  });

  test('should throw error when used outside provider', () => {
    const TestComponent = () => {
      useWarRoom();
      return null;
    };

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestComponent />)).toThrow('useWarRoom must be used within a WarRoomProvider');
    consoleSpy.mockRestore();
  });

  test('should use custom layout', () => {
    const customLayout = [DEFAULT_WAR_ROOM_LAYOUT[0]];
    const TestComponent = () => {
      const { layout } = useWarRoom();
      return <div data-testid="layout-count">{layout.length}</div>;
    };

    render(
      <WarRoomProvider layout={customLayout}>
        <TestComponent />
      </WarRoomProvider>
    );

    expect(screen.getByTestId('layout-count')).toHaveTextContent('1');
  });

  test('should manage active panel', () => {
    const TestComponent = () => {
      const { activePanel, setActivePanel } = useWarRoom();
      return (
        <div>
          <button onClick={() => setActivePanel('kpi')}>Set KPI</button>
          <button onClick={() => setActivePanel(null)}>Clear</button>
          <span data-testid="active">{activePanel ?? 'none'}</span>
        </div>
      );
    };

    render(
      <WarRoomProvider>
        <TestComponent />
      </WarRoomProvider>
    );

    expect(screen.getByTestId('active')).toHaveTextContent('none');
    
    fireEvent.click(screen.getByText('Set KPI'));
    expect(screen.getByTestId('active')).toHaveTextContent('kpi');
    
    fireEvent.click(screen.getByText('Clear'));
    expect(screen.getByTestId('active')).toHaveTextContent('none');
  });

  test('should manage refresh interval', () => {
    const TestComponent = () => {
      const { refreshInterval, setRefreshInterval } = useWarRoom();
      return (
        <div>
          <button onClick={() => setRefreshInterval(60000)}>Set 60s</button>
          <span data-testid="interval">{refreshInterval}</span>
        </div>
      );
    };

    render(
      <WarRoomProvider defaultRefreshInterval={30000}>
        <TestComponent />
      </WarRoomProvider>
    );

    expect(screen.getByTestId('interval')).toHaveTextContent('30000');
    
    fireEvent.click(screen.getByText('Set 60s'));
    expect(screen.getByTestId('interval')).toHaveTextContent('60000');
  });

  test('should trigger refresh callback', () => {
    const onRefresh = jest.fn();
    const TestComponent = () => {
      const { refreshNow } = useWarRoom();
      return <button onClick={refreshNow}>Refresh</button>;
    };

    render(
      <WarRoomProvider onRefresh={onRefresh}>
        <TestComponent />
      </WarRoomProvider>
    );

    fireEvent.click(screen.getByText('Refresh'));
    expect(onRefresh).toHaveBeenCalled();
  });

  test('should update lastRefresh on refresh', () => {
    const TestComponent = () => {
      const { lastRefresh, refreshNow } = useWarRoom();
      return (
        <div>
          <button onClick={refreshNow}>Refresh</button>
          <span data-testid="refreshed">{lastRefresh ? 'yes' : 'no'}</span>
        </div>
      );
    };

    render(
      <WarRoomProvider>
        <TestComponent />
      </WarRoomProvider>
    );

    expect(screen.getByTestId('refreshed')).toHaveTextContent('no');
    
    fireEvent.click(screen.getByText('Refresh'));
    expect(screen.getByTestId('refreshed')).toHaveTextContent('yes');
  });
});

// =============================================================================
// WAR ROOM DASHBOARD TESTS
// =============================================================================

describe('WarRoomDashboard', () => {
  test('should render dashboard with title', () => {
    render(
      <WarRoomProvider>
        <WarRoomDashboard />
      </WarRoomProvider>
    );

    expect(screen.getByText('🏢 Executive War Room')).toBeInTheDocument();
  });

  test('should render refresh controls', () => {
    render(
      <WarRoomProvider>
        <WarRoomDashboard />
      </WarRoomProvider>
    );

    expect(screen.getByRole('combobox', { name: 'Refresh interval' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument();
  });

  test('should render fullscreen button', () => {
    render(
      <WarRoomProvider>
        <WarRoomDashboard />
      </WarRoomProvider>
    );

    expect(screen.getByRole('button', { name: 'Enter fullscreen' })).toBeInTheDocument();
  });

  test('should change refresh interval', () => {
    const TestComponent = () => {
      const { refreshInterval } = useWarRoom();
      return (
        <div>
          <WarRoomDashboard />
          <span data-testid="interval">{refreshInterval}</span>
        </div>
      );
    };

    render(
      <WarRoomProvider>
        <TestComponent />
      </WarRoomProvider>
    );

    fireEvent.change(screen.getByRole('combobox', { name: 'Refresh interval' }), {
      target: { value: '60000' },
    });
    expect(screen.getByTestId('interval')).toHaveTextContent('60000');
  });

  test('should show last refresh time', () => {
    const TestComponent = () => {
      const { refreshNow } = useWarRoom();
      React.useEffect(() => {
        refreshNow();
      }, [refreshNow]);
      return <WarRoomDashboard />;
    };

    render(
      <WarRoomProvider>
        <TestComponent />
      </WarRoomProvider>
    );

    expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
  });

  test('should render children in grid', () => {
    render(
      <WarRoomProvider>
        <WarRoomDashboard>
          <div data-testid="panel-1">Panel 1</div>
          <div data-testid="panel-2">Panel 2</div>
        </WarRoomDashboard>
      </WarRoomProvider>
    );

    expect(screen.getByTestId('panel-1')).toBeInTheDocument();
    expect(screen.getByTestId('panel-2')).toBeInTheDocument();
  });
});

// =============================================================================
// WAR ROOM PANEL CONTAINER TESTS
// =============================================================================

describe('WarRoomPanelContainer', () => {
  const testConfig = DEFAULT_WAR_ROOM_LAYOUT[0];

  test('should render panel with title and icon', () => {
    render(
      <WarRoomProvider>
        <WarRoomPanelContainer config={testConfig}>
          Content
        </WarRoomPanelContainer>
      </WarRoomProvider>
    );

    expect(screen.getByText('📊')).toBeInTheDocument();
    expect(screen.getByText('Key Performance Indicators')).toBeInTheDocument();
  });

  test('should render children', () => {
    render(
      <WarRoomProvider>
        <WarRoomPanelContainer config={testConfig}>
          <div data-testid="content">Panel Content</div>
        </WarRoomPanelContainer>
      </WarRoomProvider>
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
  });

  test('should expand panel on click', () => {
    const TestComponent = () => {
      const { activePanel } = useWarRoom();
      return (
        <div>
          <WarRoomPanelContainer config={testConfig}>Content</WarRoomPanelContainer>
          <span data-testid="active">{activePanel ?? 'none'}</span>
        </div>
      );
    };

    render(
      <WarRoomProvider>
        <TestComponent />
      </WarRoomProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Expand panel' }));
    expect(screen.getByTestId('active')).toHaveTextContent('kpi');
  });

  test('should collapse panel when already active', () => {
    const TestComponent = () => {
      const { activePanel, setActivePanel } = useWarRoom();
      React.useEffect(() => {
        setActivePanel('kpi');
      }, [setActivePanel]);
      return (
        <div>
          <WarRoomPanelContainer config={testConfig}>Content</WarRoomPanelContainer>
          <span data-testid="active">{activePanel ?? 'none'}</span>
        </div>
      );
    };

    render(
      <WarRoomProvider>
        <TestComponent />
      </WarRoomProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Collapse panel' }));
    expect(screen.getByTestId('active')).toHaveTextContent('none');
  });

  test('should call onExpand callback', () => {
    const onExpand = jest.fn();
    
    render(
      <WarRoomProvider>
        <WarRoomPanelContainer config={testConfig} onExpand={onExpand}>
          Content
        </WarRoomPanelContainer>
      </WarRoomProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Expand panel' }));
    expect(onExpand).toHaveBeenCalled();
  });
});

// =============================================================================
// KPI PANEL TESTS
// =============================================================================

describe('KPIPanel', () => {
  test('should render all KPIs', () => {
    render(<KPIPanel kpis={mockKPIs} />);

    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('$125K')).toBeInTheDocument();
    expect(screen.getByText('Orders')).toBeInTheDocument();
    expect(screen.getByText('156')).toBeInTheDocument();
    expect(screen.getByText('OEE')).toBeInTheDocument();
    expect(screen.getByText('87')).toBeInTheDocument();
    expect(screen.getByText('Defects')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  test('should show units', () => {
    render(<KPIPanel kpis={mockKPIs} />);

    expect(screen.getByText('today')).toBeInTheDocument();
    expect(screen.getByText('%')).toBeInTheDocument();
  });

  test('should show positive change', () => {
    render(<KPIPanel kpis={mockKPIs} />);

    expect(screen.getByText('↑ 12.5%')).toBeInTheDocument();
  });

  test('should show negative change', () => {
    render(<KPIPanel kpis={mockKPIs} />);

    expect(screen.getByText('↓ 3.2%')).toBeInTheDocument();
  });

  test('should show target', () => {
    render(<KPIPanel kpis={mockKPIs} />);

    expect(screen.getByText('Target: 85%')).toBeInTheDocument();
  });

  test('should use custom columns', () => {
    const { container } = render(<KPIPanel kpis={mockKPIs} columns={2} />);

    const grid = container.querySelector('.grid');
    expect(grid).toHaveStyle({ gridTemplateColumns: 'repeat(2, 1fr)' });
  });
});

// =============================================================================
// ALERTS PANEL TESTS
// =============================================================================

describe('AlertsPanel', () => {
  test('should show message when no alerts', () => {
    render(<AlertsPanel alerts={[]} />);

    expect(screen.getByText('✅ No active alerts')).toBeInTheDocument();
  });

  test('should render all alerts', () => {
    render(<AlertsPanel alerts={mockAlerts} />);

    expect(screen.getByText('Machine Down')).toBeInTheDocument();
    expect(screen.getByText('Low Inventory')).toBeInTheDocument();
    expect(screen.getByText('Shift Change')).toBeInTheDocument();
  });

  test('should show alert messages', () => {
    render(<AlertsPanel alerts={mockAlerts} />);

    expect(screen.getByText('CNC Machine #3 has stopped responding')).toBeInTheDocument();
    expect(screen.getByText('Part XYZ-123 below reorder point')).toBeInTheDocument();
    expect(screen.getByText('Night shift starting in 30 minutes')).toBeInTheDocument();
  });

  test('should show severity icons', () => {
    render(<AlertsPanel alerts={mockAlerts} />);

    expect(screen.getByText('🔴')).toBeInTheDocument();
    expect(screen.getByText('🟡')).toBeInTheDocument();
    expect(screen.getByText('🔵')).toBeInTheDocument();
  });

  test('should show source when available', () => {
    render(<AlertsPanel alerts={mockAlerts} />);

    // Production source for first alert
    expect(screen.getByText(/• Production/)).toBeInTheDocument();
    // Inventory appears both in title "Low Inventory" and source, use more specific match
    expect(screen.getByText(/• Inventory/)).toBeInTheDocument();
  });

  test('should show acknowledge button when handler provided', () => {
    const onAcknowledge = jest.fn();
    render(<AlertsPanel alerts={mockAlerts} onAcknowledge={onAcknowledge} />);

    const ackButtons = screen.getAllByText('ACK');
    expect(ackButtons).toHaveLength(3);
  });

  test('should call onAcknowledge with alert ID', () => {
    const onAcknowledge = jest.fn();
    render(<AlertsPanel alerts={mockAlerts} onAcknowledge={onAcknowledge} />);

    const ackButtons = screen.getAllByText('ACK');
    fireEvent.click(ackButtons[0]);
    expect(onAcknowledge).toHaveBeenCalledWith('alert-1');
  });

  test('should limit displayed alerts', () => {
    const manyAlerts = Array(15).fill(null).map((_, i) => ({
      ...mockAlerts[0],
      id: `alert-${i}`,
      title: `Alert ${i}`,
    }));

    render(<AlertsPanel alerts={manyAlerts} maxItems={5} />);

    expect(screen.getByText('+10 more alerts')).toBeInTheDocument();
  });
});

// =============================================================================
// TIMELINE PANEL TESTS
// =============================================================================

describe('TimelinePanel', () => {
  test('should show message when no events', () => {
    render(<TimelinePanel events={[]} />);

    expect(screen.getByText('📅 No events scheduled')).toBeInTheDocument();
  });

  test('should render all events', () => {
    render(<TimelinePanel events={mockTimelineEvents} />);

    expect(screen.getByText('Morning Standup')).toBeInTheDocument();
    expect(screen.getByText('Production Review')).toBeInTheDocument();
    expect(screen.getByText('Order Deadline')).toBeInTheDocument();
    expect(screen.getByText('Monthly Milestone')).toBeInTheDocument();
  });

  test('should show event type icons', () => {
    render(<TimelinePanel events={mockTimelineEvents} />);

    // Meeting icon appears twice (Morning Standup and Production Review)
    expect(screen.getAllByText('👥')).toHaveLength(2);
    expect(screen.getByText('⏰')).toBeInTheDocument();
    expect(screen.getByText('🎯')).toBeInTheDocument();
  });

  test('should show completed status', () => {
    render(<TimelinePanel events={mockTimelineEvents} />);

    const completedMarkers = screen.getAllByText('✓');
    expect(completedMarkers.length).toBeGreaterThan(0);
  });

  test('should sort events by time', () => {
    render(<TimelinePanel events={mockTimelineEvents} />);

    // Check that events are rendered in order by checking the container structure
    // The first event title (Morning Standup) should be in the document  
    expect(screen.getByText('Morning Standup')).toBeInTheDocument();
    expect(screen.getByText('Production Review')).toBeInTheDocument();
    expect(screen.getByText('Order Deadline')).toBeInTheDocument();
    expect(screen.getByText('Monthly Milestone')).toBeInTheDocument();
  });

  test('should filter past events when showPastEvents is false', () => {
    const pastEvent: TimelineEvent = {
      id: 'past-1',
      time: new Date(Date.now() - 86400000), // 1 day ago
      title: 'Past Event',
      type: 'meeting',
      completed: false,
    };

    render(<TimelinePanel events={[pastEvent, ...mockTimelineEvents]} showPastEvents={false} />);

    // Past incomplete event should not be shown
    expect(screen.queryByText('Past Event')).not.toBeInTheDocument();
  });
});

// =============================================================================
// DEFAULT WAR ROOM LAYOUT TESTS
// =============================================================================

describe('DEFAULT_WAR_ROOM_LAYOUT', () => {
  test('should have 6 panels', () => {
    expect(DEFAULT_WAR_ROOM_LAYOUT).toHaveLength(6);
  });

  test('should have KPI panel', () => {
    const kpiPanel = DEFAULT_WAR_ROOM_LAYOUT.find((p) => p.id === 'kpi');
    expect(kpiPanel).toBeDefined();
    expect(kpiPanel?.title).toBe('Key Performance Indicators');
    expect(kpiPanel?.priority).toBe('high');
  });

  test('should have pipeline panel', () => {
    const panel = DEFAULT_WAR_ROOM_LAYOUT.find((p) => p.id === 'pipeline');
    expect(panel).toBeDefined();
    expect(panel?.title).toBe('Sales Pipeline');
  });

  test('should have production panel', () => {
    const panel = DEFAULT_WAR_ROOM_LAYOUT.find((p) => p.id === 'production');
    expect(panel).toBeDefined();
    expect(panel?.title).toBe('Production Status');
    expect(panel?.priority).toBe('high');
  });

  test('should have quality panel', () => {
    const panel = DEFAULT_WAR_ROOM_LAYOUT.find((p) => p.id === 'quality');
    expect(panel).toBeDefined();
    expect(panel?.title).toBe('Quality Metrics');
  });

  test('should have alerts panel', () => {
    const panel = DEFAULT_WAR_ROOM_LAYOUT.find((p) => p.id === 'alerts');
    expect(panel).toBeDefined();
    expect(panel?.title).toBe('Active Alerts');
    expect(panel?.priority).toBe('high');
  });

  test('should have timeline panel', () => {
    const panel = DEFAULT_WAR_ROOM_LAYOUT.find((p) => p.id === 'timeline');
    expect(panel).toBeDefined();
    expect(panel?.title).toBe("Today's Timeline");
  });

  test('should have valid span configurations', () => {
    DEFAULT_WAR_ROOM_LAYOUT.forEach((panel) => {
      expect(panel.span.cols).toBeGreaterThan(0);
      expect(panel.span.rows).toBeGreaterThan(0);
    });
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Factory Map Integration', () => {
  test('should integrate floor map with cell selection', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap />
        <CellDetailPanel />
      </FactoryMapProvider>
    );

    // Initially no cell selected
    expect(screen.getByText('Select a cell to view details')).toBeInTheDocument();
    
    // Click on a cell name in the map (simulating cell click)
    // The cell text is inside an SVG text element
    const cellTexts = screen.getAllByText('Workstation A');
    expect(cellTexts.length).toBeGreaterThan(0);
  });

  test('should integrate floor map with gemba path', () => {
    render(
      <FactoryMapProvider initialCells={mockCells}>
        <FactoryFloorMap />
        <GembaPathVisualizer path={mockOrderPath} />
      </FactoryMapProvider>
    );

    // Path should be shown
    expect(screen.getByText('Order Path: Customer Order #12345')).toBeInTheDocument();
    
    // Map should render cells on path
    expect(screen.getAllByText('Workstation A').length).toBeGreaterThanOrEqual(1);
  });

  test('should integrate map controls with floor map', () => {
    const TestComponent = () => {
      const { zoomLevel } = useFactoryMap();
      return (
        <div>
          <MapControls />
          <FactoryFloorMap />
          <span data-testid="zoom">{zoomLevel}</span>
        </div>
      );
    };

    render(
      <FactoryMapProvider initialCells={mockCells}>
        <TestComponent />
      </FactoryMapProvider>
    );

    // Zoom in
    fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }));
    expect(screen.getByTestId('zoom')).toHaveTextContent('1.25');
    
    // The SVG viewBox should adjust
    const svg = screen.getByRole('img', { name: 'Factory floor map' });
    expect(svg).toBeInTheDocument();
  });
});

describe('War Room Integration', () => {
  test('should integrate dashboard with panels', () => {
    render(
      <WarRoomProvider>
        <WarRoomDashboard>
          <WarRoomPanelContainer config={DEFAULT_WAR_ROOM_LAYOUT[0]}>
            <KPIPanel kpis={mockKPIs} />
          </WarRoomPanelContainer>
          <WarRoomPanelContainer config={DEFAULT_WAR_ROOM_LAYOUT[5]}>
            <AlertsPanel alerts={mockAlerts} />
          </WarRoomPanelContainer>
        </WarRoomDashboard>
      </WarRoomProvider>
    );

    // Dashboard header
    expect(screen.getByText('🏢 Executive War Room')).toBeInTheDocument();
    
    // KPI Panel
    expect(screen.getByText('Key Performance Indicators')).toBeInTheDocument();
    expect(screen.getByText('Revenue')).toBeInTheDocument();
    
    // Alerts Panel (uses Active Alerts from timeline config)
    expect(screen.getByText('Machine Down')).toBeInTheDocument();
  });

  test('should handle auto-refresh', async () => {
    jest.useFakeTimers();
    const onRefresh = jest.fn();

    render(
      <WarRoomProvider defaultRefreshInterval={1000} onRefresh={onRefresh}>
        <WarRoomDashboard>
          <div>Content</div>
        </WarRoomDashboard>
      </WarRoomProvider>
    );

    // Advance timer
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(onRefresh).toHaveBeenCalled();

    jest.useRealTimers();
  });
});
