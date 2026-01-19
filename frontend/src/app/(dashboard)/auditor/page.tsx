'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';
import { 
  FileSearch, 
  CheckCircle2, 
  AlertTriangle, 
  Clock,
  Calendar,
  FileText,
  Shield,
  TrendingUp,
  Filter,
  Download,
  ChevronRight,
  Building2,
  Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import Link from 'next/link';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';
import { cn } from '@/lib/utils';
import { useAuditorStore } from '@/stores';
import { PageGuard } from '@/components/layout/page-guard';
import { QUALITY_ROLES } from '@/lib/page-access';

// Fallback demo data when API is not available
const fallbackStats = {
  total_audits: 24,
  completed_this_year: 18,
  open_findings: 12,
  critical_findings: 2,
  upcoming_audits: 3,
  compliance_score: 94,
};

const fallbackUpcomingAudits = [
  { id: '1', name: 'ISO 9001 Surveillance', scheduled_date: 'Jan 15, 2025', audit_type: 'External', priority: 'high', status: 'scheduled', findings_count: 0 },
  { id: '2', name: 'Internal Quality Audit', scheduled_date: 'Jan 22, 2025', audit_type: 'Internal', priority: 'medium', status: 'scheduled', findings_count: 0 },
  { id: '3', name: 'Supplier Assessment - ABC Corp', scheduled_date: 'Feb 5, 2025', audit_type: 'Supplier', priority: 'medium', status: 'scheduled', findings_count: 0 },
];

const fallbackOpenFindings = [
  { id: '1', audit_id: '1', title: 'Document control procedure gap', area: 'Quality', severity: 'major', status: 'open', due_date: 'Dec 20', days_overdue: 0 },
  { id: '2', audit_id: '1', title: 'Training records incomplete', area: 'HR', severity: 'minor', status: 'in_progress', due_date: 'Dec 25', days_overdue: 0 },
  { id: '3', audit_id: '1', title: 'Calibration schedule not followed', area: 'Production', severity: 'major', status: 'open', due_date: 'Dec 15', days_overdue: 5 },
  { id: '4', audit_id: '1', title: 'Safety signage missing in Zone B', area: 'Safety', severity: 'minor', status: 'open', due_date: 'Dec 30', days_overdue: 0 },
];

const fallbackComplianceAreas = [
  { name: 'Quality Management', score: 96, audits: 8, trend: 'stable' },
  { name: 'Safety & Environment', score: 92, audits: 5, trend: 'up' },
  { name: 'Document Control', score: 88, audits: 4, trend: 'down' },
  { name: 'Training & Competency', score: 95, audits: 3, trend: 'stable' },
  { name: 'Supplier Management', score: 91, audits: 4, trend: 'up' },
];

const fallbackRecentAudits = [
  { id: '1', name: 'Q3 Internal Audit', scheduled_date: 'Oct 15, 2024', findings_count: 4, status: 'closed', audit_type: 'internal', priority: 'medium' },
  { id: '2', name: 'Customer Audit - XYZ Inc', scheduled_date: 'Nov 8, 2024', findings_count: 2, status: 'completed', audit_type: 'customer', priority: 'high' },
  { id: '3', name: 'Safety Inspection', scheduled_date: 'Nov 22, 2024', findings_count: 3, status: 'completed', audit_type: 'internal', priority: 'medium' },
  { id: '4', name: 'Process Audit - Welding', scheduled_date: 'Dec 5, 2024', findings_count: 1, status: 'closed', audit_type: 'internal', priority: 'low' },
];

export default function AuditorDashboard() {
  const { t } = useI18n();
  const {
    stats,
    upcomingAudits: apiUpcomingAudits,
    openFindings: apiOpenFindings,
    complianceAreas: apiComplianceAreas,
    audits: apiRecentAudits,
    isLoading,
    fetchAll,
    fetchAudits
  } = useAuditorStore();

  // Fetch data on mount
  React.useEffect(() => {
    fetchAll();
    fetchAudits();
  }, [fetchAll, fetchAudits]);

  // Use API data or fallback to demo data
  const auditStats = stats || fallbackStats;
  const upcomingAudits = apiUpcomingAudits.length > 0 ? apiUpcomingAudits : fallbackUpcomingAudits;
  const openFindings = apiOpenFindings.length > 0 ? apiOpenFindings : fallbackOpenFindings;
  const complianceAreas = apiComplianceAreas.length > 0 ? apiComplianceAreas : fallbackComplianceAreas;
  const recentAudits = apiRecentAudits.length > 0 ? apiRecentAudits : fallbackRecentAudits;
  return (
    <PageGuard requiredRoles={QUALITY_ROLES}>
    <div className="space-y-8 page-fade-in pb-12" data-testid="auditor-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.auditor.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.auditor.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.auditor.station')}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line">
            <Download className="h-3.5 w-3.5 mr-2" />
            {t('pages.auditor.exportIntel') || 'Export Intel'}
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]">
            <FileSearch className="h-3.5 w-3.5 mr-2" />
            {t('pages.auditor.initializeProtocol') || 'Initialize Protocol'}
          </Button>
        </div>
      </div>

      {/* Compliance Score Banner */}
      <Card className="rounded-rams-sm bg-rams-module border border-rams-line overflow-hidden">
        <CardContent className="p-0">
          <div className="grid grid-cols-1 md:grid-cols-3">
            <div className="p-8 md:col-span-2 space-y-6">
              <div>
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">{t('pages.auditor.organizationalComplianceMagnitude') || 'Organizational Compliance Magnitude'}</p>
                <div className="flex items-baseline gap-4 mt-2">
                  <span className="text-6xl font-mono font-bold text-rams-green tabular-nums">{auditStats.compliance_score}%</span>
                  <Badge variant="outline" className="rounded-none border-rams-green/20 bg-rams-green/5 text-rams-green font-mono font-black text-[9px] h-5">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    {t('pages.auditor.alphaShift')}
                  </Badge>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-[9px] font-mono font-black uppercase tracking-widest text-muted-foreground/40">
                  <span>{t('pages.auditor.thresholdAlignment')}</span>
                  <span>{t('pages.auditor.optimal')}</span>
                </div>
                <div className="h-1.5 bg-rams-panel border border-rams-line overflow-hidden">
                  <div className="h-full bg-rams-green transition-all duration-1000" style={{ width: `${auditStats.compliance_score}%` }} />
                </div>
              </div>
            </div>
            <div className="p-8 bg-rams-panel/30 border-l border-rams-line flex flex-col justify-between">
              <AmbientStatus 
                status={auditStats.critical_findings > 0 ? 'warning' : 'operational'} 
                label={auditStats.critical_findings > 0 ? `${auditStats.critical_findings} ${t('pages.auditor.criticalFindings')}` : t('pages.auditor.complianceOptimal')}
              />
              <div className="flex items-center gap-4 mt-8 opacity-20">
                <Shield className="h-12 w-12" />
                <div className="text-[10px] font-mono font-black uppercase leading-tight">
                  {t('pages.auditor.securityProtocol')}<br />{t('pages.auditor.verified')}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid - Using Shared StatCard */}
      <StatSection label={t('pages.auditor.stats.auditMetrics') || 'Audit Metrics'} columns={4}>
        <StatCard
          value={auditStats.completed_this_year}
          label={t('pages.auditor.stats.auditProtocolsYtd')}
          icon={CheckCircle2}
          iconColor="success"
          goal={{ current: auditStats.completed_this_year, target: auditStats.total_audits }}
        />
        <StatCard
          value={auditStats.open_findings}
          label={t('pages.auditor.stats.unresolvedFindings')}
          icon={AlertTriangle}
          iconColor="warning"
          critical={auditStats.critical_findings > 2}
        />
        <StatCard
          value={auditStats.upcoming_audits}
          label={t('pages.auditor.stats.scheduledProtocols')}
          icon={Calendar}
          iconColor="info"
        />
        <StatCard
          value={12}
          label={t('pages.auditor.stats.resolutionVelocity')}
          icon={Clock}
          iconColor="primary"
          trend="down"
          trendValue={t('pages.auditor.stats.meanDaysToClosure')}
        />
      </StatSection>

      {/* Main Content */}
      <div className="grid gap-8 lg:grid-cols-2">
        {/* Upcoming Audits */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-line">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Calendar className="h-4 w-4 text-rams-orange" />
              {t('pages.auditor.upcomingAudits') || 'Upcoming Audits'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-line/30">
              {upcomingAudits.map((audit) => (
                <div
                  key={audit.id}
                  className="flex items-center justify-between p-4 hover:bg-rams-panel transition-none group"
                >
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      "p-2 rounded-rams-sm border border-rams-line",
                      audit.priority === 'high' ? 'bg-rams-red/5 text-rams-red border-rams-red/20' : 'bg-rams-panel text-muted-foreground'
                    )}>
                      <FileSearch className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{audit.name}</p>
                      <div className="flex items-center gap-2 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">
                        <Calendar className="h-3 w-3" />
                        {audit.scheduled_date}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="rounded-none border-rams-line text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel">{audit.audit_type}</Badge>
                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/20 group-hover:text-rams-orange transition-none" />
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 bg-rams-panel/10 border-t border-rams-line">
              <Button variant="outline" size="sm" className="w-full rounded-rams-sm text-[9px] font-black uppercase tracking-widest h-8">
                {t('pages.auditor.viewAuditCalendar')}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Open Findings */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-line">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rams-red" />
              {t('pages.auditor.openFindings') || 'Open Findings'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-line/30">
              {openFindings.map((finding) => (
                <div
                  key={finding.id}
                  className="flex items-center justify-between p-4 hover:bg-rams-panel transition-none group"
                >
                  <div className="flex-1">
                    <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{finding.title}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <Badge 
                        variant="outline" 
                        className={cn(
                          "rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel",
                          finding.severity === 'major' ? 'border-rams-red/20 text-rams-red' : 'border-rams-line'
                        )}
                      >
                        {finding.severity}
                      </Badge>
                      <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">{finding.area}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={cn(
                      "text-[10px] font-mono font-black uppercase tracking-tighter",
                      (finding.days_overdue ?? 0) > 0 ? 'text-rams-red' : 'text-muted-foreground/60'
                    )}>
                      {(finding.days_overdue ?? 0) > 0 ? `${finding.days_overdue}D_OVERDUE` : `DUE: ${(finding.due_date ?? '').toUpperCase()}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 bg-rams-panel/10 border-t border-rams-line">
              <Button variant="outline" size="sm" className="w-full rounded-rams-sm text-[9px] font-black uppercase tracking-widest h-8">
                {t('pages.auditor.viewAllFindings')}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Compliance by Area */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-line">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Building2 className="h-4 w-4 text-rams-orange" />
              {t('pages.auditor.complianceByArea') || 'Compliance by Area'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {complianceAreas.map((area) => (
              <div key={area.name} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-widest text-foreground/70">{area.name}</span>
                  <div className="flex items-center gap-4">
                    <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">{area.audits} {t('pages.auditor.audits')}</span>
                    <span className={cn(
                      "text-sm font-mono font-bold tabular-nums",
                      area.score >= 90 ? 'text-rams-green' : 'text-rams-orange'
                    )}>
                      {area.score}%
                    </span>
                  </div>
                </div>
                <div className="h-1 bg-rams-panel border border-rams-line overflow-hidden">
                  <div className={cn(
                    "h-full transition-all duration-1000",
                    area.score >= 90 ? 'bg-rams-green' : 'bg-rams-orange'
                  )} style={{ width: `${area.score}%` }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Recent Audits */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-line">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <FileText className="h-4 w-4 text-rams-orange" />
              {t('pages.auditor.recentAudits') || 'Recent Audits'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-line/30">
              {recentAudits.map((audit) => (
                <div
                  key={audit.id}
                  className="flex items-center justify-between p-4 hover:bg-rams-panel transition-none group"
                >
                  <div>
                    <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{audit.name}</p>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{audit.scheduled_date}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="rounded-none border-rams-line text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel">{audit.findings_count} FINDINGS</Badge>
                    <Badge 
                      variant={audit.status === 'closed' ? 'outline' : 'warning'}
                      className={cn(
                        "rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4",
                        audit.status === 'closed' ? 'border-rams-green/20 text-rams-green bg-rams-green/5' : 'bg-rams-panel'
                      )}
                    >
                      {audit.status.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
    </PageGuard>
  );
}
