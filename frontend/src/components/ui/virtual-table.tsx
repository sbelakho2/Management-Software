/**
 * VirtualTable — Virtualized table component for large datasets.
 *
 * Uses CSS-based virtualization (no external dependency) to render
 * only visible rows. Supports:
 * - Fixed row height virtualization
 * - Column definitions with sorting
 * - Sticky header
 * - Row click handlers
 * - Loading / empty states
 * - Keyboard navigation
 *
 * For datasets > 100 rows, use this instead of mapping over all rows.
 *
 * Checklist items: #295, #441
 *
 * @example
 * ```tsx
 * <VirtualTable
 *   data={inspections}
 *   columns={[
 *     { key: "title", header: "Title", width: 200 },
 *     { key: "status", header: "Status", width: 120 },
 *   ]}
 *   rowHeight={48}
 *   maxHeight={600}
 *   onRowClick={(row) => router.push(`/quality/${row.id}`)}
 * />
 * ```
 */

"use client";

import React, { useCallback, useMemo, useRef, useState, useEffect } from "react";
import { cn } from "@/lib/utils";

// ─── Types ───────────────────────────────────────────────────────

export interface VirtualColumn<T> {
  key: string;
  header: string;
  width?: number | string;
  minWidth?: number;
  sortable?: boolean;
  align?: "left" | "center" | "right";
  render?: (value: any, row: T, index: number) => React.ReactNode;
  className?: string;
}

export interface VirtualTableProps<T extends Record<string, any>> {
  data: T[];
  columns: VirtualColumn<T>[];
  rowHeight?: number;
  maxHeight?: number;
  overscan?: number;
  onRowClick?: (row: T, index: number) => void;
  rowClassName?: string | ((row: T, index: number) => string);
  loading?: boolean;
  emptyMessage?: string;
  className?: string;
  stickyHeader?: boolean;
  sortColumn?: string;
  sortDirection?: "asc" | "desc";
  onSort?: (column: string, direction: "asc" | "desc") => void;
  getRowKey?: (row: T, index: number) => string;
  ariaLabel?: string;
}

// ─── Component ───────────────────────────────────────────────────

export function VirtualTable<T extends Record<string, any>>({
  data,
  columns,
  rowHeight = 48,
  maxHeight = 600,
  overscan = 5,
  onRowClick,
  rowClassName,
  loading = false,
  emptyMessage = "No data available",
  className,
  stickyHeader = true,
  sortColumn,
  sortDirection = "asc",
  onSort,
  getRowKey,
  ariaLabel,
}: VirtualTableProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const totalHeight = data.length * rowHeight;
  const visibleCount = Math.ceil(maxHeight / rowHeight);
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const endIndex = Math.min(
    data.length,
    Math.ceil((scrollTop + maxHeight) / rowHeight) + overscan
  );

  const visibleRows = useMemo(
    () => data.slice(startIndex, endIndex),
    [data, startIndex, endIndex]
  );

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const handleSort = useCallback(
    (column: string) => {
      if (!onSort) return;
      const newDir =
        sortColumn === column && sortDirection === "asc" ? "desc" : "asc";
      onSort(column, newDir);
    },
    [onSort, sortColumn, sortDirection]
  );

  const handleRowKeyDown = useCallback(
    (e: React.KeyboardEvent, row: T, index: number) => {
      if (onRowClick && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        onRowClick(row, index);
      }
    },
    [onRowClick]
  );

  // Loading state
  if (loading) {
    return (
      <div className={cn("border rounded-lg", className)} role="status" aria-label="Loading table data">
        <div className="flex items-center justify-center p-12 text-muted-foreground">
          <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
            <path fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" className="opacity-75" />
          </svg>
          Loading…
        </div>
      </div>
    );
  }

  // Empty state
  if (data.length === 0) {
    return (
      <div className={cn("border rounded-lg", className)}>
        <table className="w-full" role="grid" aria-label={ariaLabel}>
          <thead>
            <tr className="border-b bg-muted/50">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-3 text-left text-sm font-medium text-muted-foreground"
                  style={{ width: col.width, minWidth: col.minWidth }}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
        </table>
        <div className="flex items-center justify-center p-12 text-muted-foreground">
          {emptyMessage}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("border rounded-lg overflow-hidden", className)}>
      {/* Sticky header */}
      {stickyHeader && (
        <div className="border-b bg-muted/50">
          <table className="w-full table-fixed" role="presentation">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={cn(
                      "px-4 py-3 text-sm font-medium text-muted-foreground",
                      col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : "text-left",
                      col.sortable && "cursor-pointer hover:text-foreground select-none",
                      col.className
                    )}
                    style={{ width: col.width, minWidth: col.minWidth }}
                    onClick={col.sortable ? () => handleSort(col.key) : undefined}
                    onKeyDown={
                      col.sortable
                        ? (e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              handleSort(col.key);
                            }
                          }
                        : undefined
                    }
                    tabIndex={col.sortable ? 0 : undefined}
                    role={col.sortable ? "columnheader" : undefined}
                    aria-sort={
                      col.sortable && sortColumn === col.key
                        ? sortDirection === "asc"
                          ? "ascending"
                          : "descending"
                        : undefined
                    }
                  >
                    <span className="flex items-center gap-1">
                      {col.header}
                      {col.sortable && sortColumn === col.key && (
                        <span aria-hidden="true">
                          {sortDirection === "asc" ? "↑" : "↓"}
                        </span>
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
          </table>
        </div>
      )}

      {/* Virtualized body */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="overflow-auto"
        style={{ maxHeight }}
        role="grid"
        aria-label={ariaLabel}
        aria-rowcount={data.length}
      >
        <div style={{ height: totalHeight, position: "relative" }}>
          <table className="w-full table-fixed" role="presentation">
            <tbody>
              {visibleRows.map((row, i) => {
                const actualIndex = startIndex + i;
                const key = getRowKey
                  ? getRowKey(row, actualIndex)
                  : (row.id as string) ?? `row-${actualIndex}`;

                const rowCls =
                  typeof rowClassName === "function"
                    ? rowClassName(row, actualIndex)
                    : rowClassName;

                return (
                  <tr
                    key={key}
                    className={cn(
                      "border-b hover:bg-muted/50 transition-colors",
                      onRowClick && "cursor-pointer",
                      rowCls
                    )}
                    style={{
                      height: rowHeight,
                      position: "absolute",
                      top: actualIndex * rowHeight,
                      width: "100%",
                      display: "table-row",
                    }}
                    onClick={onRowClick ? () => onRowClick(row, actualIndex) : undefined}
                    onKeyDown={
                      onRowClick ? (e) => handleRowKeyDown(e, row, actualIndex) : undefined
                    }
                    tabIndex={onRowClick ? 0 : undefined}
                    role={onRowClick ? "link" : "row"}
                    aria-rowindex={actualIndex + 1}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={cn(
                          "px-4 py-2 text-sm truncate",
                          col.align === "right"
                            ? "text-right"
                            : col.align === "center"
                              ? "text-center"
                              : "text-left",
                          col.className
                        )}
                        style={{ width: col.width, minWidth: col.minWidth }}
                      >
                        {col.render
                          ? col.render(row[col.key], row, actualIndex)
                          : (row[col.key] as React.ReactNode) ?? "—"}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Row count footer */}
      <div className="border-t bg-muted/30 px-4 py-2 text-xs text-muted-foreground">
        {data.length.toLocaleString()} row{data.length !== 1 ? "s" : ""}
      </div>
    </div>
  );
}

export default VirtualTable;
