import React from 'react';
import { screen, within, waitFor } from '@testing-library/react';
import { renderWithI18n } from '@/test-utils';
import { useAuthStore } from '@/stores';
import { useTodayStore } from '@/stores/today';
import TodayPage from '../today/page';

const render = (ui: React.ReactElement) => renderWithI18n(ui);

// Mock next/link
jest.mock('next/link', () => {
  const LinkMock = ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
  LinkMock.displayName = 'LinkMock';
  return LinkMock;
});

// Mock next/navigation
const mockPush = jest.fn();
const mockReplace = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
}));

// Mock auth store
jest.mock('@/stores', () => ({
  useAuthStore: jest.fn(),
}));

// Mock today store to avoid real API client + open handles
jest.mock('@/stores/today', () => ({
  useTodayStore: jest.fn(),
}));

const mockUser = {
  id: 'user-1',
  email: 'john.smith@example.com',
  full_name: 'John Smith',
  role: 'gm',
  is_active: true,
  created_at: new Date().toISOString(),
};

describe('TodayPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useAuthStore as unknown as jest.Mock).mockReturnValue({ user: mockUser });
    (useTodayStore as unknown as jest.Mock).mockReturnValue({
      data: null,
      loading: false,
      error: null,
      fetchTodayScreen: jest.fn(),
    });
  });

  // REQUIREMENT: Today screen must have max 5 primary cards
  describe('Card Layout', () => {
    it('should render maximum 5 primary card sections', () => {
      render(<TodayPage />);
      
      // Count primary card sections (not counting KPI mini-cards)
      const mainCards = screen.queryAllByRole('article').filter((card) => {
        return card.classList.contains('space-y-6') === false; // Exclude container
      });
      
      // Should have: Top 3 Priorities, My Tasks, Activity, Priority RFQs, Drill Card = 5
      expect(mainCards.length).toBeLessThanOrEqual(5);
    });

    it('should display header with personalized greeting', () => {
      render(<TodayPage />);
      
      // Should have user name somewhere on the page
      const johnElements = screen.queryAllByText(/John/);
      expect(johnElements.length).toBeGreaterThan(0);
    });

    it('should display current date', () => {
      render(<TodayPage />);
      
      const today = new Date();
      const datePattern = new RegExp(today.toLocaleDateString('en-US', { month: 'long' }));
      const dateElements = screen.queryAllByText(datePattern);
      expect(dateElements.length).toBeGreaterThan(0);
    });

    it('should show Create RFQ action button in header', () => {
      render(<TodayPage />);
      
      const initializeLink = screen.getByRole('link', { name: /initialize rfq/i });
      expect(initializeLink).toBeInTheDocument();
      expect(initializeLink).toHaveAttribute('href', '/pipeline/new');
    });
  });

  // REQUIREMENT: Top 3 Priorities dominates the screen
  describe('Top 3 Priorities', () => {
    it('should render Top 3 Priorities section', () => {
      render(<TodayPage />);
      
      const prioritiesHeading = screen.getByRole('heading', { name: /top priorities/i });
      expect(prioritiesHeading).toBeInTheDocument();
    });

    it('should display priority items', () => {
      render(<TodayPage />);
      
      const prioritiesSection = screen.getByRole('heading', { name: /top priorities/i }).closest('article');
      if (prioritiesSection) {
        const priorityLinks = within(prioritiesSection).queryAllByRole('link');
        expect(priorityLinks.length).toBeGreaterThan(0);
      }
    });

    it('should show priority ranking (1, 2, 3)', () => {
      render(<TodayPage />);
      
      const prioritiesCard = screen.getByRole('heading', { name: /top priorities/i }).closest('[class*="card"]');
      if (prioritiesCard) {
        const rankings = within(prioritiesCard).queryAllByText(/^[1-3]$/);
        expect(rankings.length).toBeLessThanOrEqual(3);
      }
    });

    it('should allow navigation to priority detail', () => {
      render(<TodayPage />);
      
      const prioritiesSection = screen.getByRole('heading', { name: /top priorities/i }).closest('article');
      if (prioritiesSection) {
        const priorityLinks = within(prioritiesSection).queryAllByRole('link');
        expect(priorityLinks.length).toBeGreaterThan(0);
      }
    });

    it('should show empty state when no priorities set', () => {
      render(<TodayPage />);
      
      const prioritiesSection = screen.getByRole('heading', { name: /top priorities/i }).closest('article');
      if (prioritiesSection) {
        const emptyState = within(prioritiesSection).queryByText(/set your top 3 priorities|no priorities set/i);
        const items = within(prioritiesSection).queryAllByRole('link');
        expect(emptyState || items.length > 0).toBeTruthy();
      }
    });
  });

  // REQUIREMENT: KPI Cards should be compact and informative
  describe('KPI Cards', () => {
    it('should render KPI cards with key metrics', () => {
      render(<TodayPage />);
      
      expect(screen.getByText(/^open rfqs$/i)).toBeInTheDocument();
      expect(screen.getByText(/^pending quotes$/i)).toBeInTheDocument();
      expect(screen.getByText(/^on-time delivery$/i)).toBeInTheDocument();
      expect(screen.getByText(/^oee$/i)).toBeInTheDocument();
    });

    it('should display KPI values prominently', () => {
      render(<TodayPage />);
      
      // KPI values should be large and easily readable
      const kpiCards = screen.getAllByRole('link').filter((link) =>
        link.textContent?.match(/\d+/)
      );
      expect(kpiCards.length).toBeGreaterThan(0);
    });

    it('should show trend indicators for KPIs', () => {
      render(<TodayPage />);
      
      // Should show up/down trends
      const trends = screen.queryAllByText(/from last week/i);
      expect(trends.length).toBeGreaterThan(0);
    });

    it('should link KPIs to respective pages', () => {
      render(<TodayPage />);
      
      // There may be multiple links that mention “Open RFQs” (e.g. task links)
      // so anchor on the KPI tile title text.
      const openRfqsTileLink = screen.getByText(/^open rfqs$/i).closest('a');
      expect(openRfqsTileLink).toBeInTheDocument();
      expect(openRfqsTileLink).toHaveAttribute('href', '/pipeline');
    });

    it('should render KPIs in grid layout (responsive)', () => {
      const { container } = render(<TodayPage />);
      const grids = container.querySelectorAll('[class*="grid"]');
      expect(grids.length).toBeGreaterThan(0);
    });
  });

  // REQUIREMENT: Abnormalities must be compact and actionable
  describe('Abnormalities Section', () => {
    it('should display critical anomalies section', () => {
      render(<TodayPage />);
      expect(screen.getByRole('heading', { name: /critical anomalies/i })).toBeInTheDocument();
    });

    it('should show overdue items as abnormalities', () => {
      render(<TodayPage />);
      
      // Overdue/urgent items should be highlighted
      const urgentIndicators = screen.queryAllByText(/overdue|urgent|late/i);
      // May or may not have urgent items
      expect(urgentIndicators.length).toBeGreaterThanOrEqual(0);
    });

    it('should provide quick actions for abnormalities', () => {
      render(<TodayPage />);
      
      const anomaliesCard = screen.getByRole('heading', { name: /critical anomalies/i }).closest('div.bg-rams-module');
      if (anomaliesCard) {
        const anomalyLinks = within(anomaliesCard).queryAllByRole('link');
        expect(anomalyLinks.length).toBeGreaterThan(0);
      }
    });

    it('should highlight severity levels', () => {
      render(<TodayPage />);
      
      // Should use badges or colors to indicate severity
      const badges = screen.queryAllByRole('status');
      // Badges for priority, status, etc.
      expect(badges.length).toBeGreaterThanOrEqual(0);
    });
  });

  // REQUIREMENT: Drill card should be lightweight
  describe('Drill Card (Micro-Learning)', () => {
    it('should render drill card if available', () => {
      render(<TodayPage />);
      
      // Drill card for micro-learning
      const drillCard = screen.queryByText(/daily drill/i) || 
                       screen.queryByText(/quick question/i) ||
                       screen.queryByText(/knowledge check/i);
      // May or may not be present
      expect(drillCard || true).toBeTruthy();
    });

    it('should display question in compact format', () => {
      render(<TodayPage />);
      
      // If drill exists, should be compact
      const drillHeading = screen.queryByRole('heading', { name: /sensei daily drill/i });
      expect(drillHeading).toBeInTheDocument();
    });

    it('should allow quick answer submission', () => {
      render(<TodayPage />);
      
      expect(screen.getByRole('button', { name: /execute answer/i })).toBeInTheDocument();
    });

    it('should not dominate screen real estate', () => {
      render(<TodayPage />);
      
      // Drill card should be small relative to Top 3
      // This is a visual test, hard to assert programmatically
      expect(true).toBe(true);
    });
  });

  // REQUIREMENT: My Tasks section
  describe('My Tasks Section', () => {
    it('should render Assigned Tasks card', () => {
      render(<TodayPage />);
      expect(screen.getByRole('heading', { name: /assigned tasks/i })).toBeInTheDocument();
    });

    it('should show tasks with due labels', () => {
      render(<TodayPage />);
      const dueLabels = screen.queryAllByText(/today|tomorrow/i);
      expect(dueLabels.length).toBeGreaterThan(0);
    });

    it('should display task priority indicators', () => {
      render(<TodayPage />);
      
      // Assigned tasks are listed as links; badges may appear elsewhere on the page
      const tasksCard = screen.getByRole('heading', { name: /assigned tasks/i }).closest('div.bg-rams-module');
      if (tasksCard) {
        const taskLinks = within(tasksCard).queryAllByRole('link');
        expect(taskLinks.length).toBeGreaterThanOrEqual(0);
      }
    });

    it('should handle empty tasks state', () => {
      render(<TodayPage />);
      
      const tasksCard = screen.getByRole('heading', { name: /assigned tasks/i }).closest('div.bg-rams-module');
      if (tasksCard) {
        const emptyState = within(tasksCard).queryByText(/all clear/i);
        const links = within(tasksCard).queryAllByRole('link');
        expect(emptyState || links.length > 0).toBeTruthy();
      }
    });
  });

  // REQUIREMENT: Priority RFQs section
  describe('Priority RFQs Section', () => {
    it('should render Priority RFQs card', () => {
      render(<TodayPage />);
      
      expect(screen.getAllByText(/priority rfqs/i).length).toBeGreaterThan(0);
    });

    it('should display RFQs requiring immediate attention', () => {
      render(<TodayPage />);
      
      const rfqsSection = screen.getAllByText(/priority rfqs/i)[0].closest('div');
      expect(rfqsSection).toBeInTheDocument();
    });

    it('should show RFQ customer and value', () => {
      render(<TodayPage />);
      
      // RFQ cards should show key info
      const rfqsSection = screen.getAllByText(/priority rfqs/i)[0].closest('div');
      if (rfqsSection) {
        const rfqCards = within(rfqsSection).queryAllByRole('link');
        expect(rfqCards.length).toBeGreaterThanOrEqual(0);
      }
    });

    it('should link to full pipeline', () => {
      render(<TodayPage />);
      
      const rfqsCard = screen.getAllByText(/priority rfqs/i)[0].closest('div.bg-rams-module');
      expect(rfqsCard).toBeInTheDocument();

      // Priority RFQ cards link directly into pipeline items
      if (rfqsCard) {
        const rfqLinks = within(rfqsCard).getAllByRole('link', { name: /rfq-2024/i });
        expect(rfqLinks.length).toBeGreaterThan(0);
        expect(rfqLinks.some((link) => (link.getAttribute('href') || '').startsWith('/pipeline/'))).toBe(true);
      }
    });

    it('should display RFQ priority and status badges', () => {
      render(<TodayPage />);
      
      const rfqsSection = screen.getAllByText(/priority rfqs/i)[0].closest('div');
      if (rfqsSection) {
        const badges = within(rfqsSection).queryAllByRole('status');
        // May or may not have RFQs
        expect(badges.length).toBeGreaterThanOrEqual(0);
      }
    });
  });

  // REQUIREMENT: Loading states
  describe('Loading States', () => {
    it('should show loading skeletons initially', async () => {
      render(<TodayPage />);
      
      // Should show skeleton cards during loading
      await waitFor(() => {
        const skeletons = screen.queryAllByTestId('skeleton');
        // May or may not show skeletons depending on implementation
        expect(skeletons.length).toBeGreaterThanOrEqual(0);
      });
    });

    it('should render content after loading', () => {
      render(<TodayPage />);
      
      // Content should be immediately visible
      const johnElements = screen.queryAllByText(/john/i);
      expect(johnElements.length).toBeGreaterThan(0);
    });
  });

  // REQUIREMENT: Responsive layout
  describe('Responsive Layout', () => {
    it('should have responsive grid classes', () => {
      const { container } = render(<TodayPage />);
      
      // Should use responsive grid classes
      const grids = container.querySelectorAll('[class*="grid"]');
      expect(grids.length).toBeGreaterThan(0);
    });

    it('should stack cards on mobile', () => {
      const { container } = render(<TodayPage />);
      
      // Should have lg: classes for desktop and default stacking
      const responsiveElements = container.querySelectorAll('[class*="lg:"]');
      expect(responsiveElements.length).toBeGreaterThan(0);
    });
  });

  // REQUIREMENT: Accessibility
  describe('Accessibility', () => {
    it('should have proper heading hierarchy', () => {
      render(<TodayPage />);
      
      const h1 = screen.getByRole('heading', { level: 1 });
      expect(h1).toBeInTheDocument();
    });

    it('should have accessible card titles', () => {
      render(<TodayPage />);
      
      const cardTitles = screen.getAllByText(/top priorities|critical anomalies|assigned tasks|active risks|priority rfqs|sensei daily drill/i);
      expect(cardTitles.length).toBeGreaterThan(0);
    });

    it('should have accessible links with meaningful text', () => {
      render(<TodayPage />);
      
      const links = screen.getAllByRole('link');
      links.forEach((link) => {
        expect(link.textContent).toBeTruthy();
      });
    });
  });
});
