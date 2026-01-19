'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { useI18n } from '@/contexts/i18n-context';

export default function IntegrationsSettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title={t('settings.integrations.title')} description={t('settings.integrations.description')}>
      <div className="grid gap-px border border-rams-line bg-rams-line md:grid-cols-2 py-6">
        {[
          { nameKey: 'settings.integrations.items.sap.name', status: 'connected', descKey: 'settings.integrations.items.sap.desc' },
          { nameKey: 'settings.integrations.items.teams.name', status: 'connected', descKey: 'settings.integrations.items.teams.desc' },
          { nameKey: 'settings.integrations.items.powerbi.name', status: 'disconnected', descKey: 'settings.integrations.items.powerbi.desc' },
          { nameKey: 'settings.integrations.items.slack.name', status: 'disconnected', descKey: 'settings.integrations.items.slack.desc' },
        ].map((item) => (
          <div key={item.nameKey} className="p-6 bg-rams-module flex items-center justify-between transition-none hover:bg-rams-panel group cursor-help">
            <div className="space-y-3 min-w-0 mr-4">
              <div className="flex items-center gap-3">
                <span className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none truncate">{t(item.nameKey)}</span>
                <Badge 
                  variant={item.status === 'connected' ? 'success' : 'secondary'} 
                  className="rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4"
                >
                  {t(`settings.integrations.status.${item.status}`)}
                </Badge>
              </div>
              <p className="text-[10px] text-muted-foreground/60 leading-relaxed font-medium uppercase">{t(item.descKey)}</p>
            </div>
            <Switch checked={item.status === 'connected'} />
          </div>
        ))}
      </div>
    </SettingsPageShell>
  );
}
