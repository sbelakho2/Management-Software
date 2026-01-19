'use client';

import { PageGuard } from '@/components/layout/page-guard';
import { FINANCE_ROLES } from '@/lib/page-access';

export default function FinanceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PageGuard requiredRoles={FINANCE_ROLES}>
      {children}
    </PageGuard>
  );
}
