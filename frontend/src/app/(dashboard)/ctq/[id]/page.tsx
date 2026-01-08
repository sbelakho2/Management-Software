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
  dimensional: 'bg-blue-100 text-blue-700 border-blue-200',
  surface: 'bg-green-100 text-green-700 border-green-200',
  material: 'bg-purple-100 text-purple-700 border-purple-200',
  mechanical: 'bg-orange-100 text-orange-700 border-orange-200',
  electrical: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  visual: 'bg-pink-100 text-pink-700 border-pink-200',
  functional: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  environmental: 'bg-red-100 text-red-700 border-red-200',
  other: 'bg-gray-100 text-gray-700 border-gray-200',
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
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [ctq, setCTQ] = useState<CTQ | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showMeasurementDialog, setShowMeasurementDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isAddingMeasurement, setIsAddingMeasurement] = useState(false);

  const [measurementForm, setMeasurementForm] = useState({
    measured_value: '',
    result: 'not_measured' as MeasurementResult,
    notes: '',
  });

  useEffect(() => {
    fetchCTQ();
  }, [params.id]);

  const fetchCTQ = async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call
      // const response = await fetch(`/api/v1/ctqs/${params.id}`);
      // const data = await response.json();
      // setCTQ(data);

      // Mock data
      setTimeout(() => {
        setCTQ({
          id: params.id as string,
          ctq_number: 'CTQ-2024-0089',
          category: 'dimensional',
          priority: 'critical',
          status: 'approved',
          rfq_id: 'rfq-123',
          rfq_number: 'RFQ-2024-0456',
          part_number: 'P/N-1234567',
          characteristic: 'Mounting hole diameter',
          description: 'Critical mounting hole for bracket assembly. Must maintain tight tolerance to ensure proper fit with mating hardware.',
          specification: '10.0 ± 0.05mm',
          nominal_value: 10.0,
          upper_tolerance: 0.05,
          lower_tolerance: -0.05,
          unit_of_measure: 'mm',
          measurement_method: 'CMM (Coordinate Measuring Machine)',
          sampling_plan: '100% inspection for first 10 parts, then 1 in 10 for production run',
          check_stage: 'Final inspection',
          evidence_required: true,
          measurement_count: 45,
          pass_rate: 97.8,
          measurements: [
            {
              id: 'm1',
              ctq_id: params.id as string,
              measured_value: 10.02,
              measured_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
              measured_by_id: 'user-1',
              measured_by_name: 'John Smith',
              result: 'pass',
              notes: 'Part #456 - Within spec',
              attachment_ids: [],
              created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
            },
            {
              id: 'm2',
              ctq_id: params.id as string,
              measured_value: 9.96,
              measured_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
              measured_by_id: 'user-2',
              measured_by_name: 'Sarah Johnson',
              result: 'pass',
              notes: 'Part #455 - Good',
              attachment_ids: [],
              created_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
            },
            {
              id: 'm3',
              ctq_id: params.id as string,
              measured_value: 10.06,
              measured_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
              measured_by_id: 'user-1',
              measured_by_name: 'John Smith',
              result: 'fail',
              notes: 'Part #454 - Out of spec, scrapped',
              attachment_ids: ['att-1'],
              created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
            },
            {
              id: 'm4',
              ctq_id: params.id as string,
              measured_value: 10.048,
              measured_at: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
              measured_by_id: 'user-3',
              measured_by_name: 'Mike Williams',
              result: 'marginal',
              notes: 'Part #453 - At limit, approved for use',
              attachment_ids: [],
              created_at: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
            },
            {
              id: 'm5',
              ctq_id: params.id as string,
              measured_value: 10.01,
              measured_at: new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString(),
              measured_by_id: 'user-2',
              measured_by_name: 'Sarah Johnson',
              result: 'pass',
              notes: 'Part #452 - Excellent',
              attachment_ids: [],
              created_at: new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString(),
            },
          ],
          created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
          created_by_id: 'user-1',
          created_by_name: 'John Smith',
        });
        setIsLoading(false);
      }, 500);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch CTQ details',
        variant: 'destructive',
      });
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/ctqs/${params.id}`, { method: 'DELETE' });
      
      setTimeout(() => {
        toast({
          title: 'Success',
          description: 'CTQ deleted successfully',
        });
        router.push('/ctq');
      }, 500);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete CTQ',
        variant: 'destructive',
      });
      setIsDeleting(false);
    }
  };

  const handleAddMeasurement = async () => {
    setIsAddingMeasurement(true);
    try {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/ctqs/${params.id}/measurements`, {
      //   method: 'POST',
      //   body: JSON.stringify(measurementForm),
      // });

      setTimeout(() => {
        toast({
          title: 'Success',
          description: 'Measurement added successfully',
        });
        setShowMeasurementDialog(false);
        setMeasurementForm({ measured_value: '', result: 'not_measured', notes: '' });
        fetchCTQ();
        setIsAddingMeasurement(false);
      }, 500);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to add measurement',
        variant: 'destructive',
      });
      setIsAddingMeasurement(false);
    }
  };

  const handleExport = () => {
    toast({
      title: 'Export started',
      description: 'Your CTQ report is being generated',
    });
    // TODO: Implement actual export
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
          <h2 className="text-2xl font-bold">CTQ Not Found</h2>
          <p className="text-muted-foreground mt-2">
            The CTQ you're looking for doesn't exist or has been deleted.
          </p>
        </div>
        <Button onClick={() => router.push('/ctq')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to CTQs
        </Button>
      </div>
    );
  }

  const trend = calculateTrend(ctq.measurements);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push('/ctq')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold">{ctq.ctq_number}</h1>
              <Badge variant="outline" className={cn('gap-1', categoryColors[ctq.category])}>
                {categoryIcons[ctq.category]}
                {ctq.category}
              </Badge>
              <Badge variant={ctq.priority === 'critical' ? 'destructive' : ctq.priority === 'major' ? 'warning' : 'default'}>
                {ctq.priority}
              </Badge>
              <Badge variant={
                ctq.status === 'approved' ? 'success' : 
                ctq.status === 'active' ? 'default' :
                ctq.status === 'under_review' ? 'warning' :
                'secondary'
              }>
                {ctq.status.replace('_', ' ')}
              </Badge>
            </div>
            <p className="text-muted-foreground mt-1">{ctq.characteristic}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button variant="outline" onClick={() => router.push(`/ctq/${params.id}/edit`)}>
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button variant="destructive" onClick={() => setShowDeleteDialog(true)}>
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{ctq.pass_rate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {Math.round((ctq.measurement_count * ctq.pass_rate) / 100)} of {ctq.measurement_count} passed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Measurements</CardTitle>
            <ClipboardCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{ctq.measurement_count}</div>
            <p className="text-xs text-muted-foreground">
              {ctq.measurements.length} recent measurements
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Latest Result</CardTitle>
            {resultIcons[ctq.measurements[0]?.result || 'not_measured']}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {ctq.measurements[0]?.measured_value?.toFixed(3) || '-'} {ctq.unit_of_measure}
            </div>
            <Badge variant={resultBadgeVariant[ctq.measurements[0]?.result || 'not_measured']} className="gap-1">
              {resultIcons[ctq.measurements[0]?.result || 'not_measured']}
              {ctq.measurements[0]?.result.replace('_', ' ') || 'No data'}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Trend</CardTitle>
            {trend === 'up' ? <TrendingUp className="h-4 w-4 text-red-500" /> :
             trend === 'down' ? <TrendingDown className="h-4 w-4 text-green-500" /> :
             <Minus className="h-4 w-4 text-muted-foreground" />}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">{trend}</div>
            <p className="text-xs text-muted-foreground">
              Based on last 3 measurements
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
