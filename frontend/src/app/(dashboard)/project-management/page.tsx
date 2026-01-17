'use client';

import * as React from 'react';
import Link from 'next/link';
import { useI18n } from '@/contexts/i18n-context';
import { Plus, Search, FolderKanban, Lock, Globe, ArrowRight } from 'lucide-react';
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
  const { t } = useI18n();
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
    <div className="space-y-8 page-fade-in" data-testid="pm-page">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight ">
            {t('pages.projectManagement.title')}
          </h1>
          <p className="text-muted-foreground font-medium">{t('pages.projectManagement.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <Tabs value={view} onValueChange={(v) => setView(v as any)} className="w-[200px]">
            <TabsList className="grid w-full grid-cols-2 bg-background/50 border-border/50">
              <TabsTrigger value="list">List</TabsTrigger>
              <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
            </TabsList>
          </Tabs>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine" onClick={() => setCreateOpen(true)} data-testid="pm-create-project">
            <Plus className="mr-2 h-4 w-4" />
            New Initiative
          </Button>
        </div>
      </div>

      {view === 'portfolio' ? (
        <div className="grid gap-8 md:grid-cols-2">
          <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden">
            <CardHeader className="pb-6">
              <CardTitle className="text-lg font-heading">Initiative Distribution</CardTitle>
              <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">High-level portfolio nodes by status</CardDescription>
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
          <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md flex flex-col items-center justify-center p-12">
            <div className="relative">
              <div className="text-6xl font-heading font-bold tracking-tight text-emerald-600 dark:text-emerald-500">
                {projects.length > 0 ? Math.round((projects.filter(p => p.status === 'active' || p.status === 'completed').length / projects.length) * 100) : 0}%
              </div>
              <div className="absolute -inset-8 border-2 border-success/10 rounded-full animate-pulse" />
            </div>
            <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-success/60 mt-12">Portfolio Health Index</p>
            <p className="text-sm text-muted-foreground font-medium mt-2">Strategic Velocity Optimal</p>
          </Card>
        </div>
      ) : (
        <div className="space-y-8">
          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardContent className="p-6">
              <div className="relative group">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40 group-focus-within:text-primary transition-colors" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search initiatives by intelligence key, slug, or description..."
                  className="pl-11 h-12 bg-background/50 border-border/50 rounded-xl"
                  data-testid="pm-search"
                />
              </div>
            </CardContent>
          </Card>

          {isLoading && (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, idx) => (
                <Card key={idx} className="p-6 rounded-3xl">
                  <Skeleton className="h-6 w-48 rounded-lg" />
                  <Skeleton className="mt-4 h-4 w-full rounded-md" />
                  <Skeleton className="mt-2 h-4 w-2/3 rounded-md" />
                </Card>
              ))}
            </div>
          )}

          {!isLoading && filtered.length === 0 && (
            <div className="rounded-[3rem] border-2 border-dashed border-border/20 p-20 text-center bg-muted/5">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-[2rem] bg-muted mb-6 shadow-inner-soft">
                <FolderKanban className="h-10 w-10 text-muted-foreground/30" />
              </div>
              <p className="text-sm font-heading font-bold text-muted-foreground/60 tracking-tight">No initiatives match current search parameters.</p>
              <div className="mt-8">
                <Button variant="outline" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary" onClick={() => setCreateOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Initiate First Protocol
                </Button>
              </div>
            </div>
          )}

          {!isLoading && filtered.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="pm-project-grid">
              {filtered.map((p: Project) => {
                const tone = statusTone[p.status];
                return (
                  <Link key={p.id} href={`/project-management/${p.id}`} className="block group">
                    <Card className="h-full border-border/40 bg-card/40 backdrop-blur-sm rounded-[2rem] transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1.5 hover:border-primary/20" data-testid={`pm-project-${p.id}`}>
                      <CardHeader className="pb-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="space-y-1.5">
                            <CardTitle className="text-lg font-heading font-bold tracking-tight group-hover:text-primary transition-colors">{p.name}</CardTitle>
                            <p className="text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">NODE: {p.slug}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {p.is_private ? (
                              <div className="p-2 rounded-xl bg-danger/5 text-danger/40 border border-danger/5" title="Private Protocol">
                                <Lock className="h-3.5 w-3.5" />
                              </div>
                            ) : (
                              <div className="p-2 rounded-xl bg-primary/5 text-primary/40 border border-primary/5" title="Shared Intelligence">
                                <Globe className="h-3.5 w-3.5" />
                              </div>
                            )}
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-5">
                        <div className="flex flex-wrap gap-2">
                          <Badge className={cn('border-none rounded-md px-2 py-0.5 text-[9px] font-black uppercase tracking-widest', tone.className)}>{tone.label}</Badge>
                          <Badge variant="outline" className="rounded-md px-2 py-0.5 text-[9px] font-black uppercase tracking-widest border-border/40 text-muted-foreground/60">{typeLabel[p.project_type]}</Badge>
                        </div>
                        {p.description ? (
                          <p className="line-clamp-2 text-xs text-muted-foreground/80 leading-relaxed font-medium">{p.description}</p>
                        ) : (
                          <p className="text-xs text-muted-foreground/40 italic">No description protocol established.</p>
                        )}
                        <div className="pt-4 border-t border-border/5 flex items-center justify-between">
                          <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/30">
                            PULSE {formatRelativeTime(p.updated_at)}
                          </p>
                          <ArrowRight className="h-4 w-4 text-primary/20 group-hover:text-primary group-hover:translate-x-1 transition-all" />
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
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
