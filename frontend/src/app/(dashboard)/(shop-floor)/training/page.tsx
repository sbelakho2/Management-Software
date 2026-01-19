'use client';

import * as React from 'react';
import { Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
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
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

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
  const { t } = useI18n();
  const { skills, trainings, records } = useTrainingStore();
  
  const expiringCount = records.filter(r => {
    return false; 
  }).length;

  return (
    <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('training.stats.activeSkillNodes') || 'Active Skill Nodes'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{skills.length}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('training.stats.operationalProtocols') || 'Operational Protocols'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{trainings.length}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('training.stats.synchronizationPulse') || 'Synchronization Pulse'}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{records.filter(r => r.status === 'in_progress').length}</p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-line">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-red/60 mb-4">{t('training.stats.thresholdAlerts') || 'Threshold Alerts'}</p>
        <p className={cn('text-3xl font-mono font-bold tracking-tight tabular-nums', expiringCount > 0 ? 'text-rams-red' : 'text-foreground/90')}>
          {expiringCount}
        </p>
      </div>
    </div>
  );
}

function CertificationsTab() {
  const { t } = useI18n();
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
            placeholder={t('pages.training.certifications.searchPlaceholder') || 'Search skills...'}
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
            <SelectItem value="all">{t('common.allCategories') || 'All Categories'}</SelectItem>
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
                    <DropdownMenuItem>{t('common.edit') || 'Edit'}</DropdownMenuItem>
                    <DropdownMenuItem>{t('pages.training.certifications.viewCertifiedEmployees') || 'View Certified Employees'}</DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem className="text-danger">{t('common.archive') || 'Archive'}</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <h3 className="font-semibold mb-1">{skill.name}</h3>
              <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{skill.description}</p>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  {t('pages.training.certifications.validMonths') || 'Valid'} {skill.recertification_interval_days / 30} {t('common.months') || 'months'}
                </div>
                {skill.is_safety_critical && <Badge variant="destructive" size="sm">{t('pages.training.certifications.safety') || 'Safety'}</Badge>}
              </div>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && !isLoading && (
          <div className="col-span-full py-12 text-center text-muted-foreground">
            {t('pages.training.certifications.noSkillsFound') || 'No skills found'}
          </div>
        )}
      </div>
    </div>
  );
}

function ProgramsTab() {
  const { t } = useI18n();
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
            placeholder={t('pages.training.programs.searchPlaceholder') || 'Search programs...'}
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
            <SelectItem value="all">{t('pages.training.programs.allTypes') || 'All Types'}</SelectItem>
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
              <th className="text-left p-3 font-medium text-sm">{t('pages.training.programs.table.program') || 'Program'}</th>
              <th className="text-left p-3 font-medium text-sm">{t('common.type') || 'Type'}</th>
              <th className="text-left p-3 font-medium text-sm">{t('pages.training.programs.table.dates') || 'Dates'}</th>
              <th className="text-center p-3 font-medium text-sm">{t('common.enrolled') || 'Enrolled'}</th>
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
                <td colSpan={5} className="p-8 text-center text-muted-foreground">{t('pages.training.programs.noProgramsFound') || 'No programs found'}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RecordsTab() {
  const { t } = useI18n();
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
            placeholder={t('pages.training.records.searchPlaceholder') || 'Search by employee or training...'}
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
            <SelectItem value="all">{t('common.allStatus') || 'All Status'}</SelectItem>
            {Object.entries(recordStatusConfig).map(([key, cfg]) => (
              <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          {t('common.export') || 'Export'}
        </Button>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-3 font-medium text-sm">{t('pages.training.records.table.employee') || 'Employee'}</th>
              <th className="text-left p-3 font-medium text-sm">{t('pages.training.records.table.training') || 'Training'}</th>
              <th className="text-left p-3 font-medium text-sm">{t('common.status') || 'Status'}</th>
              <th className="text-left p-3 font-medium text-sm">{t('common.enrolled') || 'Enrolled'}</th>
              <th className="text-left p-3 font-medium text-sm">{t('common.completed') || 'Completed'}</th>
              <th className="text-center p-3 font-medium text-sm">{t('pages.training.records.table.score') || 'Score'}</th>
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
                <td colSpan={6} className="p-8 text-center text-muted-foreground">{t('pages.training.records.noRecordsFound') || 'No records found'}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TrainingPageContent() {
  const { t } = useI18n();
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
    <div className="space-y-8 page-fade-in pb-12" data-testid="training-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.training.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.training.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: ACADEMY-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm" onClick={() => router.push('/training/matrix')}>
            <TrendingUp className="mr-2 h-3.5 w-3.5" />
            {t('training.skillsMatrix') || 'Skills Matrix'}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]">
                <Plus className="mr-2 h-3.5 w-3.5" />
                {t('training.initializeActivity') || 'Initialize Activity'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => router.push('/training/certifications/new')}>
                <Award className="mr-2 h-3.5 w-3.5" />
                {t('training.newCertification') || 'New Certification'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push('/training/programs/new')}>
                <BookOpen className="mr-2 h-3.5 w-3.5" />
                {t('training.newTrainingProgram') || 'New Training Program'}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push('/training/enroll')}>
                <User className="mr-2 h-3.5 w-3.5" />
                {t('training.enrollEmployee') || 'Enroll Employee'}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats */}
      <TrainingStats />

      {/* Main Content (Modular Rack) */}
      <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
        <CardHeader className="p-0 border-b border-rams-line bg-rams-panel/20">
          <div className="flex">
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative',
                activeTab === 'certifications'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('certifications')}
            >
              <div className="flex items-center gap-2">
                <Award className="h-3.5 w-3.5" />
                {t('training.tabs.certifications') || 'Certifications'}
              </div>
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-l border-rams-line',
                activeTab === 'programs'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('programs')}
            >
              <div className="flex items-center gap-2">
                <BookOpen className="h-3.5 w-3.5" />
                {t('training.tabs.programs') || 'Programs'}
              </div>
            </button>
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-l border-rams-line',
                activeTab === 'records'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-panel/40'
              )}
              onClick={() => setActiveTab('records')}
            >
              <div className="flex items-center gap-2">
                <FileText className="h-3.5 w-3.5" />
                {t('training.tabs.records') || 'Records'}
              </div>
            </button>
          </div>
        </CardHeader>
        <CardContent className="p-6 bg-rams-module">
          <div className="animate-in fade-in duration-300">
            {activeTab === 'certifications' && <CertificationsTab />}
            {activeTab === 'programs' && <ProgramsTab />}
            {activeTab === 'records' && <RecordsTab />}
          </div>
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
