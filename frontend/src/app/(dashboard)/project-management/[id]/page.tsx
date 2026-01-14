'use client';

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useProjectManagementStore } from '@/stores/project-management-store';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Calendar, Layout, ListTodo, Layers, AlertCircle, Settings, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

import { EpicsList } from './_components/epics-list';
import { SprintList } from './_components/sprint-list';
import { BacklogView } from './_components/backlog-view';
import { KanbanBoard } from './_components/kanban-board';
import { IssuesList } from './_components/issues-list';
import { WikiView } from './_components/wiki-view';
import { ProjectSettings } from './_components/project-settings';

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const projectId = params.id as string;

  const {
    selectedProject,
    fetchProjectById,
    fetchEpics,
    fetchSprints,
    fetchStories,
    isLoading,
    error,
    clearError,
  } = useProjectManagementStore();

  React.useEffect(() => {
    if (projectId) {
      fetchProjectById(projectId);
      fetchEpics(projectId);
      fetchSprints(projectId);
      fetchStories(projectId);
    }
  }, [projectId, fetchProjectById, fetchEpics, fetchSprints, fetchStories]);

  React.useEffect(() => {
    if (error) {
      toast({
        title: 'Error loading project',
        description: error,
        variant: 'destructive',
      });
      clearError();
    }
  }, [error, toast, clearError]);

  if (isLoading && !selectedProject) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-24" />
          </div>
        </div>
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (!selectedProject && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] gap-4">
        <h2 className="text-2xl font-bold">Project Not Found</h2>
        <Button onClick={() => router.push('/project-management')}>Back to Projects</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="pm-project-detail">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push('/project-management')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{selectedProject?.name}</h1>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>{selectedProject?.slug}</span>
              <span>•</span>
              <Badge variant="outline" className="capitalize">
                {selectedProject?.status.replace('_', ' ')}
              </Badge>
              <span>•</span>
              <span className="capitalize">{selectedProject?.project_type}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
            {/* Action buttons could go here */}
        </div>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="board" className="space-y-4">
        <TabsList>
            <TabsTrigger value="board" className="gap-2">
                <Layout className="h-4 w-4" /> Board
            </TabsTrigger>
            <TabsTrigger value="backlog" className="gap-2">
                <ListTodo className="h-4 w-4" /> Backlog
            </TabsTrigger>
            <TabsTrigger value="sprints" className="gap-2">
                <Calendar className="h-4 w-4" /> Sprints
            </TabsTrigger>
            <TabsTrigger value="epics" className="gap-2">
                <Layers className="h-4 w-4" /> Epics
            </TabsTrigger>
            {selectedProject?.enable_issues !== false && (
              <TabsTrigger value="issues" className="gap-2">
                  <AlertCircle className="h-4 w-4" /> Issues
              </TabsTrigger>
            )}
            {selectedProject?.enable_wiki !== false && (
              <TabsTrigger value="wiki" className="gap-2">
                  <FileText className="h-4 w-4" /> Wiki
              </TabsTrigger>
            )}
            <TabsTrigger value="settings" className="gap-2">
                <Settings className="h-4 w-4" /> Settings
            </TabsTrigger>
        </TabsList>

        <TabsContent value="board" className="space-y-4">
            <KanbanBoard projectId={projectId} />
        </TabsContent>

        <TabsContent value="backlog" className="space-y-4">
            <BacklogView projectId={projectId} />
        </TabsContent>

        <TabsContent value="sprints" className="space-y-4">
             <SprintList projectId={projectId} />
        </TabsContent>

        <TabsContent value="epics" className="space-y-4">
            <EpicsList projectId={projectId} />
        </TabsContent>

        <TabsContent value="issues" className="space-y-4">
            <IssuesList projectId={projectId} />
        </TabsContent>

        <TabsContent value="wiki" className="space-y-4">
            <WikiView projectId={projectId} />
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
            <ProjectSettings projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
