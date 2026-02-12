'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

/**
 * Premium Table Component
 * 
 * Features:
 * - Sticky header support
 * - Row actions on hover
 * - Strong empty states
 * - Responsive design
 * - Sortable columns
 * - Selection support
 * - Loading states
 * - Zebra striping option
 */

// =============================================================================
// Base Table Components
// =============================================================================

const TableContext = React.createContext<{ inTable: boolean } | null>(null);

const Table = React.forwardRef<
  HTMLTableElement,
  React.HTMLAttributes<HTMLTableElement> & {
    stickyHeader?: boolean;
    zebra?: boolean;
  }
>(({ className, stickyHeader = false, zebra = false, ...props }, ref) => (
  <TableContext.Provider value={{ inTable: true }}>
    <div className={cn('relative w-full', stickyHeader && 'max-h-[600px] overflow-auto')}>
      <table
        ref={ref}
        className={cn(
          'w-full caption-bottom text-sm',
          zebra && '[&_tbody_tr:nth-child(even)]:bg-muted/20',
          className
        )}
        {...props}
      />
    </div>
  </TableContext.Provider>
));
Table.displayName = 'Table';

const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement> & {
    sticky?: boolean;
  }
>(({ className, sticky = false, ...props }, ref) => (
  <thead
    ref={ref}
    className={cn(
      'bg-rams-module border-b border-rams-line',
      sticky && 'sticky top-0 z-10',
      className
    )}
    {...props}
  />
));
TableHeader.displayName = 'TableHeader';

const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={cn('[&_tr:last-child]:border-0 bg-rams-chassis/50', className)}
    {...props}
  />
));
TableBody.displayName = 'TableBody';

const TableFooter = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tfoot
    ref={ref}
    className={cn(
      'border-t border-rams-line bg-rams-module font-mono font-bold [&>tr]:last:border-b-0',
      className
    )}
    {...props}
  />
));
TableFooter.displayName = 'TableFooter';

const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement> & {
    selected?: boolean;
    hoverable?: boolean;
  }
>(({ className, selected = false, hoverable = true, ...props }, ref) => {
  const ctx = React.useContext(TableContext);
  const row = (
    <tr
      ref={ref}
      className={cn(
        'border-b border-rams-line/50 transition-none',
        hoverable && 'hover:bg-rams-panel',
        selected && 'bg-rams-orange/10',
        'data-[state=selected]:bg-rams-orange/10',
        className
      )}
      {...props}
    />
  );

  // When rendered outside a <table>, wrap to keep HTML valid and avoid
  // validateDOMNesting warnings in tests.
  if (!ctx?.inTable) {
    return (
      <table className="w-full">
        <tbody>{row}</tbody>
      </table>
    );
  }

  return row;
});
TableRow.displayName = 'TableRow';

const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement> & {
    sortable?: boolean;
    sortDirection?: 'asc' | 'desc' | null;
    onSort?: () => void;
  }
>(({ className, sortable = false, sortDirection = null, onSort, children, ...props }, ref) => {
  const ctx = React.useContext(TableContext);
  const head = (
    <th
      ref={ref}
      className={cn(
        'h-10 px-4 text-left align-middle font-mono font-black uppercase tracking-widest text-[9px] text-muted-foreground/60',
        sortable && 'cursor-pointer select-none hover:text-rams-orange transition-none',
        className
      )}
      onClick={sortable && onSort ? onSort : undefined}
      {...props}
    >
      <div className="flex items-center gap-2">
        {children}
        {sortable && (
          <span className="text-[10px] opacity-40 font-bold">
            {sortDirection === 'asc' && '↑'}
            {sortDirection === 'desc' && '↓'}
            {!sortDirection && '⇅'}
          </span>
        )}
      </div>
    </th>
  );

  if (!ctx?.inTable) {
    return (
      <table className="w-full">
        <thead>
          <tr>{head}</tr>
        </thead>
      </table>
    );
  }

  return head;
});
TableHead.displayName = 'TableHead';

const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={cn(
      'p-4 align-middle [&:has([role=checkbox])]:pr-0 font-sans font-medium',
      className
    )}
    {...props}
  />
));
TableCell.displayName = 'TableCell';

const TableCaption = React.forwardRef<
  HTMLTableCaptionElement,
  React.HTMLAttributes<HTMLTableCaptionElement>
>(({ className, ...props }, ref) => (
  <caption
    ref={ref}
    className={cn('mt-4 text-[10px] font-mono uppercase tracking-widest text-muted-foreground/40', className)}
    {...props}
  />
));
TableCaption.displayName = 'TableCaption';

// =============================================================================
// Enhanced Table Components
// =============================================================================

interface TableActionsProps {
  children: React.ReactNode;
  className?: string;
}

const TableActions = React.forwardRef<HTMLDivElement, TableActionsProps>(
  ({ children, className }, ref) => (
    <div
      ref={ref}
      className={cn(
        'flex items-center gap-2 opacity-0 transition-none group-hover:opacity-100',
        className
      )}
    >
      {children}
    </div>
  )
);
TableActions.displayName = 'TableActions';

interface TableEmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

const TableEmptyState = React.forwardRef<HTMLDivElement, TableEmptyStateProps>(
  ({ title, description, action, icon, className }, ref) => {
    const { t } = useI18n();
    const resolvedTitle = title ?? t('components.table.noData');
    return (
      <div
        ref={ref}
        className={cn(
          'flex min-h-[400px] flex-col items-center justify-center gap-4 p-8 text-center',
          className
        )}
      >
        {icon && <div className="text-muted-foreground opacity-50">{icon}</div>}
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">{resolvedTitle}</h3>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {action && <div className="mt-4">{action}</div>}
      </div>
    );
  }
);
TableEmptyState.displayName = 'TableEmptyState';

interface TableLoadingStateProps {
  rows?: number;
  columns?: number;
  className?: string;
}

const TableLoadingState = React.forwardRef<HTMLDivElement, TableLoadingStateProps>(
  ({ rows = 5, columns = 4, className }, ref) => (
    <div ref={ref} className={cn('w-full space-y-4', className)}>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div
              key={colIndex}
              className="h-8 flex-1 animate-pulse rounded bg-muted"
            />
          ))}
        </div>
      ))}
    </div>
  )
);
TableLoadingState.displayName = 'TableLoadingState';

interface TablePaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
  className?: string;
}

const TablePagination = React.forwardRef<HTMLDivElement, TablePaginationProps>(
  (
    {
      currentPage,
      totalPages,
      pageSize,
      totalItems,
      onPageChange,
      onPageSizeChange,
      pageSizeOptions = [10, 20, 50, 100],
      className,
    },
    ref
  ) => {
    const { t } = useI18n();
    const startItem = (currentPage - 1) * pageSize + 1;
    const endItem = Math.min(currentPage * pageSize, totalItems);

    return (
      <div
        ref={ref}
        className={cn(
          'flex items-center justify-between border-t bg-background px-4 py-3',
          className
        )}
      >
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>
            Showing {startItem} to {endItem} of {totalItems} results
          </span>
          {onPageSizeChange && (
            <div className="flex items-center gap-2">
              <span>{t('components.table.rowsPerPage')}</span>
              <select
                value={pageSize}
                onChange={(e) => onPageSizeChange(Number(e.target.value))}
                className="rounded border bg-background px-2 py-1"
              >
                {pageSizeOptions.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="rounded border px-3 py-1 text-sm disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-2 text-sm">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="rounded border px-3 py-1 text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    );
  }
);
TablePagination.displayName = 'TablePagination';

interface TableSearchProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

const TableSearch = React.forwardRef<HTMLInputElement, TableSearchProps>(
  ({ value, onChange, placeholder = 'Search...', className }, ref) => (
    <div className={cn('relative', className)}>
      <input
        ref={ref}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border bg-background px-4 py-2 pl-10 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
      />
      <svg
        className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
    </div>
  )
);
TableSearch.displayName = 'TableSearch';

// =============================================================================
// Exports
// =============================================================================

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
  TableActions,
  TableEmptyState,
  TableLoadingState,
  TablePagination,
  TableSearch,
};
