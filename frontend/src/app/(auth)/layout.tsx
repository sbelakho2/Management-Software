'use client';

import * as React from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores';
import { useRouter } from 'next/navigation';

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
      {/* Decorative background elements for premium feel */}
      <div className="absolute top-0 left-0 w-full h-full -z-10 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-primary/5 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-primary/5 blur-[120px]" />
      </div>

      <div className="flex-1 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
          <Link href="/" className="inline-flex items-center gap-2 mb-8 group transition-all">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground font-bold text-2xl shadow-lg shadow-primary/20 group-hover:scale-105 transition-transform">
              S
            </div>
            <span className="font-bold text-3xl tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              Sensei OS
            </span>
          </Link>
        </div>

        <div className="mt-4 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="premium-glass p-8 sm:p-10 rounded-2xl shadow-premium border border-white/20 dark:border-white/5">
            {children}
          </div>
        </div>
      </div>
      
      <div className="py-8 text-center text-sm text-muted-foreground/60 relative z-10">
        <p className="tracking-widest uppercase text-[10px] font-bold">&copy; {new Date().getFullYear()} Sensei OS. Precision Manufacturing Intelligence.</p>
      </div>
    </div>
  );
}
