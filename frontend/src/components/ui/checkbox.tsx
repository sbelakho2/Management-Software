'use client';

import * as React from 'react';
import * as CheckboxPrimitive from '@radix-ui/react-checkbox';
import { Check, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

const Checkbox = React.forwardRef<
  React.ElementRef<typeof CheckboxPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>
>(({ className, ...props }, ref) => (
  <CheckboxPrimitive.Root
    ref={ref}
    className={cn(
      'peer h-4 w-4 shrink-0 rounded-rams-sm border border-rams-line bg-rams-panel transition-none',
      'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-rams-orange',
      'disabled:cursor-not-allowed disabled:opacity-40',
      'data-[state=checked]:bg-rams-orange data-[state=checked]:text-black data-[state=checked]:border-black/10',
      'data-[state=indeterminate]:bg-rams-orange data-[state=indeterminate]:text-black',
      className
    )}
    {...props}
  >
    <CheckboxPrimitive.Indicator
      className={cn('flex items-center justify-center text-current')}
    >
      {props.checked === 'indeterminate' ? (
        <Minus className="h-3.5 w-3.5 stroke-[3]" />
      ) : (
        <Check className="h-3.5 w-3.5 stroke-[3]" />
      )}
    </CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
));
Checkbox.displayName = CheckboxPrimitive.Root.displayName;

export { Checkbox };
