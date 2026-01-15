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
      <div className="flex h-screen w-screen flex-col items-center justify-center gap-6 bg-background relative overflow-hidden">
        <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none opacity-50 dark:opacity-20">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 blur-[120px] rounded-full animate-pulse" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-accent/20 blur-[120px] rounded-full animate-pulse [animation-delay:2s]" />
        </div>
        
        <div className="relative">
          <div className="h-20 w-20 rounded-[2rem] bg-primary/10 flex items-center justify-center shadow-glow animate-float">
            <div className="h-10 w-10 rounded-xl bg-primary text-primary-foreground flex items-center justify-center font-heading font-bold text-2xl quirky-card">
              S
            </div>
          </div>
          <div className="absolute -inset-4 border border-primary/20 rounded-[2.5rem] animate-pulse" />
        </div>
        
        <div className="space-y-2 text-center animate-in fade-in slide-in-from-bottom-2 duration-1000">
          <h2 className="text-xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/60">
            Synchronizing Intelligence
          </h2>
          <div className="flex items-center justify-center gap-1.5">
            <div className="h-1 w-1 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
            <div className="h-1 w-1 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
            <div className="h-1 w-1 rounded-full bg-primary animate-bounce" />
          </div>
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
