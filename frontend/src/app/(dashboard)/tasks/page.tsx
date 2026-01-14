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
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Tasks</h1>
          <p className="text-muted-foreground">Manage and track your operational tasks</p>
        </div>
        <div className="flex items-center gap-2">
          <Tabs value={view} onValueChange={(v: any) => setView(v)}>
            <TabsList>
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
          <Button onClick={() => router.push('/tasks/new')}>
            <Plus className="h-4 w-4 mr-2" />
            New Task
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search tasks..."
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Button variant="outline">
              <Filter className="h-4 w-4 mr-2" />
              Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {view === 'board' ? (
        <div className="grid gap-6 lg:grid-cols-4 overflow-x-auto pb-4">
          {(['todo', 'in_progress', 'in_review', 'done'] as TaskStatus[]).map((status) => (
            <div key={status} className="flex flex-col gap-4 min-w-[280px]">
              <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">{statusConfig[status].label}</h3>
                  <Badge variant="secondary">{tasksByStatus[status].length}</Badge>
                </div>
              </div>
              <div className="flex flex-col gap-3 min-h-[500px] bg-muted/30 rounded-lg p-3">
                {tasksByStatus[status].map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))}
                {tasksByStatus[status].length === 0 && (
                  <div className="flex flex-col items-center justify-center h-32 border-2 border-dashed rounded-lg text-muted-foreground">
                    <p className="text-sm">No tasks</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y">
              {filteredTasks.map((task) => (
                <div key={task.id} className="p-4 flex items-center justify-between hover:bg-muted/50 transition-colors">
                  <div className="flex items-center gap-4">
                    {(() => {
                      const Icon = statusConfig[task.status].icon;
                      return <Icon className={cn("h-5 w-5", statusConfig[task.status].color)} />;
                    })()}
                    <div>
                      <h4 className="font-medium">{task.title}</h4>
                      <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {task.due_date ? formatDate(task.due_date) : 'No due date'}
                        </span>
                        {task.priority !== 'medium' && (
                          <Badge className={priorityConfig[task.priority].color} variant="secondary">
                            {priorityConfig[task.priority].label}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon">
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
    <Card className="cursor-pointer hover:shadow-md transition-shadow group">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between">
          <Badge className={cn("mb-2", priority.color)} variant="secondary">
            {priority.label}
          </Badge>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => router.push(`/tasks/${task.id}`)}>View Details</DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push(`/tasks/${task.id}?mode=edit`)}>Edit</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive">Delete</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <h4 className="font-medium leading-tight">{task.title}</h4>
        {task.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">{task.description}</p>
        )}
        <div className="flex items-center justify-between pt-2 border-t">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Calendar className="h-3 w-3" />
            {task.due_date ? formatDate(task.due_date) : 'No date'}
          </div>
          <div className="flex -space-x-2">
            <div className="h-6 w-6 rounded-full border-2 border-background bg-muted flex items-center justify-center text-[10px] font-medium">
              JD
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
