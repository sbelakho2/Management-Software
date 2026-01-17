/**
 * Onboarding, Help & Documentation UX Components
 * 
 * Section 19.11: Onboarding, Help & Documentation UX
 * 
 * Provides first-run experience, product tours, contextual help,
 * empty states, and Sensei integration for intelligent suggestions.
 */

'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
  useRef,
} from 'react';

// =============================================================================
// CONSTANTS
// =============================================================================

/**
 * Tour step positions
 */
export const TOUR_POSITION = {
  TOP: 'top',
  BOTTOM: 'bottom',
  LEFT: 'left',
  RIGHT: 'right',
  CENTER: 'center',
} as const;

export type TourPositionType = (typeof TOUR_POSITION)[keyof typeof TOUR_POSITION];

/**
 * Onboarding states
 */
export const ONBOARDING_STATE = {
  NOT_STARTED: 'not_started',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  SKIPPED: 'skipped',
} as const;

export type OnboardingStateType = (typeof ONBOARDING_STATE)[keyof typeof ONBOARDING_STATE];

/**
 * Help topic categories
 */
export const HELP_CATEGORY = {
  GETTING_STARTED: 'getting_started',
  RFQ_MANAGEMENT: 'rfq_management',
  QUOTING: 'quoting',
  PRODUCTION: 'production',
  QUALITY: 'quality',
  SHIPPING: 'shipping',
  FINANCIAL: 'financial',
  SETTINGS: 'settings',
} as const;

export type HelpCategoryType = (typeof HELP_CATEGORY)[keyof typeof HELP_CATEGORY];

/**
 * Empty state types
 */
export const EMPTY_STATE_TYPE = {
  NO_DATA: 'no_data',
  NO_RESULTS: 'no_results',
  NO_ACCESS: 'no_access',
  ERROR: 'error',
  FIRST_TIME: 'first_time',
} as const;

export type EmptyStateTypeType = (typeof EMPTY_STATE_TYPE)[keyof typeof EMPTY_STATE_TYPE];

/**
 * Sensei suggestion types
 */
export const SUGGESTION_TYPE = {
  SHORTCUT: 'shortcut',
  FEATURE: 'feature',
  TIP: 'tip',
  WARNING: 'warning',
} as const;

export type SuggestionTypeType = (typeof SUGGESTION_TYPE)[keyof typeof SUGGESTION_TYPE];

// =============================================================================
// TYPES
// =============================================================================

export interface TourStep {
  id: string;
  target: string; // CSS selector
  title: string;
  content: string;
  position?: TourPositionType;
  spotlightPadding?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface HelpTopic {
  id: string;
  title: string;
  description: string;
  category: HelpCategoryType;
  keywords: string[];
  url?: string;
}

export interface SenseiSuggestion {
  id: string;
  type: SuggestionTypeType;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  dismissable?: boolean;
}

// =============================================================================
// TOUR CONTEXT
// =============================================================================

interface TourContextValue {
  isActive: boolean;
  currentStep: number;
  steps: TourStep[];
  startTour: (steps: TourStep[]) => void;
  endTour: () => void;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (index: number) => void;
}

const TourContext = createContext<TourContextValue | null>(null);

interface TourProviderProps {
  children: ReactNode;
}

/**
 * Product tour provider
 */
export function TourProvider({ children }: TourProviderProps): React.ReactElement {
  const [isActive, setIsActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [steps, setSteps] = useState<TourStep[]>([]);

  const startTour = useCallback((tourSteps: TourStep[]) => {
    setSteps(tourSteps);
    setCurrentStep(0);
    setIsActive(true);
  }, []);

  const endTour = useCallback(() => {
    setIsActive(false);
    setCurrentStep(0);
    setSteps([]);
  }, []);

  const nextStep = useCallback(() => {
    if (currentStep < steps.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      endTour();
    }
  }, [currentStep, steps.length, endTour]);

  const prevStep = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep]);

  const goToStep = useCallback((index: number) => {
    if (index >= 0 && index < steps.length) {
      setCurrentStep(index);
    }
  }, [steps.length]);

  const value = useMemo(() => ({
    isActive,
    currentStep,
    steps,
    startTour,
    endTour,
    nextStep,
    prevStep,
    goToStep,
  }), [isActive, currentStep, steps, startTour, endTour, nextStep, prevStep, goToStep]);

  return (
    <TourContext.Provider value={value}>
      {children}
    </TourContext.Provider>
  );
}

/**
 * Hook to access tour context
 */
export function useTour(): TourContextValue {
  const context = useContext(TourContext);
  if (!context) {
    throw new Error('useTour must be used within TourProvider');
  }
  return context;
}

// =============================================================================
// TOUR OVERLAY
// =============================================================================

/**
 * Calculate position for spotlight
 */
function getSpotlightStyle(
  target: HTMLElement | null,
  padding: number = 8
): React.CSSProperties {
  if (!target) {
    return {
      top: '50%',
      left: '50%',
      width: 0,
      height: 0,
      transform: 'translate(-50%, -50%)',
    };
  }

  const rect = target.getBoundingClientRect();
  return {
    top: rect.top - padding,
    left: rect.left - padding,
    width: rect.width + padding * 2,
    height: rect.height + padding * 2,
  };
}

/**
 * Calculate position for tooltip
 */
function getTooltipStyle(
  target: HTMLElement | null,
  position: TourPositionType
): React.CSSProperties {
  if (!target) {
    return {
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
    };
  }

  const rect = target.getBoundingClientRect();
  const offset = 12;

  switch (position) {
    case TOUR_POSITION.TOP:
      return {
        bottom: window.innerHeight - rect.top + offset,
        left: rect.left + rect.width / 2,
        transform: 'translateX(-50%)',
      };
    case TOUR_POSITION.BOTTOM:
      return {
        top: rect.bottom + offset,
        left: rect.left + rect.width / 2,
        transform: 'translateX(-50%)',
      };
    case TOUR_POSITION.LEFT:
      return {
        top: rect.top + rect.height / 2,
        right: window.innerWidth - rect.left + offset,
        transform: 'translateY(-50%)',
      };
    case TOUR_POSITION.RIGHT:
      return {
        top: rect.top + rect.height / 2,
        left: rect.right + offset,
        transform: 'translateY(-50%)',
      };
    case TOUR_POSITION.CENTER:
    default:
      return {
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      };
  }
}

/**
 * Tour overlay with spotlight and tooltip
 */
export function TourOverlay(): React.ReactElement | null {
  const { isActive, currentStep, steps, nextStep, prevStep, endTour } = useTour();
  const [targetElement, setTargetElement] = useState<HTMLElement | null>(null);

  const step = steps[currentStep];

  useEffect(() => {
    if (!isActive || !step) {
      setTargetElement(null);
      return;
    }

    const element = document.querySelector(step.target) as HTMLElement | null;
    setTargetElement(element);

    // Scroll element into view (safely, for test environments)
    if (element && typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [isActive, step]);

  const spotlightStyle = getSpotlightStyle(targetElement, step?.spotlightPadding);
  const tooltipStyle = getTooltipStyle(targetElement, step?.position || TOUR_POSITION.BOTTOM);

  const getClipPath = useCallback(() => {
    if (!targetElement) return undefined;
    
    const l = spotlightStyle.left;
    const t = spotlightStyle.top;
    const w = spotlightStyle.width;
    const h = spotlightStyle.height;
    
    // Create a cutout by drawing a polygon that covers the whole screen
    // then cuts into the middle and back out.
    return `polygon(
      0% 0%,
      0% 100%,
      ${l}px 100%,
      ${l}px ${t}px,
      ${Number(l) + Number(w)}px ${t}px,
      ${Number(l) + Number(w)}px ${Number(t) + Number(h)}px,
      ${l}px ${Number(t) + Number(h)}px,
      ${l}px 100%,
      100% 100%,
      100% 0%
    )`;
  }, [targetElement, spotlightStyle]);

  if (!isActive || !step) return null;

  return (
    <div className="fixed inset-0 z-[9999]" role="dialog" aria-modal="true" aria-label="Product tour">
      {/* Overlay with spotlight cutout */}
      <div
        className="absolute inset-0 bg-black/50"
        style={{
          clipPath: getClipPath() as any,
        }}
        onClick={endTour}
        aria-hidden="true"
      />

      {/* Spotlight border */}
      {targetElement && (
        <div
          className="absolute border-2 border-blue-500 rounded-lg pointer-events-none"
          style={{
            top: spotlightStyle.top,
            left: spotlightStyle.left,
            width: spotlightStyle.width,
            height: spotlightStyle.height,
          }}
          aria-hidden="true"
        />
      )}

      {/* Tooltip */}
      <div
        className="absolute bg-white dark:bg-gray-900 rounded-lg shadow-xl p-4 max-w-sm z-10"
        style={tooltipStyle}
      >
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">{step.title}</h3>
          <button
            type="button"
            onClick={endTour}
            aria-label="Close tour"
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            ✕
          </button>
        </div>

        <p className="text-gray-600 dark:text-gray-300 mb-4">{step.content}</p>

        {step.action && (
          <button
            type="button"
            onClick={step.action.onClick}
            className="mb-4 px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
          >
            {step.action.label}
          </button>
        )}

        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-500">
            {currentStep + 1} of {steps.length}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={prevStep}
              disabled={currentStep === 0}
              className="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Back
            </button>
            <button
              type="button"
              onClick={nextStep}
              className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              {currentStep === steps.length - 1 ? 'Finish' : 'Next'}
            </button>
          </div>
        </div>

        {/* Progress dots */}
        <div className="flex justify-center gap-1 mt-3">
          {steps.map((_, index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded-full ${
                index === currentStep ? 'bg-blue-600' : 'bg-gray-300'
              }`}
              aria-hidden="true"
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// ONBOARDING CONTEXT
// =============================================================================

interface OnboardingContextValue {
  state: OnboardingStateType;
  completedSteps: string[];
  markStepComplete: (stepId: string) => void;
  resetOnboarding: () => void;
  skipOnboarding: () => void;
  completeOnboarding: () => void;
  isFirstVisit: boolean;
}

const OnboardingContext = createContext<OnboardingContextValue | null>(null);

interface OnboardingProviderProps {
  children: ReactNode;
  storageKey?: string;
}

/**
 * Onboarding state provider
 */
export function OnboardingProvider({
  children,
  storageKey = 'onboarding-state',
}: OnboardingProviderProps): React.ReactElement {
  const [state, setState] = useState<OnboardingStateType>(() => {
    if (typeof localStorage === 'undefined') return ONBOARDING_STATE.NOT_STARTED;
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      try {
        return JSON.parse(stored).state || ONBOARDING_STATE.NOT_STARTED;
      } catch {
        return ONBOARDING_STATE.NOT_STARTED;
      }
    }
    return ONBOARDING_STATE.NOT_STARTED;
  });

  const [completedSteps, setCompletedSteps] = useState<string[]>(() => {
    if (typeof localStorage === 'undefined') return [];
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      try {
        return JSON.parse(stored).completedSteps || [];
      } catch {
        return [];
      }
    }
    return [];
  });

  const [isFirstVisit] = useState(() => {
    if (typeof localStorage === 'undefined') return true;
    return !localStorage.getItem(storageKey);
  });

  // Persist state
  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify({ state, completedSteps }));
  }, [state, completedSteps, storageKey]);

  const markStepComplete = useCallback((stepId: string) => {
    setCompletedSteps((prev) => {
      if (prev.includes(stepId)) return prev;
      return [...prev, stepId];
    });
    if (state === ONBOARDING_STATE.NOT_STARTED) {
      setState(ONBOARDING_STATE.IN_PROGRESS);
    }
  }, [state]);

  const resetOnboarding = useCallback(() => {
    setState(ONBOARDING_STATE.NOT_STARTED);
    setCompletedSteps([]);
    localStorage.removeItem(storageKey);
  }, [storageKey]);

  const skipOnboarding = useCallback(() => {
    setState(ONBOARDING_STATE.SKIPPED);
  }, []);

  const completeOnboarding = useCallback(() => {
    setState(ONBOARDING_STATE.COMPLETED);
  }, []);

  const value = useMemo(() => ({
    state,
    completedSteps,
    markStepComplete,
    resetOnboarding,
    skipOnboarding,
    completeOnboarding,
    isFirstVisit,
  }), [state, completedSteps, markStepComplete, resetOnboarding, skipOnboarding, completeOnboarding, isFirstVisit]);

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  );
}

/**
 * Hook to access onboarding context
 */
export function useOnboarding(): OnboardingContextValue {
  const context = useContext(OnboardingContext);
  if (!context) {
    throw new Error('useOnboarding must be used within OnboardingProvider');
  }
  return context;
}

// =============================================================================
// WELCOME MODAL
// =============================================================================

interface WelcomeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStartTour: () => void;
  onSkip: () => void;
  userName?: string;
}

/**
 * First-run welcome modal
 */
export function WelcomeModal({
  isOpen,
  onClose,
  onStartTour,
  onSkip,
  userName,
}: WelcomeModalProps): React.ReactElement | null {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-title"
    >
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
        {/* Header with gradient */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-6 text-white">
          <h2 id="welcome-title" className="text-2xl font-bold">
            Welcome{userName ? `, ${userName}` : ''}! 👋
          </h2>
          <p className="mt-2 opacity-90">
            Let&apos;s get you started with Sensei OS
          </p>
        </div>

        {/* Content */}
        <div className="p-6">
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            We&apos;ll give you a quick tour of the key features to help you get
            productive right away.
          </p>

          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <span className="text-2xl">📋</span>
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white">Manage RFQs</h3>
                <p className="text-sm text-gray-500">Track and process customer requests</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">💰</span>
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white">Create Quotes</h3>
                <p className="text-sm text-gray-500">Build accurate pricing quotes</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">🏭</span>
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white">Production Tracking</h3>
                <p className="text-sm text-gray-500">Monitor jobs through completion</p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-between">
          <button
            type="button"
            onClick={() => {
              onSkip();
              onClose();
            }}
            className="px-4 py-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
          >
            Skip for now
          </button>
          <button
            type="button"
            onClick={() => {
              onStartTour();
              onClose();
            }}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Start Tour
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// EMPTY STATE
// =============================================================================

interface EmptyStateProps {
  type?: EmptyStateTypeType;
  icon?: string;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

/**
 * Empty state component with contextual nudges
 */
export function EmptyState({
  type = EMPTY_STATE_TYPE.NO_DATA,
  icon,
  title,
  description,
  action,
  secondaryAction,
  className = '',
}: EmptyStateProps): React.ReactElement {
  const defaultIcons: Record<EmptyStateTypeType, string> = {
    [EMPTY_STATE_TYPE.NO_DATA]: '📭',
    [EMPTY_STATE_TYPE.NO_RESULTS]: '🔍',
    [EMPTY_STATE_TYPE.NO_ACCESS]: '🔒',
    [EMPTY_STATE_TYPE.ERROR]: '⚠️',
    [EMPTY_STATE_TYPE.FIRST_TIME]: '🎉',
  };

  return (
    <div
      className={`flex flex-col items-center justify-center py-12 px-4 text-center ${className}`}
      role="status"
      aria-label={title}
    >
      <span className="text-6xl mb-4" aria-hidden="true">
        {icon || defaultIcons[type]}
      </span>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
        {title}
      </h3>
      <p className="text-gray-600 dark:text-gray-400 max-w-md mb-6">
        {description}
      </p>
      <div className="flex gap-3">
        {action && (
          <button
            type="button"
            onClick={action.onClick}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            {action.label}
          </button>
        )}
        {secondaryAction && (
          <button
            type="button"
            onClick={secondaryAction.onClick}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300"
          >
            {secondaryAction.label}
          </button>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// HELP TOOLTIP
// =============================================================================

interface HelpTooltipProps {
  term: string;
  definition: string;
  learnMoreUrl?: string;
  className?: string;
}

/**
 * Help tooltip for complex terms
 */
export function HelpTooltip({
  term,
  definition,
  learnMoreUrl,
  className = '',
}: HelpTooltipProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <span className={`relative inline-flex items-center ${className}`}>
      <span>{term}</span>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onBlur={() => setTimeout(() => setIsOpen(false), 200)}
        aria-label={`Help for ${term}`}
        aria-expanded={isOpen}
        className="ml-1 w-4 h-4 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs flex items-center justify-center hover:bg-gray-300 dark:hover:bg-gray-600"
      >
        i
      </button>
      {isOpen && (
        <div
          role="tooltip"
          className="absolute bottom-full left-0 mb-2 w-64 p-3 bg-gray-900 text-white text-sm rounded-lg shadow-lg z-50"
        >
          <p className="mb-2">{definition}</p>
          {learnMoreUrl && (
            <a
              href={learnMoreUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 underline"
            >
              Learn more →
            </a>
          )}
          <div
            className="absolute -bottom-1 left-4 w-2 h-2 bg-gray-900 transform rotate-45"
            aria-hidden="true"
          />
        </div>
      )}
    </span>
  );
}

// =============================================================================
// CONTEXTUAL HELP PANEL
// =============================================================================

interface ContextualHelpPanelProps {
  isOpen: boolean;
  onClose: () => void;
  topic?: HelpTopic;
  relatedTopics?: HelpTopic[];
}

/**
 * Contextual help side panel
 */
export function ContextualHelpPanel({
  isOpen,
  onClose,
  topic,
  relatedTopics = [],
}: ContextualHelpPanelProps): React.ReactElement | null {
  if (!isOpen) return null;

  return (
    <div
      className="fixed right-0 top-0 h-full w-80 bg-white dark:bg-gray-900 shadow-xl z-40 overflow-hidden flex flex-col"
      role="complementary"
      aria-label="Help panel"
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
        <h2 className="font-bold text-gray-900 dark:text-white">Help</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close help panel"
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {topic ? (
          <>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {topic.title}
            </h3>
            <p className="text-gray-600 dark:text-gray-300 mb-4">{topic.description}</p>
            {topic.url && (
              <a
                href={topic.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 dark:text-blue-400 underline"
              >
                View full documentation →
              </a>
            )}
          </>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">
            Select a help topic or click the help icon on any element.
          </p>
        )}

        {relatedTopics.length > 0 && (
          <div className="mt-6">
            <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">Related Topics</h4>
            <ul className="space-y-2">
              {relatedTopics.map((related) => (
                <li key={related.id}>
                  <button
                    type="button"
                    className="text-left w-full text-blue-600 hover:text-blue-800 dark:text-blue-400 hover:underline"
                  >
                    {related.title}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <a
          href="https://github.com/your-org/sensei-erp/wiki"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 w-full py-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
        >
          <span>📚</span>
          <span>Browse all documentation</span>
        </a>
      </div>
    </div>
  );
}

// =============================================================================
// SENSEI SUGGESTIONS
// =============================================================================

interface SenseiSuggestionsContextValue {
  suggestions: SenseiSuggestion[];
  addSuggestion: (suggestion: SenseiSuggestion) => void;
  dismissSuggestion: (id: string) => void;
  clearSuggestions: () => void;
}

const SenseiSuggestionsContext = createContext<SenseiSuggestionsContextValue | null>(null);

interface SenseiSuggestionsProviderProps {
  children: ReactNode;
  maxSuggestions?: number;
}

/**
 * Sensei suggestions provider
 */
export function SenseiSuggestionsProvider({
  children,
  maxSuggestions = 5,
}: SenseiSuggestionsProviderProps): React.ReactElement {
  const [suggestions, setSuggestions] = useState<SenseiSuggestion[]>([]);

  const addSuggestion = useCallback((suggestion: SenseiSuggestion) => {
    setSuggestions((prev) => {
      // Don't add duplicates
      if (prev.some((s) => s.id === suggestion.id)) return prev;
      const updated = [...prev, suggestion];
      return updated.slice(-maxSuggestions);
    });
  }, [maxSuggestions]);

  const dismissSuggestion = useCallback((id: string) => {
    setSuggestions((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const clearSuggestions = useCallback(() => {
    setSuggestions([]);
  }, []);

  const value = useMemo(() => ({
    suggestions,
    addSuggestion,
    dismissSuggestion,
    clearSuggestions,
  }), [suggestions, addSuggestion, dismissSuggestion, clearSuggestions]);

  return (
    <SenseiSuggestionsContext.Provider value={value}>
      {children}
    </SenseiSuggestionsContext.Provider>
  );
}

/**
 * Hook to access Sensei suggestions
 */
export function useSenseiSuggestions(): SenseiSuggestionsContextValue {
  const context = useContext(SenseiSuggestionsContext);
  if (!context) {
    throw new Error('useSenseiSuggestions must be used within SenseiSuggestionsProvider');
  }
  return context;
}

// =============================================================================
// SENSEI SUGGESTION CARD
// =============================================================================

interface SenseiSuggestionCardProps {
  suggestion: SenseiSuggestion;
  onDismiss?: () => void;
}

/**
 * Sensei suggestion card component
 */
export function SenseiSuggestionCard({
  suggestion,
  onDismiss,
}: SenseiSuggestionCardProps): React.ReactElement {
  const typeStyles: Record<SuggestionTypeType, { icon: string; bg: string; border: string }> = {
    [SUGGESTION_TYPE.SHORTCUT]: {
      icon: '⌨️',
      bg: 'bg-blue-50 dark:bg-blue-900/30',
      border: 'border-blue-200 dark:border-blue-800',
    },
    [SUGGESTION_TYPE.FEATURE]: {
      icon: '✨',
      bg: 'bg-purple-50 dark:bg-purple-900/30',
      border: 'border-purple-200 dark:border-purple-800',
    },
    [SUGGESTION_TYPE.TIP]: {
      icon: '💡',
      bg: 'bg-yellow-50 dark:bg-yellow-900/30',
      border: 'border-yellow-200 dark:border-yellow-800',
    },
    [SUGGESTION_TYPE.WARNING]: {
      icon: '⚠️',
      bg: 'bg-orange-50 dark:bg-orange-900/30',
      border: 'border-orange-200 dark:border-orange-800',
    },
  };

  const style = typeStyles[suggestion.type];

  return (
    <div
      className={`p-3 rounded-lg border ${style.bg} ${style.border}`}
      role="article"
      aria-label={suggestion.title}
    >
      <div className="flex items-start gap-3">
        <span className="text-xl flex-shrink-0" aria-hidden="true">{style.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start">
            <h4 className="font-medium text-gray-900 dark:text-white text-sm">
              {suggestion.title}
            </h4>
            {suggestion.dismissable !== false && onDismiss && (
              <button
                type="button"
                onClick={onDismiss}
                aria-label="Dismiss suggestion"
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex-shrink-0"
              >
                ✕
              </button>
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {suggestion.description}
          </p>
          {suggestion.action && (
            <button
              type="button"
              onClick={suggestion.action.onClick}
              className="mt-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 font-medium"
            >
              {suggestion.action.label} →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// SENSEI ASSISTANT
// =============================================================================

interface SenseiAssistantProps {
  className?: string;
}

/**
 * Sensei assistant floating widget
 */
export function SenseiAssistant({ className = '' }: SenseiAssistantProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false);
  const { suggestions, dismissSuggestion } = useSenseiSuggestions();

  return (
    <div className={`fixed bottom-4 right-4 z-40 ${className}`}>
      {/* Suggestions panel */}
      {isOpen && (
        <div className="absolute bottom-16 right-0 w-80 max-h-96 bg-white dark:bg-gray-900 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <h3 className="font-bold text-gray-900 dark:text-white">Sensei Suggestions</h3>
            <span className="text-xs text-gray-500">{suggestions.length} tips</span>
          </div>
          <div className="p-3 space-y-2 max-h-72 overflow-y-auto">
            {suggestions.length > 0 ? (
              suggestions.map((suggestion) => (
                <SenseiSuggestionCard
                  key={suggestion.id}
                  suggestion={suggestion}
                  onDismiss={() => dismissSuggestion(suggestion.id)}
                />
              ))
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-sm text-center py-4">
                No suggestions right now. Keep working!
              </p>
            )}
          </div>
        </div>
      )}

      {/* Toggle button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-label="Toggle Sensei assistant"
        className="w-14 h-14 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg hover:shadow-xl transition-shadow flex items-center justify-center text-2xl"
      >
        🥋
      </button>

      {/* Badge */}
      {suggestions.length > 0 && !isOpen && (
        <span
          className="absolute top-0 right-0 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center"
          aria-label={`${suggestions.length} suggestions`}
        >
          {suggestions.length}
        </span>
      )}
    </div>
  );
}

// =============================================================================
// KEYBOARD SHORTCUT HINT
// =============================================================================

interface KeyboardShortcutHintProps {
  keys: string[];
  description: string;
  className?: string;
}

/**
 * Keyboard shortcut display hint
 */
export function KeyboardShortcutHint({
  keys,
  description,
  className = '',
}: KeyboardShortcutHintProps): React.ReactElement {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="flex gap-1">
        {keys.map((key, index) => (
          <React.Fragment key={index}>
            <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded text-sm font-mono text-gray-700 dark:text-gray-300">
              {key}
            </kbd>
            {index < keys.length - 1 && (
              <span className="text-gray-500" aria-hidden="true">+</span>
            )}
          </React.Fragment>
        ))}
      </div>
      <span className="text-sm text-gray-600 dark:text-gray-400">{description}</span>
    </div>
  );
}

// =============================================================================
// FEATURE SPOTLIGHT
// =============================================================================

interface FeatureSpotlightProps {
  isVisible: boolean;
  onDismiss: () => void;
  title: string;
  description: string;
  featureId: string;
  position?: TourPositionType;
}

/**
 * Feature spotlight for highlighting new features
 */
export function FeatureSpotlight({
  isVisible,
  onDismiss,
  title,
  description,
  featureId,
  position = TOUR_POSITION.BOTTOM,
}: FeatureSpotlightProps): React.ReactElement | null {
  useEffect(() => {
    if (isVisible) {
      // Mark as seen after showing
      localStorage.setItem(`feature-spotlight-${featureId}`, 'seen');
    }
  }, [isVisible, featureId]);

  if (!isVisible) return null;

  const positionClasses: Record<TourPositionType, string> = {
    [TOUR_POSITION.TOP]: 'bottom-full mb-2 left-1/2 -translate-x-1/2',
    [TOUR_POSITION.BOTTOM]: 'top-full mt-2 left-1/2 -translate-x-1/2',
    [TOUR_POSITION.LEFT]: 'right-full mr-2 top-1/2 -translate-y-1/2',
    [TOUR_POSITION.RIGHT]: 'left-full ml-2 top-1/2 -translate-y-1/2',
    [TOUR_POSITION.CENTER]: 'top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2',
  };

  return (
    <div
      className={`absolute z-50 w-64 p-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg shadow-xl ${positionClasses[position]}`}
      role="alert"
    >
      <div className="flex justify-between items-start mb-2">
        <span className="text-xs font-bold uppercase tracking-wide bg-white/20 px-2 py-0.5 rounded">
          New
        </span>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="text-white/70 hover:text-white"
        >
          ✕
        </button>
      </div>
      <h4 className="font-bold mb-1">{title}</h4>
      <p className="text-sm text-white/90">{description}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="mt-3 text-sm font-medium underline hover:no-underline"
      >
        Got it
      </button>
    </div>
  );
}

// =============================================================================
// CHECKLIST
// =============================================================================

interface ChecklistItem {
  id: string;
  title: string;
  description?: string;
  isComplete: boolean;
  action?: () => void;
}

interface OnboardingChecklistProps {
  title: string;
  items: ChecklistItem[];
  onComplete?: () => void;
  className?: string;
}

/**
 * Onboarding checklist component
 */
export function OnboardingChecklist({
  title,
  items,
  onComplete,
  className = '',
}: OnboardingChecklistProps): React.ReactElement {
  const completedCount = items.filter((item) => item.isComplete).length;
  const progress = (completedCount / items.length) * 100;
  const isAllComplete = completedCount === items.length;

  useEffect(() => {
    if (isAllComplete && onComplete) {
      onComplete();
    }
  }, [isAllComplete, onComplete]);

  return (
    <div
      className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4 ${className}`}
    >
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-bold text-gray-900 dark:text-white">{title}</h3>
        <span className="text-sm text-gray-500">
          {completedCount}/{items.length}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full mb-4 overflow-hidden">
        <div
          className="h-full bg-green-500 transition-all duration-300"
          style={{ width: `${progress}%` }}
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      {/* Items */}
      <ul className="space-y-3">
        {items.map((item) => (
          <li
            key={item.id}
            className={`flex items-start gap-3 ${item.isComplete ? 'opacity-60' : ''}`}
          >
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                item.isComplete
                  ? 'bg-green-500 text-white'
                  : 'border-2 border-gray-300 dark:border-gray-600'
              }`}
              aria-hidden="true"
            >
              {item.isComplete && '✓'}
            </span>
            <div className="flex-1 min-w-0">
              <span
                className={`font-medium ${
                  item.isComplete
                    ? 'text-gray-500 line-through'
                    : 'text-gray-900 dark:text-white'
                }`}
              >
                {item.title}
              </span>
              {item.description && (
                <p className="text-sm text-gray-500 dark:text-gray-400">{item.description}</p>
              )}
            </div>
            {!item.isComplete && item.action && (
              <button
                type="button"
                onClick={item.action}
                className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 font-medium flex-shrink-0"
              >
                Start
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

// =============================================================================
// HELP SEARCH
// =============================================================================

interface HelpSearchProps {
  topics: HelpTopic[];
  onSelectTopic: (topic: HelpTopic) => void;
  placeholder?: string;
  className?: string;
}

/**
 * Help search component
 */
export function HelpSearch({
  topics,
  onSelectTopic,
  placeholder = 'Search help...',
  className = '',
}: HelpSearchProps): React.ReactElement {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredTopics = useMemo(() => {
    if (!query.trim()) return [];
    const lowerQuery = query.toLowerCase();
    return topics.filter(
      (topic) =>
        topic.title.toLowerCase().includes(lowerQuery) ||
        topic.description.toLowerCase().includes(lowerQuery) ||
        topic.keywords.some((kw) => kw.toLowerCase().includes(lowerQuery))
    ).slice(0, 5);
  }, [query, topics]);

  return (
    <div className={`relative ${className}`}>
      <div className="relative">
        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          placeholder={placeholder}
          aria-label="Search help"
          className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500"
        />
        <span
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          aria-hidden="true"
        >
          🔍
        </span>
      </div>

      {isOpen && filteredTopics.length > 0 && (
        <ul
          className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 py-1 max-h-64 overflow-y-auto"
          role="listbox"
        >
          {filteredTopics.map((topic) => (
            <li
              key={topic.id}
              role="option"
              onClick={() => {
                onSelectTopic(topic);
                setQuery('');
                setIsOpen(false);
              }}
              className="px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer"
            >
              <div className="font-medium text-gray-900 dark:text-white">{topic.title}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400 truncate">
                {topic.description}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
