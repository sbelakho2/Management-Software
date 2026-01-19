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
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn, getInitials } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

const employees = [
  { id: 'E001', name: 'John Doe', role: 'Production Lead', skills: { 'CNC': 4, 'AS9100': 4, 'Quality': 3, 'Safety': 4 } },
  { id: 'E002', name: 'Sarah Chen', role: 'CNC Operator', skills: { 'CNC': 3, 'AS9100': 2, 'Quality': 2, 'Safety': 4 } },
  { id: 'E003', name: 'Maria Garcia', role: 'Quality Tech', skills: { 'CNC': 1, 'AS9100': 4, 'Quality': 4, 'Safety': 3 } },
  { id: 'E004', name: 'David Lee', role: 'CNC Operator', skills: { 'CNC': 2, 'AS9100': 2, 'Quality': 1, 'Safety': 2 } },
  { id: 'E005', name: 'Emily Rodriguez', role: 'Production', skills: { 'CNC': 0, 'AS9100': 3, 'Quality': 2, 'Safety': 4 } },
];

const skillNames = ['CNC', 'AS9100', 'Quality', 'Safety'];

const levelConfig = {
  0: { label: 'None', color: 'bg-rams-panel text-muted-foreground/40' },
  1: { label: 'Novice', color: 'bg-rams-red/10 text-rams-red' },
  2: { label: 'Intermediate', color: 'bg-rams-orange/10 text-rams-orange' },
  3: { label: 'Advanced', color: 'bg-rams-steel/10 text-rams-steel' },
  4: { label: 'Expert', color: 'bg-rams-green/10 text-rams-green' },
};

export default function TrainingMatrixPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [search, setSearch] = React.useState('');

  return (
    <div className="space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('training.matrix.title') || 'Skills Architecture'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">{t('training.matrix.subtitle') || 'Visualize and manage organizational competency nodes'}</p>
          </div>
        </div>
        <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none">
          <Download className="mr-2 h-3.5 w-3.5" />
          {t('training.matrix.exportMatrix') || 'Export Matrix'}
        </Button>
      </div>

      <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
        <CardContent className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40" />
              <Input
                placeholder={t('training.matrix.searchPlaceholder') || 'Search operatives by node identity...'}
                className="pl-9 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-3">
              <Select defaultValue="all">
                <SelectTrigger className="w-48 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                  <SelectValue placeholder={t('training.matrix.departmentNode') || 'Department Node'} />
                </SelectTrigger>
                <SelectContent className="rounded-rams-sm border-rams-line">
                  <SelectItem value="all">{t('common.allDepartments') || 'All Departments'}</SelectItem>
                  <SelectItem value="ops">{t('common.operations') || 'Operations'}</SelectItem>
                  <SelectItem value="quality">{t('common.quality') || 'Quality'}</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon" className="h-10 w-10 rounded-rams-sm border-rams-line">
                <Filter className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
        <CardHeader className="border-b border-rams-line bg-rams-panel/20 p-6">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('training.matrix.competencyMatrix') || 'Competency Matrix'}</CardTitle>
            <div className="flex flex-wrap items-center gap-6">
              {Object.entries(levelConfig).map(([level, cfg]) => (
                <div key={level} className="flex items-center gap-2">
                  <div className={cn("w-2 h-2", cfg.color.split(' ')[0])} />
                  <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50">{cfg.label}</span>
                </div>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full border-separate border-spacing-0">
              <thead>
                <tr>
                  <th className="p-5 text-left sticky left-0 bg-rams-module z-20 border-r border-rams-line min-w-[240px] text-[9px] font-black uppercase tracking-widest text-muted-foreground/50">{t('training.matrix.operativeNode') || 'Operative Node'}</th>
                  {skillNames.map(skill => (
                    <th key={skill} className="p-5 text-center min-w-[140px] text-[9px] font-black uppercase tracking-widest text-muted-foreground/50">{skill}</th>
                  ))}
                  <th className="p-5 text-center min-w-[140px] text-[9px] font-black uppercase tracking-widest text-muted-foreground/50">{t('training.matrix.strategicAvg') || 'Strategic Avg'}</th>
                </tr>
              </thead>
              <tbody>
                {employees.map(emp => {
                  const scores = Object.values(emp.skills ?? {});
                  const avg = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
                  
                  return (
                    <tr key={emp.id} className="group hover:bg-rams-panel transition-none">
                      <td className="p-5 sticky left-0 bg-rams-module z-10 border-r border-rams-line transition-none group-hover:bg-rams-panel">
                        <div className="flex items-center gap-4">
                          <Avatar size="sm" className="border border-rams-line">
                            <AvatarFallback className="font-mono font-bold text-[10px] bg-rams-panel">{getInitials(emp.name)}</AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{emp.name}</p>
                            <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">{emp.role}</p>
                          </div>
                        </div>
                      </td>
                      {skillNames.map(skill => {
                        const score = emp.skills[skill as keyof typeof emp.skills] || 0;
                        const cfg = levelConfig[score as keyof typeof levelConfig];
                        return (
                          <td key={skill} className="p-5 text-center">
                            <div className={cn(
                              "inline-flex items-center justify-center w-10 h-10 font-mono font-bold text-sm border border-rams-line transition-none cursor-default",
                              cfg.color
                            )}>
                              {score}
                            </div>
                          </td>
                        );
                      })}
                      <td className="p-5 text-center">
                        <div className="flex flex-col items-center gap-2">
                          <span className="font-mono font-bold text-sm tabular-nums">{avg.toFixed(1)}</span>
                          <div className="w-20 h-1 bg-rams-panel border border-rams-line overflow-hidden">
                            <div 
                              className="h-full bg-rams-orange transition-none" 
                              style={{ width: `${(avg / 4) * 100}%` }} 
                            />
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
