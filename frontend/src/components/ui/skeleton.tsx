import { cn } from '@/lib/utils';

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('skeleton', className)}
      {...props}
    />
  );
}

function SkeletonText({
  lines = 3,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { lines?: number }) {
  return (
    <div className={cn('space-y-2', className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            'h-4',
            i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'
          )}
        />
      ))}
    </div>
  );
}

function SkeletonCard({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('rounded-rams-sm border border-rams-border bg-rams-module p-5', className)}
      {...props}
    >
      <div className="flex items-center space-x-4">
        <Skeleton className="h-10 w-10 rounded-rams-sm" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-3 w-1/3" />
          <Skeleton className="h-3 w-1/2 opacity-50" />
        </div>
      </div>
      <div className="mt-6 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-2/3 opacity-50" />
      </div>
    </div>
  );
}

function SkeletonTable({
  rows = 5,
  columns = 4,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  rows?: number;
  columns?: number;
}) {
  return (
    <div className={cn('w-full border border-rams-border rounded-rams-sm overflow-hidden', className)} {...props}>
      {/* Header */}
      <div className="flex gap-4 border-b border-rams-border bg-rams-panel p-4">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-2 flex-1 opacity-40" />
        ))}
      </div>
      {/* Rows */}
      <div className="bg-rams-module">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex gap-4 p-4 border-b border-rams-border/30 last:border-0">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton
                key={colIndex}
                className={cn(
                  'h-2 flex-1',
                  colIndex === 0 && 'w-1/4 flex-none'
                )}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function SkeletonList({
  items = 5,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { items?: number }) {
  return (
    <div className={cn('space-y-1', className)} {...props}>
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 p-3 bg-rams-module border border-rams-border/50 rounded-rams-sm">
          <Skeleton className="h-8 w-8 rounded-rams-sm" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-2 w-1/3" />
            <Skeleton className="h-2 w-1/2 opacity-50" />
          </div>
          <Skeleton className="h-6 w-16" />
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Page-Specific Skeleton Loaders
// =============================================================================

/**
 * Dashboard page skeleton with KPI cards and charts
 */
function SkeletonDashboard({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('space-y-6', className)} {...props} data-testid="skeleton-dashboard">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>

      {/* KPI cards row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border bg-card p-6">
            <div className="flex items-center justify-between mb-4">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-8 rounded" />
            </div>
            <Skeleton className="h-8 w-20 mb-2" />
            <Skeleton className="h-3 w-32" />
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg border bg-card p-6">
          <Skeleton className="h-6 w-40 mb-6" />
          <Skeleton className="h-64 w-full rounded" />
        </div>
        <div className="rounded-lg border bg-card p-6">
          <Skeleton className="h-6 w-40 mb-6" />
          <Skeleton className="h-64 w-full rounded" />
        </div>
      </div>

      {/* Activity and table section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-lg border bg-card p-6">
          <Skeleton className="h-6 w-32 mb-4" />
          <SkeletonTable rows={5} columns={4} />
        </div>
        <div className="rounded-lg border bg-card p-6">
          <Skeleton className="h-6 w-32 mb-4" />
          <SkeletonList items={5} />
        </div>
      </div>
    </div>
  );
}

/**
 * List page skeleton with header, filters, and table
 */
function SkeletonListPage({
  className,
  rows = 10,
  columns = 5,
  showFilters = true,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  rows?: number;
  columns?: number;
  showFilters?: boolean;
}) {
  return (
    <div className={cn('space-y-6', className)} {...props} data-testid="skeleton-list-page">
      {/* Page header with action button */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-4 w-60" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>

      {/* Search and filters */}
      {showFilters && (
        <div className="flex flex-col sm:flex-row gap-4">
          <Skeleton className="h-10 flex-1 max-w-md" />
          <div className="flex gap-2">
            <Skeleton className="h-10 w-28" />
            <Skeleton className="h-10 w-28" />
            <Skeleton className="h-10 w-10" />
          </div>
        </div>
      )}

      {/* Data table */}
      <div className="rounded-lg border bg-card p-6">
        <SkeletonTable rows={rows} columns={columns} />
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-40" />
        <div className="flex gap-2">
          <Skeleton className="h-10 w-10" />
          <Skeleton className="h-10 w-10" />
          <Skeleton className="h-10 w-10" />
          <Skeleton className="h-10 w-10" />
        </div>
      </div>
    </div>
  );
}

/**
 * Detail page skeleton with info panels and sections
 */
function SkeletonDetailPage({
  className,
  sections = 3,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  sections?: number;
}) {
  return (
    <div className={cn('space-y-6', className)} {...props} data-testid="skeleton-detail-page">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
      </div>

      {/* Page header with status and actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
          <Skeleton className="h-4 w-80" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-10" />
        </div>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border bg-card p-4">
            <Skeleton className="h-3 w-20 mb-2" />
            <Skeleton className="h-5 w-32" />
          </div>
        ))}
      </div>

      {/* Content sections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {Array.from({ length: sections }).map((_, i) => (
            <div key={i} className="rounded-lg border bg-card p-6">
              <Skeleton className="h-6 w-40 mb-4" />
              <SkeletonText lines={4} />
            </div>
          ))}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="rounded-lg border bg-card p-6">
            <Skeleton className="h-6 w-28 mb-4" />
            <div className="space-y-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-24 mb-1" />
                    <Skeleton className="h-3 w-16" />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-lg border bg-card p-6">
            <Skeleton className="h-6 w-24 mb-4" />
            <SkeletonList items={3} />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Form page skeleton with input fields and sections
 */
function SkeletonFormPage({
  className,
  fields = 6,
  sections = 2,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  fields?: number;
  sections?: number;
}) {
  return (
    <div className={cn('space-y-6', className)} {...props} data-testid="skeleton-form-page">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-24" />
        </div>
      </div>

      {/* Form sections */}
      {Array.from({ length: sections }).map((_, sectionIndex) => (
        <div key={sectionIndex} className="rounded-lg border bg-card p-6">
          <Skeleton className="h-6 w-40 mb-6" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Array.from({ length: Math.ceil(fields / sections) }).map((_, fieldIndex) => (
              <div key={fieldIndex} className="space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-10 w-full" />
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Form footer */}
      <div className="flex justify-end gap-4">
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-32" />
      </div>
    </div>
  );
}

/**
 * Kanban board skeleton with columns and cards
 */
function SkeletonKanban({
  className,
  columns = 4,
  cardsPerColumn = 3,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  columns?: number;
  cardsPerColumn?: number;
}) {
  return (
    <div className={cn('space-y-6', className)} {...props} data-testid="skeleton-kanban">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-40" />
        <div className="flex gap-2">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 w-10" />
        </div>
      </div>

      {/* Kanban columns */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {Array.from({ length: columns }).map((_, colIndex) => (
          <div key={colIndex} className="flex-shrink-0 w-72 bg-muted/50 rounded-lg p-3">
            {/* Column header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Skeleton className="h-5 w-24" />
                <Skeleton className="h-5 w-6 rounded-full" />
              </div>
              <Skeleton className="h-6 w-6" />
            </div>

            {/* Cards */}
            <div className="space-y-3">
              {Array.from({ length: cardsPerColumn }).map((_, cardIndex) => (
                <div key={cardIndex} className="rounded-lg border bg-card p-4 shadow-sm">
                  <Skeleton className="h-4 w-16 mb-2" />
                  <Skeleton className="h-5 w-full mb-3" />
                  <div className="flex items-center justify-between">
                    <div className="flex -space-x-2">
                      <Skeleton className="h-6 w-6 rounded-full" />
                      <Skeleton className="h-6 w-6 rounded-full" />
                    </div>
                    <Skeleton className="h-4 w-16" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Timeline skeleton for activity feeds
 */
function SkeletonTimeline({
  className,
  items = 5,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  items?: number;
}) {
  return (
    <div className={cn('space-y-1', className)} {...props} data-testid="skeleton-timeline">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex gap-4">
          {/* Timeline line and dot */}
          <div className="flex flex-col items-center">
            <Skeleton className="h-8 w-8 rounded-full" />
            {i < items - 1 && <Skeleton className="w-0.5 flex-1 min-h-[40px] bg-muted" />}
          </div>

          {/* Content */}
          <div className="pb-6 flex-1">
            <Skeleton className="h-4 w-3/4 mb-2" />
            <Skeleton className="h-3 w-1/2 mb-2" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Modal skeleton for loading dialogs
 */
function SkeletonModal({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('space-y-6 p-6', className)} {...props} data-testid="skeleton-modal">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-72" />
      </div>

      {/* Content */}
      <div className="space-y-4">
        <div className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-10 w-full" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-10 w-full" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>

      {/* Footer */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-32" />
      </div>
    </div>
  );
}

/**
 * Stats grid skeleton for metric displays
 */
function SkeletonStats({
  className,
  items = 4,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  items?: number;
}) {
  return (
    <div
      className={cn(
        'grid gap-4',
        items <= 2 ? 'grid-cols-1 md:grid-cols-2' :
        items <= 3 ? 'grid-cols-1 md:grid-cols-3' :
        'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
        className
      )}
      {...props}
      data-testid="skeleton-stats"
    >
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="rounded-lg border bg-card p-5">
          <div className="flex items-center justify-between mb-3">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-8 w-8 rounded" />
          </div>
          <Skeleton className="h-8 w-24 mb-2" />
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-12" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Profile/User detail skeleton
 */
function SkeletonProfile({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('space-y-6', className)} {...props} data-testid="skeleton-profile">
      {/* Profile header */}
      <div className="flex flex-col sm:flex-row items-center gap-6 p-6 rounded-lg border bg-card">
        <Skeleton className="h-24 w-24 rounded-full" />
        <div className="flex-1 text-center sm:text-left space-y-2">
          <Skeleton className="h-7 w-48 mx-auto sm:mx-0" />
          <Skeleton className="h-4 w-32 mx-auto sm:mx-0" />
          <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-10" />
        </div>
      </div>

      {/* Profile info grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-lg border bg-card p-6">
          <Skeleton className="h-5 w-32 mb-4" />
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex justify-between">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-32" />
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-lg border bg-card p-6">
          <Skeleton className="h-5 w-28 mb-4" />
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex justify-between">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-36" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonTable,
  SkeletonList,
  // Page-specific skeletons
  SkeletonDashboard,
  SkeletonListPage,
  SkeletonDetailPage,
  SkeletonFormPage,
  SkeletonKanban,
  SkeletonTimeline,
  SkeletonModal,
  SkeletonStats,
  SkeletonProfile,
};
