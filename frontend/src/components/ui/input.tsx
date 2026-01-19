import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  /** ID for linking to error message via aria-describedby */
  errorId?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, errorId, 'aria-describedby': ariaDescribedBy, ...props }, ref) => {
    // Combine error ID with any existing aria-describedby
    const describedBy = [ariaDescribedBy, error && errorId].filter(Boolean).join(' ') || undefined;
    
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-rams-sm border border-rams-line bg-rams-panel px-4 py-2 text-[11px] font-bold uppercase tracking-wider transition-none placeholder:text-muted-foreground/30 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-rams-orange focus-visible:border-rams-orange disabled:cursor-not-allowed disabled:opacity-40 hover:border-rams-line/80',
          error && 'border-rams-red focus-visible:ring-rams-red focus-visible:border-rams-red hover:border-rams-red',
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
Input.displayName = 'Input';

export { Input };
