'use client';

import * as React from 'react';
import { useFinanceStore } from '@/stores';
import { useI18n } from '@/contexts/i18n-context';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

export default function CurrencySettingsPage() {
  const { t } = useI18n();
  const {
    currencySettings,
    fxRates,
    fetchCurrencySettings,
    updateCurrencySettings,
    fetchFxRates,
    upsertFxRate,
    loading,
  } = useFinanceStore();

  const [settingsForm, setSettingsForm] = React.useState({
    baseCurrency: 'USD',
    reportingCurrency: '',
    allowedCurrencies: '',
    fxSource: '',
    autoUpdateRates: false,
  });

  const [rateForm, setRateForm] = React.useState({
    asOf: '',
    fromCurrency: '',
    toCurrency: '',
    rate: '',
  });

  React.useEffect(() => {
    fetchCurrencySettings();
    fetchFxRates();
  }, [fetchCurrencySettings, fetchFxRates]);

  React.useEffect(() => {
    if (!currencySettings) return;
    setSettingsForm({
      baseCurrency: currencySettings.base_currency || 'USD',
      reportingCurrency: currencySettings.reporting_currency || '',
      allowedCurrencies: (currencySettings.allowed_currencies || []).join(', '),
      fxSource: currencySettings.fx_source || '',
      autoUpdateRates: Boolean(currencySettings.auto_update_rates),
    });
  }, [currencySettings]);

  const handleSaveSettings = async () => {
    const allowed = settingsForm.allowedCurrencies
      .split(',')
      .map((entry: string) => entry.trim())
      .filter(Boolean);

    await updateCurrencySettings({
      base_currency: settingsForm.baseCurrency,
      reporting_currency: settingsForm.reportingCurrency || undefined,
      allowed_currencies: allowed.length ? allowed : undefined,
      fx_source: settingsForm.fxSource || undefined,
      auto_update_rates: settingsForm.autoUpdateRates,
    });
  };

  const handleUpsertRate = async () => {
    if (!rateForm.asOf || !rateForm.fromCurrency || !rateForm.toCurrency || rateForm.rate === '') {
      return;
    }
    await upsertFxRate({
      as_of: rateForm.asOf,
      from_currency: rateForm.fromCurrency,
      to_currency: rateForm.toCurrency,
      rate: Number(rateForm.rate),
    });
    setRateForm({ asOf: '', fromCurrency: '', toCurrency: '', rate: '' });
  };

  return (
    <div className="space-y-8 page-fade-in">
      <div className="border-b border-rams-line pb-6">
        <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('pages.finance.currency.title') || 'Multi-Currency Settings'}</h1>
        <p className="text-2xs font-mono uppercase tracking-widest text-rams-muted">{t('pages.finance.currency.subtitle') || 'Configure base currency and manage FX rates'}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="border-b border-rams-line">
            <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.currency.currencyConfiguration') || 'Currency Configuration'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.currency.baseCurrency') || 'Base Currency'}</label>
                <Input
                  value={settingsForm.baseCurrency}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, baseCurrency: e.target.value.toUpperCase() }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.currency.reportingCurrency') || 'Reporting Currency'}</label>
                <Input
                  value={settingsForm.reportingCurrency}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, reportingCurrency: e.target.value.toUpperCase() }))}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.currency.allowedCurrencies') || 'Allowed Currencies'}</label>
                <Input
                  value={settingsForm.allowedCurrencies}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, allowedCurrencies: e.target.value.toUpperCase() }))}
                  placeholder={t('pages.finance.currency.allowedCurrenciesPlaceholder')}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.currency.fxSource') || 'FX Source'}</label>
                <Input
                  value={settingsForm.fxSource}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, fxSource: e.target.value }))}
                  placeholder={t('pages.finance.currency.manualPlaceholder') || 'Manual'}
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="auto-update"
                  type="checkbox"
                  checked={settingsForm.autoUpdateRates}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, autoUpdateRates: e.target.checked }))}
                  className="h-4 w-4"
                />
                <label htmlFor="auto-update" className="text-xs font-semibold text-muted-foreground">
                  {t('pages.finance.currency.autoUpdateFxRates') || 'Auto-update FX rates'}
                </label>
              </div>
            </div>
            <Button onClick={handleSaveSettings} disabled={loading} className="w-full">
              {t('pages.finance.currency.saveSettings') || 'Save Settings'}
            </Button>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="border-b border-rams-line">
            <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.currency.addFxRate') || 'Add FX Rate'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.currency.asOf') || 'As Of'}</label>
                <Input
                  type="date"
                  value={rateForm.asOf}
                  onChange={(e) => setRateForm((prev) => ({ ...prev, asOf: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.currency.rate') || 'Rate'}</label>
                <Input
                  type="number"
                  value={rateForm.rate}
                  onChange={(e) => setRateForm((prev) => ({ ...prev, rate: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.currency.from') || 'From'}</label>
                <Input
                  value={rateForm.fromCurrency}
                  onChange={(e) => setRateForm((prev) => ({ ...prev, fromCurrency: e.target.value.toUpperCase() }))}
                  placeholder={t('pages.finance.currency.fromPlaceholder')}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.currency.to') || 'To'}</label>
                <Input
                  value={rateForm.toCurrency}
                  onChange={(e) => setRateForm((prev) => ({ ...prev, toCurrency: e.target.value.toUpperCase() }))}
                  placeholder={t('pages.finance.currency.toPlaceholder')}
                />
              </div>
            </div>
            <Button onClick={handleUpsertRate} disabled={loading} className="w-full">
              {t('pages.finance.currency.saveRate') || 'Save Rate'}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-rams-sm border-rams-line bg-rams-module">
        <CardHeader className="border-b border-rams-line">
          <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.currency.fxRates') || 'FX Rates'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-rams-line bg-rams-panel">
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.currency.asOf') || 'As Of'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.currency.pair') || 'Pair'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.currency.rate') || 'Rate'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
              </tr>
            </thead>
            <tbody>
              {fxRates.length === 0 ? (
                <tr><td colSpan={4} className="py-8 text-center text-rams-muted">{t('pages.finance.currency.noFxRates') || 'No FX rates available.'}</td></tr>
              ) : (
                fxRates.map((rate: any) => (
                  <tr key={rate.id} className="border-b border-rams-line hover:bg-rams-panel transition-none">
                    <td className="py-3 px-4 text-muted-foreground">{rate.as_of}</td>
                    <td className="py-3 px-4 font-medium">{rate.from_currency} → {rate.to_currency}</td>
                    <td className="py-3 px-4 text-muted-foreground">{rate.rate}</td>
                    <td className="py-3 px-4">
                      <Badge variant="secondary">manual</Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
