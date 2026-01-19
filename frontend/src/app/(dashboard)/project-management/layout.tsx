'use client';

import { PageGuard } from '@/components/layout/page-guard';
import { PAGE_ACCESS } from '@/lib/page-access';

// Project management access roles from page-access.ts
const PROJECT_MANAGEMENT_ROLES = PAGE_ACCESS['/project-management'];

export default function ProjectManagementLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PageGuard requiredRoles={PROJECT_MANAGEMENT_ROLES}>
      {children}
    </PageGuard>
  );
}
