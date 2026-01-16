'use client';

import * as React from 'react';
import { useFinanceStore } from '@/stores';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Plus, Calculator } from 'lucide-react';

export default function LedgerPage() {
  const { accounts, fetchAccounts, loading } = useFinanceStore();

  React.useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  return (
    <div className="space-y-8 page-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-heading font-bold tracking-tight">Chart of Accounts</h1>
          <p className="text-muted-foreground">Manage your General Ledger accounts and their structures</p>
        </div>
        <Button className="rounded-xl shadow-glow">
          <Plus className="mr-2 h-4 w-4" />
          Add Account
        </Button>
      </div>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Account Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Balance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">Loading accounts...</TableCell>
                </TableRow>
              ) : accounts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">No accounts found</TableCell>
                </TableRow>
              ) : (
                accounts.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell className="font-mono font-bold text-primary">{account.account_code}</TableCell>
                    <TableCell className="font-medium">{account.account_name}</TableCell>
                    <TableCell className="uppercase text-[10px] font-bold tracking-widest">{account.account_type}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-tighter ${account.is_active ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'}`}>
                        {account.is_active ? 'Active' : 'Inactive'}
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
