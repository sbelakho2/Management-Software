'use client';

import * as React from 'react';
import { Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Plus,
  Search,
  Filter,
  GraduationCap,
  Award,
  Clock,
  AlertTriangle,
  CheckCircle,
  Calendar,
  Users,
  BookOpen,
  FileText,
  ChevronRight,
  MoreHorizontal,
  Download,
  RefreshCw,
  TrendingUp,
  User,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge, BadgeProps } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn, formatDate, getInitials } from '@/lib/utils';

type TabType = 'certifications' | 'programs' | 'records';

interface Certification {
  id: string;
  name: string;
  description: string;
  category: string;
  validityPeriod: number; // months
  requiredFor: string[];
  enrolledCount: number;
  certifiedCount: number;
}

interface TrainingProgram {
  id: string;
  name: string;
  description: string;
  duration: string;
  format: 'online' | 'classroom' | 'hands_on' | 'blended';
  certificationId?: string;
  certificationName?: string;
  enrolledCount: number;
  completionRate: number;
}

interface TrainingRecord {
  id: string;
  employeeId: string;
  employeeName: string;
  programId: string;
  programName: string;
  certificationName?: string;
  status: 'enrolled' | 'in_progress' | 'completed' | 'expired' | 'failed';
  enrolledDate: string;
  completedDate?: string;
  expiresDate?: string;
  score?: number;
}

const mockCertifications: Certification[] = [
  { id: '1', name: 'ISO 9001 Internal Auditor', description: 'Qualified to conduct internal quality audits', category: 'Quality', validityPeriod: 36, requiredFor: ['Quality Manager', 'Quality Engineer'], enrolledCount: 8, certifiedCount: 5 },
  { id: '2', name: 'AS9100 Awareness', description: 'Aerospace quality management system fundamentals', category: 'Quality', validityPeriod: 24, requiredFor: ['All Production', 'Quality'], enrolledCount: 45, certifiedCount: 42 },
  { id: '3', name: 'CNC Machine Operation Level 1', description: 'Basic CNC programming and operation', category: 'Technical', validityPeriod: 12, requiredFor: ['CNC Operator'], enrolledCount: 15, certifiedCount: 12 },
  { id: '4', name: 'Forklift Operator', description: 'Licensed forklift operation certification', category: 'Safety', validityPeriod: 36, requiredFor: ['Warehouse', 'Shipping'], enrolledCount: 10, certifiedCount: 10 },
  { id: '5', name: 'First Aid & CPR', description: 'Emergency first aid and CPR certification', category: 'Safety', validityPeriod: 24, requiredFor: ['Safety Team'], enrolledCount: 12, certifiedCount: 11 },
];

const mockPrograms: TrainingProgram[] = [
  { id: '1', name: 'ISO 9001 Internal Auditor Training', description: 'Comprehensive auditor training course', duration: '3 days', format: 'classroom', certificationId: '1', certificationName: 'ISO 9001 Internal Auditor', enrolledCount: 8, completionRate: 62 },
  { id: '2', name: 'New Employee Orientation', description: 'Company policies, procedures, and culture', duration: '4 hours', format: 'blended', enrolledCount: 5, completionRate: 80 },
  { id: '3', name: 'CNC Programming Fundamentals', description: 'G-code basics and machine setup', duration: '2 weeks', format: 'hands_on', certificationId: '3', certificationName: 'CNC Machine Operation Level 1', enrolledCount: 15, completionRate: 80 },
  { id: '4', name: 'Safety Awareness Training', description: 'Workplace safety and hazard recognition', duration: '2 hours', format: 'online', enrolledCount: 50, completionRate: 96 },
  { id: '5', name: 'Quality Documentation', description: 'Proper completion of quality records', duration: '1 hour', format: 'online', enrolledCount: 45, completionRate: 89 },
];

const mockRecords: TrainingRecord[] = [
  { id: '1', employeeId: 'E001', employeeName: 'John Doe', programId: '1', programName: 'ISO 9001 Internal Auditor Training', certificationName: 'ISO 9001 Internal Auditor', status: 'completed', enrolledDate: '2023-10-01', completedDate: '2023-10-03', expiresDate: '2026-10-03', score: 92 },
  { id: '2', employeeId: 'E002', employeeName: 'Sarah Chen', programId: '3', programName: 'CNC Programming Fundamentals', certificationName: 'CNC Machine Operation Level 1', status: 'in_progress', enrolledDate: '2024-01-08' },
  { id: '3', employeeId: 'E003', employeeName: 'Maria Garcia', programId: '2', programName: 'New Employee Orientation', status: 'completed', enrolledDate: '2024-01-02', completedDate: '2024-01-02' },
  { id: '4', employeeId: 'E004', employeeName: 'David Lee', programId: '4', programName: 'Safety Awareness Training', status: 'expired', enrolledDate: '2022-01-15', completedDate: '2022-01-15', expiresDate: '2024-01-15' },
  { id: '5', employeeId: 'E005', employeeName: 'Emily Rodriguez', programId: '1', programName: 'ISO 9001 Internal Auditor Training', certificationName: 'ISO 9001 Internal Auditor', status: 'enrolled', enrolledDate: '2024-01-10' },
  { id: '6', employeeId: 'E001', employeeName: 'John Doe', programId: '5', programName: 'Quality Documentation', status: 'completed', enrolledDate: '2023-11-01', completedDate: '2023-11-01', score: 100 },
];

const recordStatusConfig: Record<TrainingRecord['status'], { label: string; variant: BadgeProps['variant']; icon: typeof CheckCircle }> = {
  enrolled: { label: 'Enrolled', variant: 'secondary', icon: Clock },
  in_progress: { label: 'In Progress', variant: 'warning', icon: RefreshCw },
  completed: { label: 'Completed', variant: 'success', icon: CheckCircle },
  expired: { label: 'Expired', variant: 'danger', icon: AlertTriangle },
  failed: { label: 'Failed', variant: 'danger', icon: AlertTriangle },
};

const formatConfig: Record<TrainingProgram['format'], { label: string; color: string }> = {
  online: { label: 'Online', color: 'bg-primary/10 text-primary' },
  classroom: { label: 'Classroom', color: 'bg-success/10 text-success' },
  hands_on: { label: 'Hands-On', color: 'bg-warning/10 text-warning' },
  blended: { label: 'Blended', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' },
};

function TrainingStats() {
  const expiringCount = mockRecords.filter(r => {
    if (!r.expiresDate) return false;
    const expDate = new Date(r.expiresDate);
    const daysUntil = Math.ceil((expDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    return daysUntil <= 30 && daysUntil > 0;
  }).length;

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Award className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">{mockCertifications.length}</p>
              <p className="text-sm text-muted-foreground">Active Certifications</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-success/10 rounded-lg">
              <GraduationCap className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold">{mockPrograms.length}</p>
              <p className="text-sm text-muted-foreground">Training Programs</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-warning/10 rounded-lg">
              <Clock className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold">{mockRecords.filter(r => r.status === 'in_progress').length}</p>
              <p className="text-sm text-muted-foreground">In Progress</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className={cn(expiringCount > 0 && 'border-danger')}>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-lg', expiringCount > 0 ? 'bg-danger/10' : 'bg-muted')}>
              <AlertTriangle className={cn('h-5 w-5', expiringCount > 0 ? 'text-danger' : 'text-muted-foreground')} />
            </div>
            <div>
              <p className="text-2xl font-bold">{expiringCount}</p>
              <p className="text-sm text-muted-foreground">Expiring (30 days)</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function CertificationsTab() {
  const router = useRouter();
  const [search, setSearch] = React.useState('');
  const [categoryFilter, setCategoryFilter] = React.useState('all');

  const categories = [...new Set(mockCertifications.map(c => c.category))];

  const filtered = mockCertifications.filter(cert => {
    if (search && !cert.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (categoryFilter !== 'all' && cert.category !== categoryFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search certifications..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map(cat => (
              <SelectItem key={cat} value={cat}>{cat}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((cert) => (
          <Card 
            key={cert.id} 
            className="hover:border-primary/50 cursor-pointer transition-colors"
            onClick={() => router.push(`/training/certifications/${cert.id}`)}
          >
            <CardContent className="pt-4">
              <div className="flex items-start justify-between mb-2">
                <Badge variant="outline">{cert.category}</Badge>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                    <Button variant="ghost" size="icon-sm">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem>Edit</DropdownMenuItem>
                    <DropdownMenuItem>View Certified Employees</DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem className="text-danger">Archive</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <h3 className="font-semibold mb-1">{cert.name}</h3>
              <p className="text-sm text-muted-foreground mb-4">{cert.description}</p>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  Valid {cert.validityPeriod} months
                </div>
                <div className="flex items-center gap-1">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{cert.certifiedCount}</span>
                  <span className="text-muted-foreground">/ {cert.enrolledCount}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ProgramsTab() {
  const router = useRouter();
  const [search, setSearch] = React.useState('');
  const [formatFilter, setFormatFilter] = React.useState('all');

  const filtered = mockPrograms.filter(program => {
    if (search && !program.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (formatFilter !== 'all' && program.format !== formatFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search programs..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={formatFilter} onValueChange={setFormatFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Format" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Formats</SelectItem>
            {Object.entries(formatConfig).map(([key, cfg]) => (
              <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-3 font-medium text-sm">Program</th>
              <th className="text-left p-3 font-medium text-sm">Format</th>
              <th className="text-left p-3 font-medium text-sm">Duration</th>
              <th className="text-left p-3 font-medium text-sm">Certification</th>
              <th className="text-center p-3 font-medium text-sm">Enrolled</th>
              <th className="text-center p-3 font-medium text-sm">Completion</th>
              <th className="p-3 w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((program) => {
              const fmtCfg = formatConfig[program.format];
              return (
                <tr 
                  key={program.id} 
                  className="hover:bg-muted/50 cursor-pointer"
                  onClick={() => router.push(`/training/programs/${program.id}`)}
                >
                  <td className="p-3">
                    <p className="font-medium">{program.name}</p>
                    <p className="text-sm text-muted-foreground">{program.description}</p>
                  </td>
                  <td className="p-3">
                    <span className={cn('text-xs px-2 py-1 rounded', fmtCfg.color)}>
                      {fmtCfg.label}
                    </span>
                  </td>
                  <td className="p-3 text-sm">{program.duration}</td>
                  <td className="p-3">
                    {program.certificationName ? (
                      <Badge variant="outline" size="sm">{program.certificationName}</Badge>
                    ) : (
                      <span className="text-muted-foreground text-sm">—</span>
                    )}
                  </td>
                  <td className="p-3 text-center">
                    <span className="font-medium">{program.enrolledCount}</span>
                  </td>
                  <td className="p-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                        <div 
                          className={cn(
                            'h-full rounded-full',
                            program.completionRate >= 80 ? 'bg-success' : 
                            program.completionRate >= 50 ? 'bg-warning' : 'bg-danger'
                          )}
                          style={{ width: `${program.completionRate}%` }}
                        />
                      </div>
                      <span className="text-sm">{program.completionRate}%</span>
                    </div>
                  </td>
                  <td className="p-3">
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RecordsTab() {
  const [search, setSearch] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState('all');

  const filtered = mockRecords.filter(record => {
    if (search && !record.employeeName.toLowerCase().includes(search.toLowerCase()) && 
        !record.programName.toLowerCase().includes(search.toLowerCase())) return false;
    if (statusFilter !== 'all' && record.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by employee or program..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            {Object.entries(recordStatusConfig).map(([key, cfg]) => (
              <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Export
        </Button>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-3 font-medium text-sm">Employee</th>
              <th className="text-left p-3 font-medium text-sm">Program</th>
              <th className="text-left p-3 font-medium text-sm">Status</th>
              <th className="text-left p-3 font-medium text-sm">Enrolled</th>
              <th className="text-left p-3 font-medium text-sm">Completed</th>
              <th className="text-left p-3 font-medium text-sm">Expires</th>
              <th className="text-center p-3 font-medium text-sm">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((record) => {
              const statusCfg = recordStatusConfig[record.status];
              const StatusIcon = statusCfg.icon;
              const isExpiringSoon = record.expiresDate && (() => {
                const days = Math.ceil((new Date(record.expiresDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
                return days <= 30 && days > 0;
              })();

              return (
                <tr key={record.id} className={cn('hover:bg-muted/50', record.status === 'expired' && 'bg-danger/5')}>
                  <td className="p-3">
                    <div className="flex items-center gap-3">
                      <Avatar size="sm">
                        <AvatarFallback>{getInitials(record.employeeName)}</AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="font-medium">{record.employeeName}</p>
                        <p className="text-xs text-muted-foreground">{record.employeeId}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-3">
                    <p className="text-sm">{record.programName}</p>
                    {record.certificationName && (
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <Award className="h-3 w-3" />
                        {record.certificationName}
                      </p>
                    )}
                  </td>
                  <td className="p-3">
                    <Badge variant={statusCfg.variant} size="sm" className="gap-1">
                      <StatusIcon className="h-3 w-3" />
                      {statusCfg.label}
                    </Badge>
                  </td>
                  <td className="p-3 text-sm">
                    {formatDate(new Date(record.enrolledDate), { month: 'short', day: 'numeric', year: 'numeric' })}
                  </td>
                  <td className="p-3 text-sm">
                    {record.completedDate 
                      ? formatDate(new Date(record.completedDate), { month: 'short', day: 'numeric', year: 'numeric' })
                      : '—'}
                  </td>
                  <td className="p-3 text-sm">
                    {record.expiresDate ? (
                      <span className={cn(isExpiringSoon && 'text-warning font-medium', record.status === 'expired' && 'text-danger')}>
                        {formatDate(new Date(record.expiresDate), { month: 'short', day: 'numeric', year: 'numeric' })}
                        {isExpiringSoon && <AlertTriangle className="inline h-3 w-3 ml-1" />}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="p-3 text-center">
                    {record.score !== undefined ? (
                      <span className={cn(
                        'font-medium',
                        record.score >= 80 ? 'text-success' : record.score >= 60 ? 'text-warning' : 'text-danger'
                      )}>
                        {record.score}%
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TrainingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = React.useState<TabType>(() => {
    const tab = searchParams.get('tab') as TabType | null;
    return tab && ['certifications', 'programs', 'records'].includes(tab) ? tab : 'certifications';
  });

  React.useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('tab', activeTab);
    window.history.replaceState({}, '', url.toString());
  }, [activeTab]);

  return (
    <div className="space-y-6" data-testid="training-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Training & Certifications</h1>
          <p className="text-muted-foreground">Manage employee training and track certifications</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => router.push('/training/matrix')}>
            <TrendingUp className="mr-2 h-4 w-4" />
            Skills Matrix
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => router.push('/training/certifications/new')}>
                <Award className="mr-2 h-4 w-4" />
                New Certification
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push('/training/programs/new')}>
                <BookOpen className="mr-2 h-4 w-4" />
                New Training Program
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push('/training/enroll')}>
                <User className="mr-2 h-4 w-4" />
                Enroll Employee
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats */}
      <TrainingStats />

      {/* Tabs */}
      <Card>
        <CardHeader className="pb-0 border-b">
          <div className="flex gap-4">
            <button
              className={cn(
                'pb-3 px-1 text-sm font-medium border-b-2 transition-colors',
                activeTab === 'certifications'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              onClick={() => setActiveTab('certifications')}
            >
              <Award className="inline h-4 w-4 mr-2" />
              Certifications
            </button>
            <button
              className={cn(
                'pb-3 px-1 text-sm font-medium border-b-2 transition-colors',
                activeTab === 'programs'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              onClick={() => setActiveTab('programs')}
            >
              <BookOpen className="inline h-4 w-4 mr-2" />
              Programs
            </button>
            <button
              className={cn(
                'pb-3 px-1 text-sm font-medium border-b-2 transition-colors',
                activeTab === 'records'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              onClick={() => setActiveTab('records')}
            >
              <FileText className="inline h-4 w-4 mr-2" />
              Records
            </button>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {activeTab === 'certifications' && <CertificationsTab />}
          {activeTab === 'programs' && <ProgramsTab />}
          {activeTab === 'records' && <RecordsTab />}
        </CardContent>
      </Card>
    </div>
  );
}

export default function TrainingPage() {
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
      <TrainingPageContent />
    </Suspense>
  );
}
