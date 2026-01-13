'use client';

import * as React from 'react';
import { useProjectManagementStore, type UserStory, type Epic, type Subtask, type StoryComment } from '@/stores/project-management-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Plus, Search, ChevronRight, ChevronDown, Circle, CheckCircle2, MessageSquare, ListChecks } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { Separator } from '@/components/ui/separator';

interface BacklogViewProps {
  projectId: string;
}

const priorityColor = (priority: number): string => {
  if (priority >= 80) return '#ef4444';
  if (priority >= 60) return '#f97316';
  if (priority >= 40) return '#eab308';
  return '#9ca3af';
};

type ViewMode = 'list' | 'create' | 'detail';

export function BacklogView({ projectId }: BacklogViewProps) {
  const { 
    stories, epics, sprints, createStory, updateStory,
    subtasksByStoryId, commentsByStoryId,
    fetchSubtasks, createSubtask, updateSubtask,
    fetchStoryComments, createStoryComment
  } = useProjectManagementStore();
  
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedStory, setSelectedStory] = React.useState<UserStory | null>(null);
  const [isSheetOpen, setIsSheetOpen] = React.useState(false);
  const [viewMode, setViewMode] = React.useState<ViewMode>('list');
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // New Story Form State
  const [newStorySubject, setNewStorySubject] = React.useState('');
  const [newStoryDescription, setNewStoryDescription] = React.useState('');
  const [newStoryPriority, setNewStoryPriority] = React.useState('50');
  
  // Subtask and Comment form state
  const [newSubtaskSubject, setNewSubtaskSubject] = React.useState('');
  const [newCommentContent, setNewCommentContent] = React.useState('');

  const projectStories = stories.filter(s => s.project_id === projectId);
  const projectEpics = epics.filter(e => e.project_id === projectId);
  const projectSprints = sprints.filter(s => s.project_id === projectId);
  
  // Group by sprints (Active -> Planned -> Backlog)
  const activeSprint = projectSprints.find(s => s.status === 'active');
  const plannedSprints = projectSprints.filter(s => s.status === 'planned');
  
  const activeSprintStories = activeSprint ? projectStories.filter(s => s.sprint_id === activeSprint.id) : [];
  const plannedSprintStories = (sprintId: string) => projectStories.filter(s => s.sprint_id === sprintId);
  const backlogStories = projectStories.filter(s => !s.sprint_id);

  const handleCreateStory = async () => {
    if (!newStorySubject.trim()) return;

    setIsSubmitting(true);
    try {
      await createStory({
        project_id: projectId,
        subject: newStorySubject,
        description: newStoryDescription || undefined,
        priority: parseInt(newStoryPriority) || 50,
      });
      setNewStorySubject('');
      setNewStoryDescription('');
      setNewStoryPriority('50');
      setViewMode('list');
      setIsSheetOpen(false);
    } catch (error) {
      console.error('Failed to create story:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStoryClick = async (story: UserStory) => {
    setSelectedStory(story);
    setViewMode('detail');
    setIsSheetOpen(true);
    // Fetch subtasks and comments for this story
    await Promise.all([
      fetchSubtasks(story.id),
      fetchStoryComments(story.id)
    ]);
  };

  const handleOpenCreateStory = () => {
    setSelectedStory(null);
    setViewMode('create');
    setIsSheetOpen(true);
  };

  const handleUpdateStory = async (updates: Partial<UserStory>) => {
    if (!selectedStory) return;
    try {
      await updateStory(selectedStory.id, updates);
      setSelectedStory({ ...selectedStory, ...updates });
    } catch (error) {
      console.error('Failed to update story:', error);
    }
  };
  
  const handleAddSubtask = async () => {
    if (!selectedStory || !newSubtaskSubject.trim()) return;
    try {
      await createSubtask(selectedStory.id, newSubtaskSubject);
      setNewSubtaskSubject('');
    } catch (error) {
      console.error('Failed to create subtask:', error);
    }
  };
  
  const handleToggleSubtask = async (subtask: Subtask) => {
    try {
      await updateSubtask(subtask.id, { is_closed: !subtask.is_closed });
    } catch (error) {
      console.error('Failed to toggle subtask:', error);
    }
  };
  
  const handleAddComment = async () => {
    if (!selectedStory || !newCommentContent.trim()) return;
    try {
      await createStoryComment(selectedStory.id, newCommentContent);
      setNewCommentContent('');
    } catch (error) {
      console.error('Failed to add comment:', error);
    }
  };
  
  const currentSubtasks = selectedStory ? (subtasksByStoryId[selectedStory.id] || []) : [];
  const currentComments = selectedStory ? (commentsByStoryId[selectedStory.id] || []) : [];

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Backlog</h2>
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input 
              placeholder="Search stories..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 w-[250px]" 
            />
          </div>
          <Button data-testid="pm-create-story" onClick={handleOpenCreateStory}>
            <Plus className="mr-2 h-4 w-4" /> Create Story
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 h-[calc(100vh-200px)] pr-4">
        {/* Active Sprint Section */}
        {activeSprint && (
          <div className="mb-6 space-y-2">
            <div className="flex items-center justify-between bg-secondary/30 p-2 rounded-md">
              <div className="flex items-center font-semibold">
                <ChevronDown className="h-4 w-4 mr-2" />
                {activeSprint.name} <Badge className="ml-2" variant="default">Active</Badge>
              </div>
              <div className="text-sm text-muted-foreground mr-4">
                {activeSprintStories.length} stories
              </div>
            </div>
            <div className="space-y-1 pl-2">
              {activeSprintStories.length === 0 && (
                <p className="text-sm text-muted-foreground py-2 pl-6">No stories in active sprint.</p>
              )}
              {activeSprintStories.map(story => (
                <StoryItem key={story.id} story={story} onClick={() => handleStoryClick(story)} epics={projectEpics} />
              ))}
            </div>
          </div>
        )}

        {/* Planned Sprints */}
        {plannedSprints.map(sprint => (
          <div key={sprint.id} className="mb-6 space-y-2">
            <div className="flex items-center justify-between bg-secondary/30 p-2 rounded-md">
              <div className="flex items-center font-semibold">
                <ChevronRight className="h-4 w-4 mr-2" />
                {sprint.name} <span className="text-muted-foreground font-normal text-xs ml-2">Planned</span>
              </div>
              <div className="text-sm text-muted-foreground mr-4">
                {plannedSprintStories(sprint.id).length} stories
              </div>
            </div>
            <div className="space-y-1 pl-2">
              {plannedSprintStories(sprint.id).map(story => (
                <StoryItem key={story.id} story={story} onClick={() => handleStoryClick(story)} epics={projectEpics} />
              ))}
            </div>
          </div>
        ))}

        {/* Backlog Section */}
        <div className="mb-6 space-y-2">
          <div className="flex items-center justify-between bg-secondary/30 p-2 rounded-md">
            <div className="flex items-center font-semibold">
              <ChevronDown className="h-4 w-4 mr-2" />
              Backlog
            </div>
            <div className="text-sm text-muted-foreground mr-4">
              {backlogStories.length} stories
            </div>
          </div>
          <div className="space-y-1 pl-2">
            {backlogStories.map(story => (
              <StoryItem key={story.id} story={story} onClick={() => handleStoryClick(story)} epics={projectEpics} />
            ))}
          </div>
        </div>
      </ScrollArea>

      {/* Story Sheet - Create or Detail */}
      <Sheet open={isSheetOpen} onOpenChange={(open) => {
        setIsSheetOpen(open);
        if (!open) {
          setViewMode('list');
          setSelectedStory(null);
        }
      }}>
        <SheetContent className="w-[500px] sm:max-w-[540px] overflow-y-auto">
          {viewMode === 'create' && (
            <>
              <SheetHeader>
                <SheetTitle>Create New Story</SheetTitle>
                <SheetDescription>Add a new user story to the backlog.</SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Subject *</label>
                  <Input 
                    placeholder="As a user, I want..."
                    value={newStorySubject}
                    onChange={(e) => setNewStorySubject(e.target.value)}
                    data-testid="pm-story-subject"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Description</label>
                  <Textarea 
                    placeholder="Detailed description..."
                    value={newStoryDescription}
                    onChange={(e) => setNewStoryDescription(e.target.value)}
                    rows={4}
                    data-testid="pm-story-description"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Priority (0-100)</label>
                  <Input 
                    type="number"
                    min={0}
                    max={100}
                    value={newStoryPriority}
                    onChange={(e) => setNewStoryPriority(e.target.value)}
                    data-testid="pm-story-priority"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-4">
                  <Button variant="outline" onClick={() => setIsSheetOpen(false)}>Cancel</Button>
                  <Button onClick={handleCreateStory} disabled={isSubmitting} data-testid="pm-story-submit">
                    {isSubmitting ? 'Creating...' : 'Create Story'}
                  </Button>
                </div>
              </div>
            </>
          )}
          
          {viewMode === 'detail' && selectedStory && (
            <>
              <SheetHeader>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline">US-{selectedStory.ref}</Badge>
                  <Badge>{selectedStory.status.replace('_', ' ')}</Badge>
                </div>
                <SheetTitle className="text-xl">{selectedStory.subject}</SheetTitle>
              </SheetHeader>
              
              <div className="mt-6 space-y-6">
                {/* Description */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Description</label>
                  <Textarea 
                    placeholder="Add a description..."
                    defaultValue={selectedStory.description ?? ''}
                    onBlur={(e) => handleUpdateStory({ description: e.target.value })}
                    rows={3}
                    data-testid="pm-story-description"
                  />
                </div>
                
                {/* Priority & Epic */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Priority</label>
                    <Input 
                      type="number"
                      min={0}
                      max={100}
                      defaultValue={selectedStory.priority}
                      onBlur={(e) => handleUpdateStory({ priority: parseInt(e.target.value) || 50 })}
                      data-testid="pm-story-priority"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Epic</label>
                    <Select 
                      defaultValue={selectedStory.epic_id ?? ''}
                      onValueChange={(value) => handleUpdateStory({ epic_id: value || null })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="No epic" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">No epic</SelectItem>
                        {projectEpics.map(epic => (
                          <SelectItem key={epic.id} value={epic.id}>EP-{epic.ref}: {epic.subject}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Sprint */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Sprint</label>
                  <Select 
                    defaultValue={selectedStory.sprint_id ?? ''}
                    onValueChange={(value) => handleUpdateStory({ sprint_id: value || null })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Backlog" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Backlog</SelectItem>
                      {projectSprints.map(sprint => (
                        <SelectItem key={sprint.id} value={sprint.id}>{sprint.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Separator />

                {/* Subtasks Section */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <ListChecks className="h-4 w-4" />
                    <h3 className="font-medium">Subtasks</h3>
                    <Badge variant="secondary">{currentSubtasks.length}</Badge>
                  </div>
                  
                  <div className="space-y-2">
                    {currentSubtasks.map((subtask) => (
                      <div key={subtask.id} className="flex items-center gap-2 p-2 border rounded-md">
                        <button
                          onClick={() => handleToggleSubtask(subtask)}
                          className="focus:outline-none"
                          data-testid={`pm-subtask-toggle-${subtask.ref}`}
                        >
                          {subtask.is_closed ? (
                            <CheckCircle2 className="h-5 w-5 text-green-600" />
                          ) : (
                            <Circle className="h-5 w-5 text-muted-foreground" />
                          )}
                        </button>
                        <span className={cn("flex-1 text-sm", subtask.is_closed && "line-through text-muted-foreground")}>
                          ST-{subtask.ref}: {subtask.subject}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {subtask.is_closed ? 'Reopen' : 'Close'}
                        </span>
                      </div>
                    ))}
                    
                    <div className="flex items-center gap-2">
                      <Input 
                        placeholder="Add subtask..."
                        value={newSubtaskSubject}
                        onChange={(e) => setNewSubtaskSubject(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleAddSubtask()}
                        data-testid="pm-subtask-input"
                      />
                      <Button size="sm" onClick={handleAddSubtask} data-testid="pm-subtask-add">
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Comments Section */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" />
                    <h3 className="font-medium">Comments</h3>
                    <Badge variant="secondary">{currentComments.length}</Badge>
                  </div>
                  
                  <div className="space-y-3">
                    {currentComments.map((comment) => (
                      <div key={comment.id} className="p-3 bg-secondary/30 rounded-md">
                        <p className="text-sm">{comment.content}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(comment.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    ))}
                    
                    <div className="flex items-start gap-2">
                      <Textarea 
                        placeholder="Add a comment..."
                        value={newCommentContent}
                        onChange={(e) => setNewCommentContent(e.target.value)}
                        rows={2}
                        data-testid="pm-comment-input"
                      />
                      <Button size="sm" onClick={handleAddComment} data-testid="pm-comment-add">
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

interface StoryItemProps {
  story: UserStory;
  onClick: () => void;
  epics: Epic[];
}

function StoryItem({ story, onClick, epics }: StoryItemProps) {
  const epic = epics.find(e => e.id === story.epic_id);

  return (
    <div 
      className="flex items-center justify-between py-2 px-3 rounded-md hover:bg-accent cursor-pointer group"
      onClick={onClick}
    >
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <Circle className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        <span className="text-sm truncate">{story.subject}</span>
        {epic && (
          <Badge variant="outline" className="text-[10px] h-4 px-1 py-0 flex-shrink-0">
            EP-{epic.ref}
          </Badge>
        )}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-muted-foreground uppercase">US-{story.ref}</span>
        <div 
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: priorityColor(story.priority) }}
          title={`Priority: ${story.priority}`}
        />
      </div>
    </div>
  );
}
