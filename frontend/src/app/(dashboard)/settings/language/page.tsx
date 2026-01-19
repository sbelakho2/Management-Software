'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useI18n, type Locale } from '@/contexts/i18n-context';
import { Globe, Calendar, Clock, Check, Languages } from 'lucide-react';

export default function LanguageSettingsPage() {
  const { locale, setLocale, availableLocales, t, direction, formatDate, formatNumber } = useI18n();
  
  // Show a preview of current locale formatting
  const now = new Date();
  const sampleNumber = 1234567.89;

  return (
    <SettingsPageShell 
      title={t('settings.localization.title')} 
      description={t('settings.localization.description')}
    >
      <div className="space-y-12 py-6">
        {/* Language Selection */}
        <section className="space-y-4 max-w-md">
          <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1 flex items-center gap-2">
            <Languages className="h-3.5 w-3.5" />
            {t('settings.localization.intelligenceLanguage')}
          </Label>
          <Select value={locale} onValueChange={(value) => setLocale(value as Locale)}>
            <SelectTrigger className="bg-rams-panel border-rams-line h-10 text-[11px] rounded-rams-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {availableLocales.map((loc) => (
                <SelectItem 
                  key={loc.locale} 
                  value={loc.locale} 
                >
                  <span className="flex items-center gap-3">
                    <span className="text-lg">{loc.flag}</span>
                    <span>{loc.nativeName.toUpperCase()}</span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {/* RTL indicator for Arabic */}
          {direction === 'rtl' && (
            <div className="p-4 bg-rams-panel/40 border border-rams-line flex items-center gap-3">
              <Globe className="h-4 w-4 text-rams-orange" />
              <p className="text-[10px] font-black uppercase tracking-widest text-foreground/70">
                {t('common.info')}: {t('settings.localization.rtlActive')}
              </p>
            </div>
          )}
        </section>

        {/* Format Preview */}
        <section className="space-y-6">
          <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">
            {t('settings.localization.temporalFormat')} - {t('settings.localization.preview')}
          </Label>
          <div className="grid gap-px border border-rams-line bg-rams-line sm:grid-cols-2">
            <div className="p-6 bg-rams-module group hover:bg-rams-panel transition-none">
              <div className="flex items-center gap-2 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mb-4">
                <Calendar className="h-3.5 w-3.5" />
                {t('settings.localization.dateFormat')}
              </div>
              <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{formatDate(now, { dateStyle: 'full' })}</p>
              <p className="text-[10px] font-mono text-muted-foreground/40 mt-1">{formatDate(now, { dateStyle: 'short' })}</p>
            </div>
            <div className="p-6 bg-rams-module group hover:bg-rams-panel transition-none">
              <div className="flex items-center gap-2 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mb-4">
                <Clock className="h-3.5 w-3.5" />
                {t('settings.localization.timeFormat')}
              </div>
              <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{formatDate(now, { timeStyle: 'long' })}</p>
              <p className="text-[10px] font-mono text-muted-foreground/40 mt-1">{formatDate(now, { timeStyle: 'short' })}</p>
            </div>
          </div>
        </section>

        {/* Number Format Preview */}
        <section className="space-y-6">
          <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">
            {t('settings.localization.numericPrecisionPreview')}
          </Label>
          <div className="p-6 bg-rams-panel/20 border border-rams-line">
            <div className="grid gap-12 sm:grid-cols-2">
              <div className="space-y-2">
                <p className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{t('settings.localization.standardMetric')}</p>
                <p className="font-mono font-bold text-2xl tabular-nums text-foreground/80">{formatNumber(sampleNumber)}</p>
              </div>
              <div className="space-y-2">
                <p className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{t('settings.localization.efficiencyPercentage')}</p>
                <p className="font-mono font-bold text-2xl tabular-nums text-rams-green">{formatNumber(0.8567, { style: 'percent', maximumFractionDigits: 1 })}</p>
              </div>
            </div>
          </div>
        </section>

        {/* Success message */}
        <div className="p-4 bg-rams-green/5 border border-rams-green/20 group">
          <p className="text-[10px] font-black uppercase tracking-widest text-rams-green flex items-center gap-3">
            <div className="p-1 bg-rams-green text-white rounded-none">
              <Check className="h-3 w-3" />
            </div>
            {t('settings.localization.autoSyncActive')}
          </p>
        </div>
      </div>
    </SettingsPageShell>
  );
}
