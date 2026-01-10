import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import {
  // Constants
  MATURITY_LEVELS,
  MATURITY_LEVEL_NAMES,
  MATURITY_LEVEL_DESCRIPTIONS,
  FEATURE_REQUIREMENTS,
  // Feature utilities
  isFeatureAvailable,
  getAvailableFeatures,
  getNextLevelFeatures,
  // Level-up utilities
  checkLevelUpRequirements,
  // Leakage audit
  auditFeatureLeakage,
  runFullLeakageAudit,
  // Context
  MaturityProvider,
  useMaturity,
  // Components
  MaturityLevelIndicator,
  FeatureGate,
  LevelUpButton,
  RehearsalModeBanner,
  SandboxModeBanner,
  MaturityDashboard,
  // SAT utilities
  createSATChecklist,
  updateSATChecklistItem,
  getOfflineCapableItems,
  getSATCompletionPercentage,
  // IoT utilities
  normalizeMacAddress,
  isValidMacAddress,
  linkDeviceToStation,
  // Types
  MaturityLevel,
  DataStatus,
  IoTDevice,
} from '../deployment-maturity';

// =============================================================================
// MATURITY LEVEL CONSTANTS TESTS
// =============================================================================

describe('Maturity Level Constants', () => {
  test('should have 5 maturity levels (0-4)', () => {
    expect(MATURITY_LEVELS.LEVEL_0).toBe(0);
    expect(MATURITY_LEVELS.LEVEL_1).toBe(1);
    expect(MATURITY_LEVELS.LEVEL_2).toBe(2);
    expect(MATURITY_LEVELS.LEVEL_3).toBe(3);
    expect(MATURITY_LEVELS.LEVEL_4).toBe(4);
  });

  test('should have names for all levels', () => {
    expect(MATURITY_LEVEL_NAMES[0]).toBe('Pre-Deployment');
    expect(MATURITY_LEVEL_NAMES[1]).toBe('Basic Operations');
    expect(MATURITY_LEVEL_NAMES[2]).toBe('Standard Operations');
    expect(MATURITY_LEVEL_NAMES[3]).toBe('Advanced Operations');
    expect(MATURITY_LEVEL_NAMES[4]).toBe('Full TPS');
  });

  test('should have descriptions for all levels', () => {
    expect(MATURITY_LEVEL_DESCRIPTIONS[0]).toContain('configuration');
    expect(MATURITY_LEVEL_DESCRIPTIONS[1]).toContain('sales');
    expect(MATURITY_LEVEL_DESCRIPTIONS[2]).toContain('production');
    expect(MATURITY_LEVEL_DESCRIPTIONS[3]).toContain('TPS');
    expect(MATURITY_LEVEL_DESCRIPTIONS[4]).toContain('executive');
  });
});

// =============================================================================
// FEATURE REQUIREMENTS TESTS
// =============================================================================

describe('Feature Requirements', () => {
  test('should have features defined', () => {
    expect(FEATURE_REQUIREMENTS.length).toBeGreaterThan(10);
  });

  test('should have Level 0 features (admin)', () => {
    const level0Features = FEATURE_REQUIREMENTS.filter((f) => f.requiredLevel === 0);
    expect(level0Features.length).toBeGreaterThan(0);
    expect(level0Features.some((f) => f.id === 'system-settings')).toBe(true);
  });

  test('should have Level 1 features (sales)', () => {
    const level1Features = FEATURE_REQUIREMENTS.filter((f) => f.requiredLevel === 1);
    expect(level1Features.length).toBeGreaterThan(0);
    expect(level1Features.some((f) => f.id === 'customer-list')).toBe(true);
  });

  test('should have Level 2 features (production)', () => {
    const level2Features = FEATURE_REQUIREMENTS.filter((f) => f.requiredLevel === 2);
    expect(level2Features.length).toBeGreaterThan(0);
    expect(level2Features.some((f) => f.id === 'work-orders')).toBe(true);
  });

  test('should have Level 3 features (TPS)', () => {
    const level3Features = FEATURE_REQUIREMENTS.filter((f) => f.requiredLevel === 3);
    expect(level3Features.length).toBeGreaterThan(0);
    expect(level3Features.some((f) => f.id === 'andon')).toBe(true);
  });

  test('should have Level 4 features (executive)', () => {
    const level4Features = FEATURE_REQUIREMENTS.filter((f) => f.requiredLevel === 4);
    expect(level4Features.length).toBeGreaterThan(0);
    expect(level4Features.some((f) => f.id === 'exec-dashboard')).toBe(true);
  });

  test('should have data requirements for some features', () => {
    const featuresWithData = FEATURE_REQUIREMENTS.filter((f) => f.dataRequirements);
    expect(featuresWithData.length).toBeGreaterThan(0);
  });
});

// =============================================================================
// FEATURE AVAILABILITY TESTS
// =============================================================================

describe('isFeatureAvailable', () => {
  test('should return true for available features', () => {
    expect(isFeatureAvailable('system-settings', 0)).toBe(true);
    expect(isFeatureAvailable('customer-list', 1)).toBe(true);
    expect(isFeatureAvailable('work-orders', 2)).toBe(true);
    expect(isFeatureAvailable('andon', 3)).toBe(true);
    expect(isFeatureAvailable('exec-dashboard', 4)).toBe(true);
  });

  test('should return false for unavailable features', () => {
    expect(isFeatureAvailable('customer-list', 0)).toBe(false);
    expect(isFeatureAvailable('work-orders', 1)).toBe(false);
    expect(isFeatureAvailable('andon', 2)).toBe(false);
    expect(isFeatureAvailable('exec-dashboard', 3)).toBe(false);
  });

  test('should return true for features at lower levels', () => {
    // Level 4 should have access to all features
    expect(isFeatureAvailable('system-settings', 4)).toBe(true);
    expect(isFeatureAvailable('customer-list', 4)).toBe(true);
    expect(isFeatureAvailable('work-orders', 4)).toBe(true);
  });

  test('should return false for unknown features', () => {
    expect(isFeatureAvailable('unknown-feature', 4)).toBe(false);
  });
});

describe('getAvailableFeatures', () => {
  test('should return only Level 0 features at Level 0', () => {
    const features = getAvailableFeatures(0);
    expect(features.every((f) => f.requiredLevel <= 0)).toBe(true);
  });

  test('should return Level 0-1 features at Level 1', () => {
    const features = getAvailableFeatures(1);
    expect(features.every((f) => f.requiredLevel <= 1)).toBe(true);
    expect(features.length).toBeGreaterThan(getAvailableFeatures(0).length);
  });

  test('should return all features at Level 4', () => {
    const features = getAvailableFeatures(4);
    expect(features.length).toBe(FEATURE_REQUIREMENTS.length);
  });
});

describe('getNextLevelFeatures', () => {
  test('should return Level 1 features when at Level 0', () => {
    const features = getNextLevelFeatures(0);
    expect(features.every((f) => f.requiredLevel === 1)).toBe(true);
    expect(features.length).toBeGreaterThan(0);
  });

  test('should return Level 2 features when at Level 1', () => {
    const features = getNextLevelFeatures(1);
    expect(features.every((f) => f.requiredLevel === 2)).toBe(true);
  });

  test('should return empty array at Level 4', () => {
    const features = getNextLevelFeatures(4);
    expect(features).toEqual([]);
  });
});

// =============================================================================
// LEVEL-UP REQUIREMENTS TESTS
// =============================================================================

describe('checkLevelUpRequirements', () => {
  test('should allow level-up when no data requirements', () => {
    const result = checkLevelUpRequirements(1, {});
    expect(result.canLevelUp).toBe(true);
    expect(result.missingData).toEqual([]);
    expect(result.targetLevel).toBe(1);
  });

  test('should block level-up when data requirements not met', () => {
    const result = checkLevelUpRequirements(2, {});
    // Level 2 requires site-design and stations
    expect(result.canLevelUp).toBe(false);
    expect(result.missingData.length).toBeGreaterThan(0);
  });

  test('should allow level-up when data requirements are met', () => {
    const dataStatuses: Record<string, DataStatus> = {
      'site-design': { id: 'site-design', name: 'Site Design', isComplete: true, completionPercentage: 100 },
      'stations': { id: 'stations', name: 'Stations', isComplete: true, completionPercentage: 100 },
    };
    const result = checkLevelUpRequirements(2, dataStatuses);
    expect(result.canLevelUp).toBe(true);
  });

  test('should return incomplete data status', () => {
    const dataStatuses: Record<string, DataStatus> = {
      'site-design': { id: 'site-design', name: 'Site Design', isComplete: false, completionPercentage: 50 },
    };
    const result = checkLevelUpRequirements(2, dataStatuses);
    expect(result.canLevelUp).toBe(false);
    expect(result.missingData.some((d) => d.id === 'site-design')).toBe(true);
  });
});

// =============================================================================
// LEAKAGE AUDIT TESTS
// =============================================================================

describe('auditFeatureLeakage', () => {
  test('should detect leakage in search results', () => {
    const results = auditFeatureLeakage('exec-dashboard', 0, {
      searchResults: ['Executive Dashboard', 'User Settings'],
    });
    expect(results.find((r) => r.type === 'search')?.isLeaking).toBe(true);
  });

  test('should detect no leakage when feature not in search', () => {
    const results = auditFeatureLeakage('exec-dashboard', 0, {
      searchResults: ['User Settings', 'Profile'],
    });
    expect(results.find((r) => r.type === 'search')?.isLeaking).toBe(false);
  });

  test('should detect leakage in command palette', () => {
    const results = auditFeatureLeakage('andon', 0, {
      commandPaletteItems: ['Andon System', 'Open Settings'],
    });
    expect(results.find((r) => r.type === 'command-palette')?.isLeaking).toBe(true);
  });

  test('should detect leakage in routes', () => {
    const results = auditFeatureLeakage('work-orders', 0, {
      accessibleRoutes: ['/dashboard', '/work-orders'],
    });
    expect(results.find((r) => r.type === 'deep-link')?.isLeaking).toBe(true);
  });

  test('should detect leakage in API endpoints', () => {
    const results = auditFeatureLeakage('kaizen', 0, {
      apiEndpoints: ['/api/users', '/api/kaizen/events'],
    });
    expect(results.find((r) => r.type === 'api')?.isLeaking).toBe(true);
  });

  test('should return empty for available features', () => {
    const results = auditFeatureLeakage('system-settings', 0, {
      searchResults: ['System Settings'],
    });
    expect(results).toEqual([]);
  });
});

describe('runFullLeakageAudit', () => {
  test('should audit all features', () => {
    const audit = runFullLeakageAudit(0, {
      searchResults: ['Executive Dashboard'],
    });
    expect(audit.results.length).toBeGreaterThan(0);
  });

  test('should count total leaks', () => {
    const audit = runFullLeakageAudit(0, {
      searchResults: ['Executive Dashboard', 'Andon System', 'Kaizen Events'],
    });
    expect(audit.totalLeaks).toBeGreaterThanOrEqual(3);
  });

  test('should have no leaks when access points are clean', () => {
    const audit = runFullLeakageAudit(4, {
      searchResults: ['Everything is accessible'],
    });
    // At level 4, nothing should leak because everything is available
    expect(audit.totalLeaks).toBe(0);
  });
});

// =============================================================================
// MATURITY PROVIDER TESTS
// =============================================================================

describe('MaturityProvider', () => {
  test('should provide context to children', () => {
    const TestComponent = () => {
      const context = useMaturity();
      return <div data-testid="level">{context.currentLevel}</div>;
    };

    render(
      <MaturityProvider>
        <TestComponent />
      </MaturityProvider>
    );

    expect(screen.getByTestId('level')).toHaveTextContent('0');
  });

  test('should throw error when used outside provider', () => {
    const TestComponent = () => {
      useMaturity();
      return null;
    };

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestComponent />)).toThrow('useMaturity must be used within a MaturityProvider');
    consoleSpy.mockRestore();
  });

  test('should use initial level', () => {
    const TestComponent = () => {
      const { currentLevel } = useMaturity();
      return <div data-testid="level">{currentLevel}</div>;
    };

    render(
      <MaturityProvider initialLevel={2}>
        <TestComponent />
      </MaturityProvider>
    );

    expect(screen.getByTestId('level')).toHaveTextContent('2');
  });

  test('should set level', () => {
    const onLevelChange = jest.fn();
    const TestComponent = () => {
      const { currentLevel, setLevel } = useMaturity();
      return (
        <div>
          <button onClick={() => setLevel(3)}>Set Level</button>
          <span data-testid="level">{currentLevel}</span>
        </div>
      );
    };

    render(
      <MaturityProvider onLevelChange={onLevelChange}>
        <TestComponent />
      </MaturityProvider>
    );

    fireEvent.click(screen.getByText('Set Level'));
    expect(screen.getByTestId('level')).toHaveTextContent('3');
    expect(onLevelChange).toHaveBeenCalledWith(3);
  });

  test('should check feature availability', () => {
    const TestComponent = () => {
      const { isFeatureAvailable } = useMaturity();
      return (
        <div>
          <span data-testid="settings">{isFeatureAvailable('system-settings') ? 'yes' : 'no'}</span>
          <span data-testid="dashboard">{isFeatureAvailable('exec-dashboard') ? 'yes' : 'no'}</span>
        </div>
      );
    };

    render(
      <MaturityProvider initialLevel={0}>
        <TestComponent />
      </MaturityProvider>
    );

    expect(screen.getByTestId('settings')).toHaveTextContent('yes');
    expect(screen.getByTestId('dashboard')).toHaveTextContent('no');
  });

  test('should manage rehearsal mode', () => {
    const TestComponent = () => {
      const { rehearsalMode, setRehearsalMode } = useMaturity();
      return (
        <div>
          <button onClick={() => setRehearsalMode(true)}>Enable</button>
          <button onClick={() => setRehearsalMode(false)}>Disable</button>
          <span data-testid="mode">{rehearsalMode ? 'on' : 'off'}</span>
        </div>
      );
    };

    render(
      <MaturityProvider>
        <TestComponent />
      </MaturityProvider>
    );

    expect(screen.getByTestId('mode')).toHaveTextContent('off');
    
    fireEvent.click(screen.getByText('Enable'));
    expect(screen.getByTestId('mode')).toHaveTextContent('on');
    
    fireEvent.click(screen.getByText('Disable'));
    expect(screen.getByTestId('mode')).toHaveTextContent('off');
  });

  test('should manage sandbox mode', () => {
    const TestComponent = () => {
      const { sandboxMode, setSandboxMode } = useMaturity();
      return (
        <div>
          <button onClick={() => setSandboxMode(true)}>Enable</button>
          <span data-testid="mode">{sandboxMode ? 'on' : 'off'}</span>
        </div>
      );
    };

    render(
      <MaturityProvider>
        <TestComponent />
      </MaturityProvider>
    );

    fireEvent.click(screen.getByText('Enable'));
    expect(screen.getByTestId('mode')).toHaveTextContent('on');
  });

  test('should manage data statuses', () => {
    const TestComponent = () => {
      const { dataStatuses, setDataStatus } = useMaturity();
      return (
        <div>
          <button
            onClick={() =>
              setDataStatus('site-design', {
                id: 'site-design',
                name: 'Site Design',
                isComplete: true,
                completionPercentage: 100,
              })
            }
          >
            Complete Data
          </button>
          <span data-testid="status">
            {dataStatuses['site-design']?.isComplete ? 'complete' : 'incomplete'}
          </span>
        </div>
      );
    };

    render(
      <MaturityProvider>
        <TestComponent />
      </MaturityProvider>
    );

    expect(screen.getByTestId('status')).toHaveTextContent('incomplete');
    
    fireEvent.click(screen.getByText('Complete Data'));
    expect(screen.getByTestId('status')).toHaveTextContent('complete');
  });
});

// =============================================================================
// LEVEL-UP FUNCTIONALITY TESTS
// =============================================================================

describe('Level-Up Functionality', () => {
  test('should level up successfully', async () => {
    const onLevelUp = jest.fn();
    const TestComponent = () => {
      const { currentLevel, levelUp, lastLevelUpResult } = useMaturity();
      return (
        <div>
          <button onClick={() => levelUp()}>Level Up</button>
          <span data-testid="level">{currentLevel}</span>
          <span data-testid="result">{lastLevelUpResult?.success ? 'success' : 'pending'}</span>
        </div>
      );
    };

    render(
      <MaturityProvider onLevelUp={onLevelUp}>
        <TestComponent />
      </MaturityProvider>
    );

    fireEvent.click(screen.getByText('Level Up'));

    await waitFor(() => {
      expect(screen.getByTestId('level')).toHaveTextContent('1');
      expect(screen.getByTestId('result')).toHaveTextContent('success');
    });

    expect(onLevelUp).toHaveBeenCalled();
    expect(onLevelUp.mock.calls[0][0].success).toBe(true);
  });

  test('should fail level-up when at max level', async () => {
    const TestComponent = () => {
      const { levelUp, lastLevelUpResult } = useMaturity();
      return (
        <div>
          <button onClick={() => levelUp()}>Level Up</button>
          <span data-testid="result">{lastLevelUpResult?.success ? 'success' : 'failed'}</span>
          <span data-testid="error">{lastLevelUpResult?.errors?.[0] ?? 'none'}</span>
        </div>
      );
    };

    render(
      <MaturityProvider initialLevel={4}>
        <TestComponent />
      </MaturityProvider>
    );

    fireEvent.click(screen.getByText('Level Up'));

    await waitFor(() => {
      expect(screen.getByTestId('result')).toHaveTextContent('failed');
      expect(screen.getByTestId('error')).toHaveTextContent('maximum');
    });
  });

  test('should fail level-up when data requirements not met', async () => {
    const TestComponent = () => {
      const { levelUp, lastLevelUpResult } = useMaturity();
      return (
        <div>
          <button onClick={() => levelUp()}>Level Up</button>
          <span data-testid="result">{lastLevelUpResult?.success ? 'success' : 'failed'}</span>
          <span data-testid="errors">{lastLevelUpResult?.errors?.length ?? 0}</span>
        </div>
      );
    };

    render(
      <MaturityProvider initialLevel={1}>
        <TestComponent />
      </MaturityProvider>
    );

    fireEvent.click(screen.getByText('Level Up'));

    await waitFor(() => {
      expect(screen.getByTestId('result')).toHaveTextContent('failed');
      expect(Number(screen.getByTestId('errors').textContent)).toBeGreaterThan(0);
    });
  });

  test('should track level-up duration', async () => {
    const TestComponent = () => {
      const { levelUp, lastLevelUpResult } = useMaturity();
      return (
        <div>
          <button onClick={() => levelUp()}>Level Up</button>
          <span data-testid="duration">{lastLevelUpResult?.duration ?? 0}</span>
        </div>
      );
    };

    render(
      <MaturityProvider>
        <TestComponent />
      </MaturityProvider>
    );

    fireEvent.click(screen.getByText('Level Up'));

    await waitFor(() => {
      const duration = Number(screen.getByTestId('duration').textContent);
      expect(duration).toBeGreaterThan(0);
    });
  });
});

// =============================================================================
// MATURITY LEVEL INDICATOR TESTS
// =============================================================================

describe('MaturityLevelIndicator', () => {
  test('should display current level', () => {
    render(
      <MaturityProvider initialLevel={2}>
        <MaturityLevelIndicator />
      </MaturityProvider>
    );

    expect(screen.getByText('Maturity Level 2')).toBeInTheDocument();
    expect(screen.getByText('Standard Operations')).toBeInTheDocument();
    expect(screen.getByText('L2')).toBeInTheDocument();
  });

  test('should display level description', () => {
    render(
      <MaturityProvider initialLevel={1}>
        <MaturityLevelIndicator />
      </MaturityProvider>
    );

    expect(screen.getByText(/Basic sales and customer management/)).toBeInTheDocument();
  });

  test('should show progress bar', () => {
    render(
      <MaturityProvider initialLevel={2}>
        <MaturityLevelIndicator showProgress={true} />
      </MaturityProvider>
    );

    expect(screen.getByText('50%')).toBeInTheDocument(); // 2/4 = 50%
  });

  test('should hide progress bar when disabled', () => {
    render(
      <MaturityProvider initialLevel={2}>
        <MaturityLevelIndicator showProgress={false} />
      </MaturityProvider>
    );

    expect(screen.queryByText('Progress')).not.toBeInTheDocument();
  });

  test('should show next level features', () => {
    render(
      <MaturityProvider initialLevel={0}>
        <MaturityLevelIndicator showNextFeatures={true} />
      </MaturityProvider>
    );

    expect(screen.getByText('Next Level Unlocks:')).toBeInTheDocument();
  });

  test('should hide next level features when disabled', () => {
    render(
      <MaturityProvider initialLevel={0}>
        <MaturityLevelIndicator showNextFeatures={false} />
      </MaturityProvider>
    );

    expect(screen.queryByText('Next Level Unlocks:')).not.toBeInTheDocument();
  });

  test('should render compact mode', () => {
    render(
      <MaturityProvider initialLevel={3}>
        <MaturityLevelIndicator compact={true} />
      </MaturityProvider>
    );

    expect(screen.getByText('L3')).toBeInTheDocument();
    expect(screen.getByText('Advanced Operations')).toBeInTheDocument();
    expect(screen.queryByText('Progress')).not.toBeInTheDocument();
  });
});

// =============================================================================
// FEATURE GATE TESTS
// =============================================================================

describe('FeatureGate', () => {
  test('should render children when feature is available', () => {
    render(
      <MaturityProvider initialLevel={0}>
        <FeatureGate featureId="system-settings">
          <div data-testid="content">Feature Content</div>
        </FeatureGate>
      </MaturityProvider>
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
  });

  test('should show blocked message when feature is unavailable', () => {
    render(
      <MaturityProvider initialLevel={0}>
        <FeatureGate featureId="exec-dashboard">
          <div data-testid="content">Feature Content</div>
        </FeatureGate>
      </MaturityProvider>
    );

    expect(screen.queryByTestId('content')).not.toBeInTheDocument();
    expect(screen.getByText('🔒')).toBeInTheDocument();
    expect(screen.getByText(/Locked/)).toBeInTheDocument();
  });

  test('should show fallback when provided', () => {
    render(
      <MaturityProvider initialLevel={0}>
        <FeatureGate featureId="andon" fallback={<div data-testid="fallback">Not Available</div>}>
          <div data-testid="content">Andon</div>
        </FeatureGate>
      </MaturityProvider>
    );

    expect(screen.queryByTestId('content')).not.toBeInTheDocument();
    expect(screen.getByTestId('fallback')).toBeInTheDocument();
  });

  test('should hide blocked message when showBlockedMessage is false', () => {
    render(
      <MaturityProvider initialLevel={0}>
        <FeatureGate featureId="andon" showBlockedMessage={false}>
          <div data-testid="content">Andon</div>
        </FeatureGate>
      </MaturityProvider>
    );

    expect(screen.queryByTestId('content')).not.toBeInTheDocument();
    expect(screen.queryByText('🔒')).not.toBeInTheDocument();
  });

  test('should show required level in blocked message', () => {
    render(
      <MaturityProvider initialLevel={0}>
        <FeatureGate featureId="andon">
          <div>Content</div>
        </FeatureGate>
      </MaturityProvider>
    );

    expect(screen.getByText(/Requires Maturity Level 3/)).toBeInTheDocument();
  });
});

// =============================================================================
// LEVEL UP BUTTON TESTS
// =============================================================================

describe('LevelUpButton', () => {
  test('should render level-up button', () => {
    render(
      <MaturityProvider initialLevel={0}>
        <LevelUpButton />
      </MaturityProvider>
    );

    expect(screen.getByText('Level Up to L1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Level Up' })).toBeInTheDocument();
  });

  test('should show next level name', () => {
    render(
      <MaturityProvider initialLevel={1}>
        <LevelUpButton />
      </MaturityProvider>
    );

    expect(screen.getByText('Level Up to L2')).toBeInTheDocument();
    expect(screen.getByText('Standard Operations')).toBeInTheDocument();
  });

  test('should disable button when requirements not met', () => {
    render(
      <MaturityProvider initialLevel={1}>
        <LevelUpButton />
      </MaturityProvider>
    );

    expect(screen.getByRole('button', { name: 'Level Up' })).toBeDisabled();
  });

  test('should show missing requirements', () => {
    render(
      <MaturityProvider initialLevel={1}>
        <LevelUpButton showRequirements={true} />
      </MaturityProvider>
    );

    expect(screen.getByText('Missing Requirements:')).toBeInTheDocument();
  });

  test('should show max level message at Level 4', () => {
    render(
      <MaturityProvider initialLevel={4}>
        <LevelUpButton />
      </MaturityProvider>
    );

    expect(screen.getByText('🎉')).toBeInTheDocument();
    expect(screen.getByText('Maximum Level Achieved!')).toBeInTheDocument();
  });

  test('should trigger level-up on click', async () => {
    render(
      <MaturityProvider initialLevel={0}>
        <LevelUpButton />
      </MaturityProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Level Up' }));

    await waitFor(() => {
      expect(screen.getByText('Level Up to L2')).toBeInTheDocument();
    });
  });
});

// =============================================================================
// REHEARSAL MODE BANNER TESTS
// =============================================================================

describe('RehearsalModeBanner', () => {
  test('should not render when rehearsal mode is off', () => {
    const { container } = render(
      <MaturityProvider>
        <RehearsalModeBanner />
      </MaturityProvider>
    );

    expect(container.firstChild).toBeNull();
  });

  test('should render when rehearsal mode is on', () => {
    const TestComponent = () => {
      const { setRehearsalMode } = useMaturity();
      React.useEffect(() => {
        setRehearsalMode(true);
      }, [setRehearsalMode]);
      return <RehearsalModeBanner />;
    };

    render(
      <MaturityProvider>
        <TestComponent />
      </MaturityProvider>
    );

    expect(screen.getByText('🎭')).toBeInTheDocument();
    expect(screen.getByText('Rehearsal Mode Active')).toBeInTheDocument();
  });

  test('should exit rehearsal mode on button click', () => {
    const TestComponent = () => {
      const { rehearsalMode, setRehearsalMode } = useMaturity();
      React.useEffect(() => {
        setRehearsalMode(true);
      }, [setRehearsalMode]);
      return (
        <div>
          <RehearsalModeBanner />
          <span data-testid="mode">{rehearsalMode ? 'on' : 'off'}</span>
        </div>
      );
    };

    render(
      <MaturityProvider>
        <TestComponent />
      </MaturityProvider>
    );

    fireEvent.click(screen.getByText('Exit Rehearsal'));
    expect(screen.getByTestId('mode')).toHaveTextContent('off');
  });
});

// =============================================================================
// SANDBOX MODE BANNER TESTS
// =============================================================================

describe('SandboxModeBanner', () => {
  test('should not render when sandbox mode is off', () => {
    const { container } = render(
      <MaturityProvider>
        <SandboxModeBanner />
      </MaturityProvider>
    );

    expect(container.firstChild).toBeNull();
  });

  test('should render when sandbox mode is on', () => {
    const TestComponent = () => {
      const { setSandboxMode } = useMaturity();
      React.useEffect(() => {
        setSandboxMode(true);
      }, [setSandboxMode]);
      return <SandboxModeBanner />;
    };

    render(
      <MaturityProvider>
        <TestComponent />
      </MaturityProvider>
    );

    expect(screen.getByText('🏖️')).toBeInTheDocument();
    expect(screen.getByText('Sandbox Mode Active')).toBeInTheDocument();
  });

  test('should mention Andon isolation', () => {
    const TestComponent = () => {
      const { setSandboxMode } = useMaturity();
      React.useEffect(() => {
        setSandboxMode(true);
      }, [setSandboxMode]);
      return <SandboxModeBanner />;
    };

    render(
      <MaturityProvider>
        <TestComponent />
      </MaturityProvider>
    );

    expect(screen.getByText(/Andon and alerts are isolated/)).toBeInTheDocument();
  });
});

// =============================================================================
// MATURITY DASHBOARD TESTS
// =============================================================================

describe('MaturityDashboard', () => {
  test('should render dashboard components', () => {
    render(
      <MaturityProvider initialLevel={2}>
        <MaturityDashboard />
      </MaturityProvider>
    );

    expect(screen.getByText('Maturity Level 2')).toBeInTheDocument();
    expect(screen.getByText('Level Up to L3')).toBeInTheDocument();
  });

  test('should show feature categories', () => {
    render(
      <MaturityProvider initialLevel={2}>
        <MaturityDashboard />
      </MaturityProvider>
    );

    expect(screen.getByText('Available Features by Category')).toBeInTheDocument();
  });

  test('should display category icons', () => {
    render(
      <MaturityProvider initialLevel={2}>
        <MaturityDashboard />
      </MaturityProvider>
    );

    expect(screen.getByText('💰')).toBeInTheDocument(); // sales
    expect(screen.getByText('🏭')).toBeInTheDocument(); // production
    expect(screen.getByText('⚙️')).toBeInTheDocument(); // admin
  });
});

// =============================================================================
// SAT UTILITIES TESTS
// =============================================================================

describe('SAT Checklist Utilities', () => {
  test('should create SAT checklist with default items', () => {
    const checklist = createSATChecklist('site-1', 'Factory A');
    expect(checklist.siteId).toBe('site-1');
    expect(checklist.siteName).toBe('Factory A');
    expect(checklist.items.length).toBeGreaterThan(10);
    expect(checklist.overallStatus).toBe('not-started');
  });

  test('should have items in all categories', () => {
    const checklist = createSATChecklist('site-1', 'Factory A');
    const categories = new Set(checklist.items.map((i) => i.category));
    expect(categories.has('network')).toBe(true);
    expect(categories.has('hardware')).toBe(true);
    expect(categories.has('software')).toBe(true);
    expect(categories.has('integration')).toBe(true);
    expect(categories.has('training')).toBe(true);
  });

  test('should update checklist item', () => {
    let checklist = createSATChecklist('site-1', 'Factory A');
    const itemId = checklist.items[0].id;

    checklist = updateSATChecklistItem(checklist, itemId, {
      completed: true,
      completedBy: 'admin',
    });

    const item = checklist.items.find((i) => i.id === itemId);
    expect(item?.completed).toBe(true);
    expect(item?.completedBy).toBe('admin');
    expect(item?.completedAt).toBeDefined();
  });

  test('should update overall status on item update', () => {
    let checklist = createSATChecklist('site-1', 'Factory A');
    expect(checklist.overallStatus).toBe('not-started');

    checklist = updateSATChecklistItem(checklist, checklist.items[0].id, { completed: true });
    expect(checklist.overallStatus).toBe('in-progress');
  });

  test('should mark checklist complete when all items done', () => {
    let checklist = createSATChecklist('site-1', 'Factory A');

    for (const item of checklist.items) {
      checklist = updateSATChecklistItem(checklist, item.id, { completed: true });
    }

    expect(checklist.overallStatus).toBe('completed');
    expect(checklist.completedAt).toBeDefined();
  });

  test('should get offline-capable items', () => {
    const checklist = createSATChecklist('site-1', 'Factory A');
    const offlineItems = getOfflineCapableItems(checklist);

    expect(offlineItems.length).toBeGreaterThan(0);
    expect(offlineItems.every((i) => i.offlineCapable)).toBe(true);
  });

  test('should calculate completion percentage', () => {
    let checklist = createSATChecklist('site-1', 'Factory A');
    expect(getSATCompletionPercentage(checklist)).toBe(0);

    // Complete half the items
    const halfCount = Math.floor(checklist.items.length / 2);
    for (let i = 0; i < halfCount; i++) {
      checklist = updateSATChecklistItem(checklist, checklist.items[i].id, { completed: true });
    }

    const percentage = getSATCompletionPercentage(checklist);
    expect(percentage).toBeCloseTo((halfCount / checklist.items.length) * 100, 1);
  });
});

// =============================================================================
// IOT DEVICE UTILITIES TESTS
// =============================================================================

describe('IoT Device Utilities', () => {
  test('should normalize MAC address with colons', () => {
    expect(normalizeMacAddress('AA:BB:CC:DD:EE:FF')).toBe('aa:bb:cc:dd:ee:ff');
  });

  test('should normalize MAC address with dashes', () => {
    expect(normalizeMacAddress('AA-BB-CC-DD-EE-FF')).toBe('aa:bb:cc:dd:ee:ff');
  });

  test('should normalize MAC address without separators', () => {
    expect(normalizeMacAddress('AABBCCDDEEFF')).toBe('aa:bb:cc:dd:ee:ff');
  });

  test('should throw for invalid MAC address', () => {
    expect(() => normalizeMacAddress('invalid')).toThrow('Invalid MAC address format');
    expect(() => normalizeMacAddress('AA:BB:CC')).toThrow('Invalid MAC address format');
  });

  test('should validate valid MAC addresses', () => {
    expect(isValidMacAddress('AA:BB:CC:DD:EE:FF')).toBe(true);
    expect(isValidMacAddress('aa-bb-cc-dd-ee-ff')).toBe(true);
    expect(isValidMacAddress('aabbccddeeff')).toBe(true);
  });

  test('should invalidate invalid MAC addresses', () => {
    expect(isValidMacAddress('invalid')).toBe(false);
    expect(isValidMacAddress('AA:BB:CC')).toBe(false);
    expect(isValidMacAddress('')).toBe(false);
  });

  test('should link device to station', () => {
    const device: IoTDevice = {
      id: 'device-1',
      macAddress: 'aa:bb:cc:dd:ee:ff',
      deviceType: 'sensor',
      status: 'discovered',
      lastSeen: new Date(),
    };

    const linked = linkDeviceToStation(device, 'station-1', 'Workstation A');

    expect(linked.status).toBe('linked');
    expect(linked.linkedStationId).toBe('station-1');
    expect(linked.linkedStationName).toBe('Workstation A');
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Maturity System Integration', () => {
  test('should integrate level indicator with feature gate', () => {
    render(
      <MaturityProvider initialLevel={1}>
        <MaturityLevelIndicator compact />
        <FeatureGate featureId="customer-list">
          <div data-testid="sales">Sales Feature</div>
        </FeatureGate>
        <FeatureGate featureId="andon">
          <div data-testid="andon">Andon Feature</div>
        </FeatureGate>
      </MaturityProvider>
    );

    expect(screen.getByText('L1')).toBeInTheDocument();
    expect(screen.getByTestId('sales')).toBeInTheDocument();
    expect(screen.queryByTestId('andon')).not.toBeInTheDocument();
  });

  test('should unlock features after level-up', async () => {
    const TestComponent = () => {
      const { levelUp } = useMaturity();
      return (
        <div>
          <button onClick={() => levelUp()}>Level Up</button>
          <FeatureGate featureId="customer-list">
            <div data-testid="sales">Sales</div>
          </FeatureGate>
        </div>
      );
    };

    render(
      <MaturityProvider initialLevel={0}>
        <TestComponent />
      </MaturityProvider>
    );

    expect(screen.queryByTestId('sales')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Level Up'));

    await waitFor(() => {
      expect(screen.getByTestId('sales')).toBeInTheDocument();
    });
  });

  test('should complete full SAT workflow', () => {
    let checklist = createSATChecklist('site-1', 'Factory A');

    // Complete all network items
    const networkItems = checklist.items.filter((i) => i.category === 'network');
    for (const item of networkItems) {
      checklist = updateSATChecklistItem(checklist, item.id, {
        completed: true,
        completedBy: 'technician',
      });
    }

    // Verify partial completion
    expect(checklist.overallStatus).toBe('in-progress');
    expect(getSATCompletionPercentage(checklist)).toBeGreaterThan(0);

    // Complete remaining items
    for (const item of checklist.items) {
      if (!item.completed) {
        checklist = updateSATChecklistItem(checklist, item.id, { completed: true });
      }
    }

    expect(checklist.overallStatus).toBe('completed');
    expect(getSATCompletionPercentage(checklist)).toBe(100);
  });
});
