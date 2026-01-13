import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border font-bold transition-all focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-primary-foreground shadow-sm hover:opacity-90',
        secondary:
          'border-transparent bg-secondary/80 text-secondary-foreground backdrop-blur-sm hover:bg-secondary',
        destructive:
          'border-transparent bg-destructive text-destructive-foreground shadow-sm hover:opacity-90',
        outline: 'text-foreground border-border/50 hover:bg-accent hover:text-accent-foreground',
        ghost: 'border-transparent bg-transparent text-foreground hover:bg-accent hover:text-accent-foreground',
        primary:
          'border-transparent bg-primary text-primary-foreground shadow-sm hover:opacity-90',
        success:
          'border-transparent bg-success/15 text-success dark:bg-success/20',
        warning:
          'border-transparent bg-warning/15 text-warning dark:bg-warning/20',
        danger:
          'border-transparent bg-danger/15 text-danger dark:bg-danger/20',
        // Status badges - Premium refined
        pending:
          'border-transparent bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-500',
        active:
          'border-transparent bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-500',
        inactive:
          'border-transparent bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-500',
        completed:
          'border-transparent bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-500',
        failed:
          'border-transparent bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-500',
      },
      size: {
        default: 'px-2.5 py-0.5 text-xs',
        sm: 'px-2 py-0.5 text-[10px]',
        lg: 'px-3 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <div 
      data-testid="badge"
      className={cn(badgeVariants({ variant, size }), className)} 
      {...props} 
    />
  );
}

export { Badge, badgeVariants };
