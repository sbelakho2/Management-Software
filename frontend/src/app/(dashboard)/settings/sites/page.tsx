'use client';

import * as React from 'react';
import { Globe, Loader2 } from 'lucide-react';
import { useSitesStore } from '@/stores';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useI18n } from '@/contexts/i18n-context';

export default function SitesSettingsPage() {
  const { t } = useI18n();
  const { sites, fetchSites, createSite, loading } = useSitesStore();

  const [form, setForm] = React.useState({
    siteCode: '',
    name: '',
    timezone: '',
    country: '',
    address: '',
    defaultCurrency: '',
  });

  React.useEffect(() => {
    fetchSites();
  }, [fetchSites]);

  const handleCreate = async () => {
    if (!form.siteCode || !form.name) {
      return;
    }
    await createSite({
      site_code: form.siteCode,
      name: form.name,
      timezone: form.timezone || undefined,
      country: form.country || undefined,
      address: form.address || undefined,
      default_currency: form.defaultCurrency || undefined,
      status: 'active',
    });
    setForm({ siteCode: '', name: '', timezone: '', country: '', address: '', defaultCurrency: '' });
  };

  return (
    <div className="space-y-12 animate-in fade-in duration-150 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90 flex items-center gap-3">
            <Globe className="h-6 w-6 text-rams-orange" />
            {t('settings.sites.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('settings.sites.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('settings.sites.station')}</span>
          </p>
        </div>
      </div>

      <div className="grid gap-12 lg:grid-cols-3">
        {/* Form Column */}
        <div className="lg:col-span-1">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none sticky top-8">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('settings.sites.initializeSiteNode')}</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.sites.siteCodeIdentifier')}</label>
                <Input
                  value={form.siteCode}
                  onChange={(e) => setForm((prev) => ({ ...prev, siteCode: e.target.value.toUpperCase() }))}
                  placeholder={t('settings.sites.placeholders.siteCode')}
                  className="bg-rams-panel border-rams-line h-10 text-[11px] font-mono"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.sites.nodeCommonName')}</label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder={t('settings.sites.placeholders.nodeCommonName')}
                  className="bg-rams-panel border-rams-line h-10 text-[11px]"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.sites.countrySync')}</label>
                  <Input
                    value={form.country}
                    onChange={(e) => setForm((prev) => ({ ...prev, country: e.target.value.toUpperCase() }))}
                    placeholder={t('settings.sites.placeholders.countrySync')}
                    className="bg-rams-panel border-rams-line h-10 text-[11px]"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.sites.currencyNode')}</label>
                  <Input
                    value={form.defaultCurrency}
                    onChange={(e) => setForm((prev) => ({ ...prev, defaultCurrency: e.target.value.toUpperCase() }))}
                    placeholder={t('settings.sites.placeholders.currencyNode')}
                    className="bg-rams-panel border-rams-line h-10 text-[11px] font-mono"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.sites.temporalAlignment')}</label>
                <Input
                  value={form.timezone}
                  onChange={(e) => setForm((prev) => ({ ...prev, timezone: e.target.value }))}
                  placeholder={t('settings.sites.placeholders.temporalAlignment')}
                  className="bg-rams-panel border-rams-line h-10 text-[11px] font-mono"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.sites.physicalAddressNode')}</label>
                <Input
                  value={form.address}
                  onChange={(e) => setForm((prev) => ({ ...prev, address: e.target.value }))}
                  placeholder={t('settings.sites.placeholders.physicalAddressNode')}
                  className="bg-rams-panel border-rams-line h-10 text-[11px]"
                />
              </div>
              <Button onClick={handleCreate} disabled={loading} className="w-full rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest h-12 transition-none mt-4">
                {loading ? t('settings.sites.synchronizing') : t('settings.sites.initializeProtocol')}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Directory Column */}
        <div className="lg:col-span-2">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('settings.sites.activeSitesDirectory')}</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full border-separate border-spacing-0">
                  <thead>
                    <tr className="bg-rams-panel/50">
                      <th className="px-6 py-4 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('settings.sites.table.code')}</th>
                      <th className="px-6 py-4 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('settings.sites.table.siteIdentity')}</th>
                      <th className="px-6 py-4 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('settings.sites.table.temporalSync')}</th>
                      <th className="px-6 py-4 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('settings.sites.table.currency')}</th>
                      <th className="px-6 py-4 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('settings.sites.table.statusNode')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rams-line/30">
                    {sites.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-6 py-24 text-center">
                          <Globe className="h-12 w-12 text-muted-foreground/20 mx-auto mb-4" />
                          <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">{t('settings.sites.zeroSitesIdentified')}</p>
                          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">{t('settings.sites.initializeFirstNode')}</p>
                        </td>
                      </tr>
                    ) : (
                      sites.map((site) => (
                        <tr key={site.id} className="hover:bg-rams-panel/50 transition-none group cursor-help">
                          <td className="px-6 py-5">
                            <span className="font-mono font-bold text-rams-orange tabular-nums">{site.site_code}</span>
                          </td>
                          <td className="px-6 py-5">
                            <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{site.name}</p>
                            <p className="text-[9px] font-mono text-muted-foreground/40 mt-1 uppercase truncate max-w-[200px]">{site.address || t('settings.sites.addressUnavailable')}</p>
                          </td>
                          <td className="px-6 py-5">
                            <span className="font-mono text-[10px] font-bold text-muted-foreground/60 uppercase">{site.timezone || t('settings.sites.valueUnavailable')}</span>
                          </td>
                          <td className="px-6 py-5">
                            <span className="font-mono text-[10px] font-bold text-muted-foreground/60">{site.default_currency || t('settings.sites.valueUnavailable')}</span>
                          </td>
                          <td className="px-6 py-5">
                            <Badge 
                              variant={site.status === 'active' ? 'success' : 'secondary'}
                              className="rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4"
                            >
                              {t(`settings.sites.status.${site.status}`)}
                            </Badge>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
