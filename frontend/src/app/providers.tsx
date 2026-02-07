'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ThemeProvider } from 'next-themes';
import { useState, useEffect, type ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { PWAProvider } from '@/components/pwa/pwa-provider';
import { MaturityProvider } from '@/components/ui/deployment-maturity';
import { OfflineProvider, ErrorBoundary } from '@/components/ui/error-experience';
import { DesignSystemProvider } from '@/components/ui/design-system';
import { RUMProvider } from '@/components/ui/performance-rum';
import { I18nProvider } from '@/contexts/i18n-context';
import { useAuthStore } from '@/stores';
import { AppearanceInitializer } from '@/components/appearance-initializer';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const isE2E = process.env.NEXT_PUBLIC_E2E === '1';
  const pathname = usePathname();
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute — data is fresh
            gcTime: 10 * 60 * 1000, // 10 minutes — keep cache longer to reduce refetches
            retry: 2,
            retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 15000),
            refetchOnWindowFocus: false,
            refetchOnReconnect: 'always',
            // Structural sharing prevents unnecessary re-renders when data is deeply equal
            structuralSharing: true,
            // Throw to nearest ErrorBoundary on query failure (caught by our ErrorBoundary)
            throwOnError: false,
            networkMode: 'online',
          },
          mutations: {
            retry: 0,
            networkMode: 'online',
          },
        },
      })
  );

  // Load user on mount - but skip on auth pages to avoid "session expired" flash
  const loadUser = useAuthStore((state) => state.loadUser);
  useEffect(() => {
    const isAuthPage = pathname?.startsWith('/login') || pathname?.startsWith('/register') || pathname?.startsWith('/forgot-password');
    if (!isAuthPage) {
      loadUser();
    }
  }, [loadUser, pathname]);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <AppearanceInitializer />
          <I18nProvider>
            <TooltipProvider delayDuration={0}>
              <DesignSystemProvider>
                <RUMProvider>
                  <MaturityProvider>
                    <OfflineProvider>
                      <PWAProvider>
                        {children}
                      </PWAProvider>
                    </OfflineProvider>
                  </MaturityProvider>
                </RUMProvider>
              </DesignSystemProvider>
              <Toaster />
            </TooltipProvider>
          </I18nProvider>
        </ThemeProvider>
        {process.env.NODE_ENV === 'development' && !isE2E && (
          <ReactQueryDevtools initialIsOpen={false} />
        )}
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
