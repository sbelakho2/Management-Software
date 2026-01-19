import * as React from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
  /** ID for linking to error message via aria-describedby */
  errorId?: string;
  resize?: 'none' | 'vertical' | 'horizontal' | 'both';
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, errorId, resize = 'vertical', 'aria-describedby': ariaDescribedBy, ...props }, ref) => {
    const resizeClass = {
      none: 'resize-none',
      vertical: 'resize-y',
      horizontal: 'resize-x',
      both: 'resize',
    }[resize];

    // Combine error ID with any existing aria-describedby
    const describedBy = [ariaDescribedBy, error && errorId].filter(Boolean).join(' ') || undefined;

    return (
      <textarea
        className={cn(
          'flex min-h-[80px] w-full rounded-rams-sm border border-rams-line bg-rams-panel px-4 py-2 text-[11px] font-bold tracking-wider transition-none uppercase',
          'placeholder:text-muted-foreground/30',
          'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-rams-orange focus-visible:border-rams-orange',
          'disabled:cursor-not-allowed disabled:opacity-40',
          error && 'border-rams-red focus-visible:ring-rams-red focus-visible:border-rams-red',
          resizeClass,
          className
        )}
        ref={ref}
        aria-invalid={error || undefined}
        aria-describedby={describedBy}
        {...props}
      />
    );
  }
);
Textarea.displayName = 'Textarea';

export { Textarea };
