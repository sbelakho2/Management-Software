/**
 * Onboarding Types & Constants
 * 
 * Shared types for onboarding, help, and tour components.
 */

import { ReactNode } from 'react';

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
// INTERFACES
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

export interface OnboardingChecklistItem {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface TourContextValue {
  isActive: boolean;
  currentStep: number;
  steps: TourStep[];
  startTour: (steps: TourStep[]) => void;
  endTour: () => void;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (index: number) => void;
}

export interface OnboardingContextValue {
  state: OnboardingStateType;
  completedSteps: string[];
  markStepComplete: (stepId: string) => void;
  resetOnboarding: () => void;
  skipOnboarding: () => void;
}

export interface SenseiSuggestionsContextValue {
  suggestions: SenseiSuggestion[];
  addSuggestion: (suggestion: SenseiSuggestion) => void;
  dismissSuggestion: (id: string) => void;
  clearAll: () => void;
}

export interface TourProviderProps {
  children: ReactNode;
}

export interface OnboardingProviderProps {
  children: ReactNode;
  requiredSteps?: string[];
  storageKey?: string;
}

export interface SenseiSuggestionsProviderProps {
  children: ReactNode;
}
