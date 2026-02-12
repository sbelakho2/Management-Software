'use client';

import * as React from 'react';
import { Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
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
  Ruler,
  Gauge,
  Smile,
  FileCheck,
  ClipboardList,
  FlaskConical,
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
import { Pagination } from '@/components/ui/pagination';
import { useQualityStore, useAnalyticsStore } from '@/stores';

const QA_PAGE_SIZE = 15;
function useQaPagination<T>(items: T[], deps: unknown[] = []) {
  const [page, setPage] = React.useState(1);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  React.useEffect(() => setPage(1), deps);
  const totalPages = Math.max(1, Math.ceil(items.length / QA_PAGE_SIZE));
  const paginated = items.slice((page - 1) * QA_PAGE_SIZE, page * QA_PAGE_SIZE);
  return { page, setPage, totalPages, paginated, total: items.length };
}
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
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

type TabType = 'inspections' | 'ncrs' | 'capas' | 'msa' | 'capability' | 'customer' | 'fai' | 'self' | 'lab' | 'aql' | 'traceability' | 'change-point' | 'management-review';

const inspectionStatusConfig: Record<string, any> = {
  pending: { labelKey: 'common.pending', variant: 'secondary' as const, icon: Clock },
  in_progress: { labelKey: 'common.inProgress', variant: 'warning' as const, icon: Clock },
  completed: { labelKey: 'common.completed', variant: 'success' as const, icon: CheckCircle },
  cancelled: { labelKey: 'common.cancelled', variant: 'danger' as const, icon: XCircle },
  passed: { labelKey: 'pages.quality.status.passed', variant: 'success' as const, icon: CheckCircle },
  failed: { labelKey: 'pages.quality.status.failed', variant: 'danger' as const, icon: XCircle },
};

const ncrStatusConfig: Record<string, any> = {
  open: { labelKey: 'pages.quality.status.open', variant: 'warning' as const },
  investigating: { labelKey: 'pages.quality.status.investigating', variant: 'default' as const },
  pending_disposition: { labelKey: 'pages.quality.status.disposition', variant: 'secondary' as const },
  closed: { labelKey: 'pages.quality.status.closed', variant: 'success' as const },
  disposition: { labelKey: 'pages.quality.status.disposition', variant: 'secondary' as const },
};

const severityConfig: Record<string, any> = {
  critical: { labelKey: 'common.critical', variant: 'danger' as const },
  major: { labelKey: 'pages.quality.severity.major', variant: 'warning' as const },
  minor: { labelKey: 'pages.quality.severity.minor', variant: 'secondary' as const },
};

const capaStatusConfig: Record<string, any> = {
  open: { labelKey: 'pages.quality.status.open', variant: 'warning' as const },
  in_progress: { labelKey: 'common.inProgress', variant: 'default' as const },
  investigating: { labelKey: 'pages.quality.status.investigating', variant: 'default' as const },
  implementing: { labelKey: 'pages.quality.status.implementing', variant: 'default' as const },
  verification: { labelKey: 'pages.quality.status.verifying', variant: 'secondary' as const },
  verifying: { labelKey: 'pages.quality.status.verifying', variant: 'secondary' as const },
  effectiveness_check: { labelKey: 'pages.quality.status.effectivenessCheck', variant: 'secondary' as const },
  effective: { labelKey: 'pages.quality.status.effective', variant: 'success' as const },
  closed: { labelKey: 'pages.quality.status.closed', variant: 'success' as const },
  ineffective: { labelKey: 'pages.quality.status.ineffective', variant: 'danger' as const },
  on_hold: { labelKey: 'pages.quality.status.onHold', variant: 'secondary' as const },
};

const priorityConfig = {
  high: { labelKey: 'common.priority.high', variant: 'danger' as const },
  medium: { labelKey: 'common.priority.medium', variant: 'warning' as const },
  low: { labelKey: 'common.priority.low', variant: 'secondary' as const },
};

const msaStatusConfig: Record<string, any> = {
  in_progress: { labelKey: 'common.inProgress', variant: 'warning' as const },
  completed: { labelKey: 'common.completed', variant: 'success' as const },
  cancelled: { labelKey: 'common.cancelled', variant: 'secondary' as const },
};

const msaStudyTypeLabels: Record<string, string> = {
  grr: 'GRR',
  bias: 'Bias',
  linearity: 'Linearity',
  stability: 'Stability',
};

const capabilityStatusConfig: Record<string, any> = {
  in_progress: { labelKey: 'common.inProgress', variant: 'warning' as const },
  completed: { labelKey: 'common.completed', variant: 'success' as const },
  cancelled: { labelKey: 'common.cancelled', variant: 'secondary' as const },
};

const complaintStatusConfig: Record<string, any> = {
  received: { labelKey: 'common.new', variant: 'warning' as const },
  under_review: { labelKey: 'pages.quality.status.review', variant: 'secondary' as const },
  investigation: { labelKey: 'pages.quality.status.investigate', variant: 'default' as const },
  containment: { labelKey: 'pages.quality.status.contain', variant: 'secondary' as const },
  capa: { labelKey: 'pages.quality.status.capa', variant: 'default' as const },
  closed: { labelKey: 'pages.quality.status.closed', variant: 'success' as const },
  cancelled: { labelKey: 'common.cancelled', variant: 'secondary' as const },
};

const faiStatusConfig: Record<string, any> = {
  in_progress: { labelKey: 'common.inProgress', variant: 'warning' as const },
  completed: { labelKey: 'common.completed', variant: 'success' as const },
  cancelled: { labelKey: 'common.cancelled', variant: 'secondary' as const },
};

const selfInspectionStatusConfig: Record<string, any> = {
  in_progress: { labelKey: 'common.inProgress', variant: 'warning' as const },
  completed: { labelKey: 'common.completed', variant: 'success' as const },
  cancelled: { labelKey: 'common.cancelled', variant: 'secondary' as const },
};

function QualityStats() {
  const { t } = useI18n();
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
    <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('quality.stats.activeSyncGates') || 'Active Sync Gates'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{totalInspections}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('quality.stats.globalAnomalies') || 'Global Anomalies'}</p>
        <p className={cn('text-3xl font-mono font-bold tracking-tight tabular-nums', totalNcrs > 0 ? 'text-rams-red' : 'text-foreground/90')}
           aria-label={`${totalNcrs} anomalies${totalNcrs > 0 ? ' — attention needed' : ''}`}>
          {totalNcrs}
          {totalNcrs > 0 && <span className="sr-only"> — attention needed</span>}
        </p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('quality.stats.resolutionProtocols') || 'Resolution Protocols'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{totalCapas}</p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-line">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('quality.stats.firstPassVelocity') || 'First Pass Velocity'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums" aria-label={`First pass yield: ${currentFPY}%`}>{currentFPY}%</p>
      </div>
    </div>
  );
}

function InspectionsTab() {
  const { t } = useI18n();
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

  const { page: inspPage, setPage: setInspPage, totalPages: inspTotalPages, paginated: paginatedInspections, total: inspTotal } = useQaPagination(filteredInspections, [searchQuery, statusFilter]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('pages.quality.inspections.searchPlaceholder') || 'Search inspections...'}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder={t('common.status') || 'Status'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('pages.quality.filters.allStatuses') || 'All statuses'}</SelectItem>
              <SelectItem value="pending">{t('common.pending') || 'Pending'}</SelectItem>
              <SelectItem value="in_progress">{t('common.inProgress') || 'In Progress'}</SelectItem>
              <SelectItem value="passed">{t('pages.quality.status.passed') || 'Passed'}</SelectItem>
              <SelectItem value="failed">{t('pages.quality.status.failed') || 'Failed'}</SelectItem>
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
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.inspection') || 'Inspection'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.workOrder') || 'Work Order'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.product') || 'Product'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.type') || 'Type'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.scheduled') || 'Scheduled'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.inspector') || 'Inspector'}</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {paginatedInspections.map((insp) => {
                  const config = inspectionStatusConfig[insp.status];
                  const StatusIcon = config.icon;
                  return (
                    <tr 
                      key={insp.id}
                      className="border-b hover:bg-muted/50 cursor-pointer"
                      role="link"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); router.push(`/quality/inspections/${insp.id}`); } }}
                      onClick={() => router.push(`/quality/inspections/${insp.id}`)}
                    >
                      <td className="py-3 px-4 font-medium">{insp.inspection_number}</td>
                      <td className="py-3 px-4 text-muted-foreground">{insp.work_order?.work_order_number || '—'}</td>
                      <td className="py-3 px-4">{insp.product?.name || '—'}</td>
                      <td className="py-3 px-4 capitalize">{insp.type.replace('_', ' ')}</td>
                      <td className="py-3 px-4">
                        <Badge variant={config?.variant || 'secondary'} className="gap-1">
                          <StatusIcon className="h-3 w-3" />
                          {config?.labelKey ? t(config.labelKey) : insp.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">{new Date(insp.inspection_date).toLocaleDateString()}</td>
                      <td className="py-3 px-4 text-muted-foreground">{insp.inspector?.full_name || '—'}</td>
                      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm" aria-label="Actions">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Eye className="mr-2 h-4 w-4" />
                              {t('common.view') || 'View'}
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <ClipboardCheck className="mr-2 h-4 w-4" />
                              {t('pages.quality.actions.startInspection') || 'Start Inspection'}
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
      <Pagination currentPage={inspPage} totalPages={inspTotalPages} onPageChange={setInspPage} totalItems={inspTotal} />
    </div>
  );
}

function MSATab() {
  const { t } = useI18n();
  const {
    msaStudies,
    fetchMsaStudies,
    createMsaStudy,
    addMsaMeasurement,
    computeMsaStudy,
    loading,
  } = useQualityStore();
  const [studyForm, setStudyForm] = React.useState({
    gaugeId: '',
    name: '',
    studyType: 'grr',
    partsCount: 10,
    operatorsCount: 3,
    trialsCount: 2,
    notes: '',
  });
  const [measurementForm, setMeasurementForm] = React.useState({
    studyId: '',
    operatorId: '',
    partId: '',
    trialNumber: 1,
    measuredValue: '',
  });

  React.useEffect(() => {
    fetchMsaStudies();
  }, [fetchMsaStudies]);

  const handleCreateStudy = async () => {
    if (!studyForm.gaugeId || !studyForm.name) {
      return;
    }
    await createMsaStudy({
      gauge_id: studyForm.gaugeId,
      name: studyForm.name,
      study_type: studyForm.studyType as any,
      parts_count: Number(studyForm.partsCount),
      operators_count: Number(studyForm.operatorsCount),
      trials_count: Number(studyForm.trialsCount),
      notes: studyForm.notes || undefined,
    });
    setStudyForm({
      gaugeId: '',
      name: '',
      studyType: 'grr',
      partsCount: 10,
      operatorsCount: 3,
      trialsCount: 2,
      notes: '',
    });
  };

  const handleAddMeasurement = async () => {
    if (!measurementForm.studyId || !measurementForm.operatorId || !measurementForm.partId || measurementForm.measuredValue === '') {
      return;
    }
    await addMsaMeasurement(measurementForm.studyId, {
      operator_id: measurementForm.operatorId,
      part_id: measurementForm.partId,
      trial_number: Number(measurementForm.trialNumber),
      measured_value: Number(measurementForm.measuredValue),
    });
    setMeasurementForm({
      studyId: '',
      operatorId: '',
      partId: '',
      trialNumber: 1,
      measuredValue: '',
    });
  };

  return (
    <div className="space-y-6">
      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.msa.createStudy') || 'Create MSA Study'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.gaugeId') || 'Gauge ID'}</label>
              <Input
                value={studyForm.gaugeId}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, gaugeId: e.target.value }))}
                placeholder={t('pages.quality.msa.gaugeIdPlaceholder') || 'Gauge UUID'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.studyName') || 'Study Name'}</label>
              <Input
                value={studyForm.name}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, name: e.target.value }))}
                placeholder={t('pages.quality.msa.studyNamePlaceholder') || 'e.g., Line 2 CMM GRR'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.studyType') || 'Study Type'}</label>
              <Select
                value={studyForm.studyType}
                onValueChange={(value) => setStudyForm((prev) => ({ ...prev, studyType: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t('pages.quality.msa.selectType') || 'Select type'} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="grr">GRR</SelectItem>
                  <SelectItem value="bias">Bias</SelectItem>
                  <SelectItem value="linearity">Linearity</SelectItem>
                  <SelectItem value="stability">Stability</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.parts') || 'Parts'}</label>
              <Input
                type="number"
                value={studyForm.partsCount}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, partsCount: Number(e.target.value) }))}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.operators') || 'Operators'}</label>
              <Input
                type="number"
                value={studyForm.operatorsCount}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, operatorsCount: Number(e.target.value) }))}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.trials') || 'Trials'}</label>
              <Input
                type="number"
                value={studyForm.trialsCount}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, trialsCount: Number(e.target.value) }))}
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.notes') || 'Notes'}</label>
            <Input
              value={studyForm.notes}
              onChange={(e) => setStudyForm((prev) => ({ ...prev, notes: e.target.value }))}
              placeholder={t('pages.quality.msa.optionalNotes') || 'Optional notes'}
            />
          </div>
          <div className="flex justify-end">
            <Button onClick={handleCreateStudy} disabled={loading}>
              {t('pages.quality.msa.createStudyButton') || 'Create Study'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.msa.addMeasurement') || 'Add Measurement'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.study') || 'Study'}</label>
              <Select
                value={measurementForm.studyId}
                onValueChange={(value) => setMeasurementForm((prev) => ({ ...prev, studyId: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t('pages.quality.msa.selectStudy') || 'Select study'} />
                </SelectTrigger>
                <SelectContent>
                  {msaStudies.map((study) => (
                    <SelectItem key={study.id} value={study.id}>
                      {study.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.operatorId') || 'Operator ID'}</label>
              <Input
                value={measurementForm.operatorId}
                onChange={(e) => setMeasurementForm((prev) => ({ ...prev, operatorId: e.target.value }))}
                placeholder={t('pages.quality.msa.operatorPlaceholder') || 'Operator UUID'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.partId') || 'Part ID'}</label>
              <Input
                value={measurementForm.partId}
                onChange={(e) => setMeasurementForm((prev) => ({ ...prev, partId: e.target.value }))}
                placeholder={t('pages.quality.msa.partPlaceholder') || 'Part identifier'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.trial') || 'Trial'}</label>
              <Input
                type="number"
                value={measurementForm.trialNumber}
                onChange={(e) => setMeasurementForm((prev) => ({ ...prev, trialNumber: Number(e.target.value) }))}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.msa.measuredValue') || 'Measured Value'}</label>
              <Input
                type="number"
                value={measurementForm.measuredValue}
                onChange={(e) => setMeasurementForm((prev) => ({ ...prev, measuredValue: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button variant="outline" onClick={handleAddMeasurement} disabled={loading}>
              {t('pages.quality.msa.addMeasurementButton') || 'Add Measurement'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.msa.study') || 'Study'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.msa.gauge') || 'Gauge'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.type') || 'Type'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.msa.design') || 'Design'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.msa.grrPercent') || 'GRR %'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.msa.ndc') || 'NDC'}</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {msaStudies.map((study) => {
                  const statusConfig = msaStatusConfig[study.status] || { labelKey: study.status, variant: 'secondary' };
                  const grrPercent = study.result?.grr_percent;
                  return (
                    <tr key={study.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{study.name}</td>
                      <td className="py-3 px-4 text-muted-foreground">{study.gauge_id.slice(0, 8)}…</td>
                      <td className="py-3 px-4">{msaStudyTypeLabels[study.study_type] || study.study_type}</td>
                      <td className="py-3 px-4">
                        <Badge variant={statusConfig.variant}>
                          {statusConfig.labelKey ? t(statusConfig.labelKey) : study.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {study.parts_count}x{study.operators_count}x{study.trials_count}
                      </td>
                      <td className="py-3 px-4">
                        {grrPercent !== undefined ? `${Number(grrPercent).toFixed(1)}%` : '—'}
                      </td>
                      <td className="py-3 px-4">{study.result?.ndc ?? '—'}</td>
                      <td className="py-3 px-4">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => computeMsaStudy(study.id)}
                          disabled={loading}
                          aria-label={t('pages.quality.msa.computeGRR') || 'Compute GRR'}
                        >
                          <Ruler className="h-4 w-4" />
                        </Button>
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

function CapabilityTab() {
  const { t } = useI18n();
  const {
    capabilityStudies,
    fetchCapabilityStudies,
    createCapabilityStudy,
    addCapabilityMeasurement,
    computeCapabilityStudy,
    loading,
  } = useQualityStore();
  const [studyForm, setStudyForm] = React.useState({
    name: '',
    processName: '',
    characteristic: '',
    lsl: '',
    usl: '',
    target: '',
    unit: '',
    notes: '',
  });
  const [measurementForm, setMeasurementForm] = React.useState({
    studyId: '',
    measuredValue: '',
    sampleLabel: '',
  });

  React.useEffect(() => {
    fetchCapabilityStudies();
  }, [fetchCapabilityStudies]);

  const handleCreateStudy = async () => {
    if (!studyForm.name || !studyForm.processName || !studyForm.characteristic || studyForm.lsl === '' || studyForm.usl === '') {
      return;
    }
    await createCapabilityStudy({
      name: studyForm.name,
      process_name: studyForm.processName,
      characteristic: studyForm.characteristic,
      lsl: Number(studyForm.lsl),
      usl: Number(studyForm.usl),
      target: studyForm.target !== '' ? Number(studyForm.target) : undefined,
      unit: studyForm.unit || undefined,
      notes: studyForm.notes || undefined,
    });
    setStudyForm({
      name: '',
      processName: '',
      characteristic: '',
      lsl: '',
      usl: '',
      target: '',
      unit: '',
      notes: '',
    });
  };

  const handleAddMeasurement = async () => {
    if (!measurementForm.studyId || measurementForm.measuredValue === '') {
      return;
    }
    await addCapabilityMeasurement(measurementForm.studyId, {
      measured_value: Number(measurementForm.measuredValue),
      sample_label: measurementForm.sampleLabel || undefined,
    });
    setMeasurementForm({
      studyId: '',
      measuredValue: '',
      sampleLabel: '',
    });
  };

  return (
    <div className="space-y-6">
      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.capability.createStudy') || 'Create Capability Study'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.capability.studyName') || 'Study Name'}</label>
              <Input
                value={studyForm.name}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, name: e.target.value }))}
                placeholder={t('pages.quality.capability.studyNamePlaceholder') || 'e.g., CNC Mill 1 Diameter'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.capability.process') || 'Process'}</label>
              <Input
                value={studyForm.processName}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, processName: e.target.value }))}
                placeholder={t('pages.quality.capability.processPlaceholder') || 'e.g., CNC Mill 1'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.capability.characteristic') || 'Characteristic'}</label>
              <Input
                value={studyForm.characteristic}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, characteristic: e.target.value }))}
                placeholder={t('pages.quality.capability.characteristicPlaceholder') || 'e.g., Bore Diameter'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.capability.lsl') || 'LSL'}</label>
              <Input
                type="number"
                value={studyForm.lsl}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, lsl: e.target.value }))}
                placeholder={t('pages.quality.capability.lslPlaceholder') || 'Lower spec limit'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.capability.usl') || 'USL'}</label>
              <Input
                type="number"
                value={studyForm.usl}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, usl: e.target.value }))}
                placeholder={t('pages.quality.capability.uslPlaceholder') || 'Upper spec limit'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('common.target') || 'Target'}</label>
              <Input
                type="number"
                value={studyForm.target}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, target: e.target.value }))}
                placeholder={t('pages.quality.capability.targetPlaceholder') || 'Optional target'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.capability.unit') || 'Unit'}</label>
              <Input
                value={studyForm.unit}
                onChange={(e) => setStudyForm((prev) => ({ ...prev, unit: e.target.value }))}
                placeholder={t('pages.quality.capability.unitPlaceholder') || 'mm, in, etc.'}
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.capability.notes') || 'Notes'}</label>
            <Input
              value={studyForm.notes}
              onChange={(e) => setStudyForm((prev) => ({ ...prev, notes: e.target.value }))}
              placeholder={t('pages.quality.capability.optionalNotes') || 'Optional notes'}
            />
          </div>
          <div className="flex justify-end">
            <Button onClick={handleCreateStudy} disabled={loading}>
              {t('pages.quality.capability.createStudyButton') || 'Create Study'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.capability.addMeasurement') || 'Add Measurement'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.capability.studyLabel') || 'Study'}</label>
              <Select
                value={measurementForm.studyId}
                onValueChange={(value) => setMeasurementForm((prev) => ({ ...prev, studyId: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t('pages.quality.capability.selectStudy') || 'Select study'} />
                </SelectTrigger>
                <SelectContent>
                  {capabilityStudies.map((study) => (
                    <SelectItem key={study.id} value={study.id}>
                      {study.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.capability.measuredValue') || 'Measured Value'}</label>
              <Input
                type="number"
                value={measurementForm.measuredValue}
                onChange={(e) => setMeasurementForm((prev) => ({ ...prev, measuredValue: e.target.value }))}
                placeholder={t('pages.quality.capability.measurementPlaceholder') || 'Measurement'}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.capability.sampleLabel') || 'Sample Label'}</label>
              <Input
                value={measurementForm.sampleLabel}
                onChange={(e) => setMeasurementForm((prev) => ({ ...prev, sampleLabel: e.target.value }))}
                placeholder={t('pages.quality.capability.sampleLabelPlaceholder') || 'Optional label'}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button variant="outline" onClick={handleAddMeasurement} disabled={loading}>
              {t('pages.quality.capability.addMeasurementButton') || 'Add Measurement'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.capability.studyLabel') || 'Study'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.capability.process') || 'Process'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.capability.characteristic') || 'Characteristic'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.capability.specs') || 'Specs'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('quality.capability.cp') || 'Cp'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.capability.cpk') || 'Cpk'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {capabilityStudies.map((study) => {
                  const statusConfig = capabilityStatusConfig[study.status] || { labelKey: study.status, variant: 'secondary' };
                  return (
                    <tr key={study.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{study.name}</td>
                      <td className="py-3 px-4 text-muted-foreground">{study.process_name}</td>
                      <td className="py-3 px-4">{study.characteristic}</td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {study.lsl} - {study.usl} {study.unit || ''}
                      </td>
                      <td className="py-3 px-4">{study.result?.cp !== undefined ? Number(study.result.cp).toFixed(2) : '—'}</td>
                      <td className="py-3 px-4">{study.result?.cpk !== undefined ? Number(study.result.cpk).toFixed(2) : '—'}</td>
                      <td className="py-3 px-4">
                        <Badge variant={statusConfig.variant}>{statusConfig.labelKey ? t(statusConfig.labelKey) : study.status}</Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => computeCapabilityStudy(study.id)}
                          disabled={loading}
                          aria-label={t('pages.quality.capability.computeCpCpk') || 'Compute Cp/Cpk'}
                        >
                          <Gauge className="h-4 w-4" />
                        </Button>
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

function CustomerSatisfactionTab() {
  const { t } = useI18n();
  const {
    customerComplaints,
    customerSurveys,
    customerSatisfactionStats,
    fetchCustomerComplaints,
    fetchCustomerSurveys,
    fetchCustomerSatisfactionStats,
    createCustomerComplaint,
    closeCustomerComplaint,
    createCustomerSurvey,
    addCustomerSurveyResponse,
    loading,
  } = useQualityStore();

  const [complaintForm, setComplaintForm] = React.useState({
    customerId: '',
    title: '',
    description: '',
    status: 'received',
    rmaNumber: '',
  });
  const [surveyForm, setSurveyForm] = React.useState({
    title: '',
    description: '',
    targetResponses: '',
  });
  const [responseForm, setResponseForm] = React.useState({
    surveyId: '',
    respondentName: '',
    respondentEmail: '',
    npsScore: '9',
    comment: '',
  });

  React.useEffect(() => {
    fetchCustomerComplaints();
    fetchCustomerSurveys();
    fetchCustomerSatisfactionStats();
  }, [fetchCustomerComplaints, fetchCustomerSurveys, fetchCustomerSatisfactionStats]);

  const handleCreateComplaint = async () => {
    if (!complaintForm.title || !complaintForm.description) {
      return;
    }
    await createCustomerComplaint({
      customer_id: complaintForm.customerId || undefined,
      title: complaintForm.title,
      description: complaintForm.description,
      status: complaintForm.status,
      rma_number: complaintForm.rmaNumber || undefined,
    });
    setComplaintForm({ customerId: '', title: '', description: '', status: 'received', rmaNumber: '' });
  };

  const handleCreateSurvey = async () => {
    if (!surveyForm.title) {
      return;
    }
    await createCustomerSurvey({
      title: surveyForm.title,
      description: surveyForm.description || undefined,
      target_responses: surveyForm.targetResponses ? Number(surveyForm.targetResponses) : undefined,
    });
    setSurveyForm({ title: '', description: '', targetResponses: '' });
  };

  const handleAddResponse = async () => {
    if (!responseForm.surveyId) {
      return;
    }
    await addCustomerSurveyResponse(responseForm.surveyId, {
      respondent_name: responseForm.respondentName || undefined,
      respondent_email: responseForm.respondentEmail || undefined,
      nps_score: Number(responseForm.npsScore),
      comment: responseForm.comment || undefined,
    });
    setResponseForm({ surveyId: '', respondentName: '', respondentEmail: '', npsScore: '9', comment: '' });
  };

  const stats = customerSatisfactionStats?.nps;
  const complaintStats = customerSatisfactionStats?.complaints;

  return (
    <div className="space-y-6">
      <div className="grid gap-0 md:grid-cols-3 border border-rams-line bg-rams-line">
        <Card className="bg-rams-module border-0 shadow-none">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-2">{t('pages.quality.npsScore') || 'NPS Score'}</p>
                <p className="text-3xl font-mono font-bold tabular-nums">{stats ? stats.nps_score : '—'}</p>
              </div>
              <div className="p-3 bg-rams-panel border border-rams-line text-rams-steel">
                <Smile className="h-5 w-5" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-rams-module border-0 border-x border-rams-line shadow-none">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-orange/60 mb-2">{t('pages.quality.openComplaints') || 'Open Complaints'}</p>
                <p className="text-3xl font-mono font-bold tabular-nums">{complaintStats ? complaintStats.open : '—'}</p>
              </div>
              <div className="p-3 bg-rams-orange/10 border border-rams-orange/20 text-rams-orange">
                <AlertTriangle className="h-5 w-5" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-rams-module border-0 shadow-none">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-green/60 mb-2">{t('pages.quality.responses') || 'Responses'}</p>
                <p className="text-3xl font-mono font-bold tabular-nums">{stats ? stats.total_responses : '—'}</p>
              </div>
              <div className="p-3 bg-rams-green/10 border border-rams-green/20 text-rams-green">
                <CheckCircle className="h-5 w-5" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.logComplaint') || 'Log Customer Complaint'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              placeholder={t('pages.quality.placeholder.customerId') || 'Customer ID (optional)'}
              value={complaintForm.customerId}
              onChange={(e) => setComplaintForm((prev) => ({ ...prev, customerId: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.rmaNumber') || 'RMA Number (optional)'}
              value={complaintForm.rmaNumber}
              onChange={(e) => setComplaintForm((prev) => ({ ...prev, rmaNumber: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.complaintTitle') || 'Complaint title'}
              value={complaintForm.title}
              onChange={(e) => setComplaintForm((prev) => ({ ...prev, title: e.target.value }))}
            />
            <Select
              value={complaintForm.status}
              onValueChange={(value) => setComplaintForm((prev) => ({ ...prev, status: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('common.status') || 'Status'} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="received">{t('pages.quality.status.received') || 'Received'}</SelectItem>
                <SelectItem value="under_review">{t('pages.quality.status.underReview') || 'Under Review'}</SelectItem>
                <SelectItem value="investigation">{t('pages.quality.status.investigation') || 'Investigation'}</SelectItem>
                <SelectItem value="containment">{t('pages.quality.status.containment') || 'Containment'}</SelectItem>
                <SelectItem value="capa">{t('pages.quality.status.capa') || 'CAPA'}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Input
            placeholder={t('common.description') || 'Description'}
            value={complaintForm.description}
            onChange={(e) => setComplaintForm((prev) => ({ ...prev, description: e.target.value }))}
          />
          <div className="flex justify-end">
            <Button onClick={handleCreateComplaint} disabled={loading}>{t('pages.quality.createComplaint') || 'Create Complaint'}</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.complaint') || 'Complaint'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.status.received') || 'Received'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.rma') || 'RMA'}</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {customerComplaints.map((complaint) => {
                  const statusConfig = complaintStatusConfig[complaint.status] || { labelKey: complaint.status, variant: 'secondary' };
                  return (
                    <tr key={complaint.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{complaint.title}</td>
                      <td className="py-3 px-4">
                        <Badge variant={statusConfig.variant}>{statusConfig.labelKey ? t(statusConfig.labelKey) : complaint.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {new Date(complaint.received_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{complaint.rma_number || '—'}</td>
                      <td className="py-3 px-4">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => closeCustomerComplaint(complaint.id)}
                          disabled={loading || complaint.status === 'closed'}
                          aria-label={t('pages.quality.aria.closeComplaint') || 'Close complaint'}
                        >
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.createNPSSurvey') || 'Create NPS Survey'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              placeholder={t('pages.quality.placeholder.surveyTitle') || 'Survey title'}
              value={surveyForm.title}
              onChange={(e) => setSurveyForm((prev) => ({ ...prev, title: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.targetResponses') || 'Target responses'}
              type="number"
              value={surveyForm.targetResponses}
              onChange={(e) => setSurveyForm((prev) => ({ ...prev, targetResponses: e.target.value }))}
            />
          </div>
          <Input
            placeholder={t('common.description') || 'Description'}
            value={surveyForm.description}
            onChange={(e) => setSurveyForm((prev) => ({ ...prev, description: e.target.value }))}
          />
          <div className="flex justify-end">
            <Button onClick={handleCreateSurvey} disabled={loading}>{t('pages.quality.createSurvey') || 'Create Survey'}</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.addSurveyResponse') || 'Add Survey Response'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Select
              value={responseForm.surveyId}
              onValueChange={(value) => setResponseForm((prev) => ({ ...prev, surveyId: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('pages.quality.placeholder.selectSurvey') || 'Select survey'} />
              </SelectTrigger>
              <SelectContent>
                {customerSurveys.map((survey) => (
                  <SelectItem key={survey.id} value={survey.id}>
                    {survey.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              placeholder={t('pages.quality.placeholder.respondentName') || 'Respondent name'}
              value={responseForm.respondentName}
              onChange={(e) => setResponseForm((prev) => ({ ...prev, respondentName: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.respondentEmail') || 'Respondent email'}
              value={responseForm.respondentEmail}
              onChange={(e) => setResponseForm((prev) => ({ ...prev, respondentEmail: e.target.value }))}
            />
            <Input
              type="number"
              min={0}
              max={10}
              placeholder={t('pages.quality.placeholder.npsScore') || 'NPS score (0-10)'}
              value={responseForm.npsScore}
              onChange={(e) => setResponseForm((prev) => ({ ...prev, npsScore: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.comment') || 'Comment'}
              value={responseForm.comment}
              onChange={(e) => setResponseForm((prev) => ({ ...prev, comment: e.target.value }))}
            />
          </div>
          <div className="flex justify-end">
            <Button variant="outline" onClick={handleAddResponse} disabled={loading}>{t('pages.quality.addResponse') || 'Add Response'}</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function FAITab() {
  const { t } = useI18n();
  const {
    faiInspections,
    fetchFAIInspections,
    createFAIInspection,
    addFAICharacteristic,
    closeFAIInspection,
    loading,
  } = useQualityStore();

  const [inspectionForm, setInspectionForm] = React.useState({
    inspectionNumber: '',
    partNumber: '',
    revision: '',
    drawingNumber: '',
    productId: '',
    workOrderId: '',
    notes: '',
  });
  const [charForm, setCharForm] = React.useState({
    inspectionId: '',
    characteristicNumber: 1,
    requirement: '',
    nominal: '',
    tolerance: '',
    actual: '',
    result: 'pending',
    method: '',
    toolId: '',
  });

  React.useEffect(() => {
    fetchFAIInspections();
  }, [fetchFAIInspections]);

  const handleCreateInspection = async () => {
    if (!inspectionForm.inspectionNumber || !inspectionForm.partNumber) {
      return;
    }
    await createFAIInspection({
      inspection_number: inspectionForm.inspectionNumber,
      part_number: inspectionForm.partNumber,
      revision: inspectionForm.revision || undefined,
      drawing_number: inspectionForm.drawingNumber || undefined,
      product_id: inspectionForm.productId || undefined,
      work_order_id: inspectionForm.workOrderId || undefined,
      notes: inspectionForm.notes || undefined,
    });
    setInspectionForm({
      inspectionNumber: '',
      partNumber: '',
      revision: '',
      drawingNumber: '',
      productId: '',
      workOrderId: '',
      notes: '',
    });
  };

  const handleAddCharacteristic = async () => {
    if (!charForm.inspectionId || !charForm.requirement) {
      return;
    }
    await addFAICharacteristic(charForm.inspectionId, {
      characteristic_number: Number(charForm.characteristicNumber),
      requirement: charForm.requirement,
      nominal: charForm.nominal !== '' ? Number(charForm.nominal) : undefined,
      tolerance: charForm.tolerance || undefined,
      actual: charForm.actual !== '' ? Number(charForm.actual) : undefined,
      result: charForm.result,
      method: charForm.method || undefined,
      tool_id: charForm.toolId || undefined,
    });
    setCharForm({
      inspectionId: '',
      characteristicNumber: 1,
      requirement: '',
      nominal: '',
      tolerance: '',
      actual: '',
      result: 'pending',
      method: '',
      toolId: '',
    });
  };

  return (
    <div className="space-y-6">
      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.createFAI') || 'Create FAI (AS9102)'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Input
              placeholder={t('pages.quality.placeholder.inspectionNumber') || 'Inspection Number'}
              value={inspectionForm.inspectionNumber}
              onChange={(e) => setInspectionForm((prev) => ({ ...prev, inspectionNumber: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.partNumber') || 'Part Number'}
              value={inspectionForm.partNumber}
              onChange={(e) => setInspectionForm((prev) => ({ ...prev, partNumber: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.revision') || 'Revision'}
              value={inspectionForm.revision}
              onChange={(e) => setInspectionForm((prev) => ({ ...prev, revision: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.drawingNumber') || 'Drawing Number'}
              value={inspectionForm.drawingNumber}
              onChange={(e) => setInspectionForm((prev) => ({ ...prev, drawingNumber: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.productId') || 'Product ID'}
              value={inspectionForm.productId}
              onChange={(e) => setInspectionForm((prev) => ({ ...prev, productId: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.workOrderId') || 'Work Order ID'}
              value={inspectionForm.workOrderId}
              onChange={(e) => setInspectionForm((prev) => ({ ...prev, workOrderId: e.target.value }))}
            />
          </div>
          <Input
            placeholder={t('pages.quality.placeholder.notes') || 'Notes'}
            value={inspectionForm.notes}
            onChange={(e) => setInspectionForm((prev) => ({ ...prev, notes: e.target.value }))}
          />
          <div className="flex justify-end">
            <Button onClick={handleCreateInspection} disabled={loading}>{t('pages.quality.createFAI') || 'Create FAI'}</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.addCharacteristic') || 'Add Characteristic'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Select
              value={charForm.inspectionId}
              onValueChange={(value) => setCharForm((prev) => ({ ...prev, inspectionId: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('pages.quality.placeholder.selectFAI') || 'Select FAI'} />
              </SelectTrigger>
              <SelectContent>
                {faiInspections.map((inspection) => (
                  <SelectItem key={inspection.id} value={inspection.id}>
                    {inspection.inspection_number}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              type="number"
              placeholder={t('pages.quality.placeholder.characteristicNumber') || 'Characteristic #'}
              value={charForm.characteristicNumber}
              onChange={(e) => setCharForm((prev) => ({ ...prev, characteristicNumber: Number(e.target.value) }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.requirement') || 'Requirement'}
              value={charForm.requirement}
              onChange={(e) => setCharForm((prev) => ({ ...prev, requirement: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.nominal') || 'Nominal'}
              type="number"
              value={charForm.nominal}
              onChange={(e) => setCharForm((prev) => ({ ...prev, nominal: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.tolerance') || 'Tolerance'}
              value={charForm.tolerance}
              onChange={(e) => setCharForm((prev) => ({ ...prev, tolerance: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.actual') || 'Actual'}
              type="number"
              value={charForm.actual}
              onChange={(e) => setCharForm((prev) => ({ ...prev, actual: e.target.value }))}
            />
            <Select
              value={charForm.result}
              onValueChange={(value) => setCharForm((prev) => ({ ...prev, result: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('pages.quality.placeholder.result') || 'Result'} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pending">{t('common.pending') || 'Pending'}</SelectItem>
                <SelectItem value="pass">{t('pages.quality.status.pass') || 'Pass'}</SelectItem>
                <SelectItem value="fail">{t('pages.quality.status.fail') || 'Fail'}</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder={t('pages.quality.placeholder.method') || 'Method'}
              value={charForm.method}
              onChange={(e) => setCharForm((prev) => ({ ...prev, method: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.toolId') || 'Tool ID'}
              value={charForm.toolId}
              onChange={(e) => setCharForm((prev) => ({ ...prev, toolId: e.target.value }))}
            />
          </div>
          <div className="flex justify-end">
            <Button variant="outline" onClick={handleAddCharacteristic} disabled={loading}>{t('pages.quality.addCharacteristic') || 'Add Characteristic'}</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.fai') || 'FAI'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.part') || 'Part'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.revision') || 'Revision'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.chars') || 'Chars'}</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {faiInspections.map((inspection) => {
                  const statusConfig = faiStatusConfig[inspection.status] || { labelKey: inspection.status, variant: 'secondary' };
                  return (
                    <tr key={inspection.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{inspection.inspection_number}</td>
                      <td className="py-3 px-4 text-muted-foreground">{inspection.part_number}</td>
                      <td className="py-3 px-4 text-muted-foreground">{inspection.revision || '—'}</td>
                      <td className="py-3 px-4">
                        <Badge variant={statusConfig.variant}>{statusConfig.labelKey ? t(statusConfig.labelKey) : inspection.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {inspection.characteristics?.length ?? 0}
                      </td>
                      <td className="py-3 px-4">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => closeFAIInspection(inspection.id)}
                          disabled={loading || inspection.status === 'completed'}
                          aria-label={t('pages.quality.aria.closeFAI') || 'Close FAI'}
                        >
                          <CheckCircle className="h-4 w-4" />
                        </Button>
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

function SelfInspectionTab() {
  const { t } = useI18n();
  const {
    selfInspections,
    fetchSelfInspections,
    createSelfInspection,
    addSelfInspectionCheck,
    closeSelfInspection,
    loading,
  } = useQualityStore();

  const [inspectionForm, setInspectionForm] = React.useState({
    inspectionNumber: '',
    workOrderId: '',
    productId: '',
    notes: '',
  });
  const [checkForm, setCheckForm] = React.useState({
    inspectionId: '',
    characteristic: '',
    specification: '',
    actualValue: '',
    result: 'pending',
    notes: '',
  });

  React.useEffect(() => {
    fetchSelfInspections();
  }, [fetchSelfInspections]);

  const handleCreateInspection = async () => {
    if (!inspectionForm.inspectionNumber) {
      return;
    }
    await createSelfInspection({
      inspection_number: inspectionForm.inspectionNumber,
      work_order_id: inspectionForm.workOrderId || undefined,
      product_id: inspectionForm.productId || undefined,
      notes: inspectionForm.notes || undefined,
    });
    setInspectionForm({ inspectionNumber: '', workOrderId: '', productId: '', notes: '' });
  };

  const handleAddCheck = async () => {
    if (!checkForm.inspectionId || !checkForm.characteristic) {
      return;
    }
    await addSelfInspectionCheck(checkForm.inspectionId, {
      characteristic: checkForm.characteristic,
      specification: checkForm.specification || undefined,
      actual_value: checkForm.actualValue || undefined,
      result: checkForm.result,
      notes: checkForm.notes || undefined,
    });
    setCheckForm({
      inspectionId: '',
      characteristic: '',
      specification: '',
      actualValue: '',
      result: 'pending',
      notes: '',
    });
  };

  return (
    <div className="space-y-6">
      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.startSelfInspection') || 'Start Self Inspection'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Input
              placeholder={t('pages.quality.placeholder.inspectionNumber') || 'Inspection Number'}
              value={inspectionForm.inspectionNumber}
              onChange={(e) => setInspectionForm((prev) => ({ ...prev, inspectionNumber: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.workOrderId') || 'Work Order ID'}
              value={inspectionForm.workOrderId}
              onChange={(e) => setInspectionForm((prev) => ({ ...prev, workOrderId: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.productId') || 'Product ID'}
              value={inspectionForm.productId}
              onChange={(e) => setInspectionForm((prev) => ({ ...prev, productId: e.target.value }))}
            />
          </div>
          <Input
            placeholder={t('pages.quality.placeholder.notes') || 'Notes'}
            value={inspectionForm.notes}
            onChange={(e) => setInspectionForm((prev) => ({ ...prev, notes: e.target.value }))}
          />
          <div className="flex justify-end">
            <Button onClick={handleCreateInspection} disabled={loading}>{t('pages.quality.startInspection') || 'Start Inspection'}</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.addCheck') || 'Add Self-Check'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Select
              value={checkForm.inspectionId}
              onValueChange={(value) => setCheckForm((prev) => ({ ...prev, inspectionId: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('pages.quality.placeholder.selectInspection') || 'Select inspection'} />
              </SelectTrigger>
              <SelectContent>
                {selfInspections.map((inspection) => (
                  <SelectItem key={inspection.id} value={inspection.id}>
                    {inspection.inspection_number}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              placeholder={t('pages.quality.placeholder.characteristic') || 'Characteristic'}
              value={checkForm.characteristic}
              onChange={(e) => setCheckForm((prev) => ({ ...prev, characteristic: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.specification') || 'Specification'}
              value={checkForm.specification}
              onChange={(e) => setCheckForm((prev) => ({ ...prev, specification: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.actual') || 'Actual'}
              value={checkForm.actualValue}
              onChange={(e) => setCheckForm((prev) => ({ ...prev, actualValue: e.target.value }))}
            />
            <Select
              value={checkForm.result}
              onValueChange={(value) => setCheckForm((prev) => ({ ...prev, result: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('pages.quality.placeholder.result') || 'Result'} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pending">{t('common.pending') || 'Pending'}</SelectItem>
                <SelectItem value="pass">{t('pages.quality.status.pass') || 'Pass'}</SelectItem>
                <SelectItem value="fail">{t('pages.quality.status.fail') || 'Fail'}</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder={t('pages.quality.placeholder.notes') || 'Notes'}
              value={checkForm.notes}
              onChange={(e) => setCheckForm((prev) => ({ ...prev, notes: e.target.value }))}
            />
          </div>
          <div className="flex justify-end">
            <Button variant="outline" onClick={handleAddCheck} disabled={loading}>{t('pages.quality.addCheck') || 'Add Check'}</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.inspection') || 'Inspection'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.checks') || 'Checks'}</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {selfInspections.map((inspection) => {
                  const statusConfig = selfInspectionStatusConfig[inspection.status] || { labelKey: inspection.status, variant: 'secondary' };
                  return (
                    <tr key={inspection.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{inspection.inspection_number}</td>
                      <td className="py-3 px-4">
                        <Badge variant={statusConfig.variant}>{statusConfig.labelKey ? t(statusConfig.labelKey) : inspection.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{inspection.checks?.length ?? 0}</td>
                      <td className="py-3 px-4">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => closeSelfInspection(inspection.id)}
                          disabled={loading || inspection.status === 'completed'}
                          aria-label={t('pages.quality.aria.closeSelfInspection') || 'Close self inspection'}
                        >
                          <CheckCircle className="h-4 w-4" />
                        </Button>
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

function LabManagementTab() {
  const { t } = useI18n();
  const {
    labMethods,
    labSamples,
    fetchLabMethods,
    fetchLabSamples,
    createLabMethod,
    createLabSample,
    addLabTestRun,
    loading,
  } = useQualityStore();

  const [methodForm, setMethodForm] = React.useState({
    name: '',
    standard: '',
    unit: '',
    lowerSpec: '',
    upperSpec: '',
    targetValue: '',
  });
  const [sampleForm, setSampleForm] = React.useState({
    sampleNumber: '',
    productId: '',
    workOrderId: '',
    lotNumber: '',
  });
  const [testForm, setTestForm] = React.useState({
    sampleId: '',
    methodId: '',
    resultValue: '',
    resultStatus: 'pending',
    notes: '',
  });

  React.useEffect(() => {
    fetchLabMethods();
    fetchLabSamples();
  }, [fetchLabMethods, fetchLabSamples]);

  const handleCreateMethod = async () => {
    if (!methodForm.name) {
      return;
    }
    await createLabMethod({
      name: methodForm.name,
      standard: methodForm.standard || undefined,
      unit: methodForm.unit || undefined,
      lower_spec: methodForm.lowerSpec !== '' ? Number(methodForm.lowerSpec) : undefined,
      upper_spec: methodForm.upperSpec !== '' ? Number(methodForm.upperSpec) : undefined,
      target_value: methodForm.targetValue !== '' ? Number(methodForm.targetValue) : undefined,
    });
    setMethodForm({ name: '', standard: '', unit: '', lowerSpec: '', upperSpec: '', targetValue: '' });
  };

  const handleCreateSample = async () => {
    if (!sampleForm.sampleNumber) {
      return;
    }
    await createLabSample({
      sample_number: sampleForm.sampleNumber,
      product_id: sampleForm.productId || undefined,
      work_order_id: sampleForm.workOrderId || undefined,
      lot_number: sampleForm.lotNumber || undefined,
    });
    setSampleForm({ sampleNumber: '', productId: '', workOrderId: '', lotNumber: '' });
  };

  const handleAddTestRun = async () => {
    if (!testForm.sampleId || !testForm.methodId) {
      return;
    }
    await addLabTestRun(testForm.sampleId, {
      method_id: testForm.methodId,
      result_value: testForm.resultValue !== '' ? Number(testForm.resultValue) : undefined,
      result_status: testForm.resultStatus,
      notes: testForm.notes || undefined,
    });
    setTestForm({ sampleId: '', methodId: '', resultValue: '', resultStatus: 'pending', notes: '' });
  };

  return (
    <div className="space-y-6">
      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.createLabMethod') || 'Create Lab Method'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Input
              placeholder={t('pages.quality.placeholder.methodName') || 'Method name'}
              value={methodForm.name}
              onChange={(e) => setMethodForm((prev) => ({ ...prev, name: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.standard') || 'Standard (ASTM/ISO)'}
              value={methodForm.standard}
              onChange={(e) => setMethodForm((prev) => ({ ...prev, standard: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.unit') || 'Unit'}
              value={methodForm.unit}
              onChange={(e) => setMethodForm((prev) => ({ ...prev, unit: e.target.value }))}
            />
            <Input
              type="number"
              placeholder={t('pages.quality.placeholder.lowerSpec') || 'Lower spec'}
              value={methodForm.lowerSpec}
              onChange={(e) => setMethodForm((prev) => ({ ...prev, lowerSpec: e.target.value }))}
            />
            <Input
              type="number"
              placeholder={t('pages.quality.placeholder.upperSpec') || 'Upper spec'}
              value={methodForm.upperSpec}
              onChange={(e) => setMethodForm((prev) => ({ ...prev, upperSpec: e.target.value }))}
            />
            <Input
              type="number"
              placeholder={t('pages.quality.placeholder.targetValue') || 'Target value'}
              value={methodForm.targetValue}
              onChange={(e) => setMethodForm((prev) => ({ ...prev, targetValue: e.target.value }))}
            />
          </div>
          <div className="flex justify-end">
            <Button onClick={handleCreateMethod} disabled={loading}>{t('pages.quality.createMethod') || 'Create Method'}</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.registerLabSample') || 'Register Lab Sample'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Input
              placeholder={t('pages.quality.placeholder.sampleNumber') || 'Sample number'}
              value={sampleForm.sampleNumber}
              onChange={(e) => setSampleForm((prev) => ({ ...prev, sampleNumber: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.productId') || 'Product ID'}
              value={sampleForm.productId}
              onChange={(e) => setSampleForm((prev) => ({ ...prev, productId: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.workOrderId') || 'Work Order ID'}
              value={sampleForm.workOrderId}
              onChange={(e) => setSampleForm((prev) => ({ ...prev, workOrderId: e.target.value }))}
            />
            <Input
              placeholder={t('pages.quality.placeholder.lotNumber') || 'Lot number'}
              value={sampleForm.lotNumber}
              onChange={(e) => setSampleForm((prev) => ({ ...prev, lotNumber: e.target.value }))}
            />
          </div>
          <div className="flex justify-end">
            <Button variant="outline" onClick={handleCreateSample} disabled={loading}>{t('pages.quality.createSample') || 'Create Sample'}</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.recordTestRun') || 'Record Test Run'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Select
              value={testForm.sampleId}
              onValueChange={(value) => setTestForm((prev) => ({ ...prev, sampleId: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('pages.quality.placeholder.selectSample') || 'Select sample'} />
              </SelectTrigger>
              <SelectContent>
                {labSamples.map((sample) => (
                  <SelectItem key={sample.id} value={sample.id}>
                    {sample.sample_number}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={testForm.methodId}
              onValueChange={(value) => setTestForm((prev) => ({ ...prev, methodId: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('pages.quality.placeholder.selectMethod') || 'Select method'} />
              </SelectTrigger>
              <SelectContent>
                {labMethods.map((method) => (
                  <SelectItem key={method.id} value={method.id}>
                    {method.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              type="number"
              placeholder={t('pages.quality.placeholder.resultValue') || 'Result value'}
              value={testForm.resultValue}
              onChange={(e) => setTestForm((prev) => ({ ...prev, resultValue: e.target.value }))}
            />
            <Select
              value={testForm.resultStatus}
              onValueChange={(value) => setTestForm((prev) => ({ ...prev, resultStatus: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('common.status') || 'Status'} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pending">{t('common.pending') || 'Pending'}</SelectItem>
                <SelectItem value="pass">{t('pages.quality.status.pass') || 'Pass'}</SelectItem>
                <SelectItem value="fail">{t('pages.quality.status.fail') || 'Fail'}</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder={t('pages.quality.placeholder.notes') || 'Notes'}
              value={testForm.notes}
              onChange={(e) => setTestForm((prev) => ({ ...prev, notes: e.target.value }))}
            />
          </div>
          <div className="flex justify-end">
            <Button variant="outline" onClick={handleAddTestRun} disabled={loading}>{t('pages.quality.addTest') || 'Add Test'}</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.method') || 'Method'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.standard') || 'Standard'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.unit') || 'Unit'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.specs') || 'Specs'}</th>
                </tr>
              </thead>
              <tbody>
                {labMethods.map((method) => (
                  <tr key={method.id} className="border-b hover:bg-muted/50">
                    <td className="py-3 px-4 font-medium">{method.name}</td>
                    <td className="py-3 px-4 text-muted-foreground">{method.standard || '—'}</td>
                    <td className="py-3 px-4 text-muted-foreground">{method.unit || '—'}</td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {method.lower_spec ?? '—'} - {method.upper_spec ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AQLSamplingTab() {
  const { t } = useI18n();
  const {
    aqlPlans,
    aqlInspections,
    fetchAqlPlans,
    fetchAqlInspections,
    createAqlPlan,
    createAqlInspection,
    loading,
  } = useQualityStore();

  const [planForm, setPlanForm] = React.useState({
    planCode: '',
    standard: 'ANSI/ASQ Z1.4',
    inspectionLevel: 'II',
    aqlLevel: '1.0',
    lotSizeMin: '',
    lotSizeMax: '',
    sampleSize: '',
    acceptLimit: '',
    rejectLimit: '',
    notes: '',
  });

  const [inspectionForm, setInspectionForm] = React.useState({
    planId: '',
    lotNumber: '',
    lotSize: '',
    sampleSize: '',
    defectCount: '',
    notes: '',
  });

  React.useEffect(() => {
    fetchAqlPlans();
  }, [fetchAqlPlans]);

  React.useEffect(() => {
    if (!inspectionForm.planId && aqlPlans.length > 0) {
      setInspectionForm((prev) => ({ ...prev, planId: aqlPlans[0].id }));
    }
  }, [aqlPlans, inspectionForm.planId]);

  React.useEffect(() => {
    fetchAqlInspections(inspectionForm.planId || undefined);
  }, [fetchAqlInspections, inspectionForm.planId]);

  const planLookup = React.useMemo(() => {
    return new Map(aqlPlans.map((plan) => [plan.id, plan.plan_code]));
  }, [aqlPlans]);

  const handleCreatePlan = async () => {
    if (
      !planForm.planCode ||
      planForm.lotSizeMin === '' ||
      planForm.lotSizeMax === '' ||
      planForm.sampleSize === '' ||
      planForm.acceptLimit === '' ||
      planForm.rejectLimit === ''
    ) {
      return;
    }

    await createAqlPlan({
      plan_code: planForm.planCode,
      standard: planForm.standard,
      inspection_level: planForm.inspectionLevel,
      aql_level: planForm.aqlLevel,
      lot_size_min: Number(planForm.lotSizeMin),
      lot_size_max: Number(planForm.lotSizeMax),
      sample_size: Number(planForm.sampleSize),
      accept_limit: Number(planForm.acceptLimit),
      reject_limit: Number(planForm.rejectLimit),
      notes: planForm.notes || undefined,
    });

    setPlanForm({
      planCode: '',
      standard: 'ANSI/ASQ Z1.4',
      inspectionLevel: 'II',
      aqlLevel: '1.0',
      lotSizeMin: '',
      lotSizeMax: '',
      sampleSize: '',
      acceptLimit: '',
      rejectLimit: '',
      notes: '',
    });
  };

  const handleCreateInspection = async () => {
    if (!inspectionForm.planId || !inspectionForm.lotNumber || inspectionForm.lotSize === '' || inspectionForm.defectCount === '') {
      return;
    }

    await createAqlInspection({
      plan_id: inspectionForm.planId,
      lot_number: inspectionForm.lotNumber,
      lot_size: Number(inspectionForm.lotSize),
      sample_size: inspectionForm.sampleSize === '' ? undefined : Number(inspectionForm.sampleSize),
      defect_count: Number(inspectionForm.defectCount),
      notes: inspectionForm.notes || undefined,
    });

    setInspectionForm((prev) => ({
      ...prev,
      lotNumber: '',
      lotSize: '',
      sampleSize: '',
      defectCount: '',
      notes: '',
    }));
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/40 bg-card/40">
          <CardHeader>
            <CardTitle className="text-base">{t('pages.quality.createAqlPlan') || 'Create AQL Sampling Plan'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.planCode') || 'Plan Code'}</label>
                <Input
                  value={planForm.planCode}
                  onChange={(e) => setPlanForm((prev) => ({ ...prev, planCode: e.target.value }))}
                  placeholder={t('pages.quality.aql.planCodePlaceholder') || 'e.g., AQL-II-1.0-80-125'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.standard') || 'Standard'}</label>
                <Input
                  value={planForm.standard}
                  onChange={(e) => setPlanForm((prev) => ({ ...prev, standard: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.inspectionLevel') || 'Inspection Level'}</label>
                <Input
                  value={planForm.inspectionLevel}
                  onChange={(e) => setPlanForm((prev) => ({ ...prev, inspectionLevel: e.target.value }))}
                  placeholder="II"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.aqlLevel') || 'AQL Level'}</label>
                <Input
                  value={planForm.aqlLevel}
                  onChange={(e) => setPlanForm((prev) => ({ ...prev, aqlLevel: e.target.value }))}
                  placeholder="1.0"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.lotSizeMin') || 'Lot Size Min'}</label>
                <Input
                  type="number"
                  value={planForm.lotSizeMin}
                  onChange={(e) => setPlanForm((prev) => ({ ...prev, lotSizeMin: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.lotSizeMax') || 'Lot Size Max'}</label>
                <Input
                  type="number"
                  value={planForm.lotSizeMax}
                  onChange={(e) => setPlanForm((prev) => ({ ...prev, lotSizeMax: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.sampleSize') || 'Sample Size'}</label>
                <Input
                  type="number"
                  value={planForm.sampleSize}
                  onChange={(e) => setPlanForm((prev) => ({ ...prev, sampleSize: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.acceptReject') || 'Accept / Reject'}</label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    value={planForm.acceptLimit}
                    onChange={(e) => setPlanForm((prev) => ({ ...prev, acceptLimit: e.target.value }))}
                    placeholder={t('pages.quality.aql.accept') || 'Accept'}
                  />
                  <Input
                    type="number"
                    value={planForm.rejectLimit}
                    onChange={(e) => setPlanForm((prev) => ({ ...prev, rejectLimit: e.target.value }))}
                    placeholder={t('pages.quality.aql.reject') || 'Reject'}
                  />
                </div>
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.notes') || 'Notes'}</label>
              <Input
                value={planForm.notes}
                onChange={(e) => setPlanForm((prev) => ({ ...prev, notes: e.target.value }))}
                placeholder={t('pages.quality.placeholder.optionalNotes') || 'Optional notes'}
              />
            </div>
            <Button onClick={handleCreatePlan} disabled={loading} className="w-full">
              {t('pages.quality.aql.createPlan') || 'Create Plan'}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-border/40 bg-card/40">
          <CardHeader>
            <CardTitle className="text-base">{t('pages.quality.aql.recordLotInspection') || 'Record Lot Inspection'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.plan') || 'Plan'}</label>
                <Select
                  value={inspectionForm.planId}
                  onValueChange={(value) => setInspectionForm((prev) => ({ ...prev, planId: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t('pages.quality.aql.selectPlan') || 'Select plan'} />
                  </SelectTrigger>
                  <SelectContent>
                    {aqlPlans.map((plan) => (
                      <SelectItem key={plan.id} value={plan.id}>{plan.plan_code}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.lotNumber') || 'Lot Number'}</label>
                <Input
                  value={inspectionForm.lotNumber}
                  onChange={(e) => setInspectionForm((prev) => ({ ...prev, lotNumber: e.target.value }))}
                  placeholder={t('pages.quality.aql.lotNumberPlaceholder') || 'LOT-2026-001'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.lotSize') || 'Lot Size'}</label>
                <Input
                  type="number"
                  value={inspectionForm.lotSize}
                  onChange={(e) => setInspectionForm((prev) => ({ ...prev, lotSize: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.sampleSizeOptional') || 'Sample Size (optional)'}</label>
                <Input
                  type="number"
                  value={inspectionForm.sampleSize}
                  onChange={(e) => setInspectionForm((prev) => ({ ...prev, sampleSize: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.defectCount') || 'Defect Count'}</label>
                <Input
                  type="number"
                  value={inspectionForm.defectCount}
                  onChange={(e) => setInspectionForm((prev) => ({ ...prev, defectCount: e.target.value }))}
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.aql.notes') || 'Notes'}</label>
              <Input
                value={inspectionForm.notes}
                onChange={(e) => setInspectionForm((prev) => ({ ...prev, notes: e.target.value }))}
                placeholder={t('pages.quality.placeholder.optionalNotes') || 'Optional notes'}
              />
            </div>
            <Button onClick={handleCreateInspection} disabled={loading || aqlPlans.length === 0} className="w-full">
              {t('pages.quality.aql.recordInspection') || 'Record Inspection'}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.aql.samplingPlans') || 'Sampling Plans'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.plan') || 'Plan'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.aqlLabel') || 'AQL'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.lotRange') || 'Lot Range'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.sample') || 'Sample'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.acceptReject') || 'Accept/Reject'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                </tr>
              </thead>
              <tbody>
                {aqlPlans.length === 0 ? (
                  <tr><td colSpan={6} className="py-8 text-center text-muted-foreground">{t('pages.quality.aql.noPlans') || 'No AQL plans yet.'}</td></tr>
                ) : (
                  aqlPlans.map((plan) => (
                    <tr key={plan.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{plan.plan_code}</td>
                      <td className="py-3 px-4 text-muted-foreground">{plan.aql_level} / {plan.inspection_level}</td>
                      <td className="py-3 px-4 text-muted-foreground">{plan.lot_size_min} - {plan.lot_size_max}</td>
                      <td className="py-3 px-4 text-muted-foreground">{plan.sample_size}</td>
                      <td className="py-3 px-4 text-muted-foreground">{plan.accept_limit} / {plan.reject_limit}</td>
                      <td className="py-3 px-4">
                        <Badge variant={plan.status === 'active' ? 'success' : 'secondary'}>{plan.status}</Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.aql.lotInspections') || 'Lot Inspections'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.lot') || 'Lot'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.plan') || 'Plan'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.sample') || 'Sample'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.defects') || 'Defects'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.result') || 'Result'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.aql.inspected') || 'Inspected'}</th>
                </tr>
              </thead>
              <tbody>
                {aqlInspections.length === 0 ? (
                  <tr><td colSpan={6} className="py-8 text-center text-muted-foreground">{t('pages.quality.aql.noInspections') || 'No inspections recorded.'}</td></tr>
                ) : (
                  aqlInspections.map((inspection) => (
                    <tr key={inspection.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{inspection.lot_number}</td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {planLookup.get(inspection.plan_id) || inspection.plan_id.slice(0, 8)}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{inspection.sample_size}</td>
                      <td className="py-3 px-4 text-muted-foreground">{inspection.defect_count}</td>
                      <td className="py-3 px-4">
                        <Badge variant={inspection.result === 'accept' ? 'success' : inspection.result === 'reject' ? 'danger' : 'secondary'}>
                          {inspection.result}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {new Date(inspection.inspected_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function TraceabilityTab() {
  const { t } = useI18n();
  const {
    traceabilityMatrices,
    traceabilityLinks,
    fetchTraceabilityMatrices,
    fetchTraceabilityLinks,
    createTraceabilityMatrix,
    createTraceabilityLink,
    loading,
  } = useQualityStore();

  const [matrixForm, setMatrixForm] = React.useState({
    name: '',
    description: '',
    status: 'active',
    productId: '',
    workOrderId: '',
    lotNumber: '',
    batchId: '',
    externalReference: '',
  });

  const [linkForm, setLinkForm] = React.useState({
    matrixId: '',
    linkType: '',
    referenceId: '',
    referenceTable: '',
    notes: '',
  });

  React.useEffect(() => {
    fetchTraceabilityMatrices();
  }, [fetchTraceabilityMatrices]);

  React.useEffect(() => {
    if (!linkForm.matrixId && traceabilityMatrices.length > 0) {
      setLinkForm((prev) => ({ ...prev, matrixId: traceabilityMatrices[0].id }));
    }
  }, [traceabilityMatrices, linkForm.matrixId]);

  React.useEffect(() => {
    fetchTraceabilityLinks(linkForm.matrixId || undefined);
  }, [fetchTraceabilityLinks, linkForm.matrixId]);

  const handleCreateMatrix = async () => {
    if (!matrixForm.name) {
      return;
    }
    await createTraceabilityMatrix({
      name: matrixForm.name,
      description: matrixForm.description || undefined,
      status: matrixForm.status,
      product_id: matrixForm.productId ? String(matrixForm.productId) : undefined,
      work_order_id: matrixForm.workOrderId ? Number(matrixForm.workOrderId) : undefined,
      lot_number: matrixForm.lotNumber || undefined,
      batch_id: matrixForm.batchId || undefined,
      external_reference: matrixForm.externalReference || undefined,
    });
    setMatrixForm({
      name: '',
      description: '',
      status: 'active',
      productId: '',
      workOrderId: '',
      lotNumber: '',
      batchId: '',
      externalReference: '',
    });
  };

  const handleCreateLink = async () => {
    if (!linkForm.matrixId || !linkForm.linkType || !linkForm.referenceId) {
      return;
    }
    await createTraceabilityLink({
      matrix_id: linkForm.matrixId,
      link_type: linkForm.linkType,
      reference_id: linkForm.referenceId,
      reference_table: linkForm.referenceTable || undefined,
      notes: linkForm.notes || undefined,
    });
    setLinkForm((prev) => ({
      ...prev,
      linkType: '',
      referenceId: '',
      referenceTable: '',
      notes: '',
    }));
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/40 bg-card/40">
          <CardHeader>
            <CardTitle className="text-base">{t('pages.quality.traceability.createMatrix') || 'Create Traceability Matrix'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.name') || 'Name'}</label>
                <Input
                  value={matrixForm.name}
                  onChange={(e) => setMatrixForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder={t('pages.quality.traceability.namePlaceholder') || 'e.g., WO-1001 Trace'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.productId') || 'Product ID'}</label>
                <Input
                  value={matrixForm.productId}
                  onChange={(e) => setMatrixForm((prev) => ({ ...prev, productId: e.target.value }))}
                  placeholder={t('pages.quality.placeholder.productId') || 'Product ID'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.workOrderId') || 'Work Order ID'}</label>
                <Input
                  value={matrixForm.workOrderId}
                  onChange={(e) => setMatrixForm((prev) => ({ ...prev, workOrderId: e.target.value }))}
                  placeholder={t('pages.quality.placeholder.workOrderId') || 'Work Order ID'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.lotNumber') || 'Lot Number'}</label>
                <Input
                  value={matrixForm.lotNumber}
                  onChange={(e) => setMatrixForm((prev) => ({ ...prev, lotNumber: e.target.value }))}
                  placeholder={t('pages.quality.traceability.lotPlaceholder') || 'LOT-2026-0001'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.batchId') || 'Batch ID'}</label>
                <Input
                  value={matrixForm.batchId}
                  onChange={(e) => setMatrixForm((prev) => ({ ...prev, batchId: e.target.value }))}
                  placeholder={t('pages.quality.traceability.batchPlaceholder') || 'BATCH-01'}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.externalReference') || 'External Reference'}</label>
                <Input
                  value={matrixForm.externalReference}
                  onChange={(e) => setMatrixForm((prev) => ({ ...prev, externalReference: e.target.value }))}
                  placeholder={t('pages.quality.traceability.externalRefPlaceholder') || 'Customer PO / Shipment ID'}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('common.description') || 'Description'}</label>
                <Input
                  value={matrixForm.description}
                  onChange={(e) => setMatrixForm((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder={t('pages.quality.traceability.descriptionPlaceholder') || 'Optional description'}
                />
              </div>
            </div>
            <Button onClick={handleCreateMatrix} disabled={loading} className="w-full">
              {t('pages.quality.traceability.createMatrixButton') || 'Create Matrix'}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-border/40 bg-card/40">
          <CardHeader>
            <CardTitle className="text-base">{t('pages.quality.traceability.addLink') || 'Add Traceability Link'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.matrix') || 'Matrix'}</label>
                <Select
                  value={linkForm.matrixId}
                  onValueChange={(value) => setLinkForm((prev) => ({ ...prev, matrixId: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t('pages.quality.traceability.selectMatrix') || 'Select matrix'} />
                  </SelectTrigger>
                  <SelectContent>
                    {traceabilityMatrices.map((matrix) => (
                      <SelectItem key={matrix.id} value={matrix.id}>{matrix.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.linkType') || 'Link Type'}</label>
                <Input
                  value={linkForm.linkType}
                  onChange={(e) => setLinkForm((prev) => ({ ...prev, linkType: e.target.value }))}
                  placeholder={t('pages.quality.traceability.linkTypePlaceholder') || 'inspection / ncr / capa'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.referenceId') || 'Reference ID'}</label>
                <Input
                  value={linkForm.referenceId}
                  onChange={(e) => setLinkForm((prev) => ({ ...prev, referenceId: e.target.value }))}
                  placeholder={t('pages.quality.traceability.referenceIdPlaceholder') || 'Record ID'}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.referenceTable') || 'Reference Table'}</label>
                <Input
                  value={linkForm.referenceTable}
                  onChange={(e) => setLinkForm((prev) => ({ ...prev, referenceTable: e.target.value }))}
                  placeholder={t('pages.quality.traceability.referenceTablePlaceholder') || 'quality_inspections'}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.traceability.notes') || 'Notes'}</label>
                <Input
                  value={linkForm.notes}
                  onChange={(e) => setLinkForm((prev) => ({ ...prev, notes: e.target.value }))}
                  placeholder={t('pages.quality.placeholder.optionalNotes') || 'Optional notes'}
                />
              </div>
            </div>
            <Button onClick={handleCreateLink} disabled={loading || traceabilityMatrices.length === 0} className="w-full">
              {t('pages.quality.traceability.addLinkButton') || 'Add Link'}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.traceability.matrices') || 'Traceability Matrices'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.traceability.name') || 'Name'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.traceability.lot') || 'Lot'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.product') || 'Product'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.table.workOrder') || 'Work Order'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                </tr>
              </thead>
              <tbody>
                {traceabilityMatrices.length === 0 ? (
                  <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">{t('pages.quality.traceability.noMatrices') || 'No traceability matrices yet.'}</td></tr>
                ) : (
                  traceabilityMatrices.map((matrix) => (
                    <tr key={matrix.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{matrix.name}</td>
                      <td className="py-3 px-4 text-muted-foreground">{matrix.lot_number || '—'}</td>
                      <td className="py-3 px-4 text-muted-foreground">{matrix.product_id ?? '—'}</td>
                      <td className="py-3 px-4 text-muted-foreground">{matrix.work_order_id ?? '—'}</td>
                      <td className="py-3 px-4">
                        <Badge variant={matrix.status === 'active' ? 'success' : 'secondary'}>{matrix.status}</Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.traceability.links') || 'Traceability Links'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('common.type') || 'Type'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.traceability.reference') || 'Reference'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.traceability.table') || 'Table'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.traceability.notes') || 'Notes'}</th>
                </tr>
              </thead>
              <tbody>
                {traceabilityLinks.length === 0 ? (
                  <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.quality.traceability.noLinks') || 'No links for selected matrix.'}</td></tr>
                ) : (
                  traceabilityLinks.map((link) => (
                    <tr key={link.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{link.link_type}</td>
                      <td className="py-3 px-4 text-muted-foreground">{link.reference_id}</td>
                      <td className="py-3 px-4 text-muted-foreground">{link.reference_table || '—'}</td>
                      <td className="py-3 px-4 text-muted-foreground">{link.notes || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ChangePointTab() {
  const { t } = useI18n();
  const {
    changePointStudies,
    changePointObservations,
    changePointEvents,
    fetchChangePointStudies,
    fetchChangePointObservations,
    fetchChangePointEvents,
    createChangePointStudy,
    addChangePointObservation,
    detectChangePoint,
    loading,
  } = useQualityStore();

  const [studyForm, setStudyForm] = React.useState({
    name: '',
    processName: '',
    characteristic: '',
    method: 'mean_shift',
    sensitivity: '',
    notes: '',
  });

  const [observationForm, setObservationForm] = React.useState({
    studyId: '',
    value: '',
    sampleLabel: '',
  });

  React.useEffect(() => {
    fetchChangePointStudies();
  }, [fetchChangePointStudies]);

  React.useEffect(() => {
    if (!observationForm.studyId && changePointStudies.length > 0) {
      setObservationForm((prev) => ({ ...prev, studyId: changePointStudies[0].id }));
    }
  }, [changePointStudies, observationForm.studyId]);

  React.useEffect(() => {
    if (observationForm.studyId) {
      fetchChangePointObservations(observationForm.studyId);
      fetchChangePointEvents(observationForm.studyId);
    }
  }, [fetchChangePointObservations, fetchChangePointEvents, observationForm.studyId]);

  const handleCreateStudy = async () => {
    if (!studyForm.name || !studyForm.processName || !studyForm.characteristic) {
      return;
    }
    await createChangePointStudy({
      name: studyForm.name,
      process_name: studyForm.processName,
      characteristic: studyForm.characteristic,
      method: studyForm.method || 'mean_shift',
      sensitivity: studyForm.sensitivity === '' ? undefined : Number(studyForm.sensitivity),
      notes: studyForm.notes || undefined,
    });
    setStudyForm({
      name: '',
      processName: '',
      characteristic: '',
      method: 'mean_shift',
      sensitivity: '',
      notes: '',
    });
  };

  const handleAddObservation = async () => {
    if (!observationForm.studyId || observationForm.value === '') {
      return;
    }
    await addChangePointObservation(observationForm.studyId, {
      value: Number(observationForm.value),
      sample_label: observationForm.sampleLabel || undefined,
    });
    setObservationForm((prev) => ({
      ...prev,
      value: '',
      sampleLabel: '',
    }));
  };

  const handleDetect = async () => {
    if (!observationForm.studyId) {
      return;
    }
    await detectChangePoint(observationForm.studyId);
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/40 bg-card/40">
          <CardHeader>
            <CardTitle className="text-base">{t('pages.quality.changePoint.createStudy') || 'Create Change Point Study'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.changePoint.studyName') || 'Study Name'}</label>
                <Input
                  value={studyForm.name}
                  onChange={(e) => setStudyForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder={t('pages.quality.changePoint.studyNamePlaceholder') || 'e.g., Drill Press Drift'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.changePoint.processName') || 'Process Name'}</label>
                <Input
                  value={studyForm.processName}
                  onChange={(e) => setStudyForm((prev) => ({ ...prev, processName: e.target.value }))}
                  placeholder={t('pages.quality.changePoint.processPlaceholder') || 'Drill Press'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.changePoint.characteristic') || 'Characteristic'}</label>
                <Input
                  value={studyForm.characteristic}
                  onChange={(e) => setStudyForm((prev) => ({ ...prev, characteristic: e.target.value }))}
                  placeholder={t('pages.quality.changePoint.characteristicPlaceholder') || 'Hole Diameter'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.changePoint.method') || 'Method'}</label>
                <Input
                  value={studyForm.method}
                  onChange={(e) => setStudyForm((prev) => ({ ...prev, method: e.target.value }))}
                  placeholder={t('pages.quality.changePoint.methodPlaceholder') || 'mean_shift'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.changePoint.sensitivity') || 'Sensitivity'}</label>
                <Input
                  type="number"
                  value={studyForm.sensitivity}
                  onChange={(e) => setStudyForm((prev) => ({ ...prev, sensitivity: e.target.value }))}
                  placeholder="0.5"
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.changePoint.notes') || 'Notes'}</label>
                <Input
                  value={studyForm.notes}
                  onChange={(e) => setStudyForm((prev) => ({ ...prev, notes: e.target.value }))}
                  placeholder={t('pages.quality.placeholder.optionalNotes') || 'Optional notes'}
                />
              </div>
            </div>
            <Button onClick={handleCreateStudy} disabled={loading} className="w-full">
              {t('pages.quality.changePoint.createStudyButton') || 'Create Study'}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-border/40 bg-card/40">
          <CardHeader>
            <CardTitle className="text-base">{t('pages.quality.changePoint.addObservation') || 'Add Observation'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.changePoint.study') || 'Study'}</label>
                <Select
                  value={observationForm.studyId}
                  onValueChange={(value) => setObservationForm((prev) => ({ ...prev, studyId: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t('pages.quality.placeholder.selectStudy') || 'Select study'} />
                  </SelectTrigger>
                  <SelectContent>
                    {changePointStudies.map((study) => (
                      <SelectItem key={study.id} value={study.id}>{study.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.changePoint.value') || 'Value'}</label>
                <Input
                  type="number"
                  value={observationForm.value}
                  onChange={(e) => setObservationForm((prev) => ({ ...prev, value: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.changePoint.sampleLabel') || 'Sample Label'}</label>
                <Input
                  value={observationForm.sampleLabel}
                  onChange={(e) => setObservationForm((prev) => ({ ...prev, sampleLabel: e.target.value }))}
                  placeholder={t('pages.quality.changePoint.sampleIdPlaceholder') || 'Sample ID'}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleAddObservation} disabled={loading || changePointStudies.length === 0} className="flex-1">
                {t('pages.quality.changePoint.addObservationButton') || 'Add Observation'}
              </Button>
              <Button onClick={handleDetect} disabled={loading || !observationForm.studyId} variant="outline" className="flex-1">
                {t('pages.quality.changePoint.detectChangePoint') || 'Detect Change Point'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.changePoint.studies') || 'Studies'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.study') || 'Study'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.process') || 'Process'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.characteristic') || 'Characteristic'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.method') || 'Method'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                </tr>
              </thead>
              <tbody>
                {changePointStudies.length === 0 ? (
                  <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">{t('pages.quality.changePoint.noStudies') || 'No studies yet.'}</td></tr>
                ) : (
                  changePointStudies.map((study) => (
                    <tr key={study.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{study.name}</td>
                      <td className="py-3 px-4 text-muted-foreground">{study.process_name}</td>
                      <td className="py-3 px-4 text-muted-foreground">{study.characteristic}</td>
                      <td className="py-3 px-4 text-muted-foreground">{study.method}</td>
                      <td className="py-3 px-4">
                        <Badge variant={study.status === 'active' ? 'success' : 'secondary'}>{study.status}</Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/40 bg-card/40">
          <CardHeader>
            <CardTitle className="text-base">{t('pages.quality.changePoint.observations') || 'Observations'}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.value') || 'Value'}</th>
                    <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.sample') || 'Sample'}</th>
                    <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.observed') || 'Observed'}</th>
                  </tr>
                </thead>
                <tbody>
                  {changePointObservations.length === 0 ? (
                    <tr><td colSpan={3} className="py-8 text-center text-muted-foreground">{t('pages.quality.changePoint.noObservations') || 'No observations.'}</td></tr>
                  ) : (
                    changePointObservations.map((obs) => (
                      <tr key={obs.id} className="border-b hover:bg-muted/50">
                        <td className="py-3 px-4 font-medium">{obs.value}</td>
                        <td className="py-3 px-4 text-muted-foreground">{obs.sample_label || '—'}</td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {new Date(obs.observed_at).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/40 bg-card/40">
          <CardHeader>
            <CardTitle className="text-base">{t('pages.quality.changePoint.detectedEvents') || 'Detected Events'}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.index') || 'Index'}</th>
                    <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.magnitude') || 'Magnitude'}</th>
                    <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.confidence') || 'Confidence'}</th>
                    <th className="py-3 px-4 text-left font-medium">{t('pages.quality.changePoint.detected') || 'Detected'}</th>
                  </tr>
                </thead>
                <tbody>
                  {changePointEvents.length === 0 ? (
                    <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.quality.changePoint.noEvents') || 'No events detected.'}</td></tr>
                  ) : (
                    changePointEvents.map((event) => (
                      <tr key={event.id} className="border-b hover:bg-muted/50">
                        <td className="py-3 px-4 font-medium">{event.index_position}</td>
                        <td className="py-3 px-4 text-muted-foreground">{event.change_magnitude}</td>
                        <td className="py-3 px-4 text-muted-foreground">{event.confidence ?? '—'}</td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {new Date(event.detected_at).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ManagementReviewTab() {
  const { t } = useI18n();
  const {
    managementReviews,
    managementReviewActions,
    fetchManagementReviews,
    fetchManagementReviewActions,
    createManagementReview,
    addManagementReviewAction,
    closeManagementReview,
    loading,
  } = useQualityStore();

  const [reviewForm, setReviewForm] = React.useState({
    title: '',
    periodStart: '',
    periodEnd: '',
    scheduledFor: '',
    attendees: '',
    notes: '',
  });

  const [actionForm, setActionForm] = React.useState({
    reviewId: '',
    title: '',
    dueDate: '',
    assigneeId: '',
    notes: '',
  });

  React.useEffect(() => {
    fetchManagementReviews();
    fetchManagementReviewActions();
  }, [fetchManagementReviewActions, fetchManagementReviews]);

  React.useEffect(() => {
    if (!actionForm.reviewId && managementReviews.length > 0) {
      setActionForm((prev) => ({ ...prev, reviewId: managementReviews[0].id }));
    }
  }, [managementReviews, actionForm.reviewId]);

  const handleCreateReview = async () => {
    if (!reviewForm.title || !reviewForm.periodStart || !reviewForm.periodEnd || !reviewForm.scheduledFor) {
      return;
    }
    const attendees = reviewForm.attendees
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean);
    await createManagementReview({
      title: reviewForm.title,
      period_start: reviewForm.periodStart,
      period_end: reviewForm.periodEnd,
      scheduled_for: reviewForm.scheduledFor,
      attendees: attendees.length ? attendees : undefined,
      notes: reviewForm.notes || undefined,
    });
    setReviewForm({
      title: '',
      periodStart: '',
      periodEnd: '',
      scheduledFor: '',
      attendees: '',
      notes: '',
    });
  };

  const handleAddAction = async () => {
    if (!actionForm.reviewId || !actionForm.title) {
      return;
    }
    await addManagementReviewAction(actionForm.reviewId, {
      title: actionForm.title,
      due_date: actionForm.dueDate || undefined,
      assignee_id: actionForm.assigneeId || undefined,
      notes: actionForm.notes || undefined,
    });
    setActionForm((prev) => ({
      ...prev,
      title: '',
      dueDate: '',
      assigneeId: '',
      notes: '',
    }));
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/40 bg-card/40">
          <CardHeader>
            <CardTitle className="text-base">{t('pages.quality.managementReview.scheduleReview') || 'Schedule Management Review'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.managementReview.title') || 'Title'}</label>
                <Input
                  value={reviewForm.title}
                  onChange={(e) => setReviewForm((prev) => ({ ...prev, title: e.target.value }))}
                  placeholder={t('pages.quality.managementReview.titlePlaceholder') || 'Q2 Management Review'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.managementReview.periodStart') || 'Period Start'}</label>
                <Input
                  type="date"
                  value={reviewForm.periodStart}
                  onChange={(e) => setReviewForm((prev) => ({ ...prev, periodStart: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.managementReview.periodEnd') || 'Period End'}</label>
                <Input
                  type="date"
                  value={reviewForm.periodEnd}
                  onChange={(e) => setReviewForm((prev) => ({ ...prev, periodEnd: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.managementReview.scheduledFor') || 'Scheduled For'}</label>
                <Input
                  type="date"
                  value={reviewForm.scheduledFor}
                  onChange={(e) => setReviewForm((prev) => ({ ...prev, scheduledFor: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.managementReview.attendees') || 'Attendees'}</label>
                <Input
                  value={reviewForm.attendees}
                  onChange={(e) => setReviewForm((prev) => ({ ...prev, attendees: e.target.value }))}
                  placeholder={t('pages.quality.managementReview.attendeesPlaceholder') || 'CEO, Quality Lead'}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('common.notes') || 'Notes'}</label>
                <Input
                  value={reviewForm.notes}
                  onChange={(e) => setReviewForm((prev) => ({ ...prev, notes: e.target.value }))}
                  placeholder={t('pages.quality.placeholder.optionalNotes') || 'Optional notes'}
                />
              </div>
            </div>
            <Button onClick={handleCreateReview} disabled={loading} className="w-full">
              {t('pages.quality.managementReview.scheduleReviewButton') || 'Schedule Review'}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-border/40 bg-card/40">
          <CardHeader>
            <CardTitle className="text-base">{t('pages.quality.managementReview.addActionItem') || 'Add Action Item'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.managementReview.review') || 'Review'}</label>
                <Select
                  value={actionForm.reviewId}
                  onValueChange={(value) => setActionForm((prev) => ({ ...prev, reviewId: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t('pages.quality.managementReview.selectReview') || 'Select review'} />
                  </SelectTrigger>
                  <SelectContent>
                    {managementReviews.map((review) => (
                      <SelectItem key={review.id} value={review.id}>{review.title}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.managementReview.title') || 'Title'}</label>
                <Input
                  value={actionForm.title}
                  onChange={(e) => setActionForm((prev) => ({ ...prev, title: e.target.value }))}
                  placeholder={t('pages.quality.managementReview.actionTitlePlaceholder') || 'Improve supplier audits'}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.managementReview.dueDate') || 'Due Date'}</label>
                <Input
                  type="date"
                  value={actionForm.dueDate}
                  onChange={(e) => setActionForm((prev) => ({ ...prev, dueDate: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.quality.managementReview.assigneeId') || 'Assignee ID'}</label>
                <Input
                  value={actionForm.assigneeId}
                  onChange={(e) => setActionForm((prev) => ({ ...prev, assigneeId: e.target.value }))}
                  placeholder={t('pages.quality.managementReview.userIdPlaceholder') || 'User ID'}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">{t('common.notes') || 'Notes'}</label>
                <Input
                  value={actionForm.notes}
                  onChange={(e) => setActionForm((prev) => ({ ...prev, notes: e.target.value }))}
                  placeholder={t('pages.quality.placeholder.optionalNotes') || 'Optional notes'}
                />
              </div>
            </div>
            <Button onClick={handleAddAction} disabled={loading || managementReviews.length === 0} className="w-full">
              {t('pages.quality.managementReview.addActionItemButton') || 'Add Action Item'}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.managementReview.managementReviews') || 'Management Reviews'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.managementReview.title') || 'Title'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.managementReview.period') || 'Period'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.managementReview.scheduled') || 'Scheduled'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {managementReviews.length === 0 ? (
                  <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">{t('pages.quality.managementReview.noReviews') || 'No reviews scheduled.'}</td></tr>
                ) : (
                  managementReviews.map((review) => (
                    <tr key={review.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">{review.title}</td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {review.period_start} - {review.period_end}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{review.scheduled_for}</td>
                      <td className="py-3 px-4">
                        <Badge variant={review.status === 'closed' ? 'success' : 'secondary'}>{review.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => closeManagementReview(review.id)}
                          disabled={loading || review.status === 'closed'}
                        >
                          {t('common.close') || 'Close'}
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/40 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base">{t('pages.quality.managementReview.actionItems') || 'Action Items'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.managementReview.review') || 'Review'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.managementReview.title') || 'Title'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.managementReview.due') || 'Due'}</th>
                </tr>
              </thead>
              <tbody>
                {managementReviewActions.length === 0 ? (
                  <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">{t('pages.quality.managementReview.noActions') || 'No action items recorded.'}</td></tr>
                ) : (
                  managementReviewActions.map((action) => (
                    <tr key={action.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 text-muted-foreground">{action.review_id.slice(0, 8)}</td>
                      <td className="py-3 px-4 font-medium">{action.title}</td>
                      <td className="py-3 px-4">
                        <Badge variant={action.status === 'closed' ? 'success' : 'warning'}>{action.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{action.due_date || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function NCRsTab() {
  const { t } = useI18n();
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

  const { page: ncrPage, setPage: setNcrPage, totalPages: ncrTotalPages, paginated: paginatedNCRs, total: ncrTotal } = useQaPagination(filteredNCRs, [searchQuery, statusFilter, severityFilter]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('pages.quality.ncrs.searchPlaceholder') || 'Search NCRs...'}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder={t('common.status') || 'Status'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('pages.quality.ncrs.allStatuses') || 'All statuses'}</SelectItem>
              <SelectItem value="open">{t('pages.quality.ncrs.statusOpen') || 'Open'}</SelectItem>
              <SelectItem value="under_investigation">{t('pages.quality.ncrs.statusInvestigating') || 'Investigating'}</SelectItem>
              <SelectItem value="pending_disposition">{t('pages.quality.ncrs.statusPendingDisposition') || 'Pending Disposition'}</SelectItem>
              <SelectItem value="dispositioned">{t('pages.quality.ncrs.statusDispositioned') || 'Dispositioned'}</SelectItem>
              <SelectItem value="escalated_to_capa">{t('pages.quality.ncrs.statusEscalated') || 'Escalated to CAPA'}</SelectItem>
              <SelectItem value="closed">{t('pages.quality.ncrs.statusClosed') || 'Closed'}</SelectItem>
            </SelectContent>
          </Select>
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="w-[130px]">
              <SelectValue placeholder={t('pages.quality.ncrs.severity') || 'Severity'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('pages.quality.ncrs.allSeverities') || 'All severities'}</SelectItem>
              <SelectItem value="critical">{t('pages.quality.ncrs.severityCritical') || 'Critical'}</SelectItem>
              <SelectItem value="major">{t('pages.quality.ncrs.severityMajor') || 'Major'}</SelectItem>
              <SelectItem value="minor">{t('pages.quality.ncrs.severityMinor') || 'Minor'}</SelectItem>
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
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.ncrs.ncr') || 'NCR'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.ncrs.title') || 'Title'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.ncrs.severity') || 'Severity'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.ncrs.source') || 'Source'}</th>
                  <th className="py-3 px-4 text-right font-medium">{t('pages.quality.ncrs.affectedQty') || 'Affected Qty'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.ncrs.created') || 'Created'}</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {paginatedNCRs.map((ncr) => {
                  const statusCfg = ncrStatusConfig[ncr.status];
                  const severityCfg = severityConfig[ncr.severity];
                  return (
                    <tr 
                      key={ncr.id}
                      className="border-b hover:bg-muted/50 cursor-pointer"
                      role="link"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); router.push(`/quality/ncrs/${ncr.id}`); } }}
                      onClick={() => router.push(`/quality/ncrs/${ncr.id}`)}
                    >
                      <td className="py-3 px-4 font-medium">{ncr.ncr_number}</td>
                      <td className="py-3 px-4 truncate max-w-[200px]">{ncr.description}</td>
                      <td className="py-3 px-4">
                        <Badge variant={severityCfg?.variant || 'secondary'}>{severityCfg?.labelKey ? t(severityCfg.labelKey) : ncr.severity}</Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={statusCfg?.variant || 'secondary'}>{statusCfg?.labelKey ? t(statusCfg.labelKey) : ncr.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{ncr.product?.name || '—'}</td>
                      <td className="py-3 px-4 text-right">{ncr.quantity_affected}</td>
                      <td className="py-3 px-4">{new Date(ncr.created_at).toLocaleDateString()}</td>
                      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm" aria-label="Actions">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Eye className="mr-2 h-4 w-4" />
                              {t('common.view') || 'View'}
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Shield className="mr-2 h-4 w-4" />
                              {t('pages.quality.ncrs.createCAPA') || 'Create CAPA'}
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
      <Pagination currentPage={ncrPage} totalPages={ncrTotalPages} onPageChange={setNcrPage} totalItems={ncrTotal} />
    </div>
  );
}

function CAPAsTab() {
  const { t } = useI18n();
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

  const { page: capaPage, setPage: setCapaPage, totalPages: capaTotalPages, paginated: paginatedCAPAs, total: capaTotal } = useQaPagination(filteredCAPAs, [searchQuery, statusFilter, typeFilter]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('pages.quality.capas.searchPlaceholder') || 'Search CAPAs...'}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder={t('common.status') || 'Status'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('pages.quality.capas.allStatuses') || 'All statuses'}</SelectItem>
              <SelectItem value="open">{t('pages.quality.capas.statusOpen') || 'Open'}</SelectItem>
              <SelectItem value="implementing">{t('pages.quality.capas.statusImplementing') || 'Implementing'}</SelectItem>
              <SelectItem value="verifying">{t('pages.quality.capas.statusVerifying') || 'Verifying'}</SelectItem>
              <SelectItem value="closed">{t('pages.quality.capas.statusClosed') || 'Closed'}</SelectItem>
            </SelectContent>
          </Select>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-[130px]">
              <SelectValue placeholder={t('common.type') || 'Type'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('pages.quality.capas.allTypes') || 'All types'}</SelectItem>
              <SelectItem value="corrective">{t('pages.quality.capas.typeCorrective') || 'Corrective'}</SelectItem>
              <SelectItem value="preventive">{t('pages.quality.capas.typePreventive') || 'Preventive'}</SelectItem>
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
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.capas.capa') || 'CAPA'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.capas.title') || 'Title'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.type') || 'Type'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.capas.priority') || 'Priority'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('common.status') || 'Status'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.capas.sourceNCR') || 'Source NCR'}</th>
                  <th className="py-3 px-4 text-left font-medium">{t('pages.quality.capas.dueDate') || 'Due Date'}</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {paginatedCAPAs.map((capa) => {
                  const statusCfg = capaStatusConfig[capa.status];
                  const isOverdue = new Date(capa.due_date) < new Date() && capa.status !== 'closed';
                  return (
                    <tr 
                      key={capa.id}
                      className="border-b hover:bg-muted/50 cursor-pointer"
                      role="link"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); router.push(`/quality/capas/${capa.id}`); } }}
                      onClick={() => router.push(`/quality/capas/${capa.id}`)}
                    >
                      <td className="py-3 px-4 font-medium">{capa.capa_number}</td>
                      <td className="py-3 px-4">{capa.title}</td>
                      <td className="py-3 px-4 capitalize">{capa.type}</td>
                      <td className="py-3 px-4 capitalize">
                        {capa.status === 'open' ? (t('pages.quality.capas.priorityHigh') || 'High') : (t('pages.quality.capas.priorityMedium') || 'Medium')}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={statusCfg?.variant || 'secondary'}>{statusCfg?.labelKey ? t(statusCfg.labelKey) : capa.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{capa.ncr_id?.substring(0, 8) || '—'}</td>
                      <td className={cn('py-3 px-4', isOverdue && 'text-danger font-medium')}>
                        {new Date(capa.due_date).toLocaleDateString()}
                        {isOverdue && ` (${t('pages.quality.capas.overdue') || 'overdue'})`}
                      </td>
                      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm" aria-label="Actions">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Eye className="mr-2 h-4 w-4" />
                              {t('common.view') || 'View'}
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Edit className="mr-2 h-4 w-4" />
                              {t('common.edit') || 'Edit'}
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
      <Pagination currentPage={capaPage} totalPages={capaTotalPages} onPageChange={setCapaPage} totalItems={capaTotal} />
    </div>
  );
}

function QualityPageContent() {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { error, fetchInspections, fetchNCRs, fetchCAPAs } = useQualityStore();
  const [activeTab, setActiveTab] = React.useState<TabType>(
    (searchParams.get('tab') as TabType) || 'inspections'
  );

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    router.push(`/quality?tab=${tab}`, { scroll: false });
  };

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="quality-page">
      {/* Error state */}
      {error && (
        <div className="rounded-rams-sm border border-destructive/50 bg-destructive/10 p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="text-sm font-bold text-destructive">{t('pages.quality.errorLoading') || 'Error loading quality data'}</p>
              <p className="text-xs text-muted-foreground">{error}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => { fetchInspections(); fetchNCRs(); fetchCAPAs(); }}>
            {t('pages.quality.retry') || 'Retry'}
          </Button>
        </div>
      )}

      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.quality.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.quality.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: QUALITY-HUB-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.push('/quality/analytics')}>
            <TrendingUp className="mr-2 h-3.5 w-3.5" />
            {t('quality.analytics') || 'Analytics'}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
                <Plus className="mr-2 h-3.5 w-3.5" />
                {t('quality.newProtocol') || 'New Protocol'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => router.push('/quality/inspections/new')}>
                <ClipboardCheck className="mr-2 h-4 w-4" />
                {t('quality.newInspection') || 'New Inspection'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push('/quality/ncrs/new')}>
                <AlertTriangle className="mr-2 h-4 w-4" />
                {t('quality.newNCR') || 'New NCR'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push('/quality/capas/new')}>
                <Shield className="mr-2 h-4 w-4" />
                {t('quality.newCAPA') || 'New CAPA'}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats */}
      <QualityStats />

      {/* Tabs */}
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
        <CardHeader className="pb-0 border-b border-rams-line bg-rams-panel/20">
          <div className="flex gap-0 overflow-x-auto">
            <button
              onClick={() => handleTabChange('inspections')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative',
                activeTab === 'inspections'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40 border-r border-rams-line'
              )}
            >
              <div className="flex items-center gap-2">
                <ClipboardCheck className="h-3.5 w-3.5" />
                {t('quality.tabs.syncGates') || 'Sync Gates'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('ncrs')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'ncrs'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-3.5 w-3.5" />
                {t('quality.tabs.anomalies') || 'Anomalies (NCR)'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('capas')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'capas'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <Shield className="h-3.5 w-3.5" />
                {t('quality.tabs.protocols') || 'Protocols (CAPA)'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('msa')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'msa'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <Ruler className="h-3.5 w-3.5" />
                {t('pages.quality.tabs.msa') || 'MSA / GRR'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('capability')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'capability'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <Gauge className="h-3.5 w-3.5" />
                {t('pages.quality.tabs.capability') || 'Cp / Cpk'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('customer')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'customer'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <Smile className="h-3.5 w-3.5" />
                {t('quality.tabs.customerSatisfaction') || 'Customer Satisfaction'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('fai')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'fai'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <FileCheck className="h-3.5 w-3.5" />
                {t('pages.quality.tabs.fai') || 'FAI / AS9102'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('self')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'self'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <ClipboardList className="h-3.5 w-3.5" />
                {t('pages.quality.tabs.selfInspection') || 'Self Inspection'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('lab')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'lab'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <FlaskConical className="h-3.5 w-3.5" />
                {t('pages.quality.tabs.labManagement') || 'Lab Management'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('aql')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'aql'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <FileText className="h-3.5 w-3.5" />
                {t('pages.quality.tabs.aqlSampling') || 'AQL Sampling'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('traceability')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'traceability'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <FileText className="h-3.5 w-3.5" />
                {t('pages.quality.tabs.traceability') || 'Traceability'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('change-point')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-r border-rams-line',
                activeTab === 'change-point'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <TrendingUp className="h-3.5 w-3.5" />
                {t('pages.quality.tabs.changePoint') || 'Change Point'}
              </div>
            </button>
            <button
              onClick={() => handleTabChange('management-review')}
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative',
                activeTab === 'management-review'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
            >
              <div className="flex items-center gap-2">
                <FileText className="h-3.5 w-3.5" />
                {t('pages.quality.tabs.managementReview') || 'Management Review'}
              </div>
            </button>
          </div>
        </CardHeader>
        <CardContent className="p-6 bg-rams-module">
          {activeTab === 'inspections' && <InspectionsTab />}
          {activeTab === 'ncrs' && <NCRsTab />}
          {activeTab === 'capas' && <CAPAsTab />}
          {activeTab === 'msa' && <MSATab />}
          {activeTab === 'capability' && <CapabilityTab />}
          {activeTab === 'customer' && <CustomerSatisfactionTab />}
          {activeTab === 'fai' && <FAITab />}
          {activeTab === 'self' && <SelfInspectionTab />}
          {activeTab === 'lab' && <LabManagementTab />}
          {activeTab === 'aql' && <AQLSamplingTab />}
          {activeTab === 'traceability' && <TraceabilityTab />}
          {activeTab === 'change-point' && <ChangePointTab />}
          {activeTab === 'management-review' && <ManagementReviewTab />}
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
