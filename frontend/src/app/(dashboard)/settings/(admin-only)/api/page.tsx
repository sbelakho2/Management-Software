'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Key, Copy, Plus, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { useI18n } from '@/contexts/i18n-context';

export default function ApiSettingsPage() {
  const { t } = useI18n();
  return (
    <SettingsPageShell title={t('settings.api.title')} description={t('settings.api.description')}>
      <div className="space-y-8 py-6">
        <div className="flex items-center justify-between border-b border-rams-line pb-6">
          <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70 flex items-center gap-3">
            <Key className="h-3.5 w-3.5 text-rams-orange" />
            {t('settings.api.activeAuthNodes')}
          </h3>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[9px] h-9 px-4 transition-none">
            <Plus className="h-3.5 w-3.5 mr-2" />
            {t('settings.api.initializeNewKey')}
          </Button>
        </div>
        
        <div className="grid gap-px border border-rams-line bg-rams-line">
          {[
            { nameKey: 'settings.api.keys.erpSync', key: 'sk_live_••••••••••••45a2', created: '2023-11-15' },
            { nameKey: 'settings.api.keys.shopFloorDisplay', key: 'sk_live_••••••••••••99b1', created: '2024-01-02' },
          ].map((item) => (
            <div key={item.nameKey} className="p-6 bg-rams-module flex items-center justify-between transition-none hover:bg-rams-panel group">
              <div className="space-y-3">
                <div className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t(item.nameKey)}</div>
                <div className="flex items-center gap-3 text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest bg-rams-panel px-3 py-1 border border-rams-line">
                  <Key className="h-3 w-3" />
                  {item.key}
                </div>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/30">{t('settings.api.initializedOn')}</p>
                  <p className="text-[10px] font-mono font-bold text-muted-foreground/60">{item.created}</p>
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-none border border-transparent hover:border-rams-line hover:bg-rams-panel transition-none">
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-none border border-transparent hover:border-rams-red/20 hover:bg-rams-red/5 text-muted-foreground/40 hover:text-rams-red transition-none">
                    <Plus className="h-4 w-4 rotate-45" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* API Usage Meter */}
        <section className="pt-10 border-t border-rams-line">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70">{t('settings.api.intelligenceThroughput')}</h3>
            <span className="text-[9px] font-mono font-bold text-rams-green uppercase">{t('settings.api.optimalLoad')}</span>
          </div>
          <Card className="rounded-rams-sm border border-rams-line bg-rams-panel/20 p-8 relative overflow-hidden">
            <div className="relative z-10 space-y-6">
              <div className="flex justify-between items-end">
                <div>
                  <p className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{t('settings.api.requestVolume')}</p>
                  <p className="text-3xl font-mono font-bold text-foreground/90 tabular-nums">12,452</p>
                </div>
                <div className="text-right">
                  <p className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{t('settings.api.errorRate')}</p>
                  <p className="text-lg font-mono font-bold text-rams-green tabular-nums">0.04%</p>
                </div>
              </div>
              <div className="h-1 bg-rams-module border border-rams-line overflow-hidden">
                <div className="h-full bg-rams-orange" style={{ width: '42%' }} />
              </div>
              <p className="text-[8px] font-mono text-muted-foreground/30 uppercase tracking-[0.3em] text-center">{t('settings.api.protocolStream')}</p>
            </div>
            <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
          </Card>
        </section>
      </div>
    </SettingsPageShell>
  );
}
