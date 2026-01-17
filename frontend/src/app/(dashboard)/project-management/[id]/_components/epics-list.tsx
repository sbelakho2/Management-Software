'use client';

import * as React from 'react';
import { useProjectManagementStore, type Epic } from '@/stores/project-management-store';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { Plus, Layers } from 'lucide-react';

interface EpicsListProps {
  projectId: string;
}

export function EpicsList({ projectId }: EpicsListProps) {
  const { epics, createEpic, stories } = useProjectManagementStore();
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Form state
  const [subject, setSubject] = React.useState('');
  const [description, setDescription] = React.useState('');

  const projectEpics = epics.filter(e => e.project_id === projectId);

  const calculateProgress = (epicId: string) => {
    const epicStories = stories.filter(s => s.epic_id === epicId);
    if (epicStories.length === 0) return 0;
    const completed = epicStories.filter(s => s.status === 'done').length;
    return Math.round((completed / epicStories.length) * 100);
  };

  const handleCreateEpic = async () => {
    if (!subject.trim()) return;
    
    setIsSubmitting(true);
    try {
      await createEpic(projectId, subject, description || undefined);
      setSubject('');
      setDescription('');
      setIsDialogOpen(false);
    } catch (error) {
      console.error('Failed to create epic:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const statusColor: Record<string, string> = {
    new: 'bg-gray-100 text-gray-800',
    in_progress: 'bg-blue-100 text-blue-800',
    done: 'bg-green-100 text-green-800',
    closed: 'bg-gray-200 text-gray-600',
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-heading font-bold tracking-tight ">Epics</h2>
          <p className="text-muted-foreground">High-level initiatives breaking down into user stories.</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="pm-create-epic">
              <Plus className="mr-2 h-4 w-4" /> New Epic
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Epic</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Input 
                  placeholder="Epic Subject" 
                  value={subject} 
                  onChange={(e) => setSubject(e.target.value)}
                  data-testid="pm-epic-subject"
                />
              </div>
              <div className="space-y-2">
                <Textarea 
                  placeholder="Description" 
                  value={description} 
                  onChange={(e) => setDescription(e.target.value)}
                  data-testid="pm-epic-description"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleCreateEpic} disabled={isSubmitting} data-testid="pm-epic-submit">
                {isSubmitting ? 'Creating...' : 'Create Epic'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {projectEpics.map((epic) => {
           const progress = calculateProgress(epic.id);
           return (
            <Card key={epic.id} className="relative overflow-hidden hover:shadow-md transition-shadow">
                <div className="absolute top-0 left-0 w-1 h-full bg-primary" />
                <CardHeader>
                    <div className="flex justify-between items-start">
                        <CardTitle className="text-lg">EP-{epic.ref}: {epic.subject}</CardTitle>
                        <Badge className={statusColor[epic.status] || 'bg-gray-100'}>{epic.status.replace('_', ' ')}</Badge>
                    </div>
                </CardHeader>
                <CardContent className="pb-2">
                    <p className="text-sm text-muted-foreground line-clamp-2 min-h-[2.5rem]">
                        {epic.description || "No description provided."}
                    </p>
                    <div className="mt-4 space-y-2">
                        <div className="flex justify-between text-xs text-muted-foreground">
                            <span>Progress</span>
                            <span>{progress}%</span>
                        </div>
                        <Progress value={progress} className="h-2" />
                    </div>
                </CardContent>
                <CardFooter className="pt-2 text-xs text-muted-foreground flex justify-between">
                    <div className="flex items-center">
                        <Layers className="mr-1 h-3 w-3" />
                        {stories.filter(s => s.epic_id === epic.id).length} stories
                    </div>
                </CardFooter>
            </Card>
           );
        })}
        {projectEpics.length === 0 && (
            <div className="col-span-full flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-lg text-muted-foreground">
                <Layers className="h-12 w-12 mb-4 opacity-20" />
                <p>No epics found. Create one to get started.</p>
            </div>
        )}
      </div>
    </div>
  );
}
