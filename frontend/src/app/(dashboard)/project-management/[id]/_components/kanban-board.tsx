'use client';

import * as React from 'react';
import { useProjectManagementStore, type UserStory, type UserStoryStatus } from '@/stores/project-management-store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';

interface KanbanBoardProps {
  projectId: string;
}

const COLUMNS: { id: UserStoryStatus; title: string }[] = [
  { id: 'new', title: 'New' },
  { id: 'ready', title: 'Ready' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'ready_for_test', title: 'Ready for Test' },
  { id: 'done', title: 'Done' },
];

const priorityColor = (priority: number): string => {
  if (priority >= 80) return 'bg-red-500';
  if (priority >= 60) return 'bg-orange-500';
  if (priority >= 40) return 'bg-yellow-500';
  return 'bg-gray-400';
};

export function KanbanBoard({ projectId }: KanbanBoardProps) {
  const { stories, updateStoryStatus, selectedProject } = useProjectManagementStore();

  const columns = React.useMemo(() => {
    if (selectedProject?.custom_user_story_statuses && selectedProject.custom_user_story_statuses.length > 0) {
      return selectedProject.custom_user_story_statuses.map(s => ({
        id: s.id as UserStoryStatus,
        title: s.name,
        color: s.color
      }));
    }
    return COLUMNS;
  }, [selectedProject]);

  const projectStories = React.useMemo(() => 
    stories.filter(s => s.project_id === projectId && s.status !== 'archived'),
  [stories, projectId]);

  const handleDrop = async (storyId: string, newStatus: UserStoryStatus) => {
    try {
      await updateStoryStatus(storyId, newStatus);
    } catch (error) {
      console.error('Failed to update story status:', error);
    }
  };

  return (
    <div className="h-full overflow-x-auto">
      <div className="flex h-full gap-4 min-w-[1000px] pb-4">
        {columns.map((col) => (
          <BoardColumn
            key={col.id}
            column={col}
            stories={projectStories.filter((s) => s.status === col.id)}
            onDrop={handleDrop}
          />
        ))}
      </div>
    </div>
  );
}

interface BoardColumnProps {
  column: { id: UserStoryStatus; title: string };
  stories: UserStory[];
  onDrop: (storyId: string, newStatus: UserStoryStatus) => void;
}

function BoardColumn({ column, stories, onDrop }: BoardColumnProps) {
  const [isDragOver, setIsDragOver] = React.useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const storyId = e.dataTransfer.getData('storyId');
    if (storyId) {
      onDrop(storyId, column.id);
    }
  };

  return (
    <div
      className={cn(
        'flex h-full w-80 flex-col rounded-lg bg-secondary/50 border border-border transition-colors',
        isDragOver && 'border-primary bg-primary/10'
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="p-4 flex items-center justify-between border-b bg-background/50 rounded-t-lg">
        <h3 className="font-semibold">{column.title}</h3>
        <Badge variant="secondary">{stories.length}</Badge>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        <div className="flex flex-col gap-2">
          {stories.map((story) => (
            <StoryCard key={story.id} story={story} />
          ))}
        </div>
        {stories.length === 0 && (
          <div className="h-24 flex items-center justify-center text-muted-foreground text-sm border-2 border-dashed rounded-lg m-2">
            Drop here
          </div>
        )}
      </div>
    </div>
  );
}

function StoryCard({ story }: { story: UserStory }) {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('storyId', story.id);
  };

  return (
    <Card
      className="cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow"
      draggable
      onDragStart={handleDragStart}
    >
      <CardHeader className="p-3 space-y-0 pb-2">
        <div className="flex justify-between items-start gap-2">
          <CardTitle className="text-sm font-medium leading-tight">
            {story.subject}
          </CardTitle>
          <GripVertical className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        </div>
      </CardHeader>
      <CardContent className="p-3 pt-0">
        <div className="flex items-center justify-between mt-2">
          <Badge variant="outline" className="text-[10px] px-1 py-0 h-5">
            US-{story.ref}
          </Badge>
          <div className="flex items-center gap-1">
            <div className={cn('w-2 h-2 rounded-full', priorityColor(story.priority))} title={`Priority: ${story.priority}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
