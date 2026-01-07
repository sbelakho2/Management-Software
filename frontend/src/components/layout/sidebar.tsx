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
  ClipboardCheck,
  AlertTriangle,
  LayoutGrid,
  GraduationCap,
  Settings,
  ChevronLeft,
  ChevronRight,
  Search,
  Bell,
  Command,
  Menu,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Avatar } from '@/components/ui/avatar';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useUIStore, useAuthStore } from '@/stores';

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: number;
  children?: NavItem[];
}

const mainNavItems: NavItem[] = [
  { label: 'Today', href: '/today', icon: Home },
  { label: 'Pipeline', href: '/pipeline', icon: FileText },
  { label: 'Quotes', href: '/quotes', icon: Calculator },
  { label: 'Customers', href: '/customers', icon: Users },
  { label: 'Products', href: '/products', icon: Package },
  { label: 'Production', href: '/production', icon: Factory },
  { label: 'Quality', href: '/quality', icon: ClipboardCheck },
  { label: 'Andon', href: '/andon', icon: AlertTriangle },
  { label: 'Obeya', href: '/obeya', icon: LayoutGrid },
  { label: 'Training', href: '/training', icon: GraduationCap },
];

const bottomNavItems: NavItem[] = [
  { label: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarState, setSidebarState, setCommandPaletteOpen } = useUIStore();
  const { user } = useAuthStore();

  const isCollapsed = sidebarState === 'collapsed';
  const isHidden = sidebarState === 'hidden';

  if (isHidden) return null;

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-card transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-64'
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
        <ul className="space-y-1">
          {mainNavItems.map((item) => {
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
      </nav>

      {/* Bottom Navigation */}
      <div className="border-t p-2">
        <ul className="space-y-1">
          {bottomNavItems.map((item) => {
            const isActive = pathname === item.href;
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
  const { sidebarState } = useUIStore();
  const isCollapsed = sidebarState === 'collapsed';
  const isHidden = sidebarState === 'hidden';

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div
        className={cn(
          'transition-all duration-300',
          isHidden ? 'ml-0' : isCollapsed ? 'ml-16' : 'ml-64'
        )}
      >
        <Header />
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
