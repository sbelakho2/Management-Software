/**
 * Component Decomposition Pattern for Dashboard Pages.
 *
 * This module establishes the pattern for decomposing large
 * monolithic page components (like quality/page.tsx @ 3714 lines)
 * into manageable, testable sub-components.
 *
 * Pattern: Each tab or major section becomes its own component
 * in a `_components/` directory co-located with the page.
 *
 * Checklist items: #296, #297, #298, #445
 *
 * @example Directory Structure:
 * ```
 * quality/
 *   page.tsx                    ← Shell: tabs + routing only (~100 lines)
 *   _components/
 *     inspections-tab.tsx       ← Inspections table + dialogs
 *     ncr-tab.tsx               ← NCR table + dialogs
 *     capa-tab.tsx              ← CAPA table + dialogs
 *     msa-tab.tsx               ← MSA study forms + results
 *     capability-tab.tsx        ← Process capability analysis
 *     spc-tab.tsx               ← SPC charts
 *     gauge-management-tab.tsx  ← Gauge calibration
 *     audit-tab.tsx             ← Audit findings
 *     documents-tab.tsx         ← QMS documents
 *     risk-tab.tsx              ← Risk register
 *     complaints-tab.tsx        ← Customer complaints
 *     scars-tab.tsx             ← SCAR management
 *     shared/
 *       quality-table.tsx       ← Shared table wrapper
 *       quality-filters.tsx     ← Shared filter controls
 *       quality-dialog.tsx      ← Shared dialog wrapper
 * ```
 */

"use client";

import React, { Suspense, lazy, ComponentType } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

// ─── Types ───────────────────────────────────────────────────────

export interface TabDefinition {
  id: string;
  label: string;
  icon?: React.ReactNode;
  component: ComponentType;
  badge?: number;
  disabled?: boolean;
}

interface DecomposedPageProps {
  tabs: TabDefinition[];
  defaultTab?: string;
  className?: string;
  title?: string;
  actions?: React.ReactNode;
  onTabChange?: (tabId: string) => void;
}

// ─── Loading Fallback ────────────────────────────────────────────

function TabSkeleton() {
  return (
    <div className="space-y-4 p-4 animate-pulse" aria-label="Loading tab content">
      <div className="h-8 bg-muted rounded w-1/3" />
      <div className="h-4 bg-muted rounded w-2/3" />
      <div className="h-64 bg-muted rounded" />
    </div>
  );
}

// ─── Decomposed Page Shell ───────────────────────────────────────

/**
 * Shell component for decomposed dashboard pages.
 *
 * Renders a tab navigation with lazy-loaded tab content.
 * Each tab component is code-split for optimal bundle size.
 *
 * @example
 * ```tsx
 * // quality/page.tsx — now just ~30 lines
 * import { DecomposedPage } from "@/components/patterns/decomposed-page";
 * import InspectionsTab from "./_components/inspections-tab";
 * import NCRTab from "./_components/ncr-tab";
 *
 * export default function QualityPage() {
 *   return (
 *     <DecomposedPage
 *       title="Quality Management"
 *       defaultTab="inspections"
 *       tabs={[
 *         { id: "inspections", label: "Inspections", component: InspectionsTab },
 *         { id: "ncrs", label: "NCRs", component: NCRTab, badge: 5 },
 *       ]}
 *     />
 *   );
 * }
 * ```
 */
export function DecomposedPage({
  tabs,
  defaultTab,
  className,
  title,
  actions,
  onTabChange,
}: DecomposedPageProps) {
  const activeDefault = defaultTab || tabs[0]?.id || "";

  return (
    <div className={className}>
      {/* Page header */}
      {(title || actions) && (
        <div className="flex items-center justify-between mb-6">
          {title && <h1 className="text-2xl font-bold">{title}</h1>}
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}

      {/* Tab navigation */}
      <Tabs defaultValue={activeDefault} onValueChange={onTabChange}>
        <TabsList className="flex flex-wrap gap-1">
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              disabled={tab.disabled}
              className="flex items-center gap-2"
            >
              {tab.icon}
              {tab.label}
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="ml-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                  {tab.badge}
                </span>
              )}
            </TabsTrigger>
          ))}
        </TabsList>

        {tabs.map((tab) => (
          <TabsContent key={tab.id} value={tab.id}>
            <Suspense fallback={<TabSkeleton />}>
              <tab.component />
            </Suspense>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

/**
 * Helper to create a lazy-loaded tab component.
 *
 * @example
 * ```tsx
 * const InspectionsTab = lazyTab(() => import("./_components/inspections-tab"));
 * ```
 */
export function lazyTab<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>
): React.LazyExoticComponent<T> {
  return lazy(importFn);
}

export default DecomposedPage;
