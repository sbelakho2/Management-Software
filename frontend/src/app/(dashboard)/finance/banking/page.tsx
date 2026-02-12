'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';
import { useFinanceStore } from '@/stores';
import { 
  Building2,
  CreditCard,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  RefreshCw,
  Loader2,
  CheckCircle2,
  Clock,
  Search,
  DollarSign,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import { FINANCE_ROLES } from '@/lib/page-access';
import { PageGuard } from '@/components/layout/page-guard';
import type { BankAccount, BankTransaction, BankTransactionType, BankTransactionStatus } from '@/types';

const transactionTypeIcons: Record<BankTransactionType, React.ReactNode> = {
  deposit: <ArrowDownRight className="h-4 w-4 text-emerald-500" />,
  withdrawal: <ArrowUpRight className="h-4 w-4 text-red-500" />,
  transfer: <ArrowUpRight className="h-4 w-4 text-blue-500" />,
  fee: <ArrowUpRight className="h-4 w-4 text-amber-500" />,
  interest: <ArrowDownRight className="h-4 w-4 text-emerald-500" />,
};

const statusColors: Record<BankTransactionStatus, string> = {
  pending: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
  posted: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  reconciled: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
  voided: 'bg-red-500/10 text-red-500 border-red-500/20',
};

export default function BankingPage() {
  const { t } = useI18n();
  const {
    bankAccounts,
    bankTransactions,
    loading,
    error,
    fetchBankAccounts,
    createBankAccount,
    fetchBankTransactions,
    createBankTransaction,
    reconcileBankTransaction,
  } = useFinanceStore();

  const [selectedAccountId, setSelectedAccountId] = React.useState<string | null>(null);
  const [searchTerm, setSearchTerm] = React.useState('');
  const [showAddAccountDialog, setShowAddAccountDialog] = React.useState(false);
  const [showAddTransactionDialog, setShowAddTransactionDialog] = React.useState(false);

  const [newAccount, setNewAccount] = React.useState({
    account_name: '',
    account_number: '',
    bank_name: '',
    bank_code: '',
    iban: '',
    currency: 'TND',
    account_type: 'checking' as const,
  });

  const [newTransaction, setNewTransaction] = React.useState({
    transaction_date: new Date().toISOString().split('T')[0],
    transaction_type: 'deposit' as BankTransactionType,
    description: '',
    amount: '',
    reference: '',
  });

  React.useEffect(() => {
    fetchBankAccounts();
  }, [fetchBankAccounts]);

  React.useEffect(() => {
    if (selectedAccountId) {
      fetchBankTransactions(selectedAccountId);
    }
  }, [selectedAccountId, fetchBankTransactions]);

  const filteredTransactions = React.useMemo(() => {
    return bankTransactions.filter((tx) => {
      const matchesSearch = searchTerm === '' || 
        tx.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        tx.reference?.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesSearch;
    });
  }, [bankTransactions, searchTerm]);

  const handleCreateAccount = async () => {
    await createBankAccount(newAccount);
    setShowAddAccountDialog(false);
    setNewAccount({
      account_name: '',
      account_number: '',
      bank_name: '',
      bank_code: '',
      iban: '',
      currency: 'TND',
      account_type: 'checking',
    });
  };

  const handleCreateTransaction = async () => {
    if (!selectedAccountId) return;
    await createBankTransaction({
      bank_account_id: selectedAccountId,
      ...newTransaction,
      amount: parseFloat(newTransaction.amount),
    });
    setShowAddTransactionDialog(false);
    setNewTransaction({
      transaction_date: new Date().toISOString().split('T')[0],
      transaction_type: 'deposit',
      description: '',
      amount: '',
      reference: '',
    });
  };

  const totalBalance = bankAccounts.reduce((sum, acc) => sum + (acc.current_balance || 0), 0);

  return (
    <PageGuard requiredRoles={FINANCE_ROLES}>
      <div className="space-y-8 page-fade-in pb-12">
        {/* Header */}
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              {t('pages.finance.banking.title')}
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">
              {t('pages.finance.banking.subtitle')}
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" size="sm" onClick={() => fetchBankAccounts()} disabled={loading}>
              <RefreshCw className={cn('h-4 w-4 mr-2', loading && 'animate-spin')} />
              {t('common.refresh')}
            </Button>
            <Dialog open={showAddAccountDialog} onOpenChange={setShowAddAccountDialog}>
              <DialogTrigger asChild>
                <Button size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  {t('pages.finance.banking.addAccount')}
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{t('pages.finance.banking.addBankAccount')}</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label>{t('pages.finance.banking.accountName')}</Label>
                    <Input
                      value={newAccount.account_name}
                      onChange={(e) => setNewAccount((prev) => ({ ...prev, account_name: e.target.value }))}
                      placeholder={t('pages.finance.banking.accountNamePlaceholder')}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="grid gap-2">
                      <Label>{t('pages.finance.banking.accountNumber')}</Label>
                      <Input
                        value={newAccount.account_number}
                        onChange={(e) => setNewAccount((prev) => ({ ...prev, account_number: e.target.value }))}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label>{t('pages.finance.banking.iban')}</Label>
                      <Input
                        value={newAccount.iban}
                        onChange={(e) => setNewAccount((prev) => ({ ...prev, iban: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="grid gap-2">
                      <Label>{t('pages.finance.banking.bankName')}</Label>
                      <Input
                        value={newAccount.bank_name}
                        onChange={(e) => setNewAccount((prev) => ({ ...prev, bank_name: e.target.value }))}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label>{t('pages.finance.banking.bankCode')}</Label>
                      <Input
                        value={newAccount.bank_code}
                        onChange={(e) => setNewAccount((prev) => ({ ...prev, bank_code: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="grid gap-2">
                      <Label>{t('pages.finance.banking.currency')}</Label>
                      <select
                        className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={newAccount.currency}
                        onChange={(e) => setNewAccount((prev) => ({ ...prev, currency: e.target.value }))}
                      >
                        <option value="TND">{t('pages.finance.banking.currencyTND')}</option>
                        <option value="USD">{t('pages.finance.banking.currencyUSD')}</option>
                        <option value="EUR">{t('pages.finance.banking.currencyEUR')}</option>
                        <option value="EGP">{t('pages.finance.banking.currencyEGP')}</option>
                      </select>
                    </div>
                    <div className="grid gap-2">
                      <Label>{t('pages.finance.banking.accountType')}</Label>
                      <select
                        className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={newAccount.account_type}
                        onChange={(e) => setNewAccount((prev) => ({ ...prev, account_type: e.target.value as any }))}
                      >
                        <option value="checking">{t('pages.finance.banking.checking')}</option>
                        <option value="savings">{t('pages.finance.banking.savings')}</option>
                        <option value="cash">{t('pages.finance.banking.cash')}</option>
                      </select>
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowAddAccountDialog(false)}>{t('common.cancel')}</Button>
                  <Button onClick={handleCreateAccount} disabled={loading}>
                    {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                    {t('pages.finance.banking.createAccount')}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Total Balance Card */}
        <Card className="rounded-rams-sm border-rams-line bg-gradient-to-r from-rams-module to-rams-module/50">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-mono uppercase tracking-widest text-rams-muted mb-1">
                  {t('pages.finance.banking.totalBalance')}
                </p>
                <p className="text-3xl font-bold">
                  {totalBalance.toLocaleString('en-US', { minimumFractionDigits: 2 })} TND
                </p>
              </div>
              <div className="p-4 rounded-full bg-emerald-500/10">
                <DollarSign className="h-8 w-8 text-emerald-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Accounts and Transactions */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Accounts List */}
          <div className="lg:col-span-1 space-y-4">
            <h2 className="text-sm font-mono uppercase tracking-widest text-rams-muted">
              {t('pages.finance.banking.bankAccounts')} ({bankAccounts.length})
            </h2>
            {loading && bankAccounts.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : bankAccounts.length === 0 ? (
              <Card className="rounded-rams-sm border-rams-line bg-rams-module">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Building2 className="h-12 w-12 text-muted-foreground/50 mb-4" />
                  <p className="text-muted-foreground">{t('pages.finance.banking.noBankAccounts')}</p>
                  <Button size="sm" className="mt-4" onClick={() => setShowAddAccountDialog(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    {t('pages.finance.banking.addFirstAccount')}
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {bankAccounts.map((account) => (
                  <Card
                    key={account.id}
                    className={cn(
                      'rounded-rams-sm border-rams-line bg-rams-module cursor-pointer transition-all',
                      selectedAccountId === account.id 
                        ? 'border-rams-accent ring-1 ring-rams-accent' 
                        : 'hover:border-rams-accent/50'
                    )}
                    onClick={() => setSelectedAccountId(account.id)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-semibold text-sm">{account.account_name}</p>
                          <p className="text-xs text-muted-foreground">{account.bank_name}</p>
                          <p className="text-xs text-muted-foreground font-mono">
                            •••• {account.account_number.slice(-4)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold">
                            {account.current_balance?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                          </p>
                          <p className="text-xs text-muted-foreground">{account.currency}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Transactions List */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-mono uppercase tracking-widest text-rams-muted">
                {t('pages.finance.banking.transactions')}
              </h2>
              {selectedAccountId && (
                <Dialog open={showAddTransactionDialog} onOpenChange={setShowAddTransactionDialog}>
                  <DialogTrigger asChild>
                    <Button size="sm" variant="outline">
                      <Plus className="h-4 w-4 mr-2" />
                      {t('pages.finance.banking.addTransaction')}
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>{t('pages.finance.banking.addTransaction')}</DialogTitle>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                          <Label>{t('pages.finance.banking.date')}</Label>
                          <Input
                            type="date"
                            value={newTransaction.transaction_date}
                            onChange={(e) => setNewTransaction((prev) => ({ ...prev, transaction_date: e.target.value }))}
                          />
                        </div>
                        <div className="grid gap-2">
                          <Label>{t('pages.finance.banking.type')}</Label>
                          <select
                            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                            value={newTransaction.transaction_type}
                            onChange={(e) => setNewTransaction((prev) => ({ ...prev, transaction_type: e.target.value as BankTransactionType }))}
                          >
                            <option value="deposit">{t('pages.finance.banking.deposit')}</option>
                            <option value="withdrawal">{t('pages.finance.banking.withdrawal')}</option>
                            <option value="transfer">{t('pages.finance.banking.transfer')}</option>
                            <option value="fee">{t('pages.finance.banking.fee')}</option>
                            <option value="interest">{t('pages.finance.banking.interest')}</option>
                          </select>
                        </div>
                      </div>
                      <div className="grid gap-2">
                        <Label>{t('pages.finance.banking.description')}</Label>
                        <Input
                          value={newTransaction.description}
                          onChange={(e) => setNewTransaction((prev) => ({ ...prev, description: e.target.value }))}
                          placeholder={t('pages.finance.banking.descriptionPlaceholder')}
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                          <Label>{t('pages.finance.banking.amount')}</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={newTransaction.amount}
                            onChange={(e) => setNewTransaction((prev) => ({ ...prev, amount: e.target.value }))}
                            placeholder="0.00"
                          />
                        </div>
                        <div className="grid gap-2">
                          <Label>{t('pages.finance.banking.reference')}</Label>
                          <Input
                            value={newTransaction.reference}
                            onChange={(e) => setNewTransaction((prev) => ({ ...prev, reference: e.target.value }))}
                            placeholder={t('pages.finance.banking.referencePlaceholder')}
                          />
                        </div>
                      </div>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setShowAddTransactionDialog(false)}>{t('common.cancel')}</Button>
                      <Button onClick={handleCreateTransaction} disabled={loading}>
                        {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                        {t('pages.finance.banking.addTransaction')}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              )}
            </div>

            {!selectedAccountId ? (
              <Card className="rounded-rams-sm border-rams-line bg-rams-module">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <CreditCard className="h-12 w-12 text-muted-foreground/50 mb-4" />
                  <p className="text-muted-foreground">{t('pages.finance.banking.selectAccount')}</p>
                </CardContent>
              </Card>
            ) : (
              <>
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder={t('pages.finance.banking.searchTransactions')}
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>

                {/* Transaction List */}
                {loading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : filteredTransactions.length === 0 ? (
                  <Card className="rounded-rams-sm border-rams-line bg-rams-module">
                    <CardContent className="flex flex-col items-center justify-center py-12">
                      <CreditCard className="h-12 w-12 text-muted-foreground/50 mb-4" />
                      <p className="text-muted-foreground">{t('pages.finance.banking.noTransactions')}</p>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="space-y-2">
                    {filteredTransactions.map((tx) => (
                      <Card key={tx.id} className="rounded-rams-sm border-rams-line bg-rams-module">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="p-2 rounded-full bg-muted">
                                {transactionTypeIcons[(tx.transaction_type ?? tx.type) as BankTransactionType]}
                              </div>
                              <div>
                                <p className="font-medium text-sm">{tx.description}</p>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                  <span>{new Date(tx.transaction_date ?? tx.date).toLocaleDateString()}</span>
                                  {tx.reference && <span>• {tx.reference}</span>}
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-4">
                              <div className="text-right">
                                <p className={cn(
                                  'font-semibold',
                                  (tx.transaction_type ?? tx.type) === 'deposit' || (tx.transaction_type ?? tx.type) === 'interest'
                                    ? 'text-emerald-500'
                                    : 'text-red-500'
                                )}>
                                  {(tx.transaction_type ?? tx.type) === 'deposit' || (tx.transaction_type ?? tx.type) === 'interest' ? '+' : '-'}
                                  {Math.abs(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                                </p>
                                <p className="text-xs text-muted-foreground">{tx.currency}</p>
                              </div>
                              <Badge className={cn('text-xs', statusColors[(tx.status ?? 'pending') as BankTransactionStatus])}>
                                {tx.status === 'reconciled' && <CheckCircle2 className="h-3 w-3 mr-1" />}
                                {tx.status === 'pending' && <Clock className="h-3 w-3 mr-1" />}
                                {(tx.status ?? 'pending').toUpperCase()}
                              </Badge>
                              {tx.status === 'posted' && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => reconcileBankTransaction(tx.id)}
                                >
                                  {t('pages.finance.banking.reconcile')}
                                </Button>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </PageGuard>
  );
}
