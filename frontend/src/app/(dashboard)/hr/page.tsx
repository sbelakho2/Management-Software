'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';
import { 
  Users, 
  UserPlus, 
  Calendar, 
  Award,
  Clock,
  AlertCircle,
  TrendingUp,
  FileText,
  GraduationCap,
  Building2,
  ArrowUpRight,
  Target,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Avatar } from '@/components/ui/avatar';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';
import { QuickActionItem, QuickActionList } from '@/components/ui/quick-action';
import Link from 'next/link';
import { hasPageAccess, HR_ROLES } from '@/lib/page-access';
import { useAuthStore, useHRStore } from '@/stores';
import { PageGuard } from '@/components/layout/page-guard';
import type { UserRole } from '@/types';
import { cn } from '@/lib/utils';

export default function HRDashboard() {
  const { t } = useI18n();
  const { user } = useAuthStore();
  const { 
    stats, 
    headcount, 
    expiringCerts, 
    isLoading: storeLoading, 
    fetchStats, 
    fetchHeadcount, 
    fetchExpiringCerts 
  } = useHRStore();

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);

  React.useEffect(() => {
    fetchStats();
    fetchHeadcount();
    fetchExpiringCerts();
  }, [fetchStats, fetchHeadcount, fetchExpiringCerts]);

  // Combined loading state
  const isLoading = storeLoading && !stats;

  if (isLoading) {
    return (
      <div className="space-y-8 animate-in fade-in duration-500">
        <div className="flex items-center justify-between border-b border-rams-line pb-8">
          <Skeleton className="h-8 w-48 rounded-rams-sm" />
          <div className="flex gap-3">
            <Skeleton className="h-10 w-32 rounded-rams-sm" />
            <Skeleton className="h-10 w-32 rounded-rams-sm" />
          </div>
        </div>
        <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line last:border-r-0">
              <Skeleton className="h-12 w-full rounded-rams-sm" />
            </div>
          ))}
        </div>
        <div className="grid gap-8 lg:grid-cols-3">
          <Skeleton className="h-80 rounded-rams-sm" />
          <Skeleton className="h-80 rounded-rams-sm" />
          <Skeleton className="h-80 rounded-rams-sm" />
        </div>
      </div>
    );
  }

  return (
    <PageGuard requiredRoles={HR_ROLES}>
    <div className="space-y-8 page-fade-in pb-12" data-testid="hr-dashboard">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.hr.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.hr.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.hr.station')}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasPageAccess('/training', userRoles) && (
            <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line" asChild>
              <Link href="/training">
                <GraduationCap className="h-3.5 w-3.5 mr-2" />
                {t('pages.hr.trainingMatrix') || 'Training Matrix'}
              </Link>
            </Button>
          )}
          {hasPageAccess('/hr/add', userRoles) && (
            <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]">
              <UserPlus className="h-3.5 w-3.5 mr-2" />
              {t('pages.hr.initializePersonnel') || 'Initialize Personnel'}
            </Button>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className="flex items-center justify-end">
        <AmbientStatus status="operational" label={t('pages.hr.hrSystemsOnline')} />
      </div>

      {/* Stats Grid (Industrial Modules) */}
      <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-4 border border-rams-line bg-rams-line">
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.hr.headcountNode') || 'Headcount Node'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats?.total_employees || 0}</div>
          <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2 flex items-center gap-1">
            <TrendingUp className="h-3 w-3" /> +{stats?.new_hires_this_month || 0} {t('pages.hr.thisCycle')}
          </p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b lg:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.hr.opportunityPulse') || 'Opportunity Pulse'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{stats?.open_positions || 0}</div>
          <p className="text-[9px] font-mono font-bold text-rams-orange uppercase tracking-widest mt-2">{t('pages.hr.activeRecruitment')}</p>
        </div>
        <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.hr.capacitySync') || 'Capacity Sync'}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-steel tabular-nums">{stats?.pending_time_off || 0}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.hr.pendingRequests')}</p>
        </div>
        <div className="bg-rams-module p-6 border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.hr.thresholdBreaches') || 'Threshold Breaches'}</p>
          <div className={cn("text-3xl font-mono font-bold tracking-tight tabular-nums", (stats?.expiring_certifications || 0) > 5 ? "text-rams-red" : "text-foreground/90")}>
            {stats?.expiring_certifications || 0}
          </div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.hr.complianceGates')}</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Pending Time Off Requests */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Clock className="h-4 w-4 text-rams-orange" />
              {t('pages.hr.strategicAvailability') || 'Strategic Availability'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-1 space-y-1 bg-rams-module">
            {[
              { id: 1, employee: 'John Smith', type: 'PTO', dates: 'Dec 23-27' },
              { id: 2, employee: 'Sarah Johnson', type: 'Sick', dates: 'Dec 18' },
            ].map((request) => (
              <div
                key={request.id}
                className="flex items-center justify-between p-4 bg-rams-panel/40 border border-rams-line hover:bg-rams-panel transition-none group"
              >
                <div className="flex items-center gap-4">
                  <Avatar
                    alt={request.employee}
                    fallback={request.employee}
                    size="sm"
                    className="rounded-rams-sm border border-rams-line"
                  />
                  <div>
                    <p className="font-sans font-black text-[11px] uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{request.employee}</p>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-0.5">{request.dates}</p>
                  </div>
                </div>
                <Badge variant="outline" className="rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel border-rams-line">{request.type}</Badge>
              </div>
            ))}
            <div className="p-4 flex gap-2">
              <Button size="sm" className="flex-1 rounded-rams-sm bg-rams-orange text-black font-black uppercase text-[9px] h-8 transition-none">{t('pages.hr.commitSync')}</Button>
              <Button size="sm" variant="outline" className="flex-1 rounded-rams-sm border-rams-line text-[9px] font-black uppercase h-8 transition-none">{t('pages.hr.reviewAll')}</Button>
            </div>
          </CardContent>
        </Card>

        {/* Expiring Certifications */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-rams-red" />
              {t('pages.hr.intelligenceThresholds') || 'Intelligence Thresholds'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-1 space-y-1 bg-rams-module">
            {expiringCerts.map((cert) => (
              <div
                key={cert.id}
                className="flex items-center justify-between p-4 bg-rams-red/5 border border-rams-red/10 hover:bg-rams-red/10 transition-none group"
              >
                <div>
                  <p className="font-sans font-black text-[11px] uppercase tracking-tight text-foreground/80 group-hover:text-rams-red transition-none">{cert.employee}</p>
                  <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-rams-red/40 mt-0.5">{cert.cert}</p>
                </div>
                <Badge 
                  variant={cert.priority === 'high' ? 'destructive' : 'outline'}
                  className={cn(
                    "rounded-none text-[8px] font-black uppercase tracking-widest px-1.5 h-4",
                    cert.priority === 'medium' ? 'border-rams-orange/20 text-rams-orange bg-rams-orange/5' : 'bg-rams-panel border-rams-line'
                  )}
                >
                  {cert.expires.toUpperCase()}
                </Badge>
              </div>
            ))}
            {hasPageAccess('/training/matrix', userRoles) && (
              <div className="p-4">
                <Button variant="outline" className="w-full rounded-rams-sm border-rams-line text-[9px] font-black uppercase h-10 transition-none" asChild>
                  <Link href="/training/matrix">
                    <FileText className="h-3.5 w-3.5 mr-2" />
                    {t('pages.hr.accessTrainingMatrix')}
                  </Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Department Headcount */}
        <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Building2 className="h-4 w-4 text-rams-orange" />
              {t('pages.hr.nodeDistribution') || 'Node Distribution'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 bg-rams-module">
            <div className="space-y-6">
              {headcount.map((dept) => (
                <div key={dept.name} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase tracking-widest text-foreground/70">{dept.name}</span>
                    <span className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase">{dept.count} {t('pages.hr.nodes')}</span>
                  </div>
                  <div className="h-1 bg-rams-panel border border-rams-line overflow-hidden">
                    <div 
                      className="h-full bg-rams-orange transition-all duration-1000" 
                      style={{ width: `${dept.percentage}%` }}
                    />
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
