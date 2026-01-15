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
          'flex h-11 w-full rounded-2xl border border-border/40 bg-background/50 px-4 py-2 text-sm shadow-inner-soft transition-all placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:border-primary/50 disabled:cursor-not-allowed disabled:opacity-50 hover:border-primary/20 backdrop-blur-sm',
          error && 'border-destructive focus-visible:ring-destructive hover:border-destructive/50',
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
