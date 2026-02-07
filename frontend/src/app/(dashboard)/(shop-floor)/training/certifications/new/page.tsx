'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X } from 'lucide-react';
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
import { useTrainingStore } from '@/stores/training';
import { useHRStore } from '@/stores/hr';
import { useI18n } from '@/contexts/i18n-context';
import { useToast } from '@/hooks/use-toast';

export default function NewCertificationPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [skillId, setSkillId] = React.useState<string>('');
  const [userId, setUserId] = React.useState<string>('');
  const [proficiency, setProficiency] = React.useState<string>('');
  const [issueDate, setIssueDate] = React.useState<string>('');
  const [expiryDate, setExpiryDate] = React.useState<string>('');
  
  const { skills, fetchSkills, registerCertification } = useTrainingStore();
  const { employees, fetchEmployees } = useHRStore();

  React.useEffect(() => {
    fetchSkills();
    fetchEmployees();
  }, [fetchSkills, fetchEmployees]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!skillId || !userId) {
      toast({
        title: t('common.validation_error') || 'Validation Error',
        description: t('training.certifications.new.validation') || 'Please select a competency and a team member.',
        variant: 'destructive',
      });
      return;
    }

    try {
      setIsSubmitting(true);
      await registerCertification({
        userId: String(userId),
        skillId: String(skillId),
        proficiency: Number(proficiency) || 0,
        issueDate: issueDate || undefined,
        expiryDate: expiryDate || undefined,
      });
      toast({
        title: t('training.certifications.new.toast.success.title') || 'Certification Registered',
        description: t('training.certifications.new.toast.success.description') || 'New certification has been added to the system.',
      });
      router.push('/training');
    } catch (error: any) {
      toast({
        title: t('common.error') || 'Error',
        description: error?.message || (t('training.certifications.new.toast.error.description') as string) || 'Failed to register certification.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  return (
    <div className="max-w-2xl mx-auto space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('training.certifications.new.title') || 'New Certification'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('training.certifications.new.subtitle') || 'Register a new certificate for a team member'}</span>
              <span className="opacity-30">|</span>
              <span>STATION: ACADEMY-REG-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.back()}>{t('common.cancel') || 'Cancel'}</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting} className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            <Save className="h-3.5 w-3.5 mr-2" />
            {isSubmitting ? (t('common.saving') || 'Saving...') : (t('training.certifications.new.registerCertification') || 'Register Certification')}
          </Button>
        </div>
      </div>
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
        <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('training.certifications.new.certificationDetails') || 'Certification Details'}</CardTitle>
        </CardHeader>
        <CardContent className="p-8">
          <form onSubmit={handleSubmit} className="space-y-8">
            <div className="space-y-2">
              <Label htmlFor="skill" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.certifications.new.certificationTitle') || 'Target Competency'} *</Label>
              <Select required value={skillId} onValueChange={setSkillId}>
                <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                  <SelectValue placeholder="Select Competency / Skill" />
                </SelectTrigger>
                <SelectContent className="rounded-rams-sm border-rams-line max-h-[200px]">
                   {skills.map(s => (
                       <SelectItem key={s.id} value={String(s.id)}>{s.name} ({s.code})</SelectItem>
                   ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="user" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.certifications.new.teamMember') || 'Team Member'}</Label>
                <Select required value={userId} onValueChange={setUserId}>
                    <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue placeholder="Select Employee" />
                    </SelectTrigger>
                    <SelectContent className="rounded-rams-sm border-rams-line max-h-[200px]">
                    {employees.map(e => (
                        <SelectItem key={e.id} value={String(e.id)}>{e.first_name} {e.last_name}</SelectItem>
                    ))}
                    </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="score" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.certifications.new.finalScore') || 'Grade / Proficiency'}</Label>
                <Select value={proficiency} onValueChange={setProficiency}>
                    <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue placeholder="Level 0-4" />
                    </SelectTrigger>
                    <SelectContent className="rounded-rams-sm border-rams-line">
                        <SelectItem value="1">Level 1 - Novice</SelectItem>
                        <SelectItem value="2">Level 2 - Intermediate</SelectItem>
                        <SelectItem value="3">Level 3 - Advanced</SelectItem>
                        <SelectItem value="4">Level 4 - Expert</SelectItem>
                    </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="issueDate" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.certifications.new.issueDate') || 'Issue Date'}</Label>
                <Input id="issueDate" type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="expiryDate" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('training.certifications.new.expiryDate') || 'Expiry Date'}</Label>
                <Input id="expiryDate" type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold" />
              </div>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

