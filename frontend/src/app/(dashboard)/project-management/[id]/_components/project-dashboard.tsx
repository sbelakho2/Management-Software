'use client';

import * as React from 'react';
import { useProjectManagementStore, type Project } from '@/stores/project-management-store';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { 
  BarChart, 
  DonutChart as PieChart,
  CHART_TYPE 
} from '@/components/ui/data-visualization';
import { 
  CheckCircle2, 
  AlertCircle, 
  Trophy, 
  Target, 
  Clock, 
  Zap,
  Layout
} from 'lucide-react';

interface ProjectDashboardProps {
  projectId: string;
}

export function ProjectDashboard({ projectId }: ProjectDashboardProps) {
  const { selectedProject: project, sprints, stories, issues } = useProjectManagementStore();

  if (!project) return null;

  const progress = project.progress_percentage ?? 0;
  const activeSprint = sprints.find(s => s.status === 'active');
  // Sprint doesn't have point tracking properties; calculate from stories if needed
  const sprintStories = activeSprint ? stories.filter(s => s.sprint_id === activeSprint.id) : [];
  const completedPoints = sprintStories.filter(s => s.status === 'done').reduce((sum, s) => sum + (s.estimated_hours || 0), 0);
  const plannedPoints = sprintStories.reduce((sum, s) => sum + (s.estimated_hours || 0), 0);
  const sprintProgress = plannedPoints > 0 ? (completedPoints / plannedPoints) * 100 : 0;

  // Data for Story Distribution
  const storyStatusData = [
    { label: 'New', value: stories.filter(s => s.status === 'new').length, color: '#94a3b8' },
    { label: 'In Progress', value: stories.filter(s => s.status === 'in_progress').length, color: '#3b82f6' },
    { label: 'Testing', value: stories.filter(s => s.status === 'ready_for_test').length, color: '#f59e0b' },
    { label: 'Done', value: stories.filter(s => s.status === 'done').length, color: '#10b981' },
  ];

  // Data for Issue Severity
  const issueSeverityData = [
    { label: 'Critical', value: issues.filter(i => i.severity === 'critical').length, color: '#ef4444' },
    { label: 'Important', value: issues.filter(i => i.severity === 'important').length, color: '#f97316' },
    { label: 'Normal', value: issues.filter(i => i.severity === 'normal').length, color: '#eab308' },
    { label: 'Minor', value: issues.filter(i => i.severity === 'minor').length, color: '#3b82f6' },
  ];

  return (
    <div className="space-y-6">
      {/* Top Stats Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Overall Progress</CardTitle>
            <Trophy className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(progress)}%</div>
            <Progress value={progress} className="mt-3 h-2" />
            <p className="text-xs text-muted-foreground mt-2">
              {project.completed_user_stories} of {project.total_user_stories} stories done
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Story Points</CardTitle>
            <Target className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{project.completed_story_points} / {project.total_story_points}</div>
            <p className="text-xs text-muted-foreground mt-2">
              Velocity Tracking Enabled
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Active Sprint</CardTitle>
            <Zap className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            {activeSprint ? (
              <>
                <div className="text-lg font-bold truncate" title={activeSprint.name}>{activeSprint.name}</div>
                <div className="flex justify-between items-center mt-2 text-xs">
                  <span>{completedPoints} / {plannedPoints} pts</span>
                  <span className="font-semibold">{Math.round(sprintProgress)}%</span>
                </div>
                <Progress value={sprintProgress} className="mt-2 h-1.5" />
              </>
            ) : (
              <div className="text-sm text-muted-foreground italic py-2">No active sprint</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Open Issues</CardTitle>
            <AlertCircle className={issues.length > 0 ? "h-4 w-4 text-danger" : "h-4 w-4 text-muted-foreground"} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{project.open_issues}</div>
            <p className="text-xs text-muted-foreground mt-2">
              {issues.filter(i => i.severity === 'critical' || i.severity === 'important').length} high priority
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Story Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Work Distribution</CardTitle>
            <CardDescription>Stories by workflow status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[250px] w-full">
              <PieChart 
                data={storyStatusData}
              />
            </div>
          </CardContent>
        </Card>

        {/* Issue Severity */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Issue Severity</CardTitle>
            <CardDescription>Risk profile of reported issues</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[250px] w-full">
              <BarChart 
                data={issueSeverityData}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Integration Links */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Project Context</CardTitle>
          <CardDescription>Links to other Sensei OS modules</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {project.owner_id && (
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold text-muted-foreground">Owner</span>
                <Badge variant="secondary">Admin User</Badge>
              </div>
            )}
            <div className="flex flex-col gap-1">
              <span className="text-[10px] uppercase font-bold text-muted-foreground">Project Type</span>
              <Badge variant="outline" className="capitalize">{project.project_type}</Badge>
            </div>
            {project.start_date && (
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold text-muted-foreground">Timeline</span>
                <div className="text-xs font-medium">
                  {new Date(project.start_date).toLocaleDateString()} 
                  {project.target_end_date && ` — ${new Date(project.target_end_date).toLocaleDateString()}`}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
