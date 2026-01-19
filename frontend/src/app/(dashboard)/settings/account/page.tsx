'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useI18n } from '@/contexts/i18n-context';

export default function AccountSettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title={t('settings.account.title')} description={t('settings.account.description')}>
      <div className="space-y-12 py-6">
        <section className="space-y-4">
          <div className="space-y-2">
            <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.account.primaryEmail')}</Label>
            <Input defaultValue="admin@sensei-manuf.com" className="bg-rams-panel border-rams-line h-10 text-[11px]" />
          </div>
        </section>
        
        <section className="pt-10 border-t border-rams-line space-y-8">
          <div>
            <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70">{t('settings.account.credentialRotation')}</h3>
            <p className="text-[9px] text-muted-foreground/40 uppercase tracking-widest mt-1">{t('settings.account.credentialRotationDesc')}</p>
          </div>
          
          <div className="space-y-6 max-w-md">
            <div className="space-y-2">
              <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.account.currentPassword')}</Label>
              <Input type="password" placeholder="••••••••" className="bg-rams-panel border-rams-line h-10 text-[11px]" />
            </div>
            <div className="space-y-2">
              <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.account.newPassword')}</Label>
              <Input type="password" placeholder="••••••••" className="bg-rams-panel border-rams-line h-10 text-[11px]" />
            </div>
            <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line text-[9px] font-black uppercase tracking-widest h-10 px-6 transition-none">
              {t('settings.account.updateCredentials')}
            </Button>
          </div>
        </section>
      </div>
    </SettingsPageShell>
  );
}
