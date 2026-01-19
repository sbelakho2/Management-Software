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
    <SettingsPageShell title={t('settings.email.title')} description={t('settings.email.description')}>
      <div className="space-y-12 py-6">
        <section className="space-y-1">
          <div className="flex items-center justify-between p-5 bg-rams-panel/20 border border-rams-line group hover:bg-rams-panel transition-none">
            <div>
              <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t('settings.email.intelligenceBroadcast')}</p>
              <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">{t('settings.email.intelligenceBroadcastDesc')}</p>
            </div>
            <Switch defaultChecked />
          </div>
        </section>

        <section className="space-y-6 max-w-md">
          <div className="space-y-2">
            <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.email.dispatchIdentity')}</Label>
            <Input defaultValue={t('settings.email.defaults.dispatchIdentity')} className="bg-rams-panel border-rams-line h-10 text-[11px] font-mono" />
          </div>
          <div className="space-y-2">
            <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.email.relayReplyTo')}</Label>
            <Input defaultValue={t('settings.email.defaults.relayReplyTo')} className="bg-rams-panel border-rams-line h-10 text-[11px] font-mono" />
          </div>
        </section>

        <section className="pt-10 border-t border-rams-line">
          <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70 mb-6">{t('settings.email.serverSync')}</h3>
          <div className="p-6 bg-rams-panel/20 border border-rams-line text-center">
            <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">{t('settings.email.smtpStatus')}</p>
            <p className="text-[8px] font-mono text-muted-foreground/30 uppercase mt-2">{t('settings.email.smtpDetails')}</p>
          </div>
        </section>
      </div>
    </SettingsPageShell>
  );
}
