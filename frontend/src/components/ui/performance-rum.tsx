'use client';

import React, { createContext, useContext, useCallback, useEffect, useState, useRef, useMemo } from 'react';

// =============================================================================
// WEB VITALS CONSTANTS
// =============================================================================

/**
 * Core Web Vitals thresholds based on Google's recommendations
 * https://web.dev/vitals/
 */
export const WEB_VITALS_THRESHOLDS = {
  // Largest Contentful Paint (LCP) - loading performance
  LCP: {
    good: 2500, // ms
    needsImprovement: 4000, // ms
    unit: 'ms',
    description: 'Largest Contentful Paint - measures loading performance',
  },
  // First Input Delay (FID) - interactivity
  FID: {
    good: 100, // ms
    needsImprovement: 300, // ms
    unit: 'ms',
    description: 'First Input Delay - measures interactivity',
  },
  // Cumulative Layout Shift (CLS) - visual stability
  CLS: {
    good: 0.1,
    needsImprovement: 0.25,
    unit: '',
    description: 'Cumulative Layout Shift - measures visual stability',
  },
  // Interaction to Next Paint (INP) - responsiveness
  INP: {
    good: 200, // ms
    needsImprovement: 500, // ms
    unit: 'ms',
    description: 'Interaction to Next Paint - measures responsiveness',
  },
  // Time to First Byte (TTFB) - server response
  TTFB: {
    good: 800, // ms
    needsImprovement: 1800, // ms
    unit: 'ms',
    description: 'Time to First Byte - measures server response time',
  },
  // First Contentful Paint (FCP) - first content
  FCP: {
    good: 1800, // ms
    needsImprovement: 3000, // ms
    unit: 'ms',
    description: 'First Contentful Paint - measures first content rendered',
  },
} as const;

export type WebVitalName = keyof typeof WEB_VITALS_THRESHOLDS;

/**
 * Performance budget thresholds
 */
export const PERFORMANCE_BUDGETS = {
  // JavaScript bundle size per route
  jsBundle: {
    critical: 50 * 1024, // 50KB for critical path
    route: 200 * 1024, // 200KB per route
    total: 500 * 1024, // 500KB total
    unit: 'bytes',
  },
  // CSS bundle size
  cssBundle: {
    critical: 20 * 1024, // 20KB critical CSS
    total: 100 * 1024, // 100KB total
    unit: 'bytes',
  },
  // Image size limits
  images: {
    hero: 200 * 1024, // 200KB for hero images
    thumbnail: 50 * 1024, // 50KB for thumbnails
    icon: 10 * 1024, // 10KB for icons
    unit: 'bytes',
  },
  // Font loading
  fonts: {
    total: 100 * 1024, // 100KB total font weight
    perFamily: 50 * 1024, // 50KB per font family
    unit: 'bytes',
  },
  // Network requests
  requests: {
    initial: 10, // max 10 requests on initial load
    total: 50, // max 50 total requests
    unit: 'count',
  },
  // Interaction latency
  interaction: {
    buttonClick: 100, // 100ms max for button response
    formSubmit: 200, // 200ms max for form submission feedback
    navigation: 300, // 300ms max for navigation response
    unit: 'ms',
  },
} as const;

export type BudgetCategory = keyof typeof PERFORMANCE_BUDGETS;

// =============================================================================
// METRIC TYPES
// =============================================================================

export interface MetricValue {
  name: WebVitalName;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  timestamp: number;
  id: string;
  navigationType?: 'navigate' | 'reload' | 'back_forward' | 'prerender';
  entries?: PerformanceEntry[];
}

export interface InteractionMetric {
  id: string;
  type: 'click' | 'keydown' | 'pointerdown' | 'submit';
  target: string;
  latency: number;
  timestamp: number;
  rating: 'good' | 'needs-improvement' | 'poor';
}

export interface PerformanceSession {
  sessionId: string;
  startTime: number;
  route: string;
  metrics: MetricValue[];
  interactions: InteractionMetric[];
  resources: ResourceMetric[];
}

export interface ResourceMetric {
  name: string;
  type: 'script' | 'stylesheet' | 'image' | 'font' | 'document' | 'other';
  size: number;
  duration: number;
  timestamp: number;
}

export interface BudgetViolation {
  category: string;
  threshold: number;
  actual: number;
  unit: string;
  severity: 'warning' | 'error';
  message: string;
}

// =============================================================================
// METRIC COLLECTION
// =============================================================================

/**
 * Generates a unique ID for metrics
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Rates a metric value based on thresholds
 */
export function rateMetric(name: WebVitalName, value: number): 'good' | 'needs-improvement' | 'poor' {
  const thresholds = WEB_VITALS_THRESHOLDS[name];
  if (value <= thresholds.good) return 'good';
  if (value <= thresholds.needsImprovement) return 'needs-improvement';
  return 'poor';
}

/**
 * Rates an interaction latency
 */
export function rateInteraction(latency: number, type: InteractionMetric['type']): 'good' | 'needs-improvement' | 'poor' {
  const threshold = type === 'submit' 
    ? PERFORMANCE_BUDGETS.interaction.formSubmit 
    : PERFORMANCE_BUDGETS.interaction.buttonClick;
  
  if (latency <= threshold) return 'good';
  if (latency <= threshold * 2) return 'needs-improvement';
  return 'poor';
}

/**
 * Observes Largest Contentful Paint
 */
export function observeLCP(callback: (metric: MetricValue) => void): (() => void) | null {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
    return null;
  }

  try {
    let lastLCP: MetricValue | null = null;

    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1] as PerformanceEntry & { startTime: number };
      
      if (lastEntry) {
        lastLCP = {
          name: 'LCP',
          value: lastEntry.startTime,
          rating: rateMetric('LCP', lastEntry.startTime),
          timestamp: Date.now(),
          id: generateId(),
          entries: [lastEntry],
        };
        callback(lastLCP);
      }
    });

    observer.observe({ type: 'largest-contentful-paint', buffered: true });

    return () => observer.disconnect();
  } catch {
    return null;
  }
}

/**
 * Observes First Input Delay
 */
export function observeFID(callback: (metric: MetricValue) => void): (() => void) | null {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
    return null;
  }

  try {
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach((entry) => {
        const fidEntry = entry as PerformanceEntry & { processingStart: number; startTime: number };
        const value = fidEntry.processingStart - fidEntry.startTime;
        
        callback({
          name: 'FID',
          value,
          rating: rateMetric('FID', value),
          timestamp: Date.now(),
          id: generateId(),
          entries: [entry],
        });
      });
    });

    observer.observe({ type: 'first-input', buffered: true });

    return () => observer.disconnect();
  } catch {
    return null;
  }
}

/**
 * Observes Cumulative Layout Shift
 */
export function observeCLS(callback: (metric: MetricValue) => void): (() => void) | null {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
    return null;
  }

  try {
    let clsValue = 0;
    let clsEntries: PerformanceEntry[] = [];

    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const layoutShift = entry as PerformanceEntry & { hadRecentInput?: boolean; value?: number };
        
        if (!layoutShift.hadRecentInput && typeof layoutShift.value === 'number') {
          clsValue += layoutShift.value;
          clsEntries.push(entry);
          
          callback({
            name: 'CLS',
            value: clsValue,
            rating: rateMetric('CLS', clsValue),
            timestamp: Date.now(),
            id: generateId(),
            entries: [...clsEntries],
          });
        }
      }
    });

    observer.observe({ type: 'layout-shift', buffered: true });

    return () => observer.disconnect();
  } catch {
    return null;
  }
}

/**
 * Observes Interaction to Next Paint
 */
export function observeINP(callback: (metric: MetricValue) => void): (() => void) | null {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
    return null;
  }

  try {
    const interactions: number[] = [];

    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const eventEntry = entry as PerformanceEntry & { 
          interactionId?: number; 
          duration?: number;
        };
        
        if (eventEntry.interactionId && typeof eventEntry.duration === 'number') {
          interactions.push(eventEntry.duration);
          
          // INP is the 98th percentile of interactions
          const sortedInteractions = [...interactions].sort((a, b) => b - a);
          const p98Index = Math.floor(sortedInteractions.length * 0.02);
          const inp = sortedInteractions[p98Index] || sortedInteractions[0];
          
          callback({
            name: 'INP',
            value: inp,
            rating: rateMetric('INP', inp),
            timestamp: Date.now(),
            id: generateId(),
          });
        }
      }
    });

    observer.observe({ type: 'event', buffered: true });

    return () => observer.disconnect();
  } catch {
    return null;
  }
}

/**
 * Gets Time to First Byte from navigation timing
 */
export function getTTFB(): MetricValue | null {
  if (typeof window === 'undefined' || !window.performance) {
    return null;
  }

  try {
    const navEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    
    if (navEntry) {
      const value = navEntry.responseStart - navEntry.requestStart;
      return {
        name: 'TTFB',
        value,
        rating: rateMetric('TTFB', value),
        timestamp: Date.now(),
        id: generateId(),
        navigationType: navEntry.type as MetricValue['navigationType'],
      };
    }
  } catch {
    // Navigation timing not available
  }
  
  return null;
}

/**
 * Gets First Contentful Paint
 */
export function getFCP(): MetricValue | null {
  if (typeof window === 'undefined' || !window.performance) {
    return null;
  }

  try {
    const paintEntries = performance.getEntriesByType('paint');
    const fcpEntry = paintEntries.find(entry => entry.name === 'first-contentful-paint');
    
    if (fcpEntry) {
      return {
        name: 'FCP',
        value: fcpEntry.startTime,
        rating: rateMetric('FCP', fcpEntry.startTime),
        timestamp: Date.now(),
        id: generateId(),
      };
    }
  } catch {
    // Paint timing not available
  }
  
  return null;
}

/**
 * Observes resource loading
 */
export function observeResources(callback: (resource: ResourceMetric) => void): (() => void) | null {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
    return null;
  }

  try {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const resourceEntry = entry as PerformanceResourceTiming;
        
        let type: ResourceMetric['type'] = 'other';
        if (resourceEntry.initiatorType === 'script') type = 'script';
        else if (resourceEntry.initiatorType === 'css' || resourceEntry.initiatorType === 'link') type = 'stylesheet';
        else if (resourceEntry.initiatorType === 'img') type = 'image';
        else if (entry.name.includes('.woff') || entry.name.includes('.ttf')) type = 'font';
        
        callback({
          name: entry.name,
          type,
          size: resourceEntry.transferSize || 0,
          duration: resourceEntry.duration,
          timestamp: Date.now(),
        });
      }
    });

    observer.observe({ type: 'resource', buffered: true });

    return () => observer.disconnect();
  } catch {
    return null;
  }
}

// =============================================================================
// INTERACTION TRACKING
// =============================================================================

/**
 * Creates an interaction tracker for measuring button/form latency
 */
export function createInteractionTracker() {
  const pendingInteractions = new Map<string, { startTime: number; type: InteractionMetric['type']; target: string }>();

  const startInteraction = (id: string, type: InteractionMetric['type'], target: string): void => {
    pendingInteractions.set(id, {
      startTime: performance.now(),
      type,
      target,
    });
  };

  const endInteraction = (id: string): InteractionMetric | null => {
    const interaction = pendingInteractions.get(id);
    if (!interaction) return null;

    pendingInteractions.delete(id);
    const latency = performance.now() - interaction.startTime;

    return {
      id,
      type: interaction.type,
      target: interaction.target,
      latency,
      timestamp: Date.now(),
      rating: rateInteraction(latency, interaction.type),
    };
  };

  const cancelInteraction = (id: string): void => {
    pendingInteractions.delete(id);
  };

  return {
    startInteraction,
    endInteraction,
    cancelInteraction,
  };
}

// =============================================================================
// RUM CONTEXT
// =============================================================================

export interface RUMContextValue {
  // Current metrics
  metrics: Record<WebVitalName, MetricValue | null>;
  interactions: InteractionMetric[];
  resources: ResourceMetric[];
  
  // Session info
  sessionId: string;
  route: string;
  
  // Actions
  trackInteraction: (type: InteractionMetric['type'], target: string) => string;
  completeInteraction: (id: string) => InteractionMetric | null;
  cancelInteraction: (id: string) => void;
  
  // Budget checking
  checkBudgets: () => BudgetViolation[];
  
  // Reporting
  getReport: () => PerformanceSession;
}

const RUMContext = createContext<RUMContextValue | null>(null);

export interface RUMProviderProps {
  children: React.ReactNode;
  route?: string;
  onMetric?: (metric: MetricValue) => void;
  onInteraction?: (interaction: InteractionMetric) => void;
  onViolation?: (violation: BudgetViolation) => void;
}

export function RUMProvider({
  children,
  route = '/',
  onMetric,
  onInteraction,
  onViolation,
}: RUMProviderProps) {
  const sessionId = useMemo(() => generateId(), []);
  const [metrics, setMetrics] = useState<Record<WebVitalName, MetricValue | null>>({
    LCP: null,
    FID: null,
    CLS: null,
    INP: null,
    TTFB: null,
    FCP: null,
  });
  const [interactions, setInteractions] = useState<InteractionMetric[]>([]);
  const [resources, setResources] = useState<ResourceMetric[]>([]);
  
  const trackerRef = useRef(createInteractionTracker());

  // Initialize observers
  useEffect(() => {
    const cleanups: ((() => void) | null)[] = [];

    const handleMetric = (metric: MetricValue) => {
      setMetrics(prev => ({ ...prev, [metric.name]: metric }));
      onMetric?.(metric);
    };

    // Observe Core Web Vitals
    cleanups.push(observeLCP(handleMetric));
    cleanups.push(observeFID(handleMetric));
    cleanups.push(observeCLS(handleMetric));
    cleanups.push(observeINP(handleMetric));

    // Get initial metrics
    const ttfb = getTTFB();
    if (ttfb) handleMetric(ttfb);
    
    const fcp = getFCP();
    if (fcp) handleMetric(fcp);

    // Observe resources
    cleanups.push(observeResources((resource) => {
      setResources(prev => [...prev, resource]);
    }));

    return () => {
      cleanups.forEach(cleanup => cleanup?.());
    };
  }, [onMetric]);

  const trackInteraction = useCallback((type: InteractionMetric['type'], target: string): string => {
    const id = generateId();
    trackerRef.current.startInteraction(id, type, target);
    return id;
  }, []);

  const completeInteraction = useCallback((id: string): InteractionMetric | null => {
    const interaction = trackerRef.current.endInteraction(id);
    if (interaction) {
      setInteractions(prev => [...prev, interaction]);
      onInteraction?.(interaction);
      
      // Check for budget violation
      if (interaction.rating === 'poor') {
        const violation: BudgetViolation = {
          category: 'interaction',
          threshold: PERFORMANCE_BUDGETS.interaction.buttonClick,
          actual: interaction.latency,
          unit: 'ms',
          severity: 'warning',
          message: `Interaction "${interaction.target}" exceeded latency budget (${interaction.latency.toFixed(0)}ms > ${PERFORMANCE_BUDGETS.interaction.buttonClick}ms)`,
        };
        onViolation?.(violation);
      }
    }
    return interaction;
  }, [onInteraction, onViolation]);

  const cancelInteraction = useCallback((id: string): void => {
    trackerRef.current.cancelInteraction(id);
  }, []);

  const checkBudgets = useCallback((): BudgetViolation[] => {
    const violations: BudgetViolation[] = [];

    // Check JS bundle size
    const jsResources = resources.filter(r => r.type === 'script');
    const totalJsSize = jsResources.reduce((sum, r) => sum + r.size, 0);
    if (totalJsSize > PERFORMANCE_BUDGETS.jsBundle.total) {
      violations.push({
        category: 'jsBundle.total',
        threshold: PERFORMANCE_BUDGETS.jsBundle.total,
        actual: totalJsSize,
        unit: 'bytes',
        severity: 'error',
        message: `Total JS bundle size exceeds budget (${(totalJsSize / 1024).toFixed(0)}KB > ${(PERFORMANCE_BUDGETS.jsBundle.total / 1024).toFixed(0)}KB)`,
      });
    }

    // Check CSS bundle size
    const cssResources = resources.filter(r => r.type === 'stylesheet');
    const totalCssSize = cssResources.reduce((sum, r) => sum + r.size, 0);
    if (totalCssSize > PERFORMANCE_BUDGETS.cssBundle.total) {
      violations.push({
        category: 'cssBundle.total',
        threshold: PERFORMANCE_BUDGETS.cssBundle.total,
        actual: totalCssSize,
        unit: 'bytes',
        severity: 'warning',
        message: `Total CSS bundle size exceeds budget (${(totalCssSize / 1024).toFixed(0)}KB > ${(PERFORMANCE_BUDGETS.cssBundle.total / 1024).toFixed(0)}KB)`,
      });
    }

    // Check request count
    if (resources.length > PERFORMANCE_BUDGETS.requests.initial) {
      violations.push({
        category: 'requests.initial',
        threshold: PERFORMANCE_BUDGETS.requests.initial,
        actual: resources.length,
        unit: 'count',
        severity: 'warning',
        message: `Initial request count exceeds budget (${resources.length} > ${PERFORMANCE_BUDGETS.requests.initial})`,
      });
    }

    // Check Core Web Vitals
    if (metrics.LCP && metrics.LCP.rating === 'poor') {
      violations.push({
        category: 'LCP',
        threshold: WEB_VITALS_THRESHOLDS.LCP.good,
        actual: metrics.LCP.value,
        unit: 'ms',
        severity: 'error',
        message: `LCP is poor (${metrics.LCP.value.toFixed(0)}ms > ${WEB_VITALS_THRESHOLDS.LCP.needsImprovement}ms)`,
      });
    }

    if (metrics.CLS && metrics.CLS.rating === 'poor') {
      violations.push({
        category: 'CLS',
        threshold: WEB_VITALS_THRESHOLDS.CLS.good,
        actual: metrics.CLS.value,
        unit: '',
        severity: 'error',
        message: `CLS is poor (${metrics.CLS.value.toFixed(3)} > ${WEB_VITALS_THRESHOLDS.CLS.needsImprovement})`,
      });
    }

    return violations;
  }, [resources, metrics]);

  const getReport = useCallback((): PerformanceSession => {
    return {
      sessionId,
      startTime: Date.now(),
      route,
      metrics: Object.values(metrics).filter((m): m is MetricValue => m !== null),
      interactions,
      resources,
    };
  }, [sessionId, route, metrics, interactions, resources]);

  const value = useMemo<RUMContextValue>(() => ({
    metrics,
    interactions,
    resources,
    sessionId,
    route,
    trackInteraction,
    completeInteraction,
    cancelInteraction,
    checkBudgets,
    getReport,
  }), [metrics, interactions, resources, sessionId, route, trackInteraction, completeInteraction, cancelInteraction, checkBudgets, getReport]);

  return <RUMContext.Provider value={value}>{children}</RUMContext.Provider>;
}

export function useRUM(): RUMContextValue {
  const context = useContext(RUMContext);
  if (!context) {
    throw new Error('useRUM must be used within a RUMProvider');
  }
  return context;
}

// =============================================================================
// METRIC DISPLAY COMPONENTS
// =============================================================================

export interface WebVitalCardProps {
  name: WebVitalName;
  value: number | null;
  rating?: 'good' | 'needs-improvement' | 'poor';
  showThresholds?: boolean;
  className?: string;
}

export function WebVitalCard({
  name,
  value,
  rating,
  showThresholds = false,
  className = '',
}: WebVitalCardProps) {
  const thresholds = WEB_VITALS_THRESHOLDS[name];
  const actualRating = rating || (value !== null ? rateMetric(name, value) : 'good');

  const ratingColors = {
    good: 'bg-success/10 text-success border-success/20',
    'needs-improvement': 'bg-warning/10 text-warning border-warning/20',
    poor: 'bg-destructive/10 text-destructive border-destructive/20',
  };

  const ratingIcons = {
    good: '✓',
    'needs-improvement': '!',
    poor: '✗',
  };

  const formatValue = (v: number): string => {
    if (name === 'CLS') return v.toFixed(3);
    return `${v.toFixed(0)}${thresholds.unit}`;
  };

  return (
    <div className={`p-4 rounded-lg border ${ratingColors[actualRating]} ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">{name}</span>
        <span className="text-lg">{ratingIcons[actualRating]}</span>
      </div>
      
      <div className="text-2xl font-bold mb-1">
        {value !== null ? formatValue(value) : '—'}
      </div>
      
      <p className="text-xs opacity-75 mb-2">{thresholds.description}</p>
      
      {showThresholds && (
        <div className="text-xs space-y-1 pt-2 border-t border-current/10">
          <div className="flex justify-between">
            <span>Good:</span>
            <span>≤ {thresholds.good}{thresholds.unit}</span>
          </div>
          <div className="flex justify-between">
            <span>Needs improvement:</span>
            <span>≤ {thresholds.needsImprovement}{thresholds.unit}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export interface WebVitalsDashboardProps {
  showThresholds?: boolean;
  className?: string;
}

export function WebVitalsDashboard({ showThresholds = false, className = '' }: WebVitalsDashboardProps) {
  const { metrics } = useRUM();

  return (
    <div className={`grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 ${className}`}>
      {(Object.keys(WEB_VITALS_THRESHOLDS) as WebVitalName[]).map((name) => (
        <WebVitalCard
          key={name}
          name={name}
          value={metrics[name]?.value ?? null}
          rating={metrics[name]?.rating}
          showThresholds={showThresholds}
        />
      ))}
    </div>
  );
}

export interface InteractionLatencyListProps {
  maxItems?: number;
  showPoorOnly?: boolean;
  className?: string;
}

export function InteractionLatencyList({
  maxItems = 10,
  showPoorOnly = false,
  className = '',
}: InteractionLatencyListProps) {
  const { interactions } = useRUM();

  const filteredInteractions = showPoorOnly
    ? interactions.filter(i => i.rating === 'poor')
    : interactions;

  const displayInteractions = filteredInteractions.slice(-maxItems).reverse();

  const ratingColors = {
    good: 'text-success',
    'needs-improvement': 'text-warning',
    poor: 'text-destructive',
  };

  if (displayInteractions.length === 0) {
    return (
      <div className={`p-4 text-center text-muted-foreground ${className}`}>
        No interactions recorded yet
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {displayInteractions.map((interaction) => (
        <div
          key={interaction.id}
          className="flex items-center justify-between p-2 rounded bg-muted/50"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs bg-secondary px-2 py-0.5 rounded">
              {interaction.type}
            </span>
            <span className="text-sm truncate max-w-48">{interaction.target}</span>
          </div>
          <span className={`font-mono text-sm ${ratingColors[interaction.rating]}`}>
            {interaction.latency.toFixed(0)}ms
          </span>
        </div>
      ))}
    </div>
  );
}

export interface BudgetViolationAlertProps {
  violations: BudgetViolation[];
  onDismiss?: (index: number) => void;
  className?: string;
}

export function BudgetViolationAlert({
  violations,
  onDismiss,
  className = '',
}: BudgetViolationAlertProps) {
  if (violations.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {violations.map((violation, index) => (
        <div
          key={`${violation.category}-${index}`}
          className={`p-3 rounded-lg flex items-start gap-3 ${
            violation.severity === 'error'
              ? 'bg-destructive/10 text-destructive'
              : 'bg-warning/10 text-warning'
          }`}
          role="alert"
        >
          <span className="text-lg mt-0.5">
            {violation.severity === 'error' ? '⚠' : '!'}
          </span>
          <div className="flex-1">
            <p className="text-sm font-medium">{violation.message}</p>
            <p className="text-xs opacity-75 mt-1">
              Threshold: {violation.threshold} {violation.unit} | Actual: {violation.actual.toFixed(0)} {violation.unit}
            </p>
          </div>
          {onDismiss && (
            <button
              onClick={() => onDismiss(index)}
              className="p-1 hover:opacity-75"
              aria-label="Dismiss violation"
            >
              ✕
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// PERFORMANCE BUDGET DISPLAY
// =============================================================================

export interface PerformanceBudgetMeterProps {
  label: string;
  current: number;
  budget: number;
  unit: string;
  formatValue?: (value: number) => string;
  className?: string;
}

export function PerformanceBudgetMeter({
  label,
  current,
  budget,
  unit,
  formatValue = (v) => v.toString(),
  className = '',
}: PerformanceBudgetMeterProps) {
  const percentage = Math.min((current / budget) * 100, 100);
  const isOverBudget = current > budget;

  const getColor = () => {
    if (isOverBudget) return 'bg-destructive';
    if (percentage > 80) return 'bg-warning';
    return 'bg-success';
  };

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className={isOverBudget ? 'text-destructive' : 'text-muted-foreground'}>
          {formatValue(current)} / {formatValue(budget)} {unit}
        </span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${getColor()}`}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={current}
          aria-valuemin={0}
          aria-valuemax={budget}
          aria-label={`${label}: ${percentage.toFixed(0)}% of budget`}
        />
      </div>
    </div>
  );
}

export interface ResourceBudgetDashboardProps {
  className?: string;
}

export function ResourceBudgetDashboard({ className = '' }: ResourceBudgetDashboardProps) {
  const { resources } = useRUM();

  const jsSize = resources
    .filter(r => r.type === 'script')
    .reduce((sum, r) => sum + r.size, 0);

  const cssSize = resources
    .filter(r => r.type === 'stylesheet')
    .reduce((sum, r) => sum + r.size, 0);

  const imageSize = resources
    .filter(r => r.type === 'image')
    .reduce((sum, r) => sum + r.size, 0);

  const fontSize = resources
    .filter(r => r.type === 'font')
    .reduce((sum, r) => sum + r.size, 0);

  const formatBytes = (bytes: number): string => {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)}KB`;
    return `${bytes}B`;
  };

  return (
    <div className={`space-y-4 ${className}`}>
      <PerformanceBudgetMeter
        label="JavaScript"
        current={jsSize}
        budget={PERFORMANCE_BUDGETS.jsBundle.total}
        unit=""
        formatValue={formatBytes}
      />
      <PerformanceBudgetMeter
        label="CSS"
        current={cssSize}
        budget={PERFORMANCE_BUDGETS.cssBundle.total}
        unit=""
        formatValue={formatBytes}
      />
      <PerformanceBudgetMeter
        label="Images"
        current={imageSize}
        budget={PERFORMANCE_BUDGETS.images.hero * 5} // Assume max 5 hero-sized images
        unit=""
        formatValue={formatBytes}
      />
      <PerformanceBudgetMeter
        label="Fonts"
        current={fontSize}
        budget={PERFORMANCE_BUDGETS.fonts.total}
        unit=""
        formatValue={formatBytes}
      />
      <PerformanceBudgetMeter
        label="Requests"
        current={resources.length}
        budget={PERFORMANCE_BUDGETS.requests.initial}
        unit=""
      />
    </div>
  );
}

// =============================================================================
// TRACKED BUTTON COMPONENT
// =============================================================================

export interface TrackedButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  trackingName?: string;
  variant?: 'default' | 'primary' | 'secondary' | 'destructive' | 'ghost' | 'outline';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

export function TrackedButton({
  children,
  onClick,
  trackingName,
  variant = 'default',
  size = 'default',
  className = '',
  ...props
}: TrackedButtonProps) {
  const { trackInteraction, completeInteraction } = useRUM();
  const interactionIdRef = useRef<string | null>(null);

  const handleMouseDown = () => {
    const name = trackingName || (typeof children === 'string' ? children : 'button');
    interactionIdRef.current = trackInteraction('click', name);
  };

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (interactionIdRef.current) {
      completeInteraction(interactionIdRef.current);
      interactionIdRef.current = null;
    }
    onClick?.(e);
  };

  const variantClasses = {
    default: 'bg-muted text-foreground hover:bg-muted/80',
    primary: 'bg-primary text-primary-foreground hover:opacity-90',
    secondary: 'bg-secondary text-secondary-foreground hover:opacity-90',
    destructive: 'bg-destructive text-destructive-foreground hover:opacity-90',
    ghost: 'hover:bg-accent/80 hover:text-accent-foreground',
    outline: 'border border-input bg-background/50 shadow-sm hover:bg-accent hover:text-accent-foreground',
  };

  const sizeClasses = {
    default: 'px-4 py-2',
    sm: 'px-3 py-1.5 text-sm',
    lg: 'px-6 py-3 text-lg',
    icon: 'p-2',
  };

  return (
    <button
      onMouseDown={handleMouseDown}
      onClick={handleClick}
      className={`rounded-md font-medium transition-all ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

// =============================================================================
// RUM DASHBOARD PANEL
// =============================================================================

export interface RUMDashboardPanelProps {
  position?: 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right';
  defaultOpen?: boolean;
  className?: string;
}

export function RUMDashboardPanel({
  position = 'bottom-right',
  defaultOpen = false,
  className = '',
}: RUMDashboardPanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [activeTab, setActiveTab] = useState<'vitals' | 'interactions' | 'resources'>('vitals');
  const { checkBudgets } = useRUM();
  const [violations, setViolations] = useState<BudgetViolation[]>([]);

  useEffect(() => {
    if (isOpen) {
      const newViolations = checkBudgets();
      setViolations(newViolations);
    }
  }, [isOpen, checkBudgets]);

  const positionClasses = {
    'bottom-left': 'bottom-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'top-left': 'top-4 left-4',
    'top-right': 'top-4 right-4',
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className={`fixed ${positionClasses[position]} z-50 px-3 py-2 bg-primary text-primary-foreground rounded-lg shadow-lg hover:opacity-90 transition-opacity flex items-center gap-2 ${className}`}
        aria-label="Open performance dashboard"
      >
        <span>📊</span>
        <span className="text-sm font-medium">RUM</span>
        {violations.length > 0 && (
          <span className="w-5 h-5 bg-destructive text-destructive-foreground rounded-full text-xs flex items-center justify-center">
            {violations.length}
          </span>
        )}
      </button>
    );
  }

  return (
    <div
      className={`fixed ${positionClasses[position]} z-50 w-[480px] max-h-[80vh] bg-card border border-border rounded-lg shadow-xl overflow-hidden ${className}`}
      role="dialog"
      aria-label="Performance Dashboard"
    >
      <div className="flex items-center justify-between p-4 border-b border-border">
        <h2 className="text-lg font-semibold">Performance Dashboard</h2>
        <button
          onClick={() => setIsOpen(false)}
          className="p-1 hover:bg-muted rounded"
          aria-label="Close dashboard"
        >
          ✕
        </button>
      </div>

      {violations.length > 0 && (
        <div className="px-4 py-2 border-b border-border">
          <BudgetViolationAlert
            violations={violations}
            onDismiss={(index) => {
              setViolations(prev => prev.filter((_, i) => i !== index));
            }}
          />
        </div>
      )}

      <div className="flex border-b border-border">
        {(['vitals', 'interactions', 'resources'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-muted text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab === 'vitals' && '📈 Vitals'}
            {tab === 'interactions' && '🖱️ Interactions'}
            {tab === 'resources' && '📦 Resources'}
          </button>
        ))}
      </div>

      <div className="p-4 overflow-y-auto max-h-[50vh]">
        {activeTab === 'vitals' && (
          <WebVitalsDashboard showThresholds className="grid-cols-2 md:grid-cols-3" />
        )}
        {activeTab === 'interactions' && <InteractionLatencyList maxItems={15} />}
        {activeTab === 'resources' && <ResourceBudgetDashboard />}
      </div>
    </div>
  );
}

// =============================================================================
// PERFORMANCE REPORTING UTILITIES
// =============================================================================

export interface PerformanceReportOptions {
  includeResources?: boolean;
  includeInteractions?: boolean;
  format?: 'json' | 'console' | 'beacon';
}

/**
 * Formats a performance report for logging
 */
export function formatPerformanceReport(
  session: PerformanceSession,
  options: PerformanceReportOptions = {}
): string {
  const { includeResources = false, includeInteractions = true } = options;

  let report = `
═══════════════════════════════════════════════════════════
                    PERFORMANCE REPORT
═══════════════════════════════════════════════════════════
Session ID: ${session.sessionId}
Route: ${session.route}
Timestamp: ${new Date(session.startTime).toISOString()}

─────────────────── CORE WEB VITALS ───────────────────────
`;

  session.metrics.forEach(metric => {
    const thresholds = WEB_VITALS_THRESHOLDS[metric.name];
    const unit = thresholds.unit;
    const icon = metric.rating === 'good' ? '✓' : metric.rating === 'needs-improvement' ? '!' : '✗';
    report += `${icon} ${metric.name.padEnd(6)}: ${metric.value.toFixed(metric.name === 'CLS' ? 3 : 0)}${unit} (${metric.rating})\n`;
  });

  if (includeInteractions && session.interactions.length > 0) {
    report += `
─────────────────── INTERACTIONS ──────────────────────────
`;
    const poorInteractions = session.interactions.filter(i => i.rating === 'poor');
    report += `Total: ${session.interactions.length} | Poor: ${poorInteractions.length}\n`;
    
    poorInteractions.slice(0, 5).forEach(interaction => {
      report += `  ✗ ${interaction.target}: ${interaction.latency.toFixed(0)}ms\n`;
    });
  }

  if (includeResources) {
    report += `
─────────────────── RESOURCES ─────────────────────────────
`;
    const byType = session.resources.reduce((acc, r) => {
      acc[r.type] = (acc[r.type] || 0) + r.size;
      return acc;
    }, {} as Record<string, number>);

    Object.entries(byType).forEach(([type, size]) => {
      report += `  ${type}: ${(size / 1024).toFixed(0)}KB\n`;
    });
  }

  report += `
═══════════════════════════════════════════════════════════
`;

  return report;
}

/**
 * Sends performance data to an analytics endpoint
 */
export async function sendPerformanceBeacon(
  session: PerformanceSession,
  endpoint: string
): Promise<boolean> {
  if (typeof navigator === 'undefined' || !navigator.sendBeacon) {
    return false;
  }

  try {
    const data = JSON.stringify({
      ...session,
      timestamp: Date.now(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    });

    return navigator.sendBeacon(endpoint, data);
  } catch {
    return false;
  }
}

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Hook to track a specific interaction
 */
export function useInteractionTracking(name: string) {
  const { trackInteraction, completeInteraction, cancelInteraction } = useRUM();
  const idRef = useRef<string | null>(null);

  const start = useCallback(() => {
    idRef.current = trackInteraction('click', name);
  }, [trackInteraction, name]);

  const complete = useCallback(() => {
    if (idRef.current) {
      const result = completeInteraction(idRef.current);
      idRef.current = null;
      return result;
    }
    return null;
  }, [completeInteraction]);

  const cancel = useCallback(() => {
    if (idRef.current) {
      cancelInteraction(idRef.current);
      idRef.current = null;
    }
  }, [cancelInteraction]);

  return { start, complete, cancel };
}

/**
 * Hook to get performance budget status
 */
export function usePerformanceBudget() {
  const { checkBudgets, resources, metrics } = useRUM();
  const [violations, setViolations] = useState<BudgetViolation[]>([]);

  useEffect(() => {
    const newViolations = checkBudgets();
    setViolations(newViolations);
  }, [checkBudgets, resources, metrics]);

  const isWithinBudget = violations.length === 0;
  const errorCount = violations.filter(v => v.severity === 'error').length;
  const warningCount = violations.filter(v => v.severity === 'warning').length;

  return {
    violations,
    isWithinBudget,
    errorCount,
    warningCount,
  };
}

// =============================================================================
// EXPORTS
// =============================================================================

export { RUMContext };
