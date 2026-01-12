'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Button } from '@/components/ui/button';
import { Database, Download, Trash2 } from 'lucide-react';

export default function DataSettingsPage() {
  return (
    <SettingsPageShell title="Data Management" description="Export or manage your organization's data">
      <div className="space-y-6">
        <div className="flex items-center justify-between p-4 border rounded-lg">
          <div className="space-y-1">
            <div className="font-bold flex items-center gap-2">
              <Download className="h-4 w-4" />
              Full Data Export
            </div>
            <p className="text-sm text-muted-foreground">Download all your records in JSON or CSV format</p>
          </div>
          <Button variant="outline">Export All</Button>
        </div>
        <div className="flex items-center justify-between p-4 border rounded-lg border-destructive/30 bg-destructive/5">
          <div className="space-y-1">
            <div className="font-bold flex items-center gap-2 text-destructive">
              <Trash2 className="h-4 w-4" />
              Purge Old Records
            </div>
            <p className="text-sm text-muted-foreground">Delete records older than 5 years (compliance requirement)</p>
          </div>
          <Button variant="destructive">Purge Data</Button>
        </div>
      </div>
    </SettingsPageShell>
  );
}
