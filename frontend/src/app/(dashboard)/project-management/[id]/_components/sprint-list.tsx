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

interface SprintListProps {
  projectId: string;
}

export function SprintList({ projectId }: SprintListProps) {
  const { sprints, createSprint, stories } = useProjectManagementStore();
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
          <h2 className="text-3xl font-heading font-bold tracking-tight ">Sprints</h2>
          <p className="text-muted-foreground">Manage your iterative delivery cycles.</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="pm-create-sprint">
              <Plus className="mr-2 h-4 w-4" /> New Sprint
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Sprint</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Sprint Name</label>
                <Input 
                  placeholder="Sprint 1" 
                  value={name} 
                  onChange={(e) => setName(e.target.value)}
                  data-testid="pm-sprint-name"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Start Date</label>
                  <Input 
                    type="date"
                    value={startDate} 
                    onChange={(e) => setStartDate(e.target.value)}
                    data-testid="pm-sprint-start"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">End Date</label>
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
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleCreateSprint} disabled={isSubmitting} data-testid="pm-sprint-submit">
                {isSubmitting ? 'Creating...' : 'Create Sprint'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {activeSprint && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Timer className="h-5 w-5 text-primary" /> Active Sprint
          </h3>
          <SprintCard sprint={activeSprint} stories={stories} isActive />
        </div>
      )}

      {plannedSprints.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Calendar className="h-5 w-5" /> Planned Sprints
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
            <CheckCircle2 className="h-5 w-5 text-green-600" /> Completed Sprints
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
          <p>No sprints found. Create one to get started.</p>
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
  const sprintStories = stories.filter(s => s.sprint_id === sprint.id);
  const completedStories = sprintStories.filter(s => s.status === 'done');
  const progress = sprintStories.length > 0 
    ? Math.round((completedStories.length / sprintStories.length) * 100) 
    : 0;

  const daysRemaining = differenceInDays(new Date(sprint.end_date), new Date());

  const statusBadge: Record<string, { label: string; className: string }> = {
    planned: { label: 'Planned', className: 'bg-gray-100 text-gray-800' },
    active: { label: 'Active', className: 'bg-blue-100 text-blue-800' },
    completed: { label: 'Completed', className: 'bg-green-100 text-green-800' },
    cancelled: { label: 'Cancelled', className: 'bg-red-100 text-red-800' },
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
            <span className="font-medium">{daysRemaining}</span> days remaining
          </div>
        )}

        <div className="space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Progress</span>
            <span>{completedStories.length}/{sprintStories.length} stories ({progress}%)</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
}
