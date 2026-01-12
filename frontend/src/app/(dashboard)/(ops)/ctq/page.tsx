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

type CTQCategory = 'dimensional' | 'surface' | 'material' | 'mechanical' | 'electrical' | 'visual' | 'functional' | 'environmental' | 'other';
type CTQPriority = 'critical' | 'major' | 'minor';
type CTQStatus = 'draft' | 'active' | 'under_review' | 'approved' | 'obsolete';
type MeasurementResult = 'pass' | 'fail' | 'marginal' | 'not_measured';

interface CTQMeasurement {
  id: string;
  measuredValue: number | null;
  measuredAt: string;
  measuredBy: string;
  result: MeasurementResult;
  notes: string;
  attachmentIds: string[];
}

interface CTQ {
  id: string;
  ctqNumber: string;
  category: CTQCategory;
  priority: CTQPriority;
  status: CTQStatus;
  rfqNumber?: string;
  partNumber?: string;
  characteristic: string;
  description: string;
  specification: string;
  nominalValue: number | null;
  upperTolerance: number | null;
  lowerTolerance: number | null;
  unitOfMeasure: string;
  measurementMethod: string;
  samplingPlan: string;
  checkStage: string;
  evidenceRequired: boolean;
  latestMeasurement?: CTQMeasurement;
  measurementCount: number;
  passRate: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
}

interface CTQStats {
  total: number;
  active: number;
  approved: number;
  critical: number;
  averagePassRate: number;
  measuredToday: number;
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

// Mock data for development
const mockStats: CTQStats = {
  total: 127,
  active: 89,
  approved: 103,
  critical: 34,
  averagePassRate: 96.5,
  measuredToday: 12,
};

const mockCTQs: CTQ[] = [
  {
    id: '1',
    ctqNumber: 'CTQ-2024-0089',
    category: 'dimensional',
    priority: 'critical',
    status: 'approved',
    rfqNumber: 'RFQ-2024-0123',
    partNumber: 'BRK-1234-A',
    characteristic: 'Mounting hole diameter',
    description: 'Diameter of primary mounting holes',
    specification: '10.0 ± 0.05 mm',
    nominalValue: 10.0,
    upperTolerance: 0.05,
    lowerTolerance: -0.05,
    unitOfMeasure: 'mm',
    measurementMethod: 'CMM (Coordinate Measuring Machine)',
    samplingPlan: '5 pieces per lot',
    checkStage: 'Final Inspection',
    evidenceRequired: true,
    latestMeasurement: {
      id: 'm1',
      measuredValue: 10.02,
      measuredAt: '2024-01-15T10:30:00Z',
      measuredBy: 'John Doe',
      result: 'pass',
      notes: 'Within specification',
      attachmentIds: ['att1'],
    },
    measurementCount: 47,
    passRate: 97.8,
    createdAt: '2023-12-01T09:00:00Z',
    updatedAt: '2024-01-15T10:30:00Z',
    createdBy: 'Quality Manager',
  },
  {
    id: '2',
    ctqNumber: 'CTQ-2024-0088',
    category: 'surface',
    priority: 'major',
    status: 'active',
    rfqNumber: 'RFQ-2024-0124',
    partNumber: 'MNT-5678-B',
    characteristic: 'Surface roughness',
    description: 'Ra value for mating surface',
    specification: 'Ra 1.6 μm max',
    nominalValue: null,
    upperTolerance: 1.6,
    lowerTolerance: null,
    unitOfMeasure: 'μm',
    measurementMethod: 'Surface roughness tester',
    samplingPlan: '3 pieces per lot',
    checkStage: 'In-Process',
    evidenceRequired: true,
    latestMeasurement: {
      id: 'm2',
      measuredValue: 1.4,
      measuredAt: '2024-01-14T14:15:00Z',
      measuredBy: 'Maria Garcia',
      result: 'pass',
      notes: 'Surface finish acceptable',
      attachmentIds: [],
    },
    measurementCount: 23,
    passRate: 95.6,
    createdAt: '2023-12-05T10:00:00Z',
    updatedAt: '2024-01-14T14:15:00Z',
    createdBy: 'Engineering',
  },
  {
    id: '3',
    ctqNumber: 'CTQ-2024-0087',
    category: 'material',
    priority: 'critical',
    status: 'approved',
    rfqNumber: 'RFQ-2024-0125',
    partNumber: 'HYD-9012-C',
    characteristic: 'Material hardness',
    description: 'Rockwell hardness for structural components',
    specification: 'HRC 45-50',
    nominalValue: 47.5,
    upperTolerance: 2.5,
    lowerTolerance: -2.5,
    unitOfMeasure: 'HRC',
    measurementMethod: 'Rockwell hardness tester',
    samplingPlan: '2 pieces per lot',
    checkStage: 'Incoming Inspection',
    evidenceRequired: true,
    latestMeasurement: {
      id: 'm3',
      measuredValue: 48.2,
      measuredAt: '2024-01-13T09:45:00Z',
      measuredBy: 'Sarah Chen',
      result: 'pass',
      notes: 'Material meets specification',
      attachmentIds: ['att2', 'att3'],
    },
    measurementCount: 31,
    passRate: 100.0,
    createdAt: '2023-11-28T11:00:00Z',
    updatedAt: '2024-01-13T09:45:00Z',
    createdBy: 'Quality Manager',
  },
  {
    id: '4',
    ctqNumber: 'CTQ-2024-0086',
    category: 'functional',
    priority: 'critical',
    status: 'approved',
    rfqNumber: 'RFQ-2024-0126',
    partNumber: 'ASM-3456-D',
    characteristic: 'Pressure test',
    description: 'Hydraulic pressure holding capacity',
    specification: 'Hold 3000 PSI for 10 min, no leakage',
    nominalValue: 3000,
    upperTolerance: null,
    lowerTolerance: null,
    unitOfMeasure: 'PSI',
    measurementMethod: 'Hydrostatic pressure test',
    samplingPlan: '100% inspection',
    checkStage: 'Final Inspection',
    evidenceRequired: true,
    latestMeasurement: {
      id: 'm4',
      measuredValue: null,
      measuredAt: '2024-01-12T16:20:00Z',
      measuredBy: 'John Doe',
      result: 'fail',
      notes: 'Minor leakage detected at 8-minute mark. NCR raised.',
      attachmentIds: ['att4'],
    },
    measurementCount: 15,
    passRate: 93.3,
    createdAt: '2023-12-10T13:00:00Z',
    updatedAt: '2024-01-12T16:20:00Z',
    createdBy: 'Engineering',
  },
  {
    id: '5',
    ctqNumber: 'CTQ-2024-0085',
    category: 'dimensional',
    priority: 'major',
    status: 'active',
    rfqNumber: 'RFQ-2024-0127',
    partNumber: 'FST-7890-E',
    characteristic: 'Thread pitch',
    description: 'Thread pitch for M12 fasteners',
    specification: 'M12 × 1.75',
    nominalValue: 1.75,
    upperTolerance: 0.02,
    lowerTolerance: -0.02,
    unitOfMeasure: 'mm',
    measurementMethod: 'Thread pitch gauge',
    samplingPlan: '10 pieces per lot',
    checkStage: 'In-Process',
    evidenceRequired: false,
    measurementCount: 8,
    passRate: 100.0,
    createdAt: '2024-01-08T08:00:00Z',
    updatedAt: '2024-01-11T15:30:00Z',
    createdBy: 'Quality Engineer',
  },
];

export default function CTQPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [ctqs, setCTQs] = React.useState<CTQ[]>(mockCTQs);
  const [stats, setStats] = React.useState<CTQStats>(mockStats);
  const [isLoading, setIsLoading] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [categoryFilter, setCategoryFilter] = React.useState<string>('all');
  const [priorityFilter, setPriorityFilter] = React.useState<string>('all');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');

  // Fetch CTQs from API
  const fetchCTQs = React.useCallback(async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call
      // const response = await fetch('/api/v1/ctqs');
      // const data = await response.json();
      // setCTQs(data.items);
      // setStats(data.stats);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));
      setCTQs(mockCTQs);
      setStats(mockStats);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load CTQs. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  React.useEffect(() => {
    fetchCTQs();
  }, [fetchCTQs]);

  // Filter CTQs
  const filteredCTQs = React.useMemo(() => {
    return ctqs.filter((ctq) => {
      const matchesSearch = 
        ctq.ctqNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ctq.characteristic.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ctq.partNumber?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ctq.rfqNumber?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesCategory = categoryFilter === 'all' || ctq.category === categoryFilter;
      const matchesPriority = priorityFilter === 'all' || ctq.priority === priorityFilter;
      const matchesStatus = statusFilter === 'all' || ctq.status === statusFilter;

      return matchesSearch && matchesCategory && matchesPriority && matchesStatus;
    });
  }, [ctqs, searchQuery, categoryFilter, priorityFilter, statusFilter]);

  const handleDelete = async (id: string) => {
    try {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/ctqs/${id}`, { method: 'DELETE' });
      
      setCTQs(ctqs.filter(ctq => ctq.id !== id));
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
    try {
      // TODO: Replace with actual API call
      // await fetch('/api/v1/ctqs/export');
      
      toast({
        title: 'Success',
        description: 'CTQs exported successfully.',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to export CTQs.',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="flex-1 space-y-6 p-8 pt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Critical to Quality (CTQ)</h2>
          <p className="text-muted-foreground">
            Manage quality characteristics and specifications
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button asChild>
            <Link href="/ctq/new">
              <Plus className="mr-2 h-4 w-4" />
              New CTQ
            </Link>
          </Button>
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
            <div className="text-2xl font-bold">{stats.total}</div>
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
            <div className="text-2xl font-bold">{stats.approved}</div>
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
            <div className="text-2xl font-bold">{stats.critical}</div>
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
            <div className="text-2xl font-bold">{stats.averagePassRate.toFixed(1)}%</div>
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
            <div className="text-2xl font-bold">{stats.measuredToday}</div>
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
            <div className="text-2xl font-bold">
              {ctqs.reduce((sum, ctq) => sum + ctq.measurementCount, 0)}
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
                      {ctq.ctqNumber}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{ctq.characteristic}</p>
                      {ctq.partNumber && (
                        <p className="text-xs text-muted-foreground">{ctq.partNumber}</p>
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
                        {ctq.passRate.toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground">
                        ({ctq.measurementCount})
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {ctq.latestMeasurement ? (
                      <Badge variant={resultColors[ctq.latestMeasurement.result] as any}>
                        {ctq.latestMeasurement.result}
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
                          <Link href={`/ctq/${ctq.id}/edit`}>
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
