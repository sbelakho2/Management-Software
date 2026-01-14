'use client';

import * as React from 'react';
import { useProjectManagementStore, type Milestone } from '@/stores/project-management-store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { Plus, Flag, Calendar, CheckCircle2, Circle } from 'lucide-react';
import { format } from 'date-fns';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface MilestonesListProps {
  projectId: string;
}

export function MilestonesList({ projectId }: MilestonesListProps) {
  const { milestones, fetchMilestones, createMilestone, updateMilestone, deleteMilestone } = useProjectManagementStore();
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Form state
  const [name, setName] = React.useState('');
  const [dueDate, setDueDate] = React.useState('');
  const [milestoneType, setMilestoneType] = React.useState('deadline');
  const [description, setDescription] = React.useState('');

  React.useEffect(() => {
    fetchMilestones(projectId);
  }, [projectId, fetchMilestones]);

  const projectMilestones = milestones
    .filter(m => m.project_id === projectId)
    .sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime());

  const handleCreateMilestone = async () => {
    if (!name || !dueDate) return;
    
    setIsSubmitting(true);
    try {
      await createMilestone({
        project_id: projectId,
        name,
        due_date: dueDate,
        milestone_type: milestoneType,
        description: description || null,
      });
      setName('');
      setDueDate('');
      setDescription('');
      setIsDialogOpen(false);
    } catch (error) {
      console.error('Failed to create milestone:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleClosed = async (milestone: Milestone) => {
    try {
      await updateMilestone(milestone.id, { is_closed: !milestone.is_closed });
    } catch (error) {
      console.error('Failed to toggle milestone:', error);
    }
  };

  const openMilestones = projectMilestones.filter(m => !m.is_closed);
  const closedMilestones = projectMilestones.filter(m => m.is_closed);

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Milestones</h2>
          <p className="text-muted-foreground">Key project events and deadlines.</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="pm-create-milestone">
              <Plus className="mr-2 h-4 w-4" /> New Milestone
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Milestone</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Name</label>
                <Input 
                  placeholder="Phase 1 Complete" 
                  value={name} 
                  onChange={(e) => setName(e.target.value)}
                  data-testid="pm-milestone-name"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Description</label>
                <Input 
                  placeholder="Details..." 
                  value={description} 
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Due Date</label>
                  <Input 
                    type="date"
                    value={dueDate} 
                    onChange={(e) => setDueDate(e.target.value)}
                    data-testid="pm-milestone-due"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Type</label>
                  <Select value={milestoneType} onValueChange={setMilestoneType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="deadline">Deadline</SelectItem>
                      <SelectItem value="release">Release</SelectItem>
                      <SelectItem value="phase_gate">Phase Gate</SelectItem>
                      <SelectItem value="sprint">Sprint</SelectItem>
                      <SelectItem value="audit">Audit</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleCreateMilestone} disabled={isSubmitting} data-testid="pm-milestone-submit">
                {isSubmitting ? 'Creating...' : 'Create Milestone'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-4">
        {openMilestones.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {openMilestones.map(m => (
              <MilestoneCard key={m.id} milestone={m} onToggle={() => handleToggleClosed(m)} />
            ))}
          </div>
        )}

        {closedMilestones.length > 0 && (
          <>
            <h3 className="text-lg font-semibold mt-8">Completed Milestones</h3>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 opacity-70">
              {closedMilestones.map(m => (
                <MilestoneCard key={m.id} milestone={m} onToggle={() => handleToggleClosed(m)} />
              ))}
            </div>
          </>
        )}

        {projectMilestones.length === 0 && (
          <div className="text-center py-12 border-2 border-dashed rounded-lg">
            <Flag className="mx-auto h-12 w-12 text-muted-foreground opacity-20" />
            <h3 className="mt-4 text-lg font-medium">No milestones defined</h3>
            <p className="text-muted-foreground">Add key dates to track your project progress.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function MilestoneCard({ milestone, onToggle }: { milestone: Milestone, onToggle: () => void }) {
  const progress = milestone.total_items > 0 ? (milestone.closed_items / milestone.total_items) * 100 : 0;
  const isOverdue = !milestone.is_closed && new Date(milestone.due_date) < new Date();

  return (
    <Card className={isOverdue ? 'border-destructive/50' : ''}>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            <button onClick={onToggle} className="hover:scale-110 transition-transform">
              {milestone.is_closed ? <CheckCircle2 className="h-5 w-5 text-green-600" /> : <Circle className="h-5 w-5 text-muted-foreground" />}
            </button>
            <CardTitle className="text-lg">{milestone.name}</CardTitle>
          </div>
          <Badge variant="outline" className="capitalize">{milestone.milestone_type.replace('_', ' ')}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center text-sm text-muted-foreground gap-2">
          <Calendar className="h-4 w-4" />
          <span className={isOverdue ? 'text-destructive font-semibold' : ''}>
            {format(new Date(milestone.due_date), 'PPP')}
            {isOverdue && ' (Overdue)'}
          </span>
        </div>
        
        {milestone.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">{milestone.description}</p>
        )}

        <div className="space-y-2">
          <div className="flex justify-between text-xs font-medium">
            <span>Progress ({milestone.closed_items}/{milestone.total_items} items)</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
}
