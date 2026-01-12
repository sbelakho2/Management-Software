'use client';

import { PageGuard } from '@/components/layout/page-guard';
import { OPS_ROLES } from '@/lib/page-access';

export default function ShopFloorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PageGuard requiredRoles={OPS_ROLES}>
      {children}
    </PageGuard>
  );
}
