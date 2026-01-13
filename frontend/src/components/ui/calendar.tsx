'use client';

import * as React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  addMonths,
  subMonths,
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  addDays,
  isSameMonth,
  isSameDay,
  isWithinInterval,
} from 'date-fns';

export type DateRange = {
  from: Date | undefined;
  to?: Date | undefined;
};

interface CalendarProps {
  mode?: 'single' | 'range';
  selected?: Date | DateRange;
  onSelect?: (date: Date | DateRange | undefined) => void;
  defaultMonth?: Date;
  numberOfMonths?: number;
  initialFocus?: boolean;
  className?: string;
}

export function Calendar({
  mode = 'single',
  selected,
  onSelect,
  defaultMonth,
  numberOfMonths = 1,
  className,
}: CalendarProps) {
  const [currentMonth, setCurrentMonth] = React.useState(defaultMonth || new Date());
  const [rangeStart, setRangeStart] = React.useState<Date | undefined>(
    mode === 'range' && selected && 'from' in selected ? selected.from : undefined
  );

  const handlePrevMonth = () => setCurrentMonth(subMonths(currentMonth, 1));
  const handleNextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));

  const handleDateClick = (day: Date) => {
    if (mode === 'single') {
      onSelect?.(day);
    } else if (mode === 'range') {
      if (!rangeStart) {
        setRangeStart(day);
        onSelect?.({ from: day, to: undefined });
      } else {
        if (day < rangeStart) {
          onSelect?.({ from: day, to: rangeStart });
        } else {
          onSelect?.({ from: rangeStart, to: day });
        }
        setRangeStart(undefined);
      }
    }
  };

  const isSelected = (day: Date): boolean => {
    if (mode === 'single' && selected && selected instanceof Date) {
      return isSameDay(day, selected);
    }
    if (mode === 'range' && selected && 'from' in selected) {
      if (selected.from && selected.to) {
        return isWithinInterval(day, { start: selected.from, end: selected.to });
      }
      if (selected.from) {
        return isSameDay(day, selected.from);
      }
    }
    return false;
  };

  const isRangeStart = (day: Date): boolean => {
    if (mode === 'range' && selected && 'from' in selected && selected.from) {
      return isSameDay(day, selected.from);
    }
    return false;
  };

  const isRangeEnd = (day: Date): boolean => {
    if (mode === 'range' && selected && 'from' in selected && selected.to) {
      return isSameDay(day, selected.to);
    }
    return false;
  };

  const renderMonth = (monthDate: Date) => {
    const monthStart = startOfMonth(monthDate);
    const monthEnd = endOfMonth(monthStart);
    const startDate = startOfWeek(monthStart);
    const endDate = endOfWeek(monthEnd);

    const rows: React.ReactNode[] = [];
    let days: React.ReactNode[] = [];
    let day = startDate;

    while (day <= endDate) {
      for (let i = 0; i < 7; i++) {
        const cloneDay = day;
        const isCurrentMonth = isSameMonth(day, monthStart);
        const selected = isSelected(day);
        const rangeStart = isRangeStart(day);
        const rangeEnd = isRangeEnd(day);

        days.push(
          <button
            key={day.toString()}
            type="button"
            onClick={() => handleDateClick(cloneDay)}
            disabled={!isCurrentMonth}
            className={cn(
              'h-9 w-9 text-center text-sm p-0 font-normal rounded-md',
              !isCurrentMonth && 'text-muted-foreground opacity-50',
              isCurrentMonth && 'hover:bg-accent hover:text-accent-foreground',
              selected && 'bg-primary text-primary-foreground',
              rangeStart && 'rounded-l-md',
              rangeEnd && 'rounded-r-md',
              selected && !rangeStart && !rangeEnd && mode === 'range' && 'rounded-none bg-primary/50'
            )}
          >
            {format(day, 'd')}
          </button>
        );
        day = addDays(day, 1);
      }
      rows.push(
        <div key={day.toString()} className="flex w-full">
          {days}
        </div>
      );
      days = [];
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between px-1">
          <h2 className="font-semibold text-sm">{format(monthDate, 'MMMM yyyy')}</h2>
        </div>
        <div className="flex w-full">
          {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((dayName) => (
            <div key={dayName} className="h-9 w-9 text-center text-xs text-muted-foreground font-medium">
              {dayName}
            </div>
          ))}
        </div>
        <div className="space-y-1">{rows}</div>
      </div>
    );
  };

  const months: React.ReactNode[] = [];
  for (let i = 0; i < numberOfMonths; i++) {
    months.push(
      <div key={i} className="space-y-4">
        {renderMonth(addMonths(currentMonth, i))}
      </div>
    );
  }

  return (
    <div className={cn('p-3', className)}>
      <div className="flex items-center justify-between mb-4">
        <Button variant="outline" size="icon" className="h-7 w-7" onClick={handlePrevMonth}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="icon" className="h-7 w-7" onClick={handleNextMonth}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
      <div className={cn('flex gap-4', numberOfMonths > 1 && 'flex-row')}>
        {months}
      </div>
    </div>
  );
}
