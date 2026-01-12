'use client';

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';

type PipelineStage = 'new' | 'reviewing' | 'quoting' | 'submitted';
type Priority = 'urgent' | 'high' | 'medium' | 'low';

interface RFQItem {
  id: string;
  number: string;
  customer: string;
  stage: PipelineStage;
  priority: Priority;
  valueUsd: number;
  dueDateLabel: string;
  receivedDateLabel: string;
  assigneeName: string;
}

const STAGES: Array<{ id: PipelineStage; label: string }> = [
  { id: 'new', label: 'New' },
  { id: 'reviewing', label: 'Reviewing' },
  { id: 'quoting', label: 'Quoting' },
  { id: 'submitted', label: 'Submitted' },
];

const SEED_RFQS: RFQItem[] = [
  {
    id: 'rfq-1',
    number: 'RFQ-1001',
    customer: 'Global Manufacturing',
    stage: 'new',
    priority: 'high',
    valueUsd: 25000,
    dueDateLabel: 'Due Jan 20, 2026',
    receivedDateLabel: 'Received Jan 10, 2026',
    assigneeName: 'Jane Smith',
  },
  {
    id: 'rfq-2',
    number: 'RFQ-1002',
    customer: 'Acme Tech',
    stage: 'reviewing',
    priority: 'urgent',
    valueUsd: 78000,
    dueDateLabel: 'Due Jan 18, 2026 (Overdue)',
    receivedDateLabel: 'Received Jan 05, 2026',
    assigneeName: 'John Smith',
  },
  {
    id: 'rfq-3',
    number: 'RFQ-1003',
    customer: 'TechStart',
    stage: 'quoting',
    priority: 'medium',
    valueUsd: 12000,
    dueDateLabel: 'Due Jan 28, 2026',
    receivedDateLabel: 'Received Jan 11, 2026',
    assigneeName: 'System',
  },
  {
    id: 'rfq-4',
    number: 'RFQ-1004',
    customer: 'Precision Parts Co',
    stage: 'submitted',
    priority: 'low',
    valueUsd: 5400,
    dueDateLabel: 'Due Feb 01, 2026',
    receivedDateLabel: 'Received Jan 08, 2026',
    assigneeName: 'Jane Smith',
  },
];

function formatStageCount(count: number): string {
  return `${count} RFQ${count === 1 ? '' : 's'}`;
}

export default function PipelinePage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const initialView = (searchParams?.get('view') || 'list').toLowerCase();
  const [view, setView] = useState<'list' | 'board'>(initialView === 'board' ? 'board' : 'list');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<PipelineStage | 'all'>('all');
  const [priorityFilter, setPriorityFilter] = useState<Priority | 'all'>('all');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return SEED_RFQS.filter((rfq) => {
      if (statusFilter !== 'all' && rfq.stage !== statusFilter) return false;
      if (priorityFilter !== 'all' && rfq.priority !== priorityFilter) return false;
      if (!q) return true;
      return (
        rfq.number.toLowerCase().includes(q) ||
        rfq.customer.toLowerCase().includes(q) ||
        rfq.assigneeName.toLowerCase().includes(q)
      );
    });
  }, [search, statusFilter, priorityFilter]);

  const countsByStage = useMemo(() => {
    const counts: Record<PipelineStage, number> = {
      new: 0,
      reviewing: 0,
      quoting: 0,
      submitted: 0,
    };
    for (const rfq of filtered) counts[rfq.stage] += 1;
    return counts;
  }, [filtered]);

  const setAndPersistView = (nextView: 'list' | 'board') => {
    setView(nextView);
    router.replace(`?view=${nextView}`);
  };

  const clearFilters = () => {
    setSearch('');
    setStatusFilter('all');
    setPriorityFilter('all');
  };

  return (
    <div className="space-y-4 lg:space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold">Pipeline</h1>
          <p className="text-sm text-muted-foreground">New → Reviewing → Quoting → Submitted</p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/pipeline/new" className="underline">
            Create RFQ
          </Link>
          <button
            type="button"
            aria-label="List View"
            onClick={() => setAndPersistView('list')}
          >
            List View
          </button>
          <button
            type="button"
            aria-label="Board View"
            onClick={() => setAndPersistView('board')}
          >
            Board View
          </button>
        </div>
      </header>

      <section className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          placeholder="Search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Status Filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as PipelineStage | 'all')}
        >
          <option value="all">All statuses</option>
          {STAGES.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
        <select
          aria-label="Priority Filter"
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value as Priority | 'all')}
        >
          <option value="all">All priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        {(search || statusFilter !== 'all' || priorityFilter !== 'all') && (
          <button type="button" onClick={clearFilters}>
            Clear
          </button>
        )}
      </section>

      {view === 'board' ? (
        <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {STAGES.map((stage) => {
            const stageRfqs = filtered.filter((r) => r.stage === stage.id);
            return (
              <div key={stage.id} className="col-span-1 border p-3">
                <div className="flex items-center justify-between">
                  <h2 className="font-medium">{stage.label}</h2>
                  <span className="text-sm text-muted-foreground">{formatStageCount(stageRfqs.length)}</span>
                </div>
                <div className="mt-3 space-y-2">
                  {stageRfqs.map((rfq) => (
                    <div key={rfq.id} className="border p-2">
                      <Link href={`/pipeline/${rfq.id}`}>
                        {rfq.number}
                      </Link>
                      <div className="text-sm">{rfq.customer}</div>
                      <div className="text-xs">${rfq.valueUsd.toLocaleString()} • {rfq.dueDateLabel}</div>
                      <div className="text-xs">{rfq.priority}</div>
                      <img alt={rfq.assigneeName} src="/avatar.png" />
                    </div>
                  ))}
                  {stageRfqs.length === 0 && <div className="text-sm">No items</div>}
                </div>
              </div>
            );
          })}
        </section>
      ) : (
        <section className="space-y-2">
          <div className="flex gap-3">
            {STAGES.map((s) => (
              <div key={s.id} className="text-sm">
                <span className="font-medium">{s.label}</span> <span>{formatStageCount(countsByStage[s.id])}</span>
              </div>
            ))}
            <div className="text-sm">
              <span className="font-medium">Total</span> <span>{filtered.length} total</span>
            </div>
          </div>

          {filtered.length === 0 ? (
            <div>No results</div>
          ) : (
            <table role="table" className="w-full">
              <thead>
                <tr>
                  <th role="columnheader">RFQ</th>
                  <th role="columnheader">Customer</th>
                  <th role="columnheader">Stage</th>
                  <th role="columnheader">Priority</th>
                  <th role="columnheader">Value</th>
                  <th role="columnheader">Due</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((rfq) => (
                  <tr
                    key={rfq.id}
                    className="cursor-pointer"
                    onClick={() => router.push(`/pipeline/${rfq.id}`)}
                  >
                    <td>{rfq.number}</td>
                    <td>{rfq.customer}</td>
                    <td>{rfq.stage}</td>
                    <td>{rfq.priority}</td>
                    <td>${rfq.valueUsd.toLocaleString()}</td>
                    <td>{rfq.dueDateLabel}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
