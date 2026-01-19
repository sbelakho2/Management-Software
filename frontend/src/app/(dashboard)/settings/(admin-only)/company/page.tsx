'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useI18n } from '@/contexts/i18n-context';

export default function CompanySettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title={t('settings.company.title')} description={t('settings.company.description')}>
      <div className="space-y-12 py-6">
        <section className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.company.legalEntityIdentity')}</Label>
              <Input defaultValue={t('settings.company.defaults.legalEntityIdentity')} className="bg-rams-panel border-rams-line h-10 text-[11px]" />
            </div>
            <div className="space-y-2">
              <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.company.taxIdVat')}</Label>
              <Input defaultValue={t('settings.company.defaults.taxIdVat')} className="bg-rams-panel border-rams-line h-10 text-[11px] font-mono" />
            </div>
            <div className="md:col-span-2 space-y-2">
              <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.company.registeredOffice')}</Label>
              <Input defaultValue={t('settings.company.defaults.registeredOffice')} className="bg-rams-panel border-rams-line h-10 text-[11px]" />
            </div>
          </div>
        </section>

        <section className="pt-10 border-t border-rams-line">
          <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70 mb-6">{t('settings.company.brandingSync')}</h3>
          <div className="grid gap-8 md:grid-cols-2">
            <div className="space-y-4 p-6 bg-rams-panel/20 border border-rams-line group">
              <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">{t('settings.company.branding.primaryLogoNode')}</p>
              <div className="h-24 w-24 bg-rams-module border border-rams-line flex items-center justify-center group-hover:border-rams-orange transition-none">
                <span className="font-mono font-black text-2xl text-muted-foreground/20">{t('settings.company.branding.logoPlaceholder')}</span>
              </div>
              <Button variant="outline" size="sm" className="rounded-none text-[9px] font-black uppercase tracking-widest border-rams-line h-8 transition-none">{t('settings.company.branding.updateStream')}</Button>
            </div>
            <div className="space-y-4 p-6 bg-rams-panel/20 border border-rams-line group">
              <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">{t('settings.company.branding.interfaceAccentSync')}</p>
              <div className="flex gap-2">
                <div className="h-8 w-8 bg-rams-orange border border-black/10" />
                <div className="h-8 w-8 bg-rams-green border border-black/10 opacity-20" />
                <div className="h-8 w-8 bg-rams-steel border border-black/10 opacity-20" />
              </div>
              <p className="text-[10px] font-bold text-foreground/60 uppercase">{t('settings.company.branding.activeAccent')}</p>
            </div>
          </div>
        </section>
      </div>
    </SettingsPageShell>
  );
}
