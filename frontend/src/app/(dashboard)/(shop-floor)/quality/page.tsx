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
import { useQualityStore, useAnalyticsStore } from '@/stores';
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
  const { trends, fetchTrends } = useAnalyticsStore();

  React.useEffect(() => {
    if (trends.length === 0) {
      fetchTrends();
    }
  }, [fetchTrends, trends.length]);

  const fpyTrend = trends.find(t => t.metric.toLowerCase().includes('yield') || t.metric.toLowerCase() === 'fpy');
  const currentFPY = fpyTrend ? fpyTrend.current_value : 94.2;

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-warning/60">Active Sync Gates</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{totalInspections}</p>
            </div>
            <div className="p-3 rounded-2xl bg-warning/10 text-warning shadow-sm">
              <ClipboardCheck className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-danger/60">Global Anomalies</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-danger to-danger/70 mt-1">{totalNcrs}</p>
            </div>
            <div className="p-3 rounded-2xl bg-danger/10 text-danger shadow-sm">
              <AlertTriangle className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-primary/60">Resolution Protocols</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{totalCapas}</p>
            </div>
            <div className="p-3 rounded-2xl bg-primary/10 text-primary shadow-sm">
              <Shield className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-success/60">First Pass Velocity</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-success to-success/70 mt-1">{currentFPY}%</p>
            </div>
            <div className="p-3 rounded-2xl bg-success/10 text-success shadow-sm">
              <TrendingUp className="h-5 w-5" />
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
    <div className="space-y-8 page-fade-in" data-testid="quality-page">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Quality Assurance
          </h1>
          <p className="text-muted-foreground font-medium">Track inspections, NCRs, and corrective actions</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary" onClick={() => router.push('/quality/analytics')}>
            <TrendingUp className="mr-2 h-4 w-4" />
            Analytics
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="lg" className="rounded-xl shadow-glow subtle-shine">
                <Plus className="mr-2 h-4 w-4" />
                New Protocol
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
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden">
        <CardHeader className="pb-0 border-b border-border/10 bg-muted/5">
          <div className="flex gap-8">
            <button
              onClick={() => handleTabChange('inspections')}
              className={cn(
                'pb-4 px-1 text-xs font-bold uppercase tracking-widest transition-all relative group',
                activeTab === 'inspections'
                  ? 'text-primary'
                  : 'text-muted-foreground/60 hover:text-primary/80'
              )}
            >
              <div className="flex items-center gap-2">
                <ClipboardCheck className="h-4 w-4" />
                Sync Gates
              </div>
              {activeTab === 'inspections' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full shadow-glow" />
              )}
            </button>
            <button
              onClick={() => handleTabChange('ncrs')}
              className={cn(
                'pb-4 px-1 text-xs font-bold uppercase tracking-widest transition-all relative group',
                activeTab === 'ncrs'
                  ? 'text-primary'
                  : 'text-muted-foreground/60 hover:text-primary/80'
              )}
            >
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Anomalies (NCR)
              </div>
              {activeTab === 'ncrs' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full shadow-glow" />
              )}
            </button>
            <button
              onClick={() => handleTabChange('capas')}
              className={cn(
                'pb-4 px-1 text-xs font-bold uppercase tracking-widest transition-all relative group',
                activeTab === 'capas'
                  ? 'text-primary'
                  : 'text-muted-foreground/60 hover:text-primary/80'
              )}
            >
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Protocols (CAPA)
              </div>
              {activeTab === 'capas' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full shadow-glow" />
              )}
            </button>
          </div>
        </CardHeader>
        <CardContent className="pt-8">
          {activeTab === 'inspections' && <InspectionsTab />}
          {activeTab === 'ncrs' && <NCRsTab />}
          {activeTab === 'capas' && <CAPAsTab />}
        </CardContent>
      </Card>
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
