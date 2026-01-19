'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X } from 'lucide-react';
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

export default function NewTaskPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const [form, setForm] = React.useState({
    title: '',
    description: '',
    priority: 'medium',
    dueDate: '',
    assigneeId: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      toast({ title: t('pages.tasks.new.taskCreated'), description: t('pages.tasks.new.taskCreatedDescription') });
      router.push('/tasks');
    } catch (error) {
      toast({ title: t('common.error'), description: t('pages.tasks.new.taskCreateError'), variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('pages.tasks.new.title')}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('pages.tasks.new.subtitle')}</span>
              <span className="opacity-30">|</span>
              <span>{t('pages.tasks.new.station')}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.back()}>{t('pages.tasks.new.discard')}</Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none" onClick={handleSubmit} disabled={isSubmitting}>
            <Save className="h-3.5 w-3.5 mr-2" />
            {isSubmitting ? t('pages.tasks.new.synchronizing') : t('pages.tasks.new.createAssignment')}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.tasks.new.protocolParameters')}</CardTitle>
            <CardDescription className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('pages.tasks.new.configureMetadata')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-8 p-8">
            <div className="space-y-2">
              <Label htmlFor="title" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.tasks.new.assignmentTitle')} *</Label>
              <Input
                id="title"
                placeholder={t('pages.tasks.new.titlePlaceholder')}
                className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
            </div>
            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="priority" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('common.priorityLayer')}</Label>
                <Select value={form.priority} onValueChange={(v) => setForm({ ...form, priority: v })}>
                  <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">{t('common.priority.low')}</SelectItem>
                    <SelectItem value="medium">{t('common.priority.medium')}</SelectItem>
                    <SelectItem value="high">{t('common.priority.high')}</SelectItem>
                    <SelectItem value="urgent">{t('common.priority.urgent')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="dueDate" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('common.temporalHorizon')}</Label>
                <div className="relative">
                  <Input
                    id="dueDate"
                    type="date"
                    className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                    value={form.dueDate}
                    onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
                  />
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('common.detailedIntelligence')}</Label>
              <div className="relative">
                <Textarea
                  id="description"
                  placeholder={t('pages.tasks.new.descriptionPlaceholder')}
                  className="rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed min-h-[160px] resize-none"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
