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
    <div className="space-y-8 page-fade-in pb-12" data-testid="pm-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.projectManagement.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.projectManagement.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: PM-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-rams-panel p-1 border border-rams-border rounded-rams-sm mr-2">
            <Button
              variant={view === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setView('list')}
              className={cn("h-8 px-3 rounded-none", view === 'list' ? "bg-rams-orange text-black" : "text-muted-foreground")}
            >
              LIST
            </Button>
            <Button
              variant={view === 'portfolio' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setView('portfolio')}
              className={cn("h-8 px-3 rounded-none", view === 'portfolio' ? "bg-rams-orange text-black" : "text-muted-foreground")}
            >
              PORTFOLIO
            </Button>
          </div>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase" onClick={() => setCreateOpen(true)} data-testid="pm-create-project">
            <Plus className="mr-2 h-3.5 w-3.5" />
            INITIALIZE_INITIATIVE
          </Button>
        </div>
      </div>

      {view === 'portfolio' ? (
        <div className="grid gap-0 md:grid-cols-2 border border-rams-border bg-rams-border">
          <Card className="rounded-none border-0 border-r border-b md:border-b-0">
            <CardHeader className="pb-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">Initiative Distribution</CardTitle>
              <CardDescription className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">High-level portfolio nodes by status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[240px] flex items-center justify-center bg-rams-panel/20 border border-rams-border/50 relative overflow-hidden">
                <BarChart 
                  data={[
                    { label: 'Planning', value: projects.filter(p => p.status === 'planning').length, color: '#94a3b8' },
                    { label: 'Active', value: projects.filter(p => p.status === 'active').length, color: '#FFBE00' },
                    { label: 'On Hold', value: projects.filter(p => p.status === 'on_hold').length, color: '#D62D2D' },
                    { label: 'Completed', value: projects.filter(p => p.status === 'completed').length, color: '#2D8C3C' },
                  ]}
                />
                <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
              </div>
            </CardContent>
          </Card>
          <Card className="rounded-none border-0 border-b md:border-b-0 flex flex-col items-center justify-center p-12 bg-rams-module">
            <div className="relative">
              <div className="text-6xl font-mono font-bold tracking-tight text-rams-green tabular-nums">
                {projects.length > 0 ? Math.round((projects.filter(p => p.status === 'active' || p.status === 'completed').length / projects.length) * 100) : 0}%
              </div>
              <div className="absolute -inset-8 border border-rams-green/20 animate-pulse" />
            </div>
            <p className="text-[9px] font-mono font-black uppercase tracking-[0.3em] text-rams-green mt-12">Portfolio Health Index</p>
            <p className="text-[10px] font-sans font-bold text-muted-foreground/60 uppercase mt-2">Strategic Velocity Optimal</p>
          </Card>
        </div>
      ) : (
        <div className="space-y-8">
          <div className="relative group max-w-2xl">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 transition-colors group-focus-within:text-rams-orange" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="SEARCH_INITIATIVES..."
              className="pl-10 h-10 text-[10px]"
              data-testid="pm-search"
            />
          </div>

          {isLoading && projects.length === 0 ? (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {[1, 2, 3, 4, 5, 6].map((idx) => (
                <div key={idx} className="industrial-panel p-6 space-y-4">
                  <Skeleton className="h-4 w-1/3 rounded-none" />
                  <Skeleton className="h-12 w-full rounded-none" />
                  <Skeleton className="h-4 w-2/3 rounded-none" />
                </div>
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-24 text-center border border-dashed border-rams-border bg-rams-panel/20">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-rams-module border border-rams-border mb-6">
                <FolderKanban className="h-8 w-8 text-muted-foreground/20" />
              </div>
              <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">Zero initiative protocols identified</p>
              <div className="mt-8">
                <Button variant="outline" className="rounded-rams-sm" onClick={() => setCreateOpen(true)}>
                  <Plus className="mr-2 h-3.5 w-3.5" />
                  INITIATE_FIRST_PROTOCOL
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3" data-testid="pm-project-grid">
              {filtered.map((p: Project) => {
                const tone = statusTone[p.status];
                return (
                  <Link key={p.id} href={`/project-management/${p.id}`} className="block group">
                    <Card className="h-full rounded-rams-sm group hover:border-rams-orange/40 transition-none" data-testid={`pm-project-${p.id}`}>
                      <CardHeader className="pb-4 bg-rams-panel/10 border-b border-rams-border/30">
                        <div className="flex items-start justify-between gap-4">
                          <div className="space-y-1">
                            <CardTitle className="group-hover:text-rams-orange transition-none">{p.name}</CardTitle>
                            <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">NODE: {p.slug}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {p.is_private ? (
                              <div className="p-2 bg-rams-panel border border-rams-border text-rams-red/40" title="Private Protocol">
                                <Lock className="h-3.5 w-3.5" />
                              </div>
                            ) : (
                              <div className="p-2 bg-rams-panel border border-rams-border text-rams-green/40" title="Shared Intelligence">
                                <Globe className="h-3.5 w-3.5" />
                              </div>
                            )}
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="p-6 space-y-6">
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="outline" className={cn('rounded-none border-rams-border font-black', tone.className)}>{tone.label.toUpperCase()}</Badge>
                          <Badge variant="outline" className="rounded-none border-rams-border text-[9px] font-black uppercase tracking-widest text-muted-foreground/60">{typeLabel[p.project_type].toUpperCase()}</Badge>
                        </div>
                        <p className="line-clamp-2 text-xs text-muted-foreground leading-relaxed font-medium h-10">{p.description || 'No description protocol established.'}</p>
                        <div className="pt-6 border-t border-rams-border/30 flex items-center justify-between">
                          <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/30">
                            PULSE {formatRelativeTime(p.updated_at).toUpperCase()}
                          </p>
                          <ArrowRight className="h-4 w-4 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-1 transition-all" />
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

      {/* Create Dialog (Industrialized) */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl" data-testid="pm-create-dialog">
          <DialogHeader>
            <DialogTitle>INITIALIZE_INITIATIVE_PROTOCOL</DialogTitle>
            <DialogDescription>
              Create a new space for project intelligence, strategic alignment and cross-module work.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-6 py-4">
            <div className="grid gap-2">
              <Label htmlFor="pm-name">INITIATIVE_IDENTITY</Label>
              <Input
                id="pm-name"
                value={createForm.name}
                onChange={(e) => setCreateForm((s) => ({ ...s, name: e.target.value }))}
                placeholder="e.g., NPI - WING BRACKET..."
                data-testid="pm-create-name"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="pm-desc">PROTOCOL_SCOPE</Label>
              <Textarea
                id="pm-desc"
                value={createForm.description}
                onChange={(e) => setCreateForm((s) => ({ ...s, description: e.target.value }))}
                placeholder="Detail scope, objectives, and key strategic deliverables..."
                rows={4}
                data-testid="pm-create-description"
              />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label>ENGINEERING_TYPE</Label>
                <Select
                  value={createForm.project_type}
                  onValueChange={(v) => setCreateForm((s) => ({ ...s, project_type: v as ProjectType }))}
                >
                  <SelectTrigger data-testid="pm-create-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(typeLabel).map(([k, lbl]) => (
                      <SelectItem key={k} value={k}>
                        {lbl.toUpperCase()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label>STATUS_STATE</Label>
                <Select
                  value={createForm.status}
                  onValueChange={(v) => setCreateForm((s) => ({ ...s, status: v as ProjectStatus }))}
                >
                  <SelectTrigger data-testid="pm-create-status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(statusTone).map(([k, v]) => (
                      <SelectItem key={k} value={k}>
                        {v.label.toUpperCase()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-rams-panel border border-rams-border/50">
              <div>
                <Label className="text-foreground">PRIVATE_NODE_RESTRICTION</Label>
                <p className="text-[9px] text-muted-foreground/60 uppercase font-mono mt-1">Restrict visibility to invited team members only</p>
              </div>
              <Button
                type="button"
                variant={createForm.is_private ? 'default' : 'outline'}
                size="sm"
                onClick={() => setCreateForm((s) => ({ ...s, is_private: !s.is_private }))}
                data-testid="pm-create-visibility"
                className="h-8 rounded-none border-rams-border"
              >
                {createForm.is_private ? 'PRIVATE' : 'GLOBAL'}
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>
              CANCEL_PROTOCOL
            </Button>
            <Button onClick={onSubmitCreate} data-testid="pm-create-submit">
              INITIALIZE_INITIATIVE
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
