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
import { useTrainingStore } from '@/stores/training';

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

const recordStatusConfig: Record<string, { label: string; variant: BadgeProps['variant']; icon: typeof CheckCircle }> = {
  enrolled: { label: 'Enrolled', variant: 'secondary', icon: Clock },
  in_progress: { label: 'In Progress', variant: 'warning', icon: RefreshCw },
  completed: { label: 'Completed', variant: 'success', icon: CheckCircle },
  expired: { label: 'Expired', variant: 'danger', icon: AlertTriangle },
  failed: { label: 'Failed', variant: 'danger', icon: AlertTriangle },
};

const formatConfig: Record<string, { label: string; color: string }> = {
  online: { label: 'Online', color: 'bg-primary/10 text-primary' },
  classroom: { label: 'Classroom', color: 'bg-success/10 text-success' },
  hands_on: { label: 'Hands-On', color: 'bg-warning/10 text-warning' },
  blended: { label: 'Blended', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' },
};

function TrainingStats() {
  const { skills, trainings, records } = useTrainingStore();
  
  const expiringCount = records.filter(r => {
    // In a real app, UserSkill model might have expires_at. 
    // Records in store represent enrollments/completions.
    // For now we'll simulate based on store data if available.
    return false; 
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
              <p className="text-2xl font-bold">{skills.length}</p>
              <p className="text-sm text-muted-foreground">Active Skills</p>
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
              <p className="text-2xl font-bold">{trainings.length}</p>
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
              <p className="text-2xl font-bold">{records.filter(r => r.status === 'in_progress').length}</p>
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
  const { skills, isLoading } = useTrainingStore();
  const [search, setSearch] = React.useState('');
  const [categoryFilter, setCategoryFilter] = React.useState('all');

  const categories = [...new Set(skills.map(c => c.skill_category))];

  const filtered = skills.filter(skill => {
    if (search && !skill.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (categoryFilter !== 'all' && skill.skill_category !== categoryFilter) return false;
    return true;
  });

  if (isLoading && skills.length === 0) {
    return <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map(i => <Card key={i} className="h-40 animate-pulse bg-muted" />)}
    </div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search skills..."
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
        {filtered.map((skill) => (
          <Card 
            key={skill.id} 
            className="hover:border-primary/50 cursor-pointer transition-colors"
            onClick={() => router.push(`/training/certifications/${skill.id}`)}
          >
            <CardContent className="pt-4">
              <div className="flex items-start justify-between mb-2">
                <Badge variant="outline">{skill.skill_category}</Badge>
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
              <h3 className="font-semibold mb-1">{skill.name}</h3>
              <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{skill.description}</p>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  Valid {skill.recertification_interval_days / 30} months
                </div>
                {skill.is_safety_critical && <Badge variant="destructive" size="sm">Safety</Badge>}
              </div>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && !isLoading && (
          <div className="col-span-full py-12 text-center text-muted-foreground">
            No skills found
          </div>
        )}
      </div>
    </div>
  );
}

function ProgramsTab() {
  const router = useRouter();
  const { trainings, isLoading } = useTrainingStore();
  const [search, setSearch] = React.useState('');
  const [formatFilter, setFormatFilter] = React.useState('all');

  const filtered = trainings.filter(program => {
    if (search && !program.title.toLowerCase().includes(search.toLowerCase())) return false;
    if (formatFilter !== 'all' && program.training_type !== formatFilter) return false;
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
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="INTERNAL">Internal</SelectItem>
            <SelectItem value="EXTERNAL">External</SelectItem>
            <SelectItem value="ON_THE_JOB">On the Job</SelectItem>
            <SelectItem value="E_LEARNING">E-Learning</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-3 font-medium text-sm">Program</th>
              <th className="text-left p-3 font-medium text-sm">Type</th>
              <th className="text-left p-3 font-medium text-sm">Dates</th>
              <th className="text-center p-3 font-medium text-sm">Enrolled</th>
              <th className="p-3 w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((program) => {
              return (
                <tr 
                  key={program.id} 
                  className="hover:bg-muted/50 cursor-pointer"
                  onClick={() => router.push(`/training/programs/${program.id}`)}
                >
                  <td className="p-3">
                    <p className="font-medium">{program.title}</p>
                    <p className="text-sm text-muted-foreground line-clamp-1">{program.description}</p>
                  </td>
                  <td className="p-3">
                    <Badge variant="outline">{program.training_type}</Badge>
                  </td>
                  <td className="p-3 text-sm">
                    {formatDate(program.start_date)}
                  </td>
                  <td className="p-3 text-center">
                    <span className="font-medium">{program.enrolled_count}</span>
                    {program.capacity && <span className="text-muted-foreground text-xs ml-1">/ {program.capacity}</span>}
                  </td>
                  <td className="p-3">
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && !isLoading && (
              <tr>
                <td colSpan={5} className="p-8 text-center text-muted-foreground">No programs found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RecordsTab() {
  const { records, isLoading } = useTrainingStore();
  const [search, setSearch] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState('all');

  const filtered = records.filter(record => {
    if (search && !record.user_name.toLowerCase().includes(search.toLowerCase()) && 
        !record.training_title.toLowerCase().includes(search.toLowerCase())) return false;
    if (statusFilter !== 'all' && record.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by employee or training..."
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
              <th className="text-left p-3 font-medium text-sm">Training</th>
              <th className="text-left p-3 font-medium text-sm">Status</th>
              <th className="text-left p-3 font-medium text-sm">Enrolled</th>
              <th className="text-left p-3 font-medium text-sm">Completed</th>
              <th className="text-center p-3 font-medium text-sm">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((record) => {
              const statusCfg = recordStatusConfig[record.status] || { label: record.status, variant: 'secondary', icon: Clock };
              const StatusIcon = statusCfg.icon;

              return (
                <tr key={record.id} className={cn('hover:bg-muted/50')}>
                  <td className="p-3">
                    <div className="flex items-center gap-3">
                      <Avatar size="sm">
                        <AvatarFallback>{getInitials(record.user_name)}</AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="font-medium">{record.user_name}</p>
                        <p className="text-xs text-muted-foreground">{record.user_id.split('-')[0]}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-3">
                    <p className="text-sm">{record.training_title}</p>
                  </td>
                  <td className="p-3">
                    <Badge variant={statusCfg.variant} size="sm" className="gap-1">
                      <StatusIcon className="h-3 w-3" />
                      {statusCfg.label}
                    </Badge>
                  </td>
                  <td className="p-3 text-sm">
                    {formatDate(record.enrolled_at)}
                  </td>
                  <td className="p-3 text-sm">
                    {record.completed_at ? formatDate(record.completed_at) : '—'}
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
            {filtered.length === 0 && !isLoading && (
              <tr>
                <td colSpan={6} className="p-8 text-center text-muted-foreground">No records found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TrainingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { fetchSkills, fetchTrainings, fetchRecords } = useTrainingStore();
  
  const [activeTab, setActiveTab] = React.useState<TabType>(() => {
    const tab = searchParams.get('tab') as TabType | null;
    return tab && ['certifications', 'programs', 'records'].includes(tab) ? tab : 'certifications';
  });

  React.useEffect(() => {
    fetchSkills();
    fetchTrainings();
    fetchRecords();
  }, []);

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
