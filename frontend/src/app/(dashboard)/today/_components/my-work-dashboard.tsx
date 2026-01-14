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

  if (isLoading && myWork.stories.length === 0 && myWork.issues.length === 0) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const hasWork = myWork.stories.length > 0 || myWork.issues.length > 0;

  if (!hasWork) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p className="text-sm">No project assignments for today.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {myWork.stories.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Circle className="h-4 w-4 text-blue-500" /> Assigned User Stories
          </h3>
          <div className="grid gap-2">
            {myWork.stories.slice(0, 5).map(story => (
              <Link key={story.id} href={`/project-management/${story.project_id}?tab=backlog&story=${story.id}`} className="block">
                <div className="flex items-center justify-between p-3 rounded-xl bg-muted/30 border border-border/10 hover:bg-muted/50 transition-colors group">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-[10px] font-mono text-muted-foreground shrink-0">US-{story.ref}</span>
                    <span className="text-sm font-medium truncate">{story.subject}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant="secondary" className="text-[10px] capitalize">{story.status.replace('_', ' ')}</Badge>
                    <ArrowRight className="h-3 w-3 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {myWork.issues.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-500" /> Assigned Issues
          </h3>
          <div className="grid gap-2">
            {myWork.issues.slice(0, 5).map(issue => (
              <Link key={issue.id} href={`/project-management/${issue.project_id}?tab=issues&issue=${issue.id}`} className="block">
                <div className="flex items-center justify-between p-3 rounded-xl bg-muted/30 border border-border/10 hover:bg-muted/50 transition-colors group">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-[10px] font-mono text-muted-foreground shrink-0">IS-{issue.ref}</span>
                    <span className="text-sm font-medium truncate">{issue.subject}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant="outline" className="text-[10px] capitalize">{issue.severity}</Badge>
                    <ArrowRight className="h-3 w-3 text-muted-foreground group-hover:text-primary transition-colors" />
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
