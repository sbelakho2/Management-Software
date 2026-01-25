import { render, screen } from '@testing-library/react';
import { I18nProvider } from '@/contexts/i18n-context';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
  usePathname: () => '/today',
}));

// Mock Next.js Link
jest.mock('next/link', () => {
  return function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  };
});

// Mock Radix UI Tooltip to avoid context issues
jest.mock('@radix-ui/react-tooltip', () => ({
  Root: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Trigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Portal: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Content: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Provider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock our Tooltip component
jest.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock stores
jest.mock('@/stores', () => ({
  useUIStore: () => ({
    sidebarState: 'expanded',
    setSidebarState: jest.fn(),
    setCommandPaletteOpen: jest.fn(),
  }),
  useAuthStore: () => ({
    user: {
      id: '1',
      email: 'test@example.com',
      full_name: 'Test User',
      role: 'gm',
      roles: ['gm'],
    },
  }),
}));

// Import after mocks
import { Sidebar } from '../sidebar';

function renderSidebar() {
  return render(
    <I18nProvider defaultLocale="en">
      <Sidebar />
    </I18nProvider>
  );
}

describe('Sidebar', () => {
  it('should render the sidebar', () => {
    renderSidebar();
    expect(screen.getByText('Sensei OS')).toBeInTheDocument();
  });

  it('should render navigation items', () => {
    renderSidebar();
    
    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('Pipeline')).toBeInTheDocument();
    expect(screen.getByText('Quotes')).toBeInTheDocument();
    expect(screen.getByText('Customers')).toBeInTheDocument();
    expect(screen.getByText('Products')).toBeInTheDocument();
    expect(screen.getByText('Production')).toBeInTheDocument();
    expect(screen.getByText('Quality')).toBeInTheDocument();
    expect(screen.getByText('Andon')).toBeInTheDocument();
    expect(screen.getByText('Obeya')).toBeInTheDocument();
  });

  it('should render the settings link', () => {
    renderSidebar();
    const settingsLinks = screen.getAllByRole('link', { name: 'Settings' });
    const settingsLink = settingsLinks.find((link) => link.getAttribute('href') === '/settings');
    expect(settingsLink).toBeDefined();
  });

  it('should render the logo', () => {
    renderSidebar();
    expect(screen.getByText('S')).toBeInTheDocument();
  });

  it('should have correct links', () => {
    renderSidebar();
    
    // Check that navigation items have proper href attributes
    const todayLink = screen.getByText('Today').closest('a');
    expect(todayLink).toHaveAttribute('href', '/today');
    
    const pipelineLink = screen.getByText('Pipeline').closest('a');
    expect(pipelineLink).toHaveAttribute('href', '/rfqs');
  });
});
