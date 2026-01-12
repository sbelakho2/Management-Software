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

// Demo data
const hrStats = {
  totalEmployees: 156,
  openPositions: 8,
  pendingTimeOff: 12,
  expiringCertifications: 5,
  newHiresThisMonth: 3,
  turnoverRate: 4.2,
};

const pendingRequests = [
  { id: 1, employee: 'John Smith', type: 'PTO', dates: 'Dec 23-27', status: 'pending', avatar: null },
  { id: 2, employee: 'Sarah Johnson', type: 'Sick', dates: 'Dec 18', status: 'pending', avatar: null },
  { id: 3, employee: 'Mike Wilson', type: 'PTO', dates: 'Dec 30-Jan 2', status: 'pending', avatar: null },
];

const expiringCerts = [
  { id: 1, employee: 'Tom Brown', cert: 'Forklift Operator', expires: '5 days', priority: 'high' },
  { id: 2, employee: 'Lisa Chen', cert: 'First Aid', expires: '12 days', priority: 'medium' },
  { id: 3, employee: 'James Lee', cert: 'Crane Operator', expires: '18 days', priority: 'medium' },
  { id: 4, employee: 'Emma Davis', cert: 'Safety Training', expires: '25 days', priority: 'low' },
];

const departmentHeadcount = [
  { name: 'Operations', count: 68, percentage: 44 },
  { name: 'Engineering', count: 32, percentage: 21 },
  { name: 'Quality', count: 18, percentage: 12 },
  { name: 'Sales', count: 22, percentage: 14 },
  { name: 'Admin', count: 16, percentage: 10 },
];

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  trend,
  variant = 'default' 
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
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold mt-1">{value}</p>
            {trend && (
              <p className="text-xs text-muted-foreground mt-1">{trend}</p>
            )}
          </div>
          <div className={`p-3 rounded-full ${variantStyles[variant]}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function HRDashboard() {
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">HR Dashboard</h1>
          <p className="text-muted-foreground">
            Manage employees, track certifications, and handle requests
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/training">
              <GraduationCap className="h-4 w-4 mr-2" />
              Training
            </Link>
          </Button>
          <Button>
            <UserPlus className="h-4 w-4 mr-2" />
            Add Employee
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Employees"
          value={hrStats.totalEmployees}
          icon={Users}
          trend={`+${hrStats.newHiresThisMonth} this month`}
          variant="success"
        />
        <StatCard
          title="Open Positions"
          value={hrStats.openPositions}
          icon={UserPlus}
        />
        <StatCard
          title="Pending Time Off"
          value={hrStats.pendingTimeOff}
          icon={Calendar}
          variant="warning"
        />
        <StatCard
          title="Expiring Certs"
          value={hrStats.expiringCertifications}
          icon={Award}
          variant="danger"
        />
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Pending Time Off Requests */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Pending Requests
            </CardTitle>
            <CardDescription>Time off awaiting approval</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {pendingRequests.map((request) => (
                <div
                  key={request.id}
                  className="flex items-center justify-between py-2 border-b last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <Avatar
                      alt={request.employee}
                      fallback={request.employee}
                      size="sm"
                    />
                    <div>
                      <p className="font-medium text-sm">{request.employee}</p>
                      <p className="text-xs text-muted-foreground">{request.dates}</p>
                    </div>
                  </div>
                  <Badge variant="outline">{request.type}</Badge>
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-4">
              <Button size="sm" className="flex-1">Approve All</Button>
              <Button size="sm" variant="outline" className="flex-1">View All</Button>
            </div>
          </CardContent>
        </Card>

        {/* Expiring Certifications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-500" />
              Expiring Certifications
            </CardTitle>
            <CardDescription>Renewals needed soon</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {expiringCerts.map((cert) => (
                <div
                  key={cert.id}
                  className="flex items-center justify-between py-2 border-b last:border-0"
                >
                  <div>
                    <p className="font-medium text-sm">{cert.employee}</p>
                    <p className="text-xs text-muted-foreground">{cert.cert}</p>
                  </div>
                  <Badge 
                    variant={cert.priority === 'high' ? 'destructive' : 'outline'}
                    className={cert.priority === 'medium' ? 'border-amber-500 text-amber-600' : ''}
                  >
                    {cert.expires}
                  </Badge>
                </div>
              ))}
            </div>
            <Button variant="outline" className="w-full mt-4" asChild>
              <Link href="/training/matrix">
                <FileText className="h-4 w-4 mr-2" />
                View Training Matrix
              </Link>
            </Button>
          </CardContent>
        </Card>

        {/* Department Headcount */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Headcount by Department
            </CardTitle>
            <CardDescription>Employee distribution</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {departmentHeadcount.map((dept) => (
                <div key={dept.name} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{dept.name}</span>
                    <span className="text-muted-foreground">{dept.count}</span>
                  </div>
                  <Progress value={dept.percentage} className="h-2" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
