'use client';

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useProjectManagementStore } from '@/stores/project-management-store';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Calendar, Layout, ListTodo, Layers, AlertCircle, Settings, FileText, Flag, History, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

import { EpicsList } from './_components/epics-list';
import { SprintList } from './_components/sprint-list';
import { BacklogView } from './_components/backlog-view';
import { KanbanBoard } from './_components/kanban-board';
import { IssuesList } from './_components/issues-list';
import { WikiView } from './_components/wiki-view';
import { ProjectSettings } from './_components/project-settings';
import { MilestonesList } from './_components/milestones-list';
import { ProjectActivityTimeline } from './_components/project-activity';
import { ProjectDashboard } from './_components/project-dashboard';

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
    fetchIssues,
    fetchMilestones,
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
      fetchIssues(projectId);
      fetchMilestones(projectId);
    }
  }, [projectId, fetchProjectById, fetchEpics, fetchSprints, fetchStories, fetchIssues, fetchMilestones]);

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
      <Tabs defaultValue="dashboard" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1 bg-transparent p-0">
            <TabsTrigger value="dashboard" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border">
                <BarChart3 className="h-4 w-4" /> Dashboard
            </TabsTrigger>
            <TabsTrigger value="board" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border">
                <Layout className="h-4 w-4" /> Board
            </TabsTrigger>
            <TabsTrigger value="backlog" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border">
                <ListTodo className="h-4 w-4" /> Backlog
            </TabsTrigger>
            <TabsTrigger value="sprints" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border">
                <Calendar className="h-4 w-4" /> Sprints
            </TabsTrigger>
            <TabsTrigger value="epics" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border">
                <Layers className="h-4 w-4" /> Epics
            </TabsTrigger>
            <TabsTrigger value="milestones" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border">
                <Flag className="h-4 w-4" /> Milestones
            </TabsTrigger>
            {selectedProject?.enable_issues !== false && (
              <TabsTrigger value="issues" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border">
                  <AlertCircle className="h-4 w-4" /> Issues
              </TabsTrigger>
            )}
            {selectedProject?.enable_wiki !== false && (
              <TabsTrigger value="wiki" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border">
                  <FileText className="h-4 w-4" /> Wiki
              </TabsTrigger>
            )}
            <TabsTrigger value="activity" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border">
                <History className="h-4 w-4" /> Activity
            </TabsTrigger>
            <TabsTrigger value="settings" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border">
                <Settings className="h-4 w-4" /> Settings
            </TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard" className="space-y-4 outline-none">
            <ProjectDashboard projectId={projectId} />
        </TabsContent>

        <TabsContent value="board" className="space-y-4 outline-none">
            <KanbanBoard projectId={projectId} />
        </TabsContent>

        <TabsContent value="backlog" className="space-y-4 outline-none">
            <BacklogView projectId={projectId} />
        </TabsContent>

        <TabsContent value="sprints" className="space-y-4 outline-none">
             <SprintList projectId={projectId} />
        </TabsContent>

        <TabsContent value="epics" className="space-y-4 outline-none">
            <EpicsList projectId={projectId} />
        </TabsContent>

        <TabsContent value="milestones" className="space-y-4 outline-none">
            <MilestonesList projectId={projectId} />
        </TabsContent>

        <TabsContent value="issues" className="space-y-4 outline-none">
            <IssuesList projectId={projectId} />
        </TabsContent>

        <TabsContent value="wiki" className="space-y-4 outline-none">
            <WikiView projectId={projectId} />
        </TabsContent>

        <TabsContent value="activity" className="space-y-4 outline-none">
            <ProjectActivityTimeline projectId={projectId} />
        </TabsContent>

        <TabsContent value="settings" className="space-y-4 outline-none">
            <ProjectSettings projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
