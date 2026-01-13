'use client';

import React, { createContext, useContext, useState, useCallback, useMemo, useEffect, useRef } from 'react';

// =============================================================================
// PRODUCTION CELL TYPES
// =============================================================================

/**
 * Status of a production cell/workstation
 */
export const CELL_STATUS = {
  idle: 'idle',
  running: 'running',
  changeover: 'changeover',
  maintenance: 'maintenance',
  blocked: 'blocked',
  offline: 'offline',
} as const;

export type CellStatus = keyof typeof CELL_STATUS;

/**
 * Color mapping for cell statuses
 */
export const CELL_STATUS_COLORS: Record<CellStatus, { fill: string; stroke: string; text: string }> = {
  idle: { fill: '#e5e7eb', stroke: '#9ca3af', text: 'Idle' },
  running: { fill: '#bbf7d0', stroke: '#22c55e', text: 'Running' },
  changeover: { fill: '#fef08a', stroke: '#eab308', text: 'Changeover' },
  maintenance: { fill: '#fed7aa', stroke: '#f97316', text: 'Maintenance' },
  blocked: { fill: '#fecaca', stroke: '#ef4444', text: 'Blocked' },
  offline: { fill: '#d1d5db', stroke: '#6b7280', text: 'Offline' },
};

/**
 * Production cell definition
 */
export interface ProductionCell {
  id: string;
  name: string;
  type: 'workstation' | 'machine' | 'assembly' | 'quality' | 'storage' | 'shipping' | 'receiving';
  status: CellStatus;
  position: { x: number; y: number };
  size: { width: number; height: number };
  metrics?: {
    throughput?: number;
    efficiency?: number;
    currentJob?: string;
    operator?: string;
  };
  connections?: string[]; // IDs of connected cells (material flow)
}

/**
 * Order path through the factory
 */
export interface OrderPath {
  orderId: string;
  orderName: string;
  steps: Array<{
    cellId: string;
    cellName: string;
    status: 'completed' | 'current' | 'pending';
    timestamp?: Date;
    duration?: number; // minutes
    travelTime?: number; // minutes to next cell
  }>;
  totalTravelTime: number; // total travel/wait time (waste)
  totalProcessTime: number;
}

// =============================================================================
// FACTORY MAP CONTEXT
// =============================================================================

export interface FactoryMapContextValue {
  cells: ProductionCell[];
  selectedCell: ProductionCell | null;
  hoveredCell: ProductionCell | null;
  orderPath: OrderPath | null;
  selectCell: (cellId: string | null) => void;
  hoverCell: (cellId: string | null) => void;
  showOrderPath: (path: OrderPath | null) => void;
  getCellById: (id: string) => ProductionCell | undefined;
  updateCellStatus: (cellId: string, status: CellStatus) => void;
  zoomLevel: number;
  setZoomLevel: (level: number) => void;
  panOffset: { x: number; y: number };
  setPanOffset: (offset: { x: number; y: number }) => void;
}

const FactoryMapContext = createContext<FactoryMapContextValue | null>(null);

export interface FactoryMapProviderProps {
  children: React.ReactNode;
  initialCells?: ProductionCell[];
  onCellSelect?: (cell: ProductionCell | null) => void;
  onCellStatusChange?: (cellId: string, status: CellStatus) => void;
}

export function FactoryMapProvider({
  children,
  initialCells = [],
  onCellSelect,
  onCellStatusChange,
}: FactoryMapProviderProps) {
  const [cells, setCells] = useState<ProductionCell[]>(initialCells);
  const [selectedCell, setSelectedCell] = useState<ProductionCell | null>(null);
  const [hoveredCell, setHoveredCell] = useState<ProductionCell | null>(null);
  const [orderPath, setOrderPath] = useState<OrderPath | null>(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });

  const getCellById = useCallback(
    (id: string) => cells.find((c) => c.id === id),
    [cells]
  );

  const selectCell = useCallback(
    (cellId: string | null) => {
      const cell = cellId ? getCellById(cellId) : null;
      setSelectedCell(cell ?? null);
      onCellSelect?.(cell ?? null);
    },
    [getCellById, onCellSelect]
  );

  const hoverCell = useCallback(
    (cellId: string | null) => {
      const cell = cellId ? getCellById(cellId) : null;
      setHoveredCell(cell ?? null);
    },
    [getCellById]
  );

  const showOrderPath = useCallback((path: OrderPath | null) => {
    setOrderPath(path);
  }, []);

  const updateCellStatus = useCallback(
    (cellId: string, status: CellStatus) => {
      setCells((prev) =>
        prev.map((cell) => (cell.id === cellId ? { ...cell, status } : cell))
      );
      onCellStatusChange?.(cellId, status);
    },
    [onCellStatusChange]
  );

  const value = useMemo<FactoryMapContextValue>(
    () => ({
      cells,
      selectedCell,
      hoveredCell,
      orderPath,
      selectCell,
      hoverCell,
      showOrderPath,
      getCellById,
      updateCellStatus,
      zoomLevel,
      setZoomLevel,
      panOffset,
      setPanOffset,
    }),
    [
      cells,
      selectedCell,
      hoveredCell,
      orderPath,
      selectCell,
      hoverCell,
      showOrderPath,
      getCellById,
      updateCellStatus,
      zoomLevel,
      panOffset,
    ]
  );

  return (
    <FactoryMapContext.Provider value={value}>
      {children}
    </FactoryMapContext.Provider>
  );
}

export function useFactoryMap(): FactoryMapContextValue {
  const context = useContext(FactoryMapContext);
  if (!context) {
    throw new Error('useFactoryMap must be used within a FactoryMapProvider');
  }
  return context;
}

// =============================================================================
// SVG FACTORY FLOOR MAP
// =============================================================================

export interface FactoryFloorMapProps {
  width?: number;
  height?: number;
  showGrid?: boolean;
  showConnections?: boolean;
  className?: string;
}

export function FactoryFloorMap({
  width = 800,
  height = 600,
  showGrid = true,
  showConnections = true,
  className = '',
}: FactoryFloorMapProps) {
  const { cells, selectedCell, hoveredCell, orderPath, selectCell, hoverCell, zoomLevel, panOffset } =
    useFactoryMap();

  const renderGrid = () => {
    const gridSize = 50;
    const lines = [];

    for (let x = 0; x <= width; x += gridSize) {
      lines.push(
        <line
          key={`v-${x}`}
          x1={x}
          y1={0}
          x2={x}
          y2={height}
          stroke="#e5e7eb"
          strokeWidth={0.5}
        />
      );
    }

    for (let y = 0; y <= height; y += gridSize) {
      lines.push(
        <line
          key={`h-${y}`}
          x1={0}
          y1={y}
          x2={width}
          y2={y}
          stroke="#e5e7eb"
          strokeWidth={0.5}
        />
      );
    }

    return <g className="grid">{lines}</g>;
  };

  const renderConnections = () => {
    const connections: JSX.Element[] = [];

    cells.forEach((cell) => {
      if (cell.connections) {
        cell.connections.forEach((targetId) => {
          const target = cells.find((c) => c.id === targetId);
          if (target) {
            const fromX = cell.position.x + cell.size.width / 2;
            const fromY = cell.position.y + cell.size.height / 2;
            const toX = target.position.x + target.size.width / 2;
            const toY = target.position.y + target.size.height / 2;

            connections.push(
              <line
                key={`${cell.id}-${targetId}`}
                x1={fromX}
                y1={fromY}
                x2={toX}
                y2={toY}
                stroke="#94a3b8"
                strokeWidth={2}
                strokeDasharray="5,5"
                markerEnd="url(#arrowhead)"
              />
            );
          }
        });
      }
    });

    return <g className="connections">{connections}</g>;
  };

  const renderOrderPath = () => {
    if (!orderPath) return null;

    const pathCells = orderPath.steps.map((step) =>
      cells.find((c) => c.id === step.cellId)
    );

    const pathPoints: { x: number; y: number }[] = [];
    pathCells.forEach((cell) => {
      if (cell) {
        pathPoints.push({
          x: cell.position.x + cell.size.width / 2,
          y: cell.position.y + cell.size.height / 2,
        });
      }
    });

    if (pathPoints.length < 2) return null;

    const pathD = pathPoints
      .map((point, i) => (i === 0 ? `M ${point.x} ${point.y}` : `L ${point.x} ${point.y}`))
      .join(' ');

    return (
      <g className="order-path">
        <path
          d={pathD}
          fill="none"
          stroke="#3b82f6"
          strokeWidth={4}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.8}
        />
        {pathPoints.map((point, i) => (
          <circle
            key={orderPath.steps[i].cellId}
            cx={point.x}
            cy={point.y}
            r={8}
            fill={
              orderPath.steps[i].status === 'completed'
                ? '#22c55e'
                : orderPath.steps[i].status === 'current'
                  ? '#3b82f6'
                  : '#9ca3af'
            }
            stroke="white"
            strokeWidth={2}
          />
        ))}
      </g>
    );
  };

  const renderCell = (cell: ProductionCell) => {
    const colors = CELL_STATUS_COLORS[cell.status];
    const isSelected = selectedCell?.id === cell.id;
    const isHovered = hoveredCell?.id === cell.id;
    const isOnPath = orderPath?.steps.some((s) => s.cellId === cell.id);

    return (
      <g
        key={cell.id}
        className="production-cell"
        onClick={() => selectCell(cell.id)}
        onMouseEnter={() => hoverCell(cell.id)}
        onMouseLeave={() => hoverCell(null)}
        style={{ cursor: 'pointer' }}
      >
        <rect
          x={cell.position.x}
          y={cell.position.y}
          width={cell.size.width}
          height={cell.size.height}
          fill={colors.fill}
          stroke={isSelected ? '#3b82f6' : isOnPath ? '#3b82f6' : colors.stroke}
          strokeWidth={isSelected || isHovered ? 3 : 2}
          rx={4}
          ry={4}
        />
        <text
          x={cell.position.x + cell.size.width / 2}
          y={cell.position.y + cell.size.height / 2 - 8}
          textAnchor="middle"
          fontSize={12}
          fontWeight="bold"
          fill="#374151"
        >
          {cell.name}
        </text>
        <text
          x={cell.position.x + cell.size.width / 2}
          y={cell.position.y + cell.size.height / 2 + 8}
          textAnchor="middle"
          fontSize={10}
          fill="#6b7280"
        >
          {colors.text}
        </text>
        {cell.metrics?.currentJob && (
          <text
            x={cell.position.x + cell.size.width / 2}
            y={cell.position.y + cell.size.height / 2 + 22}
            textAnchor="middle"
            fontSize={9}
            fill="#3b82f6"
          >
            {cell.metrics.currentJob}
          </text>
        )}
      </g>
    );
  };

  return (
    <svg
      width={width}
      height={height}
      viewBox={`${-panOffset.x} ${-panOffset.y} ${width / zoomLevel} ${height / zoomLevel}`}
      className={`border border-border rounded-lg bg-white ${className}`}
      role="img"
      aria-label="Factory floor map"
    >
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="9"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8" />
        </marker>
      </defs>

      {showGrid && renderGrid()}
      {showConnections && renderConnections()}
      {renderOrderPath()}
      {cells.map(renderCell)}
    </svg>
  );
}

// =============================================================================
// CELL DETAIL PANEL
// =============================================================================

export interface CellDetailPanelProps {
  className?: string;
}

export function CellDetailPanel({ className = '' }: CellDetailPanelProps) {
  const { selectedCell, selectCell, updateCellStatus } = useFactoryMap();

  if (!selectedCell) {
    return (
      <div className={`p-4 bg-card border border-border rounded-lg ${className}`}>
        <p className="text-muted-foreground text-sm">Select a cell to view details</p>
      </div>
    );
  }

  const statusColors = CELL_STATUS_COLORS[selectedCell.status];

  return (
    <div className={`p-4 bg-card border border-border rounded-lg space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{selectedCell.name}</h3>
        <button
          onClick={() => selectCell(null)}
          className="p-1 hover:bg-muted rounded"
          aria-label="Close panel"
        >
          ✕
        </button>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Type:</span>
          <span className="text-sm font-medium capitalize">{selectedCell.type}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          <span
            className="px-2 py-0.5 rounded text-xs font-medium"
            style={{ backgroundColor: statusColors.fill, color: '#374151' }}
          >
            {statusColors.text}
          </span>
        </div>

        {selectedCell.metrics && (
          <>
            {selectedCell.metrics.throughput !== undefined && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Throughput:</span>
                <span className="text-sm font-medium">{selectedCell.metrics.throughput} units/hr</span>
              </div>
            )}
            {selectedCell.metrics.efficiency !== undefined && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Efficiency:</span>
                <span className="text-sm font-medium">{selectedCell.metrics.efficiency}%</span>
              </div>
            )}
            {selectedCell.metrics.currentJob && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Current Job:</span>
                <span className="text-sm font-medium">{selectedCell.metrics.currentJob}</span>
              </div>
            )}
            {selectedCell.metrics.operator && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Operator:</span>
                <span className="text-sm font-medium">{selectedCell.metrics.operator}</span>
              </div>
            )}
          </>
        )}

        <div className="pt-2 border-t border-border">
          <span className="text-sm text-muted-foreground block mb-2">Change Status:</span>
          <div className="flex flex-wrap gap-1">
            {(Object.keys(CELL_STATUS) as CellStatus[]).map((status) => (
              <button
                key={status}
                onClick={() => updateCellStatus(selectedCell.id, status)}
                className={`px-2 py-1 text-xs rounded border transition-colors ${
                  selectedCell.status === status
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:bg-muted'
                }`}
                style={{
                  backgroundColor:
                    selectedCell.status === status ? CELL_STATUS_COLORS[status].fill : undefined,
                }}
              >
                {CELL_STATUS_COLORS[status].text}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// GEMBA PATH VISUALIZER
// =============================================================================

export interface GembaPathVisualizerProps {
  path: OrderPath;
  onClose?: () => void;
  className?: string;
}

export function GembaPathVisualizer({ path, onClose, className = '' }: GembaPathVisualizerProps) {
  const { showOrderPath } = useFactoryMap();

  useEffect(() => {
    showOrderPath(path);
    return () => showOrderPath(null);
  }, [path, showOrderPath]);

  const wastePercentage = path.totalProcessTime > 0
    ? ((path.totalTravelTime / (path.totalTravelTime + path.totalProcessTime)) * 100).toFixed(1)
    : 0;

  return (
    <div className={`p-4 bg-card border border-border rounded-lg ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Order Path: {path.orderName}</h3>
          <p className="text-sm text-muted-foreground">ID: {path.orderId}</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded"
            aria-label="Close path view"
          >
            ✕
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4 p-3 bg-muted rounded-lg">
        <div className="text-center">
          <div className="text-2xl font-bold text-primary">
            {path.totalProcessTime} min
          </div>
          <div className="text-xs text-muted-foreground">Process Time</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-warning">
            {path.totalTravelTime} min
          </div>
          <div className="text-xs text-muted-foreground">Travel/Wait (Waste)</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-destructive">
            {wastePercentage}%
          </div>
          <div className="text-xs text-muted-foreground">Waste Ratio</div>
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-medium">Path Steps:</h4>
        <div className="space-y-1">
          {path.steps.map((step, index) => (
            <div
              key={`${step.cellId}-${index}`}
              className="flex items-center gap-2 p-2 rounded bg-muted/50"
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  step.status === 'completed'
                    ? 'bg-success'
                    : step.status === 'current'
                      ? 'bg-primary'
                      : 'bg-muted-foreground'
                }`}
              />
              <span className="text-sm flex-1">{step.cellName}</span>
              {step.duration !== undefined && (
                <span className="text-xs text-muted-foreground">{step.duration} min</span>
              )}
              {step.travelTime !== undefined && step.travelTime > 0 && (
                <span className="text-xs text-warning">+{step.travelTime} min travel</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// EXECUTIVE WAR ROOM TYPES
// =============================================================================

export type WarRoomPanel = 'kpi' | 'pipeline' | 'production' | 'quality' | 'alerts' | 'timeline';

export interface WarRoomPanelConfig {
  id: WarRoomPanel;
  title: string;
  icon: string;
  span: { cols: number; rows: number };
  priority: 'high' | 'medium' | 'low';
}

export const DEFAULT_WAR_ROOM_LAYOUT: WarRoomPanelConfig[] = [
  { id: 'kpi', title: 'Key Performance Indicators', icon: '📊', span: { cols: 2, rows: 1 }, priority: 'high' },
  { id: 'pipeline', title: 'Sales Pipeline', icon: '📈', span: { cols: 1, rows: 1 }, priority: 'medium' },
  { id: 'production', title: 'Production Status', icon: '🏭', span: { cols: 1, rows: 1 }, priority: 'high' },
  { id: 'quality', title: 'Quality Metrics', icon: '✅', span: { cols: 1, rows: 1 }, priority: 'medium' },
  { id: 'alerts', title: 'Active Alerts', icon: '⚠️', span: { cols: 1, rows: 1 }, priority: 'high' },
  { id: 'timeline', title: 'Today\'s Timeline', icon: '📅', span: { cols: 2, rows: 1 }, priority: 'low' },
];

// =============================================================================
// EXECUTIVE WAR ROOM CONTEXT
// =============================================================================

export interface WarRoomContextValue {
  layout: WarRoomPanelConfig[];
  isFullscreen: boolean;
  setFullscreen: (value: boolean) => void;
  activePanel: WarRoomPanel | null;
  setActivePanel: (panel: WarRoomPanel | null) => void;
  refreshInterval: number;
  setRefreshInterval: (ms: number) => void;
  lastRefresh: Date | null;
  refreshNow: () => void;
}

const WarRoomContext = createContext<WarRoomContextValue | null>(null);

export interface WarRoomProviderProps {
  children: React.ReactNode;
  layout?: WarRoomPanelConfig[];
  defaultRefreshInterval?: number;
  onRefresh?: () => void;
}

export function WarRoomProvider({
  children,
  layout = DEFAULT_WAR_ROOM_LAYOUT,
  defaultRefreshInterval = 30000,
  onRefresh,
}: WarRoomProviderProps) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activePanel, setActivePanel] = useState<WarRoomPanel | null>(null);
  const [refreshInterval, setRefreshInterval] = useState(defaultRefreshInterval);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const refreshNow = useCallback(() => {
    setLastRefresh(new Date());
    onRefresh?.();
  }, [onRefresh]);

  // Auto-refresh
  useEffect(() => {
    if (refreshInterval <= 0) return;

    const interval = setInterval(refreshNow, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval, refreshNow]);

  // Handle fullscreen toggle
  useEffect(() => {
    const handleFullscreen = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreen);
    return () => document.removeEventListener('fullscreenchange', handleFullscreen);
  }, []);

  const setFullscreen = useCallback((value: boolean) => {
    if (value && !document.fullscreenElement) {
      document.documentElement.requestFullscreen?.();
    } else if (!value && document.fullscreenElement) {
      document.exitFullscreen?.();
    }
    setIsFullscreen(value);
  }, []);

  const value = useMemo<WarRoomContextValue>(
    () => ({
      layout,
      isFullscreen,
      setFullscreen,
      activePanel,
      setActivePanel,
      refreshInterval,
      setRefreshInterval,
      lastRefresh,
      refreshNow,
    }),
    [layout, isFullscreen, setFullscreen, activePanel, refreshInterval, lastRefresh, refreshNow]
  );

  return (
    <WarRoomContext.Provider value={value}>{children}</WarRoomContext.Provider>
  );
}

export function useWarRoom(): WarRoomContextValue {
  const context = useContext(WarRoomContext);
  if (!context) {
    throw new Error('useWarRoom must be used within a WarRoomProvider');
  }
  return context;
}

// =============================================================================
// WAR ROOM PANEL COMPONENT
// =============================================================================

export interface WarRoomPanelContainerProps {
  config: WarRoomPanelConfig;
  children: React.ReactNode;
  onExpand?: () => void;
  className?: string;
}

export function WarRoomPanelContainer({
  config,
  children,
  onExpand,
  className = '',
}: WarRoomPanelContainerProps) {
  const { activePanel, setActivePanel } = useWarRoom();
  const isActive = activePanel === config.id;

  const handleExpand = () => {
    if (isActive) {
      setActivePanel(null);
    } else {
      setActivePanel(config.id);
      onExpand?.();
    }
  };

  const priorityColors = {
    high: 'border-l-4 border-l-primary',
    medium: 'border-l-4 border-l-warning',
    low: 'border-l-4 border-l-muted-foreground',
  };

  return (
    <div
      className={`bg-card border border-border rounded-lg overflow-hidden ${priorityColors[config.priority]} ${
        isActive ? 'ring-2 ring-primary' : ''
      } ${className}`}
      style={{
        gridColumn: isActive ? '1 / -1' : `span ${config.span.cols}`,
        gridRow: isActive ? '1 / -1' : `span ${config.span.rows}`,
      }}
    >
      <div className="flex items-center justify-between p-3 border-b border-border bg-muted/50">
        <div className="flex items-center gap-2">
          <span className="text-lg">{config.icon}</span>
          <h3 className="font-semibold text-sm">{config.title}</h3>
        </div>
        <button
          onClick={handleExpand}
          className="p-1 hover:bg-muted rounded text-xs"
          aria-label={isActive ? 'Collapse panel' : 'Expand panel'}
        >
          {isActive ? '⊟' : '⊞'}
        </button>
      </div>
      <div className="p-3 h-full overflow-auto">{children}</div>
    </div>
  );
}

// =============================================================================
// WAR ROOM DASHBOARD
// =============================================================================

export interface WarRoomDashboardProps {
  className?: string;
  children?: React.ReactNode;
}

export function WarRoomDashboard({ className = '', children }: WarRoomDashboardProps) {
  const { isFullscreen, setFullscreen, refreshInterval, setRefreshInterval, lastRefresh, refreshNow } =
    useWarRoom();

  return (
    <div
      className={`flex flex-col h-full ${isFullscreen ? 'fixed inset-0 z-50 bg-background' : ''} ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-card">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold">🏢 Executive War Room</h1>
          {lastRefresh && (
            <span className="text-xs text-muted-foreground">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
            className="text-sm px-2 py-1 border border-border rounded bg-background"
            aria-label="Refresh interval"
          >
            <option value={10000}>10s</option>
            <option value={30000}>30s</option>
            <option value={60000}>1m</option>
            <option value={300000}>5m</option>
            <option value={0}>Manual</option>
          </select>
          <button
            onClick={refreshNow}
            className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded hover:opacity-90"
          >
            Refresh
          </button>
          <button
            onClick={() => setFullscreen(!isFullscreen)}
            className="px-3 py-1 text-sm border border-border rounded hover:bg-muted"
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            {isFullscreen ? '⊟ Exit' : '⊞ Fullscreen'}
          </button>
        </div>
      </div>

      {/* Panel Grid */}
      <div className="flex-1 p-4 overflow-auto">
        <div
          className="grid gap-4"
          style={{
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gridAutoRows: 'minmax(200px, auto)',
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// KPI PANEL CONTENT
// =============================================================================

export interface KPIData {
  label: string;
  value: string | number;
  unit?: string;
  change?: number; // percentage change
  target?: number;
  status?: 'good' | 'warning' | 'critical';
}

export interface KPIPanelProps {
  kpis: KPIData[];
  columns?: number;
  className?: string;
}

export function KPIPanel({ kpis, columns = 4, className = '' }: KPIPanelProps) {
  const getStatusColor = (status?: KPIData['status']) => {
    switch (status) {
      case 'good':
        return 'text-success';
      case 'warning':
        return 'text-warning';
      case 'critical':
        return 'text-destructive';
      default:
        return 'text-foreground';
    }
  };

  return (
    <div
      className={`grid gap-4 ${className}`}
      style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
    >
      {kpis.map((kpi) => (
        <div key={kpi.label} className="p-3 bg-muted/50 rounded-lg">
          <div className="text-xs text-muted-foreground mb-1">{kpi.label}</div>
          <div className={`text-2xl font-bold ${getStatusColor(kpi.status)}`}>
            {kpi.value}
            {kpi.unit && <span className="text-sm font-normal ml-1">{kpi.unit}</span>}
          </div>
          {kpi.change !== undefined && (
            <div
              className={`text-xs ${kpi.change >= 0 ? 'text-success' : 'text-destructive'}`}
            >
              {kpi.change >= 0 ? '↑' : '↓'} {Math.abs(kpi.change)}%
            </div>
          )}
          {kpi.target !== undefined && (
            <div className="text-xs text-muted-foreground mt-1">
              Target: {kpi.target}
              {kpi.unit}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// ALERT PANEL CONTENT
// =============================================================================

export interface AlertData {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  source?: string;
}

export interface AlertsPanelProps {
  alerts: AlertData[];
  maxItems?: number;
  onAcknowledge?: (id: string) => void;
  className?: string;
}

export function AlertsPanel({
  alerts,
  maxItems = 10,
  onAcknowledge,
  className = '',
}: AlertsPanelProps) {
  const displayAlerts = alerts.slice(0, maxItems);

  const severityIcons = {
    critical: '🔴',
    warning: '🟡',
    info: '🔵',
  };

  const severityColors = {
    critical: 'bg-destructive/10 border-destructive/20',
    warning: 'bg-warning/10 border-warning/20',
    info: 'bg-primary/10 border-primary/20',
  };

  if (alerts.length === 0) {
    return (
      <div className={`flex items-center justify-center h-32 text-muted-foreground ${className}`}>
        ✅ No active alerts
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {displayAlerts.map((alert) => (
        <div
          key={alert.id}
          className={`p-3 rounded-lg border ${severityColors[alert.severity]}`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-start gap-2">
              <span className="text-lg">{severityIcons[alert.severity]}</span>
              <div>
                <div className="font-medium text-sm">{alert.title}</div>
                <div className="text-xs text-muted-foreground">{alert.message}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {alert.timestamp.toLocaleTimeString()}
                  {alert.source && ` • ${alert.source}`}
                </div>
              </div>
            </div>
            {onAcknowledge && (
              <button
                onClick={() => onAcknowledge(alert.id)}
                className="text-xs px-2 py-1 border border-border rounded hover:bg-muted"
                aria-label={`Acknowledge alert: ${alert.title}`}
              >
                ACK
              </button>
            )}
          </div>
        </div>
      ))}
      {alerts.length > maxItems && (
        <div className="text-center text-xs text-muted-foreground">
          +{alerts.length - maxItems} more alerts
        </div>
      )}
    </div>
  );
}

// =============================================================================
// TIMELINE PANEL CONTENT
// =============================================================================

export interface TimelineEvent {
  id: string;
  time: Date;
  title: string;
  type: 'meeting' | 'deadline' | 'milestone' | 'task' | 'other';
  completed?: boolean;
}

export interface TimelinePanelProps {
  events: TimelineEvent[];
  showPastEvents?: boolean;
  className?: string;
}

export function TimelinePanel({
  events,
  showPastEvents = true,
  className = '',
}: TimelinePanelProps) {
  const now = new Date();

  const filteredEvents = showPastEvents
    ? events
    : events.filter((e) => e.time >= now || e.completed);

  const sortedEvents = [...filteredEvents].sort((a, b) => a.time.getTime() - b.time.getTime());

  const typeIcons = {
    meeting: '👥',
    deadline: '⏰',
    milestone: '🎯',
    task: '✓',
    other: '•',
  };

  if (sortedEvents.length === 0) {
    return (
      <div className={`flex items-center justify-center h-32 text-muted-foreground ${className}`}>
        📅 No events scheduled
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-border" />
      <div className="space-y-3">
        {sortedEvents.map((event) => {
          const isPast = event.time < now;
          const isSoon = !isPast && event.time.getTime() - now.getTime() < 3600000; // 1 hour

          return (
            <div key={event.id} className="relative pl-8">
              <div
                className={`absolute left-1.5 w-4 h-4 rounded-full border-2 border-background ${
                  event.completed
                    ? 'bg-success'
                    : isPast
                      ? 'bg-muted-foreground'
                      : isSoon
                        ? 'bg-warning'
                        : 'bg-primary'
                }`}
              />
              <div
                className={`p-2 rounded-lg ${
                  event.completed ? 'bg-muted/30' : isPast ? 'bg-muted/50' : 'bg-muted'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm">{typeIcons[event.type]}</span>
                  <span className="text-xs font-mono text-muted-foreground">
                    {event.time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                  {event.completed && <span className="text-xs text-success">✓</span>}
                </div>
                <div
                  className={`text-sm ${event.completed ? 'line-through text-muted-foreground' : ''}`}
                >
                  {event.title}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// MAP CONTROLS
// =============================================================================

export interface MapControlsProps {
  className?: string;
}

export function MapControls({ className = '' }: MapControlsProps) {
  const { zoomLevel, setZoomLevel, panOffset, setPanOffset } = useFactoryMap();

  const handleZoomIn = () => setZoomLevel(Math.min(zoomLevel + 0.25, 3));
  const handleZoomOut = () => setZoomLevel(Math.max(zoomLevel - 0.25, 0.5));
  const handleResetView = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  return (
    <div className={`flex items-center gap-1 p-1 bg-card border border-border rounded-lg ${className}`}>
      <button
        onClick={handleZoomOut}
        className="p-2 hover:bg-muted rounded"
        aria-label="Zoom out"
        disabled={zoomLevel <= 0.5}
      >
        −
      </button>
      <span className="px-2 text-sm font-mono min-w-12 text-center">{(zoomLevel * 100).toFixed(0)}%</span>
      <button
        onClick={handleZoomIn}
        className="p-2 hover:bg-muted rounded"
        aria-label="Zoom in"
        disabled={zoomLevel >= 3}
      >
        +
      </button>
      <div className="w-px h-6 bg-border mx-1" />
      <button
        onClick={handleResetView}
        className="p-2 hover:bg-muted rounded text-sm"
        aria-label="Reset view"
      >
        ⟲
      </button>
    </div>
  );
}

// =============================================================================
// CELL STATUS LEGEND
// =============================================================================

export interface CellStatusLegendProps {
  className?: string;
}

export function CellStatusLegend({ className = '' }: CellStatusLegendProps) {
  return (
    <div className={`flex flex-wrap gap-3 p-2 bg-card border border-border rounded-lg ${className}`}>
      {(Object.keys(CELL_STATUS) as CellStatus[]).map((status) => {
        const colors = CELL_STATUS_COLORS[status];
        return (
          <div key={status} className="flex items-center gap-1.5">
            <div
              className="w-4 h-4 rounded border"
              style={{ backgroundColor: colors.fill, borderColor: colors.stroke }}
            />
            <span className="text-xs text-muted-foreground">{colors.text}</span>
          </div>
        );
      })}
    </div>
  );
}

// =============================================================================
// EXPORTS
// =============================================================================

export { FactoryMapContext, WarRoomContext };
