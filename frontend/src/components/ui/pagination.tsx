"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Standardized Pagination component (#442).
 *
 * Usage:
 *   <Pagination
 *     currentPage={page}
 *     totalPages={totalPages}
 *     onPageChange={setPage}
 *   />
 */

export interface PaginationProps {
  /** 1-based current page number */
  currentPage: number;
  /** Total number of pages */
  totalPages: number;
  /** Called when user changes page */
  onPageChange: (page: number) => void;
  /** Number of page buttons to show around current page */
  siblingCount?: number;
  /** Optional className for root container */
  className?: string;
  /** Show first/last buttons */
  showBoundaryPages?: boolean;
  /** Show page size selector */
  pageSizeOptions?: number[];
  /** Current page size */
  pageSize?: number;
  /** Called when page size changes */
  onPageSizeChange?: (size: number) => void;
  /** Total item count (for display) */
  totalItems?: number;
}

function generatePageNumbers(
  current: number,
  total: number,
  siblings: number,
): (number | "...")[] {
  const pages: (number | "...")[] = [];

  const rangeStart = Math.max(2, current - siblings);
  const rangeEnd = Math.min(total - 1, current + siblings);

  // Always show first page
  pages.push(1);

  // Left ellipsis
  if (rangeStart > 2) {
    pages.push("...");
  }

  // Middle pages
  for (let i = rangeStart; i <= rangeEnd; i++) {
    pages.push(i);
  }

  // Right ellipsis
  if (rangeEnd < total - 1) {
    pages.push("...");
  }

  // Always show last page (if > 1)
  if (total > 1) {
    pages.push(total);
  }

  return pages;
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  siblingCount = 1,
  className,
  showBoundaryPages = true,
  pageSizeOptions,
  pageSize,
  onPageSizeChange,
  totalItems,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const pages = generatePageNumbers(currentPage, totalPages, siblingCount);

  const canGoPrev = currentPage > 1;
  const canGoNext = currentPage < totalPages;

  return (
    <nav
      role="navigation"
      aria-label="Pagination"
      className={cn("flex items-center justify-between gap-4 py-4", className)}
    >
      {/* Item count */}
      {totalItems !== undefined && (
        <p className="text-sm text-muted-foreground whitespace-nowrap">
          {totalItems.toLocaleString()} item{totalItems !== 1 ? "s" : ""}
        </p>
      )}

      <div className="flex items-center gap-1">
        {/* First page */}
        {showBoundaryPages && (
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={!canGoPrev}
            onClick={() => onPageChange(1)}
            aria-label="Go to first page"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
        )}

        {/* Previous */}
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          disabled={!canGoPrev}
          onClick={() => onPageChange(currentPage - 1)}
          aria-label="Go to previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        {/* Page numbers */}
        {pages.map((page, idx) =>
          page === "..." ? (
            <span
              key={`ellipsis-${idx}`}
              className="px-2 text-sm text-muted-foreground"
              aria-hidden
            >
              …
            </span>
          ) : (
            <Button
              key={page}
              variant={page === currentPage ? "default" : "outline"}
              size="icon"
              className="h-8 w-8 text-xs"
              onClick={() => onPageChange(page)}
              aria-label={`Page ${page}`}
              aria-current={page === currentPage ? "page" : undefined}
            >
              {page}
            </Button>
          ),
        )}

        {/* Next */}
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          disabled={!canGoNext}
          onClick={() => onPageChange(currentPage + 1)}
          aria-label="Go to next page"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>

        {/* Last page */}
        {showBoundaryPages && (
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={!canGoNext}
            onClick={() => onPageChange(totalPages)}
            aria-label="Go to last page"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Page size selector */}
      {pageSizeOptions && onPageSizeChange && (
        <div className="flex items-center gap-2">
          <label htmlFor="page-size" className="text-sm text-muted-foreground whitespace-nowrap">
            Rows:
          </label>
          <select
            id="page-size"
            value={pageSize}
            onChange={(e) => {
              onPageSizeChange(Number(e.target.value));
              onPageChange(1); // Reset to first page
            }}
            className="h-8 rounded-md border border-input bg-background px-2 text-sm"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </div>
      )}
    </nav>
  );
}
