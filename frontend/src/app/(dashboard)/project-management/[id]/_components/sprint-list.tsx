'use client';

import * as React from 'react';
import { useProjectManagementStore, type Sprint, type UserStory } from '@/stores/project-management-store';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { Plus, Calendar, Timer, CheckCircle2 } from 'lucide-react';
import { format, differenceInDays } from 'date-fns';
import { useI18n } from '@/contexts/i18n-context';

interface SprintListProps {
  projectId: string;
}

export function SprintList({ projectId }: SprintListProps) {
  const { sprints, createSprint, stories } = useProjectManagementStore();
  const { t } = useI18n();
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Form state
  const [name, setName] = React.useState('');
  const [startDate, setStartDate] = React.useState('');
  const [endDate, setEndDate] = React.useState('');

  const projectSprints = sprints
    .filter(s => s.project_id === projectId)
    .sort((a, b) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime());

  const handleCreateSprint = async () => {
    if (!name || !startDate || !endDate) return;
    
    setIsSubmitting(true);
    try {
      await createSprint(projectId, name, startDate, endDate);
      setName('');
      setStartDate('');
      setEndDate('');
      setIsDialogOpen(false);
    } catch (error) {
      console.error('Failed to create sprint:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeSprint = projectSprints.find(s => s.status === 'active');
  const plannedSprints = projectSprints.filter(s => s.status === 'planned');
  const completedSprints = projectSprints.filter(s => s.status === 'completed');

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-heading font-bold tracking-tight ">{t('pages.projectManagement.detail.sprints')}</h2>
          <p className="text-muted-foreground">{t('pages.projectManagement.sprints.subtitle')}</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="pm-create-sprint">
              <Plus className="mr-2 h-4 w-4" /> {t('pages.projectManagement.sprints.newSprint')}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('pages.projectManagement.sprints.createNewSprint')}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">{t('pages.projectManagement.sprints.sprintName')}</label>
                <Input 
                  placeholder="Sprint 1" 
                  value={name} 
                  onChange={(e) => setName(e.target.value)}
                  data-testid="pm-sprint-name"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">{t('pages.projectManagement.sprints.startDate')}</label>
                  <Input 
                    type="date"
                    value={startDate} 
                    onChange={(e) => setStartDate(e.target.value)}
                    data-testid="pm-sprint-start"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">{t('pages.projectManagement.sprints.endDate')}</label>
                  <Input 
                    type="date"
                    value={endDate} 
                    onChange={(e) => setEndDate(e.target.value)}
                    data-testid="pm-sprint-end"
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>{t('common.cancel')}</Button>
              <Button onClick={handleCreateSprint} disabled={isSubmitting} data-testid="pm-sprint-submit">
                {isSubmitting ? t('pages.projectManagement.sprints.creating') : t('pages.projectManagement.sprints.createSprint')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {activeSprint && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Timer className="h-5 w-5 text-primary" /> {t('pages.projectManagement.sprints.activeSprint')}
          </h3>
          <SprintCard sprint={activeSprint} stories={stories} isActive />
        </div>
      )}

      {plannedSprints.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Calendar className="h-5 w-5" /> {t('pages.projectManagement.sprints.plannedSprints')}
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            {plannedSprints.map(sprint => (
              <SprintCard key={sprint.id} sprint={sprint} stories={stories} />
            ))}
          </div>
        </div>
      )}

      {completedSprints.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-600" /> {t('pages.projectManagement.sprints.completedSprints')}
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {completedSprints.map(sprint => (
              <SprintCard key={sprint.id} sprint={sprint} stories={stories} />
            ))}
          </div>
        </div>
      )}

      {projectSprints.length === 0 && (
        <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-lg text-muted-foreground">
          <Calendar className="h-12 w-12 mb-4 opacity-20" />
          <p>{t('pages.projectManagement.sprints.noSprintsFound')}</p>
        </div>
      )}
    </div>
  );
}

interface SprintCardProps {
  sprint: Sprint;
  stories: UserStory[];
  isActive?: boolean;
}

function SprintCard({ sprint, stories, isActive }: SprintCardProps) {
  const { t } = useI18n();
  const sprintStories = stories.filter(s => s.sprint_id === sprint.id);
  const completedStories = sprintStories.filter(s => s.status === 'done');
  const progress = sprintStories.length > 0 
    ? Math.round((completedStories.length / sprintStories.length) * 100) 
    : 0;

  const daysRemaining = differenceInDays(new Date(sprint.end_date), new Date());

  const statusBadge: Record<string, { label: string; className: string }> = {
    planned: { label: t('pages.projectManagement.sprints.statusPlanned'), className: 'bg-gray-100 text-gray-800' },
    active: { label: t('pages.projectManagement.sprints.statusActive'), className: 'bg-blue-100 text-blue-800' },
    completed: { label: t('pages.projectManagement.sprints.statusCompleted'), className: 'bg-green-100 text-green-800' },
    cancelled: { label: t('pages.projectManagement.sprints.statusCancelled'), className: 'bg-red-100 text-red-800' },
  };

  const badge = statusBadge[sprint.status] || statusBadge.planned;

  return (
    <Card className={isActive ? 'border-primary ring-1 ring-primary' : ''}>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <CardTitle className="text-lg">{sprint.name}</CardTitle>
          <Badge className={badge.className}>{badge.label}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center text-sm text-muted-foreground">
          <Calendar className="mr-2 h-4 w-4" />
          {format(new Date(sprint.start_date), 'MMM d')} - {format(new Date(sprint.end_date), 'MMM d, yyyy')}
        </div>

        {isActive && daysRemaining >= 0 && (
          <div className="text-sm">
            <span className="font-medium">{daysRemaining}</span> {t('pages.projectManagement.sprints.daysRemaining')}
          </div>
        )}

        <div className="space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{t('pages.projectManagement.sprints.progress')}</span>
            <span>{completedStories.length}/{sprintStories.length} {t('pages.projectManagement.sprints.stories')} ({progress}%)</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
}
