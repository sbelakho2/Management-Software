import { act } from '@testing-library/react';
import { useAndonStore, getSeverityColor, getSeverityLabel, getAndonTypeLabel, getAndonTypeIcon, getStatusLabel, getStatusColor, formatElapsedTime, formatDuration, calculateEscalationLevel } from '../andon-store';
import type { AndonEvent, AndonType, AndonStatus, Severity } from '@/types';

jest.mock('@/api/andon', () => ({
  andonApi: {
    getAnalytics: jest.fn().mockResolvedValue({
      avg_response_time_minutes: 0,
      avg_resolution_time_minutes: 0,
      total_signals: 0,
      uptime_impact_percent: 0,
      signals_by_category: {},
      top_problem_stations: [],
    }),
    acknowledgeEvent: jest.fn().mockResolvedValue({}),
    resolveEvent: jest.fn().mockResolvedValue({}),
    escalateEvent: jest.fn().mockResolvedValue({}),
    triggerAndon: jest.fn().mockImplementation((data: any) => {
      const now = new Date().toISOString();
      return Promise.resolve({
        id: 'andon-api-1',
        andon_number: 'AND-API-1',
        work_center_id: data.work_center_id,
        work_center: {
          id: data.work_center_id,
          name: 'Work Center',
          code: 'WC',
          type: 'assembly',
          capacity: 0,
          capacity_unit: 'units',
          efficiency_percentage: 0,
          is_active: true,
          created_at: now,
          updated_at: now,
        },
        type: data.type,
        status: 'triggered',
        severity: data.severity,
        description: data.description,
        triggered_by: 'system',
        triggered_user: {
          id: 'system',
          email: 'system@local',
          full_name: 'System',
          role: 'admin',
          roles: ['admin'],
          is_active: true,
          created_at: now,
          updated_at: now,
        },
        escalation_level: 0,
        created_at: now,
        updated_at: now,
        created_by: 'system',
        updated_by: 'system',
      });
    }),
  },
}));

// Mock Audio
const mockPlay = jest.fn();
const mockPause = jest.fn();

global.Audio = jest.fn().mockImplementation(() => ({
  play: mockPlay,
  pause: mockPause,
  volume: 1,
  loop: false,
}));

// Mock AudioContext
class MockOscillator {
  frequency = { setValueAtTime: jest.fn() };
  type = 'sine';
  connect = jest.fn();
  start = jest.fn();
  stop = jest.fn();
}

class MockGain {
  gain = { setValueAtTime: jest.fn(), exponentialRampToValueAtTime: jest.fn() };
  connect = jest.fn();
}

const mockAudioContext = {
  createOscillator: jest.fn(() => new MockOscillator()),
  createGain: jest.fn(() => new MockGain()),
  destination: {},
  currentTime: 0,
};

global.AudioContext = jest.fn().mockImplementation(() => mockAudioContext);

// Helper to create a mock AndonEvent
function createMockAndonEvent(overrides: Partial<AndonEvent> = {}): AndonEvent {
  return {
    id: 'andon-1',
    andon_number: 'AND-001',
    work_center_id: 'wc-1',
    type: 'quality',
    status: 'triggered',
    severity: 'high',
    description: 'Quality issue detected',
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

describe('andon-store', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset the store
    act(() => {
      const store = useAndonStore.getState();
      store.events.clear();
      store.workCenters.clear();
      useAndonStore.setState({
        events: new Map(),
        activeEvents: [],
        acknowledgedEvents: [],
        resolvedEvents: [],
        workCenters: new Map(),
        metrics: {
          totalActive: 0,
          totalAcknowledged: 0,
          totalResolved: 0,
          avgResponseTime: 0,
          avgResolutionTime: 0,
          byType: { quality: 0, safety: 0, material: 0, equipment: 0, assistance: 0 },
          bySeverity: { critical: 0, high: 0, medium: 0, low: 0 },
        },
        criticalCount: 0,
        unacknowledgedCount: 0,
        isConnected: false,
        connectionError: null,
        lastHeartbeat: null,
        config: {
          autoRefresh: true,
          refreshInterval: 5000,
          soundEnabled: true,
          escalationThreshold: 300000,
          criticalBlinkEnabled: true,
        },
        selectedEventId: null,
        filterType: 'all',
        filterSeverity: 'all',
        isFullscreen: false,
      });
    });
  });

  describe('Event Management', () => {
    test('addEvent adds a new event to the store', () => {
      const event = createMockAndonEvent();
      
      act(() => {
        useAndonStore.getState().addEvent(event);
      });

      const state = useAndonStore.getState();
      expect(state.events.get(event.id)).toEqual(event);
      expect(state.activeEvents).toContainEqual(event);
      expect(state.unacknowledgedCount).toBe(1);
    });

    test('addEvent categorizes events by status', () => {
      const triggeredEvent = createMockAndonEvent({ id: 'e1', status: 'triggered' });
      const acknowledgedEvent = createMockAndonEvent({ id: 'e2', status: 'acknowledged' });
      const resolvedEvent = createMockAndonEvent({ id: 'e3', status: 'resolved' });

      act(() => {
        useAndonStore.getState().addEvent(triggeredEvent);
        useAndonStore.getState().addEvent(acknowledgedEvent);
        useAndonStore.getState().addEvent(resolvedEvent);
      });

      const state = useAndonStore.getState();
      // activeEvents only contains triggered or escalated
      expect(state.activeEvents).toHaveLength(1);
      expect(state.acknowledgedEvents).toHaveLength(1);
      expect(state.resolvedEvents).toHaveLength(1);
    });

    test('addEvent tracks critical events', () => {
      const criticalEvent = createMockAndonEvent({ severity: 'critical' });

      act(() => {
        useAndonStore.getState().addEvent(criticalEvent);
      });

      expect(useAndonStore.getState().criticalCount).toBe(1);
    });

    test('updateEvent modifies an existing event', () => {
      const event = createMockAndonEvent();
      
      act(() => {
        useAndonStore.getState().addEvent(event);
        useAndonStore.getState().updateEvent(event.id, { description: 'Updated description' });
      });

      const updatedEvent = useAndonStore.getState().events.get(event.id);
      expect(updatedEvent?.description).toBe('Updated description');
    });

    test('acknowledgeEvent changes status to acknowledged', async () => {
      const event = createMockAndonEvent({ status: 'triggered' });
      
      await act(async () => {
        useAndonStore.getState().addEvent(event);
        await useAndonStore.getState().acknowledgeEvent(event.id, 'John Doe');
      });

      const acknowledgedEvent = useAndonStore.getState().events.get(event.id);
      expect(acknowledgedEvent?.status).toBe('acknowledged');
      expect(acknowledgedEvent?.acknowledged_by).toBe('John Doe');
      expect(acknowledgedEvent?.acknowledged_at).toBeDefined();
    });

    test('resolveEvent changes status to resolved', async () => {
      const event = createMockAndonEvent({ status: 'acknowledged' });
      
      await act(async () => {
        useAndonStore.getState().addEvent(event);
        await useAndonStore.getState().resolveEvent(event.id, 'Problem fixed');
      });

      const resolvedEvent = useAndonStore.getState().events.get(event.id);
      expect(resolvedEvent?.status).toBe('resolved');
      expect(resolvedEvent?.resolution).toBe('Problem fixed');
      expect(resolvedEvent?.resolved_at).toBeDefined();
    });

    test('escalateEvent increments escalation level', async () => {
      const event = createMockAndonEvent({ escalation_level: 0 });
      
      await act(async () => {
        useAndonStore.getState().addEvent(event);
        await useAndonStore.getState().escalateEvent(event.id);
      });

      const escalatedEvent = useAndonStore.getState().events.get(event.id);
      expect(escalatedEvent?.escalation_level).toBe(1);
      expect(escalatedEvent?.status).toBe('escalated');
    });

    test('escalateEvent updates escalation_level', async () => {
      const event = createMockAndonEvent({ escalation_level: 1 });
      
      await act(async () => {
        useAndonStore.getState().addEvent(event);
        await useAndonStore.getState().escalateEvent(event.id);
      });

      const escalatedEvent = useAndonStore.getState().events.get(event.id);
      expect(escalatedEvent?.escalation_level).toBe(2);
      expect(escalatedEvent?.status).toBe('escalated');
    });

    test('triggerAndon creates a new event with pending status', async () => {
      await act(async () => {
        await useAndonStore.getState().triggerAndon('wc-1', 'safety', 'critical', 'Safety hazard detected');
      });

      const state = useAndonStore.getState();
      const events = Array.from(state.events.values());
      expect(events).toHaveLength(1);
      expect(events[0].type).toBe('safety');
      expect(events[0].severity).toBe('critical');
      expect(events[0].status).toBe('triggered');
    });
  });

  describe('Work Center Management', () => {
    test('updateWorkCenter adds a new work center', () => {
      const workCenter = {
        id: 'wc-1',
        name: 'Assembly Line 1',
        status: 'running' as const,
        efficiency: 95,
        oee: 85,
        targetCount: 100,
        actualCount: 85,
        activeAndonCount: 0,
        lastUpdate: new Date().toISOString(),
      };

      act(() => {
        useAndonStore.getState().updateWorkCenter(workCenter);
      });

      expect(useAndonStore.getState().workCenters.get('wc-1')).toEqual(workCenter);
    });

    test('setWorkCenterStatus updates work center status', () => {
      const workCenter = {
        id: 'wc-1',
        name: 'Assembly Line 1',
        status: 'running' as const,
        efficiency: 95,
        oee: 85,
        targetCount: 100,
        actualCount: 85,
        activeAndonCount: 0,
        lastUpdate: new Date().toISOString(),
      };

      act(() => {
        useAndonStore.getState().updateWorkCenter(workCenter);
        useAndonStore.getState().setWorkCenterStatus('wc-1', 'stopped');
      });

      expect(useAndonStore.getState().workCenters.get('wc-1')?.status).toBe('stopped');
    });

    test('setWorkCenterStatus ignores non-existent work center', () => {
      act(() => {
        useAndonStore.getState().setWorkCenterStatus('non-existent', 'stopped');
      });

      expect(useAndonStore.getState().workCenters.size).toBe(0);
    });
  });

  describe('Metrics', () => {
    test('updateMetrics updates metrics state', () => {
      const metrics = {
        totalActive: 5,
        totalAcknowledged: 3,
        totalResolved: 10,
        avgResponseTime: 120000,
        avgResolutionTime: 600000,
        byType: { quality: 3, safety: 1, material: 1, equipment: 0, assistance: 0 },
        bySeverity: { critical: 1, high: 2, medium: 2, low: 0 },
      };

      act(() => {
        useAndonStore.getState().updateMetrics(metrics);
      });

      expect(useAndonStore.getState().metrics).toEqual(metrics);
    });

    test('recalculateMetrics computes metrics from events', () => {
      const events = [
        createMockAndonEvent({ id: 'e1', status: 'triggered', severity: 'critical', type: 'quality' }),
        createMockAndonEvent({ id: 'e2', status: 'triggered', severity: 'high', type: 'safety' }),
        createMockAndonEvent({ id: 'e3', status: 'resolved', severity: 'medium', type: 'material' }),
      ];

      act(() => {
        events.forEach((e) => useAndonStore.getState().addEvent(e));
        useAndonStore.getState().recalculateMetrics();
      });

      const metrics = useAndonStore.getState().metrics;
      // Active events are those with status 'triggered' or 'escalated'
      expect(metrics.totalActive).toBe(2);
      expect(metrics.totalResolved).toBe(1);
      expect(metrics.byType.quality).toBe(1);
      expect(metrics.byType.safety).toBe(1);
      expect(metrics.bySeverity.critical).toBe(1);
    });
  });

  describe('Connection Management', () => {
    test('connect sets isConnected to true', () => {
      act(() => {
        useAndonStore.getState().connect();
      });

      expect(useAndonStore.getState().isConnected).toBe(true);
      expect(useAndonStore.getState().connectionError).toBeNull();
    });

    test('disconnect sets isConnected to false', () => {
      act(() => {
        useAndonStore.getState().connect();
        useAndonStore.getState().disconnect();
      });

      expect(useAndonStore.getState().isConnected).toBe(false);
    });

    test('setConnectionError updates error state', () => {
      act(() => {
        useAndonStore.getState().setConnectionError('Connection failed');
      });

      expect(useAndonStore.getState().connectionError).toBe('Connection failed');
    });

    test('handleMessage processes andon events', () => {
      const event = createMockAndonEvent();
      const message = { type: 'andon_event' as const, payload: event };

      act(() => {
        useAndonStore.getState().handleMessage(message);
      });

      expect(useAndonStore.getState().events.get(event.id)).toBeDefined();
    });

    test('handleMessage processes work center updates', () => {
      const workCenter = {
        id: 'wc-1',
        name: 'Assembly Line 1',
        status: 'running' as const,
        efficiency: 95,
        oee: 85,
        targetCount: 100,
        actualCount: 85,
        activeAndonCount: 0,
        lastUpdate: new Date().toISOString(),
      };
      const message = { type: 'work_center_update' as const, payload: workCenter };

      act(() => {
        useAndonStore.getState().handleMessage(message);
      });

      expect(useAndonStore.getState().workCenters.get('wc-1')).toBeDefined();
    });

    test('handleMessage processes metrics updates', () => {
      const metrics = {
        totalActive: 5,
        totalAcknowledged: 3,
        totalResolved: 10,
        avgResponseTime: 120000,
        avgResolutionTime: 600000,
        byType: { quality: 3, safety: 1, material: 1, equipment: 0, assistance: 0 },
        bySeverity: { critical: 1, high: 2, medium: 2, low: 0 },
      };
      const message = { type: 'metrics_update' as const, payload: metrics };

      act(() => {
        useAndonStore.getState().handleMessage(message);
      });

      expect(useAndonStore.getState().metrics).toEqual(metrics);
    });

    test('handleMessage updates lastHeartbeat on heartbeat', () => {
      const message = { type: 'heartbeat' as const, payload: {} };

      act(() => {
        useAndonStore.getState().handleMessage(message);
      });

      expect(useAndonStore.getState().lastHeartbeat).toBeDefined();
    });
  });

  describe('UI State', () => {
    test('setConfig updates configuration', () => {
      act(() => {
        useAndonStore.getState().setConfig({ refreshInterval: 10000 });
      });

      expect(useAndonStore.getState().config.refreshInterval).toBe(10000);
    });

    test('toggleSound toggles sound enabled', () => {
      const initialValue = useAndonStore.getState().config.soundEnabled;
      
      act(() => {
        useAndonStore.getState().toggleSound();
      });

      expect(useAndonStore.getState().config.soundEnabled).toBe(!initialValue);
    });

    test('toggleFullscreen toggles fullscreen mode', () => {
      const initialValue = useAndonStore.getState().config.fullscreenMode;
      
      act(() => {
        useAndonStore.getState().toggleFullscreen();
      });

      expect(useAndonStore.getState().config.fullscreenMode).toBe(!initialValue);
    });

    test('selectEvent updates selectedEventId', () => {
      act(() => {
        useAndonStore.getState().selectEvent('event-123');
      });

      expect(useAndonStore.getState().selectedEventId).toBe('event-123');
    });

    test('setFilterType updates filter type', () => {
      act(() => {
        useAndonStore.getState().setFilterType('quality');
      });

      expect(useAndonStore.getState().filterType).toBe('quality');
    });

    test('setFilterSeverity updates filter severity', () => {
      act(() => {
        useAndonStore.getState().setFilterSeverity('critical');
      });

      expect(useAndonStore.getState().filterSeverity).toBe('critical');
    });
  });

  describe('Filtering', () => {
    test('getFilteredEvents returns all active events when no filters', () => {
      const events = [
        createMockAndonEvent({ id: 'e1', status: 'triggered', type: 'quality', severity: 'high' }),
        createMockAndonEvent({ id: 'e2', status: 'acknowledged', type: 'safety', severity: 'medium' }),
      ];

      act(() => {
        events.forEach((e) => useAndonStore.getState().addEvent(e));
      });

      const filtered = useAndonStore.getState().getFilteredEvents();
      expect(filtered).toHaveLength(2);
    });

    test('getFilteredEvents filters by type', () => {
      const events = [
        createMockAndonEvent({ id: 'e1', type: 'quality' }),
        createMockAndonEvent({ id: 'e2', type: 'safety' }),
        createMockAndonEvent({ id: 'e3', type: 'quality' }),
      ];

      act(() => {
        events.forEach((e) => useAndonStore.getState().addEvent(e));
        useAndonStore.getState().setFilterType('quality');
      });

      const filtered = useAndonStore.getState().getFilteredEvents();
      expect(filtered).toHaveLength(2);
      expect(filtered.every((e) => e.type === 'quality')).toBe(true);
    });

    test('getFilteredEvents filters by severity', () => {
      const events = [
        createMockAndonEvent({ id: 'e1', severity: 'critical' }),
        createMockAndonEvent({ id: 'e2', severity: 'high' }),
        createMockAndonEvent({ id: 'e3', severity: 'critical' }),
      ];

      act(() => {
        events.forEach((e) => useAndonStore.getState().addEvent(e));
        useAndonStore.getState().setFilterSeverity('critical');
      });

      const filtered = useAndonStore.getState().getFilteredEvents();
      expect(filtered).toHaveLength(2);
      expect(filtered.every((e) => e.severity === 'critical')).toBe(true);
    });

    test('getFilteredEvents filters by both type and severity', () => {
      const events = [
        createMockAndonEvent({ id: 'e1', type: 'quality', severity: 'critical' }),
        createMockAndonEvent({ id: 'e2', type: 'quality', severity: 'high' }),
        createMockAndonEvent({ id: 'e3', type: 'safety', severity: 'critical' }),
        createMockAndonEvent({ id: 'e4', type: 'safety', severity: 'high' }),
      ];

      act(() => {
        events.forEach((e) => useAndonStore.getState().addEvent(e));
        useAndonStore.getState().setFilterType('quality');
        useAndonStore.getState().setFilterSeverity('critical');
      });

      const filtered = useAndonStore.getState().getFilteredEvents();
      expect(filtered).toHaveLength(1);
      expect(filtered[0].type).toBe('quality');
      expect(filtered[0].severity).toBe('critical');
    });
  });

  describe('Helper Functions', () => {
    describe('getSeverityColor', () => {
      test('returns correct color for critical', () => {
        expect(getSeverityColor('critical')).toBe('#EF4444');
      });

      test('returns correct color for major', () => {
        expect(getSeverityColor('major')).toBe('#F59E0B');
      });

      test('returns correct color for minor', () => {
        expect(getSeverityColor('minor')).toBe('#6B7280');
      });
    });

    describe('getSeverityLabel', () => {
      test('returns correct label for critical', () => {
        expect(getSeverityLabel('critical')).toBe('Critical');
      });

      test('returns correct label for major', () => {
        expect(getSeverityLabel('major')).toBe('Major');
      });

      test('returns correct label for minor', () => {
        expect(getSeverityLabel('minor')).toBe('Minor');
      });
    });

    describe('getAndonTypeLabel', () => {
      test('returns correct label for quality', () => {
        expect(getAndonTypeLabel('quality')).toBe('Quality');
      });

      test('returns correct label for safety', () => {
        expect(getAndonTypeLabel('safety')).toBe('Safety');
      });

      test('returns correct label for material', () => {
        expect(getAndonTypeLabel('material')).toBe('Material');
      });

      test('returns correct label for equipment', () => {
        expect(getAndonTypeLabel('equipment')).toBe('Equipment');
      });

      test('returns correct label for assistance', () => {
        expect(getAndonTypeLabel('assistance')).toBe('Assistance');
      });
    });

    describe('getAndonTypeIcon', () => {
      test('returns icon for each type', () => {
        const types: AndonType[] = ['quality', 'safety', 'material', 'equipment', 'assistance'];
        types.forEach((type) => {
          expect(getAndonTypeIcon(type)).toBeDefined();
          expect(typeof getAndonTypeIcon(type)).toBe('string');
        });
      });
    });

    describe('getStatusLabel', () => {
      test('returns correct label for triggered', () => {
        expect(getStatusLabel('triggered')).toBe('Triggered');
      });

      test('returns correct label for acknowledged', () => {
        expect(getStatusLabel('acknowledged')).toBe('Acknowledged');
      });

      test('returns correct label for in_progress', () => {
        expect(getStatusLabel('in_progress')).toBe('In Progress');
      });

      test('returns correct label for resolved', () => {
        expect(getStatusLabel('resolved')).toBe('Resolved');
      });

      test('returns correct label for escalated', () => {
        expect(getStatusLabel('escalated')).toBe('Escalated');
      });
    });

    describe('getStatusColor', () => {
      test('returns correct color for triggered', () => {
        expect(getStatusColor('triggered')).toBe('#EF4444');
      });

      test('returns correct color for acknowledged', () => {
        expect(getStatusColor('acknowledged')).toBe('#F59E0B');
      });

      test('returns correct color for in_progress', () => {
        expect(getStatusColor('in_progress')).toBe('#3B82F6');
      });

      test('returns correct color for resolved', () => {
        expect(getStatusColor('resolved')).toBe('#10B981');
      });

      test('returns correct color for escalated', () => {
        expect(getStatusColor('escalated')).toBe('#DC2626');
      });
    });

    describe('formatElapsedTime', () => {
      test('formats seconds ago', () => {
        const now = new Date();
        const thirtySecsAgo = new Date(now.getTime() - 30000);
        const result = formatElapsedTime(thirtySecsAgo.toISOString());
        expect(result).toMatch(/\d+s ago/);
      });

      test('formats minutes ago', () => {
        const now = new Date();
        const fiveMinsAgo = new Date(now.getTime() - 5 * 60 * 1000);
        const result = formatElapsedTime(fiveMinsAgo.toISOString());
        expect(result).toMatch(/\d+m ago/);
      });

      test('formats hours ago', () => {
        const now = new Date();
        const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000);
        const result = formatElapsedTime(twoHoursAgo.toISOString());
        expect(result).toMatch(/\d+h.*ago/);
      });

      test('handles Date objects', () => {
        const now = new Date();
        const oneMinAgo = new Date(now.getTime() - 60000);
        const result = formatElapsedTime(oneMinAgo);
        expect(result).toMatch(/\d+m ago/);
      });
    });

    describe('formatDuration', () => {
      test('formats seconds to minutes', () => {
        expect(formatDuration(120)).toBe('2m');
      });

      test('formats seconds to hours and minutes', () => {
        expect(formatDuration(3660)).toBe('1h 1m');
      });

      test('formats large seconds to hours', () => {
        expect(formatDuration(7200)).toBe('2h 0m');
      });

      test('returns 0m for zero', () => {
        expect(formatDuration(0)).toBe('0m');
      });
    });

    describe('calculateEscalationLevel', () => {
      const thresholds = { level1: 5, level2: 15, level3: 30 };

      test('returns 0 for events under threshold', () => {
        const now = new Date();
        const twoMinsAgo = new Date(now.getTime() - 2 * 60 * 1000);
        expect(calculateEscalationLevel(twoMinsAgo.toISOString(), thresholds)).toBe(0);
      });

      test('returns 1 for events over level1 minutes', () => {
        const now = new Date();
        const sixMinsAgo = new Date(now.getTime() - 6 * 60 * 1000);
        expect(calculateEscalationLevel(sixMinsAgo.toISOString(), thresholds)).toBe(1);
      });

      test('returns 2 for events over level2 minutes', () => {
        const now = new Date();
        const twentyMinsAgo = new Date(now.getTime() - 20 * 60 * 1000);
        expect(calculateEscalationLevel(twentyMinsAgo.toISOString(), thresholds)).toBe(2);
      });

      test('returns 3 for events over level3 minutes', () => {
        const now = new Date();
        const fortyMinsAgo = new Date(now.getTime() - 40 * 60 * 1000);
        expect(calculateEscalationLevel(fortyMinsAgo.toISOString(), thresholds)).toBe(3);
      });
    });
  });

  describe('Event Sorting', () => {
    test('active events are sorted by created_at (newest first)', () => {
      const now = new Date();
      const events = [
        createMockAndonEvent({ id: 'e1', severity: 'low', created_at: new Date(now.getTime() - 30000).toISOString() }),
        createMockAndonEvent({ id: 'e2', severity: 'critical', created_at: new Date(now.getTime() - 10000).toISOString() }),
        createMockAndonEvent({ id: 'e3', severity: 'high', created_at: now.toISOString() }),
      ];

      act(() => {
        events.forEach((e) => useAndonStore.getState().addEvent(e));
      });

      const activeEvents = useAndonStore.getState().activeEvents;
      // Events should be sorted by created_at descending (newest first)
      expect(activeEvents[0].id).toBe('e3'); // newest
      expect(activeEvents[1].id).toBe('e2');
      expect(activeEvents[2].id).toBe('e1'); // oldest
    });
  });

  describe('Edge Cases', () => {
    test('updating non-existent event does not throw', () => {
      expect(() => {
        act(() => {
          useAndonStore.getState().updateEvent('non-existent', { description: 'test' });
        });
      }).not.toThrow();
    });

    test('acknowledging non-existent event does not throw', async () => {
      await act(async () => {
        await useAndonStore.getState().acknowledgeEvent('non-existent', 'User');
      });
      expect(true).toBe(true);
    });

    test('resolving non-existent event does not throw', async () => {
      await act(async () => {
        await useAndonStore.getState().resolveEvent('non-existent', 'Resolution');
      });
      expect(true).toBe(true);
    });

    test('escalating non-existent event does not throw', async () => {
      await act(async () => {
        await useAndonStore.getState().escalateEvent('non-existent');
      });
      expect(true).toBe(true);
    });

    test('getFilteredEvents returns empty array when no events', () => {
      expect(useAndonStore.getState().getFilteredEvents()).toEqual([]);
    });

    test('recalculateMetrics handles empty events', () => {
      expect(() => {
        act(() => {
          useAndonStore.getState().recalculateMetrics();
        });
      }).not.toThrow();

      const metrics = useAndonStore.getState().metrics;
      expect(metrics.totalActive).toBe(0);
    });
  });
});
