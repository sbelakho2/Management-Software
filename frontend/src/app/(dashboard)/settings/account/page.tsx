'use client';
import React from 'react';
import { SettingsPageShell } from '@/components/settings-page-shell';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function AccountSettingsPage() {
  return (
    <SettingsPageShell title="Account" description="Manage your account security and authentication">
      <div className="space-y-6 max-w-xl">
        <div className="space-y-2">
          <Label>Email Address</Label>
          <Input defaultValue="admin@sensei-manuf.com" />
        </div>
        <div className="pt-4 border-t">
          <h3 className="text-lg font-medium mb-4">Change Password</h3>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Current Password</Label>
              <Input type="password" />
            </div>
            <div className="space-y-2">
              <Label>New Password</Label>
              <Input type="password" />
            </div>
            <Button variant="outline">Update Password</Button>
          </div>
        </div>
      </div>
    </SettingsPageShell>
  );
}
