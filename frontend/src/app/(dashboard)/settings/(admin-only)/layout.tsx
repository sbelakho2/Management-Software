'use client';

import { PageGuard } from '@/components/layout/page-guard';

export default function AdminSettingsLayout({
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
