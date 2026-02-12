/**
 * Product Tour Components
 * 
 * Provides guided tour functionality with spotlight and tooltips.
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
} from 'react';

import {
  TourStep,
  TourContextValue,
  TourPositionType,
  TOUR_POSITION,
} from './types';
import { useI18n } from '@/contexts/i18n-context';

// =============================================================================
// TOUR CONTEXT
// =============================================================================

const TourContext = createContext<TourContextValue | null>(null);

interface TourProviderProps {
  children: ReactNode;
}

/**
 * Product tour provider
 * 
 * @example
 * ```tsx
 * <TourProvider>
 *   <App />
 *   <TourOverlay />
 * </TourProvider>
 * ```
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
// POSITION UTILITIES
// =============================================================================

interface SpotlightDimensions {
  top: number;
  left: number;
  width: number;
  height: number;
}

/**
 * Calculate position for spotlight
 */
function getSpotlightDimensions(
  target: HTMLElement | null,
  padding: number = 8
): SpotlightDimensions | null {
  if (!target) {
    return null;
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

// =============================================================================
// TOUR OVERLAY
// =============================================================================

/**
 * Tour overlay with spotlight and tooltip
 * 
 * Renders the visual overlay during a product tour, highlighting
 * the target element and showing the current step's content.
 */
export function TourOverlay(): React.ReactElement | null {
  const { isActive, currentStep, steps, nextStep, prevStep, endTour } = useTour();
  const { t } = useI18n();
  const [targetElement, setTargetElement] = useState<HTMLElement | null>(null);

  const step = steps[currentStep];

  useEffect(() => {
    if (!isActive || !step) {
      setTargetElement(null);
      return;
    }

    const element = document.querySelector(step.target) as HTMLElement | null;
    setTargetElement(element);

    // Scroll element into view
    if (element && typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [isActive, step]);

  if (!isActive || !step) return null;

  const spotlight = getSpotlightDimensions(targetElement, step.spotlightPadding);
  const tooltipStyle = getTooltipStyle(targetElement, step.position || TOUR_POSITION.BOTTOM);

  // Build clip path string for spotlight cutout
  const clipPath = spotlight
    ? `polygon(
        0% 0%,
        0% 100%,
        ${spotlight.left}px 100%,
        ${spotlight.left}px ${spotlight.top}px,
        ${spotlight.left + spotlight.width}px ${spotlight.top}px,
        ${spotlight.left + spotlight.width}px ${spotlight.top + spotlight.height}px,
        ${spotlight.left}px ${spotlight.top + spotlight.height}px,
        ${spotlight.left}px 100%,
        100% 100%,
        100% 0%
      )`
    : undefined;

  return (
    <div className="fixed inset-0 z-[9999]" role="dialog" aria-modal="true" aria-label={t('tour.productTour')}>
      {/* Overlay with spotlight cutout */}
      <div
        className="absolute inset-0 bg-black/50"
        style={{ clipPath }}
        onClick={endTour}
        aria-hidden="true"
      />

      {/* Spotlight border */}
      {spotlight && (
        <div
          className="absolute border-2 border-blue-500 rounded-lg pointer-events-none"
          style={{
            top: spotlight.top,
            left: spotlight.left,
            width: spotlight.width,
            height: spotlight.height,
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
            aria-label={t('tour.closeTour')}
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
            {t('tour.stepOf', { current: String(currentStep + 1), total: String(steps.length) })}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={prevStep}
              disabled={currentStep === 0}
              className="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('tour.back')}
            </button>
            <button
              type="button"
              onClick={nextStep}
              className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              {currentStep === steps.length - 1 ? t('tour.finish') : t('tour.next')}
            </button>
          </div>
        </div>

        {/* Progress dots */}
        <div className="flex justify-center gap-1 mt-3">
          {steps.map((s, index) => (
            <div
              key={s.id}
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

export { TourContext };
