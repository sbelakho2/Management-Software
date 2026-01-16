'use client';

import { WifiOff, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { SkipToContent } from '@/components/ui/accessibility';

export default function OfflinePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 page-fade-in">
      <SkipToContent targetId="main-content" />
      <main id="main-content" className="text-center max-w-md w-full">
        <div className="premium-glass p-10 rounded-[2.5rem] shadow-premium border border-white/20 dark:border-white/5 space-y-8 transition-all duration-500 hover:shadow-premium-hover">
          <div className="inline-flex items-center justify-center w-24 h-24 bg-primary/10 rounded-[2rem] mb-2 shadow-glow">
            <WifiOff className="h-12 w-12 text-primary animate-pulse" />
          </div>
          
          <div className="space-y-3">
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              Connection Lost
            </h1>
            
            <p className="text-muted-foreground font-medium text-sm">
              The Sensei OS intelligence link has been interrupted. 
              Some core features are currently unavailable.
            </p>
          </div>

          <div className="space-y-4 pt-4">
            <Button
              onClick={() => window.location.reload()}
              className="w-full h-12 text-base rounded-2xl shadow-glow subtle-shine"
              size="xl"
            >
              <RefreshCw className="mr-2 h-5 w-5" />
              Re-establish Link
            </Button>
            
            <Button
              asChild
              variant="outline"
              className="w-full h-12 text-base rounded-2xl"
              size="xl"
            >
              <Link href="/">
                <Home className="mr-2 h-5 w-5" />
                Return to Base
              </Link>
            </Button>
          </div>

          <div className="p-5 bg-primary/5 rounded-2xl text-left border border-primary/10">
            <h2 className="font-heading font-bold text-[10px] uppercase tracking-[0.2em] text-primary/60 mb-3">Offline Capabilities</h2>
            <ul className="text-xs text-muted-foreground/80 space-y-2 font-medium">
              <li className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary/40" />
                Cached intelligence data
              </li>
              <li className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary/40" />
                Previously synchronized pages
              </li>
              <li className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary/40" />
                Draft synchronization on reconnect
              </li>
            </ul>
          </div>

          <p className="text-[10px] uppercase tracking-[0.3em] font-bold text-muted-foreground/30 pt-4">
            Sensei OS • Precision Continuity
          </p>
        </div>
      </main>
    </div>
  );
}
