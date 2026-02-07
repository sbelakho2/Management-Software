'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X, Shield } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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

export default function NewCAPAPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const [form, setForm] = React.useState({
    title: '',
    description: '',
    source: 'ncr',
    priority: 'medium',
    assignee: '',
    dueDate: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      toast({ title: t('modules.quality.capa.new.capaCreated'), description: t('modules.quality.capa.new.initiatedSuccess') });
      router.push('/quality?tab=capas');
    } catch (error) {
      toast({ title: t('common.error'), description: t('modules.quality.capa.new.createFailed'), variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('modules.quality.capa.new.title')}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('modules.quality.capa.new.subtitle')}</span>
              <span className="opacity-30">|</span>
              <span>STATION: QUALITY-PLANNING-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.back()} disabled={isSubmitting}>
            {t('common.abort')}
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting} size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            {isSubmitting ? (
              t('common.synchronizing')
            ) : (
              <>
                <Save className="h-3.5 w-3.5 mr-2" />
                {t('modules.quality.capa.new.establishCapa')}
              </>
            )}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="animate-in fade-in slide-in-from-bottom-2 duration-500">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('modules.quality.capa.new.actionPlanParameters')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-8 p-8">
            <div className="space-y-2">
              <Label htmlFor="title" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.capa.new.capaIdentity')} *</Label>
              <Input
                id="title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="source" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.capa.new.originNode')}</Label>
                <Select value={form.source} onValueChange={(v) => setForm({ ...form, source: v })}>
                  <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ncr">{t('modules.quality.capa.new.source.ncr')}</SelectItem>
                    <SelectItem value="audit">{t('modules.quality.capa.new.source.audit')}</SelectItem>
                    <SelectItem value="customer">{t('modules.quality.capa.new.source.customer')}</SelectItem>
                    <SelectItem value="preventive">{t('modules.quality.capa.new.source.preventive')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="priority" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.capa.new.priorityLayer')}</Label>
                <Select value={form.priority} onValueChange={(v) => setForm({ ...form, priority: v })}>
                  <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">{t('modules.quality.capa.new.priority.low')}</SelectItem>
                    <SelectItem value="medium">{t('modules.quality.capa.new.priority.medium')}</SelectItem>
                    <SelectItem value="high">{t('modules.quality.capa.new.priority.high')}</SelectItem>
                    <SelectItem value="critical">{t('modules.quality.capa.new.priority.critical')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="assignee" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.capa.new.assignedOperative')}</Label>
                <Input
                  id="assignee"
                  placeholder={t('modules.quality.capa.new.placeholders.ownerIdentity')}
                  value={form.assignee}
                  onChange={(e) => setForm({ ...form, assignee: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="dueDate" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.capa.new.targetHorizon')}</Label>
                <Input
                  id="dueDate"
                  type="date"
                  value={form.dueDate}
                  onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.capa.new.rootCauseCountermeasures')} *</Label>
              <Textarea
                id="description"
                rows={5}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed h-48 resize-none"
                required
              />
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
