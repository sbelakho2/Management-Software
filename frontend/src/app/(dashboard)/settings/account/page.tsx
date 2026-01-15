'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function AccountSettingsPage() {
  return (
    <SettingsPageShell title="Account Node" description="Manage your primary identity credentials and authentication layers">
      <div className="space-y-10 max-w-xl">
        <div className="space-y-3">
          <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Primary Email Protocol</Label>
          <Input defaultValue="admin@sensei-manuf.com" className="h-12" />
        </div>
        
        <div className="pt-8 border-t border-border/10">
          <h3 className="text-xl font-heading font-bold tracking-tight mb-6">Credential Rotation</h3>
          <div className="space-y-6">
            <div className="space-y-3">
              <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Current Password</Label>
              <Input type="password" placeholder="••••••••" className="h-12" />
            </div>
            <div className="space-y-3">
              <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">New Intelligence Key</Label>
              <Input type="password" placeholder="••••••••" className="h-12" />
            </div>
            <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
              Update Credentials
            </Button>
          </div>
        </div>
      </div>
    </SettingsPageShell>
  );
}
