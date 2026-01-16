import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
  TableActions,
  TableEmptyState,
  TableLoadingState,
  TablePagination,
  TableSearch,
} from '../table';

describe('Table', () => {
  describe('Basic Table Structure', () => {
    it('renders table with all parts', () => {
      render(
        <Table>
          <TableCaption>Test Caption</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Header 1</TableHead>
              <TableHead>Header 2</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Cell 1</TableCell>
              <TableCell>Cell 2</TableCell>
            </TableRow>
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell>Footer 1</TableCell>
              <TableCell>Footer 2</TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      );

      expect(screen.getByText('Test Caption')).toBeInTheDocument();
      expect(screen.getByText('Header 1')).toBeInTheDocument();
      expect(screen.getByText('Cell 1')).toBeInTheDocument();
      expect(screen.getByText('Footer 1')).toBeInTheDocument();
    });

    it('applies custom className', () => {
      const { container } = render(
        <Table className="custom-class">
          <TableBody>
            <TableRow>
              <TableCell>Test</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      const table = container.querySelector('table');
      expect(table).toHaveClass('custom-class');
    });

    it('renders with zebra striping', () => {
      const { container } = render(
        <Table zebra>
          <TableBody>
            <TableRow>
              <TableCell>Row 1</TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Row 2</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      const table = container.querySelector('table');
      expect(table?.className).toContain('nth-child(even)');
    });

    it('renders with sticky header', () => {
      render(
        <Table stickyHeader>
          <TableHeader sticky>
            <TableRow>
              <TableHead>Sticky Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      );

      const header = screen.getByText('Sticky Header').closest('thead');
      expect(header).toHaveClass('sticky');
    });
  });

  describe('TableRow', () => {
    it('renders hoverable row by default', () => {
      const { container } = render(
        <TableRow>
          <TableCell>Test</TableCell>
        </TableRow>
      );

      const row = container.querySelector('tr');
      expect(row).toHaveClass('hover:bg-primary/5');
    });

    it('renders non-hoverable row when specified', () => {
      const { container } = render(
        <TableRow hoverable={false}>
          <TableCell>Test</TableCell>
        </TableRow>
      );

      const row = container.querySelector('tr');
      expect(row?.className).not.toContain('hover:bg-primary/5');
    });

    it('applies selected state', () => {
      const { container } = render(
        <TableRow selected>
          <TableCell>Selected</TableCell>
        </TableRow>
      );

      const row = container.querySelector('tr');
      expect(row).toHaveClass('bg-primary/10');
    });
  });

  describe('TableHead - Sorting', () => {
    it('renders sortable column header', () => {
      render(
        <TableHead sortable>Column</TableHead>
      );

      expect(screen.getByText('Column')).toBeInTheDocument();
      expect(screen.getByText('⇅')).toBeInTheDocument(); // Sort indicator
    });

    it('shows ascending sort indicator', () => {
      render(
        <TableHead sortable sortDirection="asc">
          Column
        </TableHead>
      );

      expect(screen.getByText('↑')).toBeInTheDocument();
    });

    it('shows descending sort indicator', () => {
      render(
        <TableHead sortable sortDirection="desc">
          Column
        </TableHead>
      );

      expect(screen.getByText('↓')).toBeInTheDocument();
    });

    it('calls onSort when clicked', () => {
      const handleSort = jest.fn();
      render(
        <TableHead sortable onSort={handleSort}>
          Column
        </TableHead>
      );

      fireEvent.click(screen.getByText('Column'));
      expect(handleSort).toHaveBeenCalledTimes(1);
    });

    it('does not call onSort for non-sortable columns', () => {
      const handleSort = jest.fn();
      render(
        <TableHead onSort={handleSort}>Column</TableHead>
      );

      fireEvent.click(screen.getByText('Column'));
      expect(handleSort).not.toHaveBeenCalled();
    });
  });

  describe('TableActions', () => {
    it('renders action buttons', () => {
      render(
        <TableRow className="group">
          <TableCell>Data</TableCell>
          <TableCell>
            <TableActions>
              <button>Edit</button>
              <button>Delete</button>
            </TableActions>
          </TableCell>
        </TableRow>
      );

      expect(screen.getByText('Edit')).toBeInTheDocument();
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    it('has opacity transition class', () => {
      const { container } = render(
        <TableActions>
          <button>Action</button>
        </TableActions>
      );

      const actions = container.firstChild;
      expect(actions).toHaveClass('opacity-0', 'group-hover:opacity-100');
    });
  });

  describe('TableEmptyState', () => {
    it('renders default empty state', () => {
      render(<TableEmptyState />);

      expect(screen.getByText('No data')).toBeInTheDocument();
    });

    it('renders custom title and description', () => {
      render(
        <TableEmptyState
          title="No results found"
          description="Try adjusting your filters"
        />
      );

      expect(screen.getByText('No results found')).toBeInTheDocument();
      expect(screen.getByText('Try adjusting your filters')).toBeInTheDocument();
    });

    it('renders custom icon', () => {
      render(
        <TableEmptyState
          icon={<span data-testid="custom-icon">📊</span>}
        />
      );

      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });

    it('renders action button', () => {
      render(
        <TableEmptyState
          action={<button>Create New</button>}
        />
      );

      expect(screen.getByText('Create New')).toBeInTheDocument();
    });
  });

  describe('TableLoadingState', () => {
    it('renders default loading skeleton', () => {
      const { container } = render(<TableLoadingState />);

      const skeletons = container.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('renders custom number of rows', () => {
      const { container } = render(<TableLoadingState rows={3} />);

      const rows = container.querySelectorAll('.flex.gap-4');
      expect(rows).toHaveLength(3);
    });

    it('renders custom number of columns', () => {
      const { container } = render(<TableLoadingState rows={1} columns={5} />);

      const columns = container.querySelectorAll('.h-8.flex-1');
      expect(columns).toHaveLength(5);
    });
  });

  describe('TablePagination', () => {
    const defaultProps = {
      currentPage: 1,
      totalPages: 5,
      pageSize: 10,
      totalItems: 50,
      onPageChange: jest.fn(),
    };

    it('renders pagination controls', () => {
      render(<TablePagination {...defaultProps} />);

      expect(screen.getByText('Showing 1 to 10 of 50 results')).toBeInTheDocument();
      expect(screen.getByText('Page 1 of 5')).toBeInTheDocument();
      expect(screen.getByText('Previous')).toBeInTheDocument();
      expect(screen.getByText('Next')).toBeInTheDocument();
    });

    it('disables Previous on first page', () => {
      render(<TablePagination {...defaultProps} currentPage={1} />);

      const previousButton = screen.getByText('Previous');
      expect(previousButton).toBeDisabled();
    });

    it('disables Next on last page', () => {
      render(<TablePagination {...defaultProps} currentPage={5} />);

      const nextButton = screen.getByText('Next');
      expect(nextButton).toBeDisabled();
    });

    it('calls onPageChange with next page', () => {
      const handlePageChange = jest.fn();
      render(
        <TablePagination {...defaultProps} onPageChange={handlePageChange} />
      );

      fireEvent.click(screen.getByText('Next'));
      expect(handlePageChange).toHaveBeenCalledWith(2);
    });

    it('calls onPageChange with previous page', () => {
      const handlePageChange = jest.fn();
      render(
        <TablePagination
          {...defaultProps}
          currentPage={3}
          onPageChange={handlePageChange}
        />
      );

      fireEvent.click(screen.getByText('Previous'));
      expect(handlePageChange).toHaveBeenCalledWith(2);
    });

    it('renders page size selector', () => {
      const handlePageSizeChange = jest.fn();
      render(
        <TablePagination
          {...defaultProps}
          onPageSizeChange={handlePageSizeChange}
        />
      );

      expect(screen.getByText('Rows per page:')).toBeInTheDocument();
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
    });

    it('calls onPageSizeChange when page size changes', () => {
      const handlePageSizeChange = jest.fn();
      render(
        <TablePagination
          {...defaultProps}
          onPageSizeChange={handlePageSizeChange}
        />
      );

      const select = screen.getByRole('combobox');
      fireEvent.change(select, { target: { value: '20' } });
      expect(handlePageSizeChange).toHaveBeenCalledWith(20);
    });

    it('displays correct item range for middle page', () => {
      render(
        <TablePagination
          {...defaultProps}
          currentPage={3}
          pageSize={10}
          totalItems={50}
        />
      );

      expect(screen.getByText('Showing 21 to 30 of 50 results')).toBeInTheDocument();
    });

    it('displays correct item range for last page', () => {
      render(
        <TablePagination
          {...defaultProps}
          currentPage={5}
          pageSize={10}
          totalItems={47}
        />
      );

      expect(screen.getByText('Showing 41 to 47 of 47 results')).toBeInTheDocument();
    });
  });

  describe('TableSearch', () => {
    it('renders search input', () => {
      const handleChange = jest.fn();
      render(<TableSearch value="" onChange={handleChange} />);

      const input = screen.getByPlaceholderText('Search...');
      expect(input).toBeInTheDocument();
    });

    it('renders with custom placeholder', () => {
      const handleChange = jest.fn();
      render(
        <TableSearch
          value=""
          onChange={handleChange}
          placeholder="Search users..."
        />
      );

      expect(screen.getByPlaceholderText('Search users...')).toBeInTheDocument();
    });

    it('calls onChange when value changes', () => {
      const handleChange = jest.fn();
      render(<TableSearch value="" onChange={handleChange} />);

      const input = screen.getByPlaceholderText('Search...');
      fireEvent.change(input, { target: { value: 'test query' } });
      expect(handleChange).toHaveBeenCalledWith('test query');
    });

    it('displays current value', () => {
      const handleChange = jest.fn();
      render(<TableSearch value="current search" onChange={handleChange} />);

      const input = screen.getByDisplayValue('current search');
      expect(input).toBeInTheDocument();
    });

    it('renders search icon', () => {
      const { container } = render(
        <TableSearch value="" onChange={jest.fn()} />
      );

      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper table semantics', () => {
      const { container } = render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Header</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Data</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      expect(container.querySelector('table')).toBeInTheDocument();
      expect(container.querySelector('thead')).toBeInTheDocument();
      expect(container.querySelector('tbody')).toBeInTheDocument();
      expect(container.querySelector('th')).toBeInTheDocument();
      expect(container.querySelector('td')).toBeInTheDocument();
    });

    it('sortable headers have cursor-pointer', () => {
      const { container } = render(
        <TableHead sortable>Column</TableHead>
      );

      const th = container.querySelector('th');
      expect(th).toHaveClass('cursor-pointer');
    });
  });

  describe('Integration Example', () => {
    it('renders complete table with all features', () => {
      const handleSort = jest.fn();
      const handlePageChange = jest.fn();

      render(
        <div>
          <TableSearch value="" onChange={jest.fn()} />
          <Table stickyHeader zebra>
            <TableHeader sticky>
              <TableRow>
                <TableHead sortable onSort={handleSort}>
                  Name
                </TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow className="group">
                <TableCell>John Doe</TableCell>
                <TableCell>john@example.com</TableCell>
                <TableCell>
                  <TableActions>
                    <button>Edit</button>
                  </TableActions>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <TablePagination
            currentPage={1}
            totalPages={10}
            pageSize={10}
            totalItems={100}
            onPageChange={handlePageChange}
          />
        </div>
      );

      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Edit')).toBeInTheDocument();
      expect(screen.getByText('Showing 1 to 10 of 100 results')).toBeInTheDocument();
    });
  });
});
