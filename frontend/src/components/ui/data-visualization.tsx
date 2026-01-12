/**
 * Data Visualization & Executive Reporting UX Components
 * 
 * Section 19.7: Data Visualization & Executive Reporting UX
 * 
 * Provides visualization components for dashboards and reports:
 * - Interactive charts with drill-down
 * - Tooltips and legends
 * - Sparklines for trend analysis
 * - Export capabilities
 * - Color semantics and accessibility
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
 * Semantic color palette for KPIs
 * Ensures consistent colors across all dashboards
 */
export const KPI_COLORS = {
  MARGIN: '#8B5CF6',      // Purple - always represents margin
  REVENUE: '#10B981',     // Green - always represents revenue
  COST: '#EF4444',        // Red - always represents cost
  VOLUME: '#3B82F6',      // Blue - always represents volume
  TIME: '#F59E0B',        // Amber - always represents time metrics
  EFFICIENCY: '#06B6D4',  // Cyan - always represents efficiency
  QUALITY: '#EC4899',     // Pink - always represents quality
  NEUTRAL: '#6B7280',     // Gray - neutral/comparison
} as const;

/**
 * Chart types supported
 */
export const CHART_TYPE = {
  BAR: 'bar',
  LINE: 'line',
  PIE: 'pie',
  DONUT: 'donut',
  AREA: 'area',
  SCATTER: 'scatter',
  SPARKLINE: 'sparkline',
} as const;

export type ChartType = (typeof CHART_TYPE)[keyof typeof CHART_TYPE];

/**
 * Export formats
 */
export const EXPORT_FORMAT = {
  PNG: 'png',
  PDF: 'pdf',
  SVG: 'svg',
  CSV: 'csv',
} as const;

export type ExportFormat = (typeof EXPORT_FORMAT)[keyof typeof EXPORT_FORMAT];

// =============================================================================
// TYPES
// =============================================================================

export interface DataPoint {
  label: string;
  value: number;
  color?: string;
  metadata?: Record<string, unknown>;
}

export interface Series {
  name: string;
  data: number[];
  color: string;
  visible?: boolean;
}

export interface ChartConfig {
  title?: string;
  subtitle?: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  showLegend?: boolean;
  showTooltip?: boolean;
  zeroBaseline?: boolean;
  animate?: boolean;
}

interface DrilldownContextValue {
  currentLevel: number;
  breadcrumbs: string[];
  drillDown: (label: string, data: DataPoint[]) => void;
  drillUp: () => void;
  resetDrilldown: () => void;
}

// =============================================================================
// DRILLDOWN CONTEXT
// =============================================================================

const DrilldownContext = createContext<DrilldownContextValue | null>(null);

export interface DrilldownProviderProps {
  children: ReactNode;
  onDrillDown?: (label: string, level: number) => void;
}

/**
 * Provider for chart drill-down functionality
 */
export function DrilldownProvider({
  children,
  onDrillDown,
}: DrilldownProviderProps) {
  const [currentLevel, setCurrentLevel] = useState(0);
  const [breadcrumbs, setBreadcrumbs] = useState<string[]>(['Overview']);
  const [dataStack, setDataStack] = useState<DataPoint[][]>([]);

  const drillDown = useCallback(
    (label: string, data: DataPoint[]) => {
      setCurrentLevel((prev) => prev + 1);
      setBreadcrumbs((prev) => [...prev, label]);
      setDataStack((prev) => [...prev, data]);
      onDrillDown?.(label, currentLevel + 1);
    },
    [currentLevel, onDrillDown]
  );

  const drillUp = useCallback(() => {
    if (currentLevel > 0) {
      setCurrentLevel((prev) => prev - 1);
      setBreadcrumbs((prev) => prev.slice(0, -1));
      setDataStack((prev) => prev.slice(0, -1));
    }
  }, [currentLevel]);

  const resetDrilldown = useCallback(() => {
    setCurrentLevel(0);
    setBreadcrumbs(['Overview']);
    setDataStack([]);
  }, []);

  const value: DrilldownContextValue = {
    currentLevel,
    breadcrumbs,
    drillDown,
    drillUp,
    resetDrilldown,
  };

  return (
    <DrilldownContext.Provider value={value}>
      {children}
    </DrilldownContext.Provider>
  );
}

/**
 * Hook to access drill-down functionality
 */
export function useDrilldown(): DrilldownContextValue {
  const context = useContext(DrilldownContext);
  if (!context) {
    throw new Error('useDrilldown must be used within DrilldownProvider');
  }
  return context;
}

// =============================================================================
// BREADCRUMB NAVIGATION
// =============================================================================

export interface DrilldownBreadcrumbsProps {
  className?: string;
}

/**
 * Breadcrumb navigation for drill-down charts
 */
export function DrilldownBreadcrumbs({ className = '' }: DrilldownBreadcrumbsProps) {
  const { breadcrumbs, drillUp, resetDrilldown, currentLevel } = useDrilldown();

  if (currentLevel === 0) {
    return null;
  }

  return (
    <nav
      className={`flex items-center gap-2 text-sm ${className}`}
      aria-label="Chart drill-down navigation"
    >
      <button
        type="button"
        onClick={resetDrilldown}
        className="text-blue-600 hover:text-blue-800 hover:underline"
      >
        {breadcrumbs[0]}
      </button>
      {breadcrumbs.slice(1).map((crumb, index) => (
        <React.Fragment key={index}>
          <span className="text-gray-400" aria-hidden="true">
            /
          </span>
          {index < breadcrumbs.length - 2 ? (
            <button
              type="button"
              onClick={() => {
                // Drill up to this level
                for (let i = 0; i < breadcrumbs.length - index - 2; i++) {
                  drillUp();
                }
              }}
              className="text-blue-600 hover:text-blue-800 hover:underline"
            >
              {crumb}
            </button>
          ) : (
            <span className="text-gray-900 font-medium">{crumb}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}

// =============================================================================
// TOOLTIP COMPONENT
// =============================================================================

export interface TooltipProps {
  visible: boolean;
  x: number;
  y: number;
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  className?: string;
}

/**
 * Chart tooltip with smart positioning
 */
export function ChartTooltip({
  visible,
  x,
  y,
  title,
  value,
  subtitle,
  color,
  className = '',
}: TooltipProps) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ left: x, top: y });

  // Smart positioning to avoid edge overflow
  useEffect(() => {
    if (tooltipRef.current && visible) {
      const rect = tooltipRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      let left = x + 10;
      let top = y - 10;

      // Prevent right overflow
      if (left + rect.width > viewportWidth - 20) {
        left = x - rect.width - 10;
      }

      // Prevent bottom overflow
      if (top + rect.height > viewportHeight - 20) {
        top = y - rect.height - 10;
      }

      // Prevent top overflow
      if (top < 10) {
        top = 10;
      }

      setPosition({ left, top });
    }
  }, [x, y, visible]);

  if (!visible) return null;

  return (
    <div
      ref={tooltipRef}
      className={`
        absolute z-50 px-3 py-2 bg-gray-900 text-white rounded-lg shadow-lg
        pointer-events-none text-sm max-w-xs
        ${className}
      `}
      style={{ left: position.left, top: position.top }}
      role="tooltip"
    >
      <div className="flex items-center gap-2">
        {color && (
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: color }}
            aria-hidden="true"
          />
        )}
        <span className="font-medium">{title}</span>
      </div>
      <div className="text-lg font-bold mt-1">{value}</div>
      {subtitle && (
        <div className="text-gray-400 text-xs mt-1">{subtitle}</div>
      )}
    </div>
  );
}

// =============================================================================
// LEGEND COMPONENT
// =============================================================================

export interface LegendItem {
  name: string;
  color: string;
  visible: boolean;
}

export interface ChartLegendProps {
  items: LegendItem[];
  onToggle: (name: string) => void;
  orientation?: 'horizontal' | 'vertical';
  className?: string;
}

/**
 * Interactive chart legend with toggle capability
 */
export function ChartLegend({
  items,
  onToggle,
  orientation = 'horizontal',
  className = '',
}: ChartLegendProps) {
  const orientationClasses = {
    horizontal: 'flex-row flex-wrap',
    vertical: 'flex-col',
  };

  return (
    <div
      className={`flex gap-3 ${orientationClasses[orientation]} ${className}`}
      role="group"
      aria-label="Chart legend"
    >
      {items.map((item) => (
        <button
          key={item.name}
          type="button"
          onClick={() => onToggle(item.name)}
          className={`
            flex items-center gap-2 px-2 py-1 rounded text-sm transition-opacity
            hover:bg-gray-100
            ${item.visible ? 'opacity-100' : 'opacity-50'}
          `}
          aria-pressed={item.visible}
          aria-label={`${item.visible ? 'Hide' : 'Show'} ${item.name} series`}
        >
          <div
            className={`w-3 h-3 rounded-full ${item.visible ? '' : 'opacity-50'}`}
            style={{ backgroundColor: item.color }}
            aria-hidden="true"
          />
          <span className={item.visible ? '' : 'line-through'}>{item.name}</span>
        </button>
      ))}
    </div>
  );
}

// =============================================================================
// SPARKLINE COMPONENT
// =============================================================================

export interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  showDot?: boolean;
  showArea?: boolean;
  className?: string;
  ariaLabel?: string;
}

/**
 * Compact sparkline for inline trend visualization
 */
export function Sparkline({
  data,
  width = 100,
  height = 24,
  color = KPI_COLORS.NEUTRAL,
  showDot = true,
  showArea = false,
  className = '',
  ariaLabel = 'Trend chart',
}: SparklineProps) {
  if (data.length === 0) {
    return (
      <div
        className={`inline-block ${className}`}
        style={{ width, height }}
        role="img"
        aria-label={ariaLabel}
      >
        <span className="text-gray-400 text-xs">No data</span>
      </div>
    );
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const padding = 2;

  // Generate SVG path
  const points = data.map((value, index) => {
    const x = (index / (data.length - 1 || 1)) * (width - padding * 2) + padding;
    const y = height - ((value - min) / range) * (height - padding * 2) - padding;
    return { x, y };
  });

  const linePath = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ');

  const areaPath = `${linePath} L ${points[points.length - 1].x} ${height - padding} L ${padding} ${height - padding} Z`;

  const lastPoint = points[points.length - 1];
  const trend = data.length > 1 ? data[data.length - 1] - data[0] : 0;

  return (
    <svg
      width={width}
      height={height}
      className={className}
      role="img"
      aria-label={`${ariaLabel}: ${trend >= 0 ? 'up' : 'down'} ${Math.abs(trend).toFixed(1)}`}
    >
      {showArea && (
        <path d={areaPath} fill={color} fillOpacity={0.1} />
      )}
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {showDot && lastPoint && (
        <circle cx={lastPoint.x} cy={lastPoint.y} r={3} fill={color} />
      )}
    </svg>
  );
}

// =============================================================================
// BAR CHART COMPONENT
// =============================================================================

export interface BarChartProps {
  data: DataPoint[];
  config?: ChartConfig;
  onBarClick?: (point: DataPoint, index: number) => void;
  horizontal?: boolean;
  className?: string;
}

/**
 * Simple bar chart with zero baseline enforcement
 */
export function BarChart({
  data,
  config = {},
  onBarClick,
  horizontal = false,
  className = '',
}: BarChartProps) {
  const {
    title,
    subtitle,
    zeroBaseline = true, // Always enforce zero baseline by default
    showTooltip = true,
  } = config;

  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  const maxValue = Math.max(...data.map((d) => d.value), 0);
  const minValue = zeroBaseline ? 0 : Math.min(...data.map((d) => d.value), 0);
  const range = maxValue - minValue || 1;

  const handleBarMouseEnter = (index: number, event: React.MouseEvent) => {
    setHoveredIndex(index);
    setTooltipPosition({ x: event.clientX, y: event.clientY });
  };

  const handleBarMouseLeave = () => {
    setHoveredIndex(null);
  };

  const handleBarClick = (point: DataPoint, index: number) => {
    onBarClick?.(point, index);
  };

  return (
    <div className={`relative ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
      )}
      {subtitle && (
        <p className="text-sm text-gray-600 mb-4">{subtitle}</p>
      )}
      
      <div
        className={`flex ${horizontal ? 'flex-col' : 'flex-row items-end'} gap-2`}
        role="img"
        aria-label={title || 'Bar chart'}
      >
        {data.map((point, index) => {
          const percentage = ((point.value - minValue) / range) * 100;
          const color = point.color || KPI_COLORS.NEUTRAL;

          return (
            <div
              key={index}
              className={`
                ${horizontal ? 'flex items-center gap-2' : 'flex flex-col items-center flex-1'}
              `}
            >
              {horizontal ? (
                <>
                  <span className="text-xs text-gray-600 w-20 truncate">
                    {point.label}
                  </span>
                  <button
                    type="button"
                    className={`
                      h-6 rounded transition-all duration-200
                      ${onBarClick ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}
                    `}
                    style={{
                      width: `${percentage}%`,
                      minWidth: 4,
                      maxWidth: '100%',
                      backgroundColor: color,
                    }}
                    onMouseEnter={(e) => handleBarMouseEnter(index, e)}
                    onMouseLeave={handleBarMouseLeave}
                    onClick={() => handleBarClick(point, index)}
                    aria-label={`${point.label}: ${point.value}`}
                  />
                </>
              ) : (
                <>
                  <button
                    type="button"
                    className={`
                      w-full rounded-t transition-all duration-200
                      ${onBarClick ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}
                    `}
                    style={{
                      height: `${percentage}%`,
                      minHeight: 4,
                      backgroundColor: color,
                    }}
                    onMouseEnter={(e) => handleBarMouseEnter(index, e)}
                    onMouseLeave={handleBarMouseLeave}
                    onClick={() => handleBarClick(point, index)}
                    aria-label={`${point.label}: ${point.value}`}
                  />
                  <span className="text-xs text-gray-600 mt-1 truncate max-w-full">
                    {point.label}
                  </span>
                </>
              )}
            </div>
          );
        })}
      </div>

      {showTooltip && hoveredIndex !== null && (
        <ChartTooltip
          visible
          x={tooltipPosition.x}
          y={tooltipPosition.y}
          title={data[hoveredIndex].label}
          value={data[hoveredIndex].value}
          color={data[hoveredIndex].color}
        />
      )}
    </div>
  );
}

// =============================================================================
// DONUT CHART COMPONENT
// =============================================================================

export interface DonutChartProps {
  data: DataPoint[];
  size?: number;
  thickness?: number;
  onSegmentClick?: (point: DataPoint, index: number) => void;
  showLegend?: boolean;
  className?: string;
}

/**
 * Donut chart with interactive segments
 */
export function DonutChart({
  data,
  size = 200,
  thickness = 40,
  onSegmentClick,
  showLegend = true,
  className = '',
}: DonutChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [legendItems, setLegendItems] = useState<LegendItem[]>(
    data.map((d) => ({ name: d.label, color: d.color || KPI_COLORS.NEUTRAL, visible: true }))
  );

  const total = data.reduce((sum, d) => sum + d.value, 0);
  const radius = size / 2;
  const innerRadius = radius - thickness;

  // Generate segments
  let currentAngle = -90; // Start at top
  const segments = data.map((point, index) => {
    const isVisible = legendItems.find((l) => l.name === point.label)?.visible ?? true;
    const percentage = total > 0 ? (point.value / total) * 100 : 0;
    const angle = isVisible ? (percentage / 100) * 360 : 0;
    const startAngle = currentAngle;
    currentAngle += angle;
    const endAngle = currentAngle;

    return {
      ...point,
      percentage,
      startAngle,
      endAngle,
      isVisible,
    };
  });

  const handleLegendToggle = (name: string) => {
    setLegendItems((items) =>
      items.map((item) =>
        item.name === name ? { ...item, visible: !item.visible } : item
      )
    );
  };

  const createArcPath = (
    startAngle: number,
    endAngle: number,
    outerR: number,
    innerR: number
  ) => {
    const startOuter = polarToCartesian(radius, radius, outerR, startAngle);
    const endOuter = polarToCartesian(radius, radius, outerR, endAngle);
    const startInner = polarToCartesian(radius, radius, innerR, endAngle);
    const endInner = polarToCartesian(radius, radius, innerR, startAngle);

    const largeArc = endAngle - startAngle > 180 ? 1 : 0;

    return `
      M ${startOuter.x} ${startOuter.y}
      A ${outerR} ${outerR} 0 ${largeArc} 1 ${endOuter.x} ${endOuter.y}
      L ${startInner.x} ${startInner.y}
      A ${innerR} ${innerR} 0 ${largeArc} 0 ${endInner.x} ${endInner.y}
      Z
    `;
  };

  return (
    <div className={`flex flex-col items-center gap-4 ${className}`}>
      <svg
        width={size}
        height={size}
        role="img"
        aria-label="Donut chart"
      >
        {segments.map((segment, index) => {
          if (!segment.isVisible || segment.percentage === 0) return null;

          const color = segment.color || KPI_COLORS.NEUTRAL;
          const isHovered = hoveredIndex === index;

          return (
            <path
              key={index}
              d={createArcPath(
                segment.startAngle,
                segment.endAngle,
                isHovered ? radius : radius - 2,
                isHovered ? innerRadius - 4 : innerRadius
              )}
              fill={color}
              className={`
                transition-all duration-200
                ${onSegmentClick ? 'cursor-pointer' : ''}
              `}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
              onClick={() => onSegmentClick?.(segment, index)}
            />
          );
        })}
        
        {/* Center text */}
        {hoveredIndex !== null && segments[hoveredIndex].isVisible && (
          <text
            x={radius}
            y={radius}
            textAnchor="middle"
            dominantBaseline="middle"
            className="text-lg font-bold fill-gray-900"
          >
            {segments[hoveredIndex].percentage.toFixed(1)}%
          </text>
        )}
      </svg>

      {showLegend && (
        <ChartLegend
          items={legendItems}
          onToggle={handleLegendToggle}
          orientation="horizontal"
        />
      )}
    </div>
  );
}

function polarToCartesian(
  cx: number,
  cy: number,
  r: number,
  angle: number
): { x: number; y: number } {
  const radians = (angle * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(radians),
    y: cy + r * Math.sin(radians),
  };
}

// =============================================================================
// KPI CARD COMPONENT
// =============================================================================

export interface KPICardProps {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  trend?: number[];
  color?: string;
  icon?: ReactNode;
  onClick?: () => void;
  className?: string;
}

/**
 * KPI card with trend sparkline
 */
export function KPICard({
  label,
  value,
  change,
  changeLabel,
  trend,
  color = KPI_COLORS.NEUTRAL,
  icon,
  onClick,
  className = '',
}: KPICardProps) {
  const isPositive = change !== undefined && change >= 0;
  const changeColor = isPositive ? 'text-green-600' : 'text-red-600';

  return (
    <div
      className={`
        bg-white rounded-lg border border-gray-200 p-4 shadow-sm
        ${onClick ? 'cursor-pointer hover:shadow-md hover:border-gray-300 transition-shadow' : ''}
        ${className}
      `}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          onClick();
        }
      }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            {icon && (
              <span className="text-xl" aria-hidden="true">
                {icon}
              </span>
            )}
            <span className="text-sm text-gray-600">{label}</span>
          </div>
          <div className="flex items-baseline gap-2 mt-1">
            <span
              className="text-2xl font-bold"
              style={{ color }}
            >
              {value}
            </span>
            {change !== undefined && (
              <span className={`text-sm font-medium ${changeColor}`}>
                {isPositive ? '+' : ''}{change}%
                {changeLabel && <span className="text-gray-500 ml-1">{changeLabel}</span>}
              </span>
            )}
          </div>
        </div>
        {trend && trend.length > 0 && (
          <Sparkline
            data={trend}
            width={60}
            height={32}
            color={color}
            showArea
          />
        )}
      </div>
    </div>
  );
}

// =============================================================================
// EXPORT UTILITIES
// =============================================================================

export interface ChartExportButtonProps {
  chartRef: React.RefObject<HTMLElement>;
  filename?: string;
  formats?: ExportFormat[];
  className?: string;
}

/**
 * Export button for charts
 */
export function ChartExportButton({
  chartRef,
  filename = 'chart',
  formats = [EXPORT_FORMAT.PNG, EXPORT_FORMAT.PDF],
  className = '',
}: ChartExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleExport = async (format: ExportFormat) => {
    if (!chartRef.current) return;

    try {
      switch (format) {
        case EXPORT_FORMAT.PNG:
          await exportAsPNG(chartRef.current, filename);
          break;
        case EXPORT_FORMAT.PDF:
          await exportAsPDF(chartRef.current, filename);
          break;
        case EXPORT_FORMAT.SVG:
          exportAsSVG(chartRef.current, filename);
          break;
        case EXPORT_FORMAT.CSV:
          // CSV export would need data passed separately
          break;
      }
    } catch (error) {
      console.error('Export failed:', error);
    }

    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <span aria-hidden="true">📥</span>
        Export
      </button>

      {isOpen && (
        <div
          className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10"
          role="menu"
        >
          {formats.map((format) => (
            <button
              key={format}
              type="button"
              onClick={() => handleExport(format)}
              className="block w-full px-4 py-2 text-left text-sm hover:bg-gray-100 first:rounded-t-lg last:rounded-b-lg"
              role="menuitem"
            >
              Download as {format.toUpperCase()}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Export helper functions (simplified - would use html2canvas/jsPDF in production)
async function exportAsPNG(element: HTMLElement, filename: string) {
  // In production, use html2canvas
  // For now, trigger download dialog simulation
  const link = document.createElement('a');
  link.download = `${filename}.png`;
  // This would normally be a data URL from canvas
  alert('PNG export initiated (would use html2canvas in production)');
}

async function exportAsPDF(element: HTMLElement, filename: string) {
  // In production, use jsPDF
  alert('PDF export initiated (would use jsPDF in production)');
}

function exportAsSVG(element: HTMLElement, filename: string) {
  const svg = element.querySelector('svg');
  if (svg) {
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svg);
    const blob = new Blob([svgString], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}.svg`;
    link.click();
    URL.revokeObjectURL(url);
  }
}

// =============================================================================
// DEEP LINK SHARING
// =============================================================================

export interface ShareableDashboardConfig {
  filters?: Record<string, string>;
  timeRange?: { start: string; end: string };
  selectedMetrics?: string[];
  view?: string;
}

/**
 * Generate shareable URL for dashboard configuration
 */
export function generateDashboardUrl(
  baseUrl: string,
  config: ShareableDashboardConfig
): string {
  const params = new URLSearchParams();

  if (config.filters) {
    Object.entries(config.filters).forEach(([key, value]) => {
      params.set(`filter_${key}`, value);
    });
  }

  if (config.timeRange) {
    params.set('start', config.timeRange.start);
    params.set('end', config.timeRange.end);
  }

  if (config.selectedMetrics && config.selectedMetrics.length > 0) {
    params.set('metrics', config.selectedMetrics.join(','));
  }

  if (config.view) {
    params.set('view', config.view);
  }

  const queryString = params.toString();
  return queryString ? `${baseUrl}?${queryString}` : baseUrl;
}

/**
 * Parse dashboard configuration from URL
 */
export function parseDashboardUrl(url: string): ShareableDashboardConfig {
  const urlObj = new URL(url);
  const params = urlObj.searchParams;
  const config: ShareableDashboardConfig = {};

  // Extract filters
  const filters: Record<string, string> = {};
  params.forEach((value, key) => {
    if (key.startsWith('filter_')) {
      filters[key.replace('filter_', '')] = value;
    }
  });
  if (Object.keys(filters).length > 0) {
    config.filters = filters;
  }

  // Extract time range
  const start = params.get('start');
  const end = params.get('end');
  if (start && end) {
    config.timeRange = { start, end };
  }

  // Extract metrics
  const metrics = params.get('metrics');
  if (metrics) {
    config.selectedMetrics = metrics.split(',');
  }

  // Extract view
  const view = params.get('view');
  if (view) {
    config.view = view;
  }

  return config;
}

/**
 * Copy dashboard link to clipboard
 */
export async function shareDashboard(config: ShareableDashboardConfig): Promise<void> {
  const url = generateDashboardUrl(window.location.href.split('?')[0], config);
  await navigator.clipboard.writeText(url);
}

// =============================================================================
// EXPORTS
// =============================================================================

