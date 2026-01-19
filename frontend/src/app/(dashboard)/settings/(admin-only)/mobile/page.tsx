'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useI18n } from '@/contexts/i18n-context';

export default function MobileSettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title={t('settings.mobile.title')} description={t('settings.mobile.description')}>
      <div className="space-y-1 py-6 max-w-2xl">
        <div className="flex items-center justify-between p-5 bg-rams-panel/20 border border-rams-line group hover:bg-rams-panel transition-none">
          <div>
            <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t('settings.mobile.telemetryPush')}</p>
            <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">{t('settings.mobile.telemetryPushDesc')}</p>
          </div>
          <Switch defaultChecked />
        </div>
        <div className="flex items-center justify-between p-5 bg-rams-panel/20 border border-rams-line group hover:bg-rams-panel transition-none">
          <div>
            <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t('settings.mobile.biometricSync')}</p>
            <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">{t('settings.mobile.biometricSyncDesc')}</p>
          </div>
          <Switch defaultChecked />
        </div>
        <div className="flex items-center justify-between p-5 bg-rams-panel/20 border border-rams-line group hover:bg-rams-panel transition-none">
          <div>
            <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t('settings.mobile.offlineIntelligence')}</p>
            <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">{t('settings.mobile.offlineIntelligenceDesc')}</p>
          </div>
          <Switch defaultChecked />
        </div>
      </div>
    </SettingsPageShell>
  );
}
