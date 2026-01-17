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
      <div className="space-y-8 max-w-xl">
        {/* Language Selection */}
        <div className="space-y-3">
          <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1 flex items-center gap-2">
            <Languages className="h-3.5 w-3.5" />
            {t('settings.localization.intelligenceLanguage')}
          </Label>
          <Select value={locale} onValueChange={(value) => setLocale(value as Locale)}>
            <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-2xl shadow-premium">
              {availableLocales.map((loc) => (
                <SelectItem 
                  key={loc.locale} 
                  value={loc.locale} 
                  className="rounded-xl m-1"
                >
                  <span className="flex items-center gap-3">
                    <span className="text-lg">{loc.flag}</span>
                    <span>{loc.nativeName}</span>
                    {loc.locale === locale && (
                      <Check className="h-4 w-4 text-primary ml-auto" />
                    )}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {/* RTL indicator for Arabic */}
          {direction === 'rtl' && (
            <p className="text-xs text-muted-foreground mt-2 flex items-center gap-2 bg-primary/5 p-3 rounded-xl">
              <Globe className="h-4 w-4 text-primary" />
              <span>{t('common.info')}: Right-to-left (RTL) layout active</span>
            </p>
          )}
        </div>

        {/* Format Preview */}
        <div className="space-y-3">
          <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">
            {t('settings.localization.temporalFormat')} - Preview
          </Label>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="p-4 rounded-2xl bg-background/50 border border-border/50">
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                <Calendar className="h-3.5 w-3.5" />
                {t('settings.localization.dateFormat')}
              </div>
              <p className="font-medium">{formatDate(now, { dateStyle: 'full' })}</p>
              <p className="text-sm text-muted-foreground mt-1">{formatDate(now, { dateStyle: 'short' })}</p>
            </div>
            <div className="p-4 rounded-2xl bg-background/50 border border-border/50">
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                <Clock className="h-3.5 w-3.5" />
                {t('settings.localization.timeFormat')}
              </div>
              <p className="font-medium">{formatDate(now, { timeStyle: 'long' })}</p>
              <p className="text-sm text-muted-foreground mt-1">{formatDate(now, { timeStyle: 'short' })}</p>
            </div>
          </div>
        </div>

        {/* Number Format Preview */}
        <div className="space-y-3">
          <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">
            Number Format Preview
          </Label>
          <div className="p-4 rounded-2xl bg-background/50 border border-border/50">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Standard Number</p>
                <p className="font-medium text-lg">{formatNumber(sampleNumber)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Percentage</p>
                <p className="font-medium text-lg">{formatNumber(0.8567, { style: 'percent', maximumFractionDigits: 1 })}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Success message */}
        <div className="p-4 rounded-2xl bg-success/5 border border-success/20 text-success">
          <p className="text-sm flex items-center gap-2">
            <Check className="h-4 w-4" />
            {t('common.success')}: Changes are saved automatically
          </p>
        </div>
      </div>
    </SettingsPageShell>
  );
}
