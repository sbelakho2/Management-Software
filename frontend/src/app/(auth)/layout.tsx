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
    <div className="min-h-screen flex flex-col relative overflow-hidden bg-rams-chassis page-fade-in">
      <SkipToContent targetId="main-content" />
      
      {/* Industrial Bezel Frame */}
      <div className="fixed inset-0 border-[8px] border-rams-chassis pointer-events-none z-[100] hidden md:block" aria-hidden="true" />
      
      {/* Screw Details */}
      <div className="fixed top-2 left-2 z-[101] hidden md:block opacity-30 select-none text-foreground">
        <svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1" /><path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1" /></svg>
      </div>
      <div className="fixed top-2 right-2 z-[101] hidden md:block opacity-30 select-none text-foreground">
        <svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1" /><path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1" /></svg>
      </div>
      <div className="fixed bottom-2 left-2 z-[101] hidden md:block opacity-30 select-none text-foreground">
        <svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1" /><path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1" /></svg>
      </div>
      <div className="fixed bottom-2 right-2 z-[101] hidden md:block opacity-30 select-none text-foreground">
        <svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1" /><path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1" /></svg>
      </div>

      <div className="flex-1 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
          <Link href="/" className="inline-flex items-center gap-4 mb-12 group">
            <div className="flex h-14 w-14 items-center justify-center rounded-rams-sm bg-rams-orange text-black font-mono font-black text-2xl border border-black/10">
              S
            </div>
            <div className="text-left">
              <span className="font-sans font-black text-2xl uppercase tracking-[0.2em] text-foreground/90 block leading-none">
                Sensei OS
              </span>
              <span className="font-mono text-[9px] font-bold uppercase tracking-[0.3em] text-muted-foreground/40 mt-1 block">
                INTELLIGENT_SYSTEM_V3
              </span>
            </div>
          </Link>
        </div>

        <main id="main-content" className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-rams-module border border-rams-border rounded-rams-sm p-8 sm:p-10 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-rams-orange/20" />
            {children}
          </div>
        </main>
      </div>
      
      {/* System Metadata Bar (Bottom) */}
      <div className="fixed bottom-0 left-0 right-0 h-8 bg-rams-chassis z-[100] border-t border-rams-border px-6 hidden md:flex items-center justify-between text-[10px] font-mono opacity-60 uppercase tracking-widest pointer-events-none">
        <div className="flex gap-6">
          <span>STATION: AUTH-01</span>
          <span>OS_VER: 3.0.0-RAMS</span>
        </div>
        <div className="flex gap-6 text-right">
          <span>{new Date().getFullYear()} &copy; STARZ_MOROCCO</span>
          <span>PROTOCOL: ACCESS_CONTROL</span>
        </div>
      </div>
    </div>
  );
}
