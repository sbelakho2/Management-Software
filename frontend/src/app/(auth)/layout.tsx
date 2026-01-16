'use client';

import * as React from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores';
import { useRouter } from 'next/navigation';
import { SkipToContent } from '@/components/ui/accessibility';

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuthStore();
  const router = useRouter();

  React.useEffect(() => {
    if (isAuthenticated && !isLoading) {
      router.push('/today');
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden page-fade-in">
      <SkipToContent targetId="main-content" />
      <div className="flex-1 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
          <Link href="/" className="inline-flex items-center gap-3 mb-8 group transition-all hover:scale-105 active:scale-95">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground font-bold text-2xl shadow-glow quirky-card">
              S
            </div>
            <span className="font-heading font-bold text-3xl tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              Sensei OS
            </span>
          </Link>
        </div>

        <main id="main-content" className="mt-4 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="premium-glass p-8 sm:p-10 rounded-[2.5rem] shadow-premium border border-white/20 dark:border-white/5 transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
            {children}
          </div>
        </main>
      </div>
      
      <div className="py-8 text-center text-sm text-muted-foreground/40 relative z-10">
        <p className="tracking-[0.3em] uppercase text-[9px] font-bold">&copy; {new Date().getFullYear()} Sensei OS • Precision Intelligence</p>
      </div>
    </div>
  );
}
