/**
 * Tests for Data Visualization & Executive Reporting UX Components
 * 
 * Section 19.7: Data Visualization & Executive Reporting UX
 */

import React, { createRef } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  // Constants
  KPI_COLORS,
  CHART_TYPE,
  EXPORT_FORMAT,
  // Context
  DrilldownProvider,
  useDrilldown,
  DrilldownBreadcrumbs,
  // Tooltip
  ChartTooltip,
  // Legend
  ChartLegend,
  // Sparkline
  Sparkline,
  // Bar Chart
  BarChart,
  // Donut Chart
  DonutChart,
  // KPI Card
  KPICard,
  // Export
  ChartExportButton,
  // URL utilities
  generateDashboardUrl,
  parseDashboardUrl,
  shareDashboard,
  // Types
  DataPoint,
  LegendItem,
} from '../data-visualization';

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('Data Visualization Constants', () => {
  describe('KPI_COLORS', () => {
    it('should define all semantic colors', () => {
      expect(KPI_COLORS.MARGIN).toBe('#8B5CF6');
      expect(KPI_COLORS.REVENUE).toBe('#10B981');
      expect(KPI_COLORS.COST).toBe('#EF4444');
      expect(KPI_COLORS.VOLUME).toBe('#3B82F6');
      expect(KPI_COLORS.TIME).toBe('#F59E0B');
      expect(KPI_COLORS.EFFICIENCY).toBe('#06B6D4');
      expect(KPI_COLORS.QUALITY).toBe('#EC4899');
      expect(KPI_COLORS.NEUTRAL).toBe('#6B7280');
    });
  });

  describe('CHART_TYPE', () => {
    it('should define all chart types', () => {
      expect(CHART_TYPE.BAR).toBe('bar');
      expect(CHART_TYPE.LINE).toBe('line');
      expect(CHART_TYPE.PIE).toBe('pie');
      expect(CHART_TYPE.DONUT).toBe('donut');
      expect(CHART_TYPE.AREA).toBe('area');
      expect(CHART_TYPE.SCATTER).toBe('scatter');
      expect(CHART_TYPE.SPARKLINE).toBe('sparkline');
    });
  });

  describe('EXPORT_FORMAT', () => {
    it('should define all export formats', () => {
      expect(EXPORT_FORMAT.PNG).toBe('png');
      expect(EXPORT_FORMAT.PDF).toBe('pdf');
      expect(EXPORT_FORMAT.SVG).toBe('svg');
      expect(EXPORT_FORMAT.CSV).toBe('csv');
    });
  });
});

// =============================================================================
// DRILLDOWN CONTEXT TESTS
// =============================================================================

describe('DrilldownProvider', () => {
  // Helper component to test hook
  function DrilldownTester() {
    const { currentLevel, breadcrumbs, drillDown, drillUp, resetDrilldown } = useDrilldown();
    return (
      <div>
        <span data-testid="level">{currentLevel}</span>
        <span data-testid="breadcrumbs">{breadcrumbs.join(' / ')}</span>
        <button onClick={() => drillDown('Category A', [])}>Drill Down</button>
        <button onClick={() => drillUp()}>Drill Up</button>
        <button onClick={() => resetDrilldown()}>Reset</button>
      </div>
    );
  }

  it('should initialize with level 0 and Overview breadcrumb', () => {
    render(
      <DrilldownProvider>
        <DrilldownTester />
      </DrilldownProvider>
    );

    expect(screen.getByTestId('level')).toHaveTextContent('0');
    expect(screen.getByTestId('breadcrumbs')).toHaveTextContent('Overview');
  });

  it('should drill down and update level and breadcrumbs', async () => {
    const user = userEvent.setup();
    render(
      <DrilldownProvider>
        <DrilldownTester />
      </DrilldownProvider>
    );

    await user.click(screen.getByText('Drill Down'));

    expect(screen.getByTestId('level')).toHaveTextContent('1');
    expect(screen.getByTestId('breadcrumbs')).toHaveTextContent('Overview / Category A');
  });

  it('should drill up and update level and breadcrumbs', async () => {
    const user = userEvent.setup();
    render(
      <DrilldownProvider>
        <DrilldownTester />
      </DrilldownProvider>
    );

    // Drill down first
    await user.click(screen.getByText('Drill Down'));
    expect(screen.getByTestId('level')).toHaveTextContent('1');

    // Drill up
    await user.click(screen.getByText('Drill Up'));
    expect(screen.getByTestId('level')).toHaveTextContent('0');
    expect(screen.getByTestId('breadcrumbs')).toHaveTextContent('Overview');
  });

  it('should not drill up below level 0', async () => {
    const user = userEvent.setup();
    render(
      <DrilldownProvider>
        <DrilldownTester />
      </DrilldownProvider>
    );

    // Try to drill up at level 0
    await user.click(screen.getByText('Drill Up'));
    expect(screen.getByTestId('level')).toHaveTextContent('0');
  });

  it('should reset to initial state', async () => {
    const user = userEvent.setup();
    render(
      <DrilldownProvider>
        <DrilldownTester />
      </DrilldownProvider>
    );

    // Drill down twice
    await user.click(screen.getByText('Drill Down'));
    await user.click(screen.getByText('Drill Down'));
    expect(screen.getByTestId('level')).toHaveTextContent('2');

    // Reset
    await user.click(screen.getByText('Reset'));
    expect(screen.getByTestId('level')).toHaveTextContent('0');
    expect(screen.getByTestId('breadcrumbs')).toHaveTextContent('Overview');
  });

  it('should call onDrillDown callback', async () => {
    const onDrillDown = jest.fn();
    const user = userEvent.setup();

    render(
      <DrilldownProvider onDrillDown={onDrillDown}>
        <DrilldownTester />
      </DrilldownProvider>
    );

    await user.click(screen.getByText('Drill Down'));
    expect(onDrillDown).toHaveBeenCalledWith('Category A', 1);
  });

  it('should throw error when useDrilldown is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<DrilldownTester />);
    }).toThrow('useDrilldown must be used within DrilldownProvider');

    consoleError.mockRestore();
  });
});

// =============================================================================
// DRILLDOWN BREADCRUMBS TESTS
// =============================================================================

describe('DrilldownBreadcrumbs', () => {
  function BreadcrumbTester() {
    const { drillDown } = useDrilldown();
    return (
      <div>
        <DrilldownBreadcrumbs />
        <button onClick={() => drillDown('Level 1', [])}>Drill 1</button>
        <button onClick={() => drillDown('Level 2', [])}>Drill 2</button>
      </div>
    );
  }

  it('should not render at level 0', () => {
    render(
      <DrilldownProvider>
        <BreadcrumbTester />
      </DrilldownProvider>
    );

    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('should render breadcrumbs after drilling down', async () => {
    const user = userEvent.setup();
    render(
      <DrilldownProvider>
        <BreadcrumbTester />
      </DrilldownProvider>
    );

    await user.click(screen.getByText('Drill 1'));

    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Level 1')).toBeInTheDocument();
  });

  it('should have accessible label', async () => {
    const user = userEvent.setup();
    render(
      <DrilldownProvider>
        <BreadcrumbTester />
      </DrilldownProvider>
    );

    await user.click(screen.getByText('Drill 1'));

    expect(screen.getByRole('navigation')).toHaveAttribute(
      'aria-label',
      'Chart drill-down navigation'
    );
  });

  it('should allow clicking breadcrumb items to navigate', async () => {
    const user = userEvent.setup();
    render(
      <DrilldownProvider>
        <BreadcrumbTester />
      </DrilldownProvider>
    );

    await user.click(screen.getByText('Drill 1'));
    await user.click(screen.getByText('Drill 2'));

    // Click on Overview to reset
    await user.click(screen.getByRole('button', { name: 'Overview' }));

    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });
});

// =============================================================================
// CHART TOOLTIP TESTS
// =============================================================================

describe('ChartTooltip', () => {
  it('should not render when not visible', () => {
    render(
      <ChartTooltip
        visible={false}
        x={100}
        y={100}
        title="Test"
        value={42}
      />
    );

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('should render when visible', () => {
    render(
      <ChartTooltip
        visible
        x={100}
        y={100}
        title="Test"
        value={42}
      />
    );

    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    expect(screen.getByText('Test')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('should display color indicator', () => {
    render(
      <ChartTooltip
        visible
        x={100}
        y={100}
        title="Revenue"
        value="$1,234"
        color={KPI_COLORS.REVENUE}
      />
    );

    const colorIndicator = screen.getByRole('tooltip').querySelector('[style*="background-color"]');
    expect(colorIndicator).toHaveStyle({ backgroundColor: KPI_COLORS.REVENUE });
  });

  it('should display subtitle when provided', () => {
    render(
      <ChartTooltip
        visible
        x={100}
        y={100}
        title="Revenue"
        value="$1,234"
        subtitle="vs last month"
      />
    );

    expect(screen.getByText('vs last month')).toBeInTheDocument();
  });

  it('should be non-interactive (pointer-events-none)', () => {
    render(
      <ChartTooltip
        visible
        x={100}
        y={100}
        title="Test"
        value={42}
      />
    );

    expect(screen.getByRole('tooltip')).toHaveClass('pointer-events-none');
  });
});

// =============================================================================
// CHART LEGEND TESTS
// =============================================================================

describe('ChartLegend', () => {
  const mockItems: LegendItem[] = [
    { name: 'Revenue', color: KPI_COLORS.REVENUE, visible: true },
    { name: 'Cost', color: KPI_COLORS.COST, visible: true },
    { name: 'Margin', color: KPI_COLORS.MARGIN, visible: false },
  ];

  it('should render all legend items', () => {
    render(<ChartLegend items={mockItems} onToggle={() => {}} />);

    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('Cost')).toBeInTheDocument();
    expect(screen.getByText('Margin')).toBeInTheDocument();
  });

  it('should call onToggle when item is clicked', async () => {
    const onToggle = jest.fn();
    const user = userEvent.setup();

    render(<ChartLegend items={mockItems} onToggle={onToggle} />);

    await user.click(screen.getByText('Revenue'));
    expect(onToggle).toHaveBeenCalledWith('Revenue');
  });

  it('should show aria-pressed state', () => {
    render(<ChartLegend items={mockItems} onToggle={() => {}} />);

    expect(screen.getByRole('button', { name: /Revenue/i })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Margin/i })).toHaveAttribute('aria-pressed', 'false');
  });

  it('should apply reduced opacity to hidden items', () => {
    render(<ChartLegend items={mockItems} onToggle={() => {}} />);

    const marginButton = screen.getByRole('button', { name: /Margin/i });
    expect(marginButton).toHaveClass('opacity-50');
  });

  it('should apply strikethrough to hidden items', () => {
    render(<ChartLegend items={mockItems} onToggle={() => {}} />);

    const marginText = screen.getByText('Margin');
    expect(marginText).toHaveClass('line-through');
  });

  it('should support vertical orientation', () => {
    render(<ChartLegend items={mockItems} onToggle={() => {}} orientation="vertical" />);

    expect(screen.getByRole('group')).toHaveClass('flex-col');
  });

  it('should have accessible label', () => {
    render(<ChartLegend items={mockItems} onToggle={() => {}} />);

    expect(screen.getByRole('group')).toHaveAttribute('aria-label', 'Chart legend');
  });
});

// =============================================================================
// SPARKLINE TESTS
// =============================================================================

describe('Sparkline', () => {
  it('should render with data', () => {
    render(<Sparkline data={[10, 20, 30, 25, 35]} ariaLabel="Revenue trend" />);

    expect(screen.getByRole('img')).toBeInTheDocument();
  });

  it('should display "No data" when empty', () => {
    render(<Sparkline data={[]} ariaLabel="Empty trend" />);

    expect(screen.getByText('No data')).toBeInTheDocument();
  });

  it('should include trend direction in aria-label', () => {
    render(<Sparkline data={[10, 20, 30]} ariaLabel="Revenue" />);

    expect(screen.getByRole('img')).toHaveAttribute(
      'aria-label',
      expect.stringContaining('up')
    );
  });

  it('should indicate downward trend', () => {
    render(<Sparkline data={[30, 20, 10]} ariaLabel="Declining" />);

    expect(screen.getByRole('img')).toHaveAttribute(
      'aria-label',
      expect.stringContaining('down')
    );
  });

  it('should use custom width and height', () => {
    render(<Sparkline data={[10, 20, 30]} width={150} height={40} />);

    const svg = screen.getByRole('img');
    expect(svg).toHaveAttribute('width', '150');
    expect(svg).toHaveAttribute('height', '40');
  });

  it('should use custom color', () => {
    render(<Sparkline data={[10, 20, 30]} color={KPI_COLORS.REVENUE} />);

    const path = screen.getByRole('img').querySelector('path');
    expect(path).toHaveAttribute('stroke', KPI_COLORS.REVENUE);
  });

  it('should render end dot when showDot is true', () => {
    render(<Sparkline data={[10, 20, 30]} showDot />);

    expect(screen.getByRole('img').querySelector('circle')).toBeInTheDocument();
  });

  it('should not render end dot when showDot is false', () => {
    render(<Sparkline data={[10, 20, 30]} showDot={false} />);

    expect(screen.getByRole('img').querySelector('circle')).not.toBeInTheDocument();
  });

  it('should render area fill when showArea is true', () => {
    render(<Sparkline data={[10, 20, 30]} showArea />);

    const paths = screen.getByRole('img').querySelectorAll('path');
    expect(paths.length).toBeGreaterThan(1); // Line + Area
  });
});

// =============================================================================
// BAR CHART TESTS
// =============================================================================

describe('BarChart', () => {
  const mockData: DataPoint[] = [
    { label: 'Q1', value: 100, color: KPI_COLORS.REVENUE },
    { label: 'Q2', value: 150, color: KPI_COLORS.REVENUE },
    { label: 'Q3', value: 125, color: KPI_COLORS.REVENUE },
    { label: 'Q4', value: 200, color: KPI_COLORS.REVENUE },
  ];

  it('should render all data points', () => {
    render(<BarChart data={mockData} />);

    expect(screen.getByText('Q1')).toBeInTheDocument();
    expect(screen.getByText('Q2')).toBeInTheDocument();
    expect(screen.getByText('Q3')).toBeInTheDocument();
    expect(screen.getByText('Q4')).toBeInTheDocument();
  });

  it('should render title and subtitle', () => {
    render(
      <BarChart
        data={mockData}
        config={{ title: 'Quarterly Revenue', subtitle: 'FY 2025' }}
      />
    );

    expect(screen.getByText('Quarterly Revenue')).toBeInTheDocument();
    expect(screen.getByText('FY 2025')).toBeInTheDocument();
  });

  it('should call onBarClick when bar is clicked', async () => {
    const onBarClick = jest.fn();
    const user = userEvent.setup();

    render(<BarChart data={mockData} onBarClick={onBarClick} />);

    await user.click(screen.getByLabelText('Q1: 100'));
    expect(onBarClick).toHaveBeenCalledWith(mockData[0], 0);
  });

  it('should show tooltip on hover', async () => {
    render(<BarChart data={mockData} config={{ showTooltip: true }} />);

    const bar = screen.getByLabelText('Q1: 100');
    fireEvent.mouseEnter(bar, { clientX: 100, clientY: 100 });

    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    expect(screen.getByRole('tooltip')).toHaveTextContent('Q1');
  });

  it('should hide tooltip on mouse leave', async () => {
    render(<BarChart data={mockData} config={{ showTooltip: true }} />);

    const bar = screen.getByLabelText('Q1: 100');
    fireEvent.mouseEnter(bar, { clientX: 100, clientY: 100 });
    expect(screen.getByRole('tooltip')).toBeInTheDocument();

    fireEvent.mouseLeave(bar);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('should render horizontal bars', () => {
    render(<BarChart data={mockData} horizontal />);

    // In horizontal mode, labels appear before bars
    const labels = screen.getAllByText(/Q[1-4]/);
    expect(labels.length).toBe(4);
  });

  it('should enforce zero baseline by default', () => {
    const dataWithNegative: DataPoint[] = [
      { label: 'A', value: -50 },
      { label: 'B', value: 100 },
    ];

    render(<BarChart data={dataWithNegative} />);

    // With zero baseline, negative values should be handled
    expect(screen.getByLabelText('A: -50')).toBeInTheDocument();
  });

  it('should have accessible role', () => {
    render(<BarChart data={mockData} config={{ title: 'Test Chart' }} />);

    expect(screen.getByRole('img', { name: 'Test Chart' })).toBeInTheDocument();
  });
});

// =============================================================================
// DONUT CHART TESTS
// =============================================================================

describe('DonutChart', () => {
  const mockData: DataPoint[] = [
    { label: 'Product A', value: 40, color: KPI_COLORS.REVENUE },
    { label: 'Product B', value: 30, color: KPI_COLORS.MARGIN },
    { label: 'Product C', value: 30, color: KPI_COLORS.VOLUME },
  ];

  it('should render SVG with correct size', () => {
    render(<DonutChart data={mockData} size={250} />);

    const svg = screen.getByRole('img', { name: 'Donut chart' });
    expect(svg).toHaveAttribute('width', '250');
    expect(svg).toHaveAttribute('height', '250');
  });

  it('should render legend by default', () => {
    render(<DonutChart data={mockData} />);

    expect(screen.getByRole('group', { name: 'Chart legend' })).toBeInTheDocument();
    expect(screen.getByText('Product A')).toBeInTheDocument();
    expect(screen.getByText('Product B')).toBeInTheDocument();
    expect(screen.getByText('Product C')).toBeInTheDocument();
  });

  it('should hide legend when showLegend is false', () => {
    render(<DonutChart data={mockData} showLegend={false} />);

    expect(screen.queryByRole('group', { name: 'Chart legend' })).not.toBeInTheDocument();
  });

  it('should call onSegmentClick when segment is clicked', async () => {
    const onSegmentClick = jest.fn();

    render(<DonutChart data={mockData} onSegmentClick={onSegmentClick} />);

    // Click on the first segment path
    const paths = screen.getByRole('img').querySelectorAll('path');
    if (paths[0]) {
      fireEvent.click(paths[0]);
      expect(onSegmentClick).toHaveBeenCalled();
    }
  });

  it('should show percentage on hover', async () => {
    render(<DonutChart data={mockData} />);

    const paths = screen.getByRole('img').querySelectorAll('path');
    if (paths[0]) {
      fireEvent.mouseEnter(paths[0]);

      // Should show percentage text in center
      await waitFor(() => {
        expect(screen.getByRole('img')).toHaveTextContent(/%/);
      });
    }
  });

  it('should toggle series visibility via legend', async () => {
    const user = userEvent.setup();

    render(<DonutChart data={mockData} />);

    // Toggle Product A off
    await user.click(screen.getByRole('button', { name: /Product A/i }));

    // Button should now show as not pressed
    expect(screen.getByRole('button', { name: /Product A/i })).toHaveAttribute('aria-pressed', 'false');
  });
});

// =============================================================================
// KPI CARD TESTS
// =============================================================================

describe('KPICard', () => {
  it('should render label and value', () => {
    render(<KPICard label="Revenue" value="$1.2M" />);

    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('$1.2M')).toBeInTheDocument();
  });

  it('should display positive change with green color', () => {
    render(<KPICard label="Revenue" value="$1.2M" change={15} />);

    expect(screen.getByText('+15%')).toHaveClass('text-green-600');
  });

  it('should display negative change with red color', () => {
    render(<KPICard label="Cost" value="$500K" change={-10} />);

    expect(screen.getByText('-10%')).toHaveClass('text-red-600');
  });

  it('should display change label', () => {
    render(<KPICard label="Revenue" value="$1.2M" change={15} changeLabel="vs last month" />);

    expect(screen.getByText('vs last month')).toBeInTheDocument();
  });

  it('should render trend sparkline', () => {
    render(<KPICard label="Revenue" value="$1.2M" trend={[10, 15, 12, 18, 22]} />);

    expect(document.querySelector('svg')).toBeInTheDocument();
  });

  it('should render icon when provided', () => {
    render(<KPICard label="Revenue" value="$1.2M" icon={<span>💰</span>} />);

    expect(screen.getByText('💰')).toBeInTheDocument();
  });

  it('should be clickable when onClick is provided', async () => {
    const onClick = jest.fn();
    const user = userEvent.setup();

    render(<KPICard label="Revenue" value="$1.2M" onClick={onClick} />);

    await user.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalled();
  });

  it('should be keyboard accessible', async () => {
    const onClick = jest.fn();
    const user = userEvent.setup();

    render(<KPICard label="Revenue" value="$1.2M" onClick={onClick} />);

    const card = screen.getByRole('button');
    card.focus();
    await user.keyboard('{Enter}');

    expect(onClick).toHaveBeenCalled();
  });

  it('should apply custom color', () => {
    render(<KPICard label="Revenue" value="$1.2M" color={KPI_COLORS.REVENUE} />);

    expect(screen.getByText('$1.2M')).toHaveStyle({ color: KPI_COLORS.REVENUE });
  });
});

// =============================================================================
// CHART EXPORT BUTTON TESTS
// =============================================================================

describe('ChartExportButton', () => {
  const mockRef = { current: document.createElement('div') };

  it('should render export button', () => {
    render(<ChartExportButton chartRef={mockRef as React.RefObject<HTMLElement>} />);

    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
  });

  it('should open dropdown on click', async () => {
    const user = userEvent.setup();

    render(<ChartExportButton chartRef={mockRef as React.RefObject<HTMLElement>} />);

    await user.click(screen.getByRole('button', { name: /export/i }));

    expect(screen.getByRole('menu')).toBeInTheDocument();
  });

  it('should show format options in dropdown', async () => {
    const user = userEvent.setup();

    render(
      <ChartExportButton
        chartRef={mockRef as React.RefObject<HTMLElement>}
        formats={[EXPORT_FORMAT.PNG, EXPORT_FORMAT.PDF]}
      />
    );

    await user.click(screen.getByRole('button', { name: /export/i }));

    expect(screen.getByRole('menuitem', { name: /PNG/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /PDF/i })).toBeInTheDocument();
  });

  it('should close dropdown after clicking format', async () => {
    const user = userEvent.setup();
    const alertMock = jest.spyOn(window, 'alert').mockImplementation(() => {});

    render(<ChartExportButton chartRef={mockRef as React.RefObject<HTMLElement>} />);

    await user.click(screen.getByRole('button', { name: /export/i }));
    await user.click(screen.getByRole('menuitem', { name: /PNG/i }));

    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    alertMock.mockRestore();
  });

  it('should have aria-expanded attribute', async () => {
    const user = userEvent.setup();

    render(<ChartExportButton chartRef={mockRef as React.RefObject<HTMLElement>} />);

    const button = screen.getByRole('button', { name: /export/i });
    expect(button).toHaveAttribute('aria-expanded', 'false');

    await user.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
  });
});

// =============================================================================
// URL UTILITIES TESTS
// =============================================================================

describe('URL Utilities', () => {
  describe('generateDashboardUrl', () => {
    it('should generate URL with filters', () => {
      const url = generateDashboardUrl('https://app.example.com/dashboard', {
        filters: { customer: 'acme', status: 'active' },
      });

      expect(url).toContain('filter_customer=acme');
      expect(url).toContain('filter_status=active');
    });

    it('should generate URL with time range', () => {
      const url = generateDashboardUrl('https://app.example.com/dashboard', {
        timeRange: { start: '2025-01-01', end: '2025-03-31' },
      });

      expect(url).toContain('start=2025-01-01');
      expect(url).toContain('end=2025-03-31');
    });

    it('should generate URL with selected metrics', () => {
      const url = generateDashboardUrl('https://app.example.com/dashboard', {
        selectedMetrics: ['revenue', 'margin', 'volume'],
      });

      expect(url).toContain('metrics=revenue%2Cmargin%2Cvolume');
    });

    it('should generate URL with view', () => {
      const url = generateDashboardUrl('https://app.example.com/dashboard', {
        view: 'summary',
      });

      expect(url).toContain('view=summary');
    });

    it('should return base URL if no config', () => {
      const url = generateDashboardUrl('https://app.example.com/dashboard', {});

      expect(url).toBe('https://app.example.com/dashboard');
    });
  });

  describe('parseDashboardUrl', () => {
    it('should parse filters from URL', () => {
      const config = parseDashboardUrl(
        'https://app.example.com/dashboard?filter_customer=acme&filter_status=active'
      );

      expect(config.filters).toEqual({ customer: 'acme', status: 'active' });
    });

    it('should parse time range from URL', () => {
      const config = parseDashboardUrl(
        'https://app.example.com/dashboard?start=2025-01-01&end=2025-03-31'
      );

      expect(config.timeRange).toEqual({
        start: '2025-01-01',
        end: '2025-03-31',
      });
    });

    it('should parse selected metrics from URL', () => {
      const config = parseDashboardUrl(
        'https://app.example.com/dashboard?metrics=revenue,margin,volume'
      );

      expect(config.selectedMetrics).toEqual(['revenue', 'margin', 'volume']);
    });

    it('should parse view from URL', () => {
      const config = parseDashboardUrl(
        'https://app.example.com/dashboard?view=summary'
      );

      expect(config.view).toBe('summary');
    });

    it('should handle empty URL', () => {
      const config = parseDashboardUrl('https://app.example.com/dashboard');

      expect(config.filters).toBeUndefined();
      expect(config.timeRange).toBeUndefined();
      expect(config.selectedMetrics).toBeUndefined();
      expect(config.view).toBeUndefined();
    });
  });

  describe('shareDashboard', () => {
    it('should copy URL to clipboard', async () => {
      const mockClipboard = {
        writeText: jest.fn().mockResolvedValue(undefined),
      };
      Object.defineProperty(navigator, 'clipboard', {
        value: mockClipboard,
        configurable: true,
      });

      // Mock window.location
      const originalLocation = window.location;
      delete (window as any).location;
      (window as any).location = {
        href: 'https://app.example.com/dashboard?old=param',
      };

      await shareDashboard({
        filters: { customer: 'acme' },
      });

      expect(mockClipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining('filter_customer=acme')
      );

      window.location = originalLocation;
    });
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Data Visualization Integration', () => {
  it('should render KPI dashboard with multiple cards', () => {
    render(
      <div className="grid grid-cols-3 gap-4">
        <KPICard
          label="Revenue"
          value="$1.2M"
          change={12}
          color={KPI_COLORS.REVENUE}
          trend={[10, 12, 11, 14, 16]}
        />
        <KPICard
          label="Margin"
          value="32%"
          change={-2}
          color={KPI_COLORS.MARGIN}
          trend={[35, 34, 33, 32, 32]}
        />
        <KPICard
          label="Volume"
          value="1,234"
          change={8}
          color={KPI_COLORS.VOLUME}
          trend={[100, 110, 105, 120, 134]}
        />
      </div>
    );

    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('Margin')).toBeInTheDocument();
    expect(screen.getByText('Volume')).toBeInTheDocument();
  });

  it('should work with drilldown context', async () => {
    const user = userEvent.setup();

    function DrilldownChart() {
      const { drillDown, currentLevel } = useDrilldown();

      const handleBarClick = (point: DataPoint) => {
        drillDown(point.label, []);
      };

      return (
        <div>
          <DrilldownBreadcrumbs />
          <span data-testid="level">Level: {currentLevel}</span>
          <BarChart
            data={[
              { label: 'Category A', value: 100 },
              { label: 'Category B', value: 150 },
            ]}
            onBarClick={handleBarClick}
          />
        </div>
      );
    }

    render(
      <DrilldownProvider>
        <DrilldownChart />
      </DrilldownProvider>
    );

    expect(screen.getByTestId('level')).toHaveTextContent('Level: 0');

    await user.click(screen.getByLabelText('Category A: 100'));

    expect(screen.getByTestId('level')).toHaveTextContent('Level: 1');
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });
});
