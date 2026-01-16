'use client';

import * as React from 'react';
import { useSitesStore } from '@/stores';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

export default function SitesSettingsPage() {
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
    <div className="space-y-8 page-fade-in">
      <div>
        <h1 className="text-4xl font-heading font-bold tracking-tight">Sites</h1>
        <p className="text-muted-foreground">Manage manufacturing sites and defaults</p>
      </div>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-base">Add Site</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Site Code</label>
              <Input
                value={form.siteCode}
                onChange={(e) => setForm((prev) => ({ ...prev, siteCode: e.target.value }))}
                placeholder="SITE-NY"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Name</label>
              <Input
                value={form.name}
                onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="New York Plant"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Timezone</label>
              <Input
                value={form.timezone}
                onChange={(e) => setForm((prev) => ({ ...prev, timezone: e.target.value }))}
                placeholder="America/New_York"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Country</label>
              <Input
                value={form.country}
                onChange={(e) => setForm((prev) => ({ ...prev, country: e.target.value }))}
                placeholder="USA"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Default Currency</label>
              <Input
                value={form.defaultCurrency}
                onChange={(e) => setForm((prev) => ({ ...prev, defaultCurrency: e.target.value.toUpperCase() }))}
                placeholder="USD"
              />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs font-semibold text-muted-foreground">Address</label>
              <Input
                value={form.address}
                onChange={(e) => setForm((prev) => ({ ...prev, address: e.target.value }))}
                placeholder="123 Industrial Ave"
              />
            </div>
          </div>
          <Button onClick={handleCreate} disabled={loading} className="w-full">
            Create Site
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-base">Sites Directory</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">Code</th>
                <th className="py-3 px-4 text-left font-medium">Name</th>
                <th className="py-3 px-4 text-left font-medium">Timezone</th>
                <th className="py-3 px-4 text-left font-medium">Currency</th>
                <th className="py-3 px-4 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {sites.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">No sites configured.</td></tr>
              ) : (
                sites.map((site) => (
                  <tr key={site.id} className="border-b hover:bg-muted/50">
                    <td className="py-3 px-4 font-medium">{site.site_code}</td>
                    <td className="py-3 px-4 text-muted-foreground">{site.name}</td>
                    <td className="py-3 px-4 text-muted-foreground">{site.timezone || '—'}</td>
                    <td className="py-3 px-4 text-muted-foreground">{site.default_currency || '—'}</td>
                    <td className="py-3 px-4">
                      <Badge variant={site.status === 'active' ? 'success' : 'secondary'}>{site.status}</Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
