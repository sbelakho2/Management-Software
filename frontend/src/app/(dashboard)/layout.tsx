'use client';

import * as React from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores';
import { TooltipProvider } from '@/components/ui/tooltip';
import { MainLayout, CommandPalette } from '@/components/layout';
import { Loader2 } from 'lucide-react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading, loadUser } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    // Attempt to load user if not already authenticated
    if (!isAuthenticated) {
      loadUser();
    }
  }, [isAuthenticated, loadUser]);

  React.useEffect(() => {
    // Redirect to login if not authenticated and not loading
    if (!isAuthenticated && !isLoading) {
      const searchParams = new URLSearchParams();
      if (pathname !== '/') {
        searchParams.set('from', pathname);
      }
      router.push(`/login${searchParams.toString() ? `?${searchParams.toString()}` : ''}`);
    }
  }, [isAuthenticated, isLoading, router, pathname]);

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect via useEffect
  }

  return (
    <TooltipProvider delayDuration={0}>
      <MainLayout>
        {children}
      </MainLayout>
      <CommandPalette />
    </TooltipProvider>
  );
}
