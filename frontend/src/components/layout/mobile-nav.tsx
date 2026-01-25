'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Menu,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUIStore, useAuthStore } from '@/stores';
import type { UserRole } from '@/types';
import { hasPageAccess } from '@/lib/page-access';
import { NAV_SECTIONS, type NavItem } from '@/lib/navigation';

/**
 * MobileBottomNav - Fixed bottom navigation for mobile devices
 * 
 * Shows 4-5 quick-access navigation items plus a "More" button
 * to open the full sidebar drawer.
 */
export function MobileBottomNav() {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const { setSidebarState } = useUIStore();

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    const roles = user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
    return roles;
  }, [user]);

  // Extract a few key items for the bottom nav
  const mobileNavItems = React.useMemo(() => {
    const items: NavItem[] = [];
    const allItems = NAV_SECTIONS.flatMap((section) => section.items);

    const addIfAccessible = (href: string) => {
      const item = allItems.find((candidate) => candidate.href === href);
      if (item && hasPageAccess(item.href, userRoles)) {
        items.push(item);
      }
    };

    // Keep these stable + role-aware (do not rely on NAV_SECTIONS ordering)
    addIfAccessible('/today');
    addIfAccessible('/projects');
    addIfAccessible('/tasks');
    addIfAccessible('/ops');
    addIfAccessible('/sales');

    // De-dupe + cap at 4 items (More button is the 5th)
    const uniqueByHref = Array.from(new Map(items.map((item) => [item.href, item])).values());
    return uniqueByHref.slice(0, 4);
  }, [userRoles]);

  // Don't show on auth pages
  if (pathname?.startsWith('/login') || pathname?.startsWith('/register') || pathname?.startsWith('/forgot')) {
    return null;
  }

  return (
    <nav 
      className="fixed bottom-4 left-4 right-4 z-50 flex h-16 items-center justify-around rounded-3xl border premium-glass shadow-premium md:hidden safe-area-inset-bottom"
      role="navigation"
      aria-label="Mobile navigation"
    >
      {mobileNavItems.map((item) => {
        const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex flex-col items-center justify-center gap-1 px-3 py-2 min-w-[64px] rounded-2xl transition-all duration-300',
              'text-muted-foreground',
              'hover:text-primary active:scale-90',
              isActive && 'text-primary bg-primary/10 shadow-glow'
            )}
            aria-current={isActive ? 'page' : undefined}
            aria-label={item.label}
          >
            <item.icon 
              className={cn('h-5 w-5 transition-transform duration-300', isActive && 'text-primary scale-110')} 
              aria-hidden="true" 
            />
            <span className={cn(
              'text-[10px] font-bold tracking-tight',
              isActive && 'text-primary'
            )}>
              {item.label}
            </span>
          </Link>
        );
      })}
      
      {/* More button to open sidebar drawer */}
      <button
        onClick={() => setSidebarState('expanded')}
        className="flex flex-col items-center justify-center gap-1 px-3 py-2 min-w-[64px] rounded-2xl text-muted-foreground transition-all duration-300 hover:text-primary active:scale-90 hover:bg-primary/5"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
        <span className="text-[10px] font-bold tracking-tight">More</span>
      </button>
    </nav>
  );
}

/**
 * MobileDrawerOverlay - Overlay for mobile sidebar drawer
 */
interface MobileDrawerOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MobileDrawerOverlay({ isOpen, onClose }: MobileDrawerOverlayProps) {
  // Close on escape key
  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when open
  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden"
      onClick={onClose}
      aria-hidden="true"
    />
  );
}

/**
 * useMobileNav hook - Provides mobile navigation utilities
 */
export function useMobileNav() {
  const { sidebarState, setSidebarState } = useUIStore();
  const isMobileMenuOpen = sidebarState === 'expanded';

  const openMobileMenu = React.useCallback(() => {
    setSidebarState('expanded');
  }, [setSidebarState]);

  const closeMobileMenu = React.useCallback(() => {
    setSidebarState('hidden');
  }, [setSidebarState]);

  const toggleMobileMenu = React.useCallback(() => {
    if (isMobileMenuOpen) {
      closeMobileMenu();
    } else {
      openMobileMenu();
    }
  }, [isMobileMenuOpen, openMobileMenu, closeMobileMenu]);

  return {
    isMobileMenuOpen,
    openMobileMenu,
    closeMobileMenu,
    toggleMobileMenu,
  };
}

export default MobileBottomNav;
