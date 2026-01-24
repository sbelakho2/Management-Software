'use client';

import { PageGuard } from '@/components/layout/page-guard';
import { UserRole } from '@/types';

const QUOTING_ROLES: UserRole[] = [
  'admin', 'ceo', 'gm', 'exec', 'sales', 'estimator', 
  'sales_engineer', 'purchasing', 'supply_chain', 
  'engineering', 'quality', 'ops'
];

export default function QuotingHelperLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PageGuard requiredRoles={QUOTING_ROLES}>
      {children}
    </PageGuard>
  );
}
