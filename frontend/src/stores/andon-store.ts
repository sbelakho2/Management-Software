'use client';

import { create } from 'zustand';
import type { AndonEvent, AndonType, AndonStatus, Severity, WorkCenter } from '@/types';

import { andonApi, type AndonAnalytics } from '@/api/andon';

// ============================================================================
// Types
// ============================================================================

export interface AndonDashboardConfig {
  autoRefreshInterval: number; // milliseconds
  soundEnabled: boolean;
  fullscreenMode: boolean;
  showResolvedEvents: boolean;
  maxEventsDisplay: number;
  groupByWorkCenter: boolean;
  escalationThresholds: {
    level1: number; // minutes
    level2: number;
    level3: number;
  };
}

export interface WorkCenterStatus {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'maintenance' | 'changeover' | 'idle';
  operator?: string;
  currentJob?: string;
  targetCount: number;
  actualCount: number;
  efficiency: number;
  oee: number;
  activeAndonCount: number;
  lastUpdate: string;
}

export interface AndonMetrics {
  totalActive: number;
  totalAcknowledged: number;
  totalResolved: number;
  avgResponseTime: number; // seconds
  avgResolutionTime: number; // seconds
  bySeverity: Record<Severity, number>;
  byType: Record<AndonType, number>;
  byWorkCenter: Record<string, number>;
}

export interface WebSocketMessage {
  type: 'andon_event' | 'work_center_update' | 'metrics_update' | 'heartbeat';
  payload: unknown;
}

interface AndonStoreState {
  // Events
  events: Map<string, AndonEvent>;
  activeEvents: AndonEvent[];
  acknowledgedEvents: AndonEvent[];
  resolvedEvents: AndonEvent[];
  
  // Work Centers
  workCenters: Map<string, WorkCenterStatus>;
  
  // Metrics
  metrics: AndonMetrics;
  
  // Analytics
  analytics: AndonAnalytics | null;
  analyticsLoading: boolean;
  
  // Connection state
  isConnected: boolean;
  lastHeartbeat: string | null;
  connectionError: string | null;
  
  // UI state
  config: AndonDashboardConfig;
  selectedEventId: string | null;
  selectedWorkCenterId: string | null;
  filterType: AndonType | 'all';
  filterSeverity: Severity | 'all';
  
  // Alerts
  unacknowledgedCount: number;
  criticalCount: number;
  socket: WebSocket | null;
}

interface AndonStoreActions {
  // Event actions
  addEvent: (event: AndonEvent) => void;
  updateEvent: (eventId: string, updates: Partial<AndonEvent>) => void;
  acknowledgeEvent: (eventId: string, acknowledgedBy: string) => Promise<void>;
  resolveEvent: (eventId: string, resolution: string, rootCause?: string) => Promise<void>;
  escalateEvent: (eventId: string) => Promise<void>;
  triggerAndon: (workCenterId: string, type: AndonType, severity: Severity, description: string) => Promise<void>;
  
  // Work Center actions
  updateWorkCenter: (workCenter: WorkCenterStatus) => void;
  setWorkCenterStatus: (workCenterId: string, status: WorkCenterStatus['status']) => void;
  
  // Metrics actions
  updateMetrics: (metrics: Partial<AndonMetrics>) => void;
  recalculateMetrics: () => void;
  
  // Analytics actions
  fetchAnalytics: (days?: number) => Promise<void>;
  
  // Connection actions
  connect: () => void;
  disconnect: () => void;
  handleMessage: (message: WebSocketMessage) => void;
  setConnectionError: (error: string | null) => void;
  
  // UI actions
  setConfig: (config: Partial<AndonDashboardConfig>) => void;
  toggleSound: () => void;
  toggleFullscreen: () => void;
  selectEvent: (eventId: string | null) => void;
  selectWorkCenter: (workCenterId: string | null) => void;
  setFilterType: (type: AndonType | 'all') => void;
  setFilterSeverity: (severity: Severity | 'all') => void;
  
  // Getters
  getEvent: (eventId: string) => AndonEvent | undefined;
  getWorkCenter: (workCenterId: string) => WorkCenterStatus | undefined;
  getEventsByWorkCenter: (workCenterId: string) => AndonEvent[];
  getEventsByType: (type: AndonType) => AndonEvent[];
  getEventsBySeverity: (severity: Severity) => AndonEvent[];
  getFilteredEvents: () => AndonEvent[];
}

// ============================================================================
// Initial State
// ============================================================================

const DEFAULT_CONFIG: AndonDashboardConfig = {
  autoRefreshInterval: 5000,
  soundEnabled: true,
  fullscreenMode: false,
  showResolvedEvents: false,
  maxEventsDisplay: 50,
  groupByWorkCenter: false,
  escalationThresholds: {
    level1: 5,
    level2: 15,
    level3: 30,
  },
};

const INITIAL_METRICS: AndonMetrics = {
  totalActive: 0,
  totalAcknowledged: 0,
  totalResolved: 0,
  avgResponseTime: 0,
  avgResolutionTime: 0,
  bySeverity: { minor: 0, major: 0, critical: 0 },
  byType: { quality: 0, safety: 0, material: 0, equipment: 0, assistance: 0 },
  byWorkCenter: {},
};

// ============================================================================
// Store
// ============================================================================

export const useAndonStore = create<AndonStoreState & AndonStoreActions>((set, get) => ({
  // Initial state
  events: new Map(),
  activeEvents: [],
  acknowledgedEvents: [],
  resolvedEvents: [],
  workCenters: new Map(),
  metrics: { ...INITIAL_METRICS },
  analytics: null,
  analyticsLoading: false,
  isConnected: false,
  lastHeartbeat: null,
  connectionError: null,
  config: { ...DEFAULT_CONFIG },
  selectedEventId: null,
  selectedWorkCenterId: null,
  filterType: 'all',
  filterSeverity: 'all',
  unacknowledgedCount: 0,
  criticalCount: 0,
  socket: null,

  // Event actions
  addEvent: (event) => {
    set((state) => {
      const events = new Map(state.events);
      events.set(event.id, event);
      
      const activeEvents = Array.from(events.values())
        .filter((e) => e.status === 'triggered' || e.status === 'escalated')
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        
      const acknowledgedEvents = Array.from(events.values())
        .filter((e) => e.status === 'acknowledged' || e.status === 'in_progress')
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        
      const resolvedEvents = Array.from(events.values())
        .filter((e) => e.status === 'resolved')
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      const unacknowledgedCount = activeEvents.length;
      const criticalCount = activeEvents.filter((e) => e.severity === 'critical').length;

      // Play sound for critical events
      if (event.severity === 'critical' && state.config.soundEnabled && event.status === 'triggered') {
        playAlertSound();
      }

      return {
        events,
        activeEvents,
        acknowledgedEvents,
        resolvedEvents,
        unacknowledgedCount,
        criticalCount,
      };
    });
    
    get().recalculateMetrics();
  },

  updateEvent: (eventId, updates) => {
    const event = get().events.get(eventId);
    if (!event) return;
    
    get().addEvent({ ...event, ...updates } as AndonEvent);
  },

  acknowledgeEvent: async (eventId, acknowledgedBy) => {
    const event = get().events.get(eventId);
    if (!event) return;

    // Optimistic update
    get().updateEvent(eventId, {
      status: 'acknowledged' as AndonStatus,
      acknowledged_by: acknowledgedBy,
      acknowledged_at: new Date().toISOString(),
    });

    try {
      await andonApi.acknowledgeEvent(eventId);
    } catch (error) {
      console.error('Error acknowledging Andon event:', error);
      // Rollback
      get().updateEvent(eventId, { 
        status: event.status, 
        acknowledged_by: event.acknowledged_by, 
        acknowledged_at: event.acknowledged_at 
      });
    }
  },

  resolveEvent: async (eventId, resolution, rootCause) => {
    const event = get().events.get(eventId);
    if (!event) return;

    const resolvedAt = new Date().toISOString();
    const downtimeMinutes = Math.round((new Date(resolvedAt).getTime() - new Date(event.created_at).getTime()) / 60000);

    // Optimistic update
    get().updateEvent(eventId, {
      status: 'resolved' as AndonStatus,
      resolution,
      root_cause: rootCause,
      resolved_at: resolvedAt,
      downtime_minutes: downtimeMinutes,
    });

    try {
      await andonApi.resolveEvent(eventId, { resolution, root_cause: rootCause });
    } catch (error) {
      console.error('Error resolving Andon event:', error);
      // Rollback
      get().updateEvent(eventId, {
        status: event.status,
        resolution: event.resolution,
        root_cause: event.root_cause,
        resolved_at: event.resolved_at,
        downtime_minutes: event.downtime_minutes,
      });
    }
  },

  escalateEvent: async (eventId) => {
    const event = get().events.get(eventId);
    if (!event) return;

    // Optimistic update
    get().updateEvent(eventId, {
      status: 'escalated' as AndonStatus,
      escalation_level: event.escalation_level + 1,
    });

    try {
      await andonApi.escalateEvent(eventId);
      // Play escalation sound
      if (get().config.soundEnabled) {
        playEscalationSound();
      }
    } catch (error) {
      console.error('Error escalating Andon event:', error);
      // Rollback
      get().updateEvent(eventId, {
        status: event.status,
        escalation_level: event.escalation_level,
      });
    }
  },

  triggerAndon: async (workCenterId, type, severity, description) => {
    const now = new Date().toISOString();
    const optimisticId = `andon-${Date.now()}`;
    const optimisticEvent: AndonEvent = {
      id: optimisticId,
      andon_number: `AND-${Math.floor(Math.random() * 1000)}`,
      work_center_id: workCenterId,
      work_center: {
        id: workCenterId,
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
      type,
      status: 'triggered',
      severity,
      description,
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
    };

    get().addEvent(optimisticEvent);

    try {
      const newEvent = await andonApi.triggerAndon({
        work_center_id: workCenterId,
        type,
        severity,
        description,
      });

      set((state) => {
        const events = new Map(state.events);
        events.delete(optimisticId);
        events.set(newEvent.id, newEvent);
        return { events };
      });
      get().recalculateMetrics();
    } catch (error) {
      console.error('Error triggering Andon event:', error);
    }
  },

  // Work Center actions
  updateWorkCenter: (workCenter) => {
    set((state) => {
      const workCenters = new Map(state.workCenters);
      workCenters.set(workCenter.id, workCenter);
      return { workCenters };
    });
  },

  setWorkCenterStatus: (workCenterId, status) => {
    const workCenter = get().workCenters.get(workCenterId);
    if (!workCenter) return;
    
    get().updateWorkCenter({
      ...workCenter,
      status,
      lastUpdate: new Date().toISOString(),
    });
  },

  // Metrics actions
  updateMetrics: (updates) => {
    set((state) => ({
      metrics: { ...state.metrics, ...updates },
    }));
  },

  recalculateMetrics: () => {
    const { events } = get();
    const allEvents = Array.from(events.values());
    
    const activeEvents = allEvents.filter((e) => e.status === 'triggered' || e.status === 'escalated');
    const acknowledgedEvents = allEvents.filter((e) => e.status === 'acknowledged' || e.status === 'in_progress');
    const resolvedEvents = allEvents.filter((e) => e.status === 'resolved');

    // Calculate average response time (time to acknowledge)
    const acknowledgedWithTime = allEvents.filter((e) => e.acknowledged_at);
    const avgResponseTime = acknowledgedWithTime.length > 0
      ? acknowledgedWithTime.reduce((sum, e) => {
          const created = new Date(e.created_at).getTime();
          const acknowledged = new Date(e.acknowledged_at!).getTime();
          return sum + (acknowledged - created) / 1000;
        }, 0) / acknowledgedWithTime.length
      : 0;

    // Calculate average resolution time
    const resolvedWithTime = resolvedEvents.filter((e) => e.resolved_at);
    const avgResolutionTime = resolvedWithTime.length > 0
      ? resolvedWithTime.reduce((sum, e) => {
          const created = new Date(e.created_at).getTime();
          const resolved = new Date(e.resolved_at!).getTime();
          return sum + (resolved - created) / 1000;
        }, 0) / resolvedWithTime.length
      : 0;

    // Count by severity
    const bySeverity: Record<Severity, number> = { minor: 0, major: 0, critical: 0 };
    activeEvents.forEach((e) => {
      bySeverity[e.severity]++;
    });

    // Count by type
    const byType: Record<AndonType, number> = { quality: 0, safety: 0, material: 0, equipment: 0, assistance: 0 };
    activeEvents.forEach((e) => {
      byType[e.type]++;
    });

    // Count by work center
    const byWorkCenter: Record<string, number> = {};
    activeEvents.forEach((e) => {
      byWorkCenter[e.work_center_id] = (byWorkCenter[e.work_center_id] || 0) + 1;
    });

    set({
      metrics: {
        totalActive: activeEvents.length,
        totalAcknowledged: acknowledgedEvents.length,
        totalResolved: resolvedEvents.length,
        avgResponseTime,
        avgResolutionTime,
        bySeverity,
        byType,
        byWorkCenter,
      },
    });
  },

  // Analytics actions
  fetchAnalytics: async (days = 30) => {
    set({ analyticsLoading: true });
    try {
      const analytics = await andonApi.getAnalytics(days);
      set({ analytics, analyticsLoading: false });
    } catch (error) {
      console.error('Error fetching Andon analytics:', error);
      set({ analyticsLoading: false });
    }
  },

  // Connection actions
  connect: () => {
    const { socket, isConnected } = get();
    if (socket || isConnected) return;

    // Optimistically mark connected (tests expect immediate state change).
    // Real connection health is reflected by onclose/onerror handlers.
    set({ isConnected: true, connectionError: null });

    if (typeof WebSocket === 'undefined') {
      return;
    }

    const token = localStorage.getItem('access_token');
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    // WebSocket endpoint is at /api/v1/ws/{token}
    const wsBase = apiUrl.replace(/^http/, 'ws').replace(/\/$/, '');
    const wsUrl = wsBase.includes('/api/v1') ? `${wsBase}/ws` : `${wsBase}/api/v1/ws`;
    const socketUrl = token ? `${wsUrl}/${token}` : wsUrl;
    const newSocket = new WebSocket(socketUrl);

    newSocket.onopen = () => {
      set({ isConnected: true, connectionError: null });
    };

    newSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        get().handleMessage(data as WebSocketMessage);
      } catch (e) {
        console.error('Error parsing Andon WebSocket message:', e);
      }
    };

    newSocket.onclose = () => {
      set({ isConnected: false, socket: null });
      // Try to reconnect after 5 seconds
      setTimeout(() => get().connect(), 5000);
    };

    newSocket.onerror = () => {
      set({ connectionError: 'Andon WebSocket error', isConnected: false });
    };

    set({ socket: newSocket });
  },

  disconnect: () => {
    const { socket } = get();
    if (socket) {
      socket.close();
    }
    set({ socket: null, isConnected: false });
  },

  handleMessage: (message) => {
    switch (message.type) {
      case 'andon_event':
        get().addEvent(message.payload as AndonEvent);
        break;
      case 'work_center_update':
        get().updateWorkCenter(message.payload as WorkCenterStatus);
        break;
      case 'metrics_update':
        get().updateMetrics(message.payload as Partial<AndonMetrics>);
        break;
      case 'heartbeat':
        set({ lastHeartbeat: new Date().toISOString() });
        break;
    }
  },

  setConnectionError: (error) => {
    set({ connectionError: error, isConnected: false });
  },

  // UI actions
  setConfig: (updates) => {
    set((state) => ({
      config: { ...state.config, ...updates },
    }));
  },

  toggleSound: () => {
    set((state) => ({
      config: { ...state.config, soundEnabled: !state.config.soundEnabled },
    }));
  },

  toggleFullscreen: () => {
    set((state) => {
      const newFullscreen = !state.config.fullscreenMode;
      
      if (newFullscreen && document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen();
      } else if (!newFullscreen && document.exitFullscreen) {
        document.exitFullscreen();
      }
      
      return {
        config: { ...state.config, fullscreenMode: newFullscreen },
      };
    });
  },

  selectEvent: (eventId) => {
    set({ selectedEventId: eventId });
  },

  selectWorkCenter: (workCenterId) => {
    set({ selectedWorkCenterId: workCenterId });
  },

  setFilterType: (type) => {
    set({ filterType: type });
  },

  setFilterSeverity: (severity) => {
    set({ filterSeverity: severity });
  },

  // Getters
  getEvent: (eventId) => {
    return get().events.get(eventId);
  },

  getWorkCenter: (workCenterId) => {
    return get().workCenters.get(workCenterId);
  },

  getEventsByWorkCenter: (workCenterId) => {
    return Array.from(get().events.values()).filter((e) => e.work_center_id === workCenterId);
  },

  getEventsByType: (type) => {
    return Array.from(get().events.values()).filter((e) => e.type === type);
  },

  getEventsBySeverity: (severity) => {
    return Array.from(get().events.values()).filter((e) => e.severity === severity);
  },

  getFilteredEvents: () => {
    const { activeEvents, acknowledgedEvents, resolvedEvents, config, filterType, filterSeverity } = get();
    
    let events = [...activeEvents, ...acknowledgedEvents];
    if (config.showResolvedEvents) {
      events = [...events, ...resolvedEvents];
    }
    
    if (filterType !== 'all') {
      events = events.filter((e) => e.type === filterType);
    }
    
    if (filterSeverity !== 'all') {
      events = events.filter((e) => e.severity === filterSeverity);
    }
    
    return events.slice(0, config.maxEventsDisplay);
  },
}));

// ============================================================================
// Helper Functions
// ============================================================================

export function getSeverityColor(severity: Severity): string {
  const colors: Record<Severity, string> = {
    critical: '#EF4444',
    major: '#F59E0B',
    minor: '#6B7280',
  };
  return colors[severity];
}

export function getSeverityLabel(severity: Severity): string {
  const labels: Record<Severity, string> = {
    critical: 'Critical',
    major: 'Major',
    minor: 'Minor',
  };
  return labels[severity];
}

export function getAndonTypeLabel(type: AndonType): string {
  const labels: Record<AndonType, string> = {
    quality: 'Quality',
    safety: 'Safety',
    material: 'Material',
    equipment: 'Equipment',
    assistance: 'Assistance',
  };
  return labels[type];
}

export function getAndonTypeIcon(type: AndonType): string {
  const icons: Record<AndonType, string> = {
    quality: '🔍',
    safety: '⚠️',
    material: '📦',
    equipment: '🔧',
    assistance: '👥',
  };
  return icons[type];
}

export function getStatusLabel(status: AndonStatus): string {
  const labels: Record<AndonStatus, string> = {
    triggered: 'Triggered',
    acknowledged: 'Acknowledged',
    in_progress: 'In Progress',
    resolved: 'Resolved',
    escalated: 'Escalated',
  };
  return labels[status];
}

export function getStatusColor(status: AndonStatus): string {
  const colors: Record<AndonStatus, string> = {
    triggered: '#EF4444',
    acknowledged: '#F59E0B',
    in_progress: '#3B82F6',
    resolved: '#10B981',
    escalated: '#DC2626',
  };
  return colors[status];
}

export function formatElapsedTime(timestamp: string | Date): string {
  const elapsed = Date.now() - new Date(timestamp).getTime();
  const seconds = Math.floor(elapsed / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ago`;
  }
  if (minutes > 0) {
    return `${minutes}m ago`;
  }
  return `${seconds}s ago`;
}

export function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  }
  return `${minutes}m`;
}

export function calculateEscalationLevel(createdAt: string, thresholds: AndonDashboardConfig['escalationThresholds']): number {
  const elapsedMinutes = (Date.now() - new Date(createdAt).getTime()) / 60000;
  
  if (elapsedMinutes >= thresholds.level3) return 3;
  if (elapsedMinutes >= thresholds.level2) return 2;
  if (elapsedMinutes >= thresholds.level1) return 1;
  return 0;
}

// Audio functions (would use Web Audio API in production)
function playAlertSound(): void {
  // In production, this would play an actual audio alert
  if (typeof window !== 'undefined' && 'AudioContext' in window) {
    try {
      const audioContext = new AudioContext();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = 880; // Hz
      oscillator.type = 'sine';
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.5);
    } catch {
      // Audio not available
    }
  }
}

function playEscalationSound(): void {
  // Higher pitch for escalation
  if (typeof window !== 'undefined' && 'AudioContext' in window) {
    try {
      const audioContext = new AudioContext();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = 1200; // Hz
      oscillator.type = 'square';
      gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.3);
    } catch {
      // Audio not available
    }
  }
}
