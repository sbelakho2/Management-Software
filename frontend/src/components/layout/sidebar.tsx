'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Bell,
  Menu,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Shield,
  Search,
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
import { hasPageAccess } from '@/lib/page-access';
import { NAV_SECTIONS, type NavItem, type NavSection } from '@/lib/navigation';
import { SkipToContent } from '@/components/ui/accessibility';
import { useI18n } from '@/contexts/i18n-context';

const bottomNavItems: NavItem[] = [
  { label: 'Settings', href: '/settings', icon: Shield },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarState, setSidebarState, setCommandPaletteOpen } = useUIStore();
  const { user, logout } = useAuthStore();
  const router = useRouter();
  const [mounted, setMounted] = React.useState(false);
  const { t, isRTL } = useI18n();

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const isCollapsed = sidebarState === 'collapsed';
  const isHidden = sidebarState === 'hidden';

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);

  const filteredSections = React.useMemo(() => {
    const sections = NAV_SECTIONS
      .map((section) => ({
        ...section,
        items: section.items.filter((item) => hasPageAccess(item.href, userRoles)),
      }))
      .filter((section) => section.items.length > 0);

    const isAdmin = userRoles.includes('admin' as UserRole);
    if (isAdmin && !sections.some((s) => s.title === 'Administration')) {
      sections.push({
        title: 'Administration',
        items: [{ label: 'Admin Panel', href: '/admin', icon: Shield }],
      });
    }

    return sections;
  }, [userRoles]);

  const filteredBottomNavItems = React.useMemo(() => {
    return bottomNavItems.filter(item => hasPageAccess(item.href, userRoles));
  }, [userRoles]);

  // On desktop, respect the hidden state. On mobile, use different logic
  const isMobileVisible = !isHidden; // On mobile, show when not hidden
  
  if (!mounted) return null;
  
  // On desktop, hide completely when isHidden
  // On mobile, slide in/out based on state
  const desktopHidden = isHidden;

  return (
    <aside
      className={cn(
        'fixed left-6 top-6 z-40 flex h-[calc(100vh-6rem)] flex-col rounded-rams-sm border border-rams-border bg-rams-module transition-all duration-300 ease-in-out',
        // Mobile: slide in from left, always full width when visible
        'max-md:-translate-x-[calc(100%+1.5rem)] max-md:w-64 max-md:left-6',
        isMobileVisible && 'max-md:translate-x-0',
        // Desktop: collapse/expand normally
        'md:translate-x-0',
        desktopHidden && 'md:-translate-x-[calc(100%+3rem)]',
        isCollapsed ? 'md:w-20' : 'md:w-64'
      )}
    >
      {/* Logo Area (Mechanical Feel) */}
      <div className="flex h-20 items-center justify-between px-6 border-b border-rams-border">
        {!isCollapsed && (
          <Link href="/today" className="flex items-center gap-3 group">
            <div className="flex h-10 w-10 items-center justify-center rounded-rams-sm bg-rams-orange text-black font-mono font-black border border-black/10">
              S
            </div>
            <span className="font-sans font-black text-xs uppercase tracking-[0.2em] opacity-80 group-hover:opacity-100 transition-opacity">
              Sensei OS
            </span>
          </Link>
        )}
        {isCollapsed && (
          <Link href="/today" className="mx-auto" aria-label="Sensei OS home">
            <div className="flex h-10 w-10 items-center justify-center rounded-rams-sm bg-rams-orange text-black font-mono font-black border border-black/10">
              S
            </div>
          </Link>
        )}
      </div>

      {/* Search (Module Inset) */}
      <div className="px-4 py-4">
        <Button
          variant="outline"
          className={cn(
            'w-full justify-start text-muted-foreground border-rams-border bg-rams-panel hover:bg-rams-panel/80 transition-none rounded-rams-sm',
            isCollapsed ? 'px-0 justify-center h-12 w-12 mx-auto' : 'px-4 h-11'
          )}
          onClick={() => setCommandPaletteOpen(true)}
          aria-label={t('navigation.search')}
        >
          <Search className={cn("h-4 w-4", isCollapsed ? "h-5 w-5" : "")} />
          {!isCollapsed && (
            <>
              <span className={cn("flex-1 text-[10px] font-bold uppercase tracking-widest", isRTL ? "mr-3 text-right" : "ml-3 text-left")}>{t('common.search')}</span>
              <kbd className={cn("pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded-sm border border-rams-border bg-rams-chassis px-1.5 font-mono text-[9px] font-bold text-muted-foreground/60", isRTL ? "mr-auto" : "ml-auto")}>
                ⌘K
              </kbd>
            </>
          )}
        </Button>
      </div>

      {/* Main Navigation (Racked Slots) */}
      <nav className="flex-1 overflow-y-auto p-2">
        {filteredSections.map((section, idx) => (
          <div key={section.title} className={cn('mb-6', idx === 0 && 'mt-2')}>
            {!isCollapsed && (
              <h3 className="mb-3 px-6 text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/40 border-l-2 border-rams-orange/20 ml-2">
                {section.title}
              </h3>
            )}
            <ul className="space-y-0.5 px-2">
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
                              'flex h-12 w-12 items-center justify-center rounded-rams-sm mx-auto transition-none border border-transparent',
                              isActive 
                                ? 'bg-rams-orange text-black font-black border-black/10' 
                                : 'text-muted-foreground hover:bg-rams-panel hover:text-foreground'
                            )}
                            aria-label={item.label}
                            aria-current={isActive ? 'page' : undefined}
                          >
                            <item.icon className="h-5 w-5" />
                          </Link>
                        </TooltipTrigger>
                        <TooltipContent side="right" className="font-mono text-[10px] uppercase font-bold bg-rams-panel text-foreground border-rams-border rounded-none">
                          {item.label}
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      <Link
                        href={item.href}
                        className={cn(
                          'flex h-10 items-center gap-3 rounded-rams-sm px-4 transition-none group relative overflow-hidden border border-transparent',
                          isActive 
                            ? 'bg-rams-panel text-foreground font-black border-rams-border shadow-[inset_2px_0_0_0_#FFBE00]' 
                            : 'text-muted-foreground hover:bg-rams-panel/50 hover:text-foreground'
                        )}
                      >
                        <item.icon className={cn("h-4 w-4 shrink-0 transition-none", isActive ? "text-rams-orange" : "text-muted-foreground group-hover:text-foreground")} />
                        <span className="truncate text-[11px] font-bold uppercase tracking-wider">{item.label}</span>
                        {item.badge && item.badge > 0 && (
                          <span className={cn(
                            "ml-auto inline-flex h-4 min-w-4 items-center justify-center rounded-rams-sm px-1 text-[9px] font-black border",
                            isActive ? "bg-rams-orange text-black border-black/10" : "bg-rams-panel text-muted-foreground border-rams-border"
                          )}>
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

      {/* Bottom Navigation (Service Module) */}
      <div className="border-t border-rams-border bg-rams-panel/30 p-2">
        <ul className="space-y-0.5 mb-4">
          {filteredBottomNavItems.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
            return (
              <li key={item.href}>
                {isCollapsed ? (
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                      <Link
                        href={item.href}
                        className={cn(
                          'flex h-10 w-10 items-center justify-center rounded-rams-sm mx-auto transition-none border',
                          isActive 
                            ? 'bg-rams-panel text-foreground border-rams-border' 
                            : 'border-transparent text-muted-foreground hover:bg-rams-panel hover:text-foreground'
                        )}
                        aria-label={item.label}
                        aria-current={isActive ? 'page' : undefined}
                      >
                        <item.icon className="h-4 w-4" />
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="font-mono text-[10px] uppercase font-bold bg-rams-panel text-foreground border-rams-border rounded-none">
                      {item.label}
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <Link
                    href={item.href}
                    className={cn(
                      'flex h-9 items-center gap-3 rounded-rams-sm px-3 transition-none border',
                      isActive 
                        ? 'bg-rams-panel text-foreground font-bold border-rams-border' 
                        : 'border-transparent text-muted-foreground hover:bg-rams-panel hover:text-foreground'
                    )}
                  >
                    <item.icon className={cn("h-4 w-4 shrink-0", isActive ? "text-foreground" : "text-muted-foreground")} />
                    <span className="truncate text-[10px] font-bold uppercase tracking-widest">{item.label}</span>
                  </Link>
                )}
              </li>
            );
          })}
        </ul>

        {/* User Module */}
        {user && (
          <div className="mt-2 pt-2 border-t border-rams-border/50">
            {isCollapsed ? (
              <Link
                href="/settings/profile"
                className="flex h-10 w-10 items-center justify-center rounded-rams-sm mx-auto hover:bg-rams-panel"
              >
                <Avatar
                  src={user.avatar_url}
                  alt={user.full_name}
                  fallback={user.full_name}
                  size="sm"
                  className="rounded-rams-sm"
                />
              </Link>
            ) : (
              <Link
                href="/settings/profile"
                className="flex items-center gap-3 rounded-rams-sm p-2 hover:bg-rams-panel border border-transparent hover:border-rams-border transition-none"
              >
                <Avatar
                  src={user.avatar_url}
                  alt={user.full_name}
                  fallback={user.full_name}
                  size="sm"
                  className="rounded-rams-sm border border-rams-border/20"
                />
                <div className="flex-1 overflow-hidden">
                  <p className="truncate text-[11px] font-black uppercase tracking-tight">{user.full_name}</p>
                  <p className="truncate text-[9px] font-mono opacity-50 uppercase tracking-tighter">{user.email}</p>
                </div>
              </Link>
            )}
          </div>
        )}

        {/* Control Buttons */}
        <div className="mt-1 flex flex-col gap-1">
          {isCollapsed ? (
            <Button
              variant="ghost"
              size="icon"
              className="flex h-12 w-12 items-center justify-center rounded-rams-sm mx-auto text-muted-foreground hover:text-rams-red hover:bg-rams-red/5 transition-none"
              onClick={async () => {
                await logout();
                router.push('/login');
              }}
              aria-label={t('auth.logout')}
            >
              <LogOut className={cn("h-5 w-5", isRTL && "rtl-flip")} />
            </Button>
          ) : (
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 px-4 h-10 rounded-rams-sm text-muted-foreground hover:text-rams-red hover:bg-rams-red/5 transition-none border border-transparent hover:border-rams-red/20"
              onClick={async () => {
                await logout();
                router.push('/login');
              }}
            >
              <LogOut className={cn("h-4 w-4 shrink-0", isRTL && "rtl-flip")} />
              <span className="text-[10px] font-black uppercase tracking-widest">{t('auth.logout')}</span>
            </Button>
          )}
          
          <Button
            variant="ghost"
            size="icon"
            className={cn('h-8 transition-none rounded-rams-sm hover:bg-rams-panel hover:text-foreground border border-transparent hover:border-rams-border', isCollapsed ? 'mx-auto w-10' : 'w-full px-4 justify-start')}
            onClick={() => setSidebarState(isCollapsed ? 'expanded' : 'collapsed')}
          >
            {isCollapsed ? (
              <ChevronRight className={cn("h-4 w-4", isRTL && "rtl-flip")} />
            ) : (
              <div className="flex items-center gap-3">
                <ChevronLeft className={cn("h-3 w-3", isRTL && "rtl-flip")} />
                <span className="text-[9px] font-black uppercase tracking-[0.3em] opacity-40">{t('accessibility.collapseSection')}</span>
              </div>
            )}
          </Button>
        </div>
      </div>
    </aside>
  );
}

export function FloatingNotifications() {
  const { toggleNotificationPanel, unreadCount } = useUIStore();
  const { t, isRTL } = useI18n();

  return (
    <div className={cn("fixed top-4 z-40", isRTL ? "left-4" : "right-4")}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="relative rounded-rams-sm h-10 w-10 border border-rams-border bg-rams-panel shadow-none hover:bg-rams-module hover:text-foreground transition-none"
            onClick={toggleNotificationPanel}
            aria-label={t('navigation.notifications')}
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className={cn("absolute -top-1 flex h-4 min-w-4 items-center justify-center rounded-rams-sm bg-rams-orange px-1 text-[9px] font-black text-black border border-black/10", isRTL ? "-left-1" : "-right-1")}>
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent className="font-mono text-[10px] uppercase font-bold bg-rams-panel text-foreground border-rams-border rounded-none">{t('navigation.notifications')}</TooltipContent>
      </Tooltip>
    </div>
  );
}

export function MobileMenuButton() {
  const { sidebarState, setSidebarState } = useUIStore();
  const { t } = useI18n();

  return (
    <Button
      variant="ghost"
      size="icon"
      className="fixed top-4 left-4 z-40 md:hidden rounded-rams-sm h-10 w-10 border border-rams-border bg-rams-panel shadow-none hover:bg-rams-module hover:text-foreground transition-none"
      onClick={() => setSidebarState(sidebarState === 'hidden' ? 'expanded' : 'hidden')}
      aria-label={sidebarState === 'hidden' ? t('accessibility.openMenu') : t('accessibility.closeMenu')}
    >
      <Menu className="h-5 w-5" />
    </Button>
  );
}

// Keep Header export for backward compatibility (but it's now empty)
export function Header() {
  return null;
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
    <div className="min-h-screen bg-rams-chassis selection:bg-rams-orange/30 selection:text-black">
      <SkipToContent targetId="main-content" />
      
      {/* Floating UI Elements */}
      <FloatingNotifications />
      <MobileMenuButton />
      
      {/* Mobile overlay when sidebar is open */}
      <div 
        className={cn(
          'fixed inset-0 z-30 bg-black/60 transition-opacity duration-300 md:hidden',
          isMobileMenuOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={() => setSidebarState('hidden')}
        aria-hidden="true"
      />
      
      <Sidebar />
      <div
        className={cn(
          'transition-all duration-300 ease-in-out min-h-screen flex flex-col',
          // On mobile (< md), no margin - sidebar overlays
          'md:pl-24',
          // On desktop, use sidebar state
          !isHidden && !isCollapsed && 'md:pl-72',
          isHidden && 'md:pl-0'
        )}
      >
        <main id="main-content" className="flex-1 p-4 md:p-8 pb-24 md:pb-8 page-fade-in max-w-[1600px] w-full mx-auto">
          {children}
        </main>
      </div>
      
      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />
    </div>
  );
}
