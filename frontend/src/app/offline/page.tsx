'use client';

import { WifiOff, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';

export default function OfflinePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center w-20 h-20 bg-muted rounded-full mb-6">
          <WifiOff className="h-10 w-10 text-muted-foreground" />
        </div>
        
        <h1 className="text-2xl font-bold mb-2">You're Offline</h1>
        
        <p className="text-muted-foreground mb-6">
          It looks like you've lost your internet connection. 
          Some features may not be available until you're back online.
        </p>

        <div className="space-y-3">
          <button
            onClick={() => window.location.reload()}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </button>
          
          <Link
            href="/"
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 border rounded-md hover:bg-muted transition-colors"
          >
            <Home className="h-4 w-4" />
            Go to Homepage
          </Link>
        </div>

        <div className="mt-8 p-4 bg-muted/50 rounded-lg text-left">
          <h2 className="font-medium text-sm mb-2">Available Offline:</h2>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>• Previously viewed pages</li>
            <li>• Cached data (may be outdated)</li>
            <li>• Draft forms (will sync when online)</li>
          </ul>
        </div>

        <p className="text-xs text-muted-foreground mt-6">
          Your work is automatically saved. Changes will sync when you're back online.
        </p>
      </div>
    </div>
  );
}
