'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Save,
  FileText,
  Target,
  Search,
  Zap,
  CheckCircle2,
  BarChart3,
  Users,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useI18n } from '@/contexts/i18n-context';

import { useA3Store } from '@/stores/a3';

export default function NewA3Page() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const createA3 = useA3Store(state => state.createA3);
  const [isSaving, setIsSaving] = React.useState(false);
  const [title, setTitle] = React.useState('');

  const handleSave = async () => {
    if (!title) {
      toast({
        title: 'Error',
        description: 'Please enter a title for the A3 report.',
        variant: 'destructive',
      });
      return;
    }

    setIsSaving(true);
    try {
      await createA3({ 
        title,
        status: 'draft',
        priority: 'medium',
        a3_type: 'problem_solving'
      });
      toast({
        title: 'A3 Report Created',
        description: 'The new A3 report has been successfully initialized.',
      });
      router.push('/a3');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create A3 report. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">{t('a3.new.title') || 'New A3 Report'}</h1>
            <p className="text-muted-foreground">{t('a3.new.subtitle') || 'Initialize a new structured problem-solving report'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => router.back()}>
            {t('common.cancel') || 'Cancel'}
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            <Save className="mr-2 h-4 w-4" />
            {isSaving ? (t('a3.new.initializing') || 'Initializing...') : (t('a3.new.createA3') || 'Create A3')}
          </Button>
        </div>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>{t('a3.new.basicInformation.title') || 'Basic Information'}</CardTitle>
          <CardDescription>{t('a3.new.basicInformation.description') || 'Enter the title and basic details for this A3 report'}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">{t('a3.new.basicInformation.a3Title') || 'A3 Title'}</Label>
            <Input 
              id="title"
              placeholder={t('a3.new.basicInformation.titlePlaceholder') || 'e.g., Reducing Defect Rate in Assembly Line A'}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4 text-primary" />
              {t('a3.sections.background.number') || '1.'} {t('a3.sections.background.title') || 'Background'}
            </CardTitle>
            <CardDescription>{t('a3.sections.background.description') || 'Define the context and importance of the problem'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder={t('a3.sections.background.placeholder') || 'Why are we talking about this? What is the business context?'}
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Target className="h-4 w-4 text-primary" />
              {t('a3.sections.currentCondition.number') || '2.'} {t('a3.sections.currentCondition.title') || 'Current Condition'}
            </CardTitle>
            <CardDescription>{t('a3.sections.currentCondition.description') || 'Describe the current state with data/facts'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder={t('a3.sections.currentCondition.placeholder') || 'What is happening now? Use charts, images, or data if possible.'}
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="h-4 w-4 text-primary" />
              {t('a3.sections.goal.number') || '3.'} {t('a3.sections.goal.title') || 'Goal / Target Condition'}
            </CardTitle>
            <CardDescription>{t('a3.sections.goal.description') || 'Define what success looks like'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder={t('a3.sections.goal.placeholder') || 'What specific outcome do we want to achieve? By when?'}
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Search className="h-4 w-4 text-primary" />
              {t('a3.sections.rootCause.number') || '4.'} {t('a3.sections.rootCause.title') || 'Root Cause Analysis'}
            </CardTitle>
            <CardDescription>{t('a3.sections.rootCause.description') || 'Identify the underlying cause(s)'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder={t('a3.sections.rootCause.placeholder') || 'Use 5-Whys or Fishbone to find the real cause.'}
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Zap className="h-4 w-4 text-primary" />
              {t('a3.sections.countermeasures.number') || '5.'} {t('a3.sections.countermeasures.title') || 'Countermeasures'}
            </CardTitle>
            <CardDescription>{t('a3.sections.countermeasures.description') || 'Proposed actions to address root causes'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder={t('a3.sections.countermeasures.placeholder') || 'What are we going to do to fix it?'}
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="h-4 w-4 text-primary" />
              {t('a3.sections.implementation.number') || '6.'} {t('a3.sections.implementation.title') || 'Implementation Plan'}
            </CardTitle>
            <CardDescription>{t('a3.sections.implementation.description') || 'Who, what, when, where'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder={t('a3.sections.implementation.placeholder') || 'Detailed steps for implementation.'}
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-4 w-4 text-primary" />
            {t('a3.sections.team.title') || 'Team & Stakeholders'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>{t('a3.sections.team.reportOwner') || 'Report Owner'}</Label>
              <Input placeholder={t('a3.sections.team.searchUsersPlaceholder') || 'Search users...'} />
            </div>
            <div className="space-y-2">
              <Label>{t('a3.sections.team.contributors') || 'Contributors'}</Label>
              <Input placeholder={t('a3.sections.team.addTeamMembersPlaceholder') || 'Add team members...'} />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
