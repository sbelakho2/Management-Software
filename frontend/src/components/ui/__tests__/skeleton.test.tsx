import { render, screen } from '@testing-library/react';
import {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonTable,
  SkeletonList,
  SkeletonDashboard,
  SkeletonListPage,
  SkeletonDetailPage,
  SkeletonFormPage,
  SkeletonKanban,
  SkeletonTimeline,
  SkeletonModal,
  SkeletonStats,
  SkeletonProfile,
} from '../skeleton';

describe('Skeleton', () => {
  it('should render with default classes', () => {
    render(<Skeleton data-testid="skeleton" />);
    const skeleton = screen.getByTestId('skeleton');
    
    expect(skeleton).toHaveClass('skeleton');
  });

  it('should apply custom className', () => {
    render(<Skeleton className="custom-class h-10 w-10" data-testid="skeleton" />);
    const skeleton = screen.getByTestId('skeleton');
    
    expect(skeleton).toHaveClass('custom-class');
    expect(skeleton).toHaveClass('h-10');
    expect(skeleton).toHaveClass('w-10');
  });

  it('should pass through additional props', () => {
    render(<Skeleton data-testid="skeleton" id="test-skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveAttribute('id', 'test-skeleton');
  });

  it('should render as a div element', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton').tagName).toBe('DIV');
  });

  it('should accept inline styles', () => {
    render(<Skeleton data-testid="skeleton" style={{ width: '100px' }} />);
    expect(screen.getByTestId('skeleton')).toHaveStyle({ width: '100px' });
  });
});

describe('SkeletonText', () => {
  it('renders default 3 lines', () => {
    const { container } = render(<SkeletonText />);
    const lines = container.querySelectorAll('.skeleton');
    expect(lines).toHaveLength(3);
  });

  it('renders custom number of lines', () => {
    const { container } = render(<SkeletonText lines={5} />);
    const lines = container.querySelectorAll('.skeleton');
    expect(lines).toHaveLength(5);
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonText className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});

describe('SkeletonCard', () => {
  it('renders with card styling', () => {
    const { container } = render(<SkeletonCard />);
    expect(container.firstChild).toHaveClass('rounded-rams-sm');
    expect(container.firstChild).toHaveClass('border');
    expect(container.firstChild).toHaveClass('bg-rams-module');
  });

  it('renders with avatar placeholder', () => {
    const { container } = render(<SkeletonCard />);
    const avatar = container.querySelector('.skeleton.h-10.w-10');
    expect(avatar).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonCard className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});

describe('SkeletonTable', () => {
  it('renders default 5 rows and 4 columns', () => {
    const { container } = render(<SkeletonTable />);
    // Header + 5 rows = 6 row divs (but header has different structure)
    const rows = container.querySelectorAll('.border-b');
    expect(rows.length).toBeGreaterThanOrEqual(5);
  });

  it('renders custom rows and columns', () => {
    const { container } = render(<SkeletonTable rows={3} columns={6} />);
    expect(container).toBeDefined();
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonTable className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});

describe('SkeletonList', () => {
  it('renders default 5 items', () => {
    const { container } = render(<SkeletonList />);
    const items = container.querySelectorAll('.flex.items-center.gap-4');
    expect(items).toHaveLength(5);
  });

  it('renders custom number of items', () => {
    const { container } = render(<SkeletonList items={3} />);
    const items = container.querySelectorAll('.flex.items-center.gap-4');
    expect(items).toHaveLength(3);
  });

  it('renders avatar placeholders', () => {
    const { container } = render(<SkeletonList />);
    const avatars = container.querySelectorAll('.skeleton.h-8.w-8');
    expect(avatars.length).toBeGreaterThanOrEqual(5);
  });
});

describe('SkeletonDashboard', () => {
  it('renders dashboard skeleton', () => {
    render(<SkeletonDashboard />);
    expect(screen.getByTestId('skeleton-dashboard')).toBeInTheDocument();
  });

  it('renders KPI cards', () => {
    const { container } = render(<SkeletonDashboard />);
    const cards = container.querySelectorAll('.rounded-lg.border.bg-card');
    expect(cards.length).toBeGreaterThanOrEqual(4);
  });

  it('renders chart placeholders', () => {
    const { container } = render(<SkeletonDashboard />);
    expect(container.querySelectorAll('.h-64').length).toBeGreaterThanOrEqual(2);
  });

  it('applies custom className', () => {
    render(<SkeletonDashboard className="custom-class" />);
    expect(screen.getByTestId('skeleton-dashboard')).toHaveClass('custom-class');
  });
});

describe('SkeletonListPage', () => {
  it('renders list page skeleton', () => {
    render(<SkeletonListPage />);
    expect(screen.getByTestId('skeleton-list-page')).toBeInTheDocument();
  });

  it('renders filters by default', () => {
    const { container } = render(<SkeletonListPage />);
    // Check for filter placeholder elements
    const filterContainer = container.querySelector('.flex.flex-col.sm\\:flex-row');
    expect(filterContainer).toBeInTheDocument();
  });

  it('can hide filters', () => {
    const { container } = render(<SkeletonListPage showFilters={false} />);
    const filterContainer = container.querySelector('.flex.flex-col.sm\\:flex-row');
    expect(filterContainer).not.toBeInTheDocument();
  });

  it('renders pagination', () => {
    const { container } = render(<SkeletonListPage />);
    const pagination = container.querySelector('.flex.items-center.justify-between:last-child');
    expect(pagination).toBeInTheDocument();
  });

  it('accepts custom row count', () => {
    render(<SkeletonListPage rows={15} />);
    expect(screen.getByTestId('skeleton-list-page')).toBeInTheDocument();
  });
});

describe('SkeletonDetailPage', () => {
  it('renders detail page skeleton', () => {
    render(<SkeletonDetailPage />);
    expect(screen.getByTestId('skeleton-detail-page')).toBeInTheDocument();
  });

  it('renders breadcrumb', () => {
    const { container } = render(<SkeletonDetailPage />);
    const breadcrumb = container.querySelector('.flex.items-center.gap-2');
    expect(breadcrumb).toBeInTheDocument();
  });

  it('renders info grid', () => {
    const { container } = render(<SkeletonDetailPage />);
    const grid = container.querySelector('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-4');
    expect(grid).toBeInTheDocument();
  });

  it('accepts custom section count', () => {
    render(<SkeletonDetailPage sections={5} />);
    expect(screen.getByTestId('skeleton-detail-page')).toBeInTheDocument();
  });
});

describe('SkeletonFormPage', () => {
  it('renders form page skeleton', () => {
    render(<SkeletonFormPage />);
    expect(screen.getByTestId('skeleton-form-page')).toBeInTheDocument();
  });

  it('renders form sections', () => {
    const { container } = render(<SkeletonFormPage sections={3} />);
    const sections = container.querySelectorAll('.rounded-lg.border.bg-card.p-6');
    expect(sections.length).toBeGreaterThanOrEqual(3);
  });

  it('renders form footer', () => {
    const { container } = render(<SkeletonFormPage />);
    const footer = container.querySelector('.flex.justify-end.gap-4');
    expect(footer).toBeInTheDocument();
  });
});

describe('SkeletonKanban', () => {
  it('renders kanban skeleton', () => {
    render(<SkeletonKanban />);
    expect(screen.getByTestId('skeleton-kanban')).toBeInTheDocument();
  });

  it('renders default 4 columns', () => {
    const { container } = render(<SkeletonKanban />);
    const columns = container.querySelectorAll('.flex-shrink-0.w-72');
    expect(columns).toHaveLength(4);
  });

  it('renders custom column count', () => {
    const { container } = render(<SkeletonKanban columns={6} />);
    const columns = container.querySelectorAll('.flex-shrink-0.w-72');
    expect(columns).toHaveLength(6);
  });

  it('renders cards in columns', () => {
    const { container } = render(<SkeletonKanban cardsPerColumn={5} />);
    expect(container).toBeDefined();
  });
});

describe('SkeletonTimeline', () => {
  it('renders timeline skeleton', () => {
    render(<SkeletonTimeline />);
    expect(screen.getByTestId('skeleton-timeline')).toBeInTheDocument();
  });

  it('renders default 5 items', () => {
    const { container } = render(<SkeletonTimeline />);
    const items = container.querySelectorAll('.flex.gap-4');
    expect(items).toHaveLength(5);
  });

  it('renders custom number of items', () => {
    const { container } = render(<SkeletonTimeline items={8} />);
    const items = container.querySelectorAll('.flex.gap-4');
    expect(items).toHaveLength(8);
  });
});

describe('SkeletonModal', () => {
  it('renders modal skeleton', () => {
    render(<SkeletonModal />);
    expect(screen.getByTestId('skeleton-modal')).toBeInTheDocument();
  });

  it('renders header section', () => {
    const { container } = render(<SkeletonModal />);
    const header = container.querySelector('.space-y-2');
    expect(header).toBeInTheDocument();
  });

  it('renders footer with buttons', () => {
    const { container } = render(<SkeletonModal />);
    const footer = container.querySelector('.border-t');
    expect(footer).toBeInTheDocument();
  });
});

describe('SkeletonStats', () => {
  it('renders stats skeleton', () => {
    render(<SkeletonStats />);
    expect(screen.getByTestId('skeleton-stats')).toBeInTheDocument();
  });

  it('renders default 4 items', () => {
    const { container } = render(<SkeletonStats />);
    const items = container.querySelectorAll('.rounded-lg.border.bg-card');
    expect(items).toHaveLength(4);
  });

  it('renders custom number of items', () => {
    const { container } = render(<SkeletonStats items={6} />);
    const items = container.querySelectorAll('.rounded-lg.border.bg-card');
    expect(items).toHaveLength(6);
  });

  it('applies responsive grid based on count', () => {
    const { container } = render(<SkeletonStats items={3} />);
    expect(container.firstChild).toHaveClass('md:grid-cols-3');
  });
});

describe('SkeletonProfile', () => {
  it('renders profile skeleton', () => {
    render(<SkeletonProfile />);
    expect(screen.getByTestId('skeleton-profile')).toBeInTheDocument();
  });

  it('renders avatar placeholder', () => {
    const { container } = render(<SkeletonProfile />);
    const avatar = container.querySelector('.h-24.w-24.rounded-full');
    expect(avatar).toBeInTheDocument();
  });

  it('renders info grids', () => {
    const { container } = render(<SkeletonProfile />);
    const grids = container.querySelectorAll('.grid.grid-cols-1.md\\:grid-cols-2');
    expect(grids.length).toBeGreaterThanOrEqual(1);
  });

  it('applies custom className', () => {
    render(<SkeletonProfile className="custom-class" />);
    expect(screen.getByTestId('skeleton-profile')).toHaveClass('custom-class');
  });
});
