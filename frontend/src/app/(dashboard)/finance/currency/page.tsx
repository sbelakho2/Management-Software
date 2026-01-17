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
      reporting_currency: settingsForm.reportingCurrency || null,
      allowed_currencies: allowed.length ? allowed : null,
      fx_source: settingsForm.fxSource || null,
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
      <div>
        <h1 className="text-4xl font-heading font-bold tracking-tight">Multi-Currency Settings</h1>
        <p className="text-muted-foreground">Configure base currency and manage FX rates</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-base">Currency Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Base Currency</label>
                <Input
                  value={settingsForm.baseCurrency}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, baseCurrency: e.target.value.toUpperCase() }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Reporting Currency</label>
                <Input
                  value={settingsForm.reportingCurrency}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, reportingCurrency: e.target.value.toUpperCase() }))}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">Allowed Currencies</label>
                <Input
                  value={settingsForm.allowedCurrencies}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, allowedCurrencies: e.target.value.toUpperCase() }))}
                  placeholder="USD, EUR, GBP"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">FX Source</label>
                <Input
                  value={settingsForm.fxSource}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, fxSource: e.target.value }))}
                  placeholder="Manual"
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
                  Auto-update FX rates
                </label>
              </div>
            </div>
            <Button onClick={handleSaveSettings} disabled={loading} className="w-full">
              Save Settings
            </Button>
          </CardContent>
        </Card>

        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-base">Add FX Rate</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">As Of</label>
                <Input
                  type="date"
                  value={rateForm.asOf}
                  onChange={(e) => setRateForm((prev) => ({ ...prev, asOf: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Rate</label>
                <Input
                  type="number"
                  value={rateForm.rate}
                  onChange={(e) => setRateForm((prev) => ({ ...prev, rate: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">From</label>
                <Input
                  value={rateForm.fromCurrency}
                  onChange={(e) => setRateForm((prev) => ({ ...prev, fromCurrency: e.target.value.toUpperCase() }))}
                  placeholder="USD"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">To</label>
                <Input
                  value={rateForm.toCurrency}
                  onChange={(e) => setRateForm((prev) => ({ ...prev, toCurrency: e.target.value.toUpperCase() }))}
                  placeholder="EUR"
                />
              </div>
            </div>
            <Button onClick={handleUpsertRate} disabled={loading} className="w-full">
              Save Rate
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-base">FX Rates</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">As Of</th>
                <th className="py-3 px-4 text-left font-medium">Pair</th>
                <th className="py-3 px-4 text-left font-medium">Rate</th>
                <th className="py-3 px-4 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {fxRates.length === 0 ? (
                <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">No FX rates available.</td></tr>
              ) : (
                fxRates.map((rate: any) => (
                  <tr key={rate.id} className="border-b hover:bg-muted/50">
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
