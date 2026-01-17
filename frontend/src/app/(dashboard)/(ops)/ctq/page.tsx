'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  Edit,
  Copy,
  Trash2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  TrendingUp,
  FileText,
  Download,
  History,
  Ruler,
  Gauge,
  FlaskConical,
  Zap,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { cn, formatDate, formatRelativeTime } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/stores';
import { useCTQStore } from '@/stores/ctq';
import { hasPageAccess } from '@/lib/page-access';
import { UserRole } from '@/types';

type CTQCategory = 'dimensional' | 'surface' | 'material' | 'mechanical' | 'electrical' | 'visual' | 'functional' | 'environmental' | 'other';
type CTQPriority = 'critical' | 'major' | 'minor';
type CTQStatus = 'draft' | 'active' | 'under_review' | 'approved' | 'obsolete';
type MeasurementResult = 'pass' | 'fail' | 'marginal' | 'not_measured';

interface CTQMeasurement {
  id: string;
  ctq_id: string;
  measured_value: number | null;
  measured_at: string;
  measured_by_id: string;
  measured_by_name: string;
  result: MeasurementResult;
  notes: string;
  attachment_ids: string[];
  created_at: string;
}

interface CTQ {
  id: string;
  ctq_number: string;
  category: CTQCategory;
  priority: CTQPriority;
  status: CTQStatus;
  rfq_id?: string;
  rfq_number?: string;
  part_number?: string;
  characteristic: string;
  description: string;
  specification: string;
  nominal_value: number | null;
  upper_tolerance: number | null;
  lower_tolerance: number | null;
  unit_of_measure: string;
  measurement_method: string;
  sampling_plan: string;
  check_stage: string;
  evidence_required: boolean;
  measurements: CTQMeasurement[];
  measurement_count: number;
  pass_rate: number;
  created_at: string;
  updated_at: string;
  created_by_id: string;
  created_by_name: string;
}

interface CTQStats {
  total: number;
  active: number;
  approved: number;
  critical: number;
  average_pass_rate: number;
  measured_today: number;
}

const categoryIcons: Record<CTQCategory, React.ReactNode> = {
  dimensional: <Ruler className="h-4 w-4" />,
  surface: <Gauge className="h-4 w-4" />,
  material: <FlaskConical className="h-4 w-4" />,
  mechanical: <Zap className="h-4 w-4" />,
  electrical: <Zap className="h-4 w-4" />,
  visual: <Eye className="h-4 w-4" />,
  functional: <CheckCircle className="h-4 w-4" />,
  environmental: <AlertTriangle className="h-4 w-4" />,
  other: <FileText className="h-4 w-4" />,
};

const categoryColors: Record<CTQCategory, string> = {
  dimensional: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  surface: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  material: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  mechanical: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  electrical: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  visual: 'bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-300',
  functional: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300',
  environmental: 'bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-300',
  other: 'bg-gray-100 text-gray-700 dark:bg-gray-900 dark:text-gray-300',
};

const priorityColors: Record<CTQPriority, string> = {
  critical: 'destructive',
  major: 'warning',
  minor: 'default',
};

const statusColors: Record<CTQStatus, string> = {
  draft: 'secondary',
  active: 'default',
  under_review: 'warning',
  approved: 'success',
  obsolete: 'secondary',
};

const resultColors: Record<MeasurementResult, string> = {
  pass: 'success',
  fail: 'destructive',
  marginal: 'warning',
  not_measured: 'secondary',
};

export default function CTQPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { user } = useAuthStore();
  
  const { 
    ctqs, 
    stats, 
    isLoading, 
    fetchCTQs, 
    deleteCTQ 
  } = useCTQStore();

  const [searchQuery, setSearchQuery] = React.useState('');
  const [categoryFilter, setCategoryFilter] = React.useState<string>('all');
  const [priorityFilter, setPriorityFilter] = React.useState<string>('all');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);

  React.useEffect(() => {
    fetchCTQs();
  }, []);

  // Filter CTQs
  const filteredCTQs = React.useMemo(() => {
    return ctqs.filter((ctq) => {
      const matchesSearch = 
        ctq.ctq_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ctq.characteristic.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ctq.part_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ctq.rfq_number?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesCategory = categoryFilter === 'all' || ctq.category === categoryFilter;
      const matchesPriority = priorityFilter === 'all' || ctq.priority === priorityFilter;
      const matchesStatus = statusFilter === 'all' || ctq.status === statusFilter;

      return matchesSearch && matchesCategory && matchesPriority && matchesStatus;
    });
  }, [ctqs, searchQuery, categoryFilter, priorityFilter, statusFilter]);

  const handleDelete = async (id: string) => {
    try {
      await deleteCTQ(id);
      toast({
        title: 'Success',
        description: 'CTQ deleted successfully.',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete CTQ.',
        variant: 'destructive',
      });
    }
  };

  const handleExport = async () => {
    toast({
      title: 'Info',
      description: 'Exporting CTQs...',
    });
  };

  return (
    <div className="space-y-8 page-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Critical to Quality (CTQ)
          </h1>
          <p className="text-muted-foreground font-medium">
            Manage precision quality characteristics and automated gate specifications
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export Intel
          </Button>
          {hasPageAccess('/ctq/new', userRoles) && (
            <Button size="lg" className="rounded-xl shadow-glow subtle-shine">
              <Plus className="mr-2 h-4 w-4" />
              New Specification
            </Button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total CTQs</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{stats.total}</div>
            <p className="text-xs text-muted-foreground">
              {stats.active} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Approved</CardTitle>
            <CheckCircle className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{stats.approved}</div>
            <p className="text-xs text-muted-foreground">
              {((stats.approved / stats.total) * 100).toFixed(1)}% of total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Critical</CardTitle>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{stats.critical}</div>
            <p className="text-xs text-muted-foreground">
              Highest priority
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{stats.average_pass_rate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              Average across all CTQs
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Measured Today</CardTitle>
            <Gauge className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{stats.measured_today}</div>
            <p className="text-xs text-muted-foreground">
              Measurements recorded
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Measurements</CardTitle>
            <History className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              {ctqs.reduce((sum, ctq) => sum + ctq.measurement_count, 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              All time
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search CTQs..."
                  className="pl-8"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="dimensional">Dimensional</SelectItem>
                <SelectItem value="surface">Surface</SelectItem>
                <SelectItem value="material">Material</SelectItem>
                <SelectItem value="mechanical">Mechanical</SelectItem>
                <SelectItem value="electrical">Electrical</SelectItem>
                <SelectItem value="visual">Visual</SelectItem>
                <SelectItem value="functional">Functional</SelectItem>
                <SelectItem value="environmental">Environmental</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priorities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="major">Major</SelectItem>
                <SelectItem value="minor">Minor</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="under_review">Under Review</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="obsolete">Obsolete</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* CTQ Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>CTQ Number</TableHead>
              <TableHead>Characteristic</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Specification</TableHead>
              <TableHead>Pass Rate</TableHead>
              <TableHead>Latest Result</TableHead>
              <TableHead className="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-8" /></TableCell>
                </TableRow>
              ))
            ) : filteredCTQs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8">
                  <div className="flex flex-col items-center gap-2">
                    <FileText className="h-8 w-8 text-muted-foreground" />
                    <p className="text-muted-foreground">
                      {searchQuery || categoryFilter !== 'all' || priorityFilter !== 'all' || statusFilter !== 'all'
                        ? 'No CTQs match your filters'
                        : 'No CTQs found'}
                    </p>
                    {(searchQuery || categoryFilter !== 'all' || priorityFilter !== 'all' || statusFilter !== 'all') && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSearchQuery('');
                          setCategoryFilter('all');
                          setPriorityFilter('all');
                          setStatusFilter('all');
                        }}
                      >
                        Clear Filters
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              filteredCTQs.map((ctq) => (
                <TableRow key={ctq.id} className="cursor-pointer hover:bg-muted/50">
                  <TableCell>
                    <Link href={`/ctq/${ctq.id}`} className="font-medium hover:underline">
                      {ctq.ctq_number}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{ctq.characteristic}</p>
                      {ctq.part_number && (
                        <p className="text-xs text-muted-foreground">{ctq.part_number}</p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={cn('gap-1', categoryColors[ctq.category])}>
                      {categoryIcons[ctq.category]}
                      {ctq.category}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={priorityColors[ctq.priority] as any}>
                      {ctq.priority}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusColors[ctq.status] as any}>
                      {ctq.status.replace('_', ' ')}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="font-mono text-xs">
                      {ctq.specification}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="text-sm font-medium">
                        {ctq.pass_rate.toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground">
                        ({ctq.measurement_count})
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {ctq.measurements && ctq.measurements.length > 0 ? (
                      <Badge variant={resultColors[ctq.measurements[0].result] as any}>
                        {ctq.measurements[0].result}
                      </Badge>
                    ) : (
                      <Badge variant="secondary">No data</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem asChild>
                          <Link href={`/ctq/${ctq.id}`}>
                            <Eye className="mr-2 h-4 w-4" />
                            View Details
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link href={`/ctq/${ctq.id}?mode=edit`}>
                            <Edit className="mr-2 h-4 w-4" />
                            Edit
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Copy className="mr-2 h-4 w-4" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => handleDelete(ctq.id)}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
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
      </Card>
    </div>
  );
}
