'use client';

import { Loader2 } from 'lucide-react';
import { useI18n } from '@/contexts/i18n-context';

export default function AuthLoading() {
  const { t } = useI18n();

  return (
    <div className="flex h-screen items-center justify-center bg-gradient-to-br from-background to-muted">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">{t('auth.loading')}</p>
      </div>
    </div>
  );
}
