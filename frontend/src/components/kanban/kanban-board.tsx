'use client';

import * as React from 'react';
import {
  useKanbanStore,
  type KanbanCard,
  type KanbanColumn,
  getPriorityColor,
  formatCurrency,
  getDaysUntilDue,
  getDueDateStatus,
} from '@/stores/kanban-store';
import type { RFQ, RFQStatus, Priority } from '@/types';
import { cn } from '@/lib/utils';

// ============================================================================
// Kanban Board Component
// ============================================================================

interface KanbanBoardProps {
  rfqs: RFQ[];
  onCardClick?: (rfq: RFQ) => void;
  onCardMove?: (cardId: string, fromStatus: RFQStatus, toStatus: RFQStatus) => Promise<void>;
  className?: string;
}

export function KanbanBoard({
  rfqs,
  onCardClick,
  onCardMove,
  className,
}: KanbanBoardProps) {
  const {
    initializeFromRFQs,
    config,
    dragState,
  } = useKanbanStore();

  // Initialize store with RFQs
  React.useEffect(() => {
    initializeFromRFQs(rfqs);
  }, [rfqs, initializeFromRFQs]);

  return (
    <div className={cn('flex h-full gap-4 overflow-x-auto p-4', className)}>
      {config.columns.map((column) => (
        <KanbanColumnComponent
          key={column.id}
          column={column}
          onCardClick={onCardClick}
          onCardMove={onCardMove}
          isDragTarget={dragState.targetColumn === column.id}
        />
      ))}
    </div>
  );
}

// ============================================================================
// Kanban Column Component
// ============================================================================

interface KanbanColumnProps {
  column: KanbanColumn;
  onCardClick?: (rfq: RFQ) => void;
  onCardMove?: (cardId: string, fromStatus: RFQStatus, toStatus: RFQStatus) => Promise<void>;
  isDragTarget?: boolean;
}

function KanbanColumnComponent({
  column,
  onCardClick,
  onCardMove,
  isDragTarget,
}: KanbanColumnProps) {
  const {
    getFilteredCards,
    getColumnWipStatus,
    config,
    dragState,
    moveCard,
    updateDragTarget,
    endDrag,
  } = useKanbanStore();

  const cards = getFilteredCards(column.id);
  const wipStatus = getColumnWipStatus(column.id);
  const columnRef = React.useRef<HTMLDivElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    updateDragTarget(column.id);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    if (columnRef.current && !columnRef.current.contains(e.relatedTarget as Node)) {
      updateDragTarget(null);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    const cardId = e.dataTransfer.getData('text/plain');
    const sourceColumn = dragState.sourceColumn;

    if (cardId && sourceColumn && sourceColumn !== column.id) {
      await moveCard(cardId, sourceColumn, column.id, cards.length);
      onCardMove?.(cardId, sourceColumn, column.id);
    }
    endDrag();
  };

  return (
    <div
      ref={columnRef}
      className={cn(
        'flex w-80 flex-shrink-0 flex-col rounded-lg bg-gray-100 dark:bg-gray-800',
        isDragTarget && 'ring-2 ring-blue-500 ring-offset-2'
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Column Header */}
      <div
        className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700"
        style={{ borderTopColor: column.color, borderTopWidth: 3 }}
      >
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {column.title}
          </h3>
          <span
            className={cn(
              'rounded-full px-2 py-0.5 text-xs font-medium',
              wipStatus.isOverLimit
                ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                : 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
            )}
          >
            {wipStatus.count}
            {config.showWipLimits && wipStatus.limit && (
              <span className="ml-0.5 opacity-60">/{wipStatus.limit}</span>
            )}
          </span>
        </div>
      </div>

      {/* Cards Container */}
      <div className="flex-1 space-y-3 overflow-y-auto p-3">
        {cards.map((card) => (
          <KanbanCardComponent
            key={card.id}
            card={card}
            onClick={() => onCardClick?.(card.rfq)}
            config={config}
          />
        ))}

        {/* Empty state */}
        {cards.length === 0 && (
          <div className="flex h-24 items-center justify-center rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600">
            <p className="text-sm text-gray-400 dark:text-gray-500">
              No items
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Kanban Card Component
// ============================================================================

interface KanbanCardComponentProps {
  card: KanbanCard;
  onClick?: () => void;
  config: {
    showAvatars: boolean;
    showDueDates: boolean;
    showValues: boolean;
    compactMode: boolean;
  };
}

function KanbanCardComponent({
  card,
  onClick,
  config,
}: KanbanCardComponentProps) {
  const { startDrag, endDrag, selectedCardId, selectCard } = useKanbanStore();
  const { rfq } = card;

  const dueDateStatus = getDueDateStatus(rfq.due_date);
  const daysUntilDue = getDaysUntilDue(rfq.due_date);
  const isSelected = selectedCardId === card.id;

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('text/plain', card.id);
    e.dataTransfer.effectAllowed = 'move';
    startDrag(card);
  };

  const handleDragEnd = () => {
    endDrag();
  };

  return (
    <div
      draggable
      onClick={() => {
        selectCard(card.id);
        onClick?.();
      }}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className={cn(
        'cursor-pointer rounded-lg border bg-white p-3 shadow-sm transition-all dark:bg-gray-900',
        'hover:shadow-md hover:ring-1 hover:ring-gray-200 dark:hover:ring-gray-700',
        isSelected && 'ring-2 ring-blue-500',
        config.compactMode && 'p-2'
      )}
    >
      {/* Header */}
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {rfq.rfq_number}
          </p>
          <h4 className="mt-0.5 truncate text-sm font-medium text-gray-900 dark:text-white">
            {rfq.title}
          </h4>
        </div>
        <PriorityBadge priority={rfq.priority} />
      </div>

      {/* Customer */}
      <p className="mb-2 truncate text-xs text-gray-600 dark:text-gray-400">
        {rfq.customer?.name || 'Unknown Customer'}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between gap-2">
        {/* Due Date */}
        {config.showDueDates && (
          <DueDateBadge status={dueDateStatus} days={daysUntilDue} />
        )}

        {/* Value */}
        {config.showValues && rfq.estimated_value && (
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
            {formatCurrency(rfq.estimated_value, rfq.currency)}
          </span>
        )}

        {/* Assignee Avatar */}
        {config.showAvatars && rfq.assigned_user && (
          <div className="flex -space-x-2">
            <Avatar
              name={rfq.assigned_user.full_name}
              avatarUrl={rfq.assigned_user.avatar_url}
            />
          </div>
        )}
      </div>

      {/* Tags */}
      {rfq.tags && rfq.tags.length > 0 && !config.compactMode && (
        <div className="mt-2 flex flex-wrap gap-1">
          {rfq.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400"
            >
              {tag}
            </span>
          ))}
          {rfq.tags.length > 3 && (
            <span className="text-xs text-gray-400">
              +{rfq.tags.length - 3}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Supporting Components
// ============================================================================

function PriorityBadge({ priority }: { priority: Priority }) {
  const labels: Record<Priority, string> = {
    urgent: 'Urgent',
    high: 'High',
    medium: 'Medium',
    low: 'Low',
  };

  const colors: Record<Priority, string> = {
    urgent: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    high: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
    medium: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    low: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
  };

  return (
    <span
      className={cn(
        'flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
        colors[priority]
      )}
    >
      {labels[priority]}
    </span>
  );
}

function DueDateBadge({
  status,
  days,
}: {
  status: 'overdue' | 'due-soon' | 'on-track';
  days: number;
}) {
  const getLabel = () => {
    if (days === 0) return 'Due today';
    if (days === 1) return 'Due tomorrow';
    if (days < 0) return `${Math.abs(days)}d overdue`;
    return `${days}d left`;
  };

  const colors = {
    overdue: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    'due-soon': 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    'on-track': 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  };

  return (
    <span
      className={cn(
        'flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
        colors[status]
      )}
    >
      <CalendarIcon className="h-3 w-3" />
      {getLabel()}
    </span>
  );
}

function Avatar({
  name,
  avatarUrl,
}: {
  name: string;
  avatarUrl?: string;
}) {
  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={name}
        title={name}
        className="h-6 w-6 rounded-full border-2 border-white object-cover dark:border-gray-900"
      />
    );
  }

  return (
    <div
      title={name}
      className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-gray-300 text-xs font-medium text-gray-700 dark:border-gray-900 dark:bg-gray-600 dark:text-gray-200"
    >
      {initials}
    </div>
  );
}

function CalendarIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

// ============================================================================
// Kanban Toolbar Component
// ============================================================================

interface KanbanToolbarProps {
  onSearch?: (query: string) => void;
  onFilterChange?: () => void;
  onViewChange?: (view: 'kanban' | 'list' | 'calendar') => void;
  currentView?: 'kanban' | 'list' | 'calendar';
}

export function KanbanToolbar({
  onSearch,
  onFilterChange,
  onViewChange,
  currentView = 'kanban',
}: KanbanToolbarProps) {
  const { searchQuery, setSearchQuery, config, setConfig, clearFilters } = useKanbanStore();
  const [localSearch, setLocalSearch] = React.useState(searchQuery);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(localSearch);
    onSearch?.(localSearch);
  };

  return (
    <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-900">
      {/* Search */}
      <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md">
        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            placeholder="Search RFQs..."
            className="w-full rounded-md border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          />
        </div>
      </form>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Filter button */}
        <button
          onClick={onFilterChange}
          className="flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
        >
          <FilterIcon className="h-4 w-4" />
          Filters
        </button>

        {/* Clear filters */}
        <button
          onClick={clearFilters}
          className="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          Clear
        </button>

        {/* View toggle */}
        <div className="flex rounded-md border border-gray-300 dark:border-gray-600">
          <button
            onClick={() => onViewChange?.('kanban')}
            className={cn(
              'rounded-l-md px-3 py-2',
              currentView === 'kanban'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200'
            )}
            aria-label="Kanban view"
            title="Kanban view"
            aria-pressed={currentView === 'kanban'}
          >
            <KanbanIcon className="h-4 w-4" aria-hidden="true" />
          </button>
          <button
            onClick={() => onViewChange?.('list')}
            className={cn(
              'border-x border-gray-300 px-3 py-2 dark:border-gray-600',
              currentView === 'list'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200'
            )}
            aria-label="List view"
            title="List view"
            aria-pressed={currentView === 'list'}
          >
            <ListIcon className="h-4 w-4" aria-hidden="true" />
          </button>
          <button
            onClick={() => onViewChange?.('calendar')}
            className={cn(
              'rounded-r-md px-3 py-2',
              currentView === 'calendar'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200'
            )}
            aria-label="Calendar view"
            title="Calendar view"
            aria-pressed={currentView === 'calendar'}
          >
            <CalendarIcon className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Settings */}
        <div className="relative">
          <button
            onClick={() =>
              setConfig({ compactMode: !config.compactMode })
            }
            className="rounded-md border border-gray-300 bg-white p-2 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
            aria-label={config.compactMode ? 'Expand cards' : 'Compact cards'}
            title={config.compactMode ? 'Expand cards' : 'Compact cards'}
            aria-pressed={config.compactMode}
          >
            <SettingsIcon className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}

// Additional Icons

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function FilterIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    </svg>
  );
}

function KanbanIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="3" width="5" height="18" rx="1" />
      <rect x="10" y="3" width="5" height="12" rx="1" />
      <rect x="17" y="3" width="5" height="8" rx="1" />
    </svg>
  );
}

function ListIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="8" y1="6" x2="21" y2="6" />
      <line x1="8" y1="12" x2="21" y2="12" />
      <line x1="8" y1="18" x2="21" y2="18" />
      <line x1="3" y1="6" x2="3.01" y2="6" />
      <line x1="3" y1="12" x2="3.01" y2="12" />
      <line x1="3" y1="18" x2="3.01" y2="18" />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

// ============================================================================
// Kanban Metrics Component
// ============================================================================

export function KanbanMetrics() {
  const { config, getColumnWipStatus, getFilteredCards } = useKanbanStore();

  const metrics = config.columns.map((column) => {
    const cards = getFilteredCards(column.id);
    const totalValue = cards.reduce(
      (sum, card) => sum + (card.rfq.estimated_value || 0),
      0
    );
    return {
      column,
      count: cards.length,
      totalValue,
      wipStatus: getColumnWipStatus(column.id),
    };
  });

  const totalCards = metrics.reduce((sum, m) => sum + m.count, 0);
  const totalValue = metrics.reduce((sum, m) => sum + m.totalValue, 0);

  return (
    <div className="flex items-center gap-6 border-b border-gray-200 bg-gray-50 px-4 py-2 dark:border-gray-700 dark:bg-gray-800">
      <div className="text-sm">
        <span className="text-gray-500 dark:text-gray-400">Total: </span>
        <span className="font-medium text-gray-900 dark:text-white">
          {totalCards} RFQs
        </span>
      </div>
      <div className="text-sm">
        <span className="text-gray-500 dark:text-gray-400">Pipeline Value: </span>
        <span className="font-medium text-gray-900 dark:text-white">
          {formatCurrency(totalValue)}
        </span>
      </div>
      <div className="flex-1" />
      <div className="flex gap-4">
        {metrics.slice(0, 4).map(({ column, count, totalValue }) => (
          <div key={column.id} className="text-center">
            <div
              className="text-xs font-medium"
              style={{ color: column.color }}
            >
              {column.title}
            </div>
            <div className="text-sm text-gray-900 dark:text-white">
              {count} ({formatCurrency(totalValue)})
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
