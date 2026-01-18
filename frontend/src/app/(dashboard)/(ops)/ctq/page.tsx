'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
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

const priorityColors: Record<CTQPriority, any> = {
  critical: 'danger',
  major: 'warning',
  minor: 'secondary',
};

const statusColors: Record<CTQStatus, any> = {
  draft: 'secondary',
  active: 'success',
  under_review: 'warning',
  approved: 'default',
  obsolete: 'outline',
};

const resultColors: Record<MeasurementResult, any> = {
  pass: 'success',
  fail: 'danger',
  marginal: 'warning',
  not_measured: 'secondary',
};

export default function CTQPage() {
  const { t } = useI18n();
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
    <div className="space-y-8 page-fade-in pb-12" data-testid="ctq-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.ctq.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.ctq.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: QUALITY-SPEC-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-border">
            <History className="h-3.5 w-3.5 mr-2" />
            Legacy Data
          </Button>
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-border" onClick={handleExport}>
            <Download className="h-3.5 w-3.5 mr-2" />
            Export Intel
          </Button>
          {hasPageAccess('/ctq/new', userRoles) && (
            <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]" onClick={() => router.push('/ctq/new')}>
              <Plus className="mr-2 h-3.5 w-3.5" />
              Initialize CTQ
            </Button>
          )}
        </div>
      </div>

      {/* Stats Grid (Industrial Modules) */}
      <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-6 border border-rams-border bg-rams-border">
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Total CTQ Nodes</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats?.total || 0}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{stats.active} Active Sync</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Approved Nodes</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{stats.approved}</div>
          <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">{((stats.approved / (stats.total || 1)) * 100).toFixed(1)}% GATE_PASS</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Critical Gates</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-red tabular-nums">{stats.critical}</div>
          <p className="text-[9px] font-mono font-bold text-rams-red uppercase tracking-widest mt-2">HIGH_SPEC_RISK</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Mean Pass Rate</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{stats.average_pass_rate.toFixed(1)}%</div>
          <p className="text-[9px] font-mono font-bold text-rams-orange uppercase tracking-widest mt-2">SYNC_VELOCITY</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Measured Today</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.measured_today}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">PULSE_DETECTIONS</p>
        </div>
        <div className="bg-rams-module p-6 border-b md:border-b-0 border-rams-border group">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">Aggregated Log</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">
            {ctqs.reduce((sum, ctq) => sum + ctq.measurement_count, 0)}
          </div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">TOTAL_VERIFICATIONS</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 items-center gap-4 max-w-4xl">
          <div className="relative flex-1 min-w-[240px] group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 transition-colors group-focus-within:text-rams-orange" />
            <Input
              placeholder="SEARCH_CTQ_NODES..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-10 text-[10px]"
            />
          </div>
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-[160px] h-10 text-[10px]">
              <Filter className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder="CATEGORY_NODE" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">ALL_CATEGORIES</SelectItem>
              <SelectItem value="dimensional">DIMENSIONAL</SelectItem>
              <SelectItem value="surface">SURFACE_FINISH</SelectItem>
              <SelectItem value="material">MATERIAL_NODE</SelectItem>
              <SelectItem value="mechanical">MECHANICAL</SelectItem>
              <SelectItem value="electrical">ELECTRICAL</SelectItem>
              <SelectItem value="visual">VISUAL_GATE</SelectItem>
              <SelectItem value="functional">FUNCTIONAL_SYNC</SelectItem>
            </SelectContent>
          </Select>
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="w-[160px] h-10 text-[10px]">
              <AlertTriangle className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder="PRIORITY_LVL" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">ALL_PRIORITIES</SelectItem>
              <SelectItem value="critical">CRITICAL_NODE</SelectItem>
              <SelectItem value="major">MAJOR_RISK</SelectItem>
              <SelectItem value="minor">MINOR_PROTOCOL</SelectItem>
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[160px] h-10 text-[10px]">
              <Clock className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder="STATUS_STATE" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">ALL_STATUS</SelectItem>
              <SelectItem value="draft">DRAFT_MODE</SelectItem>
              <SelectItem value="active">ACTIVE_SYNC</SelectItem>
              <SelectItem value="under_review">UNDER_REVIEW</SelectItem>
              <SelectItem value="approved">APPROVED_GATE</SelectItem>
              <SelectItem value="obsolete">OBSOLETE_NODE</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* CTQ Table */}
      <Card className="rounded-rams-sm overflow-hidden border-rams-border shadow-none">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>CTQ_IDENTIFIER</TableHead>
                <TableHead>CHARACTERISTIC</TableHead>
                <TableHead>CATEGORY_NODE</TableHead>
                <TableHead>PRIORITY</TableHead>
                <TableHead>STATUS_NODE</TableHead>
                <TableHead>SPECIFICATION</TableHead>
                <TableHead>PASS_RATE_KPI</TableHead>
                <TableHead>LATEST_SYNC</TableHead>
                <TableHead className="w-10"></TableHead>
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
                  <TableCell colSpan={9} className="text-center py-24">
                    <FileText className="h-12 w-12 text-muted-foreground/20 mx-auto mb-4" />
                    <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">Zero CTQ protocols identified</p>
                    <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">Adjust parameters or initialize new specification</p>
                  </TableCell>
                </TableRow>
              ) : (
                filteredCTQs.map((ctq) => (
                  <TableRow 
                    key={ctq.id} 
                    className="group transition-none cursor-pointer"
                    onClick={() => router.push(`/ctq/${ctq.id}`)}
                  >
                    <TableCell className="font-mono font-bold text-rams-orange tabular-nums">{ctq.ctq_number}</TableCell>
                    <TableCell>
                      <div className="space-y-0.5">
                        <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{ctq.characteristic}</p>
                        {ctq.part_number && <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">{ctq.part_number}</p>}
                      </div>
                    </TableCell>
                    <TableCell className="font-sans font-bold text-[11px] uppercase tracking-tight text-muted-foreground/60">{ctq.category}</TableCell>
                    <TableCell>
                      <Badge variant={priorityColors[ctq.priority]} size="sm">
                        {ctq.priority.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusColors[ctq.status]} size="sm">
                        {ctq.status.toUpperCase().replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-[10px] font-mono font-bold text-foreground/70 uppercase">
                        {ctq.specification}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="w-24 space-y-1.5">
                        <div className="flex justify-between text-[9px] font-mono font-bold tabular-nums">
                          <span className={cn(ctq.pass_rate >= 95 ? 'text-rams-green' : 'text-rams-orange')}>{Math.round(ctq.pass_rate)}%</span>
                        </div>
                        <div className="h-1 bg-rams-panel border border-rams-border/30 overflow-hidden">
                          <div className={cn(
                            "h-full transition-all duration-500",
                            ctq.pass_rate >= 95 ? 'bg-rams-green' : 'bg-rams-orange'
                          )} style={{ width: `${ctq.pass_rate}%` }} />
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant={ctq.measurements?.[0]?.result === 'pass' ? 'success' : 
                                ctq.measurements?.[0]?.result === 'fail' ? 'danger' : 'secondary'}
                        size="sm"
                        className="h-4 px-1"
                      >
                        {ctq.measurements?.[0]?.result?.toUpperCase() || 'NO_DATA'}
                      </Badge>
                    </TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => router.push(`/ctq/${ctq.id}`)}>
                            <Eye className="mr-2 h-3.5 w-3.5" /> ANALYZE
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => router.push(`/ctq/${ctq.id}/edit`)}>
                            <Edit className="mr-2 h-3.5 w-3.5" /> REFINE
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => router.push(`/ctq/${ctq.id}/measure`)}>
                            <Gauge className="mr-2 h-3.5 w-3.5 text-rams-orange" /> MEASURE
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-rams-red" onClick={() => handleDelete(ctq.id)}>
                            TERMINATE_NODE
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  );
}
