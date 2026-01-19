'use client';

import { useEffect, useState } from 'react';
import { useI18n } from '@/contexts/i18n-context';
import { useCurrency, CURRENCIES, CurrencyCode, getCurrencyForLocale } from '@/stores/currency-store';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, CheckCircle, AlertCircle, Clock, Globe } from 'lucide-react';

export function CurrencySettings() {
  const { t, locale } = useI18n();
  const {
    displayCurrency,
    baseCurrency,
    rates,
    isLoading,
    error,
    setDisplayCurrency,
    fetchRates,
    formatInCurrency,
  } = useCurrency();

  const [previewAmount] = useState(1000);

  // Auto-detect suggested currency based on locale
  const suggestedCurrency = getCurrencyForLocale(locale);

  useEffect(() => {
    // Fetch rates on mount if stale
    fetchRates();
  }, [fetchRates]);

  const handleCurrencyChange = (currency: string) => {
    setDisplayCurrency(currency as CurrencyCode);
  };

  const handleRefreshRates = async () => {
    await fetchRates();
  };

  const formatLastUpdated = () => {
    if (!rates.date) return t('settings.currency.never');
    return new Date(rates.date).toLocaleDateString(locale, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-6">
      {/* Currency Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-primary" />
            {t('settings.currency.displayCurrency')}
          </CardTitle>
          <CardDescription>
            {t('settings.currency.displayCurrencyDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t('settings.currency.selectCurrency')}
              </label>
              <Select value={displayCurrency} onValueChange={handleCurrencyChange}>
                <SelectTrigger>
                  <SelectValue placeholder={t('settings.currency.selectCurrency')} />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CURRENCIES).map(([code, info]) => (
                    <SelectItem key={code} value={code}>
                      <span className="flex items-center gap-2">
                        <span className="font-mono">{info.symbol}</span>
                        <span>{code} - {info.name}</span>
                        {code === suggestedCurrency && (
                          <Badge variant="secondary" className="ml-2 text-xs">
                            {t('settings.currency.suggested')}
                          </Badge>
                        )}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t('settings.currency.preview')}
              </label>
              <div className="rounded-lg border bg-muted/50 p-3">
                <div className="text-2xl font-semibold">
                  {formatInCurrency(previewAmount, displayCurrency)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {t('settings.currency.sampleAmount')}
                </div>
              </div>
            </div>
          </div>

          {displayCurrency !== suggestedCurrency && (
            <div className="flex items-center gap-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20 p-3 text-sm">
              <AlertCircle className="h-4 w-4 text-yellow-500" />
              <span>
                {t('settings.currency.suggestionNote', { currency: suggestedCurrency })}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setDisplayCurrency(suggestedCurrency)}
              >
                {t('settings.currency.useSuggested')}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Exchange Rates */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <RefreshCw className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''} text-primary`} />
                {t('settings.currency.exchangeRates')}
              </CardTitle>
              <CardDescription>
                {t('settings.currency.exchangeRatesDesc')}
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshRates}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              {t('settings.currency.refresh')}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Status */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              {error ? (
                <AlertCircle className="h-4 w-4 text-red-500" />
              ) : (
                <CheckCircle className="h-4 w-4 text-green-500" />
              )}
              <span>
                {error 
                  ? t('settings.currency.statusError')
                  : t('settings.currency.statusOk')
                }
              </span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>{t('settings.currency.lastUpdated')}: {formatLastUpdated()}</span>
            </div>
          </div>

          {/* Rates Table */}
          <div className="rounded-lg border overflow-hidden">
            <div className="grid grid-cols-4 gap-4 bg-muted/50 p-3 text-sm font-medium">
              <div>{t('settings.currency.currency')}</div>
              <div className="text-right">{t('settings.currency.rateVsEur')}</div>
              <div className="text-right">{t('settings.currency.rateVsDisplay', { currency: displayCurrency })}</div>
              <div className="text-right">{t('settings.currency.valueIn', { currency: displayCurrency })}</div>
            </div>
            <div className="divide-y">
              {Object.entries(CURRENCIES).map(([code, info]) => {
                const rateVsEur = rates.rates[code] || 1;
                const displayRate = rates.rates[displayCurrency] || 1;
                const crossRate = rateVsEur / displayRate;
                const convertedValue = 1000 * crossRate;

                return (
                  <div
                    key={code}
                    className={`grid grid-cols-4 gap-4 p-3 text-sm ${
                      code === displayCurrency ? 'bg-primary/5' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-muted-foreground">{info.symbol}</span>
                      <span className="font-medium">{code}</span>
                      {code === displayCurrency && (
                        <Badge variant="outline" className="text-xs">
                          {t('settings.currency.display')}
                        </Badge>
                      )}
                    </div>
                    <div className="text-right font-mono">
                      {rateVsEur.toFixed(4)}
                    </div>
                    <div className="text-right font-mono">
                      {code === displayCurrency ? '1.0000' : crossRate.toFixed(4)}
                    </div>
                    <div className="text-right font-mono">
                      {formatInCurrency(convertedValue, code as CurrencyCode, { maximumFractionDigits: 0 })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            {t('settings.currency.disclaimer')}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
