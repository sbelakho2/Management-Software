'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Edit,
  Trash2,
  Plus,
  FileText,
  Download,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Ruler,
  Gauge,
  FlaskConical,
  Zap,
  Eye,
  Calendar,
  User,
  ClipboardCheck,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { useCTQStore } from '@/stores/ctq';
import { useI18n } from '@/contexts/i18n-context';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

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
  dimensional: 'bg-rams-steel/10 text-rams-steel border-rams-steel/20',
  surface: 'bg-rams-green/10 text-rams-green border-rams-green/20',
  material: 'bg-rams-panel text-foreground/70 border-rams-line',
  mechanical: 'bg-rams-orange/10 text-rams-orange border-rams-orange/20',
  electrical: 'bg-rams-orange/10 text-rams-orange border-rams-orange/20',
  visual: 'bg-rams-steel/10 text-rams-steel border-rams-steel/20',
  functional: 'bg-rams-green/10 text-rams-green border-rams-green/20',
  environmental: 'bg-rams-red/10 text-rams-red border-rams-red/20',
  other: 'bg-rams-panel text-muted-foreground border-rams-line',
};

const resultBadgeVariant: Record<MeasurementResult, 'default' | 'success' | 'destructive' | 'warning'> = {
  pass: 'success',
  fail: 'destructive',
  marginal: 'warning',
  not_measured: 'default',
};

const resultIcons: Record<MeasurementResult, React.ReactNode> = {
  pass: <CheckCircle className="h-3 w-3" />,
  fail: <XCircle className="h-3 w-3" />,
  marginal: <AlertTriangle className="h-3 w-3" />,
  not_measured: <Minus className="h-3 w-3" />,
};

export default function CTQDetailPage() {
  const { t } = useI18n();
  const params = useParams();
  const router = useRouter();
  const { id } = params;
  const { toast } = useToast();
  
  const { 
    fetchCTQById, 
    updateCTQ, 
    deleteCTQ, 
    addMeasurement,
    isLoading: storeLoading 
  } = useCTQStore();

  const [isLoading, setIsLoading] = useState(true);
  const [ctq, setCTQ] = useState<CTQ | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showMeasurementDialog, setShowMeasurementDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isAddingMeasurement, setIsAddingMeasurement] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const [measurementForm, setMeasurementForm] = useState({
    measured_value: '',
    result: 'not_measured' as MeasurementResult,
    notes: '',
  });

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const data = await fetchCTQById(id as string);
      if (data) {
        setCTQ(data as any);
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load CTQ details',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await deleteCTQ(id as string);
      toast({
        title: 'Success',
        description: 'CTQ deleted successfully',
      });
      router.push('/ctq');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete CTQ',
        variant: 'destructive',
      });
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  const handleAddMeasurement = async () => {
    if (!measurementForm.measured_value) return;

    setIsAddingMeasurement(true);
    try {
      await addMeasurement(id as string, {
        measured_value: parseFloat(measurementForm.measured_value),
        notes: measurementForm.notes,
      });
      
      toast({
        title: 'Success',
        description: 'Measurement added successfully',
      });
      
      setShowMeasurementDialog(false);
      setMeasurementForm({ measured_value: '', result: 'not_measured', notes: '' });
      
      // Reload data
      loadData();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to add measurement',
        variant: 'destructive',
      });
    } finally {
      setIsAddingMeasurement(false);
    }
  };

  const handleExport = () => {
    if (!ctq) return;

    toast({
      title: 'Export started',
      description: 'Your CTQ report is being generated',
    });

    const headers = ['Date', 'Measured Value', 'Result', 'Measured By', 'Notes'];
    const rows = ctq.measurements.map(m => [
      new Date(m.measured_at).toLocaleDateString(),
      m.measured_value ?? '',
      m.result,
      m.measured_by_name || 'N/A',
      m.notes || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(r => r.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `CTQ_${ctq.ctq_number}_Report.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const calculateTrend = (measurements: CTQMeasurement[]): 'up' | 'down' | 'stable' => {
    if (measurements.length < 3) return 'stable';
    const recent = measurements.slice(0, 3);
    const values = recent.map(m => m.measured_value).filter((v): v is number => v !== null);
    if (values.length < 3) return 'stable';
    
    if (values[0] > values[1] && values[1] > values[2]) return 'up';
    if (values[0] < values[1] && values[1] < values[2]) return 'down';
    return 'stable';
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-96" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!ctq) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] space-y-4">
        <FileText className="h-16 w-16 text-muted-foreground" />
        <div className="text-center">
          <h2 className="text-3xl font-heading font-bold tracking-tight ">{t('pages.ctqDetail.notFound') || 'CTQ Not Found'}</h2>
          <p className="text-muted-foreground mt-2">
            {t('pages.ctqDetail.notFoundDescription') || "The CTQ you're looking for doesn't exist or has been deleted."}
          </p>
        </div>
        <Button onClick={() => router.push('/ctq')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t('pages.ctqDetail.backToCTQs') || 'Back to CTQs'}
        </Button>
      </div>
    );
  }

  const trend = calculateTrend(ctq.measurements);

  return (
    <div className="space-y-8 page-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-orange/10 transition-none" onClick={() => router.push('/ctq')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-heading font-bold tracking-tight ">{ctq.ctq_number}</h1>
              <Badge variant="outline" className={cn('rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider gap-1', categoryColors[ctq.category])}>
                {categoryIcons[ctq.category]}
                {ctq.category}
              </Badge>
              <Badge variant={ctq.priority === 'critical' ? 'destructive' : ctq.priority === 'major' ? 'warning' : 'default'} className="rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                {ctq.priority}
              </Badge>
              <Badge variant={
                ctq.status === 'approved' ? 'success' : 
                ctq.status === 'active' ? 'default' :
                ctq.status === 'under_review' ? 'warning' :
                'secondary'
              } className="rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                {ctq.status.replace('_', ' ')}
              </Badge>
            </div>
            <p className="text-muted-foreground font-medium text-sm mt-1">{ctq.characteristic} Characteristic</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-rams-sm border-rams-line hover:bg-rams-orange/5" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            {t('pages.ctqDetail.exportIntel') || 'Export Intel'}
          </Button>
          <Button variant="outline" size="lg" className="rounded-rams-sm border-rams-line hover:bg-rams-orange/5" onClick={() => setIsEditing(true)}>
            <Edit className="mr-2 h-4 w-4" />
            {t('common.edit') || 'Edit'}
          </Button>
          <Button variant="destructive" size="lg" className="rounded-rams-sm" onClick={() => setShowDeleteDialog(true)}>
            <Trash2 className="mr-2 h-4 w-4" />
            {t('pages.ctqDetail.retire') || 'Retire'}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">{t('pages.ctqDetail.passRate') || 'Pass Rate'}</CardTitle>
            <CheckCircle className="h-4 w-4 text-rams-green/60" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight ">{ctq.pass_rate.toFixed(1)}%</div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-2">
              {Math.round((ctq.measurement_count * ctq.pass_rate) / 100)} of {ctq.measurement_count} {t('pages.ctqDetail.passed') || 'PASSED'}
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">{t('pages.ctqDetail.synchronizationPulse') || 'Synchronization Pulse'}</CardTitle>
            <ClipboardCheck className="h-4 w-4 text-rams-orange/60" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight ">{ctq.measurement_count}</div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-2">
              {t('pages.ctqDetail.totalRecordedSamples') || 'Total Recorded Samples'}
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">{t('pages.ctqDetail.latestIntelligence') || 'Latest Intelligence'}</CardTitle>
            {resultIcons[ctq.measurements[0]?.result || 'not_measured']}
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight ">
              {ctq.measurements[0]?.measured_value?.toFixed(3) || '-'} <span className="text-base text-muted-foreground/60">{ctq.unit_of_measure}</span>
            </div>
            <div className="mt-2">
              <Badge variant={resultBadgeVariant[ctq.measurements[0]?.result || 'not_measured']} className="gap-1 rounded-md px-1.5 py-0 text-[9px] font-bold uppercase tracking-widest">
                {resultIcons[ctq.measurements[0]?.result || 'not_measured']}
                {ctq.measurements[0]?.result.replace('_', ' ') || 'No data'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">{t('pages.ctqDetail.performanceTrend') || 'Performance Trend'}</CardTitle>
            {trend === 'up' ? <TrendingUp className="h-4 w-4 text-rams-red/60" /> :
             trend === 'down' ? <TrendingDown className="h-4 w-4 text-rams-green/60" /> :
             <Minus className="h-4 w-4 text-muted-foreground/60" />}
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-heading font-bold tracking-tight  capitalize">{trend}</div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 mt-2">
              {t('pages.ctqDetail.velocityOverSamples') || 'Velocity over last 3 samples'}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Specification Details */}
        <Card>
          <CardHeader>
            <CardTitle>Specification Details</CardTitle>
            <CardDescription>Quality characteristic requirements</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-sm font-medium">Description</Label>
              <p className="text-sm text-muted-foreground mt-1">{ctq.description}</p>
            </div>
            <Separator />
            <div className="grid gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">Specification</Label>
                  <p className="text-sm font-mono mt-1">{ctq.specification}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Nominal Value</Label>
                  <p className="text-sm font-mono mt-1">
                    {ctq.nominal_value} {ctq.unit_of_measure}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">Upper Tolerance</Label>
                  <p className="text-sm font-mono mt-1">
                    +{ctq.upper_tolerance} {ctq.unit_of_measure}
                  </p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Lower Tolerance</Label>
                  <p className="text-sm font-mono mt-1">
                    {ctq.lower_tolerance} {ctq.unit_of_measure}
                  </p>
                </div>
              </div>
            </div>
            <Separator />
            <div className="grid gap-4">
              {ctq.rfq_number && (
                <div>
                  <Label className="text-sm font-medium">Related RFQ</Label>
                  <p className="text-sm mt-1">
                    <Link href={`/rfq/${ctq.rfq_id}`} className="text-primary hover:underline">
                      {ctq.rfq_number}
                    </Link>
                  </p>
                </div>
              )}
              {ctq.part_number && (
                <div>
                  <Label className="text-sm font-medium">Part Number</Label>
                  <p className="text-sm font-mono mt-1">{ctq.part_number}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Measurement Details */}
        <Card>
          <CardHeader>
            <CardTitle>Measurement Information</CardTitle>
            <CardDescription>How this characteristic is measured</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-sm font-medium">Measurement Method</Label>
              <p className="text-sm text-muted-foreground mt-1">{ctq.measurement_method}</p>
            </div>
            <Separator />
            <div>
              <Label className="text-sm font-medium">Sampling Plan</Label>
              <p className="text-sm text-muted-foreground mt-1">{ctq.sampling_plan}</p>
            </div>
            <Separator />
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm font-medium">Check Stage</Label>
                <p className="text-sm text-muted-foreground mt-1">{ctq.check_stage}</p>
              </div>
              <div>
                <Label className="text-sm font-medium">Evidence Required</Label>
                <p className="text-sm text-muted-foreground mt-1">
                  {ctq.evidence_required ? 'Yes' : 'No'}
                </p>
              </div>
            </div>
            <Separator />
            <div className="grid grid-cols-2 gap-4 text-xs text-muted-foreground">
              <div>
                <Label className="text-xs font-medium">Created</Label>
                <p className="flex items-center gap-1 mt-1">
                  <Calendar className="h-3 w-3" />
                  {new Date(ctq.created_at).toLocaleDateString()}
                </p>
                <p className="flex items-center gap-1 mt-1">
                  <User className="h-3 w-3" />
                  {ctq.created_by_name}
                </p>
              </div>
              <div>
                <Label className="text-xs font-medium">Last Updated</Label>
                <p className="flex items-center gap-1 mt-1">
                  <Calendar className="h-3 w-3" />
                  {new Date(ctq.updated_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Measurements History */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Measurement History</CardTitle>
              <CardDescription>Recent measurement results for this CTQ</CardDescription>
            </div>
            <Button onClick={() => setShowMeasurementDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Measurement
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date & Time</TableHead>
                <TableHead>Measured By</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Result</TableHead>
                <TableHead>Notes</TableHead>
                <TableHead>Evidence</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ctq.measurements.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No measurements recorded yet
                  </TableCell>
                </TableRow>
              ) : (
                ctq.measurements.map((measurement) => (
                  <TableRow key={measurement.id}>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="text-sm">
                          {new Date(measurement.measured_at).toLocaleDateString()}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(measurement.measured_at).toLocaleTimeString()}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>{measurement.measured_by_name}</TableCell>
                    <TableCell className="font-mono">
                      {measurement.measured_value !== null 
                        ? `${measurement.measured_value.toFixed(3)} ${ctq.unit_of_measure}`
                        : '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={resultBadgeVariant[measurement.result]} className="gap-1">
                        {resultIcons[measurement.result]}
                        {measurement.result.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs truncate">
                      {measurement.notes || '-'}
                    </TableCell>
                    <TableCell>
                      {measurement.attachment_ids.length > 0 ? (
                        <Button variant="ghost" size="sm">
                          <FileText className="mr-1 h-3 w-3" />
                          {measurement.attachment_ids.length}
                        </Button>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete CTQ</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {ctq.ctq_number}? This action cannot be undone and will also delete all associated measurements.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? 'Deleting...' : 'Delete CTQ'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Measurement Dialog */}
      <Dialog open={showMeasurementDialog} onOpenChange={setShowMeasurementDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Measurement</DialogTitle>
            <DialogDescription>
              Record a new measurement for {ctq.characteristic}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="measured_value">Measured Value ({ctq.unit_of_measure})</Label>
              <Input
                id="measured_value"
                type="number"
                step="0.001"
                placeholder={`Enter value in ${ctq.unit_of_measure}`}
                value={measurementForm.measured_value}
                onChange={(e) => setMeasurementForm({ ...measurementForm, measured_value: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="result">Result</Label>
              <Select
                value={measurementForm.result}
                onValueChange={(value: MeasurementResult) => setMeasurementForm({ ...measurementForm, result: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pass">Pass</SelectItem>
                  <SelectItem value="fail">Fail</SelectItem>
                  <SelectItem value="marginal">Marginal</SelectItem>
                  <SelectItem value="not_measured">Not Measured</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Add any relevant notes about this measurement"
                value={measurementForm.notes}
                onChange={(e) => setMeasurementForm({ ...measurementForm, notes: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowMeasurementDialog(false)} disabled={isAddingMeasurement}>
              Cancel
            </Button>
            <Button onClick={handleAddMeasurement} disabled={isAddingMeasurement}>
              {isAddingMeasurement ? 'Adding...' : 'Add Measurement'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
