'use client';

import { PageGuard } from '@/components/layout/page-guard';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PageGuard requiredRoles={['admin']}>
      {children}
    </PageGuard>
  );
}
