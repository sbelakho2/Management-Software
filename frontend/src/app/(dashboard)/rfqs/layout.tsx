'use client';

import { PageGuard } from '@/components/layout/page-guard';
import { SALES_ROLES } from '@/lib/page-access';

export default function RfqsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PageGuard requiredRoles={SALES_ROLES}>
      {children}
    </PageGuard>
  );
}
