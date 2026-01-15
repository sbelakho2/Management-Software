'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
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

const statusConfig: Record<string, { label: string; icon: any; color: string }> = {
  todo: { label: 'To Do', icon: Circle, color: 'text-muted-foreground' },
  in_progress: { label: 'In Progress', icon: Clock, color: 'text-blue-500' },
  in_review: { label: 'Review', icon: AlertCircle, color: 'text-yellow-500' },
  done: { label: 'Completed', icon: CheckCircle2, color: 'text-green-500' },
  cancelled: { label: 'Cancelled', icon: XCircle, color: 'text-red-500' },
  backlog: { label: 'Backlog', icon: Circle, color: 'text-gray-400' },
};

import { XCircle } from 'lucide-react';

const priorityConfig: Record<string, { label: string; color: string }> = {
  low: { label: 'Low', color: 'bg-slate-100 text-slate-800' },
  medium: { label: 'Medium', color: 'bg-blue-100 text-blue-800' },
  high: { label: 'High', color: 'bg-orange-100 text-orange-800' },
  critical: { label: 'Critical', color: 'bg-red-100 text-red-800' },
};

export default function TasksPage() {
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
    <div className="space-y-8 page-fade-in" data-testid="tasks-page">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Mission Control
          </h1>
          <p className="text-muted-foreground font-medium">Manage and track your operational assignments</p>
        </div>
        <div className="flex items-center gap-3">
          <Tabs value={view} onValueChange={(v: any) => setView(v)}>
            <TabsList className="bg-background/50 border-border/50">
              <TabsTrigger value="board">
                <LayoutGrid className="h-4 w-4 mr-2" />
                Board
              </TabsTrigger>
              <TabsTrigger value="list">
                <List className="h-4 w-4 mr-2" />
                List
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine" onClick={() => router.push('/tasks/new')}>
            <Plus className="mr-2 h-4 w-4" />
            New Assignment
          </Button>
        </div>
      </div>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1 group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40 group-focus-within:text-primary transition-colors" />
              <Input
                placeholder="Search assignments by intelligence key..."
                className="pl-11 h-12 bg-background/50 border-border/50 rounded-xl"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Button variant="outline" size="lg" className="rounded-xl border-border/50 h-12">
              <Filter className="h-4 w-4 mr-2" />
              Strategic Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {view === 'board' ? (
        <div className="grid gap-8 lg:grid-cols-4 overflow-x-auto pb-8 no-scrollbar">
          {(['todo', 'in_progress', 'in_review', 'done'] as TaskStatus[]).map((status) => (
            <div key={status} className="flex flex-col gap-6 min-w-[300px]">
              <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-3">
                  <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">{statusConfig[status].label}</h3>
                  <Badge variant="secondary" className="bg-primary/10 text-primary border-none text-[9px] font-bold">{tasksByStatus[status].length}</Badge>
                </div>
              </div>
              <div className="flex flex-col gap-4 min-h-[600px] bg-muted/10 rounded-[2.5rem] p-4 border border-border/5">
                {tasksByStatus[status].map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))}
                {tasksByStatus[status].length === 0 && (
                  <div className="flex flex-col items-center justify-center h-40 border-2 border-dashed border-border/20 rounded-[2rem] text-muted-foreground/40">
                    <p className="text-xs font-bold uppercase tracking-widest">No Protocol Nodes</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Card className="rounded-[2rem] border-border/40 overflow-hidden">
          <CardContent className="p-0">
            <div className="divide-y divide-border/10">
              {filteredTasks.map((task) => (
                <div key={task.id} className="p-5 flex items-center justify-between hover:bg-primary/5 transition-all group">
                  <div className="flex items-center gap-5">
                    {(() => {
                      const Icon = statusConfig[task.status].icon;
                      return (
                        <div className={cn("p-2.5 rounded-xl bg-background shadow-sm transition-transform group-hover:scale-110", statusConfig[task.status].color)}>
                          <Icon className="h-5 w-5" />
                        </div>
                      );
                    })()}
                    <div>
                      <h4 className="font-heading font-bold text-base tracking-tight group-hover:text-primary transition-colors">{task.title}</h4>
                      <div className="flex items-center gap-4 mt-1.5">
                        <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
                          <Calendar className="h-3 w-3" />
                          {task.due_date ? formatDate(task.due_date) : 'Undetermined Horizon'}
                        </span>
                        {task.priority !== 'medium' && (
                          <Badge className={cn("text-[9px] font-bold uppercase tracking-wider", priorityConfig[task.priority].color)} variant="secondary">
                            {priorityConfig[task.priority].label}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" className="rounded-xl group-hover:bg-primary/10">
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
    <Card className="cursor-pointer transition-all duration-500 hover:shadow-glow hover:-translate-y-1.5 group border-border/40 bg-card/60 backdrop-blur-sm rounded-[1.5rem]">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-start justify-between">
          <Badge className={cn("text-[9px] font-bold uppercase tracking-widest rounded-md", priority.color)} variant="secondary">
            {priority.label}
          </Badge>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-primary/10">
                <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="rounded-2xl shadow-premium">
              <DropdownMenuItem onClick={() => router.push(`/tasks/${task.id}`)} className="rounded-xl m-1">View Node</DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push(`/tasks/${task.id}?mode=edit`)} className="rounded-xl m-1">Refine Protocol</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-danger rounded-xl m-1">De-authorize</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <h4 className="font-heading font-bold text-sm leading-snug group-hover:text-primary transition-colors">{task.title}</h4>
        {task.description && (
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed font-medium">{task.description}</p>
        )}
        <div className="flex items-center justify-between pt-4 border-t border-border/10">
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
            <Calendar className="h-3 w-3" />
            {task.due_date ? formatDate(task.due_date) : 'ASAP'}
          </div>
          <div className="flex -space-x-2">
            <div className="h-7 w-7 rounded-full border-2 border-background bg-primary/10 flex items-center justify-center text-[9px] font-bold text-primary shadow-sm">
              JD
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
