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

export default function NewProgramPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const [form, setForm] = React.useState({
    title: '',
    description: '',
    category: '',
    level: 'beginner',
    duration: '',
    instructor: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      toast({
        title: t('training.programs.new.toast.success.title') || 'Program Created',
        description: t('training.programs.new.toast.success.description') || 'New training program has been added to the catalog.',
      });
      router.push('/training');
    }, 1000);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('training.programs.new.title') || 'New Training Program'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('training.programs.new.subtitle') || 'Create a new development curriculum'}</span>
              <span className="opacity-30">|</span>
              <span>STATION: ACADEMY-CREATE-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.back()}>{t('common.cancel') || 'Cancel'}</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting} className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            <Save className="h-3.5 w-3.5 mr-2" />
            {isSubmitting ? (t('common.creating') || 'Creating...') : (t('training.programs.new.createProgram') || 'Create Program')}
          </Button>
        </div>
      </div>

      <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
        <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('training.programs.new.programDetails') || 'Program Details'}</CardTitle>
        </CardHeader>
        <CardContent className="p-8">
          <form onSubmit={handleSubmit} className="space-y-8">
            <div className="space-y-2">
              <Label htmlFor="title" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.programs.new.programTitle') || 'Program Title'} *</Label>
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
                <Label htmlFor="category" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.programs.new.category') || 'Category'}</Label>
                <Input
                  id="category"
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="level" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.programs.new.skillLevel') || 'Skill Level'}</Label>
                <Select value={form.level} onValueChange={(v) => setForm({ ...form, level: v })}>
                  <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"><SelectValue /></SelectTrigger>
                  <SelectContent className="rounded-rams-sm border-rams-line">
                    <SelectItem value="beginner">{t('common.beginner') || 'Beginner'}</SelectItem>
                    <SelectItem value="intermediate">{t('common.intermediate') || 'Intermediate'}</SelectItem>
                    <SelectItem value="advanced">{t('common.advanced') || 'Advanced'}</SelectItem>
                    <SelectItem value="expert">{t('common.expert') || 'Expert'}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="duration" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.programs.new.estimatedDuration') || 'Estimated Duration'}</Label>
                <Input
                  id="duration"
                  placeholder={t('training.programs.new.durationPlaceholder') || 'e.g., 20 hours'}
                  value={form.duration}
                  onChange={(e) => setForm({ ...form, duration: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="instructor" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.programs.new.instructor') || 'Instructor'}</Label>
                <Input
                  id="instructor"
                  value={form.instructor}
                  onChange={(e) => setForm({ ...form, instructor: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('common.description') || 'Description'}</Label>
              <Textarea
                id="description"
                rows={4}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed h-48 resize-none"
              />
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
