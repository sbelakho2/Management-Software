/**
 * Tests for Onboarding, Help & Documentation UX Components
 * 
 * Section 19.11: Onboarding, Help & Documentation UX
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  // Constants
  TOUR_POSITION,
  ONBOARDING_STATE,
  HELP_CATEGORY,
  EMPTY_STATE_TYPE,
  SUGGESTION_TYPE,
  // Tour
  TourProvider,
  useTour,
  TourOverlay,
  // Onboarding
  OnboardingProvider,
  useOnboarding,
  WelcomeModal,
  // Empty State
  EmptyState,
  // Help
  HelpTooltip,
  ContextualHelpPanel,
  HelpSearch,
  // Sensei
  SenseiSuggestionsProvider,
  useSenseiSuggestions,
  SenseiSuggestionCard,
  SenseiAssistant,
  // Other
  KeyboardShortcutHint,
  FeatureSpotlight,
  OnboardingChecklist,
  // Types
  TourStep,
  HelpTopic,
  SenseiSuggestion,
} from '../onboarding-help';

// =============================================================================
// CONSTANTS TESTS
// =============================================================================

describe('Onboarding Help Constants', () => {
  describe('TOUR_POSITION', () => {
    it('should define all positions', () => {
      expect(TOUR_POSITION.TOP).toBe('top');
      expect(TOUR_POSITION.BOTTOM).toBe('bottom');
      expect(TOUR_POSITION.LEFT).toBe('left');
      expect(TOUR_POSITION.RIGHT).toBe('right');
      expect(TOUR_POSITION.CENTER).toBe('center');
    });
  });

  describe('ONBOARDING_STATE', () => {
    it('should define all states', () => {
      expect(ONBOARDING_STATE.NOT_STARTED).toBe('not_started');
      expect(ONBOARDING_STATE.IN_PROGRESS).toBe('in_progress');
      expect(ONBOARDING_STATE.COMPLETED).toBe('completed');
      expect(ONBOARDING_STATE.SKIPPED).toBe('skipped');
    });
  });

  describe('HELP_CATEGORY', () => {
    it('should define all categories', () => {
      expect(HELP_CATEGORY.GETTING_STARTED).toBe('getting_started');
      expect(HELP_CATEGORY.RFQ_MANAGEMENT).toBe('rfq_management');
      expect(HELP_CATEGORY.QUOTING).toBe('quoting');
      expect(HELP_CATEGORY.PRODUCTION).toBe('production');
      expect(HELP_CATEGORY.QUALITY).toBe('quality');
    });
  });

  describe('EMPTY_STATE_TYPE', () => {
    it('should define all types', () => {
      expect(EMPTY_STATE_TYPE.NO_DATA).toBe('no_data');
      expect(EMPTY_STATE_TYPE.NO_RESULTS).toBe('no_results');
      expect(EMPTY_STATE_TYPE.NO_ACCESS).toBe('no_access');
      expect(EMPTY_STATE_TYPE.ERROR).toBe('error');
      expect(EMPTY_STATE_TYPE.FIRST_TIME).toBe('first_time');
    });
  });

  describe('SUGGESTION_TYPE', () => {
    it('should define all types', () => {
      expect(SUGGESTION_TYPE.SHORTCUT).toBe('shortcut');
      expect(SUGGESTION_TYPE.FEATURE).toBe('feature');
      expect(SUGGESTION_TYPE.TIP).toBe('tip');
      expect(SUGGESTION_TYPE.WARNING).toBe('warning');
    });
  });
});

// =============================================================================
// TOUR PROVIDER TESTS
// =============================================================================

describe('TourProvider', () => {
  function TourTester() {
    const { isActive, currentStep, steps, startTour, nextStep, prevStep, endTour } = useTour();
    return (
      <div>
        <span data-testid="active">{isActive.toString()}</span>
        <span data-testid="step">{currentStep}</span>
        <span data-testid="count">{steps.length}</span>
        <button onClick={() => startTour([
          { id: '1', target: '#test', title: 'Step 1', content: 'Content 1' },
          { id: '2', target: '#test2', title: 'Step 2', content: 'Content 2' },
        ])}>Start</button>
        <button onClick={nextStep}>Next</button>
        <button onClick={prevStep}>Prev</button>
        <button onClick={endTour}>End</button>
      </div>
    );
  }

  it('should start with inactive tour', () => {
    render(
      <TourProvider>
        <TourTester />
      </TourProvider>
    );

    expect(screen.getByTestId('active')).toHaveTextContent('false');
    expect(screen.getByTestId('step')).toHaveTextContent('0');
  });

  it('should start tour with steps', async () => {
    const user = userEvent.setup();

    render(
      <TourProvider>
        <TourTester />
      </TourProvider>
    );

    await user.click(screen.getByText('Start'));

    expect(screen.getByTestId('active')).toHaveTextContent('true');
    expect(screen.getByTestId('count')).toHaveTextContent('2');
  });

  it('should navigate to next step', async () => {
    const user = userEvent.setup();

    render(
      <TourProvider>
        <TourTester />
      </TourProvider>
    );

    await user.click(screen.getByText('Start'));
    await user.click(screen.getByText('Next'));

    expect(screen.getByTestId('step')).toHaveTextContent('1');
  });

  it('should navigate to previous step', async () => {
    const user = userEvent.setup();

    render(
      <TourProvider>
        <TourTester />
      </TourProvider>
    );

    await user.click(screen.getByText('Start'));
    await user.click(screen.getByText('Next'));
    await user.click(screen.getByText('Prev'));

    expect(screen.getByTestId('step')).toHaveTextContent('0');
  });

  it('should end tour', async () => {
    const user = userEvent.setup();

    render(
      <TourProvider>
        <TourTester />
      </TourProvider>
    );

    await user.click(screen.getByText('Start'));
    await user.click(screen.getByText('End'));

    expect(screen.getByTestId('active')).toHaveTextContent('false');
  });

  it('should throw error when useTour is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TourTester />)).toThrow('useTour must be used within TourProvider');
    consoleError.mockRestore();
  });
});

// =============================================================================
// TOUR OVERLAY TESTS
// =============================================================================

describe('TourOverlay', () => {
  const mockSteps: TourStep[] = [
    { id: '1', target: '#test-element', title: 'Test Step', content: 'Test content' },
  ];

  function TourOverlayWrapper() {
    const { startTour } = useTour();
    return (
      <div>
        <div id="test-element">Target</div>
        <button onClick={() => startTour(mockSteps)}>Start Tour</button>
        <TourOverlay />
      </div>
    );
  }

  it('should not render when tour is inactive', () => {
    render(
      <TourProvider>
        <TourOverlay />
      </TourProvider>
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should render when tour is active', async () => {
    const user = userEvent.setup();

    render(
      <TourProvider>
        <TourOverlayWrapper />
      </TourProvider>
    );

    await user.click(screen.getByText('Start Tour'));

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Test Step')).toBeInTheDocument();
    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('should show step counter', async () => {
    const user = userEvent.setup();

    render(
      <TourProvider>
        <TourOverlayWrapper />
      </TourProvider>
    );

    await user.click(screen.getByText('Start Tour'));

    expect(screen.getByText('1 of 1')).toBeInTheDocument();
  });

  it('should have close button', async () => {
    const user = userEvent.setup();

    render(
      <TourProvider>
        <TourOverlayWrapper />
      </TourProvider>
    );

    await user.click(screen.getByText('Start Tour'));

    expect(screen.getByLabelText('Close tour')).toBeInTheDocument();
  });
});

// =============================================================================
// ONBOARDING PROVIDER TESTS
// =============================================================================

describe('OnboardingProvider', () => {
  function OnboardingTester() {
    const { state, completedSteps, markStepComplete, skipOnboarding, completeOnboarding, isFirstVisit } = useOnboarding();
    return (
      <div>
        <span data-testid="state">{state}</span>
        <span data-testid="steps">{completedSteps.length}</span>
        <span data-testid="first">{isFirstVisit.toString()}</span>
        <button onClick={() => markStepComplete('step1')}>Complete Step</button>
        <button onClick={skipOnboarding}>Skip</button>
        <button onClick={completeOnboarding}>Complete</button>
      </div>
    );
  }

  beforeEach(() => {
    localStorage.clear();
  });

  it('should start with not_started state', () => {
    render(
      <OnboardingProvider>
        <OnboardingTester />
      </OnboardingProvider>
    );

    expect(screen.getByTestId('state')).toHaveTextContent('not_started');
  });

  it('should track first visit', () => {
    render(
      <OnboardingProvider>
        <OnboardingTester />
      </OnboardingProvider>
    );

    expect(screen.getByTestId('first')).toHaveTextContent('true');
  });

  it('should mark steps complete', async () => {
    const user = userEvent.setup();

    render(
      <OnboardingProvider>
        <OnboardingTester />
      </OnboardingProvider>
    );

    await user.click(screen.getByText('Complete Step'));

    expect(screen.getByTestId('steps')).toHaveTextContent('1');
    expect(screen.getByTestId('state')).toHaveTextContent('in_progress');
  });

  it('should skip onboarding', async () => {
    const user = userEvent.setup();

    render(
      <OnboardingProvider>
        <OnboardingTester />
      </OnboardingProvider>
    );

    await user.click(screen.getByText('Skip'));

    expect(screen.getByTestId('state')).toHaveTextContent('skipped');
  });

  it('should complete onboarding', async () => {
    const user = userEvent.setup();

    render(
      <OnboardingProvider>
        <OnboardingTester />
      </OnboardingProvider>
    );

    await user.click(screen.getByText('Complete'));

    expect(screen.getByTestId('state')).toHaveTextContent('completed');
  });

  it('should throw error when useOnboarding is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<OnboardingTester />)).toThrow('useOnboarding must be used within OnboardingProvider');
    consoleError.mockRestore();
  });
});

// =============================================================================
// WELCOME MODAL TESTS
// =============================================================================

describe('WelcomeModal', () => {
  it('should not render when closed', () => {
    render(
      <WelcomeModal
        isOpen={false}
        onClose={() => {}}
        onStartTour={() => {}}
        onSkip={() => {}}
      />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should render when open', () => {
    render(
      <WelcomeModal
        isOpen
        onClose={() => {}}
        onStartTour={() => {}}
        onSkip={() => {}}
      />
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('should show welcome message', () => {
    render(
      <WelcomeModal
        isOpen
        onClose={() => {}}
        onStartTour={() => {}}
        onSkip={() => {}}
      />
    );

    expect(screen.getByText(/welcome/i)).toBeInTheDocument();
  });

  it('should personalize with user name', () => {
    render(
      <WelcomeModal
        isOpen
        onClose={() => {}}
        onStartTour={() => {}}
        onSkip={() => {}}
        userName="John"
      />
    );

    expect(screen.getByText(/welcome, john/i)).toBeInTheDocument();
  });

  it('should call onStartTour and onClose when starting tour', async () => {
    const onStartTour = jest.fn();
    const onClose = jest.fn();
    const user = userEvent.setup();

    render(
      <WelcomeModal
        isOpen
        onClose={onClose}
        onStartTour={onStartTour}
        onSkip={() => {}}
      />
    );

    await user.click(screen.getByText('Start Tour'));

    expect(onStartTour).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('should call onSkip and onClose when skipping', async () => {
    const onSkip = jest.fn();
    const onClose = jest.fn();
    const user = userEvent.setup();

    render(
      <WelcomeModal
        isOpen
        onClose={onClose}
        onStartTour={() => {}}
        onSkip={onSkip}
      />
    );

    await user.click(screen.getByText('Skip for now'));

    expect(onSkip).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});

// =============================================================================
// EMPTY STATE TESTS
// =============================================================================

describe('EmptyState', () => {
  it('should render title and description', () => {
    render(
      <EmptyState
        title="No data"
        description="There is no data to display"
      />
    );

    expect(screen.getByText('No data')).toBeInTheDocument();
    expect(screen.getByText('There is no data to display')).toBeInTheDocument();
  });

  it('should render default icon based on type', () => {
    render(
      <EmptyState
        type={EMPTY_STATE_TYPE.NO_RESULTS}
        title="No results"
        description="No matching results"
      />
    );

    expect(screen.getByText('🔍')).toBeInTheDocument();
  });

  it('should render custom icon', () => {
    render(
      <EmptyState
        icon="🎉"
        title="Custom"
        description="Custom state"
      />
    );

    expect(screen.getByText('🎉')).toBeInTheDocument();
  });

  it('should render action button', () => {
    const onClick = jest.fn();

    render(
      <EmptyState
        title="No data"
        description="No data available"
        action={{ label: 'Add Data', onClick }}
      />
    );

    expect(screen.getByText('Add Data')).toBeInTheDocument();
  });

  it('should call action on click', async () => {
    const onClick = jest.fn();
    const user = userEvent.setup();

    render(
      <EmptyState
        title="No data"
        description="No data available"
        action={{ label: 'Add Data', onClick }}
      />
    );

    await user.click(screen.getByText('Add Data'));
    expect(onClick).toHaveBeenCalled();
  });

  it('should render secondary action', () => {
    render(
      <EmptyState
        title="No data"
        description="No data available"
        action={{ label: 'Primary', onClick: () => {} }}
        secondaryAction={{ label: 'Secondary', onClick: () => {} }}
      />
    );

    expect(screen.getByText('Secondary')).toBeInTheDocument();
  });
});

// =============================================================================
// HELP TOOLTIP TESTS
// =============================================================================

describe('HelpTooltip', () => {
  it('should render term', () => {
    render(
      <HelpTooltip
        term="RFQ"
        definition="Request for Quote"
      />
    );

    expect(screen.getByText('RFQ')).toBeInTheDocument();
  });

  it('should render help button', () => {
    render(
      <HelpTooltip
        term="RFQ"
        definition="Request for Quote"
      />
    );

    expect(screen.getByLabelText('Help for RFQ')).toBeInTheDocument();
  });

  it('should show definition on click', async () => {
    const user = userEvent.setup();

    render(
      <HelpTooltip
        term="RFQ"
        definition="Request for Quote - A document sent to suppliers"
      />
    );

    await user.click(screen.getByLabelText('Help for RFQ'));

    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    expect(screen.getByText(/request for quote/i)).toBeInTheDocument();
  });

  it('should show learn more link when provided', async () => {
    const user = userEvent.setup();

    render(
      <HelpTooltip
        term="RFQ"
        definition="Request for Quote"
        learnMoreUrl="https://docs.example.com/rfq"
      />
    );

    await user.click(screen.getByLabelText('Help for RFQ'));

    expect(screen.getByText(/learn more/i)).toHaveAttribute('href', 'https://docs.example.com/rfq');
  });
});

// =============================================================================
// CONTEXTUAL HELP PANEL TESTS
// =============================================================================

describe('ContextualHelpPanel', () => {
  const mockTopic: HelpTopic = {
    id: '1',
    title: 'Getting Started',
    description: 'Learn the basics',
    category: HELP_CATEGORY.GETTING_STARTED,
    keywords: ['start', 'begin'],
    url: 'https://docs.example.com/start',
  };

  it('should not render when closed', () => {
    render(
      <ContextualHelpPanel
        isOpen={false}
        onClose={() => {}}
      />
    );

    expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
  });

  it('should render when open', () => {
    render(
      <ContextualHelpPanel
        isOpen
        onClose={() => {}}
      />
    );

    expect(screen.getByRole('complementary')).toBeInTheDocument();
  });

  it('should display topic content', () => {
    render(
      <ContextualHelpPanel
        isOpen
        onClose={() => {}}
        topic={mockTopic}
      />
    );

    expect(screen.getByText('Getting Started')).toBeInTheDocument();
    expect(screen.getByText('Learn the basics')).toBeInTheDocument();
  });

  it('should display related topics', () => {
    const relatedTopics: HelpTopic[] = [
      { id: '2', title: 'Next Steps', description: 'Continue', category: HELP_CATEGORY.GETTING_STARTED, keywords: [] },
    ];

    render(
      <ContextualHelpPanel
        isOpen
        onClose={() => {}}
        topic={mockTopic}
        relatedTopics={relatedTopics}
      />
    );

    expect(screen.getByText('Related Topics')).toBeInTheDocument();
    expect(screen.getByText('Next Steps')).toBeInTheDocument();
  });

  it('should call onClose when close button clicked', async () => {
    const onClose = jest.fn();
    const user = userEvent.setup();

    render(
      <ContextualHelpPanel
        isOpen
        onClose={onClose}
      />
    );

    await user.click(screen.getByLabelText('Close help panel'));
    expect(onClose).toHaveBeenCalled();
  });
});

// =============================================================================
// SENSEI SUGGESTIONS TESTS
// =============================================================================

describe('SenseiSuggestionsProvider', () => {
  function SenseiTester() {
    const { suggestions, addSuggestion, dismissSuggestion, clearSuggestions } = useSenseiSuggestions();
    return (
      <div>
        <span data-testid="count">{suggestions.length}</span>
        <button onClick={() => addSuggestion({
          id: 'test',
          type: SUGGESTION_TYPE.TIP,
          title: 'Test Tip',
          description: 'Test description',
        })}>Add</button>
        <button onClick={() => dismissSuggestion('test')}>Dismiss</button>
        <button onClick={clearSuggestions}>Clear</button>
      </div>
    );
  }

  it('should start with no suggestions', () => {
    render(
      <SenseiSuggestionsProvider>
        <SenseiTester />
      </SenseiSuggestionsProvider>
    );

    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('should add suggestions', async () => {
    const user = userEvent.setup();

    render(
      <SenseiSuggestionsProvider>
        <SenseiTester />
      </SenseiSuggestionsProvider>
    );

    await user.click(screen.getByText('Add'));
    expect(screen.getByTestId('count')).toHaveTextContent('1');
  });

  it('should not add duplicate suggestions', async () => {
    const user = userEvent.setup();

    render(
      <SenseiSuggestionsProvider>
        <SenseiTester />
      </SenseiSuggestionsProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Add'));
    expect(screen.getByTestId('count')).toHaveTextContent('1');
  });

  it('should dismiss suggestions', async () => {
    const user = userEvent.setup();

    render(
      <SenseiSuggestionsProvider>
        <SenseiTester />
      </SenseiSuggestionsProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Dismiss'));
    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('should clear all suggestions', async () => {
    const user = userEvent.setup();

    render(
      <SenseiSuggestionsProvider>
        <SenseiTester />
      </SenseiSuggestionsProvider>
    );

    await user.click(screen.getByText('Add'));
    await user.click(screen.getByText('Clear'));
    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('should throw error when useSenseiSuggestions is used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<SenseiTester />)).toThrow('useSenseiSuggestions must be used within SenseiSuggestionsProvider');
    consoleError.mockRestore();
  });
});

// =============================================================================
// SENSEI SUGGESTION CARD TESTS
// =============================================================================

describe('SenseiSuggestionCard', () => {
  const baseSuggestion: SenseiSuggestion = {
    id: 'test',
    type: SUGGESTION_TYPE.TIP,
    title: 'Pro Tip',
    description: 'This is a helpful tip',
  };

  it('should render suggestion', () => {
    render(<SenseiSuggestionCard suggestion={baseSuggestion} />);

    expect(screen.getByText('Pro Tip')).toBeInTheDocument();
    expect(screen.getByText('This is a helpful tip')).toBeInTheDocument();
  });

  it('should render dismiss button', () => {
    render(<SenseiSuggestionCard suggestion={baseSuggestion} onDismiss={() => {}} />);

    expect(screen.getByLabelText('Dismiss suggestion')).toBeInTheDocument();
  });

  it('should call onDismiss when dismiss button clicked', async () => {
    const onDismiss = jest.fn();
    const user = userEvent.setup();

    render(<SenseiSuggestionCard suggestion={baseSuggestion} onDismiss={onDismiss} />);

    await user.click(screen.getByLabelText('Dismiss suggestion'));
    expect(onDismiss).toHaveBeenCalled();
  });

  it('should render action button when provided', () => {
    const suggestion: SenseiSuggestion = {
      ...baseSuggestion,
      action: { label: 'Try it', onClick: () => {} },
    };

    render(<SenseiSuggestionCard suggestion={suggestion} />);

    expect(screen.getByText(/try it/i)).toBeInTheDocument();
  });

  it('should render appropriate style for type', () => {
    render(<SenseiSuggestionCard suggestion={{ ...baseSuggestion, type: SUGGESTION_TYPE.WARNING }} />);

    expect(screen.getByText('⚠️')).toBeInTheDocument();
  });
});

// =============================================================================
// SENSEI ASSISTANT TESTS
// =============================================================================

describe('SenseiAssistant', () => {
  it('should render toggle button', () => {
    render(
      <SenseiSuggestionsProvider>
        <SenseiAssistant />
      </SenseiSuggestionsProvider>
    );

    expect(screen.getByLabelText('Toggle Sensei assistant')).toBeInTheDocument();
  });

  it('should toggle panel on click', async () => {
    const user = userEvent.setup();

    render(
      <SenseiSuggestionsProvider>
        <SenseiAssistant />
      </SenseiSuggestionsProvider>
    );

    await user.click(screen.getByLabelText('Toggle Sensei assistant'));
    expect(screen.getByText('Sensei Suggestions')).toBeInTheDocument();
  });

  it('should show empty message when no suggestions', async () => {
    const user = userEvent.setup();

    render(
      <SenseiSuggestionsProvider>
        <SenseiAssistant />
      </SenseiSuggestionsProvider>
    );

    await user.click(screen.getByLabelText('Toggle Sensei assistant'));
    expect(screen.getByText(/no suggestions/i)).toBeInTheDocument();
  });
});

// =============================================================================
// KEYBOARD SHORTCUT HINT TESTS
// =============================================================================

describe('KeyboardShortcutHint', () => {
  it('should render keys', () => {
    render(
      <KeyboardShortcutHint
        keys={['Ctrl', 'S']}
        description="Save"
      />
    );

    expect(screen.getByText('Ctrl')).toBeInTheDocument();
    expect(screen.getByText('S')).toBeInTheDocument();
  });

  it('should render description', () => {
    render(
      <KeyboardShortcutHint
        keys={['Ctrl', 'S']}
        description="Save document"
      />
    );

    expect(screen.getByText('Save document')).toBeInTheDocument();
  });

  it('should render plus signs between keys', () => {
    render(
      <KeyboardShortcutHint
        keys={['Ctrl', 'Shift', 'S']}
        description="Save as"
      />
    );

    const plusSigns = screen.getAllByText('+');
    expect(plusSigns.length).toBe(2);
  });
});

// =============================================================================
// FEATURE SPOTLIGHT TESTS
// =============================================================================

describe('FeatureSpotlight', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should not render when not visible', () => {
    render(
      <FeatureSpotlight
        isVisible={false}
        onDismiss={() => {}}
        title="New Feature"
        description="Check this out"
        featureId="feature1"
      />
    );

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('should render when visible', () => {
    render(
      <FeatureSpotlight
        isVisible
        onDismiss={() => {}}
        title="New Feature"
        description="Check this out"
        featureId="feature1"
      />
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('should show new badge', () => {
    render(
      <FeatureSpotlight
        isVisible
        onDismiss={() => {}}
        title="New Feature"
        description="Check this out"
        featureId="feature1"
      />
    );

    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('should display title and description', () => {
    render(
      <FeatureSpotlight
        isVisible
        onDismiss={() => {}}
        title="New Feature"
        description="Check this out"
        featureId="feature1"
      />
    );

    expect(screen.getByText('New Feature')).toBeInTheDocument();
    expect(screen.getByText('Check this out')).toBeInTheDocument();
  });

  it('should call onDismiss when dismiss button clicked', async () => {
    const onDismiss = jest.fn();
    const user = userEvent.setup();

    render(
      <FeatureSpotlight
        isVisible
        onDismiss={onDismiss}
        title="New Feature"
        description="Check this out"
        featureId="feature1"
      />
    );

    await user.click(screen.getByText('Got it'));
    expect(onDismiss).toHaveBeenCalled();
  });

  it('should save to localStorage when shown', () => {
    render(
      <FeatureSpotlight
        isVisible
        onDismiss={() => {}}
        title="New Feature"
        description="Check this out"
        featureId="feature1"
      />
    );

    expect(localStorage.getItem('feature-spotlight-feature1')).toBe('seen');
  });
});

// =============================================================================
// ONBOARDING CHECKLIST TESTS
// =============================================================================

describe('OnboardingChecklist', () => {
  const mockItems = [
    { id: '1', title: 'Step 1', isComplete: false },
    { id: '2', title: 'Step 2', isComplete: true },
    { id: '3', title: 'Step 3', isComplete: false },
  ];

  it('should render title', () => {
    render(
      <OnboardingChecklist
        title="Getting Started"
        items={mockItems}
      />
    );

    expect(screen.getByText('Getting Started')).toBeInTheDocument();
  });

  it('should render all items', () => {
    render(
      <OnboardingChecklist
        title="Getting Started"
        items={mockItems}
      />
    );

    expect(screen.getByText('Step 1')).toBeInTheDocument();
    expect(screen.getByText('Step 2')).toBeInTheDocument();
    expect(screen.getByText('Step 3')).toBeInTheDocument();
  });

  it('should show progress count', () => {
    render(
      <OnboardingChecklist
        title="Getting Started"
        items={mockItems}
      />
    );

    expect(screen.getByText('1/3')).toBeInTheDocument();
  });

  it('should have progress bar', () => {
    render(
      <OnboardingChecklist
        title="Getting Started"
        items={mockItems}
      />
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should show action button for incomplete items', () => {
    const itemsWithAction = [
      { id: '1', title: 'Step 1', isComplete: false, action: () => {} },
    ];

    render(
      <OnboardingChecklist
        title="Getting Started"
        items={itemsWithAction}
      />
    );

    expect(screen.getByText('Start')).toBeInTheDocument();
  });

  it('should call onComplete when all items complete', () => {
    const onComplete = jest.fn();
    const allComplete = [
      { id: '1', title: 'Step 1', isComplete: true },
      { id: '2', title: 'Step 2', isComplete: true },
    ];

    render(
      <OnboardingChecklist
        title="Getting Started"
        items={allComplete}
        onComplete={onComplete}
      />
    );

    expect(onComplete).toHaveBeenCalled();
  });
});

// =============================================================================
// HELP SEARCH TESTS
// =============================================================================

describe('HelpSearch', () => {
  const mockTopics: HelpTopic[] = [
    { id: '1', title: 'Getting Started', description: 'Learn the basics', category: HELP_CATEGORY.GETTING_STARTED, keywords: ['start', 'begin'] },
    { id: '2', title: 'RFQ Management', description: 'Manage RFQs', category: HELP_CATEGORY.RFQ_MANAGEMENT, keywords: ['rfq', 'quote'] },
    { id: '3', title: 'Production', description: 'Track production', category: HELP_CATEGORY.PRODUCTION, keywords: ['production', 'job'] },
  ];

  it('should render search input', () => {
    render(
      <HelpSearch
        topics={mockTopics}
        onSelectTopic={() => {}}
      />
    );

    expect(screen.getByLabelText('Search help')).toBeInTheDocument();
  });

  it('should show results when typing', async () => {
    const user = userEvent.setup();

    render(
      <HelpSearch
        topics={mockTopics}
        onSelectTopic={() => {}}
      />
    );

    await user.type(screen.getByLabelText('Search help'), 'RFQ');

    expect(screen.getByText('RFQ Management')).toBeInTheDocument();
  });

  it('should search by keywords', async () => {
    const user = userEvent.setup();

    render(
      <HelpSearch
        topics={mockTopics}
        onSelectTopic={() => {}}
      />
    );

    await user.type(screen.getByLabelText('Search help'), 'quote');

    expect(screen.getByText('RFQ Management')).toBeInTheDocument();
  });

  it('should call onSelectTopic when topic clicked', async () => {
    const onSelectTopic = jest.fn();
    const user = userEvent.setup();

    render(
      <HelpSearch
        topics={mockTopics}
        onSelectTopic={onSelectTopic}
      />
    );

    await user.type(screen.getByLabelText('Search help'), 'RFQ');
    await user.click(screen.getByText('RFQ Management'));

    expect(onSelectTopic).toHaveBeenCalledWith(mockTopics[1]);
  });

  it('should limit results to 5', async () => {
    const manyTopics: HelpTopic[] = Array.from({ length: 10 }, (_, i) => ({
      id: `${i}`,
      title: `Topic ${i}`,
      description: 'Test',
      category: HELP_CATEGORY.GETTING_STARTED,
      keywords: ['test'],
    }));

    const user = userEvent.setup();

    render(
      <HelpSearch
        topics={manyTopics}
        onSelectTopic={() => {}}
      />
    );

    await user.type(screen.getByLabelText('Search help'), 'test');

    const options = screen.getAllByRole('option');
    expect(options.length).toBe(5);
  });
});
