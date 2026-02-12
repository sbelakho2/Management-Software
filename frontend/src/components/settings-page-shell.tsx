'use client';

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Save, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useI18n } from '@/contexts/i18n-context';

interface SettingsPageShellProps {
  title: string;
  description: string;
  children: React.ReactNode;
}

export function SettingsPageShell({ title, description, children }: SettingsPageShellProps) {
  const { t } = useI18n();
  const { toast } = useToast();
  const [isSaving, setIsSaving] = React.useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise(resolve => setTimeout(resolve, 800));
    setIsSaving(false);
    toast({
      title: t('settings.shell.toastTitle'),
      description: t('settings.shell.toastDescription', { title: title.toUpperCase() }),
    });
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {title}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">{description}</p>
        </div>
        <Button onClick={handleSave} disabled={isSaving} className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
              {t('settings.shell.synchronizing')}
            </>
          ) : (
            <>
              <Save className="mr-2 h-3.5 w-3.5" />
              {t('settings.shell.saveConfiguration')}
            </>
          )}
        </Button>
      </div>
      <div className="bg-rams-module">
        {children}
      </div>
    </div>
  );
}
