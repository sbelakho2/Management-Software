'use client';

import * as React from 'react';
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
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Avatar } from '@/components/ui/avatar';
import Link from 'next/link';
import { hasPageAccess } from '@/lib/page-access';
import { useAuthStore, useHRStore } from '@/stores';
import type { UserRole } from '@/types';

function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  variant = 'default',
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  trend?: string;
  variant?: 'default' | 'warning' | 'danger' | 'success';
}) {
  const variantStyles = {
    default: 'bg-primary/10 text-primary',
    warning: 'bg-amber-500/10 text-amber-600',
    danger: 'bg-destructive/10 text-destructive',
    success: 'bg-emerald-500/10 text-emerald-600',
  };

  return (
    <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{title}</p>
            <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{value}</p>
            {trend && <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 mt-2">{trend}</p>}
          </div>
          <div className={`p-4 rounded-2xl shadow-sm ${variantStyles[variant]}`}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function HRDashboard() {
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
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 page-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            People & Talent
          </h1>
          <p className="text-muted-foreground font-medium">
            Manage organizational headcount, certifications, and human capital velocity
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasPageAccess('/training', userRoles) && (
            <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary" asChild>
              <Link href="/training">
                <GraduationCap className="h-4 w-4 mr-2" />
                Training Matrix
              </Link>
            </Button>
          )}
          {hasPageAccess('/hr/add', userRoles) && (
            <Button size="lg" className="rounded-xl shadow-glow subtle-shine">
              <UserPlus className="h-4 w-4 mr-2" />
              Add Employee
            </Button>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Organizational Headcount"
          value={stats?.total_employees || 0}
          icon={Users}
          trend={`+${stats?.new_hires_this_month || 0} vs LAST CYCLE`}
          variant="success"
        />
        <StatCard
          title="Active Opportunity Pulse"
          value={stats?.open_positions || 0}
          icon={UserPlus}
        />
        <StatCard
          title="Capacity Synchronization"
          value={stats?.pending_time_off || 0}
          icon={Calendar}
          variant="warning"
        />
        <StatCard
          title="Intelligence Thresholds"
          value={stats?.expiring_certifications || 0}
          icon={Award}
          variant="danger"
        />
      </div>

      {/* Main Content */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Pending Time Off Requests */}
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary">
                <Clock className="h-5 w-5" />
              </div>
              Strategic Availability
            </CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 pl-11">Capacity synchronization requests</CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="space-y-3">
              {[
                { id: 1, employee: 'John Smith', type: 'PTO', dates: 'Dec 23-27' },
                { id: 2, employee: 'Sarah Johnson', type: 'Sick', dates: 'Dec 18' },
              ].map((request) => (
                <div
                  key={request.id}
                  className="flex items-center justify-between p-4 rounded-2xl bg-muted/10 border border-border/5 group transition-all hover:bg-primary/5"
                >
                  <div className="flex items-center gap-4">
                    <Avatar
                      alt={request.employee}
                      fallback={request.employee}
                      size="sm"
                      className="ring-2 ring-background shadow-sm"
                    />
                    <div>
                      <p className="font-heading font-bold text-sm tracking-tight text-foreground/80 group-hover:text-primary transition-colors">{request.employee}</p>
                      <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40">{request.dates}</p>
                    </div>
                  </div>
                  <Badge variant="secondary" className="text-[9px] font-bold uppercase tracking-widest bg-background/50">{request.type}</Badge>
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-6">
              <Button size="sm" className="flex-1 rounded-xl shadow-glow">Commit Sync</Button>
              <Button size="sm" variant="outline" className="flex-1 rounded-xl border-primary/20 hover:bg-primary/5 text-primary">Review All</Button>
            </div>
          </CardContent>
        </Card>

        {/* Expiring Certifications */}
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <div className="p-2 rounded-xl bg-danger/10 text-danger">
                <AlertCircle className="h-5 w-5" />
              </div>
              Intelligence Thresholds
            </CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 pl-11">Renewals required for compliance</CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="space-y-3">
              {expiringCerts.map((cert) => (
                <div
                  key={cert.id}
                  className="flex items-center justify-between p-4 rounded-2xl bg-danger/5 border border-danger/5 group transition-all hover:bg-danger/10"
                >
                  <div>
                    <p className="font-heading font-bold text-sm tracking-tight text-foreground/80 group-hover:text-danger transition-colors">{cert.employee}</p>
                    <p className="text-[9px] font-bold uppercase tracking-widest text-danger/40">{cert.cert}</p>
                  </div>
                  <Badge 
                    variant={cert.priority === 'high' ? 'destructive' : 'outline'}
                    className={cn(
                      "text-[9px] font-bold uppercase tracking-widest rounded-md",
                      cert.priority === 'medium' ? 'border-amber-500/20 text-amber-600 bg-amber-500/5' : ''
                    )}
                  >
                    {cert.expires}
                  </Badge>
                </div>
              ))}
            </div>
            {hasPageAccess('/training/matrix', userRoles) && (
              <Button variant="outline" className="w-full mt-6 rounded-xl border-primary/20 hover:bg-primary/5 text-primary h-11" asChild>
                <Link href="/training/matrix">
                  <FileText className="h-4 w-4 mr-2" />
                  Access Training Matrix
                </Link>
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Department Headcount */}
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary">
                <Building2 className="h-5 w-5" />
              </div>
              Node Distribution
            </CardTitle>
            <CardDescription className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 pl-11">Headcount by department node</CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="space-y-6">
              {headcount.map((dept) => (
                <div key={dept.name} className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-widest text-foreground/70">{dept.name}</span>
                    <span className="text-[10px] font-mono font-bold text-primary/60 bg-primary/5 px-2 py-0.5 rounded-full">{dept.count} NODES</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted/20 overflow-hidden shadow-inner-soft">
                    <div 
                      className="h-full bg-gradient-to-r from-primary to-primary/60 transition-all duration-1000" 
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
  );
}
