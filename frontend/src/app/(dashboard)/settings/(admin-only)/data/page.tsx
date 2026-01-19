'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Button } from '@/components/ui/button';
import { Database, Download, Trash2 } from 'lucide-react';
import { useI18n } from '@/contexts/i18n-context';

export default function DataSettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title={t('settings.data.title')} description={t('settings.data.description')}>
      <div className="space-y-1 py-6">
        <div className="flex items-center justify-between p-6 bg-rams-panel/20 border border-rams-line transition-none hover:bg-rams-panel group">
          <div className="space-y-2">
            <div className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none flex items-center gap-3">
              <Download className="h-4 w-4" />
              {t('settings.data.fullExport')}
            </div>
            <p className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-widest leading-relaxed">{t('settings.data.fullExportDesc')}</p>
          </div>
          <Button variant="outline" className="rounded-rams-sm border-rams-line text-[9px] font-black uppercase tracking-widest h-10 px-6 transition-none">{t('settings.data.establishExport')}</Button>
        </div>
        <div className="flex items-center justify-between p-6 border border-rams-red/20 bg-rams-red/5 transition-none group hover:bg-rams-red/10">
          <div className="space-y-2">
            <div className="font-sans font-black text-xs uppercase tracking-tight text-rams-red flex items-center gap-3">
              <Trash2 className="h-4 w-4" />
              {t('settings.data.pruningProtocol')}
            </div>
            <p className="text-[10px] font-medium text-rams-red/60 uppercase tracking-widest leading-relaxed">{t('settings.data.pruningProtocolDesc')}</p>
          </div>
          <Button variant="destructive" className="rounded-rams-sm bg-rams-red text-white font-black uppercase tracking-widest text-[9px] h-10 px-6 transition-none">{t('settings.data.executePurge')}</Button>
        </div>
      </div>
    </SettingsPageShell>
  );
}
