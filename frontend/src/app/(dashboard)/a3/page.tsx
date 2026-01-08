'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Plus,
  Search,
  Filter,
  Download,
  FileText,
  CheckCircle,
  Clock,
  AlertTriangle,
  TrendingUp,
  Users,
  Target,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

type A3Type = 'problem_solving' | 'proposal' | 'status_report' | 'strategy';
type A3Status = 'draft' | 'in_progress' | 'review' | 'approved' | 'implemented' | 'closed' | 'cancelled';
type A3Priority = 'critical' | 'high' | 'medium' | 'low';

interface A3 {
  id: string;
  a3_number: string;
  title: string;
  a3_type: A3Type;
  status: A3Status;
  author_name: string;
  sponsor_name?: string;
  coach_name?: string;
  target_completion_date?: string;
  progress_percentage: number;
  priority: A3Priority;
  department?: string;
  tags?: string[];
  created_at: string;
  updated_at: string;
}

interface A3Stats {
  total: number;
  by_status: Record<A3Status, number>;
  overdue_count: number;
  approval_pending: number;
}

const statusBadgeVariant: Record<A3Status, 'default' | 'secondary' | 'warning' | 'destructive' | 'success'> = {
  draft: 'secondary',
  in_progress: 'default',
  review: 'warning',
  approved: 'success',
  implemented: 'success',
  closed: 'secondary',
  cancelled: 'secondary',
};

const priorityBadgeVariant: Record<A3Priority, 'default' | 'secondary' | 'warning' | 'destructive'> = {
  low: 'secondary',
  medium: 'default',
  high: 'warning',
  critical: 'destructive',
};

const typeConfig: Record<A3Type, { label: string; color: string }> = {
  problem_solving: { label: 'Problem Solving', color: 'bg-blue-100 text-blue-700 border-blue-200' },
  proposal: { label: 'Proposal', color: 'bg-green-100 text-green-700 border-green-200' },
  status_report: { label: 'Status Report', color: 'bg-purple-100 text-purple-700 border-purple-200' },
  strategy: { label: 'Strategy', color: 'bg-orange-100 text-orange-700 border-orange-200' },
};

export default function A3Page() {
  const router = useRouter();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [a3s, setA3s] = useState<A3[]>([]);
  const [stats, setStats] = useState<A3Stats>({
    total: 0,
    by_status: {
      draft: 0,
      in_progress: 0,
      review: 0,
      approved: 0,
      implemented: 0,
      closed: 0,
      cancelled: 0,
    },
    overdue_count: 0,
    approval_pending: 0,
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');

  useEffect(() => {
    fetchA3s();
  }, []);

  const fetchA3s = async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call
      // const response = await fetch('/api/v1/a3s');
      // const data = await response.json();

      // Mock data
      setTimeout(() => {
        const mockA3s: A3[] = [
          {
            id: '1',
            a3_number: 'A3-2024-0023',
            title: 'Reduce Setup Time for CNC Machines',
            a3_type: 'problem_solving',
            status: 'in_progress',
            author_name: 'John Smith',
            sponsor_name: 'Sarah Johnson',
            coach_name: 'Mike Williams',
            target_completion_date: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(),
            progress_percentage: 65,
            priority: 'high',
            department: 'Manufacturing',
            tags: ['lean', 'setup-reduction', 'smed'],
            created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
            updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          },
          {
            id: '2',
            a3_number: 'A3-2024-0024',
            title: 'Surface Finish Defect Root Cause Analysis',
            a3_type: 'problem_solving',
            status: 'review',
            author_name: 'Sarah Chen',
            sponsor_name: 'Mike Williams',
            target_completion_date: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(),
            progress_percentage: 95,
            priority: 'critical',
            department: 'Quality',
            tags: ['quality', 'defects', 'root-cause'],
            created_at: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
            updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
          },
          {
            id: '3',
            a3_number: 'A3-2024-0025',
            title: 'New MRP System Implementation Proposal',
            a3_type: 'proposal',
            status: 'approved',
            author_name: 'Maria Garcia',
            sponsor_name: 'John Smith',
            target_completion_date: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString(),
            progress_percentage: 100,
            priority: 'medium',
            department: 'IT',
            tags: ['systems', 'erp', 'improvement'],
            created_at: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
            updated_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          },
          {
            id: '4',
            a3_number: 'A3-2024-0026',
            title: 'Q1 2024 Strategic Objectives',
            a3_type: 'strategy',
            status: 'implemented',
            author_name: 'David Lee',
            sponsor_name: 'CEO',
            target_completion_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
            progress_percentage: 100,
            priority: 'high',
            department: 'Management',
            tags: ['strategy', 'objectives', 'planning'],
            created_at: new Date(Date.now() - 120 * 24 * 60 * 60 * 1000).toISOString(),
            updated_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          },
          {
            id: '5',
            a3_number: 'A3-2024-0027',
            title: 'Inventory Accuracy Improvement',
            a3_type: 'problem_solving',
            status: 'draft',
            author_name: 'Emily Brown',
            target_completion_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
            progress_percentage: 15,
            priority: 'medium',
            department: 'Operations',
            tags: ['inventory', 'accuracy', 'cycle-count'],
            created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
            updated_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
          },
        ];

        setA3s(mockA3s);

        // Calculate stats
        const stats: A3Stats = {
          total: mockA3s.length,
          by_status: mockA3s.reduce((acc, a3) => {
            acc[a3.status] = (acc[a3.status] || 0) + 1;
            return acc;
          }, {} as Record<A3Status, number>),
          overdue_count: mockA3s.filter(a3 => {
            if (!a3.target_completion_date) return false;
            if (['closed', 'cancelled'].includes(a3.status)) return false;
            return new Date(a3.target_completion_date) < new Date();
          }).length,
          approval_pending: mockA3s.filter(a3 => a3.status === 'review').length,
        };

        setStats(stats);
        setIsLoading(false);
      }, 500);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch A3 reports',
        variant: 'destructive',
      });
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/a3s/${id}`, { method: 'DELETE' });

      toast({
        title: 'Success',
        description: 'A3 deleted successfully',
      });
      fetchA3s();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete A3',
        variant: 'destructive',
      });
    }
  };

  const filteredA3s = a3s.filter(a3 => {
    const matchesSearch = 
      a3.a3_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a3.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a3.author_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a3.department?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesType = typeFilter === 'all' || a3.a3_type === typeFilter;
    const matchesStatus = statusFilter === 'all' || a3.status === statusFilter;
    const matchesPriority = priorityFilter === 'all' || a3.priority === priorityFilter;

    return matchesSearch && matchesType && matchesStatus && matchesPriority;
  });

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const isOverdue = (a3: A3): boolean => {
    if (!a3.target_completion_date) return false;
    if (['closed', 'cancelled'].includes(a3.status)) return false;
    return new Date(a3.target_completion_date) < new Date();
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">A3 Reports</h1>
          <p className="text-muted-foreground mt-1">Structured problem solving and continuous improvement</p>
        </div>
        <Button onClick={() => router.push('/a3/new')}>
          <Plus className="mr-2 h-4 w-4" />
          New A3
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total A3s</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">
              {stats.by_status.in_progress || 0} in progress
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Review</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.approval_pending}</div>
            <p className="text-xs text-muted-foreground">Awaiting approval</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(stats.by_status.approved || 0) + (stats.by_status.implemented || 0) + (stats.by_status.closed || 0)}
            </div>
            <p className="text-xs text-muted-foreground">Approved or closed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">{stats.overdue_count}</div>
            <p className="text-xs text-muted-foreground">Past target date</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search A3s..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger>
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="problem_solving">Problem Solving</SelectItem>
                <SelectItem value="proposal">Proposal</SelectItem>
                <SelectItem value="status_report">Status Report</SelectItem>
                <SelectItem value="strategy">Strategy</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="review">In Review</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="implemented">Implemented</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger>
                <SelectValue placeholder="All Priorities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priorities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* A3 Table */}
      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>A3 Number</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Author</TableHead>
                <TableHead>Progress</TableHead>
                <TableHead>Target Date</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredA3s.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                    No A3 reports found. Create your first A3 to get started.
                  </TableCell>
                </TableRow>
              ) : (
                filteredA3s.map((a3) => (
                  <TableRow key={a3.id} className="cursor-pointer hover:bg-muted/50">
                    <TableCell>
                      <Link href={`/a3/${a3.id}`} className="font-medium text-primary hover:underline">
                        {a3.a3_number}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <div className="max-w-xs truncate">{a3.title}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn('gap-1', typeConfig[a3.a3_type].color)}>
                        {typeConfig[a3.a3_type].label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant[a3.status]}>
                        {a3.status.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={priorityBadgeVariant[a3.priority]} className="capitalize">
                        {a3.priority}
                      </Badge>
                    </TableCell>
                    <TableCell>{a3.author_name}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={a3.progress_percentage} className="h-2 w-16" />
                        <span className="text-xs text-muted-foreground">{a3.progress_percentage}%</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {a3.target_completion_date && (
                        <span className={cn(isOverdue(a3) && 'text-destructive font-medium')}>
                          {formatDate(a3.target_completion_date)}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            Actions
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => router.push(`/a3/${a3.id}`)}>
                            <FileText className="mr-2 h-4 w-4" />
                            View Details
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => router.push(`/a3/${a3.id}/edit`)}>
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Download className="mr-2 h-4 w-4" />
                            Export PDF
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-destructive" onClick={() => handleDelete(a3.id)}>
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
