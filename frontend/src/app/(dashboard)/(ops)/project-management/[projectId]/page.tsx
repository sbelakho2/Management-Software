'use client';

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Plus, RefreshCw, MessageSquare, CheckCircle2, Circle, Layers, CalendarDays, ListChecks } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { cn, formatRelativeTime } from '@/lib/utils';
import {
  useProjectManagementStore,
  type Project,
  type Epic,
  type Sprint,
  type UserStory,
  type Subtask,
  type StoryComment,
} from '@/stores/project-management-store';

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    planning: 'bg-muted text-muted-foreground',
    active: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-100',
    on_hold: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100',
    completed: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100',
    archived: 'bg-gray-200 text-gray-700 dark:bg-gray-800 dark:text-gray-200',
    cancelled: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100',
  };
  return <Badge className={cn('border', map[status] ?? 'bg-muted text-muted-foreground')}>{status}</Badge>;
}

import { GanttChart, type GanttTask } from '@/components/ui/gantt-chart';

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const projectId = String(params?.projectId ?? '');

  const {
    selectedProject,
    epics,
    sprints,
    stories,
    subtasksByStoryId,
    commentsByStoryId,
    isLoading,
    error,
    fetchProjectById,
    fetchEpics,
    fetchSprints,
    fetchStories,
    createEpic,
    createSprint,
    createStory,
    fetchSubtasks,
    createSubtask,
    updateSubtask,
    fetchStoryComments,
    createStoryComment,
    clearError,
  } = useProjectManagementStore();

  const [activeTab, setActiveTab] = React.useState<'backlog' | 'sprints' | 'epics'>('backlog');

  const [createEpicOpen, setCreateEpicOpen] = React.useState(false);
  const [epicForm, setEpicForm] = React.useState({ subject: '', description: '' });

  const [createSprintOpen, setCreateSprintOpen] = React.useState(false);
  const [sprintForm, setSprintForm] = React.useState({ name: '', start_date: '', end_date: '' });

  const [createStoryOpen, setCreateStoryOpen] = React.useState(false);
  const [storyForm, setStoryForm] = React.useState({ subject: '', description: '', priority: 50, epic_id: '', sprint_id: '' });

  const [selectedStoryId, setSelectedStoryId] = React.useState<string | null>(null);
  const [subtaskText, setSubtaskText] = React.useState('');
  const [commentText, setCommentText] = React.useState('');

  const project: Project | null = selectedProject?.id === projectId ? selectedProject : null;

  React.useEffect(() => {
    if (!projectId) return;
    fetchProjectById(projectId);
    fetchEpics(projectId);
    fetchSprints(projectId);
    fetchStories(projectId);
  }, [projectId, fetchProjectById, fetchEpics, fetchSprints, fetchStories]);

  React.useEffect(() => {
    if (error) {
      toast({ title: 'Project Management Error', description: error, variant: 'destructive' });
      clearError();
    }
  }, [error, toast, clearError]);

  const refreshAll = async () => {
    await Promise.all([
      fetchProjectById(projectId),
      fetchEpics(projectId),
      fetchSprints(projectId),
      fetchStories(projectId),
    ]);
    toast({ title: 'Refreshed', description: 'Project data updated.' });
  };

  const onCreateEpic = async () => {
    if (!epicForm.subject.trim()) {
      toast({ title: 'Epic subject required', variant: 'destructive' });
      return;
    }
    await createEpic(projectId, epicForm.subject.trim(), epicForm.description.trim() || undefined);
    setEpicForm({ subject: '', description: '' });
    setCreateEpicOpen(false);
    toast({ title: 'Epic created' });
  };

  const onCreateSprint = async () => {
    if (!sprintForm.name.trim() || !sprintForm.start_date || !sprintForm.end_date) {
      toast({ title: 'Sprint name and dates required', variant: 'destructive' });
      return;
    }
    await createSprint(projectId, sprintForm.name.trim(), sprintForm.start_date, sprintForm.end_date);
    setSprintForm({ name: '', start_date: '', end_date: '' });
    setCreateSprintOpen(false);
    toast({ title: 'Sprint created' });
  };

  const onCreateStory = async () => {
    if (!storyForm.subject.trim()) {
      toast({ title: 'Story subject required', variant: 'destructive' });
      return;
    }
    await createStory({
      project_id: projectId,
      subject: storyForm.subject.trim(),
      description: storyForm.description.trim() || undefined,
      priority: storyForm.priority,
      epic_id: storyForm.epic_id || null,
      sprint_id: storyForm.sprint_id || null,
    });
    setStoryForm({ subject: '', description: '', priority: 50, epic_id: '', sprint_id: '' });
    setCreateStoryOpen(false);
    toast({ title: 'Story created' });
  };

  const selectStory = async (storyId: string) => {
    setSelectedStoryId(storyId);
    await Promise.all([fetchSubtasks(storyId), fetchStoryComments(storyId)]);
  };

  const onAddSubtask = async () => {
    if (!selectedStoryId) return;
    if (!subtaskText.trim()) {
      toast({ title: 'Subtask subject required', variant: 'destructive' });
      return;
    }
    await createSubtask(selectedStoryId, subtaskText.trim());
    setSubtaskText('');
  };

  const onAddComment = async () => {
    if (!selectedStoryId) return;
    if (!commentText.trim()) {
      toast({ title: 'Comment required', variant: 'destructive' });
      return;
    }
    await createStoryComment(selectedStoryId, commentText.trim());
    setCommentText('');
  };

  const storyList = stories.slice().sort((a, b) => a.ref - b.ref);

  const selectedStory = selectedStoryId ? storyList.find((s) => s.id === selectedStoryId) ?? null : null;
  const selectedSubtasks: Subtask[] = selectedStoryId ? (subtasksByStoryId[selectedStoryId] ?? []) : [];
  const selectedComments: StoryComment[] = selectedStoryId ? (commentsByStoryId[selectedStoryId] ?? []) : [];

  return (
    <div className="space-y-6" data-testid="pm-project-detail">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={() => router.push('/project-management')} aria-label="Back">
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              {project ? (
                <h1 className="text-2xl font-semibold tracking-tight" data-testid="pm-project-title">{project.name}</h1>
              ) : (
                <Skeleton className="h-7 w-64" />
              )}
              {project ? (
                <p className="text-sm text-muted-foreground">/{project.slug} • Updated {formatRelativeTime(project.updated_at)}</p>
              ) : (
                <Skeleton className="mt-2 h-4 w-72" />
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={refreshAll} data-testid="pm-refresh">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button onClick={() => setCreateStoryOpen(true)} data-testid="pm-create-story">
            <Plus className="mr-2 h-4 w-4" />
            New Story
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between">
            <span>Overview</span>
            {project ? <StatusBadge status={project.status} /> : null}
          </CardTitle>
          <CardDescription>
            Stories: {stories.length} • Epics: {epics.length} • Sprints: {sprints.length}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-md border p-3">
              <p className="text-xs text-muted-foreground">Backlog</p>
              <p className="mt-1 text-sm font-medium">{stories.length} stories</p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-xs text-muted-foreground">Epics</p>
              <p className="mt-1 text-sm font-medium">{epics.length} epics</p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-xs text-muted-foreground">Sprints</p>
              <p className="mt-1 text-sm font-medium">{sprints.length} sprints</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList>
          <TabsTrigger value="backlog" className="gap-2"><ListChecks className="h-4 w-4" />Backlog</TabsTrigger>
          <TabsTrigger value="sprints" className="gap-2"><CalendarDays className="h-4 w-4" />Sprints</TabsTrigger>
          <TabsTrigger value="epics" className="gap-2"><Layers className="h-4 w-4" />Epics</TabsTrigger>
          <TabsTrigger value="gantt" className="gap-2"><Clock className="h-4 w-4" />Gantt</TabsTrigger>
        </TabsList>

        <TabsContent value="backlog" className="mt-4">
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center justify-between">
                  <span>Stories</span>
                </CardTitle>
                <CardDescription>Select a story to manage subtasks and comments.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {isLoading && storyList.length === 0 && (
                  <div className="space-y-2">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                )}

                {!isLoading && storyList.length === 0 && (
                  <div className="rounded-lg border border-dashed p-10 text-center">
                    <p className="text-sm text-muted-foreground">No stories yet.</p>
                    <div className="mt-3">
                      <Button variant="outline" onClick={() => setCreateStoryOpen(true)}>
                        <Plus className="mr-2 h-4 w-4" />
                        Create first story
                      </Button>
                    </div>
                  </div>
                )}

                {storyList.map((s: UserStory) => (
                  <button
                    key={s.id}
                    onClick={() => selectStory(s.id)}
                    className={cn(
                      'w-full rounded-md border p-3 text-left transition-colors hover:bg-accent/40',
                      selectedStoryId === s.id && 'bg-accent'
                    )}
                    data-testid={`pm-story-${s.id}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">US-{s.ref} • {s.subject}</p>
                        <p className="text-xs text-muted-foreground">Priority {s.priority} • {s.status}</p>
                      </div>
                      <Badge variant="outline">{s.status}</Badge>
                    </div>
                    {s.description ? (
                      <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{s.description}</p>
                    ) : null}
                  </button>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center justify-between">
                  <span>Story Detail</span>
                  {selectedStory ? <Badge variant="secondary">US-{selectedStory.ref}</Badge> : null}
                </CardTitle>
                <CardDescription>
                  {selectedStory ? 'Manage subtasks and comments.' : 'Select a story.'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {!selectedStory && (
                  <div className="rounded-md border border-dashed p-6 text-center">
                    <p className="text-sm text-muted-foreground">No story selected.</p>
                  </div>
                )}

                {selectedStory && (
                  <>
                    <div className="space-y-1">
                      <p className="text-sm font-medium">{selectedStory.subject}</p>
                      <p className="text-xs text-muted-foreground">{selectedStory.status} • Priority {selectedStory.priority}</p>
                    </div>

                    <Separator />

                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">Subtasks</p>
                      <div className="space-y-2">
                        {selectedSubtasks.map((st) => (
                          <div key={st.id} className="flex items-center justify-between gap-2 rounded-md border p-2" data-testid={`pm-subtask-${st.id}`}>
                            <div className="flex items-center gap-2">
                              {st.is_closed ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                              ) : (
                                <Circle className="h-4 w-4 text-muted-foreground" />
                              )}
                              <div>
                                <p className="text-sm">ST-{st.ref} • {st.subject}</p>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              variant={st.is_closed ? 'outline' : 'default'}
                              onClick={() => updateSubtask(st.id, { is_closed: !st.is_closed })}
                              data-testid={`pm-subtask-toggle-${st.id}`}
                            >
                              {st.is_closed ? 'Reopen' : 'Close'}
                            </Button>
                          </div>
                        ))}
                      </div>

                      <div className="flex items-center gap-2">
                        <Input
                          value={subtaskText}
                          onChange={(e) => setSubtaskText(e.target.value)}
                          placeholder="Add subtask"
                          data-testid="pm-subtask-input"
                        />
                        <Button onClick={onAddSubtask} data-testid="pm-subtask-add">
                          <Plus className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>

                    <Separator />

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-medium text-muted-foreground">Comments</p>
                        <MessageSquare className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="space-y-2">
                        {selectedComments.length === 0 && (
                          <p className="text-xs text-muted-foreground">No comments yet.</p>
                        )}
                        {selectedComments.map((c) => (
                          <div key={c.id} className="rounded-md border p-2" data-testid={`pm-comment-${c.id}`}>
                            <p className="text-sm">{c.content}</p>
                            <p className="mt-1 text-xs text-muted-foreground">{formatRelativeTime(c.created_at)}</p>
                          </div>
                        ))}
                      </div>
                      <Textarea
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        placeholder="Write a comment"
                        rows={3}
                        data-testid="pm-comment-input"
                      />
                      <Button variant="outline" onClick={onAddComment} data-testid="pm-comment-add">
                        Add Comment
                      </Button>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="sprints" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center justify-between">
                <span>Sprints</span>
                <Button size="sm" onClick={() => setCreateSprintOpen(true)} data-testid="pm-create-sprint">
                  <Plus className="mr-2 h-4 w-4" />New Sprint
                </Button>
              </CardTitle>
              <CardDescription>Plan work in time-boxed iterations.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {sprints.length === 0 && (
                <p className="text-sm text-muted-foreground">No sprints yet.</p>
              )}
              {sprints.map((sp: Sprint) => (
                <div key={sp.id} className="rounded-md border p-3" data-testid={`pm-sprint-${sp.id}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium">{sp.name}</p>
                      <p className="text-xs text-muted-foreground">{sp.start_date} → {sp.end_date}</p>
                    </div>
                    <Badge variant="outline">{sp.status}</Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="epics" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center justify-between">
                <span>Epics</span>
                <Button size="sm" onClick={() => setCreateEpicOpen(true)} data-testid="pm-create-epic">
                  <Plus className="mr-2 h-4 w-4" />New Epic
                </Button>
              </CardTitle>
              <CardDescription>Group stories under high-level themes.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {epics.length === 0 && (
                <p className="text-sm text-muted-foreground">No epics yet.</p>
              )}
              {epics.map((e: Epic) => (
                <div key={e.id} className="rounded-md border p-3" data-testid={`pm-epic-${e.id}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium">E-{e.ref} • {e.subject}</p>
                      {e.description ? (
                        <p className="mt-1 text-sm text-muted-foreground">{e.description}</p>
                      ) : null}
                    </div>
                    <Badge variant="outline">{e.status}</Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="gantt" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Project Timeline (Gantt)</CardTitle>
              <CardDescription>Visual schedule of sprints and user stories.</CardDescription>
            </CardHeader>
            <CardContent>
              {sprints.length > 0 ? (
                <GanttChart 
                  tasks={sprints.map(sp => ({
                    id: sp.id,
                    name: sp.name,
                    start: new Date(sp.start_date),
                    end: new Date(sp.end_date),
                    progress: 0, // In production, calculate based on story completion
                    color: sp.status === 'closed' ? 'bg-muted' : 'bg-primary'
                  }))} 
                />
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  Create sprints to see them on the Gantt chart.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <Dialog open={createEpicOpen} onOpenChange={setCreateEpicOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="pm-epic-dialog">
          <DialogHeader>
            <DialogTitle>Create Epic</DialogTitle>
            <DialogDescription>Track a large theme spanning multiple stories.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label>Subject</Label>
              <Input value={epicForm.subject} onChange={(e) => setEpicForm((s) => ({ ...s, subject: e.target.value }))} data-testid="pm-epic-subject" />
            </div>
            <div className="grid gap-2">
              <Label>Description</Label>
              <Textarea value={epicForm.description} onChange={(e) => setEpicForm((s) => ({ ...s, description: e.target.value }))} rows={4} data-testid="pm-epic-description" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateEpicOpen(false)}>Cancel</Button>
            <Button onClick={onCreateEpic} data-testid="pm-epic-submit">Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={createSprintOpen} onOpenChange={setCreateSprintOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="pm-sprint-dialog">
          <DialogHeader>
            <DialogTitle>Create Sprint</DialogTitle>
            <DialogDescription>Create a time-boxed iteration for planned work.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label>Name</Label>
              <Input value={sprintForm.name} onChange={(e) => setSprintForm((s) => ({ ...s, name: e.target.value }))} data-testid="pm-sprint-name" />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label>Start date</Label>
                <Input type="date" value={sprintForm.start_date} onChange={(e) => setSprintForm((s) => ({ ...s, start_date: e.target.value }))} data-testid="pm-sprint-start" />
              </div>
              <div className="grid gap-2">
                <Label>End date</Label>
                <Input type="date" value={sprintForm.end_date} onChange={(e) => setSprintForm((s) => ({ ...s, end_date: e.target.value }))} data-testid="pm-sprint-end" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateSprintOpen(false)}>Cancel</Button>
            <Button onClick={onCreateSprint} data-testid="pm-sprint-submit">Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={createStoryOpen} onOpenChange={setCreateStoryOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="pm-story-dialog">
          <DialogHeader>
            <DialogTitle>Create Story</DialogTitle>
            <DialogDescription>Create a user story in this project.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label>Subject</Label>
              <Input value={storyForm.subject} onChange={(e) => setStoryForm((s) => ({ ...s, subject: e.target.value }))} data-testid="pm-story-subject" />
            </div>
            <div className="grid gap-2">
              <Label>Description</Label>
              <Textarea value={storyForm.description} onChange={(e) => setStoryForm((s) => ({ ...s, description: e.target.value }))} rows={4} data-testid="pm-story-description" />
            </div>
            <div className="grid gap-2">
              <Label>Priority (0-100)</Label>
              <Input
                type="number"
                min={0}
                max={100}
                value={storyForm.priority}
                onChange={(e) => setStoryForm((s) => ({ ...s, priority: Number(e.target.value || 0) }))}
                data-testid="pm-story-priority"
              />
            </div>
            <div className="text-xs text-muted-foreground">
              Optional: link to an epic or sprint from the Epics/Sprints tabs once created.
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateStoryOpen(false)}>Cancel</Button>
            <Button onClick={onCreateStory} data-testid="pm-story-submit">Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="text-xs text-muted-foreground">
        <Link href="/project-management" className="underline">Project list</Link>
      </div>
    </div>
  );
}
