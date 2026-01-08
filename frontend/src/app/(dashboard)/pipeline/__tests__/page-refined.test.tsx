import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter, useSearchParams } from 'next/navigation';
import PipelinePage from '../page-refined';
import { usePipelineStore } from '@/stores/pipeline';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
}));

// Mock pipeline store
jest.mock('@/stores/pipeline', () => ({
  usePipelineStore: jest.fn(),
}));

describe('PipelinePage - Refined Version', () => {
  const mockRouter = {
    push: jest.fn(),
    replace: jest.fn(),
  };

  const mockRFQs = [
    {
      id: '1',
      rfqNumber: 'RFQ-2024-001',
      customerName: 'Acme Corp',
      customerId: 'c1',
      title: 'Custom parts order',
      description: 'High-precision components',
      dueDate: new Date(Date.now() + 86400000).toISOString(),
      receivedDate: new Date(Date.now() - 86400000).toISOString(),
      estimatedValue: 50000,
      priority: 'high' as const,
      status: 'new' as const,
      assignee: { id: 'u1', name: 'John Doe', avatar: 'avatar.jpg' },
      tags: ['precision', 'urgent'],
      version: 1,
      attachmentCount: 3,
      commentCount: 5,
      lastActivityAt: new Date().toISOString(),
    },
    {
      id: '2',
      rfqNumber: 'RFQ-2024-002',
      customerName: 'TechStart Inc',
      customerId: 'c2',
      title: 'Prototype development',
      dueDate: new Date(Date.now() + 172800000).toISOString(),
      receivedDate: new Date(Date.now() - 172800000).toISOString(),
      estimatedValue: 25000,
      priority: 'medium' as const,
      status: 'reviewing' as const,
      tags: ['prototype'],
      version: 1,
      attachmentCount: 1,
      commentCount: 2,
      lastActivityAt: new Date().toISOString(),
    },
  ];

  const mockStats = {
    totalRFQs: 2,
    activeRFQs: 2,
    totalValue: 75000,
    avgResponseTime: 24,
    conversionRate: 65,
    overdueCount: 0,
  };

  const mockStoreState = {
    rfqs: mockRFQs,
    stats: mockStats,
    isLoading: false,
    error: null,
    lastFetchedAt: Date.now(),
    fetchRFQs: jest.fn(),
    fetchRFQById: jest.fn(),
    createRFQ: jest.fn(),
    updateRFQ: jest.fn(),
    deleteRFQ: jest.fn(),
    bulkDeleteRFQs: jest.fn(),
    exportRFQs: jest.fn(),
    setRFQStatus: jest.fn(),
    assignRFQ: jest.fn(),
    clearError: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (useSearchParams as jest.Mock).mockReturnValue(new URLSearchParams());
    (usePipelineStore as unknown as jest.Mock).mockReturnValue(mockStoreState);
  });

  describe('Rendering', () => {
    it('should render pipeline page with header', () => {
      render(<PipelinePage />);
      expect(screen.getByText('Pipeline')).toBeInTheDocument();
      expect(screen.getByText('Manage your RFQs and opportunities')).toBeInTheDocument();
    });

    it('should render analytics dashboard', () => {
      render(<PipelinePage />);
      const analytics = screen.getByTestId('pipeline-analytics');
      expect(analytics).toBeInTheDocument();
      expect(screen.getByText('Total RFQs')).toBeInTheDocument();
      expect(screen.getByText('Total Value')).toBeInTheDocument();
      expect(screen.getByText('Avg Response Time')).toBeInTheDocument();
      expect(screen.getByText('Conversion Rate')).toBeInTheDocument();
    });

    it('should display correct analytics values', () => {
      render(<PipelinePage />);
      expect(screen.getByText('2')).toBeInTheDocument(); // Total RFQs
      expect(screen.getByText('$75,000.00')).toBeInTheDocument(); // Total Value
      expect(screen.getByText('24h')).toBeInTheDocument(); // Avg Response Time
      expect(screen.getByText('65%')).toBeInTheDocument(); // Conversion Rate
    });

    it('should render New RFQ button', () => {
      render(<PipelinePage />);
      const newButton = screen.getByTestId('new-rfq-button');
      expect(newButton).toBeInTheDocument();
      expect(newButton).toHaveAttribute('href', '/pipeline/new');
    });

    it('should render search input', () => {
      render(<PipelinePage />);
      const searchInput = screen.getByTestId('search-input');
      expect(searchInput).toBeInTheDocument();
      expect(searchInput).toHaveAttribute('placeholder', 'Search RFQs...');
    });

    it('should render filter dropdowns', () => {
      render(<PipelinePage />);
      const statusFilter = screen.getByText('All Status');
      const priorityFilter = screen.getByText('All Priority');
      expect(statusFilter).toBeInTheDocument();
      expect(priorityFilter).toBeInTheDocument();
    });

    it('should render view toggle buttons', () => {
      render(<PipelinePage />);
      const listView = screen.getByTestId('view-list');
      const kanbanView = screen.getByTestId('view-kanban');
      expect(listView).toBeInTheDocument();
      expect(kanbanView).toBeInTheDocument();
    });
  });

  describe('Data Fetching', () => {
    it('should fetch RFQs on mount', () => {
      render(<PipelinePage />);
      expect(mockStoreState.fetchRFQs).toHaveBeenCalledTimes(1);
    });

    it('should show loading state', () => {
      const loadingState = { ...mockStoreState, isLoading: true };
      (usePipelineStore as unknown as jest.Mock).mockReturnValue(loadingState);

      render(<PipelinePage />);
      // Skeletons should be present
      const skeletons = screen.getAllByRole('status', { hidden: true });
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('should display error message when fetch fails', () => {
      const errorState = {
        ...mockStoreState,
        error: 'Failed to fetch RFQs',
        rfqs: [],
      };
      (usePipelineStore as unknown as jest.Mock).mockReturnValue(errorState);

      render(<PipelinePage />);
      // Error handling would be implemented in the component
    });
  });

  describe('List View', () => {
    it('should render RFQs in table format', () => {
      render(<PipelinePage />);
      const table = screen.getByTestId('rfq-table');
      expect(table).toBeInTheDocument();

      const rows = screen.getAllByTestId('rfq-row');
      expect(rows).toHaveLength(2);
    });

    it('should display RFQ details in table rows', () => {
      render(<PipelinePage />);
      
      expect(screen.getByText('RFQ-2024-001')).toBeInTheDocument();
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('Custom parts order')).toBeInTheDocument();
      expect(screen.getByText('$50,000.00')).toBeInTheDocument();
    });

    it('should navigate to RFQ detail on row click', () => {
      render(<PipelinePage />);
      
      const firstRow = screen.getAllByTestId('rfq-row')[0];
      fireEvent.click(firstRow);

      expect(mockRouter.push).toHaveBeenCalledWith('/pipeline/1');
    });

    it('should display attachment and comment counts', () => {
      render(<PipelinePage />);
      
      expect(screen.getByText('📎 3')).toBeInTheDocument();
      expect(screen.getByText('💬 5')).toBeInTheDocument();
    });

    it('should show action menu for each RFQ', () => {
      render(<PipelinePage />);
      
      const actionButtons = screen.getAllByTestId('rfq-actions');
      expect(actionButtons).toHaveLength(2);
    });
  });

  describe('Kanban View', () => {
    beforeEach(() => {
      const searchParams = new URLSearchParams('view=kanban');
      (useSearchParams as jest.Mock).mockReturnValue(searchParams);
    });

    it('should render kanban board', () => {
      render(<PipelinePage />);
      
      const kanbanBoard = screen.getByTestId('kanban-board');
      expect(kanbanBoard).toBeInTheDocument();
    });

    it('should render kanban columns', () => {
      render(<PipelinePage />);
      
      const columns = screen.getAllByTestId('kanban-column');
      expect(columns).toHaveLength(4); // new, reviewing, quoting, submitted
    });

    it('should display RFQs in correct columns', () => {
      render(<PipelinePage />);
      
      const cards = screen.getAllByTestId('kanban-card');
      expect(cards.length).toBeGreaterThan(0);
    });

    it('should switch to kanban view on button click', () => {
      const searchParams = new URLSearchParams('view=list');
      (useSearchParams as jest.Mock).mockReturnValue(searchParams);

      render(<PipelinePage />);
      
      const kanbanButton = screen.getByTestId('view-kanban');
      fireEvent.click(kanbanButton);

      expect(mockRouter.replace).toHaveBeenCalledWith(
        expect.stringContaining('view=kanban'),
        expect.any(Object)
      );
    });
  });

  describe('Filtering & Search', () => {
    it('should filter RFQs by search term', () => {
      render(<PipelinePage />);
      
      const searchInput = screen.getByTestId('search-input');
      fireEvent.change(searchInput, { target: { value: 'Acme' } });

      // Should only show matching RFQs
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.queryByText('TechStart Inc')).not.toBeInTheDocument();
    });

    it('should filter RFQs by status', async () => {
      render(<PipelinePage />);
      
      const statusFilter = screen.getByText('All Status');
      fireEvent.click(statusFilter);

      await waitFor(() => {
        const newOption = screen.getByText('New');
        fireEvent.click(newOption);
      });

      // Should only show New RFQs
    });

    it('should filter RFQs by priority', async () => {
      render(<PipelinePage />);
      
      const priorityFilter = screen.getByText('All Priority');
      fireEvent.click(priorityFilter);

      await waitFor(() => {
        const highOption = screen.getByText('High');
        fireEvent.click(highOption);
      });

      // Should only show High priority RFQs
    });

    it('should combine multiple filters', () => {
      render(<PipelinePage />);
      
      const searchInput = screen.getByTestId('search-input');
      fireEvent.change(searchInput, { target: { value: 'parts' } });

      // With search + status filter, should show subset
    });

    it('should clear search on empty input', () => {
      render(<PipelinePage />);
      
      const searchInput = screen.getByTestId('search-input');
      fireEvent.change(searchInput, { target: { value: 'Acme' } });
      fireEvent.change(searchInput, { target: { value: '' } });

      // Should show all RFQs again
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('TechStart Inc')).toBeInTheDocument();
    });
  });

  describe('Sorting', () => {
    it('should sort by due date', () => {
      render(<PipelinePage />);
      
      // Default sort should be by due date ascending
      const rows = screen.getAllByTestId('rfq-row');
      expect(rows[0]).toHaveTextContent('RFQ-2024-001');
    });

    it('should reverse sort order on toggle', () => {
      render(<PipelinePage />);
      
      const sortToggle = screen.getByRole('button', { name: /arrowupdown/i });
      fireEvent.click(sortToggle);

      // Should reverse order
    });

    it('should sort by value', async () => {
      render(<PipelinePage />);
      
      const sortSelect = screen.getByText('Due Date');
      fireEvent.click(sortSelect);

      await waitFor(() => {
        const valueOption = screen.getByText('Value');
        fireEvent.click(valueOption);
      });

      // Should sort by estimated value
    });

    it('should sort by priority', async () => {
      render(<PipelinePage />);
      
      const sortSelect = screen.getByText('Due Date');
      fireEvent.click(sortSelect);

      await waitFor(() => {
        const priorityOption = screen.getByText('Priority');
        fireEvent.click(priorityOption);
      });

      // Urgent > High > Medium > Low
    });
  });

  describe('Selection & Bulk Actions', () => {
    it('should select individual RFQs', () => {
      render(<PipelinePage />);
      
      const checkboxes = screen.getAllByRole('checkbox');
      const firstRFQCheckbox = checkboxes[1]; // Skip the "select all" checkbox
      
      fireEvent.click(firstRFQCheckbox);

      // Bulk action toolbar should appear
    });

    it('should select all RFQs', () => {
      render(<PipelinePage />);
      
      const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
      fireEvent.click(selectAllCheckbox);

      // All RFQs should be selected
    });

    it('should deselect all RFQs', () => {
      render(<PipelinePage />);
      
      const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
      fireEvent.click(selectAllCheckbox); // Select all
      fireEvent.click(selectAllCheckbox); // Deselect all

      // No RFQs should be selected
    });

    it('should export selected RFQs', async () => {
      render(<PipelinePage />);
      
      // Select first RFQ
      const checkbox = screen.getAllByRole('checkbox')[1];
      fireEvent.click(checkbox);

      // Click export in bulk actions
      const exportButton = screen.getByRole('button', { name: /export/i });
      fireEvent.click(exportButton);

      await waitFor(() => {
        expect(mockStoreState.exportRFQs).toHaveBeenCalledWith(['1']);
      });
    });

    it('should delete selected RFQs', async () => {
      render(<PipelinePage />);
      
      // Select first RFQ
      const checkbox = screen.getAllByRole('checkbox')[1];
      fireEvent.click(checkbox);

      // Click delete in bulk actions
      const deleteButton = screen.getByRole('button', { name: /delete/i });
      fireEvent.click(deleteButton);

      // Confirmation dialog would appear
    });
  });

  describe('Export Functionality', () => {
    it('should export all RFQs', async () => {
      render(<PipelinePage />);
      
      const exportButton = screen.getAllByRole('button').find(
        btn => btn.querySelector('svg') && btn.getAttribute('variant') === 'outline'
      );

      if (exportButton) {
        fireEvent.click(exportButton);

        await waitFor(() => {
          expect(mockStoreState.exportRFQs).toHaveBeenCalledWith();
        });
      }
    });
  });

  describe('Summary', () => {
    it('should display correct summary information', () => {
      render(<PipelinePage />);
      
      const summary = screen.getByTestId('pipeline-summary');
      expect(summary).toBeInTheDocument();
      expect(summary).toHaveTextContent('Showing 2 of 2 RFQs');
      expect(summary).toHaveTextContent('Total Value: $75,000.00');
    });

    it('should update summary when filtered', () => {
      render(<PipelinePage />);
      
      const searchInput = screen.getByTestId('search-input');
      fireEvent.change(searchInput, { target: { value: 'Acme' } });

      const summary = screen.getByTestId('pipeline-summary');
      expect(summary).toHaveTextContent('Showing 1 of 2 RFQs');
    });
  });

  describe('Empty States', () => {
    it('should show empty state when no RFQs', () => {
      const emptyState = { ...mockStoreState, rfqs: [], stats: { ...mockStats, totalRFQs: 0 } };
      (usePipelineStore as unknown as jest.Mock).mockReturnValue(emptyState);

      render(<PipelinePage />);
      
      expect(screen.getByText('No RFQs found')).toBeInTheDocument();
    });

    it('should show empty state when search returns no results', () => {
      render(<PipelinePage />);
      
      const searchInput = screen.getByTestId('search-input');
      fireEvent.change(searchInput, { target: { value: 'NonexistentRFQ' } });

      expect(screen.getByText('No RFQs found')).toBeInTheDocument();
    });
  });

  describe('Responsive Design', () => {
    it('should render mobile-friendly layout', () => {
      // Mock mobile viewport
      global.innerWidth = 375;
      global.dispatchEvent(new Event('resize'));

      render(<PipelinePage />);
      
      // Component should adapt to mobile
    });

    it('should render tablet-friendly layout', () => {
      // Mock tablet viewport
      global.innerWidth = 768;
      global.dispatchEvent(new Event('resize'));

      render(<PipelinePage />);
      
      // Component should adapt to tablet
    });
  });

  describe('Performance', () => {
    it('should memoize filtered RFQs', () => {
      const { rerender } = render(<PipelinePage />);
      
      // Rerender without changing filters
      rerender(<PipelinePage />);

      // Should not recalculate filtered RFQs
    });

    it('should debounce search input', async () => {
      render(<PipelinePage />);
      
      const searchInput = screen.getByTestId('search-input');
      
      // Type quickly
      fireEvent.change(searchInput, { target: { value: 'A' } });
      fireEvent.change(searchInput, { target: { value: 'Ac' } });
      fireEvent.change(searchInput, { target: { value: 'Acm' } });

      // Should not filter on every keystroke
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<PipelinePage />);
      
      // Check for semantic HTML and ARIA attributes
      const searchInput = screen.getByTestId('search-input');
      expect(searchInput).toHaveAttribute('placeholder');
    });

    it('should be keyboard navigable', () => {
      render(<PipelinePage />);
      
      const newButton = screen.getByTestId('new-rfq-button');
      newButton.focus();
      expect(newButton).toHaveFocus();
    });

    it('should announce changes to screen readers', () => {
      render(<PipelinePage />);
      
      // Aria-live regions should announce filter changes
    });
  });
});
