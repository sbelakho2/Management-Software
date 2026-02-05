import React from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { I18nProvider, type Locale } from '@/contexts/i18n-context';

interface RenderWithI18nOptions extends Omit<RenderOptions, 'wrapper'> {
  locale?: Locale;
}

export function renderWithI18n(ui: React.ReactElement, options: RenderWithI18nOptions = {}) {
  const { locale = 'en', ...renderOptions } = options;

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <I18nProvider defaultLocale={locale}>{children}</I18nProvider>;
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}
