'use client';

import * as React from 'react';
import { useFinanceStore } from '@/stores';
import { useI18n } from '@/contexts/i18n-context';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Plus, Calculator } from 'lucide-react';

export default function LedgerPage() {
  const { t } = useI18n();
  const { accounts, fetchAccounts, loading } = useFinanceStore();

  React.useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  return (
    <div className="space-y-8 page-fade-in">
      <div className="flex items-center justify-between border-b border-rams-line pb-6">
        <div>
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('pages.finance.ledger.title') || 'Chart of Accounts'}</h1>
          <p className="text-2xs font-mono uppercase tracking-widest text-rams-muted">{t('pages.finance.ledger.subtitle') || 'Manage your General Ledger accounts and their structures'}</p>
        </div>
        <Button className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]">
          <Plus className="mr-2 h-4 w-4" />
          {t('pages.finance.ledger.addAccount') || 'Add Account'}
        </Button>
      </div>

      <Card className="rounded-rams-sm border-rams-line bg-rams-module">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('pages.finance.ledger.code') || 'Code'}</TableHead>
                <TableHead>{t('pages.finance.ledger.accountName') || 'Account Name'}</TableHead>
                <TableHead>{t('pages.finance.ledger.type') || 'Type'}</TableHead>
                <TableHead>{t('common.status') || 'Status'}</TableHead>
                <TableHead className="text-right">{t('pages.finance.ledger.balance') || 'Balance'}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">{t('pages.finance.ledger.loadingAccounts') || 'Loading accounts...'}</TableCell>
                </TableRow>
              ) : accounts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">{t('pages.finance.ledger.noAccountsFound') || 'No accounts found'}</TableCell>
                </TableRow>
              ) : (
                accounts.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell className="font-mono font-bold text-primary">{account.account_code}</TableCell>
                    <TableCell className="font-medium">{account.account_name}</TableCell>
                    <TableCell className="uppercase text-[10px] font-bold tracking-widest">{account.account_type}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-rams-sm text-[10px] font-bold uppercase tracking-tighter ${account.is_active ? 'bg-rams-panel text-rams-green border border-rams-green' : 'bg-rams-panel text-rams-muted'}`}>
                        {account.is_active ? (t('common.active') || 'Active') : (t('common.inactive') || 'Inactive')}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-heading font-bold">$0.00</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
