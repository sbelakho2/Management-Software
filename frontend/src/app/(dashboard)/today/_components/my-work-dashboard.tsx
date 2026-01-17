'use client';

import * as React from 'react';
import Link from 'next/link';
import { useProjectManagementStore } from '@/stores/project-management-store';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { CheckCircle2, Circle, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

export function MyWorkDashboard() {
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
      <div className="text-center py-12 bg-muted/5 rounded-[2rem] border border-dashed border-border/20">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-muted/10 mb-4">
          <CheckCircle2 className="h-8 w-8 text-muted-foreground/20" />
        </div>
        <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground/40">Strategic Clarity</p>
        <p className="text-[10px] text-muted-foreground/30 mt-1 uppercase tracking-[0.2em]">No assignments identified</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {stories.length > 0 && (
        <section className="space-y-4">
          <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50 flex items-center gap-2 px-1">
            <div className="h-1.5 w-1.5 rounded-full bg-primary/40" />
            Strategic User Stories
          </h3>
          <div className="grid gap-3">
            {stories.slice(0, 5).map(story => (
              <Link key={story.id} href={`/project-management/${story.project_id}?tab=backlog&story=${story.id}`} className="block group">
                <div className="flex items-center justify-between p-4 rounded-2xl bg-muted/20 border border-border/5 hover:bg-primary/5 hover:border-primary/10 transition-all duration-300">
                  <div className="flex items-center gap-4 min-w-0">
                    <span className="text-[9px] font-mono font-bold text-primary/40 bg-primary/5 px-2 py-1 rounded-md shrink-0">US-{story.ref}</span>
                    <span className="text-sm font-bold tracking-tight truncate text-foreground/80 group-hover:text-primary transition-colors">{story.subject}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <Badge variant="secondary" className="text-[9px] font-bold uppercase tracking-wider bg-background/50">{story.status.replace('_', ' ')}</Badge>
                    <ArrowRight className="h-4 w-4 text-muted-foreground/30 group-hover:text-primary group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {issues.length > 0 && (
        <section className="space-y-4">
          <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-danger/50 flex items-center gap-2 px-1">
            <div className="h-1.5 w-1.5 rounded-full bg-danger/40" />
            Critical Anomalies
          </h3>
          <div className="grid gap-3">
            {issues.slice(0, 5).map(issue => (
              <Link key={issue.id} href={`/project-management/${issue.project_id}?tab=issues&issue=${issue.id}`} className="block group">
                <div className="flex items-center justify-between p-4 rounded-2xl bg-danger/5 border border-danger/5 hover:bg-danger/10 transition-all duration-300">
                  <div className="flex items-center gap-4 min-w-0">
                    <span className="text-[9px] font-mono font-bold text-danger/40 bg-danger/5 px-2 py-1 rounded-md shrink-0">IS-{issue.ref}</span>
                    <span className="text-sm font-bold tracking-tight truncate text-foreground/80 group-hover:text-danger transition-colors">{issue.subject}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <Badge variant="outline" className="text-[9px] font-bold uppercase tracking-wider border-danger/20 text-danger/60">{issue.severity}</Badge>
                    <ArrowRight className="h-4 w-4 text-danger/20 group-hover:text-danger group-hover:translate-x-1 transition-all" />
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
