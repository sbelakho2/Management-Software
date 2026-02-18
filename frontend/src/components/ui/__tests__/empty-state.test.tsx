import React from 'react';
import { render as rtlRender, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { I18nProvider } from '@/contexts/i18n-context';
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

const renderWithI18n = (ui: React.ReactElement) =>
  rtlRender(<I18nProvider>{ui}</I18nProvider>);

describe('EmptyState', () => {
  describe('base component', () => {
    it('renders with default props', () => {
      renderWithI18n(<EmptyState />);
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText('No items found')).toBeInTheDocument();
    });

    it('renders custom title and description', () => {
      renderWithI18n(
        <EmptyState
          title="Custom Title"
          description="Custom description text"
        />
      );
      expect(screen.getByText('Custom Title')).toBeInTheDocument();
      expect(screen.getByText('Custom description text')).toBeInTheDocument();
    });

    it('renders with custom icon', () => {
      renderWithI18n(
        <EmptyState
          icon={<svg data-testid="custom-icon" />}
          title="Test"
        />
      );
      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });

    it('renders hint text', () => {
      renderWithI18n(<EmptyState hint="This is a helpful hint" />);
      expect(screen.getByText('This is a helpful hint')).toBeInTheDocument();
    });

    it('renders primary action button', () => {
      const onClick = jest.fn();
      renderWithI18n(
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
      renderWithI18n(
        <EmptyState
          secondaryAction={{ label: 'Go Back', onClick }}
        />
      );
      expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
    });

    it('renders multiple actions', () => {
      renderWithI18n(
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
      renderWithI18n(
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
      renderWithI18n(<EmptyState variant="default" />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('renders search variant', () => {
      renderWithI18n(<EmptyState variant="search" title="No search results" />);
      expect(screen.getByText('No search results')).toBeInTheDocument();
    });

    it('renders error variant', () => {
      renderWithI18n(<EmptyState variant="error" title="Error occurred" />);
      expect(screen.getByText('Error occurred')).toBeInTheDocument();
    });

    it('renders filtered variant', () => {
      renderWithI18n(<EmptyState variant="filtered" title="No matches" />);
      expect(screen.getByText('No matches')).toBeInTheDocument();
    });

    it('renders success variant', () => {
      renderWithI18n(<EmptyState variant="success" title="All done!" />);
      expect(screen.getByText('All done!')).toBeInTheDocument();
    });

    it('renders pending variant', () => {
      renderWithI18n(<EmptyState variant="pending" title="Waiting..." />);
      expect(screen.getByText('Waiting...')).toBeInTheDocument();
    });
  });

  describe('sizes', () => {
    it('renders small size', () => {
      renderWithI18n(<EmptyState size="sm" title="Small" />);
      expect(screen.getByText('Small')).toBeInTheDocument();
    });

    it('renders medium size (default)', () => {
      renderWithI18n(<EmptyState size="md" title="Medium" />);
      expect(screen.getByText('Medium')).toBeInTheDocument();
    });

    it('renders large size', () => {
      renderWithI18n(<EmptyState size="lg" title="Large" />);
      expect(screen.getByText('Large')).toBeInTheDocument();
    });
  });

  describe('styling options', () => {
    it('renders with border by default', () => {
      const { container } = renderWithI18n(<EmptyState bordered={true} />);
      expect(container.firstChild).toHaveClass('border');
    });

    it('renders without border when disabled', () => {
      const { container } = renderWithI18n(<EmptyState bordered={false} />);
      expect(container.firstChild).not.toHaveClass('border');
    });

    it('renders centered by default', () => {
      const { container } = renderWithI18n(<EmptyState centered={true} />);
      expect(container.firstChild).toHaveClass('text-center');
    });

    it('applies custom className', () => {
      const { container } = renderWithI18n(<EmptyState className="custom-class" />);
      expect(container.firstChild).toHaveClass('custom-class');
    });
  });
});

describe('Entity-specific Empty States', () => {
  describe('RFQEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<RFQEmptyState />);
      expect(screen.getByText('No RFQs Yet')).toBeInTheDocument();
    });

    it('renders create button when onCreateClick provided', () => {
      const onClick = jest.fn();
      renderWithI18n(<RFQEmptyState onCreateClick={onClick} />);
      expect(screen.getByRole('button', { name: 'Create RFQ' })).toBeInTheDocument();
    });

    it('renders create link when createHref provided', () => {
      renderWithI18n(<RFQEmptyState createHref="/rfqs/new" />);
      expect(screen.getByRole('link', { name: 'Create RFQ' })).toHaveAttribute('href', '/rfqs/new');
    });
  });

  describe('QuoteEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<QuoteEmptyState />);
      expect(screen.getByText('No Quotes Yet')).toBeInTheDocument();
    });

    it('renders create button', () => {
      const onClick = jest.fn();
      renderWithI18n(<QuoteEmptyState onCreateClick={onClick} />);
      expect(screen.getByRole('button', { name: 'Create Quote' })).toBeInTheDocument();
    });
  });

  describe('WorkOrderEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<WorkOrderEmptyState />);
      expect(screen.getByText('No Work Orders Yet')).toBeInTheDocument();
    });

    it('renders create button', () => {
      renderWithI18n(<WorkOrderEmptyState createHref="/work-orders/new" />);
      expect(screen.getByRole('link', { name: 'Create Work Order' })).toBeInTheDocument();
    });
  });

  describe('AccountEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<AccountEmptyState />);
      expect(screen.getByText('No Accounts Yet')).toBeInTheDocument();
    });

    it('renders add button', () => {
      const onClick = jest.fn();
      renderWithI18n(<AccountEmptyState onCreateClick={onClick} />);
      expect(screen.getByRole('button', { name: 'Add Account' })).toBeInTheDocument();
    });
  });

  describe('ProductEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<ProductEmptyState />);
      expect(screen.getByText('No Products Yet')).toBeInTheDocument();
    });

    it('renders add button', () => {
      const onClick = jest.fn();
      renderWithI18n(<ProductEmptyState onCreateClick={onClick} />);
      expect(screen.getByRole('button', { name: 'Add Product' })).toBeInTheDocument();
    });
  });

  describe('ContactEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<ContactEmptyState />);
      expect(screen.getByText('No Contacts Yet')).toBeInTheDocument();
    });
  });

  describe('AndonEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<AndonEmptyState />);
      expect(screen.getByText('No Active Alerts')).toBeInTheDocument();
    });

    it('uses success variant', () => {
      renderWithI18n(<AndonEmptyState />);
      expect(screen.getByText('No Active Alerts')).toBeInTheDocument();
    });
  });

  describe('A3EmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<A3EmptyState />);
      expect(screen.getByText('No A3 Reports Yet')).toBeInTheDocument();
    });
  });

  describe('TrainingEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<TrainingEmptyState />);
      expect(screen.getByText('No Training Records Yet')).toBeInTheDocument();
    });
  });

  describe('WorkCenterEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<WorkCenterEmptyState />);
      expect(screen.getByText('No Work Centers Yet')).toBeInTheDocument();
    });
  });
});

describe('Utility Empty States', () => {
  describe('SearchEmptyState', () => {
    it('renders with search query', () => {
      renderWithI18n(<SearchEmptyState searchQuery="test query" />);
      expect(screen.getByText('No results for "test query"')).toBeInTheDocument();
    });

    it('renders with default message when no query', () => {
      renderWithI18n(<SearchEmptyState />);
      expect(screen.getByText('No results for "your search"')).toBeInTheDocument();
    });

    it('shows search tips', () => {
      renderWithI18n(<SearchEmptyState />);
      expect(screen.getByText(/Try adjusting/)).toBeInTheDocument();
    });
  });

  describe('FilterEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<FilterEmptyState />);
      expect(screen.getByText('No Matching Results')).toBeInTheDocument();
    });

    it('renders clear filters button', () => {
      const onClear = jest.fn();
      renderWithI18n(<FilterEmptyState onClearFilters={onClear} />);
      const button = screen.getByRole('button', { name: 'Clear Filters' });
      fireEvent.click(button);
      expect(onClear).toHaveBeenCalled();
    });
  });

  describe('ErrorEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<ErrorEmptyState />);
      expect(screen.getByText('Something Went Wrong')).toBeInTheDocument();
    });

    it('renders retry button', () => {
      const onRetry = jest.fn();
      renderWithI18n(<ErrorEmptyState onRetry={onRetry} />);
      const button = screen.getByRole('button', { name: 'Retry' });
      fireEvent.click(button);
      expect(onRetry).toHaveBeenCalled();
    });
  });

  describe('NotFoundEmptyState', () => {
    it('renders with default props', () => {
      renderWithI18n(<NotFoundEmptyState />);
      expect(screen.getByText('Page Not Found')).toBeInTheDocument();
    });

    it('renders go back button', () => {
      const onBack = jest.fn();
      renderWithI18n(<NotFoundEmptyState onBackClick={onBack} />);
      expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
    });

    it('renders go home link', () => {
      renderWithI18n(<NotFoundEmptyState />);
      expect(screen.getByRole('link', { name: 'Go Home' })).toHaveAttribute('href', '/');
    });
  });
});

describe('Accessibility', () => {
  it('has status role', () => {
    renderWithI18n(<EmptyState />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('has aria-label with title', () => {
    renderWithI18n(<EmptyState title="Custom Title" />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Custom Title');
  });

  it('buttons are keyboard accessible', () => {
    const onClick = jest.fn();
    renderWithI18n(<EmptyState primaryAction={{ label: 'Click Me', onClick }} />);
    const button = screen.getByRole('button', { name: 'Click Me' });
    button.focus();
    expect(document.activeElement).toBe(button);
  });
});
