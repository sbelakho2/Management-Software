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
          'flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
          error && 'border-destructive focus-visible:ring-destructive',
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
