'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  FileText,
  Calculator,
  Users,
  Package,
  Factory,
  FolderKanban,
  ClipboardCheck,
  AlertTriangle,
  LayoutGrid,
  Eye,
  GraduationCap,
  Wrench,
  Globe,
  Shield,
  Settings,
  ChevronLeft,
  ChevronRight,
  Search,
  Bell,
  Command,
  Menu,
  LogOut,
  DollarSign,
  BarChart3,
  ScrollText,
  Target,
  AlertCircle,
  FileSearch,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Avatar } from '@/components/ui/avatar';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useUIStore, useAuthStore } from '@/stores';
import { UserRole } from '@/types';
import { MobileBottomNav } from './mobile-nav';

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: number;
  roles?: UserRole[];
  children?: NavItem[];
}

interface NavSection {
  title: string;
  items: NavItem[];
  roles?: UserRole[];
}

const navSections: NavSection[] = [
  {
    title: 'Dashboards',
    items: [
      { label: 'Today', href: '/today', icon: Home },
      { label: 'Tasks', href: '/tasks', icon: ClipboardCheck },
      { label: 'Executive', href: '/executive', icon: Eye, roles: ['admin', 'ceo', 'gm', 'exec'] },
      { label: 'Analytics', href: '/analytics', icon: BarChart3, roles: ['admin', 'ceo', 'gm', 'exec', 'ops'] },
      { label: 'HR', href: '/hr', icon: Users, roles: ['admin', 'ceo', 'gm', 'exec', 'hr'] },
      { label: 'IT', href: '/it', icon: Shield, roles: ['admin', 'ceo', 'gm', 'it'] },
      { label: 'Warehouse', href: '/warehouse', icon: Package, roles: ['admin', 'ceo', 'gm', 'exec', 'ops', 'warehouse', 'supply_chain'] },
      { label: 'Auditor', href: '/auditor', icon: FileSearch, roles: ['admin', 'ceo', 'gm', 'auditor', 'quality'] },
    ]
  },
  {
    title: 'Sales & CRM',
    roles: ['admin', 'ceo', 'gm', 'exec', 'sales_engineer', 'estimator', 'ops', 'sales'],
    items: [
      { label: 'Sales Overview', href: '/sales', icon: Target },
      { label: 'Pipeline', href: '/pipeline', icon: FileText },
      { label: 'Quotes', href: '/quotes', icon: Calculator },
      { label: 'Customers', href: '/customers', icon: Users },
    ]
  },
  {
    title: 'Operations',
    roles: ['admin', 'ceo', 'gm', 'exec', 'ops', 'supervisor', 'team_lead', 'operator', 'quality', 'supply_chain', 'maintenance', 'warehouse', 'engineering'],
    items: [
      { label: 'Ops Overview', href: '/ops', icon: LayoutGrid },
      { label: 'Production', href: '/production', icon: Factory },
      { label: 'Projects', href: '/projects', icon: FolderKanban },
      { label: 'Products', href: '/products', icon: Package },
      { label: 'Obeya', href: '/obeya', icon: LayoutGrid },
      { label: 'A3 Reports', href: '/a3', icon: ScrollText },
      { label: 'CTQ Tracking', href: '/ctq', icon: Target },
      { label: 'Exceptions', href: '/exceptions', icon: AlertCircle },
    ]
  },
  {
    title: 'Quality & Support',
    items: [
      { label: 'Quality', href: '/quality', icon: Shield },
      { label: 'Andon', href: '/andon', icon: AlertTriangle },
      { label: 'Maintenance', href: '/maintenance', icon: Wrench },
      { label: 'Supply Chain', href: '/supply-chain', icon: Globe, roles: ['admin', 'ceo', 'gm', 'exec', 'ops', 'supply_chain', 'warehouse', 'purchasing', 'logistics'] },
      { label: 'Training', href: '/training', icon: GraduationCap },
      { label: 'Training Matrix', href: '/training/matrix', icon: FileSearch, roles: ['admin', 'ceo', 'gm', 'exec', 'ops', 'supervisor', 'hr'] },
      { label: 'Finance', href: '/finance', icon: DollarSign, roles: ['admin', 'ceo', 'gm', 'exec', 'finance', 'accountant'] },
    ]
  }
];

const bottomNavItems: NavItem[] = [
  { label: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarState, setSidebarState, setCommandPaletteOpen } = useUIStore();
  const { user, logout } = useAuthStore();
  const router = useRouter();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const isCollapsed = sidebarState === 'collapsed';
  const isHidden = sidebarState === 'hidden';

  const canAccess = (roles?: UserRole[]) => {
    if (!roles || roles.length === 0) return true;
    if (!user) return false;
    const userRoles = user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
    return roles.some(role => userRoles.includes(role));
  };

  const filteredSections = navSections
    .filter(section => canAccess(section.roles))
    .map(section => ({
      ...section,
      items: section.items.filter(item => canAccess(item.roles))
    }))
    .filter(section => section.items.length > 0);

  if (user?.role === 'admin') {
    // Add Admin section at the bottom of main nav
    filteredSections.push({
      title: 'Administration',
      items: [{ label: 'Admin Panel', href: '/admin', icon: Shield }]
    });
  }

  // On desktop, respect the hidden state. On mobile, use different logic
  const isMobileVisible = !isHidden; // On mobile, show when not hidden
  
  if (!mounted) return null;
  
  // On desktop, hide completely when isHidden
  // On mobile, slide in/out based on state
  const desktopHidden = isHidden;

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-card transition-all duration-300',
        // Mobile: slide in from left, always full width when visible
        'max-md:-translate-x-full max-md:w-64',
        isMobileVisible && 'max-md:translate-x-0',
        // Desktop: collapse/expand normally
        'md:translate-x-0',
        desktopHidden && 'md:-translate-x-full',
        isCollapsed ? 'md:w-16' : 'md:w-64'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b px-4">
        {!isCollapsed && (
          <Link href="/today" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
              S
            </div>
            <span className="font-semibold text-lg">Sensei</span>
          </Link>
        )}
        {isCollapsed && (
          <Link href="/today" className="mx-auto">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
              S
            </div>
          </Link>
        )}
      </div>

      {/* Search */}
      <div className="p-2">
        <Button
          variant="outline"
          className={cn(
            'w-full justify-start text-muted-foreground',
            isCollapsed ? 'px-2' : 'px-3'
          )}
          onClick={() => setCommandPaletteOpen(true)}
        >
          <Search className="h-4 w-4" />
          {!isCollapsed && (
            <>
              <span className="ml-2 flex-1 text-left">Search...</span>
              <kbd className="ml-auto pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                <span className="text-xs">⌘</span>K
              </kbd>
            </>
          )}
        </Button>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 overflow-y-auto p-2">
        {filteredSections.map((section, idx) => (
          <div key={section.title} className={cn('mb-4', idx === 0 && 'mt-0')}>
            {!isCollapsed && (
              <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {section.title}
              </h3>
            )}
            <ul className="space-y-1">
              {section.items.map((item) => {
                const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
                return (
                  <li key={item.href}>
                    {isCollapsed ? (
                      <Tooltip delayDuration={0}>
                        <TooltipTrigger asChild>
                          <Link
                            href={item.href}
                            className={cn(
                              'flex h-10 w-10 items-center justify-center rounded-md mx-auto',
                              'transition-colors hover:bg-accent hover:text-accent-foreground',
                              isActive && 'bg-accent text-accent-foreground'
                            )}
                          >
                            <item.icon className="h-5 w-5" />
                          </Link>
                        </TooltipTrigger>
                        <TooltipContent side="right">
                          {item.label}
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      <Link
                        href={item.href}
                        className={cn(
                          'flex h-10 items-center gap-3 rounded-md px-3',
                          'transition-colors hover:bg-accent hover:text-accent-foreground',
                          isActive && 'bg-accent text-accent-foreground'
                        )}
                      >
                        <item.icon className="h-5 w-5 shrink-0" />
                        <span className="truncate">{item.label}</span>
                        {item.badge && item.badge > 0 && (
                          <span className="ml-auto inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-medium text-primary-foreground">
                            {item.badge}
                          </span>
                        )}
                      </Link>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Bottom Navigation */}
      <div className="border-t p-2">
        <ul className="space-y-1 mb-2">
          {bottomNavItems.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
            return (
              <li key={item.href}>
                {isCollapsed ? (
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                      <Link
                        href={item.href}
                        className={cn(
                          'flex h-10 w-10 items-center justify-center rounded-md mx-auto',
                          'transition-colors hover:bg-accent hover:text-accent-foreground',
                          isActive && 'bg-accent text-accent-foreground'
                        )}
                      >
                        <item.icon className="h-5 w-5" />
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      {item.label}
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <Link
                    href={item.href}
                    className={cn(
                      'flex h-10 items-center gap-3 rounded-md px-3',
                      'transition-colors hover:bg-accent hover:text-accent-foreground',
                      isActive && 'bg-accent text-accent-foreground'
                    )}
                  >
                    <item.icon className="h-5 w-5 shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </Link>
                )}
              </li>
            );
          })}
        </ul>

        {/* User Profile */}
        {user && (
          <div className="mt-2 pt-2 border-t">
            {isCollapsed ? (
              <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <Link
                    href="/settings/profile"
                    className="flex h-10 w-10 items-center justify-center rounded-md mx-auto hover:bg-accent"
                  >
                    <Avatar
                      src={user.avatar_url}
                      alt={user.full_name}
                      fallback={user.full_name}
                      size="sm"
                    />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">
                  {user.full_name}
                </TooltipContent>
              </Tooltip>
            ) : (
              <Link
                href="/settings/profile"
                className="flex items-center gap-3 rounded-md p-2 hover:bg-accent"
              >
                <Avatar
                  src={user.avatar_url}
                  alt={user.full_name}
                  fallback={user.full_name}
                  size="sm"
                />
                <div className="flex-1 overflow-hidden">
                  <p className="truncate text-sm font-medium">{user.full_name}</p>
                  <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                </div>
              </Link>
            )}
          </div>
        )}

        {/* Logout */}
        <div className="mt-1">
          {isCollapsed ? (
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="flex h-10 w-10 items-center justify-center rounded-md mx-auto text-muted-foreground hover:text-danger hover:bg-danger/10"
                  onClick={async () => {
                    await logout();
                    router.push('/login');
                  }}
                >
                  <LogOut className="h-5 w-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                Logout
              </TooltipContent>
            </Tooltip>
          ) : (
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 px-3 text-muted-foreground hover:text-danger hover:bg-danger/10"
              onClick={async () => {
                await logout();
                router.push('/login');
              }}
            >
              <LogOut className="h-5 w-5 shrink-0" />
              <span>Logout</span>
            </Button>
          )}
        </div>

        {/* Collapse Toggle */}
        <Button
          variant="ghost"
          size="icon"
          className={cn('mt-2', isCollapsed ? 'mx-auto' : 'w-full')}
          onClick={() => setSidebarState(isCollapsed ? 'expanded' : 'collapsed')}
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              {!isCollapsed && <span className="ml-2">Collapse</span>}
            </>
          )}
        </Button>
      </div>
    </aside>
  );
}

export function Header() {
  const { 
    toggleCommandPalette, 
    toggleNotificationPanel, 
    unreadCount,
    setSidebarState,
    sidebarState,
  } = useUIStore();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4">
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={() => setSidebarState(sidebarState === 'hidden' ? 'expanded' : 'hidden')}
      >
        <Menu className="h-5 w-5" />
      </Button>

      <div className="flex-1" />

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Command Palette */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleCommandPalette}
            >
              <Command className="h-5 w-5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Command Palette</p>
            <kbd className="ml-2 text-xs text-muted-foreground">⌘K</kbd>
          </TooltipContent>
        </Tooltip>

        {/* Notifications */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              onClick={toggleNotificationPanel}
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-danger px-1 text-xs font-medium text-white">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>Notifications</TooltipContent>
        </Tooltip>
      </div>
    </header>
  );
}

export function MainLayout({ children }: { children: React.ReactNode }) {
  const { sidebarState, setSidebarState } = useUIStore();
  const isCollapsed = sidebarState === 'collapsed';
  const isHidden = sidebarState === 'hidden';
  const isMobileMenuOpen = sidebarState === 'expanded';

  // Close mobile menu on route change
  const pathname = usePathname();
  React.useEffect(() => {
    // Close mobile menu when route changes (only on mobile)
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setSidebarState('hidden');
    }
  }, [pathname, setSidebarState]);

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile overlay when sidebar is open */}
      <div 
        className={cn(
          'fixed inset-0 z-30 bg-black/50 backdrop-blur-sm transition-opacity duration-300 md:hidden',
          isMobileMenuOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={() => setSidebarState('hidden')}
        aria-hidden="true"
      />
      
      <Sidebar />
      <div
        className={cn(
          'transition-all duration-300',
          // On mobile (< md), no margin - sidebar overlays
          'md:ml-16',
          // On desktop, use sidebar state
          !isHidden && !isCollapsed && 'md:ml-64',
          isHidden && 'md:ml-0'
        )}
      >
        <Header />
        {/* Add bottom padding on mobile for the bottom nav */}
        <main className="p-6 pb-24 md:pb-6">
          {children}
        </main>
      </div>
      
      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />
    </div>
  );
}
