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
  const router = useRouter();
  const [search, setSearch] = React.useState('');

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Skills Matrix</h1>
            <p className="text-muted-foreground">Visualize and manage team competency levels</p>
          </div>
        </div>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Export Matrix
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search employees..."
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <Select defaultValue="all">
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Department" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Departments</SelectItem>
                  <SelectItem value="ops">Operations</SelectItem>
                  <SelectItem value="quality">Quality</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon">
                <Filter className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Competency Grid</CardTitle>
            <div className="flex items-center gap-4 text-xs">
              {Object.entries(levelConfig).map(([level, cfg]) => (
                <div key={level} className="flex items-center gap-1">
                  <div className={cn("w-3 h-3 rounded", cfg.color.split(' ')[0])} />
                  <span className="text-muted-foreground">{cfg.label}</span>
                </div>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-muted/50 border-b">
                  <th className="p-4 text-left font-medium text-sm sticky left-0 bg-muted/50 z-10 min-w-[200px]">Employee</th>
                  {skillNames.map(skill => (
                    <th key={skill} className="p-4 text-center font-medium text-sm min-w-[120px]">{skill}</th>
                  ))}
                  <th className="p-4 text-center font-medium text-sm">Avg. Score</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {employees.map(emp => {
                  const scores = Object.values(emp.skills);
                  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
                  
                  return (
                    <tr key={emp.id} className="hover:bg-muted/30">
                      <td className="p-4 sticky left-0 bg-background z-10 border-r">
                        <div className="flex items-center gap-3">
                          <Avatar size="sm">
                            <AvatarFallback>{getInitials(emp.name)}</AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium text-sm">{emp.name}</p>
                            <p className="text-xs text-muted-foreground">{emp.role}</p>
                          </div>
                        </div>
                      </td>
                      {skillNames.map(skill => {
                        const score = emp.skills[skill as keyof typeof emp.skills] || 0;
                        const cfg = levelConfig[score as keyof typeof levelConfig];
                        return (
                          <td key={skill} className="p-4 text-center">
                            <div className={cn(
                              "inline-flex items-center justify-center w-10 h-10 rounded-lg font-bold transition-transform hover:scale-110 cursor-default",
                              cfg.color
                            )}>
                              {score}
                            </div>
                          </td>
                        );
                      })}
                      <td className="p-4 text-center">
                        <div className="flex flex-col items-center gap-1">
                          <span className="font-bold">{avg.toFixed(1)}</span>
                          <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-primary" 
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
