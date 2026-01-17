'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { useI18n } from '@/contexts/i18n-context';

export default function CompanySettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title="Company Settings" description="Manage your organization details and branding">
      <div className="space-y-4 max-w-2xl">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>Legal Company Name</Label>
            <Input defaultValue="Sensei Manufacturing Solutions" />
          </div>
          <div className="space-y-2">
            <Label>Tax ID / VAT Number</Label>
            <Input defaultValue="MA-123456789" />
          </div>
          <div className="sm:col-span-2 space-y-2">
            <Label>Registered Office Address</Label>
            <Input defaultValue="123 Industrial Ave, Casablanca, Morocco" />
          </div>
        </div>
      </div>
    </SettingsPageShell>
  );
}
