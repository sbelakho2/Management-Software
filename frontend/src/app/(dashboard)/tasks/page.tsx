'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
import {
  Plus,
  Search,
  Filter,
  LayoutGrid,
  List,
  MoreHorizontal,
  Calendar,
  Clock,
  CheckCircle2,
  Circle,
  AlertCircle,
  Users,
  Tag,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useTasksStore } from '@/stores/tasks';
import { cn, formatDate } from '@/lib/utils';
import type { Task, TaskStatus, Priority } from '@/types';

const statusConfig: Record<string, { label: string; icon: any; color: string; variant: any }> = {
  todo: { label: 'To Do', icon: Circle, color: 'text-muted-foreground', variant: 'secondary' },
  in_progress: { label: 'In Progress', icon: Clock, color: 'text-rams-orange', variant: 'warning' },
  in_review: { label: 'Review', icon: AlertCircle, color: 'text-rams-steel', variant: 'outline' },
  done: { label: 'Completed', icon: CheckCircle2, color: 'text-rams-green', variant: 'success' },
  cancelled: { label: 'Cancelled', icon: XCircle, color: 'text-rams-red', variant: 'destructive' },
  backlog: { label: 'Backlog', icon: Circle, color: 'text-muted-foreground/40', variant: 'secondary' },
};

import { XCircle as XCircleIcon } from 'lucide-react';

const priorityConfig: Record<string, { label: string; variant: any }> = {
  low: { label: 'Low', variant: 'secondary' },
  medium: { label: 'Medium', variant: 'default' },
  high: { label: 'High', variant: 'warning' },
  critical: { label: 'Critical', variant: 'danger' },
};

export default function TasksPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { tasks: tasksRaw, loading, fetchTasks, moveTask } = useTasksStore();
  const tasks = tasksRaw ?? [];
  const [view, setView] = React.useState<'list' | 'board'>('board');
  const [search, setSearch] = React.useState('');

  React.useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const filteredTasks = tasks.filter((task) =>
    task.title.toLowerCase().includes(search.toLowerCase()) ||
    task.description?.toLowerCase().includes(search.toLowerCase())
  );

  const tasksByStatus = React.useMemo(() => {
    const grouped: Record<string, Task[]> = {
      todo: [],
      in_progress: [],
      in_review: [],
      done: [],
      cancelled: [],
      backlog: [],
    };
    filteredTasks.forEach((task) => {
      const status = task.status;
      if (grouped[status]) {
        grouped[status].push(task);
      }
    });
    return grouped;
  }, [filteredTasks]);

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="tasks-page">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.tasks.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.tasks.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: TASK-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-rams-panel p-1 border border-rams-border rounded-rams-sm mr-2">
            <Button
              variant={view === 'board' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setView('board')}
              className={cn("h-8 px-3 rounded-none", view === 'board' ? "bg-rams-orange text-black" : "text-muted-foreground")}
            >
              <LayoutGrid className="mr-2 h-3.5 w-3.5" />
              BOARD
            </Button>
            <Button
              variant={view === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setView('list')}
              className={cn("h-8 px-3 rounded-none", view === 'list' ? "bg-rams-orange text-black" : "text-muted-foreground")}
            >
              <List className="mr-2 h-3.5 w-3.5" />
              LIST
            </Button>
          </div>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase" onClick={() => router.push('/tasks/new')}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            Initialize Task
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="relative flex-1 group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 transition-colors group-focus-within:text-rams-orange" />
          <Input
            placeholder="SEARCH_TASK_PROTOCOLS..."
            className="pl-10 h-10 text-[10px]"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Button variant="outline" size="default" className="rounded-rams-sm border-rams-border h-10">
          <Filter className="h-3.5 w-3.5 mr-2" />
          Strategic Filters
        </Button>
      </div>

      {view === 'board' ? (
        <div className="grid gap-8 lg:grid-cols-4 overflow-x-auto pb-8 scrollbar-hide">
          {(['todo', 'in_progress', 'in_review', 'done'] as TaskStatus[]).map((status) => (
            <div key={status} className="flex flex-col gap-6 min-w-[300px]">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-3">
                  <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/60">{statusConfig[status].label}</h3>
                  <Badge variant="secondary" className="rounded-none border-rams-border font-mono text-[9px] font-bold">{tasksByStatus[status].length}</Badge>
                </div>
              </div>
              <div className="flex flex-col gap-1 min-h-[600px] bg-rams-panel/20 border border-rams-border/50 p-1">
                {tasksByStatus[status].map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))}
                {tasksByStatus[status].length === 0 && (
                  <div className="flex flex-col items-center justify-center h-40 border border-dashed border-rams-border/30 text-muted-foreground/20">
                    <p className="text-[9px] font-black uppercase tracking-widest">Zero Protocol Nodes</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Card className="rounded-rams-sm overflow-hidden border-rams-border">
          <CardContent className="p-0">
            <div className="divide-y divide-rams-border/30">
              {filteredTasks.map((task) => (
                <div key={task.id} className="p-4 flex items-center justify-between hover:bg-rams-panel transition-none group">
                  <div className="flex items-center gap-4">
                    {(() => {
                      const Icon = statusConfig[task.status].icon;
                      return (
                        <div className={cn("p-2 rounded-rams-sm bg-rams-panel border border-rams-border", statusConfig[task.status].color)}>
                          <Icon className="h-4 w-4" />
                        </div>
                      );
                    })()}
                    <div>
                      <h4 className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{task.title}</h4>
                      <div className="flex items-center gap-4 mt-1">
                        <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                          <Calendar className="h-3 w-3" />
                          {task.due_date ? formatDate(task.due_date) : 'ASAP'}
                        </span>
                        <Badge variant={priorityConfig[task.priority].variant} size="sm">
                          {priorityConfig[task.priority].label.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" className="h-8 w-8 rounded-rams-sm">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function TaskCard({ task }: { task: Task }) {
  const router = useRouter();
  const priority = priorityConfig[task.priority];

  return (
    <Card className="cursor-pointer transition-none group border-rams-border bg-rams-module rounded-none hover:border-rams-orange/40">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-start justify-between">
          <Badge variant={priority.variant} size="sm">
            {priority.label.toUpperCase()}
          </Badge>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-7 w-7 rounded-rams-sm opacity-0 group-hover:opacity-100 transition-none hover:bg-rams-panel">
                <MoreHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>VIEW_NODE</DropdownMenuItem>
              <DropdownMenuItem>REFINE_PROTOCOL</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-rams-red">TERMINATE_PROTOCOL</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <h4 className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 leading-snug group-hover:text-rams-orange transition-none">{task.title}</h4>
        {task.description && (
          <p className="text-[11px] text-muted-foreground/60 line-clamp-2 leading-relaxed font-medium">{task.description}</p>
        )}
        <div className="flex items-center justify-between pt-4 border-t border-rams-border/30">
          <div className="flex items-center gap-2 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
            <Calendar className="h-3 w-3" />
            {task.due_date ? formatDate(task.due_date) : 'ASAP'}
          </div>
          <div className="flex -space-x-1">
            <div className="h-6 w-6 rounded-none border border-rams-border bg-rams-panel flex items-center justify-center text-[8px] font-black text-muted-foreground uppercase">
              {getInitials(task.assigned_to_name || 'UN')}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').toUpperCase();
}
