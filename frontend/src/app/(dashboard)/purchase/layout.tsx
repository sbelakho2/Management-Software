'use client';

import { PageGuard } from '@/components/layout/page-guard';
import { PAGE_ACCESS } from '@/lib/page-access';

// Purchase access roles from page-access.ts
const PURCHASE_ROLES = PAGE_ACCESS['/purchase'];

export default function PurchaseLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PageGuard requiredRoles={PURCHASE_ROLES}>
      {children}
    </PageGuard>
  );
}
