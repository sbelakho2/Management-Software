'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, GraduationCap, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { useI18n } from '@/contexts/i18n-context';
export default function EnrollTrainingPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const programs = [
    { id: '1', title: 'Safety Fundamentals 2024' },
    { id: '2', title: 'Lean Six Sigma White Belt' },
    { id: '3', title: 'Advanced Machining Center Operation' },
    { id: '4', title: 'Quality Assurance - Basic' },
  ];
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      toast({
        title: t('training.enroll.toast.success.title') || 'Enrolled Successfully',
        description: t('training.enroll.toast.success.description') || 'You have been added to the training program.',
      });
      router.push('/training');
    }, 1000);
  };
  return (
    <div className="max-w-2xl mx-auto space-y-8 page-fade-in pb-12">
      <div className="flex items-center gap-4 border-b border-rams-line pb-8">
        <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('training.enroll.title') || 'Enrollment Protocol'}</h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">{t('training.enroll.subtitle') || 'Join a new organizational development program'}</p>
        </div>
      </div>
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
        <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('training.enroll.initiateEnrollment') || 'Initiate Enrollment'}</CardTitle>
          <CardDescription className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground/50 mt-1">{t('training.enroll.configureParams') || 'Configure your training node parameters'}</CardDescription>
        </CardHeader>
        <CardContent className="p-8">
          <form onSubmit={handleSubmit} className="space-y-8">
            <div className="space-y-2">
              <Label htmlFor="program" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.enroll.strategicProgramNode') || 'Strategic Program Node'}</Label>
              <Select required>
                <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                  <SelectValue placeholder={t('training.enroll.selectProgram') || 'Select a program node'} />
                </SelectTrigger>
                <SelectContent className="rounded-rams-sm border-rams-line">
                  {programs.map(p => (
                    <SelectItem key={p.id} value={p.id}>{p.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reason" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.enroll.rationalOptimization') || 'Rational Optimization Context (Optional)'}</Label>
              <Input id="reason" placeholder={t('training.enroll.reasonPlaceholder') || 'e.g. Skill gap resolution, maturity escalation...'} className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider" />
            </div>
            <div className="pt-6 flex gap-4">
              <Button type="button" variant="outline" className="flex-1 rounded-rams-sm border-rams-line h-10 transition-none" onClick={() => router.back()}>{t('common.abort') || 'Abort'}</Button>
              <Button type="submit" className="flex-1 rounded-rams-sm bg-rams-orange text-black font-black h-10 uppercase tracking-widest text-[10px] transition-none" disabled={isSubmitting}>
                {isSubmitting ? (t('common.synchronizing') || 'Synchronizing...') : (t('training.enroll.establishEnrollment') || 'Establish Enrollment')}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
