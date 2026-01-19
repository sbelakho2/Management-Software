'use client';

import { PageGuard } from '@/components/layout/page-guard';
import { PAGE_ACCESS } from '@/lib/page-access';

// Projects access roles from page-access.ts (same as project-management)
const PROJECTS_ROLES = PAGE_ACCESS['/projects'];

export default function ProjectsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PageGuard requiredRoles={PROJECTS_ROLES}>
      {children}
    </PageGuard>
  );
}
