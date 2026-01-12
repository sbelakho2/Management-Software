'use client';

import { useEffect } from 'react';
import { AlertTriangle, RefreshCw, Home, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: ErrorProps) {
  useEffect(() => {
    // Log error to monitoring service
    console.error('Dashboard error:', error);
  }, [error]);

  return (
    <div className="flex h-[60vh] items-center justify-center p-4">
      <Card className="max-w-lg w-full">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-7 w-7 text-destructive" />
          </div>
          <CardTitle className="text-xl">Something went wrong</CardTitle>
          <CardDescription>
            We encountered an error while loading this page.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {process.env.NODE_ENV === 'development' && (
            <div className="rounded-lg bg-muted p-3 text-sm">
              <p className="font-mono text-xs text-muted-foreground break-all">
                {error.message}
              </p>
              {error.digest && (
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  Error ID: {error.digest}
                </p>
              )}
            </div>
          )}
          
          <div className="flex flex-col sm:flex-row gap-2 justify-center">
            <Button 
              variant="outline" 
              onClick={() => window.history.back()}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Go Back
            </Button>
            <Button onClick={reset} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Try Again
            </Button>
            <Button 
              variant="secondary" 
              onClick={() => window.location.href = '/today'}
              className="gap-2"
            >
              <Home className="h-4 w-4" />
              Dashboard
            </Button>
          </div>
          
          <p className="text-center text-xs text-muted-foreground mt-4">
            If this problem persists, please contact support.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
