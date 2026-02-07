'use client';

import * as React from 'react';
import * as CollapsiblePrimitive from '@radix-ui/react-collapsible';
import { ChevronDown } from 'lucide-react';

import { cn } from '@/lib/utils';

/**
 * Accordion Component - Sensei Rams Design System
 * 
 * Collapsible content sections following the Rams design principles:
 * - Clean, functional aesthetics
 * - Smooth animations
 * - Clear visual hierarchy
 * 
 * Built on top of Radix Collapsible primitive.
 */

interface AccordionContextValue {
  type: 'single' | 'multiple';
  value: string | string[];
  onValueChange: (value: string) => void;
}

const AccordionContext = React.createContext<AccordionContextValue | null>(null);

interface AccordionProps {
  type?: 'single' | 'multiple';
  defaultValue?: string;
  value?: string | string[];
  onValueChange?: (value: string | string[]) => void;
  collapsible?: boolean;
  children: React.ReactNode;
  className?: string;
}

function Accordion({
  type = 'single',
  defaultValue,
  value: controlledValue,
  onValueChange,
  collapsible = false,
  children,
  className,
}: AccordionProps) {
  const [uncontrolledValue, setUncontrolledValue] = React.useState<string | string[]>(
    defaultValue || (type === 'multiple' ? [] : '')
  );
  
  const value = controlledValue !== undefined ? controlledValue : uncontrolledValue;
  
  const handleValueChange = React.useCallback((itemValue: string) => {
    const newValue = type === 'multiple'
      ? (Array.isArray(value) && value.includes(itemValue)
          ? value.filter(v => v !== itemValue)
          : [...(Array.isArray(value) ? value : []), itemValue])
      : (value === itemValue && collapsible ? '' : itemValue);
    
    if (onValueChange) {
      onValueChange(newValue);
    } else {
      setUncontrolledValue(newValue);
    }
  }, [type, value, collapsible, onValueChange]);
  
  return (
    <AccordionContext.Provider value={{ type, value, onValueChange: handleValueChange }}>
      <div className={cn('space-y-0', className)}>
        {children}
      </div>
    </AccordionContext.Provider>
  );
}

interface AccordionItemProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

function AccordionItem({ value, children, className }: AccordionItemProps) {
  const context = React.useContext(AccordionContext);
  if (!context) throw new Error('AccordionItem must be used within Accordion');
  
  const isOpen = Array.isArray(context.value)
    ? context.value.includes(value)
    : context.value === value;
  
  return (
    <CollapsiblePrimitive.Root
      open={isOpen}
      onOpenChange={() => context.onValueChange(value)}
      className={cn('border-b border-rams-line last:border-b-0', className)}
    >
      {children}
    </CollapsiblePrimitive.Root>
  );
}

interface AccordionTriggerProps {
  children: React.ReactNode;
  className?: string;
}

function AccordionTrigger({ children, className }: AccordionTriggerProps) {
  return (
    <CollapsiblePrimitive.Trigger
      className={cn(
        'flex w-full items-center justify-between py-4 font-medium transition-all',
        'hover:bg-rams-panel/50 rounded-md px-2 -mx-2',
        '[&[data-state=open]>svg]:rotate-180',
        className
      )}
    >
      {children}
      <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200 text-muted-foreground" />
    </CollapsiblePrimitive.Trigger>
  );
}

interface AccordionContentProps {
  children: React.ReactNode;
  className?: string;
}

function AccordionContent({ children, className }: AccordionContentProps) {
  return (
    <CollapsiblePrimitive.Content
      className="overflow-hidden text-sm transition-all data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down"
    >
      <div className={cn('pb-4 pt-0', className)}>{children}</div>
    </CollapsiblePrimitive.Content>
  );
}

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent };
