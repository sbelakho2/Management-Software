'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export default function LanguageSettingsPage() {
  return (
    <SettingsPageShell title="Localization Protocol" description="Calibrate organizational language and regional data structures">
      <div className="space-y-8 max-w-md">
        <div className="space-y-3">
          <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Intelligence Language</Label>
          <Select defaultValue="en">
            <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-2xl shadow-premium">
              <SelectItem value="en" className="rounded-xl m-1">English (Strategic)</SelectItem>
              <SelectItem value="fr" className="rounded-xl m-1">Français</SelectItem>
              <SelectItem value="ar" className="rounded-xl m-1">العربية</SelectItem>
              <SelectItem value="es" className="rounded-xl m-1">Español</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-3">
          <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Temporal Format</Label>
          <Select defaultValue="mdy">
            <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-2xl shadow-premium">
              <SelectItem value="mdy" className="rounded-xl m-1">MM/DD/YYYY</SelectItem>
              <SelectItem value="dmy" className="rounded-xl m-1">DD/MM/YYYY</SelectItem>
              <SelectItem value="ymd" className="rounded-xl m-1">YYYY-MM-DD (ISO Protocol)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </SettingsPageShell>
  );
}
