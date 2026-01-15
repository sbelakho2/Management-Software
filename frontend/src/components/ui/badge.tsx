import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-xl border font-bold transition-all focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 select-none',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-primary-foreground shadow-glow hover:scale-105 active:scale-95',
        secondary:
          'border-border/40 bg-secondary/80 text-secondary-foreground backdrop-blur-sm hover:bg-secondary hover:border-primary/20',
        destructive:
          'border-transparent bg-destructive text-destructive-foreground shadow-sm hover:opacity-90',
        outline: 'text-foreground border-primary/20 bg-background/50 hover:bg-primary/5 hover:border-primary/40',
        ghost: 'border-transparent bg-transparent text-foreground hover:bg-primary/10 hover:text-primary',
        primary:
          'border-transparent bg-primary text-primary-foreground shadow-glow hover:opacity-90',
        success:
          'border-transparent bg-success/10 text-success ring-1 ring-inset ring-success/20 dark:bg-success/20',
        warning:
          'border-transparent bg-warning/10 text-warning ring-1 ring-inset ring-warning/20 dark:bg-warning/20',
        danger:
          'border-transparent bg-danger/10 text-danger ring-1 ring-inset ring-danger/20 dark:bg-danger/20',
        // Status badges - Premium refined
        pending:
          'border-transparent bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-400',
        active:
          'border-transparent bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-900/30 dark:text-emerald-400',
        inactive:
          'border-transparent bg-slate-50 text-slate-700 ring-1 ring-inset ring-slate-600/20 dark:bg-slate-900/30 dark:text-slate-400',
        completed:
          'border-transparent bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-600/20 dark:bg-sky-900/30 dark:text-sky-400',
        failed:
          'border-transparent bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20 dark:bg-rose-900/30 dark:text-rose-400',
      },
      size: {
        default: 'px-3 py-1 text-[10px] uppercase tracking-wider',
        sm: 'px-2 py-0.5 text-[9px] uppercase tracking-widest',
        lg: 'px-4 py-1.5 text-xs font-black uppercase tracking-[0.15em]',
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
