import { act, renderHook } from '@testing-library/react';
import {
  useKanbanStore,
  getPriorityColor,
  formatCurrency,
  getDaysUntilDue,
  getDueDateStatus,
} from '../kanban-store';
import type { RFQ, RFQStatus, Customer, User } from '@/types';

// Mock the RFQ API
jest.mock('@/api/rfq', () => ({
  rfqApi: {
    update: jest.fn().mockResolvedValue({}),
  },
}));

// Mock localStorage
const mockLocalStorage: Record<string, string> = {};
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: jest.fn((key: string) => mockLocalStorage[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      mockLocalStorage[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete mockLocalStorage[key];
    }),
    clear: jest.fn(() => {
      Object.keys(mockLocalStorage).forEach(key => delete mockLocalStorage[key]);
    }),
  },
  writable: true,
});

// Helper to create mock RFQ
function createMockRFQ(overrides: Partial<RFQ> = {}): RFQ {
  const mockCustomer: Customer = {
    id: 'customer-1',
    name: 'Test Customer',
    code: 'TC001',
    type: 'direct',
    status: 'active',
    tags: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  return {
    id: `rfq-${Math.random().toString(36).substr(2, 9)}`,
    rfq_number: 'RFQ-001',
    customer_id: 'customer-1',
    customer: mockCustomer,
    title: 'Test RFQ',
    status: 'new',
    priority: 'medium',
    due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    received_date: new Date().toISOString(),
    currency: 'USD',
    attachments: [],
    line_items: [],
    tags: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    created_by: 'user-1',
    updated_by: 'user-1',
    ...overrides,
  };
}

describe('kanban-store', () => {
  beforeEach(() => {
    // Reset store state
    const { getState } = useKanbanStore;
    act(() => {
      getState().initializeFromRFQs([]);
      getState().clearFilters();
    });
  });

  describe('initializeFromRFQs', () => {
    it('initializes empty state', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      act(() => {
        result.current.initializeFromRFQs([]);
      });
      
      expect(result.current.cards.size).toBe(0);
    });

    it('groups RFQs by status', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfqs = [
        createMockRFQ({ id: 'rfq-1', status: 'new' }),
        createMockRFQ({ id: 'rfq-2', status: 'new' }),
        createMockRFQ({ id: 'rfq-3', status: 'reviewing' }),
        createMockRFQ({ id: 'rfq-4', status: 'quoting' }),
      ];
      
      act(() => {
        result.current.initializeFromRFQs(rfqs);
      });
      
      expect(result.current.cards.size).toBe(4);
      expect(result.current.getColumnCards('new').length).toBe(2);
      expect(result.current.getColumnCards('reviewing').length).toBe(1);
      expect(result.current.getColumnCards('quoting').length).toBe(1);
    });

    it('creates cards with correct properties', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfq = createMockRFQ({ id: 'rfq-test', status: 'new', title: 'Test RFQ' });
      
      act(() => {
        result.current.initializeFromRFQs([rfq]);
      });
      
      const card = result.current.getCard('rfq-test');
      expect(card).toBeDefined();
      expect(card?.id).toBe('rfq-test');
      expect(card?.columnId).toBe('new');
      expect(card?.rfq.title).toBe('Test RFQ');
    });
  });

  describe('moveCard', () => {
    it('moves card from one column to another', async () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
      
      act(() => {
        result.current.initializeFromRFQs([rfq]);
      });
      
      await act(async () => {
        await result.current.moveCard('rfq-1', 'new', 'reviewing', 0);
      });
      
      expect(result.current.getColumnCards('new').length).toBe(0);
      expect(result.current.getColumnCards('reviewing').length).toBe(1);
      
      const card = result.current.getCard('rfq-1');
      expect(card?.columnId).toBe('reviewing');
      expect(card?.rfq.status).toBe('reviewing');
    });

    it('updates card position after move', async () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfqs = [
        createMockRFQ({ id: 'rfq-1', status: 'reviewing' }),
        createMockRFQ({ id: 'rfq-2', status: 'new' }),
      ];
      
      act(() => {
        result.current.initializeFromRFQs(rfqs);
      });
      
      await act(async () => {
        await result.current.moveCard('rfq-2', 'new', 'reviewing', 0);
      });
      
      const cards = result.current.getColumnCards('reviewing');
      expect(cards.length).toBe(2);
      expect(cards[0].id).toBe('rfq-2');
      expect(cards[0].position).toBe(0);
    });

    it('does nothing for non-existent card', async () => {
      const { result } = renderHook(() => useKanbanStore());
      
      act(() => {
        result.current.initializeFromRFQs([]);
      });
      
      await act(async () => {
        await result.current.moveCard('non-existent', 'new', 'reviewing', 0);
      });
      
      expect(result.current.cards.size).toBe(0);
    });
  });

  describe('reorderCard', () => {
    it('reorders cards within a column', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfqs = [
        createMockRFQ({ id: 'rfq-1', status: 'new' }),
        createMockRFQ({ id: 'rfq-2', status: 'new' }),
        createMockRFQ({ id: 'rfq-3', status: 'new' }),
      ];
      
      act(() => {
        result.current.initializeFromRFQs(rfqs);
      });
      
      act(() => {
        result.current.reorderCard('rfq-1', 'new', 2);
      });
      
      const cards = result.current.getColumnCards('new');
      expect(cards[0].id).toBe('rfq-2');
      expect(cards[1].id).toBe('rfq-3');
      expect(cards[2].id).toBe('rfq-1');
    });
  });

  describe('updateCard', () => {
    it('updates RFQ properties on card', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfq = createMockRFQ({ id: 'rfq-1', title: 'Original Title' });
      
      act(() => {
        result.current.initializeFromRFQs([rfq]);
      });
      
      act(() => {
        result.current.updateCard('rfq-1', { title: 'Updated Title' });
      });
      
      const card = result.current.getCard('rfq-1');
      expect(card?.rfq.title).toBe('Updated Title');
    });
  });

  describe('removeCard', () => {
    it('removes card from store', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
      
      act(() => {
        result.current.initializeFromRFQs([rfq]);
      });
      
      expect(result.current.cards.size).toBe(1);
      
      act(() => {
        result.current.removeCard('rfq-1');
      });
      
      expect(result.current.cards.size).toBe(0);
      expect(result.current.getColumnCards('new').length).toBe(0);
    });
  });

  describe('addCard', () => {
    it('adds new card to column', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      act(() => {
        result.current.initializeFromRFQs([]);
      });
      
      const rfq = createMockRFQ({ id: 'rfq-new', status: 'new' });
      
      act(() => {
        result.current.addCard(rfq, 'new');
      });
      
      expect(result.current.cards.size).toBe(1);
      expect(result.current.getColumnCards('new').length).toBe(1);
    });

    it('adds card at specific position', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const existingRfqs = [
        createMockRFQ({ id: 'rfq-1', status: 'new' }),
        createMockRFQ({ id: 'rfq-2', status: 'new' }),
      ];
      
      act(() => {
        result.current.initializeFromRFQs(existingRfqs);
      });
      
      const newRfq = createMockRFQ({ id: 'rfq-new', status: 'new' });
      
      act(() => {
        result.current.addCard(newRfq, 'new', 1);
      });
      
      const cards = result.current.getColumnCards('new');
      expect(cards[1].id).toBe('rfq-new');
    });
  });

  describe('drag state', () => {
    it('tracks drag start', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
      
      act(() => {
        result.current.initializeFromRFQs([rfq]);
      });
      
      const card = result.current.getCard('rfq-1')!;
      
      act(() => {
        result.current.startDrag(card);
      });
      
      expect(result.current.dragState.isDragging).toBe(true);
      expect(result.current.dragState.activeCard?.id).toBe('rfq-1');
      expect(result.current.dragState.sourceColumn).toBe('new');
    });

    it('tracks drag target', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      act(() => {
        result.current.updateDragTarget('reviewing');
      });
      
      expect(result.current.dragState.targetColumn).toBe('reviewing');
    });

    it('resets drag state on end', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
      
      act(() => {
        result.current.initializeFromRFQs([rfq]);
        const card = result.current.getCard('rfq-1')!;
        result.current.startDrag(card);
      });
      
      act(() => {
        result.current.endDrag();
      });
      
      expect(result.current.dragState.isDragging).toBe(false);
      expect(result.current.dragState.activeCard).toBeNull();
    });
  });

  describe('selection', () => {
    it('selects and deselects cards', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      act(() => {
        result.current.selectCard('rfq-1');
      });
      
      expect(result.current.selectedCardId).toBe('rfq-1');
      
      act(() => {
        result.current.selectCard(null);
      });
      
      expect(result.current.selectedCardId).toBeNull();
    });
  });

  describe('filters', () => {
    it('sets filters', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      act(() => {
        result.current.setFilters({ priority: ['high', 'urgent'] });
      });
      
      expect(result.current.filters.priority).toEqual(['high', 'urgent']);
    });

    it('clears filters', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      act(() => {
        result.current.setFilters({ priority: ['high'] });
        result.current.setSearchQuery('test');
      });
      
      act(() => {
        result.current.clearFilters();
      });
      
      expect(result.current.filters.priority).toEqual([]);
      expect(result.current.searchQuery).toBe('');
    });

    it('filters cards by priority', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfqs = [
        createMockRFQ({ id: 'rfq-1', status: 'new', priority: 'high' }),
        createMockRFQ({ id: 'rfq-2', status: 'new', priority: 'low' }),
        createMockRFQ({ id: 'rfq-3', status: 'new', priority: 'urgent' }),
      ];
      
      act(() => {
        result.current.initializeFromRFQs(rfqs);
        result.current.setFilters({ priority: ['high', 'urgent'] });
      });
      
      const filtered = result.current.getFilteredCards('new');
      expect(filtered.length).toBe(2);
      expect(filtered.find(c => c.id === 'rfq-2')).toBeUndefined();
    });

    it('filters cards by search query', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfqs = [
        createMockRFQ({ id: 'rfq-1', status: 'new', title: 'Widget Assembly' }),
        createMockRFQ({ id: 'rfq-2', status: 'new', title: 'Gadget Manufacturing' }),
      ];
      
      act(() => {
        result.current.initializeFromRFQs(rfqs);
        result.current.setSearchQuery('widget');
      });
      
      const filtered = result.current.getFilteredCards('new');
      expect(filtered.length).toBe(1);
      expect(filtered[0].rfq.title).toBe('Widget Assembly');
    });

    it('filters cards by customer', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfqs = [
        createMockRFQ({ id: 'rfq-1', status: 'new', customer_id: 'cust-1' }),
        createMockRFQ({ id: 'rfq-2', status: 'new', customer_id: 'cust-2' }),
      ];
      
      act(() => {
        result.current.initializeFromRFQs(rfqs);
        result.current.setFilters({ customer: ['cust-1'] });
      });
      
      const filtered = result.current.getFilteredCards('new');
      expect(filtered.length).toBe(1);
      expect(filtered[0].rfq.customer_id).toBe('cust-1');
    });
  });

  describe('config', () => {
    it('updates config', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      act(() => {
        result.current.setConfig({ compactMode: true });
      });
      
      expect(result.current.config.compactMode).toBe(true);
    });

    it('sets WIP limit', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      act(() => {
        result.current.setWipLimit('new', 10);
      });
      
      const column = result.current.config.columns.find(c => c.id === 'new');
      expect(column?.wipLimit).toBe(10);
    });
  });

  describe('getColumnWipStatus', () => {
    it('returns correct WIP status', () => {
      const { result } = renderHook(() => useKanbanStore());
      
      const rfqs = [
        createMockRFQ({ id: 'rfq-1', status: 'reviewing' }),
        createMockRFQ({ id: 'rfq-2', status: 'reviewing' }),
        createMockRFQ({ id: 'rfq-3', status: 'reviewing' }),
        createMockRFQ({ id: 'rfq-4', status: 'reviewing' }),
        createMockRFQ({ id: 'rfq-5', status: 'reviewing' }),
        createMockRFQ({ id: 'rfq-6', status: 'reviewing' }),
      ];
      
      act(() => {
        result.current.initializeFromRFQs(rfqs);
      });
      
      const status = result.current.getColumnWipStatus('reviewing');
      expect(status.count).toBe(6);
      expect(status.limit).toBe(5);
      expect(status.isOverLimit).toBe(true);
    });
  });
});

describe('helper functions', () => {
  describe('getPriorityColor', () => {
    it('returns correct colors for each priority', () => {
      expect(getPriorityColor('urgent')).toBe('#EF4444');
      expect(getPriorityColor('high')).toBe('#F59E0B');
      expect(getPriorityColor('medium')).toBe('#3B82F6');
      expect(getPriorityColor('low')).toBe('#6B7280');
    });
  });

  describe('formatCurrency', () => {
    it('formats USD currency', () => {
      expect(formatCurrency(1234567, 'USD')).toBe('$1,234,567');
    });

    it('formats with default USD', () => {
      expect(formatCurrency(1000)).toBe('$1,000');
    });
  });

  describe('getDaysUntilDue', () => {
    it('returns positive days for future date', () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 5);
      expect(getDaysUntilDue(futureDate.toISOString())).toBe(5);
    });

    it('returns negative days for past date', () => {
      const pastDate = new Date();
      pastDate.setDate(pastDate.getDate() - 3);
      expect(getDaysUntilDue(pastDate.toISOString())).toBe(-3);
    });

    it('returns 0 for today', () => {
      const today = new Date();
      expect(getDaysUntilDue(today.toISOString())).toBe(0);
    });
  });

  describe('getDueDateStatus', () => {
    it('returns overdue for past dates', () => {
      const pastDate = new Date();
      pastDate.setDate(pastDate.getDate() - 1);
      expect(getDueDateStatus(pastDate.toISOString())).toBe('overdue');
    });

    it('returns due-soon for dates within 3 days', () => {
      const soonDate = new Date();
      soonDate.setDate(soonDate.getDate() + 2);
      expect(getDueDateStatus(soonDate.toISOString())).toBe('due-soon');
    });

    it('returns on-track for dates more than 3 days away', () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 10);
      expect(getDueDateStatus(futureDate.toISOString())).toBe('on-track');
    });
  });
});
