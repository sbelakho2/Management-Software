'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Save,
  LayoutGrid,
  Users,
  Target,
  BarChart3,
  Plus,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { useI18n } from '@/contexts/i18n-context';

export default function NewObeyaBoardPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const [isSaving, setIsSaving] = React.useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
    toast({
      title: 'Obeya Board Created',
      description: 'Your new digital obeya board has been successfully initialized.',
    });
    router.push('/obeya');
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-orange/10 transition-none" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">{t('pages.obeyaNew.title') || 'New Strategic Obeya'}</h1>
            <p className="text-muted-foreground font-medium text-sm">{t('pages.obeyaNew.description') || 'Create a centralized organizational intelligence node for your team'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-rams-sm border-rams-line hover:bg-rams-orange/5 h-12 px-8" onClick={() => router.back()}>
            {t('common.abort') || 'Abort'}
          </Button>
          <Button size="lg" className="rounded-rams-sm bg-rams-orange text-black h-12 px-8 font-black" onClick={handleSave} disabled={isSaving}>
            <Save className="h-4 w-4 mr-2" />
            {isSaving ? (t('common.initializing') || 'Initializing...') : (t('pages.obeyaNew.establishBoard') || 'Establish Board')}
          </Button>
        </div>
      </div>

      <div className="grid gap-8">
        <Card className="rounded-rams-sm border-rams-line bg-rams-module overflow-hidden">
          <CardHeader className="pb-8 border-b border-rams-line bg-rams-panel/20 p-8">
            <CardTitle className="text-lg font-heading">{t('pages.obeyaNew.protocolConfiguration') || 'Protocol Configuration'}</CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">{t('pages.obeyaNew.protocolConfigurationDescription') || 'Basic parameters and ownership nodes'}</CardDescription>
          </CardHeader>
          <CardContent className="p-8 space-y-8">
            <div className="grid gap-8 sm:grid-cols-2">
              <div className="sm:col-span-2 space-y-3">
                <Label htmlFor="name" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">{t('pages.obeyaNew.boardIdentity') || 'Strategic Board Identity'}</Label>
                <Input id="name" placeholder={t('pages.obeyaNew.boardIdentityPlaceholder') || 'e.g. Operations Tier 2 Command Center'} className="h-12 rounded-rams-sm bg-rams-panel border-rams-line transition-none focus:border-rams-orange" />
              </div>
              <div className="space-y-3">
                <Label htmlFor="team" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">{t('pages.obeyaNew.departmentNode') || 'Departmental Node'}</Label>
                <Select>
                  <SelectTrigger id="team" className="h-12 rounded-rams-sm bg-rams-panel border-rams-line">
                    <SelectValue placeholder={t('pages.obeyaNew.identifyTeam') || 'Identify team'} />
                  </SelectTrigger>
                  <SelectContent className="rounded-rams-sm">
                    <SelectItem value="ops" className="rounded-rams-sm m-1">Operations</SelectItem>
                    <SelectItem value="eng" className="rounded-rams-sm m-1">Engineering</SelectItem>
                    <SelectItem value="quality" className="rounded-rams-sm m-1">Quality Assurance</SelectItem>
                    <SelectItem value="sales" className="rounded-rams-sm m-1">Strategic Sales</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-3">
                <Label htmlFor="owner" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">{t('pages.obeyaNew.primaryCustodian') || 'Primary Custodian'}</Label>
                <Input id="owner" placeholder={t('pages.obeyaNew.searchUserNodes') || 'Search user nodes...'} className="h-12 rounded-rams-sm bg-rams-panel border-rams-line" />
              </div>
            </div>
            <div className="space-y-3">
              <Label htmlFor="desc" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">{t('pages.obeyaNew.strategicContext') || 'Strategic Context'}</Label>
              <Textarea id="desc" placeholder={t('pages.obeyaNew.strategicContextPlaceholder') || 'Purpose and scope of this management protocol...'} className="rounded-rams-sm bg-rams-panel border-rams-line focus:border-rams-orange transition-none min-h-[100px] resize-none" rows={3} />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="p-8">
            <CardTitle className="text-lg font-heading">{t('pages.obeyaNew.intelligenceModules') || 'Intelligence Modules (SQDCP)'}</CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">{t('pages.obeyaNew.intelligenceModulesDescription') || 'Select categorical nodes to activate on board'}</CardDescription>
          </CardHeader>
          <CardContent className="p-8 pt-0">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {[
                { id: 'safety', label: 'Safety (S)', color: 'bg-rams-green' },
                { id: 'quality', label: 'Quality (Q)', color: 'bg-rams-steel' },
                { id: 'delivery', label: 'Delivery (D)', color: 'bg-rams-orange' },
                { id: 'cost', label: 'Cost (C)', color: 'bg-rams-red' },
                { id: 'people', label: 'People (P)', color: 'bg-rams-steel' },
                { id: 'exceptions', label: 'Exceptions Log', color: 'bg-rams-muted' },
              ].map((module) => (
                <div key={module.id} className="flex items-center justify-between p-5 rounded-rams-sm bg-rams-panel/20 border border-rams-line group transition-none hover:bg-rams-orange/5">
                  <div className="flex items-center gap-4">
                    <div className={cn("w-1.5 h-8 rounded-none", module.color)} />
                    <span className="font-heading font-bold text-sm tracking-tight text-foreground/80">{module.label}</span>
                  </div>
                  <input type="checkbox" defaultChecked className="h-5 w-5 rounded-rams-sm border-rams-line bg-rams-panel text-rams-orange focus:ring-rams-orange transition-none cursor-pointer" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
