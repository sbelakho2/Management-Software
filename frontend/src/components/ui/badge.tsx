import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-rams-sm border font-mono font-black transition-none focus:outline-none select-none',
  {
    variants: {
      variant: {
        default:
          'border-black/10 bg-rams-orange text-black',
        secondary:
          'border-rams-line bg-rams-panel text-muted-foreground',
        destructive:
          'border-transparent bg-rams-red text-white',
        outline: 'text-foreground border-rams-line bg-transparent',
        ghost: 'border-transparent bg-transparent text-foreground',
        primary:
          'border-black/10 bg-rams-orange text-black',
        success:
          'border-rams-green/20 bg-rams-green/10 text-rams-green',
        warning:
          'border-rams-orange/20 bg-rams-orange/10 text-rams-orange',
        danger:
          'border-rams-red/20 bg-rams-red/10 text-rams-red',
        pending:
          'border-rams-orange/20 bg-rams-orange/10 text-rams-orange',
        active:
          'border-rams-green/20 bg-rams-green/10 text-rams-green',
        inactive:
          'border-rams-line bg-rams-panel/50 text-muted-foreground/60',
        completed:
          'border-rams-steel/20 bg-rams-steel/10 text-rams-steel',
        failed:
          'border-rams-red/20 bg-rams-red/10 text-rams-red',
      },
      size: {
        default: 'px-1.5 py-0 h-4 text-[8px] uppercase tracking-widest',
        sm: 'px-1 py-0 h-3.5 text-[7px] uppercase tracking-tighter',
        lg: 'px-2.5 py-0.5 h-5 text-[10px] uppercase tracking-[0.2em]',
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
