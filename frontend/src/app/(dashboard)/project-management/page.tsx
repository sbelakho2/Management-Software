'use client';

import * as React from 'react';
import Link from 'next/link';
import { Plus, Search, FolderKanban, Lock, Globe } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { cn, formatRelativeTime } from '@/lib/utils';
import { useProjectManagementStore, type Project, type ProjectStatus, type ProjectType } from '@/stores/project-management-store';

const statusTone: Record<ProjectStatus, { label: string; className: string }> = {
  planning: { label: 'Planning', className: 'bg-muted text-muted-foreground' },
  active: { label: 'Active', className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-100' },
  on_hold: { label: 'On Hold', className: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100' },
  completed: { label: 'Completed', className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100' },
  archived: { label: 'Archived', className: 'bg-gray-200 text-gray-700 dark:bg-gray-800 dark:text-gray-200' },
  cancelled: { label: 'Cancelled', className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100' },
};

const typeLabel: Record<ProjectType, string> = {
  standard: 'Standard',
  scrum: 'Scrum',
  kanban: 'Kanban',
  hybrid: 'Hybrid',
  npi: 'NPI',
  kaizen: 'Kaizen',
  a3: 'A3',
  maintenance: 'Maintenance',
};

import { BarChart, CHART_TYPE } from '@/components/ui/data-visualization';

export default function ProjectManagementPage() {
  const { toast } = useToast();
  const {
    projects: projectsRaw,
    isLoading,
    error,
    fetchProjects,
    createProject,
    clearError,
  } = useProjectManagementStore();

  const projects = projectsRaw ?? [];

  const [view, setView] = React.useState<'list' | 'portfolio'>('list');
  const [query, setQuery] = React.useState('');
  const [createOpen, setCreateOpen] = React.useState(false);
  const [createForm, setCreateForm] = React.useState({
    name: '',
    description: '',
    project_type: 'standard' as ProjectType,
    status: 'planning' as ProjectStatus,
    is_private: false,
  });

  React.useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  React.useEffect(() => {
    if (error) {
      toast({
        title: 'Project Management Error',
        description: error,
        variant: 'destructive',
      });
      clearError();
    }
  }, [error, toast, clearError]);

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return projects;
    return projects.filter((p) =>
      p.name.toLowerCase().includes(q) ||
      p.slug.toLowerCase().includes(q) ||
      (p.description ?? '').toLowerCase().includes(q)
    );
  }, [projects, query]);

  const onSubmitCreate = async () => {
    if (!createForm.name.trim()) {
      toast({ title: 'Project name required', variant: 'destructive' });
      return;
    }
    try {
      const created = await createProject({
        name: createForm.name.trim(),
        description: createForm.description.trim() || null,
        project_type: createForm.project_type,
        status: createForm.status,
        is_private: createForm.is_private,
      });
      toast({ title: 'Project created', description: created.name });
      setCreateOpen(false);
      setCreateForm({ name: '', description: '', project_type: 'standard', status: 'planning', is_private: false });
    } catch {
      // error already handled by store + toast
    }
  };

  return (
    <div className="space-y-6" data-testid="pm-page">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Project Management</h1>
          <p className="text-sm text-muted-foreground">
            Projects, epics, sprints, and stories integrated across Sensei OS.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Tabs value={view} onValueChange={(v) => setView(v as any)} className="w-[200px]">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="list">List</TabsTrigger>
              <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
            </TabsList>
          </Tabs>
          <Button onClick={() => setCreateOpen(true)} data-testid="pm-create-project">
            <Plus className="mr-2 h-4 w-4" /> New Project
          </Button>
        </div>
      </div>

      {view === 'portfolio' ? (
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Projects by Status</CardTitle>
              <CardDescription>High-level portfolio distribution</CardDescription>
            </CardHeader>
            <CardContent>
              <BarChart 
                data={[
                  { label: 'Planning', value: projects.filter(p => p.status === 'planning').length, color: '#94a3b8' },
                  { label: 'Active', value: projects.filter(p => p.status === 'active').length, color: '#10b981' },
                  { label: 'On Hold', value: projects.filter(p => p.status === 'on_hold').length, color: '#f59e0b' },
                  { label: 'Completed', value: projects.filter(p => p.status === 'completed').length, color: '#3b82f6' },
                ]}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Health</CardTitle>
              <CardDescription>Aggregated project status</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col justify-center items-center h-[200px]">
              <div className="text-4xl font-bold text-success">
                {projects.length > 0 ? Math.round((projects.filter(p => p.status === 'active' || p.status === 'completed').length / projects.length) * 100) : 0}%
              </div>
              <p className="text-muted-foreground mt-2">Healthy / Completed Ratio</p>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <FolderKanban className="h-5 w-5" />
              Projects
            </CardTitle>
            <CardDescription>Search, open, and manage your workspaces.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search projects by name, slug, or description"
                  className="pl-9"
                  data-testid="pm-search"
                />
              </div>
            </div>

          {isLoading && (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, idx) => (
                <Card key={idx} className="p-4">
                  <Skeleton className="h-5 w-48" />
                  <Skeleton className="mt-3 h-4 w-full" />
                  <Skeleton className="mt-2 h-4 w-2/3" />
                </Card>
              ))}
            </div>
          )}

          {!isLoading && filtered.length === 0 && (
            <div className="rounded-lg border border-dashed p-10 text-center">
              <p className="text-sm text-muted-foreground">No projects match your search.</p>
              <div className="mt-3">
                <Button variant="outline" onClick={() => setCreateOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create your first project
                </Button>
              </div>
            </div>
          )}

          {!isLoading && filtered.length > 0 && (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="pm-project-grid">
              {filtered.map((p: Project) => {
                const tone = statusTone[p.status];
                return (
                  <Link key={p.id} href={`/project-management/${p.id}`} className="block">
                    <Card className="h-full transition-colors hover:bg-accent/40" data-testid={`pm-project-${p.id}`}>
                      <CardHeader className="pb-2">
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1">
                            <CardTitle className="text-base leading-5">{p.name}</CardTitle>
                            <p className="text-xs text-muted-foreground">/{p.slug}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {p.is_private ? (
                              <Badge variant="secondary" className="gap-1">
                                <Lock className="h-3 w-3" /> Private
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="gap-1">
                                <Globe className="h-3 w-3" /> Shared
                              </Badge>
                            )}
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex flex-wrap gap-2">
                          <Badge className={cn('border', tone.className)}>{tone.label}</Badge>
                          <Badge variant="outline">{typeLabel[p.project_type]}</Badge>
                        </div>
                        {p.description ? (
                          <p className="line-clamp-2 text-sm text-muted-foreground">{p.description}</p>
                        ) : (
                          <p className="text-sm text-muted-foreground">No description</p>
                        )}
                        <p className="text-xs text-muted-foreground">
                          Updated {formatRelativeTime(p.updated_at)}
                        </p>
                      </CardContent>
                    </Card>
                  </Link>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="pm-create-dialog">
          <DialogHeader>
            <DialogTitle>Create Project</DialogTitle>
            <DialogDescription>
              Create a new project workspace for stories, sprints, epics, and cross-module work.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="pm-name">Name</Label>
              <Input
                id="pm-name"
                value={createForm.name}
                onChange={(e) => setCreateForm((s) => ({ ...s, name: e.target.value }))}
                placeholder="e.g., NPI - Wing Bracket"
                data-testid="pm-create-name"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="pm-desc">Description</Label>
              <Textarea
                id="pm-desc"
                value={createForm.description}
                onChange={(e) => setCreateForm((s) => ({ ...s, description: e.target.value }))}
                placeholder="Scope, objectives, and key deliverables"
                rows={4}
                data-testid="pm-create-description"
              />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label>Type</Label>
                <Select
                  value={createForm.project_type}
                  onValueChange={(v) => setCreateForm((s) => ({ ...s, project_type: v as ProjectType }))}
                >
                  <SelectTrigger data-testid="pm-create-type">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(typeLabel).map(([k, lbl]) => (
                      <SelectItem key={k} value={k}>
                        {lbl}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label>Status</Label>
                <Select
                  value={createForm.status}
                  onValueChange={(v) => setCreateForm((s) => ({ ...s, status: v as ProjectStatus }))}
                >
                  <SelectTrigger data-testid="pm-create-status">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(statusTone).map(([k, v]) => (
                      <SelectItem key={k} value={k}>
                        {v.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center justify-between rounded-md border p-3">
              <div>
                <p className="text-sm font-medium">Visibility</p>
                <p className="text-xs text-muted-foreground">Private projects require membership for access.</p>
              </div>
              <Button
                type="button"
                variant={createForm.is_private ? 'default' : 'outline'}
                onClick={() => setCreateForm((s) => ({ ...s, is_private: !s.is_private }))}
                data-testid="pm-create-visibility"
              >
                {createForm.is_private ? 'Private' : 'Shared'}
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={onSubmitCreate} data-testid="pm-create-submit">
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
