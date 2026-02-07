'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ChevronLeft, Clock, BookOpen, Users, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useI18n } from '@/contexts/i18n-context';

import { useTrainingStore } from '@/stores/training';

export default function ProgramDetailsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useParams();
  const { trainings, fetchTrainings } = useTrainingStore();

  React.useEffect(() => {
    fetchTrainings();
  }, [fetchTrainings]);

  const training = React.useMemo(() => 
    trainings.find(t => t.id === params.id), 
    [trainings, params.id]
  );
  
  if (!training) {
      if (trainings.length === 0) return null; // Or loading state
      // If loaded but not found:
      // return <div>Not Found</div>;
  }
  
  // Modules are not yet in the Training interface, using placeholder if necessary or omitting.
  // For now we will omit curriculum if data is missing.
  
  return (
    <div className="space-y-8 page-fade-in pb-12">
      <div className="flex items-center gap-4 border-b border-rams-line pb-8">
        <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="space-y-1">
          <div className="flex items-center gap-3">
             {/* Fallback to mock title if undefined during load */}
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{training?.title || 'Loading...'}</h1>
            <Badge variant="outline" className="rounded-none text-[8px] font-black uppercase tracking-widest h-4 px-1 border-rams-line">{training?.status || 'Active'}</Badge>
          </div>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">{training?.training_type || 'Training Program'} | ID: {training?.id}</p>
        </div>
      </div>

      <div className="grid gap-8 md:grid-cols-3">
        <div className="md:col-span-2 space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('training.programs.detail.programDescription') || 'Program Description'}</CardTitle>
            </CardHeader>
            <CardContent className="p-8">
              <p className="text-xs font-medium text-foreground/70 uppercase leading-relaxed">{training?.description || 'No description available for this training node.'}</p>
            </CardContent>
          </Card>
          
          {/* Modules section hidden until backend support is confirmed */}
        </div>

        <div className="space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('training.programs.detail.details') || 'Details'}</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 border-b border-rams-line pb-4">
                <span className="flex items-center gap-3">
                  <Clock className="h-3.5 w-3.5 opacity-40" /> {t('common.period') || 'Period'}
                </span>
                <span className="font-mono font-bold text-foreground/80">{training?.start_date ? new Date(training.start_date).toLocaleDateString() : '-'}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 border-b border-rams-line pb-4">
                <span className="flex items-center gap-3">
                  <Users className="h-3.5 w-3.5 opacity-40" /> {t('common.instructor') || 'Instructor'}
                </span>
                <span className="font-bold text-foreground/80">{training?.instructor_id || 'TBD'}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <span className="flex items-center gap-3">
                  <BookOpen className="h-3.5 w-3.5 opacity-40" /> {t('common.enrolled') || 'Enrolled'}
                </span>
                <span className="font-bold text-foreground/80">{training?.enrolled_count || 0} {t('common.activeUsers') || 'users'}</span>
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
