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
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

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

  if (!mounted || isLoading) {
    return (
      <div className="flex h-screen w-screen flex-col items-center justify-center gap-8 bg-rams-chassis relative overflow-hidden">
        <div className="relative">
          <div className="h-20 w-20 bg-rams-module flex items-center justify-center border border-rams-border">
            <div className="h-10 w-10 bg-rams-orange text-black flex items-center justify-center font-mono font-black text-2xl border border-black/10">
              S
            </div>
          </div>
          <div className="absolute -inset-4 border border-rams-orange/20 animate-pulse" />
        </div>
        
        <div className="space-y-4 text-center animate-in fade-in duration-500">
          <h2 className="text-[10px] font-mono font-black uppercase tracking-[0.3em] text-foreground/60">
            SYSTEM_INITIALIZATION...
          </h2>
          <div className="flex items-center justify-center gap-1">
            <div className="h-1 w-4 bg-rams-orange animate-pulse" />
            <div className="h-1 w-4 bg-rams-orange animate-pulse [animation-delay:150ms]" />
            <div className="h-1 w-4 bg-rams-orange animate-pulse [animation-delay:300ms]" />
          </div>
        </div>

        <div className="fixed bottom-8 text-[9px] font-mono text-muted-foreground/40 uppercase tracking-widest">
          PROTOCOL: SENSEI_OS_V3 // BOOT_SEQUENCE
        </div>
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
