'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
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

export default function EditA3Page() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useParams();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const [form, setForm] = React.useState({
    title: 'Optimization of Machining Center B Cycle Time',
    a3_type: 'problem_solving',
    status: 'in_progress',
    priority: 'high',
    department: 'Manufacturing',
    background: 'Cycle times for Center B have increased by 15% over the last 3 months due to frequent tool changes and setup delays.',
    currentStatus: 'Average cycle time: 42 mins. Targeted cycle time: 35 mins.',
    goals: 'Reduce setup time by 20% and tool change time by 10%.',
    analysis: 'Root cause identified as lack of standardized setup kits and disorganized tool crib.',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      toast({ title: 'A3 Report Updated', description: 'Changes have been saved successfully.' });
      router.push(`/a3/${params.id}`);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to update A3 report.', variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">{t('a3.edit.title') || 'Edit A3 Report'}</h1>
            <p className="text-muted-foreground">{t('a3.edit.subtitle') || 'Modify the strategic problem-solving document'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => router.back()}>{t('common.cancel') || 'Cancel'}</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            <Save className="h-4 w-4 mr-2" />
            {isSubmitting ? (t('a3.edit.saving') || 'Saving...') : (t('a3.edit.saveChanges') || 'Save Changes')}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('a3.edit.basicInformation') || 'Basic Information'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">{t('a3.edit.reportTitle') || 'Report Title'} *</Label>
              <Input
                id="title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="type">{t('a3.edit.reportType') || 'Report Type'}</Label>
                <Select value={form.a3_type} onValueChange={(v) => setForm({ ...form, a3_type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="problem_solving">{t('a3.types.problemSolving') || 'Problem Solving'}</SelectItem>
                    <SelectItem value="proposal">{t('a3.types.proposal') || 'Proposal'}</SelectItem>
                    <SelectItem value="status_report">{t('a3.types.statusReport') || 'Status Report'}</SelectItem>
                    <SelectItem value="strategy">{t('a3.types.strategy') || 'Strategy'}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="status">{t('a3.edit.status') || 'Status'}</Label>
                <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">{t('a3.statuses.draft') || 'Draft'}</SelectItem>
                    <SelectItem value="in_progress">{t('a3.statuses.inProgress') || 'In Progress'}</SelectItem>
                    <SelectItem value="review">{t('a3.statuses.review') || 'Review'}</SelectItem>
                    <SelectItem value="approved">{t('a3.statuses.approved') || 'Approved'}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('a3.edit.content') || 'Content'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="background">{t('a3.edit.sections.background') || '1. Background'}</Label>
              <Textarea
                id="background"
                rows={3}
                value={form.background}
                onChange={(e) => setForm({ ...form, background: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="currentStatus">{t('a3.edit.sections.currentStatus') || '2. Current Status'}</Label>
              <Textarea
                id="currentStatus"
                rows={3}
                value={form.currentStatus}
                onChange={(e) => setForm({ ...form, currentStatus: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="goals">{t('a3.edit.sections.goals') || '3. Goals / Targets'}</Label>
              <Textarea
                id="goals"
                rows={3}
                value={form.goals}
                onChange={(e) => setForm({ ...form, goals: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="analysis">{t('a3.edit.sections.analysis') || '4. Root Cause Analysis'}</Label>
              <Textarea
                id="analysis"
                rows={3}
                value={form.analysis}
                onChange={(e) => setForm({ ...form, analysis: e.target.value })}
              />
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
