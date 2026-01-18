import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-rams-sm text-[10px] font-black uppercase tracking-widest transition-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-rams-orange focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-40 select-none border border-transparent',
  {
    variants: {
      variant: {
        default:
          'bg-rams-orange text-black border-black/10 hover:bg-rams-orange/90',
        destructive:
          'bg-rams-red text-white hover:bg-rams-red/90',
        outline:
          'border-rams-border bg-rams-panel/50 hover:bg-rams-panel hover:border-rams-border/80 text-foreground/80',
        secondary:
          'bg-rams-module text-foreground/70 border-rams-border hover:bg-rams-panel',
        ghost: 'hover:bg-rams-panel hover:text-foreground text-foreground/60 transition-none',
        link: 'text-rams-orange underline-offset-4 hover:underline',
        success:
          'bg-rams-green text-white hover:bg-rams-green/90',
        warning:
          'bg-rams-orange text-black hover:bg-rams-orange/90',
      },
      size: {
        default: 'h-10 px-6 py-2',
        sm: 'h-8 px-4',
        lg: 'h-12 px-10 text-[11px]',
        xl: 'h-14 px-12 text-[12px]',
        icon: 'h-10 w-10 min-h-[40px] min-w-[40px]',
        'icon-sm': 'h-9 w-9 min-h-[36px] min-w-[36px]',
        'icon-xs': 'h-7 w-7',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        aria-busy={loading}
        {...props}
      >
        {loading ? (
          <>
            <svg
              className="mr-2 h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span className="sr-only">Loading, please wait...</span>
            {children}
          </>
        ) : (
          children
        )}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
