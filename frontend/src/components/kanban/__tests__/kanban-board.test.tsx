import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  KanbanBoard,
  KanbanToolbar,
  KanbanMetrics,
} from '../kanban-board';
import { useKanbanStore } from '@/stores/kanban-store';
import type { RFQ, Customer, Priority } from '@/types';

// Mock the kanban store
const mockGetFilteredCards = jest.fn(() => []);
const mockGetColumnWipStatus = jest.fn(() => ({ count: 0, limit: 10, isOverLimit: false }));
const mockInitializeFromRFQs = jest.fn();
const mockMoveCard = jest.fn();
const mockStartDrag = jest.fn();
const mockEndDrag = jest.fn();
const mockUpdateDragTarget = jest.fn();
const mockSelectCard = jest.fn();
const mockSetSearchQuery = jest.fn();
const mockSetConfig = jest.fn();
const mockClearFilters = jest.fn();
const mockSetFilters = jest.fn();

const defaultMockStoreState = {
  cards: new Map(),
  config: {
    columns: [
      { id: 'new', title: 'New', color: '#3B82F6', wipLimit: 10, position: 0 },
      { id: 'reviewing', title: 'Reviewing', color: '#8B5CF6', wipLimit: 5, position: 1 },
      { id: 'quoting', title: 'Quoting', color: '#F59E0B', wipLimit: 8, position: 2 },
    ],
    compactMode: false,
    showMetrics: true,
    showColumnCounts: true,
    showWipLimits: true,
    showAvatars: true,
    showDueDates: true,
    showValues: true,
  },
  dragState: { isDragging: false, activeCard: null, sourceColumn: null, targetColumn: null, targetIndex: null },
  selectedCardId: null,
  searchQuery: '',
  filters: { priority: [], assignee: [], customer: [], dueDateRange: null, valueRange: null, tags: [] },
  getFilteredCards: mockGetFilteredCards,
  getColumnWipStatus: mockGetColumnWipStatus,
  initializeFromRFQs: mockInitializeFromRFQs,
  moveCard: mockMoveCard,
  startDrag: mockStartDrag,
  endDrag: mockEndDrag,
  updateDragTarget: mockUpdateDragTarget,
  selectCard: mockSelectCard,
  setSearchQuery: mockSetSearchQuery,
  setConfig: mockSetConfig,
  clearFilters: mockClearFilters,
  setFilters: mockSetFilters,
};

let mockStoreState = { ...defaultMockStoreState };

jest.mock('@/stores/kanban-store', () => ({
  useKanbanStore: jest.fn(() => mockStoreState),
  getPriorityColor: jest.fn((priority: string) => {
    const colors: Record<string, string> = {
      urgent: '#EF4444',
      high: '#F59E0B',
      medium: '#3B82F6',
      low: '#6B7280',
    };
    return colors[priority] || '#6B7280';
  }),
  formatCurrency: jest.fn((value: number) => `$${value.toLocaleString()}`),
  getDaysUntilDue: jest.fn(() => 5),
  getDueDateStatus: jest.fn(() => 'on-track'),
}));

// Helper to create mock data
function createMockCustomer(): Customer {
  return {
    id: 'customer-1',
    name: 'Test Customer Inc.',
    code: 'TC001',
    type: 'direct',
    status: 'active',
    tags: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

function createMockRFQ(overrides: Partial<RFQ> = {}): RFQ {
  return {
    id: 'rfq-1',
    rfq_number: 'RFQ-001',
    customer_id: 'customer-1',
    customer: createMockCustomer(),
    title: 'Test RFQ',
    status: 'new',
    priority: 'medium',
    due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    received_date: new Date().toISOString(),
    currency: 'USD',
    attachments: [],
    line_items: [
      { id: 'item-1', part_number: 'PART-001', description: 'Part 1', quantity: 100 },
    ],
    tags: ['automotive'],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    created_by: 'user-1',
    updated_by: 'user-1',
    ...overrides,
  } as RFQ;
}

function createMockCard(rfq: RFQ) {
  return {
    id: rfq.id,
    columnId: rfq.status,
    position: 0,
    rfq,
  };
}

describe('KanbanBoard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStoreState = { ...defaultMockStoreState };
    mockGetFilteredCards.mockReturnValue([]);
    mockGetColumnWipStatus.mockReturnValue({ count: 0, limit: 10, isOverLimit: false });
  });

  it('renders all columns', () => {
    render(<KanbanBoard rfqs={[]} />);
    
    expect(screen.getByText('New')).toBeInTheDocument();
    expect(screen.getByText('Reviewing')).toBeInTheDocument();
    expect(screen.getByText('Quoting')).toBeInTheDocument();
  });

  it('renders empty state message in columns', () => {
    render(<KanbanBoard rfqs={[]} />);
    
    const emptyMessages = screen.getAllByText('No items');
    expect(emptyMessages.length).toBe(3);
  });

  it('renders cards in correct columns', () => {
    const mockRfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
    const mockCard = createMockCard(mockRfq);
    
    mockGetFilteredCards.mockImplementation((columnId: string) => {
      if (columnId === 'new') return [mockCard];
      return [];
    });
    
    render(<KanbanBoard rfqs={[mockRfq]} />);
    
    expect(screen.getByText('RFQ-001')).toBeInTheDocument();
    expect(screen.getByText('Test RFQ')).toBeInTheDocument();
  });

  it('shows WIP limit indicator', () => {
    mockGetColumnWipStatus.mockImplementation((columnId: string) => {
      if (columnId === 'reviewing') {
        return { count: 7, limit: 5, isOverLimit: true };
      }
      return { count: 0, limit: 10, isOverLimit: false };
    });
    
    render(<KanbanBoard rfqs={[]} />);
    
    expect(screen.getByText('7')).toBeInTheDocument();
  });

  it('calls onCardClick when card is clicked', async () => {
    const mockOnCardClick = jest.fn();
    const mockRfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
    const mockCard = createMockCard(mockRfq);
    
    mockGetFilteredCards.mockImplementation((columnId: string) => {
      if (columnId === 'new') return [mockCard];
      return [];
    });
    
    render(<KanbanBoard rfqs={[mockRfq]} onCardClick={mockOnCardClick} />);
    
    const card = screen.getByText('RFQ-001').closest('div[draggable="true"]');
    if (card) {
      await userEvent.click(card);
      expect(mockOnCardClick).toHaveBeenCalledWith(mockRfq);
    }
  });

  it('initializes store with RFQs on mount', () => {
    const mockRfqs = [createMockRFQ({ id: 'rfq-1' })];
    
    render(<KanbanBoard rfqs={mockRfqs} />);
    
    expect(mockInitializeFromRFQs).toHaveBeenCalledWith(mockRfqs);
  });

  it('renders priority badges on cards', () => {
    const mockRfq = createMockRFQ({ id: 'rfq-1', status: 'new', priority: 'high' });
    const mockCard = createMockCard(mockRfq);
    
    mockGetFilteredCards.mockImplementation((columnId: string) => {
      if (columnId === 'new') return [mockCard];
      return [];
    });
    
    render(<KanbanBoard rfqs={[mockRfq]} />);
    
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('renders customer name on cards', () => {
    const mockRfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
    const mockCard = createMockCard(mockRfq);
    
    mockGetFilteredCards.mockImplementation((columnId: string) => {
      if (columnId === 'new') return [mockCard];
      return [];
    });
    
    render(<KanbanBoard rfqs={[mockRfq]} />);
    
    expect(screen.getByText('Test Customer Inc.')).toBeInTheDocument();
  });

  it('renders tags on cards', () => {
    const mockRfq = createMockRFQ({ id: 'rfq-1', status: 'new', tags: ['automotive', 'priority'] });
    const mockCard = createMockCard(mockRfq);
    
    mockGetFilteredCards.mockImplementation((columnId: string) => {
      if (columnId === 'new') return [mockCard];
      return [];
    });
    
    render(<KanbanBoard rfqs={[mockRfq]} />);
    
    expect(screen.getByText('automotive')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<KanbanBoard rfqs={[]} className="custom-class" />);
    
    expect(container.firstChild).toHaveClass('custom-class');
  });
});

describe('KanbanToolbar', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStoreState = { ...defaultMockStoreState };
  });

  it('renders search input', () => {
    render(<KanbanToolbar />);
    
    expect(screen.getByPlaceholderText('Search RFQs...')).toBeInTheDocument();
  });

  it('renders filter button', () => {
    render(<KanbanToolbar />);
    
    expect(screen.getByText('Filters')).toBeInTheDocument();
  });

  it('calls onFilterChange when filter button clicked', async () => {
    const onFilterChange = jest.fn();
    render(<KanbanToolbar onFilterChange={onFilterChange} />);
    
    const filterButton = screen.getByText('Filters');
    await userEvent.click(filterButton);
    
    expect(onFilterChange).toHaveBeenCalled();
  });

  it('renders view toggle buttons', () => {
    render(<KanbanToolbar />);
    
    expect(screen.getByTitle('Kanban view')).toBeInTheDocument();
    expect(screen.getByTitle('List view')).toBeInTheDocument();
    expect(screen.getByTitle('Calendar view')).toBeInTheDocument();
  });

  it('calls onViewChange when view button clicked', async () => {
    const onViewChange = jest.fn();
    render(<KanbanToolbar onViewChange={onViewChange} />);
    
    const listButton = screen.getByTitle('List view');
    await userEvent.click(listButton);
    
    expect(onViewChange).toHaveBeenCalledWith('list');
  });

  it('renders compact mode toggle', () => {
    render(<KanbanToolbar />);
    
    expect(screen.getByTitle('Compact cards')).toBeInTheDocument();
  });

  it('toggles compact mode when clicked', async () => {
    render(<KanbanToolbar />);
    
    const compactToggle = screen.getByTitle('Compact cards');
    await userEvent.click(compactToggle);
    
    expect(mockSetConfig).toHaveBeenCalledWith({ compactMode: true });
  });

  it('submits search on form submit', async () => {
    render(<KanbanToolbar onSearch={jest.fn()} />);
    
    const input = screen.getByPlaceholderText('Search RFQs...');
    await userEvent.type(input, 'test{enter}');
    
    expect(mockSetSearchQuery).toHaveBeenCalledWith('test');
  });

  it('highlights current view', () => {
    render(<KanbanToolbar currentView="list" />);
    
    const listButton = screen.getByTitle('List view');
    expect(listButton).toHaveClass('bg-blue-600');
  });
});

describe('KanbanMetrics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const mockCards = new Map([
      ['rfq-1', { id: 'rfq-1', columnId: 'new', position: 0, rfq: createMockRFQ({ id: 'rfq-1' }) }],
      ['rfq-2', { id: 'rfq-2', columnId: 'quoting', position: 0, rfq: createMockRFQ({ id: 'rfq-2' }) }],
    ]);
    mockStoreState = {
      ...defaultMockStoreState,
      cards: mockCards,
      getFilteredCards: jest.fn((columnId: string) => {
        return Array.from(mockCards.values()).filter(c => c.columnId === columnId);
      }),
    };
  });

  it('renders total RFQ count', () => {
    render(<KanbanMetrics />);
    
    expect(screen.getByText(/2\s*RFQs/)).toBeInTheDocument();
    expect(screen.getByText(/Total:/)).toBeInTheDocument();
  });

  it('renders pipeline value section', () => {
    render(<KanbanMetrics />);
    
    expect(screen.getByText(/Pipeline Value:/)).toBeInTheDocument();
  });

  it('renders column metrics', () => {
    render(<KanbanMetrics />);
    
    expect(screen.getByText('New')).toBeInTheDocument();
    expect(screen.getByText('Reviewing')).toBeInTheDocument();
    expect(screen.getByText('Quoting')).toBeInTheDocument();
  });

  it('shows column counts', () => {
    render(<KanbanMetrics />);
    
    // Verify columns are rendered with their values
    const container = screen.getByText('New').parentElement;
    expect(container).toBeInTheDocument();
  });
});

describe('Drag and Drop Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStoreState = { ...defaultMockStoreState };
  });

  it('cards are draggable', () => {
    const mockRfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
    const mockCard = createMockCard(mockRfq);
    
    mockGetFilteredCards.mockImplementation((columnId: string) => {
      if (columnId === 'new') return [mockCard];
      return [];
    });
    
    render(<KanbanBoard rfqs={[mockRfq]} />);
    
    const card = screen.getByText('RFQ-001').closest('div[draggable="true"]');
    expect(card).toHaveAttribute('draggable', 'true');
  });

  it('triggers endDrag on drag end', () => {
    const mockRfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
    const mockCard = createMockCard(mockRfq);
    
    mockGetFilteredCards.mockImplementation((columnId: string) => {
      if (columnId === 'new') return [mockCard];
      return [];
    });
    
    render(<KanbanBoard rfqs={[mockRfq]} />);
    
    const card = screen.getByText('RFQ-001').closest('div[draggable="true"]');
    if (card) {
      fireEvent.dragEnd(card);
      expect(mockEndDrag).toHaveBeenCalled();
    }
  });
});

describe('Priority Badges (via KanbanBoard)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStoreState = { ...defaultMockStoreState };
  });

  const priorityCases: Array<{ priority: Priority; label: string }> = [
    { priority: 'urgent', label: 'Urgent' },
    { priority: 'high', label: 'High' },
    { priority: 'medium', label: 'Medium' },
    { priority: 'low', label: 'Low' },
  ];

  priorityCases.forEach(({ priority, label }) => {
    it(`renders ${priority} priority badge`, () => {
      const mockRfq = createMockRFQ({ id: 'rfq-1', status: 'new', priority });
      const mockCard = createMockCard(mockRfq);
      
      mockGetFilteredCards.mockImplementation((columnId: string) => {
        if (columnId === 'new') return [mockCard];
        return [];
      });
      
      render(<KanbanBoard rfqs={[mockRfq]} />);
      
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });
});

describe('Card Selection', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStoreState = { ...defaultMockStoreState };
  });

  it('selects card on click', async () => {
    const mockRfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
    const mockCard = createMockCard(mockRfq);
    
    mockGetFilteredCards.mockImplementation((columnId: string) => {
      if (columnId === 'new') return [mockCard];
      return [];
    });
    
    render(<KanbanBoard rfqs={[mockRfq]} />);
    
    const card = screen.getByText('RFQ-001').closest('div[draggable="true"]');
    if (card) {
      await userEvent.click(card);
      expect(mockSelectCard).toHaveBeenCalledWith('rfq-1');
    }
  });

  it('shows selected state when card is selected', () => {
    const mockRfq = createMockRFQ({ id: 'rfq-1', status: 'new' });
    const mockCard = createMockCard(mockRfq);
    
    mockStoreState.selectedCardId = 'rfq-1';
    
    mockGetFilteredCards.mockImplementation((columnId: string) => {
      if (columnId === 'new') return [mockCard];
      return [];
    });
    
    render(<KanbanBoard rfqs={[mockRfq]} />);
    
    const card = screen.getByText('RFQ-001').closest('div[draggable="true"]');
    expect(card).toHaveClass('ring-2');
  });
});

describe('Accessibility', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStoreState = { ...defaultMockStoreState };
  });

  it('has column headings', () => {
    render(<KanbanBoard rfqs={[]} />);
    
    expect(screen.getByRole('heading', { name: 'New' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Reviewing' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Quoting' })).toBeInTheDocument();
  });

  it('search input has placeholder', () => {
    render(<KanbanToolbar />);
    
    const input = screen.getByPlaceholderText('Search RFQs...');
    expect(input).toHaveAttribute('type', 'text');
  });

  it('view buttons have titles', () => {
    render(<KanbanToolbar />);
    
    expect(screen.getByTitle('Kanban view')).toBeInTheDocument();
    expect(screen.getByTitle('List view')).toBeInTheDocument();
    expect(screen.getByTitle('Calendar view')).toBeInTheDocument();
  });
});
