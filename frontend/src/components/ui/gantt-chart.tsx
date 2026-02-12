'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { format, differenceInDays, addDays, startOfDay, endOfDay, isWithinInterval } from 'date-fns';
import { ErrorBoundary } from '@/components/error-boundary';
import { useI18n } from '@/contexts/i18n-context';

export interface GanttTask {
  id: string;
  name: string;
  start: Date;
  end: Date;
  progress: number;
  dependencies?: string[];
  color?: string;
}

export interface GanttChartProps {
  tasks: GanttTask[];
  className?: string;
}

export function GanttChart({ tasks, className }: GanttChartProps) {
  const { t } = useI18n();
  if (!tasks.length) return <div className="text-center py-10 text-muted-foreground border rounded-lg">{t('components.ganttChart.noTasks')}</div>;

  // Calculate timeline range
  const minDate = new Date(Math.min(...tasks.map(t => t.start.getTime())));
  const maxDate = new Date(Math.max(...tasks.map(t => t.end.getTime())));
  
  // Add some padding to the range (e.g., 2 days)
  const startDate = startOfDay(addDays(minDate, -2));
  const endDate = endOfDay(addDays(maxDate, 5));
  
  const totalDays = differenceInDays(endDate, startDate) + 1;
  const dayWidth = 40; // px
  const rowHeight = 40; // px
  const labelWidth = 200; // px
  
  const timelineWidth = totalDays * dayWidth;
  const totalWidth = labelWidth + timelineWidth;
  const totalHeight = (tasks.length + 1) * rowHeight;

  return (
    <ErrorBoundary>
      <div className={cn("overflow-x-auto border rounded-xl bg-background", className)}>
        <div style={{ width: totalWidth, height: totalHeight }} className="relative font-sans text-xs">
        {/* Header - Days */}
        <div className="flex sticky top-0 z-20 bg-muted/50 border-b h-[40px]">
          <div style={{ width: labelWidth }} className="flex-shrink-0 border-r p-2 font-bold flex items-center">{t('components.ganttChart.taskName')}</div>
          <div className="flex">
            {Array.from({ length: totalDays }).map((_, i) => {
              const date = addDays(startDate, i);
              const isWeekend = [0, 6].includes(date.getDay());
              return (
                <div 
                  key={i} 
                  style={{ width: dayWidth }} 
                  className={cn(
                    "flex-shrink-0 border-r p-1 text-center flex flex-col justify-center",
                    isWeekend && "bg-muted/30"
                  )}
                >
                  <span className="opacity-50">{format(date, 'EEE')}</span>
                  <span className="font-bold">{format(date, 'd')}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Rows */}
        {tasks.map((task, rowIndex) => {
          const startOffset = differenceInDays(task.start, startDate) * dayWidth;
          const taskWidth = (differenceInDays(task.end, task.start) + 1) * dayWidth;
          
          return (
            <div key={task.id} className="flex border-b hover:bg-muted/20 transition-colors group" style={{ height: rowHeight }}>
              {/* Task Label */}
              <div style={{ width: labelWidth }} className="flex-shrink-0 border-r p-2 flex items-center truncate font-medium">
                {task.name}
              </div>
              
              {/* Timeline Row */}
              <div className="relative flex-1">
                {/* Vertical day markers */}
                {Array.from({ length: totalDays }).map((_, i) => (
                  <div 
                    key={i} 
                    style={{ left: i * dayWidth, width: dayWidth }} 
                    className="absolute top-0 bottom-0 border-r border-dashed border-muted opacity-20 pointer-events-none" 
                  />
                ))}
                
                {/* Task Bar */}
                <div 
                  className={cn(
                    "absolute top-2 rounded-md shadow-sm border h-6 flex items-center overflow-hidden cursor-pointer hover:brightness-95 transition-all",
                    task.color || "bg-primary text-primary-foreground border-primary/20"
                  )}
                  style={{ left: startOffset, width: taskWidth }}
                  title={`${task.name}: ${task.progress}% complete`}
                >
                  {/* Progress Fill */}
                  <div 
                    className="absolute inset-0 bg-black/20" 
                    style={{ width: `${task.progress}%` }} 
                  />
                  <span className="relative z-10 px-2 truncate font-bold drop-shadow-sm">
                    {task.progress}%
                  </span>
                </div>
                
                {/* Dependency lines (Simplified implementation) */}
                {task.dependencies?.map(depId => {
                  const depTask = tasks.find(t => t.id === depId);
                  if (!depTask) return null;
                  // In a production Gantt, we'd render SVG paths between bars here
                  return null;
                })}
              </div>
            </div>
          );
        })}
        
        {/* Today Marker */}
        {isWithinInterval(new Date(), { start: startDate, end: endDate }) && (
          <div 
            className="absolute top-0 bottom-0 w-px bg-danger z-10 shadow-[0_0_4px_rgba(239,68,68,0.5)]"
            style={{ left: labelWidth + differenceInDays(new Date(), startDate) * dayWidth + (new Date().getHours() / 24) * dayWidth }}
          >
            <div className="absolute top-0 -translate-x-1/2 bg-danger text-white px-1 rounded-sm text-[8px] font-bold">TODAY</div>
          </div>
        )}
        </div>
      </div>
    </ErrorBoundary>
  );
}
