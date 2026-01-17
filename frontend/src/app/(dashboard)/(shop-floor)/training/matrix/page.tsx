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
  0: { label: 'None', color: 'bg-slate-100 text-slate-400' },
  1: { label: 'Novice', color: 'bg-red-100 text-red-700' },
  2: { label: 'Intermediate', color: 'bg-orange-100 text-orange-700' },
  3: { label: 'Advanced', color: 'bg-blue-100 text-blue-700' },
  4: { label: 'Expert', color: 'bg-green-100 text-green-700' },
};

export default function TrainingMatrixPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [search, setSearch] = React.useState('');

  return (
    <div className="space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">Skills Architecture</h1>
            <p className="text-muted-foreground font-medium text-sm">Visualize and manage organizational competency nodes</p>
          </div>
        </div>
        <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
          <Download className="mr-2 h-4 w-4" />
          Export Matrix
        </Button>
      </div>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1 max-w-sm group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40 group-focus-within:text-primary transition-colors" />
              <Input
                placeholder="Search operatives by node identity..."
                className="pl-11 h-12 bg-background/50 border-border/50 rounded-xl"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-3">
              <Select defaultValue="all">
                <SelectTrigger className="w-48 h-12 rounded-xl bg-background/50 border-border/50">
                  <SelectValue placeholder="Department Node" />
                </SelectTrigger>
                <SelectContent className="rounded-2xl shadow-premium">
                  <SelectItem value="all" className="rounded-xl m-1">All Departments</SelectItem>
                  <SelectItem value="ops" className="rounded-xl m-1">Operations</SelectItem>
                  <SelectItem value="quality" className="rounded-xl m-1">Quality</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon" className="h-12 w-12 rounded-xl border-border/50">
                <Filter className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden">
        <CardHeader className="border-b border-border/10 bg-muted/5 p-6">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-heading">Competency Matrix</CardTitle>
            <div className="flex flex-wrap items-center gap-6">
              {Object.entries(levelConfig).map(([level, cfg]) => (
                <div key={level} className="flex items-center gap-2">
                  <div className={cn("w-2.5 h-2.5 rounded-full shadow-sm", cfg.color.split(' ')[0])} />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{cfg.label}</span>
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
                  <th className="p-5 text-left sticky left-0 bg-background/80 backdrop-blur-md z-20 border-r border-border/10 min-w-[240px]">Operative Node</th>
                  {skillNames.map(skill => (
                    <th key={skill} className="p-5 text-center min-w-[140px]">{skill}</th>
                  ))}
                  <th className="p-5 text-center min-w-[140px]">Strategic Avg</th>
                </tr>
              </thead>
              <tbody>
                {employees.map(emp => {
                  const scores = Object.values(emp.skills ?? {});
                  const avg = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
                  
                  return (
                    <tr key={emp.id} className="group hover:bg-primary/5 transition-all duration-300">
                      <td className="p-5 sticky left-0 bg-background/80 backdrop-blur-md z-10 border-r border-border/10 transition-colors group-hover:bg-transparent">
                        <div className="flex items-center gap-4">
                          <Avatar size="sm" className="ring-2 ring-background shadow-sm">
                            <AvatarFallback className="font-heading font-bold bg-muted/30">{getInitials(emp.name)}</AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-heading font-bold text-sm tracking-tight text-foreground/80 group-hover:text-primary transition-colors">{emp.name}</p>
                            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{emp.role}</p>
                          </div>
                        </div>
                      </td>
                      {skillNames.map(skill => {
                        const score = emp.skills[skill as keyof typeof emp.skills] || 0;
                        const cfg = levelConfig[score as keyof typeof levelConfig];
                        return (
                          <td key={skill} className="p-5 text-center">
                            <div className={cn(
                              "inline-flex items-center justify-center w-12 h-12 rounded-2xl font-heading font-bold text-base shadow-inner-soft transition-all duration-500 group-hover:scale-110 cursor-default border border-transparent hover:border-primary/20",
                              cfg.color
                            )}>
                              {score}
                            </div>
                          </td>
                        );
                      })}
                      <td className="p-5 text-center">
                        <div className="flex flex-col items-center gap-2">
                          <span className="font-heading font-bold text-base tracking-tight">{avg.toFixed(1)}</span>
                          <div className="w-20 h-1.5 bg-muted/20 rounded-full overflow-hidden shadow-inner-soft">
                            <div 
                              className="h-full bg-gradient-to-r from-primary to-primary/60 transition-all duration-1000" 
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
