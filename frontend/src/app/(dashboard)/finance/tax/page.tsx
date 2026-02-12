'use client';

import * as React from 'react';
import { useFinanceStore } from '@/stores';
import { useI18n } from '@/contexts/i18n-context';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

export default function TaxCompliancePage() {
  const { t } = useI18n();
  const {
    taxJurisdictions,
    taxRates,
    taxTransactions,
    fetchTaxJurisdictions,
    fetchTaxRates,
    fetchTaxTransactions,
    createTaxJurisdiction,
    createTaxRate,
    createTaxTransaction,
    loading,
  } = useFinanceStore();

  const [jurisdictionForm, setJurisdictionForm] = React.useState({
    code: '',
    name: '',
    country: '',
    region: '',
    status: 'active',
  });

  const [rateForm, setRateForm] = React.useState({
    jurisdictionId: '',
    taxType: '',
    rate: '',
    effectiveDate: '',
    status: 'active',
  });

  const [transactionForm, setTransactionForm] = React.useState({
    jurisdictionId: '',
    taxRateId: '',
    referenceType: '',
    referenceId: '',
    taxableAmount: '',
    taxAmount: '',
    currency: 'USD',
    status: 'pending',
  });

  React.useEffect(() => {
    fetchTaxJurisdictions();
    fetchTaxRates();
    fetchTaxTransactions();
  }, [fetchTaxJurisdictions, fetchTaxRates, fetchTaxTransactions]);

  const handleCreateJurisdiction = async () => {
    if (!jurisdictionForm.code || !jurisdictionForm.name || !jurisdictionForm.country) {
      return;
    }
    await createTaxJurisdiction({
      code: jurisdictionForm.code.toUpperCase(),
      name: jurisdictionForm.name,
      country: jurisdictionForm.country,
      region: jurisdictionForm.region || undefined,
      status: jurisdictionForm.status,
    });
    setJurisdictionForm({
      code: '',
      name: '',
      country: '',
      region: '',
      status: 'active',
    });
  };

  const handleCreateRate = async () => {
    if (!rateForm.jurisdictionId || !rateForm.taxType || !rateForm.effectiveDate) {
      return;
    }
    await createTaxRate({
      jurisdiction_id: rateForm.jurisdictionId,
      tax_type: rateForm.taxType,
      rate: Number(rateForm.rate || 0),
      effective_date: rateForm.effectiveDate,
      status: rateForm.status,
    });
    setRateForm({
      jurisdictionId: '',
      taxType: '',
      rate: '',
      effectiveDate: '',
      status: 'active',
    });
  };

  const handleCreateTransaction = async () => {
    if (!transactionForm.jurisdictionId || !transactionForm.taxRateId || !transactionForm.referenceId) {
      return;
    }
    await createTaxTransaction({
      jurisdiction_id: transactionForm.jurisdictionId,
      tax_rate_id: transactionForm.taxRateId,
      reference_type: transactionForm.referenceType || 'sale',
      reference_id: transactionForm.referenceId,
      taxable_amount: Number(transactionForm.taxableAmount || 0),
      tax_amount: Number(transactionForm.taxAmount || 0),
      currency: transactionForm.currency,
      status: transactionForm.status,
    });
    setTransactionForm({
      jurisdictionId: '',
      taxRateId: '',
      referenceType: '',
      referenceId: '',
      taxableAmount: '',
      taxAmount: '',
      currency: 'USD',
      status: 'pending',
    });
  };

  return (
    <div className="space-y-8 page-fade-in">
      <div className="border-b border-rams-line pb-6">
        <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('pages.finance.tax.title') || 'Tax Compliance'}</h1>
        <p className="text-2xs font-mono uppercase tracking-widest text-rams-muted">{t('pages.finance.tax.subtitle') || 'Maintain jurisdictions, rates, and tax transaction records'}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="border-b border-rams-line">
            <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.tax.taxJurisdiction') || 'Tax Jurisdiction'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.code') || 'Code'}</label>
                <Input value={jurisdictionForm.code} onChange={(e) => setJurisdictionForm((prev) => ({ ...prev, code: e.target.value }))} placeholder={t('pages.finance.tax.codePlaceholder')} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.name') || 'Name'}</label>
                <Input value={jurisdictionForm.name} onChange={(e) => setJurisdictionForm((prev) => ({ ...prev, name: e.target.value }))} placeholder={t('pages.finance.tax.namePlaceholder')} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.country') || 'Country'}</label>
                <Input value={jurisdictionForm.country} onChange={(e) => setJurisdictionForm((prev) => ({ ...prev, country: e.target.value }))} placeholder={t('pages.finance.tax.countryPlaceholder')} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.region') || 'Region'}</label>
                <Input value={jurisdictionForm.region} onChange={(e) => setJurisdictionForm((prev) => ({ ...prev, region: e.target.value }))} placeholder={t('pages.finance.tax.regionPlaceholder')} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('common.status') || 'Status'}</label>
                <Input value={jurisdictionForm.status} onChange={(e) => setJurisdictionForm((prev) => ({ ...prev, status: e.target.value }))} placeholder={t('pages.finance.tax.activePlaceholder')} />
              </div>
            </div>
            <Button onClick={handleCreateJurisdiction} disabled={loading} className="w-full">
              {t('pages.finance.tax.saveJurisdiction') || 'Save Jurisdiction'}
            </Button>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="border-b border-rams-line">
            <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.tax.taxRate') || 'Tax Rate'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.jurisdictionId') || 'Jurisdiction ID'}</label>
                <Input value={rateForm.jurisdictionId} onChange={(e) => setRateForm((prev) => ({ ...prev, jurisdictionId: e.target.value }))} placeholder={t('pages.finance.tax.uuidPlaceholder')} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.taxType') || 'Tax Type'}</label>
                <Input value={rateForm.taxType} onChange={(e) => setRateForm((prev) => ({ ...prev, taxType: e.target.value }))} placeholder={t('pages.finance.tax.taxTypePlaceholder')} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.rate') || 'Rate'}</label>
                <Input value={rateForm.rate} onChange={(e) => setRateForm((prev) => ({ ...prev, rate: e.target.value }))} placeholder="0.075" />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.effectiveDate') || 'Effective Date'}</label>
                <Input type="date" value={rateForm.effectiveDate} onChange={(e) => setRateForm((prev) => ({ ...prev, effectiveDate: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('common.status') || 'Status'}</label>
                <Input value={rateForm.status} onChange={(e) => setRateForm((prev) => ({ ...prev, status: e.target.value }))} placeholder={t('pages.finance.tax.activePlaceholder')} />
              </div>
            </div>
            <Button onClick={handleCreateRate} disabled={loading} className="w-full">
              {t('pages.finance.tax.saveRate') || 'Save Rate'}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-rams-sm border-rams-line bg-rams-module">
        <CardHeader className="border-b border-rams-line">
          <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.tax.jurisdictions') || 'Jurisdictions'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-rams-line bg-rams-panel">
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.code') || 'Code'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.name') || 'Name'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.country') || 'Country'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.region') || 'Region'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
              </tr>
            </thead>
            <tbody>
              {taxJurisdictions.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-rams-muted">{t('pages.finance.tax.noJurisdictions') || 'No jurisdictions configured.'}</td></tr>
              ) : (
                taxJurisdictions.map((jurisdiction: any) => (
                  <tr key={jurisdiction.id} className="border-b border-rams-line hover:bg-rams-panel transition-none">
                    <td className="py-3 px-4 font-medium">{jurisdiction.code}</td>
                    <td className="py-3 px-4 text-muted-foreground">{jurisdiction.name}</td>
                    <td className="py-3 px-4 text-muted-foreground">{jurisdiction.country}</td>
                    <td className="py-3 px-4 text-muted-foreground">{jurisdiction.region || '-'}</td>
                    <td className="py-3 px-4"><Badge variant="secondary">{jurisdiction.status}</Badge></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card className="rounded-rams-sm border-rams-line bg-rams-module">
        <CardHeader className="border-b border-rams-line">
          <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.tax.taxRates') || 'Tax Rates'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-rams-line bg-rams-panel">
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.jurisdiction') || 'Jurisdiction'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.type') || 'Type'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.rate') || 'Rate'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.effective') || 'Effective'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
              </tr>
            </thead>
            <tbody>
              {taxRates.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-rams-muted">{t('pages.finance.tax.noTaxRates') || 'No tax rates configured.'}</td></tr>
              ) : (
                taxRates.map((rate: any) => (
                  <tr key={rate.id} className="border-b border-rams-line hover:bg-rams-panel transition-none">
                    <td className="py-3 px-4 text-muted-foreground">{rate.jurisdiction_id}</td>
                    <td className="py-3 px-4 font-medium">{rate.tax_type}</td>
                    <td className="py-3 px-4 text-muted-foreground">{rate.rate}</td>
                    <td className="py-3 px-4 text-muted-foreground">{rate.effective_date}</td>
                    <td className="py-3 px-4"><Badge variant="secondary">{rate.status}</Badge></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card className="rounded-rams-sm border-rams-line bg-rams-module">
        <CardHeader className="border-b border-rams-line">
          <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.tax.taxTransactions') || 'Tax Transactions'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.jurisdictionId') || 'Jurisdiction ID'}</label>
              <Input value={transactionForm.jurisdictionId} onChange={(e) => setTransactionForm((prev) => ({ ...prev, jurisdictionId: e.target.value }))} placeholder={t('pages.finance.tax.uuidPlaceholder')} />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.taxRateId') || 'Tax Rate ID'}</label>
              <Input value={transactionForm.taxRateId} onChange={(e) => setTransactionForm((prev) => ({ ...prev, taxRateId: e.target.value }))} placeholder={t('pages.finance.tax.uuidPlaceholder')} />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.referenceType') || 'Reference Type'}</label>
              <Input value={transactionForm.referenceType} onChange={(e) => setTransactionForm((prev) => ({ ...prev, referenceType: e.target.value }))} placeholder={t('pages.finance.tax.referenceTypePlaceholder')} />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.referenceId') || 'Reference ID'}</label>
              <Input value={transactionForm.referenceId} onChange={(e) => setTransactionForm((prev) => ({ ...prev, referenceId: e.target.value }))} placeholder={t('pages.finance.tax.referenceIdPlaceholder')} />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.taxableAmount') || 'Taxable Amount'}</label>
              <Input value={transactionForm.taxableAmount} onChange={(e) => setTransactionForm((prev) => ({ ...prev, taxableAmount: e.target.value }))} placeholder="1000" />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.taxAmount') || 'Tax Amount'}</label>
              <Input value={transactionForm.taxAmount} onChange={(e) => setTransactionForm((prev) => ({ ...prev, taxAmount: e.target.value }))} placeholder="75" />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.tax.currency') || 'Currency'}</label>
              <Input value={transactionForm.currency} onChange={(e) => setTransactionForm((prev) => ({ ...prev, currency: e.target.value.toUpperCase() }))} placeholder={t('pages.finance.tax.currencyPlaceholder')} />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('common.status') || 'Status'}</label>
              <Input value={transactionForm.status} onChange={(e) => setTransactionForm((prev) => ({ ...prev, status: e.target.value }))} placeholder={t('pages.finance.tax.pendingPlaceholder')} />
            </div>
          </div>
          <Button onClick={handleCreateTransaction} disabled={loading} className="w-full">
            {t('pages.finance.tax.recordTransaction') || 'Record Transaction'}
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-rams-sm border-rams-line bg-rams-module">
        <CardHeader className="border-b border-rams-line">
          <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.tax.transactionLedger') || 'Transaction Ledger'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-rams-line bg-rams-panel">
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.reference') || 'Reference'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.taxable') || 'Taxable'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.tax') || 'Tax'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.tax.currency') || 'Currency'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
              </tr>
            </thead>
            <tbody>
              {taxTransactions.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-rams-muted">{t('pages.finance.tax.noTransactions') || 'No transactions recorded.'}</td></tr>
              ) : (
                taxTransactions.map((txn: any) => (
                  <tr key={txn.id} className="border-b border-rams-line hover:bg-rams-panel">
                    <td className="py-3 px-4 font-medium">{txn.reference_type} · {txn.reference_id}</td>
                    <td className="py-3 px-4 text-muted-foreground">{txn.taxable_amount}</td>
                    <td className="py-3 px-4 text-muted-foreground">{txn.tax_amount}</td>
                    <td className="py-3 px-4"><Badge variant="secondary">{txn.currency}</Badge></td>
                    <td className="py-3 px-4"><Badge variant="secondary">{txn.status}</Badge></td>
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
