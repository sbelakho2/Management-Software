'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Button } from '@/components/ui/button';
import { Database, Download, Trash2 } from 'lucide-react';

export default function DataSettingsPage() {
  return (
    <SettingsPageShell title="Data Architecture" description="Manage high-level data protocols and organizational exports">
      <div className="space-y-6">
        <div className="flex items-center justify-between p-6 rounded-2xl bg-primary/5 border border-primary/10 group transition-all hover:bg-primary/10">
          <div className="space-y-1">
            <div className="font-heading font-bold flex items-center gap-2 text-primary">
              <Download className="h-4 w-4" />
              Full Intelligence Export
            </div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Download all organizational nodes in JSON/CSV format</p>
          </div>
          <Button variant="outline" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">Establish Export</Button>
        </div>
        <div className="flex items-center justify-between p-6 rounded-2xl border border-danger/20 bg-danger/[0.02] group transition-all hover:bg-danger/[0.05]">
          <div className="space-y-1">
            <div className="font-heading font-bold flex items-center gap-2 text-danger">
              <Trash2 className="h-4 w-4" />
              Pruning Protocol
            </div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">De-authorize records older than 5 years (compliance threshold)</p>
          </div>
          <Button variant="destructive" className="rounded-xl shadow-sm">Execute Purge</Button>
        </div>
      </div>
    </SettingsPageShell>
  );
}
