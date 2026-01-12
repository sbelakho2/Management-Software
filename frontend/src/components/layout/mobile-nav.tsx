'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  ClipboardCheck,
  LayoutGrid,
  Target,
  Menu,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUIStore, useAuthStore } from '@/stores';
import type { UserRole } from '@/types';

interface MobileNavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  roles?: UserRole[];
}

const mobileNavItems: MobileNavItem[] = [
  { label: 'Home', href: '/today', icon: Home },
  { label: 'Tasks', href: '/tasks', icon: ClipboardCheck },
  { label: 'Ops', href: '/ops', icon: LayoutGrid },
  { label: 'Sales', href: '/sales', icon: Target },
];

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

  const canAccess = React.useCallback((roles?: UserRole[]) => {
    if (!roles || roles.length === 0) return true;
    if (!user) return false;
    const userRoles = user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
    return roles.some(role => userRoles.includes(role));
  }, [user]);

  const filteredItems = mobileNavItems.filter(item => canAccess(item.roles));

  // Don't show on auth pages
  if (pathname?.startsWith('/login') || pathname?.startsWith('/register') || pathname?.startsWith('/forgot')) {
    return null;
  }

  return (
    <nav 
      className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:hidden safe-area-inset-bottom"
      role="navigation"
      aria-label="Mobile navigation"
    >
      {filteredItems.map((item) => {
        const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex flex-col items-center justify-center gap-1 px-3 py-2 min-w-[64px]',
              'text-muted-foreground transition-colors',
              'hover:text-foreground active:scale-95',
              isActive && 'text-primary'
            )}
            aria-current={isActive ? 'page' : undefined}
          >
            <item.icon 
              className={cn('h-5 w-5', isActive && 'text-primary')} 
              aria-hidden="true" 
            />
            <span className={cn(
              'text-[10px] font-medium',
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
        className="flex flex-col items-center justify-center gap-1 px-3 py-2 min-w-[64px] text-muted-foreground transition-colors hover:text-foreground active:scale-95"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
        <span className="text-[10px] font-medium">More</span>
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
