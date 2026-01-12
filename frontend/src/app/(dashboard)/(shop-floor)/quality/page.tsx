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
import { cn } from '@/lib/utils';
import { useQualityStore } from '@/stores';
import {
  QualityInspection,
  NonConformanceReport,
  CAPA,
  InspectionType,
  InspectionStatus,
  NCRStatus,
  Severity as NCSeverity,
  NCRDisposition,
  CAPAStatus,
  CAPAType,
} from '@/types';

type TabType = 'inspections' | 'ncrs' | 'capas';

const inspectionStatusConfig: Record<string, any> = {
  pending: { label: 'Pending', variant: 'secondary' as const, icon: Clock },
  in_progress: { label: 'In Progress', variant: 'warning' as const, icon: Clock },
  completed: { label: 'Completed', variant: 'success' as const, icon: CheckCircle },
  cancelled: { label: 'Cancelled', variant: 'danger' as const, icon: XCircle },
  passed: { label: 'Passed', variant: 'success' as const, icon: CheckCircle },
  failed: { label: 'Failed', variant: 'danger' as const, icon: XCircle },
};

const ncrStatusConfig: Record<string, any> = {
  open: { label: 'Open', variant: 'warning' as const },
  investigating: { label: 'Investigating', variant: 'default' as const },
  pending_disposition: { label: 'Disposition', variant: 'secondary' as const },
  closed: { label: 'Closed', variant: 'success' as const },
  disposition: { label: 'Disposition', variant: 'secondary' as const },
};

const severityConfig: Record<string, any> = {
  critical: { label: 'Critical', variant: 'danger' as const },
  major: { label: 'Major', variant: 'warning' as const },
  minor: { label: 'Minor', variant: 'secondary' as const },
};

const capaStatusConfig: Record<string, any> = {
  open: { label: 'Open', variant: 'warning' as const },
  in_progress: { label: 'In Progress', variant: 'default' as const },
  pending_verification: { label: 'Verifying', variant: 'secondary' as const },
  verified: { label: 'Verified', variant: 'success' as const },
  closed: { label: 'Closed', variant: 'success' as const },
  implementing: { label: 'Implementing', variant: 'default' as const },
  verifying: { label: 'Verifying', variant: 'secondary' as const },
};

const priorityConfig = {
  high: { label: 'High', variant: 'danger' as const },
  medium: { label: 'Medium', variant: 'warning' as const },
  low: { label: 'Low', variant: 'secondary' as const },
};

function QualityStats() {
  const { totalInspections, totalNcrs, totalCapas } = useQualityStore();

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/10">
              <ClipboardCheck className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold">{totalInspections}</p>
              <p className="text-sm text-muted-foreground">Active Inspections</p>
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
              <p className="text-2xl font-bold">{totalNcrs}</p>
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
              <p className="text-2xl font-bold">{totalCapas}</p>
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
  const { inspections, fetchInspections, loading } = useQualityStore();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');

  React.useEffect(() => {
    fetchInspections();
  }, [fetchInspections]);

  const filteredInspections = inspections.filter((insp) => {
    const matchesSearch = searchQuery === '' ||
      insp.inspection_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      insp.product?.name?.toLowerCase().includes(searchQuery.toLowerCase());
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
                      <td className="py-3 px-4 font-medium">{insp.inspection_number}</td>
                      <td className="py-3 px-4 text-muted-foreground">{insp.work_order?.work_order_number || '—'}</td>
                      <td className="py-3 px-4">{insp.product?.name || '—'}</td>
                      <td className="py-3 px-4 capitalize">{insp.type.replace('_', ' ')}</td>
                      <td className="py-3 px-4">
                        <Badge variant={config?.variant || 'secondary'} className="gap-1">
                          <StatusIcon className="h-3 w-3" />
                          {config?.label || insp.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">{new Date(insp.inspection_date).toLocaleDateString()}</td>
                      <td className="py-3 px-4 text-muted-foreground">{insp.inspector?.full_name || '—'}</td>
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
  const { ncrs, fetchNCRs, loading } = useQualityStore();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [severityFilter, setSeverityFilter] = React.useState<string>('all');

  React.useEffect(() => {
    fetchNCRs();
  }, [fetchNCRs]);

  const filteredNCRs = ncrs.filter((ncr) => {
    const matchesSearch = searchQuery === '' ||
      ncr.ncr_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ncr.description.toLowerCase().includes(searchQuery.toLowerCase());
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
                      <td className="py-3 px-4 font-medium">{ncr.ncr_number}</td>
                      <td className="py-3 px-4 truncate max-w-[200px]">{ncr.description}</td>
                      <td className="py-3 px-4">
                        <Badge variant={severityCfg?.variant || 'secondary'}>{severityCfg?.label || ncr.severity}</Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={statusCfg?.variant || 'secondary'}>{statusCfg?.label || ncr.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{ncr.product?.name || '—'}</td>
                      <td className="py-3 px-4 text-right">{ncr.quantity_affected}</td>
                      <td className="py-3 px-4">{new Date(ncr.created_at).toLocaleDateString()}</td>
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
  const { capas, fetchCAPAs, loading } = useQualityStore();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [typeFilter, setTypeFilter] = React.useState<string>('all');

  React.useEffect(() => {
    fetchCAPAs();
  }, [fetchCAPAs]);

  const filteredCAPAs = capas.filter((capa) => {
    const matchesSearch = searchQuery === '' ||
      capa.capa_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
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
                  const isOverdue = new Date(capa.due_date) < new Date() && capa.status !== 'closed';
                  return (
                    <tr 
                      key={capa.id}
                      className="border-b hover:bg-muted/50 cursor-pointer"
                      onClick={() => router.push(`/quality/capas/${capa.id}`)}
                    >
                      <td className="py-3 px-4 font-medium">{capa.capa_number}</td>
                      <td className="py-3 px-4">{capa.title}</td>
                      <td className="py-3 px-4 capitalize">{capa.type}</td>
                      <td className="py-3 px-4 capitalize">
                        {capa.status === 'open' ? 'High' : 'Medium'}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={statusCfg?.variant || 'secondary'}>{statusCfg?.label || capa.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{capa.ncr_id?.substring(0, 8) || '—'}</td>
                      <td className={cn('py-3 px-4', isOverdue && 'text-danger font-medium')}>
                        {new Date(capa.due_date).toLocaleDateString()}
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
    <div className="space-y-6" data-testid="quality-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Quality Management</h1>
          <p className="text-muted-foreground">Track inspections, NCRs, and corrective actions</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => router.push('/quality/analytics')}>
            <TrendingUp className="mr-2 h-4 w-4" />
            Analytics
          </Button>
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
