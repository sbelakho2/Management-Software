'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { useI18n } from '@/contexts/i18n-context';

export default function IntegrationsSettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title="Integrations" description="Connect Sensei with your existing manufacturing tools">
      <div className="grid gap-4 md:grid-cols-2">
        {[
          { name: 'SAP ERP', status: 'Connected', desc: 'Sync production orders and inventory' },
          { name: 'Microsoft Teams', status: 'Connected', desc: 'Send andon alerts to channels' },
          { name: 'PowerBI', status: 'Not Connected', desc: 'Export operational data for analysis' },
          { name: 'Slack', status: 'Not Connected', desc: 'Real-time notifications and chat' },
        ].map((item) => (
          <div key={item.name} className="p-4 border rounded-lg flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-bold">{item.name}</span>
                <Badge variant={item.status === 'Connected' ? 'success' : 'secondary' as any} className="text-[10px]">
                  {item.status}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">{item.desc}</p>
            </div>
            <Switch checked={item.status === 'Connected'} />
          </div>
        ))}
      </div>
    </SettingsPageShell>
  );
}
