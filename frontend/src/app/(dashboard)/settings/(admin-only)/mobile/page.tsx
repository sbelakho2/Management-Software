'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useI18n } from '@/contexts/i18n-context';

export default function MobileSettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title="Mobile App" description="Manage mobile app access and push notifications">
      <div className="space-y-6 max-w-md">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label>Push Notifications</Label>
            <p className="text-xs text-muted-foreground">Receive alerts on your mobile device</p>
          </div>
          <Switch defaultChecked />
        </div>
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label>Biometric Auth</Label>
            <p className="text-xs text-muted-foreground">Use FaceID or Fingerprint to unlock</p>
          </div>
          <Switch defaultChecked />
        </div>
      </div>
    </SettingsPageShell>
  );
}
