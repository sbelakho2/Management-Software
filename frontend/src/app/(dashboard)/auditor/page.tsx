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
    <div className="space-y-8 page-fade-in" data-testid="auditor-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight ">
            {t('pages.auditor.title')}
          </h1>
          <p className="text-muted-foreground font-medium">
            {t('pages.auditor.subtitle')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            <Download className="h-4 w-4 mr-2" />
            Export Intelligence
          </Button>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine">
            <FileSearch className="h-4 w-4 mr-2" />
            New Protocol
          </Button>
        </div>
      </div>

      {/* Compliance Score Banner */}
      <Card className="bg-gradient-to-r from-emerald-50 to-blue-50 dark:from-emerald-950/20 dark:to-blue-950/20 border-emerald-200 dark:border-emerald-900">
        <CardContent className="py-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Overall Compliance Score</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-4xl font-bold text-emerald-600">{auditStats.complianceScore}%</span>
                <Badge variant="outline" className="bg-emerald-100 text-emerald-700 border-emerald-300">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +2% from last quarter
                </Badge>
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-3">
              <AmbientStatus 
                status={auditStats.criticalFindings > 0 ? 'warning' : 'operational'} 
                label={auditStats.criticalFindings > 0 ? `${auditStats.criticalFindings} Critical Findings` : 'Compliance Optimal'}
              />
              <Shield className="h-16 w-16 text-emerald-600/20" />
            </div>
          </div>
          <div className="goal-progress-track mt-4">
            <div className="goal-progress-fill bg-emerald-500" style={{ width: `${auditStats.complianceScore}%` }} />
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
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upcoming Audits */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Upcoming Audits
            </CardTitle>
            <CardDescription>Scheduled audits in the next 60 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {upcomingAudits.map((audit) => (
                <div
                  key={audit.id}
                  className="flex items-center justify-between py-3 border-b last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-full ${
                      audit.priority === 'high' ? 'bg-destructive/10 text-destructive' : 'bg-primary/10 text-primary'
                    }`}>
                      <FileSearch className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{audit.name}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        {audit.date}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{audit.type}</Badge>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
              ))}
            </div>
            <Button variant="outline" className="w-full mt-4">
              View Audit Calendar
            </Button>
          </CardContent>
        </Card>

        {/* Open Findings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Open Findings
            </CardTitle>
            <CardDescription>Findings requiring action</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {openFindings.map((finding) => (
                <div
                  key={finding.id}
                  className="flex items-center justify-between py-3 border-b last:border-0"
                >
                  <div className="flex-1">
                    <p className="font-medium text-sm">{finding.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge 
                        variant="outline" 
                        className={finding.severity === 'major' ? 'border-destructive text-destructive' : ''}
                      >
                        {finding.severity}
                      </Badge>
                      <span className="text-xs text-muted-foreground">{finding.area}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-medium ${finding.daysOverdue > 0 ? 'text-destructive' : ''}`}>
                      {finding.daysOverdue > 0 ? `${finding.daysOverdue}d overdue` : `Due ${finding.dueDate}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <Button variant="outline" className="w-full mt-4">
              <Filter className="h-4 w-4 mr-2" />
              View All Findings
            </Button>
          </CardContent>
        </Card>

        {/* Compliance by Area */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Compliance by Area
            </CardTitle>
            <CardDescription>Scores by audit area</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {complianceAreas.map((area) => (
                <div key={area.name} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{area.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">{area.audits} audits</span>
                      <span className={`font-bold ${area.score >= 90 ? 'text-emerald-600' : 'text-amber-600'}`}>
                        {area.score}%
                      </span>
                    </div>
                  </div>
                  <Progress value={area.score} className="h-2" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Audits */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Recent Audits
            </CardTitle>
            <CardDescription>Latest completed audits</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentAudits.map((audit) => (
                <div
                  key={audit.id}
                  className="flex items-center justify-between py-3 border-b last:border-0"
                >
                  <div>
                    <p className="font-medium text-sm">{audit.name}</p>
                    <p className="text-xs text-muted-foreground">{audit.date}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{audit.findings} findings</Badge>
                    <Badge 
                      variant={audit.status === 'closed' ? 'outline' : 'destructive'}
                      className={audit.status === 'closed' ? 'text-emerald-600' : ''}
                    >
                      {audit.status}
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
