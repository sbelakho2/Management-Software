'use client';

import * as React from 'react';
import * as SwitchPrimitives from '@radix-ui/react-switch';
import { cn } from '@/lib/utils';

const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitives.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitives.Root
    className={cn(
      'peer inline-flex h-5 w-10 shrink-0 cursor-pointer items-center rounded-rams-sm border border-rams-border',
      'transition-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-rams-orange',
      'disabled:cursor-not-allowed disabled:opacity-40',
      'data-[state=checked]:bg-rams-orange/20 data-[state=unchecked]:bg-rams-panel',
      className
    )}
    {...props}
    ref={ref}
  >
    <SwitchPrimitives.Thumb
      className={cn(
        'pointer-events-none block h-3.5 w-3.5 rounded-full bg-rams-chassis border border-rams-border shadow-none',
        'transition-transform duration-100 data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-1',
        'data-[state=checked]:bg-rams-orange'
      )}
    />
  </SwitchPrimitives.Root>
));
Switch.displayName = SwitchPrimitives.Root.displayName;

export { Switch };
