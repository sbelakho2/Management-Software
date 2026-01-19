'use client';

import { PageGuard } from '@/components/layout/page-guard';

// Admin and CEO both have full system access
const ADMIN_ROLES = ['admin', 'ceo'] as const;

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PageGuard requiredRoles={[...ADMIN_ROLES]}>
      {children}
    </PageGuard>
  );
}
