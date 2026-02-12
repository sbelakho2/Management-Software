'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';

export type ErrorBoundaryProps = {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, info: React.ErrorInfo) => void;
};

type ErrorBoundaryState = {
  hasError: boolean;
  error?: Error;
};

function ErrorBoundaryFallback() {
  const { t } = useI18n();

  return (
    <div className="rounded-xl border border-rose-200/60 bg-rose-50/70 p-4 text-sm text-rose-900">
      {t('errors.boundaryFallback')}
    </div>
  );
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    if (this.props.onError) {
      this.props.onError(error, info);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <ErrorBoundaryFallback />
        )
      );
    }

    return this.props.children;
  }
}
