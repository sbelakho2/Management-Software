'use client';

import React, { createContext, useContext, useState, useCallback, useMemo, useEffect, useRef } from 'react';

// =============================================================================
// MATURITY LEVEL DEFINITIONS
// =============================================================================

/**
 * Deployment maturity levels as defined in Section 18.15
 * Each level unlocks progressively more features
 */
export const MATURITY_LEVELS = {
  LEVEL_0: 0, // Pre-Deployment
  LEVEL_1: 1, // Basic Operations
  LEVEL_2: 2, // Standard Operations
  LEVEL_3: 3, // Advanced Operations
  LEVEL_4: 4, // Full TPS
} as const;

export type MaturityLevel = typeof MATURITY_LEVELS[keyof typeof MATURITY_LEVELS];

export const MATURITY_LEVEL_NAMES: Record<MaturityLevel, string> = {
  [MATURITY_LEVELS.LEVEL_0]: 'Pre-Deployment',
  [MATURITY_LEVELS.LEVEL_1]: 'Basic Operations',
  [MATURITY_LEVELS.LEVEL_2]: 'Standard Operations',
  [MATURITY_LEVELS.LEVEL_3]: 'Advanced Operations',
  [MATURITY_LEVELS.LEVEL_4]: 'Full TPS',
};

export const MATURITY_LEVEL_DESCRIPTIONS: Record<MaturityLevel, string> = {
  [MATURITY_LEVELS.LEVEL_0]: 'Initial configuration and deployment setup',
  [MATURITY_LEVELS.LEVEL_1]: 'Basic sales and customer management',
  [MATURITY_LEVELS.LEVEL_2]: 'Standard production workflows and scheduling',
  [MATURITY_LEVELS.LEVEL_3]: 'Advanced TPS capabilities and continuous improvement',
  [MATURITY_LEVELS.LEVEL_4]: 'Full TPS with executive visibility and governance',
};

// =============================================================================
// FEATURE GATING
// =============================================================================

/**
 * Feature categories and their required maturity levels
 */
export interface FeatureRequirement {
  id: string;
  name: string;
  category: 'sales' | 'production' | 'tps' | 'executive' | 'admin';
  requiredLevel: MaturityLevel;
  dataRequirements?: string[];
}

export const FEATURE_REQUIREMENTS: FeatureRequirement[] = [
  // Level 0 - Always available
  { id: 'system-settings', name: 'System Settings', category: 'admin', requiredLevel: 0 },
  { id: 'user-management', name: 'User Management', category: 'admin', requiredLevel: 0 },
  
  // Level 1 - Basic Operations
  { id: 'customer-list', name: 'Customer List', category: 'sales', requiredLevel: 1 },
  { id: 'quote-creation', name: 'Quote Creation', category: 'sales', requiredLevel: 1 },
  { id: 'pipeline-basic', name: 'Sales Pipeline', category: 'sales', requiredLevel: 1 },

  // Level 2 - Standard Operations (production)
  {
    id: 'work-orders',
    name: 'Work Order Management',
    category: 'production',
    requiredLevel: 2,
    dataRequirements: ['site-design', 'stations'],
  },
  {
    id: 'job-scheduling',
    name: 'Job Scheduling',
    category: 'production',
    requiredLevel: 2,
    dataRequirements: ['site-design'],
  },
  { id: 'quality-checks', name: 'Quality Checks', category: 'production', requiredLevel: 2 },
  
  // Level 3 - Advanced Operations (TPS)
  { id: 'andon', name: 'Andon System', category: 'tps', requiredLevel: 3, dataRequirements: ['stations', 'operators'] },
  { id: 'kaizen', name: 'Kaizen Events', category: 'tps', requiredLevel: 3 },
  { id: 'problem-solving-a3', name: 'A3 Problem Solving', category: 'tps', requiredLevel: 3 },

  // Level 4 - Full TPS (executive)
  { id: 'exec-dashboard', name: 'Executive Dashboard', category: 'executive', requiredLevel: 4 },
  { id: 'obeya', name: 'Obeya Room', category: 'executive', requiredLevel: 4 },
  { id: 'sqdcp-metrics', name: 'SQDCP Metrics', category: 'executive', requiredLevel: 4 },
  { id: 'governance', name: 'Governance & Audit', category: 'executive', requiredLevel: 4 },
];

/**
 * Check if a feature is available at the current maturity level
 */
export function isFeatureAvailable(featureId: string, currentLevel: MaturityLevel): boolean {
  const feature = FEATURE_REQUIREMENTS.find((f) => f.id === featureId);
  if (!feature) return false;
  return currentLevel >= feature.requiredLevel;
}

/**
 * Get all features available at a given level
 */
export function getAvailableFeatures(level: MaturityLevel): FeatureRequirement[] {
  return FEATURE_REQUIREMENTS.filter((f) => f.requiredLevel <= level);
}

/**
 * Get features that will be unlocked at the next level
 */
export function getNextLevelFeatures(currentLevel: MaturityLevel): FeatureRequirement[] {
  if (currentLevel >= MATURITY_LEVELS.LEVEL_4) return [];
  const nextLevel = (currentLevel + 1) as MaturityLevel;
  return FEATURE_REQUIREMENTS.filter((f) => f.requiredLevel === nextLevel);
}

// =============================================================================
// DATA REQUIREMENTS CHECKING
// =============================================================================

export interface DataStatus {
  id: string;
  name: string;
  isComplete: boolean;
  completionPercentage: number;
  missingItems?: string[];
}

export interface LevelUpRequirement {
  canLevelUp: boolean;
  missingData: DataStatus[];
  targetLevel: MaturityLevel;
}

/**
 * Check if data requirements are met for a level-up
 */
export function checkLevelUpRequirements(
  targetLevel: MaturityLevel,
  dataStatuses: Record<string, DataStatus>
): LevelUpRequirement {
  const featuresAtTarget = FEATURE_REQUIREMENTS.filter((f) => f.requiredLevel === targetLevel);
  const missingData: DataStatus[] = [];

  for (const feature of featuresAtTarget) {
    if (feature.dataRequirements) {
      for (const req of feature.dataRequirements) {
        const status = dataStatuses[req];
        if (!status || !status.isComplete) {
          if (!missingData.find((d) => d.id === req)) {
            missingData.push(
              status || {
                id: req,
                name: req.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
                isComplete: false,
                completionPercentage: 0,
                missingItems: ['Not configured'],
              }
            );
          }
        }
      }
    }
  }

  return {
    canLevelUp: missingData.length === 0,
    missingData,
    targetLevel,
  };
}

// =============================================================================
// LEAKAGE AUDIT UTILITIES
// =============================================================================

export interface LeakageResult {
  type: 'search' | 'command-palette' | 'deep-link' | 'api';
  featureId: string;
  isLeaking: boolean;
  details?: string;
}

/**
 * Audit for feature leakage through various access points
 */
export function auditFeatureLeakage(
  featureId: string,
  currentLevel: MaturityLevel,
  accessPoints: {
    searchResults?: string[];
    commandPaletteItems?: string[];
    accessibleRoutes?: string[];
    apiEndpoints?: string[];
  }
): LeakageResult[] {
  const feature = FEATURE_REQUIREMENTS.find((f) => f.id === featureId);
  if (!feature) return [];

  const shouldBeHidden = feature.requiredLevel > currentLevel;
  if (!shouldBeHidden) return []; // Feature is available, no leakage possible

  const results: LeakageResult[] = [];

  // Check search results
  if (accessPoints.searchResults) {
    const isInSearch = accessPoints.searchResults.some(
      (r) => r.toLowerCase().includes(feature.name.toLowerCase())
    );
    results.push({
      type: 'search',
      featureId,
      isLeaking: isInSearch,
      details: isInSearch ? `Found "${feature.name}" in search results` : undefined,
    });
  }

  // Check command palette
  if (accessPoints.commandPaletteItems) {
    const isInPalette = accessPoints.commandPaletteItems.some(
      (r) => r.toLowerCase().includes(feature.name.toLowerCase())
    );
    results.push({
      type: 'command-palette',
      featureId,
      isLeaking: isInPalette,
      details: isInPalette ? `Found "${feature.name}" in command palette` : undefined,
    });
  }

  // Check accessible routes
  if (accessPoints.accessibleRoutes) {
    const isAccessible = accessPoints.accessibleRoutes.some(
      (r) => r.includes(featureId) || r.includes(featureId.replace(/-/g, '/'))
    );
    results.push({
      type: 'deep-link',
      featureId,
      isLeaking: isAccessible,
      details: isAccessible ? `Route for "${feature.name}" is accessible` : undefined,
    });
  }

  // Check API endpoints
  if (accessPoints.apiEndpoints) {
    const isApiAccessible = accessPoints.apiEndpoints.some(
      (e) => e.includes(featureId) || e.includes(featureId.replace(/-/g, '_'))
    );
    results.push({
      type: 'api',
      featureId,
      isLeaking: isApiAccessible,
      details: isApiAccessible ? `API endpoint for "${feature.name}" is accessible` : undefined,
    });
  }

  return results;
}

/**
 * Run full leakage audit for all features
 */
export function runFullLeakageAudit(
  currentLevel: MaturityLevel,
  accessPoints: {
    searchResults?: string[];
    commandPaletteItems?: string[];
    accessibleRoutes?: string[];
    apiEndpoints?: string[];
  }
): { totalLeaks: number; results: LeakageResult[] } {
  const allResults: LeakageResult[] = [];

  for (const feature of FEATURE_REQUIREMENTS) {
    const results = auditFeatureLeakage(feature.id, currentLevel, accessPoints);
    allResults.push(...results);
  }

  return {
    totalLeaks: allResults.filter((r) => r.isLeaking).length,
    results: allResults,
  };
}

// =============================================================================
// MATURITY LEVEL CONTEXT
// =============================================================================

export interface MaturityContextValue {
  currentLevel: MaturityLevel;
  setLevel: (level: MaturityLevel) => void;
  levelUp: () => Promise<LevelUpResult>;
  isFeatureAvailable: (featureId: string) => boolean;
  availableFeatures: FeatureRequirement[];
  nextLevelFeatures: FeatureRequirement[];
  dataStatuses: Record<string, DataStatus>;
  setDataStatus: (id: string, status: DataStatus) => void;
  isLevelingUp: boolean;
  lastLevelUpResult: LevelUpResult | null;
  rehearsalMode: boolean;
  setRehearsalMode: (enabled: boolean) => void;
  sandboxMode: boolean;
  setSandboxMode: (enabled: boolean) => void;
}

export interface LevelUpResult {
  success: boolean;
  previousLevel: MaturityLevel;
  newLevel: MaturityLevel;
  duration: number; // milliseconds
  errors?: string[];
}

const MaturityContext = createContext<MaturityContextValue | null>(null);

export interface MaturityProviderProps {
  children: React.ReactNode;
  initialLevel?: MaturityLevel;
  initialDataStatuses?: Record<string, DataStatus>;
  onLevelChange?: (level: MaturityLevel) => void;
  onLevelUp?: (result: LevelUpResult) => void;
}

export function MaturityProvider({
  children,
  initialLevel = MATURITY_LEVELS.LEVEL_0,
  initialDataStatuses = {},
  onLevelChange,
  onLevelUp,
}: MaturityProviderProps) {
  const [currentLevel, setCurrentLevel] = useState<MaturityLevel>(initialLevel);
  const [dataStatuses, setDataStatuses] = useState<Record<string, DataStatus>>(initialDataStatuses);
  const [isLevelingUp, setIsLevelingUp] = useState(false);
  const [lastLevelUpResult, setLastLevelUpResult] = useState<LevelUpResult | null>(null);
  const [rehearsalMode, setRehearsalMode] = useState(false);
  const [sandboxMode, setSandboxMode] = useState(false);

  const setLevel = useCallback(
    (level: MaturityLevel) => {
      setCurrentLevel(level);
      onLevelChange?.(level);
    },
    [onLevelChange]
  );

  const levelUp = useCallback(async (): Promise<LevelUpResult> => {
    if (currentLevel >= MATURITY_LEVELS.LEVEL_4) {
      const result: LevelUpResult = {
        success: false,
        previousLevel: currentLevel,
        newLevel: currentLevel,
        duration: 0,
        errors: ['Already at maximum maturity level'],
      };
      setLastLevelUpResult(result);
      return result;
    }

    const targetLevel = (currentLevel + 1) as MaturityLevel;
    const requirements = checkLevelUpRequirements(targetLevel, dataStatuses);

    if (!requirements.canLevelUp) {
      const result: LevelUpResult = {
        success: false,
        previousLevel: currentLevel,
        newLevel: currentLevel,
        duration: 0,
        errors: requirements.missingData.map(
          (d) => `Missing required data: ${d.name} (${d.completionPercentage}% complete)`
        ),
      };
      setLastLevelUpResult(result);
      return result;
    }

    setIsLevelingUp(true);
    const startTime = performance.now();

    try {
      // Simulate level-up processing (configuration migration, cache invalidation, etc.)
      await new Promise((resolve) => setTimeout(resolve, 100));

      const duration = performance.now() - startTime;
      const result: LevelUpResult = {
        success: true,
        previousLevel: currentLevel,
        newLevel: targetLevel,
        duration,
      };

      setCurrentLevel(targetLevel);
      setLastLevelUpResult(result);
      onLevelChange?.(targetLevel);
      onLevelUp?.(result);

      return result;
    } catch (error) {
      const duration = performance.now() - startTime;
      const result: LevelUpResult = {
        success: false,
        previousLevel: currentLevel,
        newLevel: currentLevel,
        duration,
        errors: [error instanceof Error ? error.message : 'Unknown error during level-up'],
      };
      setLastLevelUpResult(result);
      return result;
    } finally {
      setIsLevelingUp(false);
    }
  }, [currentLevel, dataStatuses, onLevelChange, onLevelUp]);

  const checkFeatureAvailability = useCallback(
    (featureId: string) => isFeatureAvailable(featureId, currentLevel),
    [currentLevel]
  );

  const setDataStatusHandler = useCallback((id: string, status: DataStatus) => {
    setDataStatuses((prev) => ({ ...prev, [id]: status }));
  }, []);

  const availableFeatures = useMemo(
    () => getAvailableFeatures(currentLevel),
    [currentLevel]
  );

  const nextLevelFeatures = useMemo(
    () => getNextLevelFeatures(currentLevel),
    [currentLevel]
  );

  const value = useMemo<MaturityContextValue>(
    () => ({
      currentLevel,
      setLevel,
      levelUp,
      isFeatureAvailable: checkFeatureAvailability,
      availableFeatures,
      nextLevelFeatures,
      dataStatuses,
      setDataStatus: setDataStatusHandler,
      isLevelingUp,
      lastLevelUpResult,
      rehearsalMode,
      setRehearsalMode,
      sandboxMode,
      setSandboxMode,
    }),
    [
      currentLevel,
      setLevel,
      levelUp,
      checkFeatureAvailability,
      availableFeatures,
      nextLevelFeatures,
      dataStatuses,
      setDataStatusHandler,
      isLevelingUp,
      lastLevelUpResult,
      rehearsalMode,
      sandboxMode,
    ]
  );

  return (
    <MaturityContext.Provider value={value}>{children}</MaturityContext.Provider>
  );
}

export function useMaturity(): MaturityContextValue {
  const context = useContext(MaturityContext);
  if (!context) {
    throw new Error('useMaturity must be used within a MaturityProvider');
  }
  return context;
}

// =============================================================================
// MATURITY LEVEL INDICATOR COMPONENT
// =============================================================================

export interface MaturityLevelIndicatorProps {
  showProgress?: boolean;
  showNextFeatures?: boolean;
  compact?: boolean;
  className?: string;
}

export function MaturityLevelIndicator({
  showProgress = true,
  showNextFeatures = true,
  compact = false,
  className = '',
}: MaturityLevelIndicatorProps) {
  const { currentLevel, nextLevelFeatures, dataStatuses } = useMaturity();

  const levelName = MATURITY_LEVEL_NAMES[currentLevel];
  const levelDescription = MATURITY_LEVEL_DESCRIPTIONS[currentLevel];
  const progressPercent = (currentLevel / MATURITY_LEVELS.LEVEL_4) * 100;

  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="px-2 py-1 text-xs font-medium bg-primary/10 text-primary rounded">
          L{currentLevel}
        </div>
        <span className="text-sm text-muted-foreground">{levelName}</span>
      </div>
    );
  }

  return (
    <div className={`p-4 bg-card border border-border rounded-lg ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="font-semibold">Maturity Level {currentLevel}</h3>
          <p className="text-sm text-muted-foreground">{levelName}</p>
        </div>
        <div className="text-3xl font-bold text-primary">L{currentLevel}</div>
      </div>

      <p className="text-sm text-muted-foreground mb-4">{levelDescription}</p>

      {showProgress && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>Progress</span>
            <span>{progressPercent.toFixed(0)}%</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {showNextFeatures && nextLevelFeatures.length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-2">Next Level Unlocks:</h4>
          <ul className="space-y-1">
            {nextLevelFeatures.slice(0, 3).map((feature) => (
              <li key={feature.id} className="flex items-center gap-2 text-sm">
                <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full" />
                <span>{feature.name}</span>
              </li>
            ))}
            {nextLevelFeatures.length > 3 && (
              <li className="text-xs text-muted-foreground pl-3">
                +{nextLevelFeatures.length - 3} more features
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// FEATURE GATE COMPONENT
// =============================================================================

export interface FeatureGateProps {
  featureId: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  showBlockedMessage?: boolean;
}

export function FeatureGate({
  featureId,
  children,
  fallback,
  showBlockedMessage = true,
}: FeatureGateProps) {
  const { currentLevel, isFeatureAvailable } = useMaturity();

  if (isFeatureAvailable(featureId)) {
    return <>{children}</>;
  }

  if (fallback) {
    return <>{fallback}</>;
  }

  if (!showBlockedMessage) {
    return null;
  }

  const feature = FEATURE_REQUIREMENTS.find((f) => f.id === featureId);

  return (
    <div className="p-4 bg-muted/50 border border-border rounded-lg text-center">
      <div className="text-2xl mb-2">🔒</div>
      <h3 className="font-medium mb-1">{feature?.name || 'Feature'} Locked</h3>
      <p className="text-sm text-muted-foreground">
        Requires Maturity Level {feature?.requiredLevel || '?'} (current: L{currentLevel})
      </p>
    </div>
  );
}

// =============================================================================
// LEVEL UP BUTTON COMPONENT
// =============================================================================

export interface LevelUpButtonProps {
  className?: string;
  showRequirements?: boolean;
}

export function LevelUpButton({ className = '', showRequirements = true }: LevelUpButtonProps) {
  const { currentLevel, levelUp, isLevelingUp, dataStatuses } = useMaturity();

  if (currentLevel >= MATURITY_LEVELS.LEVEL_4) {
    return (
      <div className={`p-4 bg-success/10 border border-success/20 rounded-lg text-center ${className}`}>
        <div className="text-2xl mb-2">🎉</div>
        <p className="font-medium text-success">Maximum Level Achieved!</p>
      </div>
    );
  }

  const targetLevel = (currentLevel + 1) as MaturityLevel;
  const requirements = checkLevelUpRequirements(targetLevel, dataStatuses);

  const handleLevelUp = async () => {
    const result = await levelUp();
    if (!result.success && result.errors) {
      // Could show a toast or modal here
      console.error('Level-up failed:', result.errors);
    }
  };

  return (
    <div className={`p-4 bg-card border border-border rounded-lg ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold">Level Up to L{targetLevel}</h3>
          <p className="text-sm text-muted-foreground">{MATURITY_LEVEL_NAMES[targetLevel]}</p>
        </div>
        <button
          onClick={handleLevelUp}
          disabled={!requirements.canLevelUp || isLevelingUp}
          className={`px-4 py-2 rounded font-medium transition-colors ${
            requirements.canLevelUp && !isLevelingUp
              ? 'bg-primary text-primary-foreground hover:opacity-90'
              : 'bg-muted text-muted-foreground cursor-not-allowed'
          }`}
        >
          {isLevelingUp ? 'Upgrading...' : 'Level Up'}
        </button>
      </div>

      {showRequirements && !requirements.canLevelUp && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-warning">Missing Requirements:</p>
          {requirements.missingData.map((data) => (
            <div key={data.id} className="flex items-center gap-2 text-sm">
              <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-warning"
                  style={{ width: `${data.completionPercentage}%` }}
                />
              </div>
              <span className="text-muted-foreground">
                {data.name} ({data.completionPercentage}%)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// REHEARSAL MODE BANNER
// =============================================================================

export interface RehearsalModeBannerProps {
  className?: string;
}

export function RehearsalModeBanner({ className = '' }: RehearsalModeBannerProps) {
  const { rehearsalMode, setRehearsalMode } = useMaturity();

  if (!rehearsalMode) return null;

  return (
    <div
      className={`flex items-center justify-between px-4 py-2 bg-warning/20 border-b border-warning/30 ${className}`}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">🎭</span>
        <span className="font-medium text-warning-foreground">Rehearsal Mode Active</span>
        <span className="text-sm text-muted-foreground">
          - Actions are simulated and won&apos;t affect production data
        </span>
      </div>
      <button
        onClick={() => setRehearsalMode(false)}
        className="px-3 py-1 text-sm border border-warning/50 rounded hover:bg-warning/10"
      >
        Exit Rehearsal
      </button>
    </div>
  );
}

// =============================================================================
// SANDBOX MODE BANNER
// =============================================================================

export interface SandboxModeBannerProps {
  className?: string;
}

export function SandboxModeBanner({ className = '' }: SandboxModeBannerProps) {
  const { sandboxMode, setSandboxMode } = useMaturity();

  if (!sandboxMode) return null;

  return (
    <div
      className={`flex items-center justify-between px-4 py-2 bg-primary/20 border-b border-primary/30 ${className}`}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">🏖️</span>
        <span className="font-medium">Sandbox Mode Active</span>
        <span className="text-sm text-muted-foreground">
          - Andon and alerts are isolated from executive dashboards
        </span>
      </div>
      <button
        onClick={() => setSandboxMode(false)}
        className="px-3 py-1 text-sm border border-primary/50 rounded hover:bg-primary/10"
      >
        Exit Sandbox
      </button>
    </div>
  );
}

// =============================================================================
// MATURITY DASHBOARD COMPONENT
// =============================================================================

export interface MaturityDashboardProps {
  className?: string;
}

export function MaturityDashboard({ className = '' }: MaturityDashboardProps) {
  const { currentLevel, availableFeatures, lastLevelUpResult } = useMaturity();

  const featuresByCategory = useMemo(() => {
    const categories: Record<string, FeatureRequirement[]> = {};
    for (const feature of availableFeatures) {
      if (!categories[feature.category]) {
        categories[feature.category] = [];
      }
      categories[feature.category].push(feature);
    }
    return categories;
  }, [availableFeatures]);

  const categoryIcons: Record<string, string> = {
    sales: '💰',
    production: '🏭',
    tps: '📊',
    executive: '👔',
    admin: '⚙️',
  };

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="grid md:grid-cols-2 gap-4">
        <MaturityLevelIndicator />
        <LevelUpButton />
      </div>

      {lastLevelUpResult && (
        <div
          className={`p-4 rounded-lg ${
            lastLevelUpResult.success
              ? 'bg-success/10 border border-success/20'
              : 'bg-destructive/10 border border-destructive/20'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="text-xl">{lastLevelUpResult.success ? '✅' : '❌'}</span>
            <div>
              <p className="font-medium">
                {lastLevelUpResult.success
                  ? `Successfully upgraded to Level ${lastLevelUpResult.newLevel}`
                  : 'Level-up failed'}
              </p>
              <p className="text-sm text-muted-foreground">
                Duration: {lastLevelUpResult.duration.toFixed(0)}ms
              </p>
            </div>
          </div>
          {lastLevelUpResult.errors && (
            <ul className="mt-2 space-y-1">
              {lastLevelUpResult.errors.map((error, i) => (
                <li key={i} className="text-sm text-destructive">
                  • {error}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div>
        <h3 className="font-semibold mb-4">Available Features by Category</h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(featuresByCategory).map(([category, features]) => (
            <div key={category} className="p-4 bg-card border border-border rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">{categoryIcons[category] || '📦'}</span>
                <h4 className="font-medium capitalize">{category}</h4>
                <span className="ml-auto text-xs bg-muted px-2 py-0.5 rounded">
                  {features.length}
                </span>
              </div>
              <ul className="space-y-1">
                {features.map((feature) => (
                  <li key={feature.id} className="flex items-center gap-2 text-sm">
                    <span className="w-1.5 h-1.5 bg-success rounded-full" />
                    <span>{feature.name}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// SAT (SITE ACCEPTANCE TEST) UTILITIES
// =============================================================================

export interface SATChecklistItem {
  id: string;
  category: 'network' | 'hardware' | 'software' | 'integration' | 'training';
  description: string;
  completed: boolean;
  completedAt?: Date;
  completedBy?: string;
  offlineCapable: boolean;
  notes?: string;
}

export interface SATChecklist {
  id: string;
  siteId: string;
  siteName: string;
  createdAt: Date;
  completedAt?: Date;
  items: SATChecklistItem[];
  overallStatus: 'not-started' | 'in-progress' | 'completed' | 'blocked';
}

/**
 * Create a new SAT checklist
 */
export function createSATChecklist(siteId: string, siteName: string): SATChecklist {
  const defaultItems: Omit<SATChecklistItem, 'id'>[] = [
    { category: 'network', description: 'Network connectivity verified', completed: false, offlineCapable: false },
    { category: 'network', description: 'Firewall rules configured', completed: false, offlineCapable: false },
    { category: 'network', description: 'SSL certificates installed', completed: false, offlineCapable: false },
    { category: 'hardware', description: 'Edge devices discovered', completed: false, offlineCapable: true },
    { category: 'hardware', description: 'MAC addresses registered', completed: false, offlineCapable: true },
    { category: 'hardware', description: 'Station assignments verified', completed: false, offlineCapable: true },
    { category: 'software', description: 'System version deployed', completed: false, offlineCapable: true },
    { category: 'software', description: 'Database migrations complete', completed: false, offlineCapable: false },
    { category: 'software', description: 'Initial data seeded', completed: false, offlineCapable: true },
    { category: 'integration', description: 'ERP connection tested', completed: false, offlineCapable: false },
    { category: 'integration', description: 'IoT sensors responding', completed: false, offlineCapable: true },
    { category: 'integration', description: 'Notification systems verified', completed: false, offlineCapable: false },
    { category: 'training', description: 'Admin training completed', completed: false, offlineCapable: true },
    { category: 'training', description: 'Operator training completed', completed: false, offlineCapable: true },
    { category: 'training', description: 'Documentation reviewed', completed: false, offlineCapable: true },
  ];

  return {
    id: `sat-${siteId}-${Date.now()}`,
    siteId,
    siteName,
    createdAt: new Date(),
    items: defaultItems.map((item, index) => ({
      ...item,
      id: `item-${index + 1}`,
    })),
    overallStatus: 'not-started',
  };
}

/**
 * Update SAT checklist item
 */
export function updateSATChecklistItem(
  checklist: SATChecklist,
  itemId: string,
  updates: Partial<Pick<SATChecklistItem, 'completed' | 'completedBy' | 'notes'>>
): SATChecklist {
  const updatedItems = checklist.items.map((item) =>
    item.id === itemId
      ? {
          ...item,
          ...updates,
          completedAt: updates.completed ? new Date() : undefined,
        }
      : item
  );

  const completedCount = updatedItems.filter((i) => i.completed).length;
  let overallStatus: SATChecklist['overallStatus'];

  if (completedCount === 0) {
    overallStatus = 'not-started';
  } else if (completedCount === updatedItems.length) {
    overallStatus = 'completed';
  } else {
    overallStatus = 'in-progress';
  }

  return {
    ...checklist,
    items: updatedItems,
    overallStatus,
    completedAt: overallStatus === 'completed' ? new Date() : undefined,
  };
}

/**
 * Get offline-capable items from checklist
 */
export function getOfflineCapableItems(checklist: SATChecklist): SATChecklistItem[] {
  return checklist.items.filter((item) => item.offlineCapable);
}

/**
 * Calculate checklist completion percentage
 */
export function getSATCompletionPercentage(checklist: SATChecklist): number {
  if (checklist.items.length === 0) return 0;
  const completed = checklist.items.filter((i) => i.completed).length;
  return (completed / checklist.items.length) * 100;
}

// =============================================================================
// IOT DEVICE DISCOVERY
// =============================================================================

export interface IoTDevice {
  id: string;
  macAddress: string;
  ipAddress?: string;
  deviceType: 'sensor' | 'controller' | 'display' | 'scanner' | 'printer' | 'unknown';
  status: 'discovered' | 'linked' | 'offline' | 'error';
  linkedStationId?: string;
  linkedStationName?: string;
  lastSeen: Date;
  metadata?: Record<string, string>;
}

/**
 * Parse MAC address to standard format
 */
export function normalizeMacAddress(mac: string): string {
  const cleaned = mac.replace(/[^a-fA-F0-9]/g, '').toLowerCase();
  if (cleaned.length !== 12) {
    throw new Error('Invalid MAC address format');
  }
  return cleaned.match(/.{2}/g)!.join(':');
}

/**
 * Validate MAC address format
 */
export function isValidMacAddress(mac: string): boolean {
  try {
    normalizeMacAddress(mac);
    return true;
  } catch {
    return false;
  }
}

/**
 * Link device to station
 */
export function linkDeviceToStation(
  device: IoTDevice,
  stationId: string,
  stationName: string
): IoTDevice {
  return {
    ...device,
    status: 'linked',
    linkedStationId: stationId,
    linkedStationName: stationName,
  };
}

// =============================================================================
// EXPORTS
// =============================================================================

export { MaturityContext };
