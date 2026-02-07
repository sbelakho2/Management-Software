'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Download,
  Filter,
  Search,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Users,
  Grid,
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn, getInitials } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';
import { useTrainingStore } from '@/stores/training';
import { useHRStore } from '@/stores/hr';
import { EmployeeProfile } from '@/types';

// Proficiency Level Configuration (Sensei-Rams Style)
const levelConfig: Record<number, { label: string; color: string; short: string }> = {
  0: { label: 'None', short: 'N', color: 'bg-rams-panel text-muted-foreground/30 border-rams-line' },
  1: { label: 'Novice', short: '1', color: 'bg-rams-red/5 text-rams-red border-rams-red/20' },
  2: { label: 'Intermediate', short: '2', color: 'bg-rams-orange/5 text-rams-orange border-rams-orange/20' },
  3: { label: 'Advanced', short: '3', color: 'bg-rams-steel/5 text-rams-steel border-rams-steel/20' },
  4: { label: 'Expert', short: '4', color: 'bg-rams-green/5 text-rams-green border-rams-green/20' },
};

export default function TrainingMatrixPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [search, setSearch] = React.useState('');
  const [departmentFilter, setDepartmentFilter] = React.useState<string>('all');
  
  // Data Stores
  const { 
    skills, 
    userSkills, 
    fetchSkills, 
    fetchUserSkills, 
    isLoading: isTrainingLoading 
  } = useTrainingStore();
  
  const { 
    employees, 
    fetchEmployees,
    isLoading: isHRLoading 
  } = useHRStore();

  // Initial Data Fetch
  React.useEffect(() => {
    fetchSkills();
    fetchUserSkills();
    fetchEmployees();
  }, [fetchSkills, fetchUserSkills, fetchEmployees]);

  // Derived State: Matrix Data
  const matrixData = React.useMemo(() => {
    // 1. Create a lookup for UserSkills: userId -> skillId -> level
    const skillMap = new Map<string, Map<string, number>>();
    
    userSkills.forEach(us => {
      // Assuming us.user_id matches employee.user_id or employee.id
      if (!skillMap.has(us.user_id)) {
        skillMap.set(us.user_id, new Map());
      }
      skillMap.get(us.user_id)?.set(us.skill_id, us.proficiency_level);
    });

    // 2. Filter Employees
    const filteredEmployees = employees.filter(emp => {
      const matchesSearch = 
        emp.first_name.toLowerCase().includes(search.toLowerCase()) || 
        emp.last_name.toLowerCase().includes(search.toLowerCase()) ||
        (emp.job_title && emp.job_title.toLowerCase().includes(search.toLowerCase()));
      
      const matchesDept = departmentFilter === 'all' || emp.department === departmentFilter;

      return matchesSearch && matchesDept;
    });

    // 3. Sort Employees (by Department then Name)
    filteredEmployees.sort((a, b) => {
      if (a.department !== b.department) return (a.department || '').localeCompare(b.department || '');
      return `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`);
    });

    return { filteredEmployees, skillMap };
  }, [employees, userSkills, search, departmentFilter]);

  // Get unique departments for filter
  const departments = React.useMemo(() => {
    const rawDepts = employees.map(e => e.department).filter(Boolean) as string[];
    return Array.from(new Set(rawDepts)).sort();
  }, [employees]);

  const isLoading = isTrainingLoading || isHRLoading;

  return (
    <div className="space-y-8 page-fade-in pb-12">
      {/* Header Section */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="icon" 
            className="rounded-rams-sm hover:bg-rams-panel transition-none" 
            onClick={() => router.back()}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('training.matrix.title') || 'Skills Architecture'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <Grid className="h-3 w-3" />
              {t('training.matrix.subtitle') || 'Organizational Competency Grid'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
            <Button 
                variant="outline" 
                size="default" 
                className="rounded-rams-sm border-rams-line h-10 px-6 transition-none font-mono uppercase text-xs tracking-wider"
                onClick={() => { fetchSkills(); fetchUserSkills(); fetchEmployees(); }}
            >
                <RefreshCw className={cn("mr-2 h-3.5 w-3.5", isLoading && "animate-spin")} />
                {t('common.refresh') || 'SYNC'}
            </Button>
            <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none font-mono uppercase text-xs tracking-wider">
                <Download className="mr-2 h-3.5 w-3.5" />
                {t('training.matrix.exportMatrix') || 'EXPORT DATA'}
            </Button>
        </div>
      </div>

      {/* Logic Controls */}
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
        <CardContent className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40" />
              <Input
                placeholder={t('training.matrix.searchPlaceholder') || 'SEARCH NODE IDENTITY / ROLE...'}
                className="pl-9 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider font-mono placeholder:font-sans"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-3">
              <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
                <SelectTrigger className="w-48 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider font-mono">
                  <SelectValue placeholder={t('training.matrix.departmentNode') || 'Department Node'} />
                </SelectTrigger>
                <SelectContent className="rounded-rams-sm border-rams-line bg-rams-module">
                  <SelectItem value="all" className="uppercase text-[10px] font-bold tracking-wider">{t('common.allDepartments') || 'All Sectors'}</SelectItem>
                  {departments.map(dept => (
                    <SelectItem key={dept} value={dept} className="uppercase text-[10px] font-bold tracking-wider">{dept}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="ml-auto hidden xl:flex items-center gap-4 border-l border-rams-line pl-6">
                <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50">Proficiency Index</span>
                {Object.entries(levelConfig).filter(([k]) => k !== '0').map(([level, cfg]) => (
                    <div key={level} className="flex items-center gap-2">
                        <div className={cn("w-2 h-2 rounded-full", cfg.color.split(' ')[0])} />
                        <span className="text-[9px] font-mono uppercase tracking-widest text-muted-foreground">{cfg.label}</span>
                    </div>
                ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Interactive Matrix */}
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
            {isLoading && employees.length === 0 ? (
                <div className="p-12 text-center text-muted-foreground font-mono uppercase tracking-widest text-xs">
                    Initializing Matrix Sequence...
                </div>
            ) : (
                <table className="w-full border-separate border-spacing-0">
                    <thead>
                    <tr>
                        <th className="p-4 text-left sticky left-0 bg-rams-module z-20 border-b border-r border-rams-line min-w-[280px]">
                            <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50">Operative Node</span>
                        </th>
                        {skills.map(skill => (
                        <th key={skill.id} className="p-4 text-center min-w-[120px] border-b border-rams-line group hover:bg-rams-panel/30 transition-colors">
                            <div className="flex flex-col items-center gap-1">
                                <span className="text-[9px] font-black uppercase tracking-widest text-foreground/70">{skill.code}</span>
                                <span className="text-[9px] font-medium uppercase tracking-tight text-muted-foreground/50 line-clamp-1 max-w-[100px]" title={skill.name}>{skill.name}</span>
                            </div>
                        </th>
                        ))}
                    </tr>
                    </thead>
                    <tbody className="bg-rams-panel/5">
                    {matrixData.filteredEmployees.map(emp => {
                        // Use user_id if available, fallback to id if the backend aligns them, but typically userSkills are keyed by user_id
                        const empSkills = matrixData.skillMap.get(emp.user_id || emp.id) || new Map();
                        
                        return (
                        <tr key={emp.id} className="group hover:bg-rams-panel/40 transition-none">
                            <td className="p-4 sticky left-0 bg-rams-module z-10 border-r border-b border-rams-line transition-none group-hover:bg-rams-panel">
                            <div className="flex items-center gap-4">
                                <Avatar className="h-8 w-8 rounded-none border border-rams-line">
                                    <AvatarFallback className="font-mono font-bold text-[10px] bg-rams-panel text-rams-orange">{getInitials(`${emp.first_name} ${emp.last_name}`)}</AvatarFallback>
                                </Avatar>
                                <div>
                                <p className="font-sans font-bold text-xs uppercase tracking-tight text-foreground/90 group-hover:text-rams-orange transition-none">
                                    {emp.first_name} {emp.last_name}
                                </p>
                                <div className="flex items-center gap-2">
                                    <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/50">{emp.job_title || 'Unassigned'}</span>
                                    {emp.department && (
                                        <>
                                            <span className="text-[9px] text-rams-line mx-1">|</span>
                                            <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/50">{emp.department}</span>
                                        </>
                                    )}
                                </div>
                                </div>
                            </div>
                            </td>
                            {skills.map(skill => {
                            const level = empSkills.get(skill.id) || 0;
                            const cfg = levelConfig[level] || levelConfig[0];
                            return (
                                <td key={`${emp.id}-${skill.id}`} className="p-2 text-center border-b border-rams-line/50">
                                <div 
                                    className={cn(
                                        "inline-flex items-center justify-center w-8 h-8 font-mono font-bold text-xs border transition-all duration-200 cursor-default rounded-sm",
                                        cfg.color,
                                        level > 0 ? "hover:scale-110 hover:shadow-lg shadow-rams-black/10" : "opacity-40"
                                    )}
                                    title={`${skill.name}: ${cfg.label}`}
                                >
                                    {level > 0 ? level : '-'}
                                </div>
                                </td>
                            );
                            })}
                        </tr>
                        );
                    })}
                    </tbody>
                </table>
            )}
        </div>
        {!isLoading && matrixData.filteredEmployees.length === 0 && (
            <div className="py-12 flex flex-col items-center justify-center text-center">
                <Users className="h-12 w-12 text-muted-foreground/20 mb-4" />
                <h3 className="text-sm font-bold uppercase tracking-widest text-foreground/50">No Data Points Located</h3>
                <p className="text-xs text-muted-foreground/40 mt-2 font-mono uppercase">Adjust filter parameters to expand search</p>
            </div>
        )}
      </Card>
    </div>
  );
}
