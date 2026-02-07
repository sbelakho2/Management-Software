'use client';

import React, { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { EmailComposer } from '@/components/email/email-composer';
import { PageGuard } from '@/components/layout/page-guard';
import { SALES_ROLES } from '@/lib/page-access';
import type { Recipient } from '@/stores/email-drafting-store';

export default function EmailDraftingPage() {
  return (
    <Suspense fallback={<div className="flex h-full items-center justify-center"><p className="text-muted-foreground">Loading…</p></div>}>
      <EmailDraftingContent />
    </Suspense>
  );
}

function EmailDraftingContent() {
  const params = useSearchParams();
  const entityType = params.get('entityType') || undefined;
  const entityId = params.get('entityId') || undefined;
  const referenceNumber = params.get('reference') || undefined;
  const recipientEmail = params.get('recipientEmail') || undefined;
  const recipientName = params.get('recipientName') || undefined;

  const initialRecipient: Recipient | undefined = recipientEmail
    ? {
        id: recipientEmail,
        email: recipientEmail,
        name: recipientName || undefined,
        languagePreference: 'en',
        previousInteractions: 0,
      }
    : undefined;

  return (
    <PageGuard requiredRoles={SALES_ROLES}>
      <div className="flex h-full flex-col">
        <EmailComposer
          initialRecipient={initialRecipient}
          referenceNumber={referenceNumber}
          initialThreadEntityType={entityType}
          initialThreadEntityId={entityId}
        />
      </div>
    </PageGuard>
  );
}

