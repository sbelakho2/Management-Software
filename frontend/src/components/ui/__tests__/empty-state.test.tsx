import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  EmptyState,
  RFQEmptyState,
  QuoteEmptyState,
  WorkOrderEmptyState,
  AccountEmptyState,
  ProductEmptyState,
  ContactEmptyState,
  AndonEmptyState,
  A3EmptyState,
  TrainingEmptyState,
  WorkCenterEmptyState,
  SearchEmptyState,
  FilterEmptyState,
  ErrorEmptyState,
  NotFoundEmptyState,
} from '../empty-state';

describe('EmptyState', () => {
  describe('base component', () => {
    it('renders with default props', () => {
      render(<EmptyState />);
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText('No items found')).toBeInTheDocument();
    });

    it('renders custom title and description', () => {
      render(
        <EmptyState
          title="Custom Title"
          description="Custom description text"
        />
      );
      expect(screen.getByText('Custom Title')).toBeInTheDocument();
      expect(screen.getByText('Custom description text')).toBeInTheDocument();
    });

    it('renders with custom icon', () => {
      render(
        <EmptyState
          icon={<svg data-testid="custom-icon" />}
          title="Test"
        />
      );
      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });

    it('renders hint text', () => {
      render(<EmptyState hint="This is a helpful hint" />);
      expect(screen.getByText('This is a helpful hint')).toBeInTheDocument();
    });

    it('renders primary action button', () => {
      const onClick = jest.fn();
      render(
        <EmptyState
          primaryAction={{ label: 'Create Item', onClick }}
        />
      );
      const button = screen.getByRole('button', { name: 'Create Item' });
      expect(button).toBeInTheDocument();
      fireEvent.click(button);
      expect(onClick).toHaveBeenCalled();
    });

    it('renders secondary action button', () => {
      const onClick = jest.fn();
      render(
        <EmptyState
          secondaryAction={{ label: 'Go Back', onClick }}
        />
      );
      expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
    });

    it('renders multiple actions', () => {
      render(
        <EmptyState
          primaryAction={{ label: 'Primary' }}
          secondaryAction={{ label: 'Secondary' }}
          actions={[
            { label: 'Action 1' },
            { label: 'Action 2' },
          ]}
        />
      );
      expect(screen.getByRole('button', { name: 'Primary' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Secondary' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Action 1' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Action 2' })).toBeInTheDocument();
    });

    it('renders action as link when href is provided', () => {
      render(
        <EmptyState
          primaryAction={{ label: 'Go Home', href: '/home' }}
        />
      );
      const link = screen.getByRole('link', { name: 'Go Home' });
      expect(link).toHaveAttribute('href', '/home');
    });
  });

  describe('variants', () => {
    it('renders default variant', () => {
      render(<EmptyState variant="default" />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('renders search variant', () => {
      render(<EmptyState variant="search" title="No search results" />);
      expect(screen.getByText('No search results')).toBeInTheDocument();
    });

    it('renders error variant', () => {
      render(<EmptyState variant="error" title="Error occurred" />);
      expect(screen.getByText('Error occurred')).toBeInTheDocument();
    });

    it('renders filtered variant', () => {
      render(<EmptyState variant="filtered" title="No matches" />);
      expect(screen.getByText('No matches')).toBeInTheDocument();
    });

    it('renders success variant', () => {
      render(<EmptyState variant="success" title="All done!" />);
      expect(screen.getByText('All done!')).toBeInTheDocument();
    });

    it('renders pending variant', () => {
      render(<EmptyState variant="pending" title="Waiting..." />);
      expect(screen.getByText('Waiting...')).toBeInTheDocument();
    });
  });

  describe('sizes', () => {
    it('renders small size', () => {
      render(<EmptyState size="sm" title="Small" />);
      expect(screen.getByText('Small')).toBeInTheDocument();
    });

    it('renders medium size (default)', () => {
      render(<EmptyState size="md" title="Medium" />);
      expect(screen.getByText('Medium')).toBeInTheDocument();
    });

    it('renders large size', () => {
      render(<EmptyState size="lg" title="Large" />);
      expect(screen.getByText('Large')).toBeInTheDocument();
    });
  });

  describe('styling options', () => {
    it('renders with border by default', () => {
      const { container } = render(<EmptyState bordered={true} />);
      expect(container.firstChild).toHaveClass('border');
    });

    it('renders without border when disabled', () => {
      const { container } = render(<EmptyState bordered={false} />);
      expect(container.firstChild).not.toHaveClass('border');
    });

    it('renders centered by default', () => {
      const { container } = render(<EmptyState centered={true} />);
      expect(container.firstChild).toHaveClass('text-center');
    });

    it('applies custom className', () => {
      const { container } = render(<EmptyState className="custom-class" />);
      expect(container.firstChild).toHaveClass('custom-class');
    });
  });
});

describe('Entity-specific Empty States', () => {
  describe('RFQEmptyState', () => {
    it('renders with default props', () => {
      render(<RFQEmptyState />);
      expect(screen.getByText('No RFQs found')).toBeInTheDocument();
    });

    it('renders create button when onCreateClick provided', () => {
      const onClick = jest.fn();
      render(<RFQEmptyState onCreateClick={onClick} />);
      expect(screen.getByRole('button', { name: 'Create First RFQ' })).toBeInTheDocument();
    });

    it('renders create link when createHref provided', () => {
      render(<RFQEmptyState createHref="/rfqs/new" />);
      expect(screen.getByRole('link', { name: 'Create First RFQ' })).toHaveAttribute('href', '/rfqs/new');
    });
  });

  describe('QuoteEmptyState', () => {
    it('renders with default props', () => {
      render(<QuoteEmptyState />);
      expect(screen.getByText('No quotes found')).toBeInTheDocument();
    });

    it('renders create button', () => {
      const onClick = jest.fn();
      render(<QuoteEmptyState onCreateClick={onClick} />);
      expect(screen.getByRole('button', { name: 'Create Quote' })).toBeInTheDocument();
    });
  });

  describe('WorkOrderEmptyState', () => {
    it('renders with default props', () => {
      render(<WorkOrderEmptyState />);
      expect(screen.getByText('No work orders found')).toBeInTheDocument();
    });

    it('renders create button', () => {
      render(<WorkOrderEmptyState createHref="/work-orders/new" />);
      expect(screen.getByRole('link', { name: 'Create Work Order' })).toBeInTheDocument();
    });
  });

  describe('AccountEmptyState', () => {
    it('renders with default props', () => {
      render(<AccountEmptyState />);
      expect(screen.getByText('No accounts found')).toBeInTheDocument();
    });

    it('renders add button', () => {
      const onClick = jest.fn();
      render(<AccountEmptyState onCreateClick={onClick} />);
      expect(screen.getByRole('button', { name: 'Add Account' })).toBeInTheDocument();
    });
  });

  describe('ProductEmptyState', () => {
    it('renders with default props', () => {
      render(<ProductEmptyState />);
      expect(screen.getByText('No products found')).toBeInTheDocument();
    });

    it('renders add button', () => {
      const onClick = jest.fn();
      render(<ProductEmptyState onCreateClick={onClick} />);
      expect(screen.getByRole('button', { name: 'Add Product' })).toBeInTheDocument();
    });
  });

  describe('ContactEmptyState', () => {
    it('renders with default props', () => {
      render(<ContactEmptyState />);
      expect(screen.getByText('No contacts found')).toBeInTheDocument();
    });
  });

  describe('AndonEmptyState', () => {
    it('renders with default props', () => {
      render(<AndonEmptyState />);
      expect(screen.getByText('No andon events')).toBeInTheDocument();
    });

    it('uses success variant', () => {
      render(<AndonEmptyState />);
      // Success variant shows positive message
      expect(screen.getByText(/Great job/)).toBeInTheDocument();
    });
  });

  describe('A3EmptyState', () => {
    it('renders with default props', () => {
      render(<A3EmptyState />);
      expect(screen.getByText('No A3 reports found')).toBeInTheDocument();
    });
  });

  describe('TrainingEmptyState', () => {
    it('renders with default props', () => {
      render(<TrainingEmptyState />);
      expect(screen.getByText('No training records found')).toBeInTheDocument();
    });
  });

  describe('WorkCenterEmptyState', () => {
    it('renders with default props', () => {
      render(<WorkCenterEmptyState />);
      expect(screen.getByText('No work centers found')).toBeInTheDocument();
    });
  });
});

describe('Utility Empty States', () => {
  describe('SearchEmptyState', () => {
    it('renders with search query', () => {
      render(<SearchEmptyState searchQuery="test query" />);
      expect(screen.getByText('No results for "test query"')).toBeInTheDocument();
    });

    it('renders with default message when no query', () => {
      render(<SearchEmptyState />);
      expect(screen.getByText('No results for "your search"')).toBeInTheDocument();
    });

    it('shows search tips', () => {
      render(<SearchEmptyState />);
      expect(screen.getByText(/Try adjusting/)).toBeInTheDocument();
    });
  });

  describe('FilterEmptyState', () => {
    it('renders with default props', () => {
      render(<FilterEmptyState />);
      expect(screen.getByText('No matches with current filters')).toBeInTheDocument();
    });

    it('renders clear filters button', () => {
      const onClear = jest.fn();
      render(<FilterEmptyState onClearFilters={onClear} />);
      const button = screen.getByRole('button', { name: 'Clear Filters' });
      fireEvent.click(button);
      expect(onClear).toHaveBeenCalled();
    });
  });

  describe('ErrorEmptyState', () => {
    it('renders with default props', () => {
      render(<ErrorEmptyState />);
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('renders retry button', () => {
      const onRetry = jest.fn();
      render(<ErrorEmptyState onRetry={onRetry} />);
      const button = screen.getByRole('button', { name: 'Retry' });
      fireEvent.click(button);
      expect(onRetry).toHaveBeenCalled();
    });
  });

  describe('NotFoundEmptyState', () => {
    it('renders with default props', () => {
      render(<NotFoundEmptyState />);
      expect(screen.getByText('Page not found')).toBeInTheDocument();
    });

    it('renders go back button', () => {
      const onBack = jest.fn();
      render(<NotFoundEmptyState onBackClick={onBack} />);
      expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
    });

    it('renders go home link', () => {
      render(<NotFoundEmptyState />);
      expect(screen.getByRole('link', { name: 'Go Home' })).toHaveAttribute('href', '/');
    });
  });
});

describe('Accessibility', () => {
  it('has status role', () => {
    render(<EmptyState />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('has aria-label with title', () => {
    render(<EmptyState title="Custom Title" />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Custom Title');
  });

  it('buttons are keyboard accessible', () => {
    const onClick = jest.fn();
    render(<EmptyState primaryAction={{ label: 'Click Me', onClick }} />);
    const button = screen.getByRole('button', { name: 'Click Me' });
    button.focus();
    expect(document.activeElement).toBe(button);
  });
});
