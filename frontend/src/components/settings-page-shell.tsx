'use client';

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Save, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface SettingsPageShellProps {
  title: string;
  description: string;
  children: React.ReactNode;
}

export function SettingsPageShell({ title, description, children }: SettingsPageShellProps) {
  const { toast } = useToast();
  const [isSaving, setIsSaving] = React.useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise(resolve => setTimeout(resolve, 800));
    setIsSaving(false);
    toast({
      title: 'Settings updated',
      description: `Your ${title.toLowerCase()} have been successfully saved.`,
    });
  };

  return (
    <div className="space-y-8 page-fade-in max-w-4xl">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            {title}
          </h1>
          <p className="text-muted-foreground font-medium text-sm">{description}</p>
        </div>
        <Button onClick={handleSave} disabled={isSaving} className="rounded-2xl shadow-glow subtle-shine h-12 px-8" size="lg">
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Synchronizing...
            </>
          ) : (
            <>
              <Save className="mr-2 h-5 w-5" />
              Save Configuration
            </>
          )}
        </Button>
      </div>
      <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium overflow-hidden">
        <CardContent className="pt-8 p-8 md:p-10">
          {children}
        </CardContent>
      </Card>
    </div>
  );
}
