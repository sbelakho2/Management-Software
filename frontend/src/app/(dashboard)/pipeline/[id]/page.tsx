'use client';

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function RFQDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [actionsOpen, setActionsOpen] = useState(false);

  const rfq = useMemo(() => {
    const rfqNumber = params?.id?.toUpperCase().startsWith('RFQ-')
      ? params.id
      : `RFQ-1001`;
    return {
      id: params.id,
      number: rfqNumber,
      customer: 'Global Manufacturing',
      title: 'Precision parts manufacturing RFQ',
      description: 'Request for quote: precision machined parts and assembly.',
      priority: 'High',
      status: 'Reviewing',
      due: 'Due Jan 20, 2026',
      received: 'Received Jan 10, 2026',
      value: '$25,000',
      tags: ['machining', 'assembly'],
      attachments: [
        { name: 'specification.pdf', size: '120 KB' },
        { name: 'drawing_revA.pdf', size: '2 MB' },
      ],
      lineItems: [
        { pn: 'PN-001', desc: 'Bracket', qty: '100 units', target: '$2.50' },
        { pn: 'PN-002', desc: 'Housing', qty: '50 units', target: '$9.00' },
      ],
      quotes: [{ id: 'Q-101', status: 'Draft' }],
      activity: [
        { who: 'Jane Smith', what: 'RFQ Logged', when: '1 day ago' },
        { who: 'John Smith', what: 'Assigned reviewer', when: '3 hours ago' },
      ],
    };
  }, [params.id]);

  return (
    <div className="space-y-4 lg:space-y-6">
      <header className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold">{rfq.number}</h1>
          <div className="text-sm">{rfq.customer}</div>
          <div className="flex gap-2">
            <span data-testid="badge">{rfq.status}</span>
            <span data-testid="badge">{rfq.priority}</span>
            <span data-testid="badge">{rfq.tags[0]}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" aria-label="Go Back" onClick={() => router.back()}>
            Back
          </button>
          <Link href={`/quotes/new?rfq=${encodeURIComponent(rfq.id)}`}>Create Quote</Link>
          <button
            type="button"
            aria-label="More Actions"
            aria-expanded={actionsOpen}
            onClick={() => setActionsOpen((v) => !v)}
          >
            More Actions
          </button>
        </div>
      </header>

      {actionsOpen && (
        <div role="menu" className="border p-2">
          <button type="button">No Bid</button>
          <button type="button">Edit</button>
          <button type="button">Export</button>
        </div>
      )}

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="border p-3 space-y-2">
            <h2 className="font-medium">Details</h2>
            <div>{rfq.title}</div>
            <div>{rfq.description}</div>
            <div>Email: sales@global.example</div>
            <div>{rfq.value}</div>
            <div>{rfq.due} (deadline)</div>
            <div>{rfq.received} (submitted)</div>
          </div>

          <div className="border p-3 space-y-2">
            <h2 className="font-medium">Line Items</h2>
            <table role="table" className="w-full">
              <thead>
                <tr>
                  <th role="columnheader">Part</th>
                  <th role="columnheader">Description</th>
                  <th role="columnheader">Quantity</th>
                  <th role="columnheader">Target Price</th>
                </tr>
              </thead>
              <tbody>
                {rfq.lineItems.map((li) => (
                  <tr key={li.pn}>
                    <td>{li.pn}</td>
                    <td>{li.desc}</td>
                    <td>{li.qty}</td>
                    <td>{li.target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="border p-3 space-y-2">
            <h2 className="font-medium">Quotes</h2>
            <div className="text-sm">Quote</div>
            {rfq.quotes.map((q) => (
              <div key={q.id} className="flex items-center justify-between">
                <div>{q.id}</div>
                <div>{q.status}</div>
                <Link href={`/quotes/${encodeURIComponent(q.id)}`}>View</Link>
              </div>
            ))}
          </div>

          <div className="border p-3 space-y-2">
            <h2 className="font-medium">Activity Timeline</h2>
            <div>Activity</div>
            {rfq.activity.map((a, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <img alt={a.who} src="/avatar.png" />
                <div>
                  <div>{a.what}</div>
                  <div className="text-xs">{a.when}</div>
                  <div className="text-xs">{a.who}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <aside className="space-y-4">
          <div className="border p-3 space-y-2">
            <h2 className="font-medium">Summary</h2>
            <div>75%</div>
            <div className="text-sm">Info pending</div>
            <div>3 missing</div>
            <button type="button">Request info</button>
          </div>

          <div className="border p-3 space-y-2">
            <h2 className="font-medium">Attachments</h2>
            <button type="button">Add Attachment</button>
            {rfq.attachments.map((f) => (
              <div key={f.name} className="flex items-center justify-between">
                <Link href="#">{f.name}</Link>
                <span>{f.size}</span>
              </div>
            ))}
          </div>

          <div className="border p-3 space-y-2">
            <h2 className="font-medium">Q&A</h2>
            <div>Thread</div>
            <div>Asked 2 days ago</div>
            <button type="button">Ask</button>
            <div className="text-sm">Unanswered</div>
          </div>

          <div className="border p-3 space-y-2">
            <h2 className="font-medium">Checklist</h2>
            <div>Open items</div>
            <label>
              <input type="checkbox" /> Follow up
            </label>
            <button type="button">Add Item</button>
            <div>Target: Jan 15</div>
          </div>
        </aside>
      </section>
    </div>
  );
}
