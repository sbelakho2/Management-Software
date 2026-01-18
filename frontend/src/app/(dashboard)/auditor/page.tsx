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
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import Link from 'next/link';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';

// Demo data
const auditStats = {
  totalAudits: 24,
  completedThisYear: 18,
  openFindings: 12,
  criticalFindings: 2,
  upcomingAudits: 3,
  complianceScore: 94,
};

const upcomingAudits = [
  { id: 1, name: 'ISO 9001 Surveillance', date: 'Jan 15, 2025', type: 'External', priority: 'high' },
  { id: 2, name: 'Internal Quality Audit', date: 'Jan 22, 2025', type: 'Internal', priority: 'medium' },
  { id: 3, name: 'Supplier Assessment - ABC Corp', date: 'Feb 5, 2025', type: 'Supplier', priority: 'medium' },
];

const openFindings = [
  { id: 1, title: 'Document control procedure gap', area: 'Quality', severity: 'major', dueDate: 'Dec 20', daysOverdue: 0 },
  { id: 2, title: 'Training records incomplete', area: 'HR', severity: 'minor', dueDate: 'Dec 25', daysOverdue: 0 },
  { id: 3, title: 'Calibration schedule not followed', area: 'Production', severity: 'major', dueDate: 'Dec 15', daysOverdue: 5 },
  { id: 4, title: 'Safety signage missing in Zone B', area: 'Safety', severity: 'minor', dueDate: 'Dec 30', daysOverdue: 0 },
];

const complianceAreas = [
  { name: 'Quality Management', score: 96, audits: 8 },
  { name: 'Safety & Environment', score: 92, audits: 5 },
  { name: 'Document Control', score: 88, audits: 4 },
  { name: 'Training & Competency', score: 95, audits: 3 },
  { name: 'Supplier Management', score: 91, audits: 4 },
];

const recentAudits = [
  { id: 1, name: 'Q3 Internal Audit', date: 'Oct 15, 2024', findings: 4, status: 'closed' },
  { id: 2, name: 'Customer Audit - XYZ Inc', date: 'Nov 8, 2024', findings: 2, status: 'open' },
  { id: 3, name: 'Safety Inspection', date: 'Nov 22, 2024', findings: 3, status: 'open' },
  { id: 4, name: 'Process Audit - Welding', date: 'Dec 5, 2024', findings: 1, status: 'closed' },
];

export default function AuditorDashboard() {
  const { t } = useI18n();
  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="auditor-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-border pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.auditor.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.auditor.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: AUDIT-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-border">
            <Download className="h-3.5 w-3.5 mr-2" />
            Export Intel
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]">
            <FileSearch className="h-3.5 w-3.5 mr-2" />
            Initialize Protocol
          </Button>
        </div>
      </div>

      {/* Compliance Score Banner */}
      <Card className="rounded-rams-sm bg-rams-module border border-rams-border overflow-hidden">
        <CardContent className="p-0">
          <div className="grid grid-cols-1 md:grid-cols-3">
            <div className="p-8 md:col-span-2 space-y-6">
              <div>
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">Organizational Compliance Magnitude</p>
                <div className="flex items-baseline gap-4 mt-2">
                  <span className="text-6xl font-mono font-bold text-rams-green tabular-nums">{auditStats.complianceScore}%</span>
                  <Badge variant="outline" className="rounded-none border-rams-green/20 bg-rams-green/5 text-rams-green font-mono font-black text-[9px] h-5">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +2% ALPHA_SHIFT
                  </Badge>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-[9px] font-mono font-black uppercase tracking-widest text-muted-foreground/40">
                  <span>Threshold_Alignment</span>
                  <span>Optimal</span>
                </div>
                <div className="h-1.5 bg-rams-panel border border-rams-border/30 overflow-hidden">
                  <div className="h-full bg-rams-green transition-all duration-1000" style={{ width: `${auditStats.complianceScore}%` }} />
                </div>
              </div>
            </div>
            <div className="p-8 bg-rams-panel/30 border-l border-rams-border flex flex-col justify-between">
              <AmbientStatus 
                status={auditStats.criticalFindings > 0 ? 'warning' : 'operational'} 
                label={auditStats.criticalFindings > 0 ? `${auditStats.criticalFindings} Critical Findings` : 'Compliance Optimal'}
              />
              <div className="flex items-center gap-4 mt-8 opacity-20">
                <Shield className="h-12 w-12" />
                <div className="text-[10px] font-mono font-black uppercase leading-tight">
                  Security_Protocol<br />Verified
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid - Using Shared StatCard */}
      <StatSection label="Audit Metrics" columns={4}>
        <StatCard
          value={auditStats.completedThisYear}
          label="Audit Protocols (YTD)"
          icon={CheckCircle2}
          iconColor="success"
          goal={{ current: auditStats.completedThisYear, target: auditStats.totalAudits }}
        />
        <StatCard
          value={auditStats.openFindings}
          label="Unresolved Findings"
          icon={AlertTriangle}
          iconColor="warning"
          critical={auditStats.criticalFindings > 2}
        />
        <StatCard
          value={auditStats.upcomingAudits}
          label="Scheduled Protocols"
          icon={Calendar}
          iconColor="info"
        />
        <StatCard
          value={12}
          label="Resolution Velocity"
          icon={Clock}
          iconColor="primary"
          trend="down"
          trendValue="Mean days to closure"
        />
      </StatSection>

      {/* Main Content */}
      <div className="grid gap-8 lg:grid-cols-2">
        {/* Upcoming Audits */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-border">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-border">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Calendar className="h-4 w-4 text-rams-orange" />
              Upcoming Audits
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-border/30">
              {upcomingAudits.map((audit) => (
                <div
                  key={audit.id}
                  className="flex items-center justify-between p-4 hover:bg-rams-panel transition-none group"
                >
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      "p-2 rounded-rams-sm border border-rams-border",
                      audit.priority === 'high' ? 'bg-rams-red/5 text-rams-red border-rams-red/20' : 'bg-rams-panel text-muted-foreground'
                    )}>
                      <FileSearch className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{audit.name}</p>
                      <div className="flex items-center gap-2 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">
                        <Calendar className="h-3 w-3" />
                        {audit.date}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="rounded-none border-rams-border text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel">{audit.type}</Badge>
                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 bg-rams-panel/10 border-t border-rams-border">
              <Button variant="outline" size="sm" className="w-full rounded-rams-sm text-[9px] font-black uppercase tracking-widest h-8">
                VIEW_AUDIT_CALENDAR
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Open Findings */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-border">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-border">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rams-red" />
              Open Findings
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-border/30">
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
                          finding.severity === 'major' ? 'border-rams-red/20 text-rams-red' : 'border-rams-border'
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
                      finding.daysOverdue > 0 ? 'text-rams-red' : 'text-muted-foreground/60'
                    )}>
                      {finding.daysOverdue > 0 ? `${finding.daysOverdue}D_OVERDUE` : `DUE: ${finding.dueDate.toUpperCase()}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 bg-rams-panel/10 border-t border-rams-border">
              <Button variant="outline" size="sm" className="w-full rounded-rams-sm text-[9px] font-black uppercase tracking-widest h-8">
                VIEW_ALL_FINDINGS
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Compliance by Area */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-border">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-border">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Building2 className="h-4 w-4 text-rams-orange" />
              Compliance by Area
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {complianceAreas.map((area) => (
              <div key={area.name} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-widest text-foreground/70">{area.name}</span>
                  <div className="flex items-center gap-4">
                    <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">{area.audits} AUDITS</span>
                    <span className={cn(
                      "text-sm font-mono font-bold tabular-nums",
                      area.score >= 90 ? 'text-rams-green' : 'text-rams-orange'
                    )}>
                      {area.score}%
                    </span>
                  </div>
                </div>
                <div className="h-1 bg-rams-panel border border-rams-border/30 overflow-hidden">
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
        <Card className="rounded-rams-sm overflow-hidden border-rams-border">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-border">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <FileText className="h-4 w-4 text-rams-orange" />
              Recent Audits
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-border/30">
              {recentAudits.map((audit) => (
                <div
                  key={audit.id}
                  className="flex items-center justify-between p-4 hover:bg-rams-panel transition-none group"
                >
                  <div>
                    <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{audit.name}</p>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{audit.date}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="rounded-none border-rams-border text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel">{audit.findings} FINDINGS</Badge>
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
  );
}
