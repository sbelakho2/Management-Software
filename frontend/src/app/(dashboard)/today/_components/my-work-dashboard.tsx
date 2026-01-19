'use client';

import * as React from 'react';
import Link from 'next/link';
import { useI18n } from '@/contexts/i18n-context';
import { useProjectManagementStore } from '@/stores/project-management-store';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { CheckCircle2, Circle, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

export function MyWorkDashboard() {
  const { t } = useI18n();
  const { myWork, fetchMyWork, isLoading } = useProjectManagementStore();

  React.useEffect(() => {
    fetchMyWork();
  }, [fetchMyWork]);

  // Guard against undefined myWork during hydration
  const stories = myWork?.stories ?? [];
  const issues = myWork?.issues ?? [];

  if (isLoading && stories.length === 0 && issues.length === 0) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const hasWork = stories.length > 0 || issues.length > 0;

  if (!hasWork) {
    return (
      <div className="text-center py-12 industrial-panel bg-rams-panel/20 border-dashed">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-rams-module border border-rams-line mb-4">
          <CheckCircle2 className="h-8 w-8 text-muted-foreground/20" />
        </div>
        <p className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-muted-foreground/40">{t('pages.today.myWork.strategicClarity')}</p>
        <p className="text-[9px] text-muted-foreground/30 mt-1 uppercase tracking-[0.2em]">{t('pages.today.myWork.noAssignments')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {stories.length > 0 && (
        <section className="space-y-4">
          <h3 className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 flex items-center gap-3 px-1">
            <div className="h-1.5 w-1.5 bg-rams-orange" />
            {t('pages.today.myWork.strategicUserStories')}
          </h3>
          <div className="grid gap-1">
            {stories.slice(0, 5).map(story => (
              <Link key={story.id} href={`/project-management/${story.project_id}?tab=backlog&story=${story.id}`} className="block group">
                <div className="flex items-center justify-between p-4 bg-rams-module border border-rams-line hover:border-rams-orange/40 transition-none">
                  <div className="flex items-center gap-4 min-w-0">
                    <span className="text-[9px] font-mono font-bold text-rams-orange bg-rams-orange/5 px-2 py-1 border border-rams-orange/20 shrink-0">US-{story.ref}</span>
                    <span className="text-[11px] font-black uppercase tracking-tight truncate text-foreground/80 group-hover:text-rams-orange transition-none">{story.subject}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <Badge variant="secondary" size="sm">{story.status.toUpperCase().replace('_', ' ')}</Badge>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {issues.length > 0 && (
        <section className="space-y-4">
          <h3 className="text-[9px] font-black uppercase tracking-[0.25em] text-rams-red/50 flex items-center gap-3 px-1">
            <div className="h-1.5 w-1.5 bg-rams-red" />
            {t('pages.today.myWork.criticalAnomalies')}
          </h3>
          <div className="grid gap-1">
            {issues.slice(0, 5).map(issue => (
              <Link key={issue.id} href={`/project-management/${issue.project_id}?tab=issues&issue=${issue.id}`} className="block group">
                <div className="flex items-center justify-between p-4 bg-rams-red/5 border border-rams-red/10 hover:border-rams-red/30 transition-none">
                  <div className="flex items-center gap-4 min-w-0">
                    <span className="text-[9px] font-mono font-bold text-rams-red bg-rams-red/5 px-2 py-1 border border-rams-red/20 shrink-0">IS-{issue.ref}</span>
                    <span className="text-[11px] font-black uppercase tracking-tight truncate text-foreground/80 group-hover:text-rams-red transition-none">{issue.subject}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <Badge variant="destructive" size="sm">{issue.severity.toUpperCase()}</Badge>
                    <ArrowRight className="h-3.5 w-3.5 text-rams-red/20 group-hover:text-rams-red group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
