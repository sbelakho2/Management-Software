'use client';

import { WifiOff, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { SkipToContent } from '@/components/ui/accessibility';
import { useI18n } from '@/contexts/i18n-context';

export default function OfflinePage() {
  const { t } = useI18n();
  return (
    <div className="min-h-screen flex items-center justify-center bg-rams-chassis p-4 page-fade-in">
      <SkipToContent targetId="main-content" />
      <main id="main-content" className="text-center max-w-md w-full">
        <div className="bg-rams-module p-10 border border-rams-line rounded-rams-sm space-y-8 transition-none">
          <div className="inline-flex items-center justify-center w-24 h-24 bg-rams-panel border border-rams-line rounded-rams-sm mb-2">
            <WifiOff className="h-12 w-12 text-rams-orange" />
          </div>
          
          <div className="space-y-3">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              Connection Lost
            </h1>
            
            <p className="text-[11px] font-mono font-bold text-muted-foreground uppercase tracking-widest">
              The Sensei OS intelligence link has been interrupted. 
              Some core features are currently unavailable.
            </p>
          </div>

          <div className="space-y-4 pt-4">
            <Button
              onClick={() => window.location.reload()}
              className="w-full h-10 rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] transition-none"
              size="default"
            >
              <RefreshCw className="mr-2 h-3.5 w-3.5" />
              Re-establish Link
            </Button>
            
            <Button
              asChild
              variant="outline"
              className="w-full h-10 rounded-rams-sm border-rams-line transition-none"
              size="default"
            >
              <Link href="/">
                <Home className="mr-2 h-3.5 w-3.5" />
                Return to Base
              </Link>
            </Button>
          </div>

          <div className="p-5 bg-rams-panel/20 border border-rams-line text-left">
            <h2 className="text-[9px] font-black uppercase tracking-[0.2em] text-rams-orange mb-3">Offline Capabilities</h2>
            <ul className="text-[10px] font-mono font-bold text-muted-foreground/60 space-y-2 uppercase tracking-widest">
              <li className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 bg-rams-green" />
                Cached intelligence data
              </li>
              <li className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 bg-rams-green" />
                Previously synchronized pages
              </li>
              <li className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 bg-rams-green" />
                Draft synchronization on reconnect
              </li>
            </ul>
          </div>

          <p className="text-[9px] uppercase tracking-[0.3em] font-black text-muted-foreground/30 pt-4">
            Sensei OS • Precision Continuity
          </p>
        </div>
      </main>
    </div>
  );
}
