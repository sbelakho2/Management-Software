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
      toast({ title: t('quality.capa.new.capaCreated') || 'CAPA Created', description: t('quality.capa.new.initiatedSuccess') || 'Corrective action plan has been initiated.' });
      router.push('/quality?tab=capas');
    } catch (error) {
      toast({ title: t('common.error') || 'Error', description: t('quality.capa.new.createFailed') || 'Failed to create CAPA.', variant: 'destructive' });
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
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('quality.capa.new.title') || 'Initialize CAPA Protocol'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('quality.capa.new.subtitle') || 'Corrective & Preventive Action'}</span>
              <span className="opacity-30">|</span>
              <span>STATION: QUALITY-PLANNING-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.back()} disabled={isSubmitting}>
            {t('common.abort') || 'ABORT'}
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting} size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            {isSubmitting ? (
              t('common.synchronizing') || 'SYNCHRONIZING...'
            ) : (
              <>
                <Save className="h-3.5 w-3.5 mr-2" />
                {t('quality.capa.new.establishCapa') || 'ESTABLISH_CAPA'}
              </>
            )}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="animate-in fade-in slide-in-from-bottom-2 duration-500">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('quality.capa.new.actionPlanParameters') || 'Action Plan Parameters'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-8 p-8">
            <div className="space-y-2">
              <Label htmlFor="title" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.capa.new.capaIdentity') || 'CAPA Identity Protocol'} *</Label>
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
                <Label htmlFor="source" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.capa.new.originNode') || 'Origin Node (Source)'}</Label>
                <Select value={form.source} onValueChange={(v) => setForm({ ...form, source: v })}>
                  <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ncr">NCR_FOLLOW-UP</SelectItem>
                    <SelectItem value="audit">AUDIT_FINDING</SelectItem>
                    <SelectItem value="customer">CUSTOMER_FEEDBACK</SelectItem>
                    <SelectItem value="preventive">PREVENTIVE_SYNC</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="priority" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.capa.new.priorityLayer') || 'Priority Layer'}</Label>
                <Select value={form.priority} onValueChange={(v) => setForm({ ...form, priority: v })}>
                  <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">LOW_PRIORITY</SelectItem>
                    <SelectItem value="medium">MEDIUM_SYNC</SelectItem>
                    <SelectItem value="high">HIGH_URGENCY</SelectItem>
                    <SelectItem value="critical">CRITICAL_BREACH</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="assignee" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.capa.new.assignedOperative') || 'Assigned Operative'}</Label>
                <Input
                  id="assignee"
                  placeholder="OWNER_IDENTITY"
                  value={form.assignee}
                  onChange={(e) => setForm({ ...form, assignee: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="dueDate" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.capa.new.targetHorizon') || 'Target Horizon Date'}</Label>
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
              <Label htmlFor="description" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.capa.new.rootCauseCountermeasures') || 'Root Cause & Countermeasures'} *</Label>
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
