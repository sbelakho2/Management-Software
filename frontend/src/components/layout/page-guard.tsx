'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Loader2, ShieldAlert } from 'lucide-react';
import { useAuthStore } from '@/stores';
import type { UserRole } from '@/types';
import { useI18n } from '@/contexts/i18n-context';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface PageGuardProps {
  children: React.ReactNode;
  /** Required roles for this page. Empty array = all authenticated users */
  requiredRoles?: UserRole[];
  /** Custom fallback when unauthorized */
  fallback?: React.ReactNode;
}

/**
 * PageGuard - Wraps page content with role-based access control
 * 
 * @example
 * <PageGuard requiredRoles={['admin', 'ceo', 'gm']}>
 *   <ExecutiveDashboard />
 * </PageGuard>
 */
export function PageGuard({ children, requiredRoles = [], fallback }: PageGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading, isAuthenticated } = useAuthStore();
  const { t } = useI18n();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push(`/login?from=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  // Still loading auth state
  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Not authenticated
  if (!isAuthenticated || !user) {
    return null; // Will redirect
  }

  // Check role access
  const userRoles: UserRole[] = user.roles?.length > 0 ? user.roles : [user.role as UserRole];

  // Admin (and backend superuser) always have full access
  const isFullAccess =
    userRoles.includes('admin') ||
    userRoles.includes('superuser' as UserRole);
  
  // If requiredRoles is empty, all authenticated users have access
  // Otherwise check if user has any of the required roles
  const hasAccess =
    isFullAccess ||
    requiredRoles.length === 0 ||
    userRoles.some((role) => requiredRoles.includes(role));

  if (!hasAccess) {
    if (fallback) {
      return <>{fallback}</>;
    }

    // Show access denied message
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Card className="max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
              <ShieldAlert className="h-7 w-7 text-destructive" />
            </div>
            <CardTitle>{t('components.pageGuard.accessRestricted')}</CardTitle>
            <CardDescription>
              {t('components.pageGuard.noPermission')}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center">
            <Button onClick={() => router.push('/today')} variant="outline">
              {t('components.pageGuard.returnToDashboard')}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Hook to get current user's roles
 */
export function useUserRoles(): UserRole[] {
  const { user } = useAuthStore();
  if (!user) return [];
  return user.roles?.length > 0 ? user.roles : [user.role as UserRole];
}

/**
 * Hook to check if current user can view financial data
 */
export function useCanViewFinancials(): boolean {
  const roles = useUserRoles();
  const financialRoles: UserRole[] = ['admin', 'ceo', 'gm', 'exec', 'finance', 'accountant'];
  return roles.some(role => financialRoles.includes(role));
}

/**
 * Hook to check if current user is admin
 */
export function useIsAdmin(): boolean {
  const roles = useUserRoles();
  return roles.includes('admin') || roles.includes('superuser' as UserRole);
}
