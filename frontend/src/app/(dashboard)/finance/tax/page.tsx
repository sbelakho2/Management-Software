'use client';

import * as React from 'react';
import { useFinanceStore } from '@/stores';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

export default function TaxCompliancePage() {
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
      region: jurisdictionForm.region || null,
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
      <div>
        <h1 className="text-4xl font-heading font-bold tracking-tight">Tax Compliance</h1>
        <p className="text-muted-foreground">Maintain jurisdictions, rates, and tax transaction records</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-base">Tax Jurisdiction</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Code</label>
                <Input value={jurisdictionForm.code} onChange={(e) => setJurisdictionForm((prev) => ({ ...prev, code: e.target.value }))} placeholder="CA-BC" />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Name</label>
                <Input value={jurisdictionForm.name} onChange={(e) => setJurisdictionForm((prev) => ({ ...prev, name: e.target.value }))} placeholder="British Columbia" />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Country</label>
                <Input value={jurisdictionForm.country} onChange={(e) => setJurisdictionForm((prev) => ({ ...prev, country: e.target.value }))} placeholder="Canada" />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Region</label>
                <Input value={jurisdictionForm.region} onChange={(e) => setJurisdictionForm((prev) => ({ ...prev, region: e.target.value }))} placeholder="BC" />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Status</label>
                <Input value={jurisdictionForm.status} onChange={(e) => setJurisdictionForm((prev) => ({ ...prev, status: e.target.value }))} placeholder="active" />
              </div>
            </div>
            <Button onClick={handleCreateJurisdiction} disabled={loading} className="w-full">
              Save Jurisdiction
            </Button>
          </CardContent>
        </Card>

        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-base">Tax Rate</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Jurisdiction ID</label>
                <Input value={rateForm.jurisdictionId} onChange={(e) => setRateForm((prev) => ({ ...prev, jurisdictionId: e.target.value }))} placeholder="UUID" />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Tax Type</label>
                <Input value={rateForm.taxType} onChange={(e) => setRateForm((prev) => ({ ...prev, taxType: e.target.value }))} placeholder="vat" />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Rate</label>
                <Input value={rateForm.rate} onChange={(e) => setRateForm((prev) => ({ ...prev, rate: e.target.value }))} placeholder="0.075" />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Effective Date</label>
                <Input type="date" value={rateForm.effectiveDate} onChange={(e) => setRateForm((prev) => ({ ...prev, effectiveDate: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Status</label>
                <Input value={rateForm.status} onChange={(e) => setRateForm((prev) => ({ ...prev, status: e.target.value }))} placeholder="active" />
              </div>
            </div>
            <Button onClick={handleCreateRate} disabled={loading} className="w-full">
              Save Rate
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-base">Jurisdictions</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">Code</th>
                <th className="py-3 px-4 text-left font-medium">Name</th>
                <th className="py-3 px-4 text-left font-medium">Country</th>
                <th className="py-3 px-4 text-left font-medium">Region</th>
                <th className="py-3 px-4 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {taxJurisdictions.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">No jurisdictions configured.</td></tr>
              ) : (
                taxJurisdictions.map((jurisdiction: any) => (
                  <tr key={jurisdiction.id} className="border-b hover:bg-muted/50">
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

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-base">Tax Rates</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">Jurisdiction</th>
                <th className="py-3 px-4 text-left font-medium">Type</th>
                <th className="py-3 px-4 text-left font-medium">Rate</th>
                <th className="py-3 px-4 text-left font-medium">Effective</th>
                <th className="py-3 px-4 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {taxRates.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">No tax rates configured.</td></tr>
              ) : (
                taxRates.map((rate: any) => (
                  <tr key={rate.id} className="border-b hover:bg-muted/50">
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

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-base">Tax Transactions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Jurisdiction ID</label>
              <Input value={transactionForm.jurisdictionId} onChange={(e) => setTransactionForm((prev) => ({ ...prev, jurisdictionId: e.target.value }))} placeholder="UUID" />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Tax Rate ID</label>
              <Input value={transactionForm.taxRateId} onChange={(e) => setTransactionForm((prev) => ({ ...prev, taxRateId: e.target.value }))} placeholder="UUID" />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Reference Type</label>
              <Input value={transactionForm.referenceType} onChange={(e) => setTransactionForm((prev) => ({ ...prev, referenceType: e.target.value }))} placeholder="sale" />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Reference ID</label>
              <Input value={transactionForm.referenceId} onChange={(e) => setTransactionForm((prev) => ({ ...prev, referenceId: e.target.value }))} placeholder="SO-1001" />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Taxable Amount</label>
              <Input value={transactionForm.taxableAmount} onChange={(e) => setTransactionForm((prev) => ({ ...prev, taxableAmount: e.target.value }))} placeholder="1000" />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Tax Amount</label>
              <Input value={transactionForm.taxAmount} onChange={(e) => setTransactionForm((prev) => ({ ...prev, taxAmount: e.target.value }))} placeholder="75" />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Currency</label>
              <Input value={transactionForm.currency} onChange={(e) => setTransactionForm((prev) => ({ ...prev, currency: e.target.value.toUpperCase() }))} placeholder="USD" />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Status</label>
              <Input value={transactionForm.status} onChange={(e) => setTransactionForm((prev) => ({ ...prev, status: e.target.value }))} placeholder="pending" />
            </div>
          </div>
          <Button onClick={handleCreateTransaction} disabled={loading} className="w-full">
            Record Transaction
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-base">Transaction Ledger</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">Reference</th>
                <th className="py-3 px-4 text-left font-medium">Taxable</th>
                <th className="py-3 px-4 text-left font-medium">Tax</th>
                <th className="py-3 px-4 text-left font-medium">Currency</th>
                <th className="py-3 px-4 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {taxTransactions.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">No transactions recorded.</td></tr>
              ) : (
                taxTransactions.map((txn: any) => (
                  <tr key={txn.id} className="border-b hover:bg-muted/50">
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
