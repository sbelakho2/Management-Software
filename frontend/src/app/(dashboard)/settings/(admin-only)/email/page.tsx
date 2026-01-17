'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { useI18n } from '@/contexts/i18n-context';

export default function EmailSettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title="Email Settings" description="Configure SMTP and notification emails">
      <div className="space-y-6 max-w-xl">
        <div className="flex items-center justify-between">
          <Label>Enable System Notifications</Label>
          <Switch defaultChecked />
        </div>
        <div className="space-y-2">
          <Label>Sender Name</Label>
          <Input defaultValue="Sensei System" />
        </div>
        <div className="space-y-2">
          <Label>Reply-To Address</Label>
          <Input defaultValue="no-reply@sensei-manuf.com" />
        </div>
      </div>
    </SettingsPageShell>
  );
}
