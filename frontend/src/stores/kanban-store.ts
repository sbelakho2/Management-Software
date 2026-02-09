'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { RFQ, RFQStatus, UUID, Priority } from '@/types';
import { rfqApi } from '@/api/rfq';

/**
 * Kanban column definition
 */
export interface KanbanColumn {
  id: RFQStatus;
  title: string;
  color: string;
  description: string;
  wipLimit?: number;
}

/**
 * Kanban card representing an RFQ in the pipeline
 */
export interface KanbanCard {
  id: UUID;
  rfq: RFQ;
  position: number;
  columnId: RFQStatus;
}

/**
 * Kanban board configuration
 */
export interface KanbanConfig {
  columns: KanbanColumn[];
  showWipLimits: boolean;
  showAvatars: boolean;
  showDueDates: boolean;
  showValues: boolean;
  compactMode: boolean;
  groupByPriority: boolean;
}

/**
 * Drag and drop state
 */
export interface DragState {
  isDragging: boolean;
  activeCard: KanbanCard | null;
  sourceColumn: RFQStatus | null;
  targetColumn: RFQStatus | null;
}

/**
 * Kanban store state
 */
interface KanbanState {
  cards: Map<UUID, KanbanCard>;
  columnCards: Map<RFQStatus, UUID[]>;
  config: KanbanConfig;
  dragState: DragState;
  selectedCardId: UUID | null;
  filters: KanbanFilters;
  searchQuery: string;
  
  // Actions
  initializeFromRFQs: (rfqs: RFQ[]) => void;
  moveCard: (cardId: UUID, fromColumn: RFQStatus, toColumn: RFQStatus, newPosition: number) => Promise<void>;
  reorderCard: (cardId: UUID, column: RFQStatus, newPosition: number) => void;
  updateCard: (cardId: UUID, updates: Partial<RFQ>) => void;
  removeCard: (cardId: UUID) => void;
  addCard: (rfq: RFQ, column: RFQStatus, position?: number) => void;
  
  // Drag state actions
  startDrag: (card: KanbanCard) => void;
  updateDragTarget: (column: RFQStatus | null) => void;
  endDrag: () => void;
  
  // Selection actions
  selectCard: (cardId: UUID | null) => void;
  
  // Filter actions
  setFilters: (filters: Partial<KanbanFilters>) => void;
  clearFilters: () => void;
  setSearchQuery: (query: string) => void;
  
  // Config actions
  setConfig: (config: Partial<KanbanConfig>) => void;
  toggleColumn: (columnId: RFQStatus, visible: boolean) => void;
  setWipLimit: (columnId: RFQStatus, limit: number | undefined) => void;
  
  // Getters
  getColumnCards: (columnId: RFQStatus) => KanbanCard[];
  getCard: (cardId: UUID) => KanbanCard | undefined;
  getFilteredCards: (columnId: RFQStatus) => KanbanCard[];
  getColumnWipStatus: (columnId: RFQStatus) => { count: number; limit: number | undefined; isOverLimit: boolean };
}

/**
 * Kanban filter options
 */
export interface KanbanFilters {
  priority: Priority[];
  assignee: UUID[];
  customer: UUID[];
  dueDateRange: { start: string | null; end: string | null };
  valueRange: { min: number | null; max: number | null };
  tags: string[];
}

/**
 * Default column configuration
 */
const DEFAULT_COLUMNS: KanbanColumn[] = [
  {
    id: 'new',
    title: 'New',
    color: '#3B82F6',
    description: 'Newly received RFQs awaiting initial review',
    wipLimit: undefined,
  },
  {
    id: 'reviewing',
    title: 'Reviewing',
    color: '#8B5CF6',
    description: 'RFQs under technical and feasibility review',
    wipLimit: 5,
  },
  {
    id: 'quoting',
    title: 'Quoting',
    color: '#F59E0B',
    description: 'Active quote preparation',
    wipLimit: 3,
  },
  {
    id: 'submitted',
    title: 'Submitted',
    color: '#10B981',
    description: 'Quotes sent to customer awaiting response',
    wipLimit: undefined,
  },
  {
    id: 'won',
    title: 'Won',
    color: '#22C55E',
    description: 'Successful quotes converted to orders',
    wipLimit: undefined,
  },
  {
    id: 'lost',
    title: 'Lost',
    color: '#EF4444',
    description: 'Quotes that were not accepted',
    wipLimit: undefined,
  },
  {
    id: 'no_bid',
    title: 'No Bid',
    color: '#6B7280',
    description: 'RFQs declined to quote',
    wipLimit: undefined,
  },
];

/**
 * Default configuration
 */
const DEFAULT_CONFIG: KanbanConfig = {
  columns: DEFAULT_COLUMNS,
  showWipLimits: true,
  showAvatars: true,
  showDueDates: true,
  showValues: true,
  compactMode: false,
  groupByPriority: false,
};

/**
 * Default filters
 */
const DEFAULT_FILTERS: KanbanFilters = {
  priority: [],
  assignee: [],
  customer: [],
  dueDateRange: { start: null, end: null },
  valueRange: { min: null, max: null },
  tags: [],
};

/**
 * Kanban board store
 */
export const useKanbanStore = create<KanbanState>()(
  persist(
    (set, get) => ({
      cards: new Map(),
      columnCards: new Map(),
      config: DEFAULT_CONFIG,
      dragState: {
        isDragging: false,
        activeCard: null,
        sourceColumn: null,
        targetColumn: null,
      },
      selectedCardId: null,
      filters: DEFAULT_FILTERS,
      searchQuery: '',

      initializeFromRFQs: (rfqs: RFQ[]) => {
        const cards = new Map<UUID, KanbanCard>();
        const columnCards = new Map<RFQStatus, UUID[]>();

        // Initialize column arrays
        for (const column of DEFAULT_COLUMNS) {
          columnCards.set(column.id, []);
        }

        // Group RFQs by status and create cards
        rfqs.forEach((rfq, index) => {
          const card: KanbanCard = {
            id: rfq.id,
            rfq,
            position: index,
            columnId: rfq.status,
          };
          cards.set(rfq.id, card);

          const columnList = columnCards.get(rfq.status) || [];
          columnList.push(rfq.id);
          columnCards.set(rfq.status, columnList);
        });

        // Sort cards within each column by position
        for (const [status, cardIds] of columnCards) {
          const sortedIds = cardIds.sort((a, b) => {
            const cardA = cards.get(a);
            const cardB = cards.get(b);
            return (cardA?.position || 0) - (cardB?.position || 0);
          });
          columnCards.set(status, sortedIds);
        }

        set({ cards, columnCards });
      },

      moveCard: async (cardId: UUID, fromColumn: RFQStatus, toColumn: RFQStatus, newPosition: number) => {
        const { cards, columnCards } = get();
        const card = cards.get(cardId);
        
        if (!card) return;

        // Remove from source column
        const sourceCards = [...(columnCards.get(fromColumn) || [])];
        const sourceIndex = sourceCards.indexOf(cardId);
        if (sourceIndex > -1) {
          sourceCards.splice(sourceIndex, 1);
        }

        // Add to target column at new position
        const targetCards = [...(columnCards.get(toColumn) || [])];
        const insertIndex = Math.min(newPosition, targetCards.length);
        targetCards.splice(insertIndex, 0, cardId);

        // Update card
        const updatedCard: KanbanCard = {
          ...card,
          columnId: toColumn,
          position: insertIndex,
          rfq: {
            ...card.rfq,
            status: toColumn,
          },
        };

        // Update positions for all cards in target column
        const newCards = new Map(cards);
        newCards.set(cardId, updatedCard);
        
        targetCards.forEach((id, index) => {
          const existingCard = newCards.get(id);
          if (existingCard) {
            newCards.set(id, { ...existingCard, position: index });
          }
        });

        const newColumnCards = new Map(columnCards);
        newColumnCards.set(fromColumn, sourceCards);
        newColumnCards.set(toColumn, targetCards);

        set({ cards: newCards, columnCards: newColumnCards });

        try {
          await rfqApi.update(cardId, { status: toColumn });
        } catch (error) {
          console.error('Failed to persist status change:', error);
          // Rollback state on failure
          set({ cards, columnCards });
          throw error;
        }
      },

      reorderCard: (cardId: UUID, column: RFQStatus, newPosition: number) => {
        const { cards, columnCards } = get();
        const columnCardIds = [...(columnCards.get(column) || [])];
        
        const currentIndex = columnCardIds.indexOf(cardId);
        if (currentIndex === -1) return;

        // Remove from current position
        columnCardIds.splice(currentIndex, 1);
        
        // Insert at new position
        const insertIndex = Math.min(newPosition, columnCardIds.length);
        columnCardIds.splice(insertIndex, 0, cardId);

        // Update positions
        const newCards = new Map(cards);
        columnCardIds.forEach((id, index) => {
          const existingCard = newCards.get(id);
          if (existingCard) {
            newCards.set(id, { ...existingCard, position: index });
          }
        });

        const newColumnCards = new Map(columnCards);
        newColumnCards.set(column, columnCardIds);

        set({ cards: newCards, columnCards: newColumnCards });
      },

      updateCard: (cardId: UUID, updates: Partial<RFQ>) => {
        const { cards } = get();
        const card = cards.get(cardId);
        
        if (!card) return;

        const newCards = new Map(cards);
        newCards.set(cardId, {
          ...card,
          rfq: { ...card.rfq, ...updates },
        });

        set({ cards: newCards });
      },

      removeCard: (cardId: UUID) => {
        const { cards, columnCards } = get();
        const card = cards.get(cardId);
        
        if (!card) return;

        const newCards = new Map(cards);
        newCards.delete(cardId);

        const newColumnCards = new Map(columnCards);
        const columnCardIds = [...(newColumnCards.get(card.columnId) || [])];
        const index = columnCardIds.indexOf(cardId);
        if (index > -1) {
          columnCardIds.splice(index, 1);
          newColumnCards.set(card.columnId, columnCardIds);
        }

        set({ cards: newCards, columnCards: newColumnCards });
      },

      addCard: (rfq: RFQ, column: RFQStatus, position?: number) => {
        const { cards, columnCards } = get();
        const columnCardIds = [...(columnCards.get(column) || [])];
        const insertPos = position ?? columnCardIds.length;

        const card: KanbanCard = {
          id: rfq.id,
          rfq,
          position: insertPos,
          columnId: column,
        };

        const newCards = new Map(cards);
        newCards.set(rfq.id, card);

        columnCardIds.splice(insertPos, 0, rfq.id);

        // Update positions
        columnCardIds.forEach((id, index) => {
          const existingCard = newCards.get(id);
          if (existingCard) {
            newCards.set(id, { ...existingCard, position: index });
          }
        });

        const newColumnCards = new Map(columnCards);
        newColumnCards.set(column, columnCardIds);

        set({ cards: newCards, columnCards: newColumnCards });
      },

      startDrag: (card: KanbanCard) => {
        set({
          dragState: {
            isDragging: true,
            activeCard: card,
            sourceColumn: card.columnId,
            targetColumn: null,
          },
        });
      },

      updateDragTarget: (column: RFQStatus | null) => {
        set((state) => ({
          dragState: { ...state.dragState, targetColumn: column },
        }));
      },

      endDrag: () => {
        set({
          dragState: {
            isDragging: false,
            activeCard: null,
            sourceColumn: null,
            targetColumn: null,
          },
        });
      },

      selectCard: (cardId: UUID | null) => {
        set({ selectedCardId: cardId });
      },

      setFilters: (filters: Partial<KanbanFilters>) => {
        set((state) => ({
          filters: { ...state.filters, ...filters },
        }));
      },

      clearFilters: () => {
        set({ filters: DEFAULT_FILTERS, searchQuery: '' });
      },

      setSearchQuery: (query: string) => {
        set({ searchQuery: query });
      },

      setConfig: (config: Partial<KanbanConfig>) => {
        set((state) => ({
          config: { ...state.config, ...config },
        }));
      },

      toggleColumn: (columnId: RFQStatus, visible: boolean) => {
        const { config } = get();
        const columns = config.columns.map((col) =>
          col.id === columnId ? { ...col, visible } : col
        );
        set({ config: { ...config, columns } });
      },

      setWipLimit: (columnId: RFQStatus, limit: number | undefined) => {
        const { config } = get();
        const columns = config.columns.map((col) =>
          col.id === columnId ? { ...col, wipLimit: limit } : col
        );
        set({ config: { ...config, columns } });
      },

      getColumnCards: (columnId: RFQStatus): KanbanCard[] => {
        const { cards, columnCards } = get();
        const cardIds = columnCards.get(columnId) || [];
        return cardIds
          .map((id) => cards.get(id))
          .filter((card): card is KanbanCard => card !== undefined);
      },

      getCard: (cardId: UUID): KanbanCard | undefined => {
        return get().cards.get(cardId);
      },

      getFilteredCards: (columnId: RFQStatus): KanbanCard[] => {
        const { filters, searchQuery } = get();
        const columnCardsList = get().getColumnCards(columnId);

        return columnCardsList.filter((card) => {
          const rfq = card.rfq;

          // Search query filter
          if (searchQuery) {
            const query = searchQuery.toLowerCase();
            const searchableText = [
              rfq.rfq_number,
              rfq.title,
              rfq.description,
              rfq.customer?.name,
              ...rfq.tags,
            ]
              .filter(Boolean)
              .join(' ')
              .toLowerCase();
            
            if (!searchableText.includes(query)) {
              return false;
            }
          }

          // Priority filter
          if (filters.priority.length > 0 && !filters.priority.includes(rfq.priority)) {
            return false;
          }

          // Assignee filter
          if (filters.assignee.length > 0) {
            if (!rfq.assigned_to || !filters.assignee.includes(rfq.assigned_to)) {
              return false;
            }
          }

          // Customer filter
          if (filters.customer.length > 0 && !filters.customer.includes(rfq.customer_id)) {
            return false;
          }

          // Due date range filter
          if (filters.dueDateRange.start || filters.dueDateRange.end) {
            const dueDate = new Date(rfq.due_date);
            if (filters.dueDateRange.start && dueDate < new Date(filters.dueDateRange.start)) {
              return false;
            }
            if (filters.dueDateRange.end && dueDate > new Date(filters.dueDateRange.end)) {
              return false;
            }
          }

          // Value range filter
          if (filters.valueRange.min !== null || filters.valueRange.max !== null) {
            const value = rfq.estimated_value || 0;
            if (filters.valueRange.min !== null && value < filters.valueRange.min) {
              return false;
            }
            if (filters.valueRange.max !== null && value > filters.valueRange.max) {
              return false;
            }
          }

          // Tags filter
          if (filters.tags.length > 0) {
            const hasMatchingTag = filters.tags.some((tag) => rfq.tags.includes(tag));
            if (!hasMatchingTag) {
              return false;
            }
          }

          return true;
        });
      },

      getColumnWipStatus: (columnId: RFQStatus) => {
        const { config } = get();
        const columnConfig = config.columns.find((col) => col.id === columnId);
        const count = get().getFilteredCards(columnId).length;
        const limit = columnConfig?.wipLimit;

        return {
          count,
          limit,
          isOverLimit: limit !== undefined && count > limit,
        };
      },
    }),
    {
      name: 'kanban-store',
      partialize: (state) => ({
        config: state.config,
        filters: state.filters,
      }),
      // Defensive merge: ensure Map-typed fields are never overwritten by plain objects from localStorage
      merge: (persisted, current) => ({
        ...current,
        ...(persisted as Partial<KanbanState>),
        cards: current.cards,
        columnCards: current.columnCards,
      } as KanbanState),
      // Custom serialization for Maps
      storage: {
        getItem: (name) => {
          const item = localStorage.getItem(name);
          if (!item) return null;
          return JSON.parse(item);
        },
        setItem: (name, value) => {
          localStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: (name) => {
          localStorage.removeItem(name);
        },
      },
    }
  )
);

/**
 * Priority color helper
 */
export function getPriorityColor(priority: Priority): string {
  switch (priority) {
    case 'urgent':
      return '#EF4444';
    case 'high':
      return '#F59E0B';
    case 'medium':
      return '#3B82F6';
    case 'low':
      return '#6B7280';
    default:
      return '#6B7280';
  }
}

/**
 * Format currency helper - re-exports from centralized utils
 * This ensures consistency with user's display currency preferences
 */
import { formatCurrency as formatCurrencyFromUtils } from '@/lib/utils';

export function formatCurrency(amount: number, currency?: string): string {
  return formatCurrencyFromUtils(amount, currency);
}

/**
 * Get days until due
 */
export function getDaysUntilDue(dueDate: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dueDate);
  due.setHours(0, 0, 0, 0);
  return Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

/**
 * Get due date status
 */
export function getDueDateStatus(dueDate: string): 'overdue' | 'due-soon' | 'on-track' {
  const days = getDaysUntilDue(dueDate);
  if (days < 0) return 'overdue';
  if (days <= 3) return 'due-soon';
  return 'on-track';
}
