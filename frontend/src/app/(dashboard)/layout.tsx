'use client';

import { TooltipProvider } from '@/components/ui/tooltip';
import { MainLayout, CommandPalette } from '@/components/layout';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <TooltipProvider delayDuration={0}>
      <MainLayout>
        {children}
      </MainLayout>
      <CommandPalette />
    </TooltipProvider>
  );
}
