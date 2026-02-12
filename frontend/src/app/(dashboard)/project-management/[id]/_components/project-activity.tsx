'use client';

import * as React from 'react';
import { useProjectManagementStore, type ProjectActivity } from '@/stores/project-management-store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { formatDistanceToNow } from 'date-fns';
import { 
  PlusCircle, 
  MessageSquare, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  Settings, 
  ArrowRightCircle,
  Trash2,
  Edit3
} from 'lucide-react';
import { useI18n } from '@/contexts/i18n-context';

interface ProjectActivityTimelineProps {
  projectId: string;
}

const getActivityIcon = (type: string) => {
  if (type.includes('create')) return <PlusCircle className="h-4 w-4 text-green-500" />;
  if (type.includes('comment')) return <MessageSquare className="h-4 w-4 text-blue-500" />;
  if (type.includes('delete')) return <Trash2 className="h-4 w-4 text-red-500" />;
  if (type.includes('update')) return <Edit3 className="h-4 w-4 text-amber-500" />;
  if (type.includes('close')) return <CheckCircle2 className="h-4 w-4 text-purple-500" />;
  if (type.includes('wiki')) return <FileText className="h-4 w-4 text-sky-500" />;
  return <ArrowRightCircle className="h-4 w-4 text-muted-foreground" />;
};

export function ProjectActivityTimeline({ projectId }: ProjectActivityTimelineProps) {
  const { activities, fetchActivities, isLoading } = useProjectManagementStore();
  const { t } = useI18n();

  React.useEffect(() => {
    fetchActivities(projectId);
  }, [projectId, fetchActivities]);

  if (isLoading && activities.length === 0) {
    return <div className="p-8 text-center text-muted-foreground">{t('pages.projectManagement.activity.loading')}</div>;
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-lg">{t('pages.projectManagement.activity.title')}</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[600px] pr-4">
          <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
            {activities.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">{t('pages.projectManagement.activity.noRecentActivity')}</div>
            ) : (
              activities.map((activity) => (
                <div key={activity.id} className="relative flex items-start gap-4 ml-2">
                  <div className="absolute left-0 mt-1 flex h-6 w-6 items-center justify-center rounded-full bg-background border shadow-sm z-10">
                    {getActivityIcon(activity.activity_type)}
                  </div>
                  <div className="flex-1 ml-8 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium leading-none">
                        {activity.summary}
                      </p>
                      <time className="text-[10px] text-muted-foreground whitespace-nowrap">
                        {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                      </time>
                    </div>
                    {activity.details && (
                      <div className="text-xs text-muted-foreground mt-1 rounded-md bg-muted/30 p-2">
                        {/* Summary of changes if available */}
                        {Object.entries(activity.details).slice(0, 3).map(([key, val]) => (
                          <div key={key} className="flex gap-1">
                            <span className="font-semibold uppercase text-[9px]">{key}:</span>
                            <span className="truncate max-w-[200px]">{String(val)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className="text-[9px] h-4 px-1 uppercase tracking-tighter">
                        {activity.entity_type.replace('_', ' ')}
                      </Badge>
                      {activity.entity_ref && (
                        <span className="text-[9px] text-muted-foreground font-mono">
                          #{activity.entity_ref}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
