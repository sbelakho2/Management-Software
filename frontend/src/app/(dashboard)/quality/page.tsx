'use client';

import * as React from 'react';
import { Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  Edit,
  ClipboardCheck,
  AlertTriangle,
  Shield,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  AlertCircle,
  FileText,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { cn, formatDate, formatRelativeTime } from '@/lib/utils';

type TabType = 'inspections' | 'ncrs' | 'capas';

interface Inspection {
  id: string;
  inspectionNumber: string;
  workOrderNumber: string;
  productName: string;
  type: 'incoming' | 'in_process' | 'final' | 'source';
  status: 'pending' | 'in_progress' | 'passed' | 'failed' | 'conditional';
  inspector?: string;
  scheduledAt: string;
  completedAt?: string;
}

interface NCR {
  id: string;
  ncrNumber: string;
  title: string;
  severity: 'critical' | 'major' | 'minor';
  status: 'open' | 'investigating' | 'disposition' | 'closed';
  source: string;
  affectedQuantity: number;
  assignedTo?: string;
  createdAt: string;
}

interface CAPA {
  id: string;
  capaNumber: string;
  title: string;
  type: 'corrective' | 'preventive';
  status: 'open' | 'implementing' | 'verifying' | 'closed';
  priority: 'high' | 'medium' | 'low';
  sourceNCR?: string;
  dueDate: string;
  assignedTo?: string;
  createdAt: string;
}

const mockInspections: Inspection[] = [
  { id: '1', inspectionNumber: 'INS-2024-0089', workOrderNumber: 'WO-2024-0045', productName: 'Precision Bracket Type A', type: 'final', status: 'pending', scheduledAt: '2024-01-15T10:00:00Z' },
  { id: '2', inspectionNumber: 'INS-2024-0088', workOrderNumber: 'WO-2024-0044', productName: 'Mounting Plate Assembly', type: 'in_process', status: 'in_progress', inspector: 'John Doe', scheduledAt: '2024-01-14T14:00:00Z' },
  { id: '3', inspectionNumber: 'INS-2024-0087', workOrderNumber: 'WO-2024-0043', productName: 'Hydraulic Fitting', type: 'incoming', status: 'passed', inspector: 'Maria Garcia', scheduledAt: '2024-01-13T09:00:00Z', completedAt: '2024-01-13T11:30:00Z' },
  { id: '4', inspectionNumber: 'INS-2024-0086', workOrderNumber: 'WO-2024-0042', productName: 'Structural Fastener Kit', type: 'final', status: 'failed', inspector: 'Sarah Chen', scheduledAt: '2024-01-12T15:00:00Z', completedAt: '2024-01-12T16:45:00Z' },
];

const mockNCRs: NCR[] = [
  { id: '1', ncrNumber: 'NCR-2024-0034', title: 'Surface finish defect on bracket assembly', severity: 'major', status: 'investigating', source: 'Final Inspection', affectedQuantity: 25, assignedTo: 'Quality Team', createdAt: '2024-01-12T16:45:00Z' },
  { id: '2', ncrNumber: 'NCR-2024-0033', title: 'Dimensional out of tolerance - mounting holes', severity: 'critical', status: 'disposition', source: 'Customer Complaint', affectedQuantity: 50, assignedTo: 'John Doe', createdAt: '2024-01-10T09:30:00Z' },
  { id: '3', ncrNumber: 'NCR-2024-0032', title: 'Material certificate mismatch', severity: 'minor', status: 'open', source: 'Incoming Inspection', affectedQuantity: 100, createdAt: '2024-01-09T14:00:00Z' },
  { id: '4', ncrNumber: 'NCR-2024-0031', title: 'Thread damage on fasteners', severity: 'major', status: 'closed', source: 'In-Process Inspection', affectedQuantity: 15, assignedTo: 'Maria Garcia', createdAt: '2024-01-05T11:00:00Z' },
];

const mockCAPAs: CAPA[] = [
  { id: '1', capaNumber: 'CAPA-2024-0012', title: 'Implement enhanced surface finish inspection', type: 'corrective', status: 'implementing', priority: 'high', sourceNCR: 'NCR-2024-0034', dueDate: '2024-02-15', assignedTo: 'John Doe', createdAt: '2024-01-13T10:00:00Z' },
  { id: '2', capaNumber: 'CAPA-2024-0011', title: 'Update CMM program for hole tolerances', type: 'corrective', status: 'verifying', priority: 'high', sourceNCR: 'NCR-2024-0033', dueDate: '2024-02-01', assignedTo: 'Sarah Chen', createdAt: '2024-01-11T09:00:00Z' },
  { id: '3', capaNumber: 'CAPA-2024-0010', title: 'Revise incoming inspection checklist', type: 'preventive', status: 'open', priority: 'medium', dueDate: '2024-02-28', createdAt: '2024-01-10T14:00:00Z' },
  { id: '4', capaNumber: 'CAPA-2024-0009', title: 'Add torque verification step', type: 'corrective', status: 'closed', priority: 'medium', sourceNCR: 'NCR-2024-0031', dueDate: '2024-01-20', assignedTo: 'Maria Garcia', createdAt: '2024-01-06T11:00:00Z' },
];

const inspectionStatusConfig = {
  pending: { label: 'Pending', variant: 'secondary' as const, icon: Clock },
  in_progress: { label: 'In Progress', variant: 'warning' as const, icon: Clock },
  passed: { label: 'Passed', variant: 'success' as const, icon: CheckCircle },
  failed: { label: 'Failed', variant: 'danger' as const, icon: XCircle },
  conditional: { label: 'Conditional', variant: 'warning' as const, icon: AlertCircle },
};

const ncrStatusConfig = {
  open: { label: 'Open', variant: 'warning' as const },
  investigating: { label: 'Investigating', variant: 'default' as const },
  disposition: { label: 'Disposition', variant: 'secondary' as const },
  closed: { label: 'Closed', variant: 'success' as const },
};

const severityConfig = {
  critical: { label: 'Critical', variant: 'danger' as const },
  major: { label: 'Major', variant: 'warning' as const },
  minor: { label: 'Minor', variant: 'secondary' as const },
};

const capaStatusConfig = {
  open: { label: 'Open', variant: 'warning' as const },
  implementing: { label: 'Implementing', variant: 'default' as const },
  verifying: { label: 'Verifying', variant: 'secondary' as const },
  closed: { label: 'Closed', variant: 'success' as const },
};

const priorityConfig = {
  high: { label: 'High', variant: 'danger' as const },
  medium: { label: 'Medium', variant: 'warning' as const },
  low: { label: 'Low', variant: 'secondary' as const },
};

function QualityStats() {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/10">
              <ClipboardCheck className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold">5</p>
              <p className="text-sm text-muted-foreground">Pending Inspections</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-danger/10">
              <AlertTriangle className="h-5 w-5 text-danger" />
            </div>
            <div>
              <p className="text-2xl font-bold">3</p>
              <p className="text-sm text-muted-foreground">Open NCRs</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Shield className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">4</p>
              <p className="text-sm text-muted-foreground">Active CAPAs</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-success/10">
              <TrendingUp className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold">94.2%</p>
              <p className="text-sm text-muted-foreground">First Pass Yield</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function InspectionsTab() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');

  const filteredInspections = mockInspections.filter((insp) => {
    const matchesSearch = searchQuery === '' ||
      insp.inspectionNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      insp.productName.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || insp.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search inspections..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="passed">Passed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">Inspection</th>
                  <th className="py-3 px-4 text-left font-medium">Work Order</th>
                  <th className="py-3 px-4 text-left font-medium">Product</th>
                  <th className="py-3 px-4 text-left font-medium">Type</th>
                  <th className="py-3 px-4 text-left font-medium">Status</th>
                  <th className="py-3 px-4 text-left font-medium">Scheduled</th>
                  <th className="py-3 px-4 text-left font-medium">Inspector</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filteredInspections.map((insp) => {
                  const config = inspectionStatusConfig[insp.status];
                  const StatusIcon = config.icon;
                  return (
                    <tr 
                      key={insp.id}
                      className="border-b hover:bg-muted/50 cursor-pointer"
                      onClick={() => router.push(`/quality/inspections/${insp.id}`)}
                    >
                      <td className="py-3 px-4 font-medium">{insp.inspectionNumber}</td>
                      <td className="py-3 px-4 text-muted-foreground">{insp.workOrderNumber}</td>
                      <td className="py-3 px-4">{insp.productName}</td>
                      <td className="py-3 px-4 capitalize">{insp.type.replace('_', ' ')}</td>
                      <td className="py-3 px-4">
                        <Badge variant={config.variant} className="gap-1">
                          <StatusIcon className="h-3 w-3" />
                          {config.label}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">{formatDate(new Date(insp.scheduledAt))}</td>
                      <td className="py-3 px-4 text-muted-foreground">{insp.inspector || '—'}</td>
                      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Eye className="mr-2 h-4 w-4" />
                              View
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <ClipboardCheck className="mr-2 h-4 w-4" />
                              Start Inspection
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function NCRsTab() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [severityFilter, setSeverityFilter] = React.useState<string>('all');

  const filteredNCRs = mockNCRs.filter((ncr) => {
    const matchesSearch = searchQuery === '' ||
      ncr.ncrNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ncr.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || ncr.status === statusFilter;
    const matchesSeverity = severityFilter === 'all' || ncr.severity === severityFilter;
    return matchesSearch && matchesStatus && matchesSeverity;
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search NCRs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="investigating">Investigating</SelectItem>
              <SelectItem value="disposition">Disposition</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
            </SelectContent>
          </Select>
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="w-[130px]">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="major">Major</SelectItem>
              <SelectItem value="minor">Minor</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">NCR</th>
                  <th className="py-3 px-4 text-left font-medium">Title</th>
                  <th className="py-3 px-4 text-left font-medium">Severity</th>
                  <th className="py-3 px-4 text-left font-medium">Status</th>
                  <th className="py-3 px-4 text-left font-medium">Source</th>
                  <th className="py-3 px-4 text-right font-medium">Affected Qty</th>
                  <th className="py-3 px-4 text-left font-medium">Created</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filteredNCRs.map((ncr) => {
                  const statusCfg = ncrStatusConfig[ncr.status];
                  const severityCfg = severityConfig[ncr.severity];
                  return (
                    <tr 
                      key={ncr.id}
                      className="border-b hover:bg-muted/50 cursor-pointer"
                      onClick={() => router.push(`/quality/ncrs/${ncr.id}`)}
                    >
                      <td className="py-3 px-4 font-medium">{ncr.ncrNumber}</td>
                      <td className="py-3 px-4">{ncr.title}</td>
                      <td className="py-3 px-4">
                        <Badge variant={severityCfg.variant}>{severityCfg.label}</Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={statusCfg.variant}>{statusCfg.label}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{ncr.source}</td>
                      <td className="py-3 px-4 text-right">{ncr.affectedQuantity}</td>
                      <td className="py-3 px-4">{formatRelativeTime(ncr.createdAt)}</td>
                      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Eye className="mr-2 h-4 w-4" />
                              View
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Shield className="mr-2 h-4 w-4" />
                              Create CAPA
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function CAPAsTab() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [typeFilter, setTypeFilter] = React.useState<string>('all');

  const filteredCAPAs = mockCAPAs.filter((capa) => {
    const matchesSearch = searchQuery === '' ||
      capa.capaNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      capa.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || capa.status === statusFilter;
    const matchesType = typeFilter === 'all' || capa.type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search CAPAs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="implementing">Implementing</SelectItem>
              <SelectItem value="verifying">Verifying</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
            </SelectContent>
          </Select>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-[130px]">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              <SelectItem value="corrective">Corrective</SelectItem>
              <SelectItem value="preventive">Preventive</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">CAPA</th>
                  <th className="py-3 px-4 text-left font-medium">Title</th>
                  <th className="py-3 px-4 text-left font-medium">Type</th>
                  <th className="py-3 px-4 text-left font-medium">Priority</th>
                  <th className="py-3 px-4 text-left font-medium">Status</th>
                  <th className="py-3 px-4 text-left font-medium">Source NCR</th>
                  <th className="py-3 px-4 text-left font-medium">Due Date</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filteredCAPAs.map((capa) => {
                  const statusCfg = capaStatusConfig[capa.status];
                  const priorityCfg = priorityConfig[capa.priority];
                  const isOverdue = new Date(capa.dueDate) < new Date() && capa.status !== 'closed';
                  return (
                    <tr 
                      key={capa.id}
                      className="border-b hover:bg-muted/50 cursor-pointer"
                      onClick={() => router.push(`/quality/capas/${capa.id}`)}
                    >
                      <td className="py-3 px-4 font-medium">{capa.capaNumber}</td>
                      <td className="py-3 px-4">{capa.title}</td>
                      <td className="py-3 px-4 capitalize">{capa.type}</td>
                      <td className="py-3 px-4">
                        <Badge variant={priorityCfg.variant}>{priorityCfg.label}</Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={statusCfg.variant}>{statusCfg.label}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{capa.sourceNCR || '—'}</td>
                      <td className={cn('py-3 px-4', isOverdue && 'text-danger font-medium')}>
                        {formatDate(new Date(capa.dueDate))}
                        {isOverdue && ' (overdue)'}
                      </td>
                      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Eye className="mr-2 h-4 w-4" />
                              View
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Edit className="mr-2 h-4 w-4" />
                              Edit
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function QualityPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = React.useState<TabType>(
    (searchParams.get('tab') as TabType) || 'inspections'
  );

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    router.push(`/quality?tab=${tab}`, { scroll: false });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Quality Management</h1>
          <p className="text-muted-foreground">Track inspections, NCRs, and corrective actions</p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push('/quality/inspections/new')}>
              <ClipboardCheck className="mr-2 h-4 w-4" />
              New Inspection
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push('/quality/ncrs/new')}>
              <AlertTriangle className="mr-2 h-4 w-4" />
              New NCR
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push('/quality/capas/new')}>
              <Shield className="mr-2 h-4 w-4" />
              New CAPA
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Stats */}
      <QualityStats />

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-4">
          <button
            onClick={() => handleTabChange('inspections')}
            className={cn(
              'pb-3 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'inspections'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            <ClipboardCheck className="inline-block mr-2 h-4 w-4" />
            Inspections
          </button>
          <button
            onClick={() => handleTabChange('ncrs')}
            className={cn(
              'pb-3 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'ncrs'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            <AlertTriangle className="inline-block mr-2 h-4 w-4" />
            NCRs
          </button>
          <button
            onClick={() => handleTabChange('capas')}
            className={cn(
              'pb-3 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'capas'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            <Shield className="inline-block mr-2 h-4 w-4" />
            CAPAs
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'inspections' && <InspectionsTab />}
      {activeTab === 'ncrs' && <NCRsTab />}
      {activeTab === 'capas' && <CAPAsTab />}
    </div>
  );
}

export default function QualityPage() {
  return (
    <Suspense fallback={
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-48 bg-muted animate-pulse rounded" />
            <div className="h-4 w-72 bg-muted animate-pulse rounded mt-2" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    }>
      <QualityPageContent />
    </Suspense>
  );
}
