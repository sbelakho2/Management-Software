'use client';

import { useEffect } from 'react';
import { AlertTriangle, RefreshCw, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useI18n } from '@/contexts/i18n-context';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function AuthError({ error, reset }: ErrorProps) {
  const { t } = useI18n();

  useEffect(() => {
    console.error('Auth error:', error);
  }, [error]);

  return (
    <div className="flex h-screen items-center justify-center p-4 bg-gradient-to-br from-background to-muted">
      <Card className="max-w-md w-full">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-6 w-6 text-destructive" />
          </div>
          <CardTitle>{t('auth.error.title')}</CardTitle>
          <CardDescription>
            {t('auth.error.description')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {process.env.NODE_ENV === 'development' && error.message && (
            <div className="rounded-lg bg-muted p-3">
              <p className="font-mono text-xs text-muted-foreground break-all">
                {error.message}
              </p>
            </div>
          )}
          
          <div className="flex flex-col gap-2">
            <Button onClick={reset} className="gap-2 w-full">
              <RefreshCw className="h-4 w-4" />
              {t('auth.error.tryAgain')}
            </Button>
            <Button 
              variant="outline" 
              onClick={() => window.location.href = '/login'}
              className="gap-2 w-full"
            >
              <ArrowLeft className="h-4 w-4" />
              {t('auth.error.backToLogin')}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
