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
  MapPin,
  Laptop
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

const recordStatusConfig: Record<string, { label: string; className: string; icon: typeof CheckCircle }> = {
  enrolled: { label: 'Enrolled', className: 'bg-rams-steel/10 text-rams-steel border-rams-steel/30', icon: Clock },
  in_progress: { label: 'In Progress', className: 'bg-rams-orange/10 text-rams-orange border-rams-orange/30', icon: RefreshCw },
  completed: { label: 'Completed', className: 'bg-rams-green/10 text-rams-green border-rams-green/30', icon: CheckCircle },
  expired: { label: 'Expired', className: 'bg-rams-red/10 text-rams-red border-rams-red/30', icon: AlertTriangle },
  failed: { label: 'Failed', className: 'bg-rams-red/10 text-rams-red border-rams-red/30', icon: AlertTriangle },
};

function TrainingStats() {
  const { t } = useI18n();
  const { skills, trainings, records } = useTrainingStore();
  
  const expiringCount = records.filter(r => {
    if (!r.expiresDate) return false;
    const expiry = new Date(r.expiresDate);
    const now = new Date();
    const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;
    return expiry.getTime() > now.getTime() && expiry.getTime() - now.getTime() <= thirtyDaysMs;
  }).length;

  return (
    <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
      <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('training.stats.activeSkillNodes') || 'Active Skill Nodes'}</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{skills.length}</div>
        <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">{t('pages.hr.systemActive') || 'System Active'}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('training.stats.operationalProtocols') || 'Operational Protocols'}</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{trainings.length}</div>
        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.hr.availableModules') || 'Available Modules'}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('training.stats.synchronizationPulse') || 'Synchronization Pulse'}</p>
        <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{records.filter(r => r.status === 'in_progress').length}</div>
        <p className="text-[9px] font-mono font-bold text-rams-orange uppercase tracking-widest mt-2">{t('pages.hr.activeSessions') || 'Active Sessions'}</p>
      </div>
      <div className="bg-rams-module p-6 border-b md:border-b-0 border-rams-line group hover:bg-rams-panel transition-none cursor-help">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('training.stats.thresholdAlerts') || 'Threshold Alerts'}</p>
        <div className={cn('text-3xl font-mono font-bold tracking-tight tabular-nums', expiringCount > 0 ? 'text-rams-red' : 'text-foreground/90')}>
          {expiringCount}
        </div>
        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('pages.hr.expiringSoon') || 'Expiring Soon'}</p>
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
      {[1, 2, 3].map(i => <div key={i} className="h-40 animate-pulse bg-rams-panel border border-rams-line" />)}
    </div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder={t('pages.training.certifications.searchPlaceholder') || 'Search skills...'}
            className="pl-9 h-9 bg-rams-module border-rams-line rounded-rams-sm text-xs font-mono focus-visible:ring-rams-orange"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-40 h-9 bg-rams-module border-rams-line rounded-rams-sm text-xs font-mono uppercase tracking-wide">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent className="bg-rams-module border-rams-line">
            <SelectItem value="all" className="text-xs uppercase font-bold">{t('common.allCategories') || 'All Categories'}</SelectItem>
            {categories.map(cat => (
              <SelectItem key={cat} value={cat} className="text-xs uppercase font-mono">{cat}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((skill) => (
          <div 
            key={skill.id} 
            className="group relative rounded-rams-sm border border-rams-line bg-rams-module hover:bg-rams-panel transition-colors p-4 cursor-pointer"
            onClick={() => router.push(`/training/certifications/${skill.id}`)}
          >
            <div className="flex items-start justify-between mb-3">
              <Badge variant="outline" className="rounded-none bg-transparent border-rams-line text-[9px] font-black uppercase tracking-widest text-muted-foreground">
                {skill.skill_category}
              </Badge>
              <DropdownMenu>
                <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                  <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-foreground">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48 bg-rams-module border-rams-line rounded-rams-sm">
                  <DropdownMenuItem className="text-xs uppercase font-bold tracking-wider cursor-pointer">{t('common.edit') || 'Edit'}</DropdownMenuItem>
                  <DropdownMenuItem className="text-xs uppercase font-bold tracking-wider cursor-pointer">{t('pages.training.certifications.viewCertifiedEmployees') || 'View Certified Personnel'}</DropdownMenuItem>
                  <DropdownMenuSeparator className="bg-rams-line" />
                  <DropdownMenuItem className="text-xs uppercase font-bold tracking-wider text-rams-red focus:text-rams-red cursor-pointer">{t('common.archive') || 'Archive Protocol'}</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            
            <h3 className="font-sans font-black text-sm uppercase tracking-tight mb-2 group-hover:text-rams-orange transition-colors">{skill.name}</h3>
            <p className="text-[10px] text-muted-foreground font-mono mb-4 line-clamp-2 h-8">{skill.description}</p>
            
            <div className="pt-3 border-t border-rams-line flex items-center justify-between text-[9px] font-mono text-muted-foreground uppercase tracking-wider">
              <div className="flex items-center gap-1.5">
                <Calendar className="h-3 w-3 opacity-50" />
                <span>{t('pages.training.certifications.validMonths') || 'VALID'} {skill.recertification_interval_days / 30} MO</span>
              </div>
              {skill.is_safety_critical && (
                <Badge variant="destructive" className="rounded-none h-4 px-1 text-[8px] font-black bg-rams-red/10 text-rams-red border border-rams-red/30">
                  {t('pages.training.certifications.safety') || 'CRITICAL'}
                </Badge>
              )}
            </div>
          </div>
        ))}
        {filtered.length === 0 && !isLoading && (
          <div className="col-span-full py-16 text-center border border-dashed border-rams-line rounded-rams-sm bg-rams-module">
            <Award className="h-10 w-10 mx-auto text-muted-foreground/30 mb-4" />
            <p className="text-xs font-black uppercase tracking-widest text-muted-foreground">No certifications found</p>
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
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder={t('pages.training.programs.searchPlaceholder') || 'Search programs...'}
            className="pl-9 h-9 bg-rams-module border-rams-line rounded-rams-sm text-xs font-mono focus-visible:ring-rams-orange"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={formatFilter} onValueChange={setFormatFilter}>
          <SelectTrigger className="w-40 h-9 bg-rams-module border-rams-line rounded-rams-sm text-xs font-mono uppercase tracking-wide">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent className="bg-rams-module border-rams-line">
            <SelectItem value="all" className="text-xs uppercase font-bold">{t('pages.training.programs.allTypes') || 'All Types'}</SelectItem>
            <SelectItem value="INTERNAL" className="text-xs uppercase font-mono">Internal</SelectItem>
            <SelectItem value="EXTERNAL" className="text-xs uppercase font-mono">External</SelectItem>
            <SelectItem value="ON_THE_JOB" className="text-xs uppercase font-mono">On the Job</SelectItem>
            <SelectItem value="E_LEARNING" className="text-xs uppercase font-mono">E-Learning</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="border border-rams-line rounded-rams-sm overflow-hidden bg-rams-module">
        <div className="grid grid-cols-[2fr,1fr,1fr,1fr,40px] gap-4 p-3 bg-rams-panel/50 border-b border-rams-line text-[10px] uppercase font-black tracking-widest text-muted-foreground">
          <div>{t('pages.training.programs.table.program') || 'Program ID'}</div>
          <div>{t('common.type') || 'Type'}</div>
          <div>{t('pages.training.programs.table.dates') || 'Timeline'}</div>
          <div className="text-center">{t('common.enrolled') || 'Enrollment'}</div>
          <div></div>
        </div>
        <div className="divide-y divide-rams-line">
          {filtered.map((program) => {
            return (
              <div 
                key={program.id} 
                className="grid grid-cols-[2fr,1fr,1fr,1fr,40px] gap-4 p-3 items-center hover:bg-rams-panel transition-colors cursor-pointer group"
                onClick={() => router.push(`/training/programs/${program.id}`)}
              >
                <div>
                  <p className="font-sans font-black text-xs uppercase tracking-tight truncate group-hover:text-rams-orange">{program.title}</p>
                  <p className="text-[10px] text-muted-foreground font-mono truncate">{program.description}</p>
                </div>
                <div>
                  <Badge variant="outline" className="rounded-none bg-rams-steel/5 border-rams-steel/30 text-rams-steel text-[8px] font-black uppercase tracking-widest px-1.5 h-5">
                    {program.training_type.replace(/_/g, ' ')}
                  </Badge>
                </div>
                <div className="text-[10px] font-mono text-muted-foreground uppercase">
                  {formatDate(program.start_date)}
                </div>
                <div className="text-center">
                  <span className="font-mono font-bold text-sm tabular-nums">{program.enrolled_count}</span>
                  {program.capacity && <span className="text-muted-foreground text-[10px] font-mono ml-1">/ {program.capacity}</span>}
                </div>
                <div className="flex justify-end">
                  <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-rams-orange" />
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && !isLoading && (
            <div className="p-12 text-center text-muted-foreground">
              <BookOpen className="h-8 w-8 mx-auto opacity-30 mb-3" />
              <p className="text-xs font-mono uppercase tracking-wider">{t('pages.training.programs.noProgramsFound') || 'No programs found'}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RecordsTab() {
  const { t } = useI18n();
  const router = useRouter(); // Added router
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
            placeholder={t('pages.training.records.searchPlaceholder') || 'Search personnel or activity...'}
            className="pl-9 h-9 bg-rams-module border-rams-line rounded-rams-sm text-xs font-mono focus-visible:ring-rams-orange"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40 h-9 bg-rams-module border-rams-line rounded-rams-sm text-xs font-mono uppercase tracking-wide">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent className="bg-rams-module border-rams-line">
            <SelectItem value="all" className="text-xs uppercase font-bold">{t('common.allStatus') || 'All Status'}</SelectItem>
            {Object.entries(recordStatusConfig).map(([key, cfg]) => (
              <SelectItem key={key} value={key} className="text-xs uppercase font-mono">{cfg.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" className="h-9 rounded-rams-sm border-rams-line text-[10px] font-black uppercase tracking-wider">
          <Download className="mr-2 h-3.5 w-3.5" />
          {t('common.export') || 'Export Data'}
        </Button>
      </div>

      <div className="border border-rams-line rounded-rams-sm overflow-hidden bg-rams-module">
        <div className="grid grid-cols-[1.5fr,1.5fr,1fr,1fr,1fr,1fr] gap-4 p-3 bg-rams-panel/50 border-b border-rams-line text-[10px] uppercase font-black tracking-widest text-muted-foreground">
          <div>{t('pages.training.records.table.employee') || 'Personnel'}</div>
          <div>{t('pages.training.records.table.training') || 'Module'}</div>
          <div>{t('common.status') || 'Status'}</div>
          <div>{t('common.enrolled') || 'Start Date'}</div>
          <div>{t('common.completed') || 'End Date'}</div>
          <div className="text-center">{t('pages.training.records.table.score') || 'Score'}</div>
        </div>
        <div className="divide-y divide-rams-line">
          {filtered.map((record) => {
            const statusCfg = recordStatusConfig[record.status] || { label: record.status, className: 'bg-rams-panel border-rams-line', icon: Clock };
            const StatusIcon = statusCfg.icon;

            return (
              <div 
                key={record.id} 
                className="grid grid-cols-[1.5fr,1.5fr,1fr,1fr,1fr,1fr] gap-4 p-3 items-center hover:bg-rams-panel transition-colors text-[11px] cursor-pointer group"
                onClick={() => router.push(`/training/certifications/${record.id}`)}
              >
                <div className="flex items-center gap-3">
                  <Avatar className="h-8 w-8 rounded-rams-sm border border-rams-line">
                    <AvatarFallback className="bg-rams-panel text-[10px] font-black">
                      {getInitials(record.user_name)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="overflow-hidden">
                    <p className="font-sans font-bold uppercase tracking-tight truncate">{record.user_name}</p>
                    <p className="text-[9px] font-mono text-muted-foreground truncate">{record.user_id.split('-')[0]}</p>
                  </div>
                </div>
                <div>
                  <p className="font-mono text-xs truncate" title={record.training_title}>{record.training_title}</p>
                </div>
                <div>
                  <Badge variant="outline" className={cn("rounded-none border px-1.5 h-5 text-[8px] font-black uppercase tracking-widest gap-1", statusCfg.className)}>
                    <StatusIcon className="h-3 w-3" />
                    {statusCfg.label}
                  </Badge>
                </div>
                <div className="font-mono text-muted-foreground uppercase">
                  {formatDate(record.enrolled_at)}
                </div>
                <div className="font-mono text-muted-foreground uppercase">
                  {record.completed_at ? formatDate(record.completed_at) : '—'}
                </div>
                <div className="text-center font-mono font-bold">
                  {record.score !== undefined ? (
                    <span className={cn(
                      record.score >= 80 ? 'text-rams-green' : record.score >= 60 ? 'text-rams-orange' : 'text-rams-red'
                    )}>
                      {record.score}%
                    </span>
                  ) : '—'}
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && !isLoading && (
            <div className="p-12 text-center text-muted-foreground">
              <FileText className="h-8 w-8 mx-auto opacity-30 mb-3" />
              <p className="text-xs font-mono uppercase tracking-wider">{t('pages.training.records.noRecordsFound') || 'No records found'}</p>
            </div>
          )}
        </div>
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
          <Button variant="outline" size="sm" className="rounded-rams-sm border-rams-line" onClick={() => router.push('/training/matrix')}>
            <TrendingUp className="mr-2 h-3.5 w-3.5" />
            {t('training.skillsMatrix') || 'Skills Matrix'}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px]">
                <Plus className="mr-2 h-3.5 w-3.5" />
                {t('training.initializeActivity') || 'Initialize Activity'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-rams-module border-rams-line rounded-rams-sm">
              <DropdownMenuItem className="text-xs uppercase font-bold tracking-wider cursor-pointer" onClick={() => router.push('/training/certifications/new')}>
                <Award className="mr-2 h-3 w-3" />
                {t('training.newCertification') || 'New Certification'}
              </DropdownMenuItem>
              <DropdownMenuItem className="text-xs uppercase font-bold tracking-wider cursor-pointer" onClick={() => router.push('/training/programs/new')}>
                <BookOpen className="mr-2 h-3 w-3" />
                {t('training.newTrainingProgram') || 'New Training Program'}
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-rams-line" />
              <DropdownMenuItem className="text-xs uppercase font-bold tracking-wider cursor-pointer" onClick={() => router.push('/training/enroll')}>
                <User className="mr-2 h-3 w-3" />
                {t('training.enrollEmployee') || 'Enroll Employee'}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats */}
      <TrainingStats />

      {/* Main Content (Modular Rack) */}
      <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none bg-transparent">
        <CardHeader className="p-0 border-b border-rams-line bg-rams-panel/20">
          <div className="flex overflow-x-auto scrollbar-hide">
            <button
              className={cn(
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative whitespace-nowrap',
                activeTab === 'certifications'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-line/40'
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
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-l border-rams-line whitespace-nowrap',
                activeTab === 'programs'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-line/40'
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
                'px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] transition-none relative border-l border-rams-line whitespace-nowrap',
                activeTab === 'records'
                  ? 'text-foreground border-b-2 border-rams-orange bg-rams-module'
                  : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-rams-line/40'
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
        <CardContent className="p-6 bg-rams-module border border-t-0 border-rams-line">
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
      <div className="flex h-[50vh] flex-col items-center justify-center space-y-4">
        <div className="h-8 w-8 animate-spin text-rams-orange rounded-full border-2 border-current border-t-transparent" />
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground animate-pulse">
          Loading Training Modules...
        </p>
      </div>
    }>
      <TrainingPageContent />
    </Suspense>
  );
}
