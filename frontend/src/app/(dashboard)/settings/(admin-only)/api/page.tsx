'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Key, Copy, Plus } from 'lucide-react';
import { useI18n } from '@/contexts/i18n-context';

export default function ApiSettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title="API Key Management" description="Manage access keys for external integrations">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium">Active Keys</h3>
          <Button size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Generate New Key
          </Button>
        </div>
        <div className="border rounded-lg divide-y">
          {[
            { name: 'ERP Sync', key: 'sk_live_••••••••••••45a2', created: '2023-11-15' },
            { name: 'Shop Floor Display', key: 'sk_live_••••••••••••99b1', created: '2024-01-02' },
          ].map((item) => (
            <div key={item.name} className="p-4 flex items-center justify-between">
              <div className="space-y-1">
                <div className="font-medium">{item.name}</div>
                <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
                  <Key className="h-3 w-3" />
                  {item.key}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="icon">
                  <Copy className="h-4 w-4" />
                </Button>
                <div className="text-xs text-muted-foreground italic">Created {item.created}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </SettingsPageShell>
  );
}
