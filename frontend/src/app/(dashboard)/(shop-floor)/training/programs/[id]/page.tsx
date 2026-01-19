'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ChevronLeft, Clock, BookOpen, Users, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useI18n } from '@/contexts/i18n-context';

export default function ProgramDetailsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useParams();

  // Mock data for display
  const program = {
    id: params.id,
    title: 'Advanced Machining Center Operation',
    description: 'Comprehensive training on high-speed CNC centers, including setup, programming, and maintenance.',
    category: 'Technical Skills',
    level: 'Advanced',
    duration: '40 hours',
    instructor: 'Robert Smith',
    enrolledCount: 12,
    completionRate: 85,
    modules: [
      { id: 'm1', title: 'Unit 1: Safety & Pre-checks', duration: '4h', status: 'completed' },
      { id: 'm2', title: 'Unit 2: Setup & Calibration', duration: '8h', status: 'completed' },
      { id: 'm3', title: 'Unit 3: Advanced Programming', duration: '12h', status: 'in_progress' },
      { id: 'm4', title: 'Unit 4: Quality & Inspection', duration: '8h', status: 'todo' },
      { id: 'm5', title: 'Unit 5: Maintenance Basics', duration: '8h', status: 'todo' },
    ]
  };

  return (
    <div className="space-y-8 page-fade-in pb-12">
      <div className="flex items-center gap-4 border-b border-rams-line pb-8">
        <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{program.title}</h1>
            <Badge variant="outline" className="rounded-none text-[8px] font-black uppercase tracking-widest h-4 px-1 border-rams-line">{program.level}</Badge>
          </div>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">{program.category} | STATION: ACADEMY-PROG-01</p>
        </div>
      </div>

      <div className="grid gap-8 md:grid-cols-3">
        <div className="md:col-span-2 space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('training.programs.detail.programDescription') || 'Program Description'}</CardTitle>
            </CardHeader>
            <CardContent className="p-8">
              <p className="text-xs font-medium text-foreground/70 uppercase leading-relaxed">{program.description}</p>
            </CardContent>
          </Card>

          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('training.programs.detail.curriculum') || 'Curriculum'}</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-rams-line/30">
                {program.modules.map((module, idx) => (
                  <div key={module.id} className="flex items-center justify-between p-5 hover:bg-rams-panel transition-none group">
                    <div className="flex items-center gap-4">
                      <div className="flex h-8 w-8 items-center justify-center bg-rams-panel border border-rams-line text-[10px] font-mono font-bold">
                        {idx + 1}
                      </div>
                      <div>
                        <p className="text-xs font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{module.title}</p>
                        <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-0.5">{module.duration}</p>
                      </div>
                    </div>
                    {module.status === 'completed' ? (
                      <CheckCircle className="h-5 w-5 text-rams-green" />
                    ) : module.status === 'in_progress' ? (
                      <Badge variant="warning" size="sm" className="rounded-none text-[8px] font-black h-4">{t('common.inProgress') || 'In Progress'}</Badge>
                    ) : (
                      <Badge variant="secondary" size="sm" className="rounded-none text-[8px] font-black h-4">{t('common.scheduled') || 'Scheduled'}</Badge>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('training.programs.detail.details') || 'Details'}</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 border-b border-rams-line pb-4">
                <span className="flex items-center gap-3">
                  <Clock className="h-3.5 w-3.5 opacity-40" /> {t('common.duration') || 'Duration'}
                </span>
                <span className="font-mono font-bold text-foreground/80">{program.duration}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 border-b border-rams-line pb-4">
                <span className="flex items-center gap-3">
                  <Users className="h-3.5 w-3.5 opacity-40" /> {t('common.instructor') || 'Instructor'}
                </span>
                <span className="font-bold text-foreground/80">{program.instructor}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <span className="flex items-center gap-3">
                  <BookOpen className="h-3.5 w-3.5 opacity-40" /> {t('common.enrolled') || 'Enrolled'}
                </span>
                <span className="font-bold text-foreground/80">{program.enrolledCount} {t('common.activeUsers') || 'active users'}</span>
              </div>
              <div className="pt-4">
                <Button className="w-full rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 transition-none">{t('training.programs.detail.continueLearning') || 'Continue Learning'}</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
