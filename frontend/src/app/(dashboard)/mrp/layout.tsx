'use client';

import { PageGuard } from '@/components/layout/page-guard';
import { PAGE_ACCESS } from '@/lib/page-access';

// MRP access roles from page-access.ts
const MRP_ROLES = PAGE_ACCESS['/mrp'];

export default function MrpLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PageGuard requiredRoles={MRP_ROLES}>
      {children}
    </PageGuard>
  );
}
