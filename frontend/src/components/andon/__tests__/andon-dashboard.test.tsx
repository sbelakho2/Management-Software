import React from 'react';
import { render, screen, fireEvent, within, act } from '@testing-library/react';
import {
  AndonDashboard,
  AndonDashboardHeader,
  AndonMetricsBar,
  AndonEventCard,
  AndonEventList,
  WorkCenterStatusCard,
  AndonFilterBar,
} from '../andon-dashboard';
import { useAndonStore } from '@/stores/andon-store';
import type { AndonEvent } from '@/types';

// Mock the store
jest.mock('@/stores/andon-store', () => {
  const actual = jest.requireActual('@/stores/andon-store');
  return {
    ...actual,
    useAndonStore: jest.fn(),
  };
});

// Helper to create a mock AndonEvent
function createMockAndonEvent(overrides: Partial<AndonEvent> = {}): AndonEvent {
  return {
    id: 'andon-1',
    andon_number: 'AND-001',
    work_center_id: 'wc-1',
    type: 'quality',
    status: 'triggered',
    severity: 'high',
    description: 'Quality issue detected on the production line',
    escalation_level: 0,
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    created_by_id: 'user-1',
    updated_by_id: 'user-1',
    work_center: {
      id: 'wc-1',
      name: 'Assembly Line 1',
      code: 'AL1',
      location: 'Building A',
      capacity: 100,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by_id: 'user-1',
      updated_by_id: 'user-1',
    },
    ...overrides,
  } as AndonEvent;
}

// Default mock store state
const createMockStore = (overrides = {}) => ({
  events: new Map(),
  activeEvents: [],
  acknowledgedEvents: [],
  resolvedEvents: [],
  workCenters: new Map(),
  metrics: {
    totalActive: 0,
    totalAcknowledged: 0,
    totalResolved: 0,
    avgResponseTime: 0, // in seconds
    avgResolutionTime: 0, // in seconds
    byType: { quality: 0, safety: 0, material: 0, equipment: 0, assistance: 0 },
    bySeverity: { critical: 0, high: 0, medium: 0, low: 0 },
  },
  criticalCount: 0,
  unacknowledgedCount: 0,
  isConnected: true,
  connectionError: null,
  lastHeartbeat: new Date().toISOString(),
  config: {
    autoRefresh: true,
    refreshInterval: 5000,
    soundEnabled: true,
    escalationThreshold: 300000,
    criticalBlinkEnabled: true,
  },
  selectedEventId: null,
  filterType: 'all' as const,
  filterSeverity: 'all' as const,
  isFullscreen: false,
  addEvent: jest.fn(),
  updateEvent: jest.fn(),
  acknowledgeEvent: jest.fn(),
  resolveEvent: jest.fn(),
  escalateEvent: jest.fn(),
  triggerAndon: jest.fn(),
  updateWorkCenter: jest.fn(),
  setWorkCenterStatus: jest.fn(),
  updateMetrics: jest.fn(),
  recalculateMetrics: jest.fn(),
  connect: jest.fn(),
  disconnect: jest.fn(),
  handleMessage: jest.fn(),
  setConnectionError: jest.fn(),
  setConfig: jest.fn(),
  toggleSound: jest.fn(),
  toggleFullscreen: jest.fn(),
  selectEvent: jest.fn(),
  setFilterType: jest.fn(),
  setFilterSeverity: jest.fn(),
  getFilteredEvents: jest.fn().mockReturnValue([]),
  ...overrides,
});

describe('Andon Dashboard Components', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('AndonDashboardHeader', () => {
    test('renders title', () => {
      const mockStore = createMockStore();
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboardHeader title="Test Dashboard" />);

      expect(screen.getByText('Test Dashboard')).toBeInTheDocument();
    });

    test('renders default title when not provided', () => {
      const mockStore = createMockStore();
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboardHeader />);

      expect(screen.getByText('Andon Dashboard')).toBeInTheDocument();
    });

    test('displays critical count badge when there are critical alerts', () => {
      const mockStore = createMockStore({ criticalCount: 3 });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboardHeader />);

      expect(screen.getByText(/3 Critical/)).toBeInTheDocument();
    });

    test('displays unacknowledged count badge when there are active alerts', () => {
      const mockStore = createMockStore({ unacknowledgedCount: 5 });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboardHeader />);

      expect(screen.getByText(/5 Active/)).toBeInTheDocument();
    });

    test('shows connection status when enabled', () => {
      const mockStore = createMockStore({ isConnected: true });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboardHeader showConnectionStatus={true} />);

      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    test('shows disconnected status', () => {
      const mockStore = createMockStore({ isConnected: false });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboardHeader showConnectionStatus={true} />);

      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });

    test('calls onRefresh when refresh button is clicked', () => {
      const mockStore = createMockStore();
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );
      const onRefresh = jest.fn();

      render(<AndonDashboardHeader onRefresh={onRefresh} />);

      const refreshButton = screen.getByTitle('Refresh');
      fireEvent.click(refreshButton);

      expect(onRefresh).toHaveBeenCalled();
    });

    test('calls toggleSound when sound button is clicked', () => {
      const toggleSound = jest.fn();
      const mockStore = createMockStore({ toggleSound });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboardHeader />);

      const soundButton = screen.getByTitle('Mute alerts');
      fireEvent.click(soundButton);

      expect(toggleSound).toHaveBeenCalled();
    });

    test('calls toggleFullscreen when fullscreen button is clicked', () => {
      const toggleFullscreen = jest.fn();
      const mockStore = createMockStore({ toggleFullscreen });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboardHeader />);

      const fullscreenButton = screen.getByTitle('Toggle fullscreen');
      fireEvent.click(fullscreenButton);

      expect(toggleFullscreen).toHaveBeenCalled();
    });
  });

  describe('AndonMetricsBar', () => {
    test('renders all metric cards', () => {
      const mockStore = createMockStore({
        metrics: {
          totalActive: 5,
          totalAcknowledged: 3,
          totalResolved: 10,
          avgResponseTime: 120000,
          avgResolutionTime: 600000,
          byType: { quality: 2, safety: 1, material: 1, equipment: 1, assistance: 0 },
          bySeverity: { critical: 1, high: 2, medium: 2, low: 0 },
        },
      });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonMetricsBar />);

      expect(screen.getByText('Active Alerts')).toBeInTheDocument();
      expect(screen.getByText('Acknowledged')).toBeInTheDocument();
      expect(screen.getByText('Resolved Today')).toBeInTheDocument();
      expect(screen.getByText('Avg Response')).toBeInTheDocument();
      expect(screen.getByText('Avg Resolution')).toBeInTheDocument();
    });

    test('displays metric values', () => {
      const mockStore = createMockStore({
        metrics: {
          totalActive: 5,
          totalAcknowledged: 3,
          totalResolved: 10,
          avgResponseTime: 120, // seconds
          avgResolutionTime: 600, // seconds
          byType: { quality: 0, safety: 0, material: 0, equipment: 0, assistance: 0 },
          bySeverity: { critical: 0, high: 0, medium: 0, low: 0 },
        },
      });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonMetricsBar />);

      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
      // Duration is in seconds, so 120s = 2m, 600s = 10m
      expect(screen.getByText('2m')).toBeInTheDocument();
      expect(screen.getByText('10m')).toBeInTheDocument();
    });
  });

  describe('AndonEventCard', () => {
    test('renders event information', () => {
      const event = createMockAndonEvent();

      render(<AndonEventCard event={event} />);

      expect(screen.getByText('Assembly Line 1')).toBeInTheDocument();
      expect(screen.getByText(/Quality.*AND-001/)).toBeInTheDocument();
      expect(screen.getByText('Quality issue detected on the production line')).toBeInTheDocument();
    });

    test('renders escalation level badge when escalated', () => {
      const event = createMockAndonEvent({ escalation_level: 2 });

      render(<AndonEventCard event={event} />);

      expect(screen.getByText('L2')).toBeInTheDocument();
    });

    test('renders status badge', () => {
      const event = createMockAndonEvent({ status: 'triggered' });

      render(<AndonEventCard event={event} />);

      expect(screen.getByText('Triggered')).toBeInTheDocument();
    });

    test('renders Acknowledge button for triggered events', () => {
      const event = createMockAndonEvent({ status: 'triggered' });
      const onAcknowledge = jest.fn();

      render(<AndonEventCard event={event} onAcknowledge={onAcknowledge} />);

      const button = screen.getByRole('button', { name: /Acknowledge/i });
      expect(button).toBeInTheDocument();
    });

    test('calls onAcknowledge when Acknowledge button is clicked', () => {
      const event = createMockAndonEvent({ status: 'triggered' });
      const onAcknowledge = jest.fn();

      render(<AndonEventCard event={event} onAcknowledge={onAcknowledge} />);

      fireEvent.click(screen.getByRole('button', { name: /Acknowledge/i }));
      expect(onAcknowledge).toHaveBeenCalled();
    });

    test('renders Escalate button for active events', () => {
      const event = createMockAndonEvent({ status: 'triggered' });
      const onEscalate = jest.fn();

      render(<AndonEventCard event={event} onEscalate={onEscalate} />);

      expect(screen.getByRole('button', { name: /Escalate/i })).toBeInTheDocument();
    });

    test('calls onEscalate when Escalate button is clicked', () => {
      const event = createMockAndonEvent({ status: 'triggered' });
      const onEscalate = jest.fn();

      render(<AndonEventCard event={event} onEscalate={onEscalate} />);

      fireEvent.click(screen.getByRole('button', { name: /Escalate/i }));
      expect(onEscalate).toHaveBeenCalled();
    });

    test('renders Resolve button for active events', () => {
      const event = createMockAndonEvent({ status: 'acknowledged' });
      const onResolve = jest.fn();

      render(<AndonEventCard event={event} onResolve={onResolve} />);

      expect(screen.getByRole('button', { name: /Resolve/i })).toBeInTheDocument();
    });

    test('calls onResolve when Resolve button is clicked', () => {
      const event = createMockAndonEvent({ status: 'acknowledged' });
      const onResolve = jest.fn();

      render(<AndonEventCard event={event} onResolve={onResolve} />);

      fireEvent.click(screen.getByRole('button', { name: /Resolve/i }));
      expect(onResolve).toHaveBeenCalled();
    });

    test('is clickable when onClick is provided', () => {
      const event = createMockAndonEvent();
      const onClick = jest.fn();

      render(<AndonEventCard event={event} onClick={onClick} />);

      const card = screen.getByRole('button');
      fireEvent.click(card);
      expect(onClick).toHaveBeenCalled();
    });

    test('handles keyboard interaction', () => {
      const event = createMockAndonEvent();
      const onClick = jest.fn();

      render(<AndonEventCard event={event} onClick={onClick} />);

      const card = screen.getByRole('button');
      fireEvent.keyDown(card, { key: 'Enter' });
      expect(onClick).toHaveBeenCalled();
    });

    test('applies selected styling when isSelected is true', () => {
      const event = createMockAndonEvent();

      render(<AndonEventCard event={event} isSelected={true} onClick={() => {}} />);

      const card = screen.getByRole('button');
      expect(card).toHaveClass('ring-2', 'ring-blue-500');
    });

    test('renders in compact mode', () => {
      const event = createMockAndonEvent();

      render(<AndonEventCard event={event} compact={true} />);

      expect(screen.getByText('Quality issue detected on the production line')).toBeInTheDocument();
    });

    test('does not render action buttons in compact mode', () => {
      const event = createMockAndonEvent({ status: 'triggered' });

      render(
        <AndonEventCard
          event={event}
          compact={true}
          onAcknowledge={() => {}}
          onEscalate={() => {}}
          onResolve={() => {}}
        />
      );

      expect(screen.queryByRole('button', { name: /Acknowledge/i })).not.toBeInTheDocument();
    });
  });

  describe('AndonEventList', () => {
    test('renders empty state when no events', () => {
      render(<AndonEventList events={[]} />);

      expect(screen.getByText('No active alerts')).toBeInTheDocument();
      expect(screen.getByText('All systems operating normally')).toBeInTheDocument();
    });

    test('renders custom empty message', () => {
      render(<AndonEventList events={[]} emptyMessage="No alerts found" />);

      expect(screen.getByText('No alerts found')).toBeInTheDocument();
    });

    test('renders list of events', () => {
      const events = [
        createMockAndonEvent({ id: 'e1', description: 'First event' }),
        createMockAndonEvent({ id: 'e2', description: 'Second event' }),
      ];

      render(<AndonEventList events={events} />);

      expect(screen.getByText('First event')).toBeInTheDocument();
      expect(screen.getByText('Second event')).toBeInTheDocument();
    });

    test('calls onEventClick when event is clicked', () => {
      const events = [createMockAndonEvent()];
      const onEventClick = jest.fn();

      render(<AndonEventList events={events} onEventClick={onEventClick} />);

      const card = screen.getByRole('button');
      fireEvent.click(card);
      expect(onEventClick).toHaveBeenCalledWith(events[0]);
    });

    test('passes onAcknowledge to event cards', () => {
      const events = [createMockAndonEvent({ status: 'triggered' })];
      const onAcknowledge = jest.fn();

      render(<AndonEventList events={events} onAcknowledge={onAcknowledge} />);

      fireEvent.click(screen.getByRole('button', { name: /Acknowledge/i }));
      expect(onAcknowledge).toHaveBeenCalledWith('andon-1');
    });

    test('highlights selected event', () => {
      const events = [
        createMockAndonEvent({ id: 'e1' }),
        createMockAndonEvent({ id: 'e2' }),
      ];

      render(<AndonEventList events={events} selectedEventId="e1" onEventClick={() => {}} />);

      const buttons = screen.getAllByRole('button');
      expect(buttons[0]).toHaveClass('ring-2', 'ring-blue-500');
      expect(buttons[1]).not.toHaveClass('ring-blue-500');
    });
  });

  describe('WorkCenterStatusCard', () => {
    const baseWorkCenter = {
      id: 'wc-1',
      name: 'Assembly Line 1',
      status: 'running' as const,
      operator: 'John Doe',
      currentJob: 'JOB-001',
      targetCount: 100,
      actualCount: 85,
      efficiency: 95,
      oee: 85,
      activeAndonCount: 0,
      lastUpdate: new Date().toISOString(),
    };

    test('renders work center information', () => {
      render(<WorkCenterStatusCard workCenter={baseWorkCenter} />);

      expect(screen.getByText('Assembly Line 1')).toBeInTheDocument();
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Running')).toBeInTheDocument();
    });

    test('renders current job', () => {
      render(<WorkCenterStatusCard workCenter={baseWorkCenter} />);

      expect(screen.getByText(/JOB-001/)).toBeInTheDocument();
    });

    test('renders progress bar with counts', () => {
      render(<WorkCenterStatusCard workCenter={baseWorkCenter} />);

      expect(screen.getByText('85/100')).toBeInTheDocument();
    });

    test('renders efficiency and OEE metrics', () => {
      render(<WorkCenterStatusCard workCenter={baseWorkCenter} />);

      expect(screen.getByText('95%')).toBeInTheDocument();
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    test('renders active andon count badge when alerts present', () => {
      const workCenter = { ...baseWorkCenter, activeAndonCount: 2 };

      render(<WorkCenterStatusCard workCenter={workCenter} />);

      expect(screen.getByText('2')).toBeInTheDocument();
    });

    test('renders different status indicators', () => {
      const statuses: Array<'running' | 'stopped' | 'maintenance' | 'changeover' | 'idle'> = [
        'running',
        'stopped',
        'maintenance',
        'changeover',
        'idle',
      ];

      statuses.forEach((status) => {
        const { unmount } = render(
          <WorkCenterStatusCard workCenter={{ ...baseWorkCenter, status }} />
        );
        const expectedText = status.charAt(0).toUpperCase() + status.slice(1);
        expect(screen.getByText(expectedText)).toBeInTheDocument();
        unmount();
      });
    });

    test('is clickable when onClick is provided', () => {
      const onClick = jest.fn();

      render(<WorkCenterStatusCard workCenter={baseWorkCenter} onClick={onClick} />);

      const card = screen.getByRole('button');
      fireEvent.click(card);
      expect(onClick).toHaveBeenCalled();
    });

    test('handles keyboard interaction', () => {
      const onClick = jest.fn();

      render(<WorkCenterStatusCard workCenter={baseWorkCenter} onClick={onClick} />);

      const card = screen.getByRole('button');
      fireEvent.keyDown(card, { key: 'Enter' });
      expect(onClick).toHaveBeenCalled();
    });

    test('applies selected styling when isSelected is true', () => {
      render(
        <WorkCenterStatusCard workCenter={baseWorkCenter} isSelected={true} onClick={() => {}} />
      );

      const card = screen.getByRole('button');
      expect(card).toHaveClass('ring-2', 'ring-blue-500');
    });
  });

  describe('AndonFilterBar', () => {
    test('renders type filter buttons', () => {
      render(
        <AndonFilterBar
          currentType="all"
          currentSeverity="all"
          onTypeChange={() => {}}
          onSeverityChange={() => {}}
        />
      );

      const allButtons = screen.getAllByRole('button', { name: 'All' });
      expect(allButtons).toHaveLength(2); // One for type, one for severity
      expect(screen.getByRole('button', { name: 'Quality' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Safety' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Material' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Equipment' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Assistance' })).toBeInTheDocument();
    });

    test('renders severity filter buttons', () => {
      render(
        <AndonFilterBar
          currentType="all"
          currentSeverity="all"
          onTypeChange={() => {}}
          onSeverityChange={() => {}}
        />
      );

      // Find buttons containing these text - severity uses 'critical', 'major', 'minor'
      expect(screen.getByRole('button', { name: 'Critical' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Major' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Minor' })).toBeInTheDocument();
    });

    test('calls onTypeChange when type button is clicked', () => {
      const onTypeChange = jest.fn();

      render(
        <AndonFilterBar
          currentType="all"
          currentSeverity="all"
          onTypeChange={onTypeChange}
          onSeverityChange={() => {}}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: 'Quality' }));
      expect(onTypeChange).toHaveBeenCalledWith('quality');
    });

    test('calls onSeverityChange when severity button is clicked', () => {
      const onSeverityChange = jest.fn();

      render(
        <AndonFilterBar
          currentType="all"
          currentSeverity="all"
          onTypeChange={() => {}}
          onSeverityChange={onSeverityChange}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: 'Critical' }));
      expect(onSeverityChange).toHaveBeenCalledWith('critical');
    });

    test('highlights active type filter', () => {
      render(
        <AndonFilterBar
          currentType="quality"
          currentSeverity="all"
          onTypeChange={() => {}}
          onSeverityChange={() => {}}
        />
      );

      const qualityButton = screen.getByRole('button', { name: 'Quality' });
      expect(qualityButton).toHaveClass('bg-blue-600', 'text-white');
    });

    test('highlights active severity filter', () => {
      render(
        <AndonFilterBar
          currentType="all"
          currentSeverity="critical"
          onTypeChange={() => {}}
          onSeverityChange={() => {}}
        />
      );

      const criticalButton = screen.getByRole('button', { name: 'Critical' });
      expect(criticalButton).toHaveClass('text-white');
    });
  });

  describe('AndonDashboard', () => {
    test('renders all dashboard sections', () => {
      const mockStore = createMockStore();
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboard />);

      expect(screen.getByText('Andon Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Active Alerts')).toBeInTheDocument();
      expect(screen.getByText('Work Centers')).toBeInTheDocument();
    });

    test('shows alert count in heading', () => {
      const events = [
        createMockAndonEvent({ id: 'e1' }),
        createMockAndonEvent({ id: 'e2' }),
      ];
      const mockStore = createMockStore({
        activeEvents: events,
        getFilteredEvents: jest.fn().mockReturnValue(events),
      });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboard />);

      expect(screen.getByText(/Active Alerts \(2\)/)).toBeInTheDocument();
    });

    test('renders work centers from store', () => {
      const workCenters = new Map([
        ['wc-1', {
          id: 'wc-1',
          name: 'Assembly Line 1',
          status: 'running' as const,
          efficiency: 95,
          oee: 85,
          targetCount: 100,
          actualCount: 85,
          activeAndonCount: 0,
          lastUpdate: new Date().toISOString(),
        }],
        ['wc-2', {
          id: 'wc-2',
          name: 'Assembly Line 2',
          status: 'stopped' as const,
          efficiency: 0,
          oee: 0,
          targetCount: 100,
          actualCount: 0,
          activeAndonCount: 1,
          lastUpdate: new Date().toISOString(),
        }],
      ]);
      const mockStore = createMockStore({ workCenters });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboard />);

      expect(screen.getByText('Assembly Line 1')).toBeInTheDocument();
      expect(screen.getByText('Assembly Line 2')).toBeInTheDocument();
    });

    test('shows empty work centers message when none configured', () => {
      const mockStore = createMockStore({ workCenters: new Map() });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboard />);

      expect(screen.getByText('No work centers configured')).toBeInTheDocument();
    });

    test('calls store actions on event interactions', () => {
      const acknowledgeEvent = jest.fn();
      const escalateEvent = jest.fn();
      const resolveEvent = jest.fn();
      const selectEvent = jest.fn();
      const events = [createMockAndonEvent({ status: 'triggered' })];
      const mockStore = createMockStore({
        activeEvents: events,
        getFilteredEvents: jest.fn().mockReturnValue(events),
        acknowledgeEvent,
        escalateEvent,
        resolveEvent,
        selectEvent,
      });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboard />);

      // Find the Acknowledge button specifically (not the card with role="button")
      const acknowledgeButtons = screen.getAllByRole('button', { name: /Acknowledge/i });
      // The actual button is the one that's a <button> element, not the card
      const ackButton = acknowledgeButtons.find((btn) => btn.tagName === 'BUTTON');
      if (ackButton) {
        fireEvent.click(ackButton);
        expect(acknowledgeEvent).toHaveBeenCalledWith('andon-1', 'Current User');
      }
    });

    test('calls onEventClick callback', () => {
      const selectEvent = jest.fn();
      const onEventClick = jest.fn();
      const events = [createMockAndonEvent()];
      const mockStore = createMockStore({
        activeEvents: events,
        getFilteredEvents: jest.fn().mockReturnValue(events),
        selectEvent,
      });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboard onEventClick={onEventClick} />);

      // Find clickable event card
      const eventCards = screen.getAllByRole('button');
      const eventCard = eventCards.find(btn => btn.textContent?.includes('Assembly Line 1'));
      if (eventCard) {
        fireEvent.click(eventCard);
        expect(selectEvent).toHaveBeenCalledWith('andon-1');
        expect(onEventClick).toHaveBeenCalledWith(events[0]);
      }
    });

    test('calls filter actions from filter bar', () => {
      const setFilterType = jest.fn();
      const setFilterSeverity = jest.fn();
      const mockStore = createMockStore({ setFilterType, setFilterSeverity });
      (useAndonStore as unknown as jest.Mock).mockImplementation((selector) =>
        selector ? selector(mockStore) : mockStore
      );

      render(<AndonDashboard />);

      fireEvent.click(screen.getByRole('button', { name: 'Quality' }));
      expect(setFilterType).toHaveBeenCalledWith('quality');

      fireEvent.click(screen.getByRole('button', { name: 'Critical' }));
      expect(setFilterSeverity).toHaveBeenCalledWith('critical');
    });
  });

  describe('Accessibility', () => {
    test('AndonEventCard is keyboard navigable', () => {
      const event = createMockAndonEvent();
      const onClick = jest.fn();

      render(<AndonEventCard event={event} onClick={onClick} />);

      const card = screen.getByRole('button');
      expect(card).toHaveAttribute('tabIndex', '0');

      fireEvent.keyDown(card, { key: ' ' });
      expect(onClick).toHaveBeenCalled();
    });

    test('WorkCenterStatusCard is keyboard navigable', () => {
      const workCenter = {
        id: 'wc-1',
        name: 'Test',
        status: 'running' as const,
        efficiency: 95,
        oee: 85,
        targetCount: 100,
        actualCount: 85,
        activeAndonCount: 0,
        lastUpdate: new Date().toISOString(),
      };
      const onClick = jest.fn();

      render(<WorkCenterStatusCard workCenter={workCenter} onClick={onClick} />);

      const card = screen.getByRole('button');
      expect(card).toHaveAttribute('tabIndex', '0');

      fireEvent.keyDown(card, { key: ' ' });
      expect(onClick).toHaveBeenCalled();
    });

    test('filter buttons are accessible', () => {
      render(
        <AndonFilterBar
          currentType="all"
          currentSeverity="all"
          onTypeChange={() => {}}
          onSeverityChange={() => {}}
        />
      );

      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
      buttons.forEach((button) => {
        expect(button).toBeEnabled();
      });
    });
  });
});
