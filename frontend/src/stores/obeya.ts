import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

type ObeyaCategory = 
  | 'issue' | 'action' | 'risk' | 'decision' | 'milestone' 
  | 'kpi' | 'escalation' | 'information' | 'lesson_learned'
  | 'metrics' | 'schedule' | 'quality' | 'cost' | 'safety' 
  | 'morale' | 'delivery' | 'strategy';

type ObeyaStatus = 'new' | 'in_progress' | 'blocked' | 'waiting' | 'completed' | 'cancelled';
type ObeyaPriority = 'low' | 'medium' | 'high' | 'critical';
type ObeyaBoard = 'daily' | 'weekly' | 'project' | 'strategic' | 'quality' | 'safety' | 'improvement';

interface ObeyaItem {
  id: string;
  board: ObeyaBoard;
  column?: string;
  position: number;
  title: string;
  description?: string;
  category: ObeyaCategory;
  status: ObeyaStatus;
  priority: ObeyaPriority;
  color?: string;
  related_entity_type?: string;
  related_entity_id?: string;
  assigned_to_id?: string;
  assigned_to_name?: string;
  due_date?: string;
  target_date?: string;
  completed_at?: string;
  blocked_reason?: string;
  resolution?: string;
  decision_outcome?: string;
  decision_rationale?: string;
  kpi_target?: string;
  kpi_actual?: string;
  kpi_unit?: string;
  kpi_trend?: 'improving' | 'stable' | 'declining';
  is_escalated: boolean;
  escalated_to_id?: string;
  escalated_to_name?: string;
  escalated_at?: string;
  escalation_reason?: string;
  days_open?: number;
  days_overdue?: number;
  attachments?: any[];
  links?: any[];
  tags?: string[];
  meeting_date?: string;
  meeting_type?: string;
  notes?: string;
  custom_fields?: Record<string, any>;
  comments_count: number;
  created_at: string;
  updated_at: string;
  created_by_id: string;
  created_by_name: string;
}

interface ObeyaComment {
  id: string;
  item_id: string;
  author_id: string;
  author_name: string;
  content: string;
  parent_id?: string;
  is_status_change: boolean;
  old_status?: string;
  new_status?: string;
  is_pinned: boolean;
  is_edited: boolean;
  edited_at?: string;
  mentions?: string[];
  attachments?: any[];
  created_at: string;
}

interface ObeyaStats {
  total_items: number;
  by_status: Record<ObeyaStatus, number>;
  by_priority: Record<ObeyaPriority, number>;
  by_category: Record<ObeyaCategory, number>;
  overdue_count: number;
  escalated_count: number;
  completed_this_week: number;
  avg_days_to_complete: number;
}

interface SQDCPMetrics {
  safety: {
    incidents: number;
    days_since_last_incident: number;
    near_misses: number;
    training_completion: number;
    status: 'green' | 'yellow' | 'red';
  };
  quality: {
    first_pass_yield: number;
    defect_rate: number;
    customer_complaints: number;
    ncr_open: number;
    status: 'green' | 'yellow' | 'red';
  };
  delivery: {
    on_time_delivery: number;
    lead_time_days: number;
    schedule_adherence: number;
    backlog_items: number;
    status: 'green' | 'yellow' | 'red';
  };
  cost: {
    variance_percent: number;
    cost_savings: number;
    waste_reduction: number;
    budget_utilization: number;
    status: 'green' | 'yellow' | 'red';
  };
  people: {
    morale_score: number;
    training_hours: number;
    attendance_rate: number;
    active_improvements: number;
    status: 'green' | 'yellow' | 'red';
  };
}

interface ObeyaState {
  items: ObeyaItem[];
  stats: ObeyaStats;
  sqdcpMetrics: SQDCPMetrics | null;
  cognitiveInsights: any | null;
  selectedBoard: ObeyaBoard;
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
  socket: WebSocket | null;
  isConnected: boolean;

  fetchItems: (board?: ObeyaBoard) => Promise<void>;
  fetchItemById: (id: string) => Promise<ObeyaItem | null>;
  fetchSQDCPMetrics: () => Promise<void>;
  fetchCognitiveInsights: () => Promise<void>;
  createItem: (item: Partial<ObeyaItem>) => Promise<ObeyaItem>;
  updateItem: (id: string, updates: Partial<ObeyaItem>) => Promise<ObeyaItem>;
  deleteItem: (id: string) => Promise<void>;
  moveItem: (id: string, column: string, position: number) => Promise<void>;
  addComment: (itemId: string, comment: Partial<ObeyaComment>) => Promise<ObeyaComment>;
  fetchComments: (itemId: string) => Promise<ObeyaComment[]>;
  escalateItem: (id: string, reason: string, escalatedToId: string) => Promise<void>;
  resolveItem: (id: string, resolution: string) => Promise<void>;
  setSelectedBoard: (board: ObeyaBoard) => void;
  clearError: () => void;
  connect: () => void;
  disconnect: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const initialStats: ObeyaStats = {
  total_items: 0,
  by_status: {
    new: 0,
    in_progress: 0,
    blocked: 0,
    waiting: 0,
    completed: 0,
    cancelled: 0,
  },
  by_priority: {
    low: 0,
    medium: 0,
    high: 0,
    critical: 0,
  },
  by_category: {
    issue: 0,
    action: 0,
    risk: 0,
    decision: 0,
    milestone: 0,
    kpi: 0,
    escalation: 0,
    information: 0,
    lesson_learned: 0,
    metrics: 0,
    schedule: 0,
    quality: 0,
    cost: 0,
    safety: 0,
    morale: 0,
    delivery: 0,
    strategy: 0,
  },
  overdue_count: 0,
  escalated_count: 0,
  completed_this_week: 0,
  avg_days_to_complete: 0,
};

export const useObeyaStore = create<ObeyaState>()(
  devtools(
    persist(
      (set, get) => ({
        items: [],
        stats: initialStats,
        sqdcpMetrics: null,
        selectedBoard: 'daily',
        isLoading: false,
        error: null,
        lastFetchedAt: null,
        socket: null,
        isConnected: false,

        connect: () => {
          const { socket, isConnected } = get();
          if (socket || isConnected) return;

          const token = localStorage.getItem('access_token');
          if (!token) return;

          const wsUrl = API_BASE_URL.replace('http', 'ws').replace('/api/v1', '/ws');
          const newSocket = new WebSocket(`${wsUrl}/${token}`);

          newSocket.onopen = () => {
            set({ isConnected: true });
            console.log('Obeya WebSocket connected');
          };

          newSocket.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              if (data.type === 'metric_update') {
                // Refresh metrics when they change
                get().fetchSQDCPMetrics();
                get().fetchCognitiveInsights();
              }
              if (data.type === 'silo_alert') {
                get().fetchCognitiveInsights();
              }
            } catch (e) {
              console.error('Error parsing Obeya WebSocket message:', e);
            }
          };

          newSocket.onclose = () => {
            set({ isConnected: false, socket: null });
            console.log('Obeya WebSocket disconnected');
            // Try to reconnect after 5 seconds
            setTimeout(() => get().connect(), 5000);
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

        fetchItems: async (board?: ObeyaBoard) => {
          const { lastFetchedAt, selectedBoard } = get();
          const now = Date.now();
          const targetBoard = board || selectedBoard;

          // Cache for 30 seconds
          if (lastFetchedAt && now - lastFetchedAt < 30000) {
            return;
          }

          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/items?board=${targetBoard}`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to fetch Obeya items: ${response.statusText}`);
            }

            const data = await response.json();
            const items: ObeyaItem[] = data.items || [];

            // Calculate stats
            const stats: ObeyaStats = {
              total_items: items.length,
              by_status: items.reduce((acc, item) => {
                acc[item.status] = (acc[item.status] || 0) + 1;
                return acc;
              }, {} as Record<ObeyaStatus, number>),
              by_priority: items.reduce((acc, item) => {
                acc[item.priority] = (acc[item.priority] || 0) + 1;
                return acc;
              }, {} as Record<ObeyaPriority, number>),
              by_category: items.reduce((acc, item) => {
                acc[item.category] = (acc[item.category] || 0) + 1;
                return acc;
              }, {} as Record<ObeyaCategory, number>),
              overdue_count: items.filter(i => i.days_overdue && i.days_overdue > 0).length,
              escalated_count: items.filter(i => i.is_escalated).length,
              completed_this_week: items.filter(i => {
                if (!i.completed_at) return false;
                const completedDate = new Date(i.completed_at);
                const weekAgo = new Date();
                weekAgo.setDate(weekAgo.getDate() - 7);
                return completedDate >= weekAgo;
              }).length,
              avg_days_to_complete: 0, // Calculated on backend
            };

            set({
              items,
              stats,
              selectedBoard: targetBoard,
              lastFetchedAt: now,
              isLoading: false,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch Obeya items',
              isLoading: false,
            });
          }
        },

        fetchItemById: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/items/${id}`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to fetch Obeya item: ${response.statusText}`);
            }

            const item: ObeyaItem = await response.json();

            set(state => ({
              items: state.items.map(i => i.id === id ? item : i),
              isLoading: false,
            }));

            return item;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch Obeya item',
              isLoading: false,
            });
            return null;
          }
        },

        fetchSQDCPMetrics: async () => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/sqdcp-metrics`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to fetch SQDCP metrics: ${response.statusText}`);
            }

            const metrics: SQDCPMetrics = await response.json();

            set({ sqdcpMetrics: metrics, isLoading: false });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch SQDCP metrics',
              isLoading: false,
            });
          }
        },

        fetchCognitiveInsights: async () => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/cognitive-obeya/dashboard`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to fetch Cognitive insights: ${response.statusText}`);
            }

            const data = await response.json();
            set({ cognitiveInsights: data.data, isLoading: false });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch Cognitive insights',
              isLoading: false,
            });
          }
        },

        createItem: async (itemData: Partial<ObeyaItem>) => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/items`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
              body: JSON.stringify(itemData),
            });

            if (!response.ok) {
              throw new Error(`Failed to create Obeya item: ${response.statusText}`);
            }

            const item: ObeyaItem = await response.json();

            set(state => ({
              items: [item, ...state.items],
              stats: {
                ...state.stats,
                total_items: state.stats.total_items + 1,
              },
              isLoading: false,
            }));

            return item;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to create Obeya item',
              isLoading: false,
            });
            throw error;
          }
        },

        updateItem: async (id: string, updates: Partial<ObeyaItem>) => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/items/${id}`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
              body: JSON.stringify(updates),
            });

            if (!response.ok) {
              throw new Error(`Failed to update Obeya item: ${response.statusText}`);
            }

            const item: ObeyaItem = await response.json();

            set(state => ({
              items: state.items.map(i => i.id === id ? item : i),
              isLoading: false,
            }));

            return item;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to update Obeya item',
              isLoading: false,
            });
            throw error;
          }
        },

        deleteItem: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/items/${id}`, {
              method: 'DELETE',
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to delete Obeya item: ${response.statusText}`);
            }

            set(state => ({
              items: state.items.filter(i => i.id !== id),
              stats: {
                ...state.stats,
                total_items: Math.max(0, state.stats.total_items - 1),
              },
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete Obeya item',
              isLoading: false,
            });
            throw error;
          }
        },

        moveItem: async (id: string, column: string, position: number) => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/items/${id}/move`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
              body: JSON.stringify({ column, position }),
            });

            if (!response.ok) {
              throw new Error(`Failed to move Obeya item: ${response.statusText}`);
            }

            const item: ObeyaItem = await response.json();

            set(state => ({
              items: state.items.map(i => i.id === id ? item : i),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to move Obeya item',
              isLoading: false,
            });
            throw error;
          }
        },

        addComment: async (itemId: string, commentData: Partial<ObeyaComment>) => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/items/${itemId}/comments`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
              body: JSON.stringify(commentData),
            });

            if (!response.ok) {
              throw new Error(`Failed to add comment: ${response.statusText}`);
            }

            const comment: ObeyaComment = await response.json();

            // Update item comment count
            set(state => ({
              items: state.items.map(i => 
                i.id === itemId 
                  ? { ...i, comments_count: i.comments_count + 1 }
                  : i
              ),
              isLoading: false,
            }));

            return comment;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to add comment',
              isLoading: false,
            });
            throw error;
          }
        },

        fetchComments: async (itemId: string) => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/items/${itemId}/comments`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            });

            if (!response.ok) {
              throw new Error(`Failed to fetch comments: ${response.statusText}`);
            }

            const comments: ObeyaComment[] = await response.json();
            set({ isLoading: false });
            return comments;
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch comments',
              isLoading: false,
            });
            return [];
          }
        },

        escalateItem: async (id: string, reason: string, escalatedToId: string) => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/items/${id}/escalate`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
              body: JSON.stringify({ reason, escalated_to_id: escalatedToId }),
            });

            if (!response.ok) {
              throw new Error(`Failed to escalate item: ${response.statusText}`);
            }

            const item: ObeyaItem = await response.json();

            set(state => ({
              items: state.items.map(i => i.id === id ? item : i),
              stats: {
                ...state.stats,
                escalated_count: state.stats.escalated_count + 1,
              },
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to escalate item',
              isLoading: false,
            });
            throw error;
          }
        },

        resolveItem: async (id: string, resolution: string) => {
          set({ isLoading: true, error: null });
          try {
            const response = await fetch(`${API_BASE_URL}/obeya/items/${id}/resolve`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
              body: JSON.stringify({ resolution }),
            });

            if (!response.ok) {
              throw new Error(`Failed to resolve item: ${response.statusText}`);
            }

            const item: ObeyaItem = await response.json();

            set(state => ({
              items: state.items.map(i => i.id === id ? item : i),
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to resolve item',
              isLoading: false,
            });
            throw error;
          }
        },

        setSelectedBoard: (board: ObeyaBoard) => {
          set({ selectedBoard: board });
          get().fetchItems(board);
        },

        clearError: () => set({ error: null }),
      }),
      {
        name: 'obeya-storage',
        partialize: (state) => ({
          items: state.items,
          stats: state.stats,
          sqdcpMetrics: state.sqdcpMetrics,
          cognitiveInsights: state.cognitiveInsights,
          selectedBoard: state.selectedBoard,
          lastFetchedAt: state.lastFetchedAt,
        }),
      }
    )
  )
);
