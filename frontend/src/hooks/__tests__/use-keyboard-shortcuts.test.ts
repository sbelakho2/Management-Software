/**
 * Tests for Keyboard Shortcuts System
 */

import {
  useKeyboardShortcutsStore,
  parseShortcutString,
  formatShortcutSequence,
  normalizeKey,
  matchesKey,
  sequencesMatch,
  useKeyboardShortcuts,
  useShortcut,
  useShortcutScope,
  useDisableShortcuts,
  useFormattedShortcuts,
  initializeKeyboardShortcuts,
  defaultShortcuts,
  Shortcut,
  ShortcutKey,
  ShortcutSequence,
} from '../use-keyboard-shortcuts';
import { renderHook, act } from '@testing-library/react';
import { fireEvent } from '@testing-library/react';

// Reset store before each test
beforeEach(() => {
  useKeyboardShortcutsStore.setState({
    shortcuts: new Map(),
    overrides: [],
    chordBuffer: [],
    chordTimeout: 1000,
    isChordActive: false,
    lastChordTime: 0,
    activeScope: 'global',
    scopeStack: ['global'],
    isEnabled: true,
    showHelp: false,
  });
});

// =============================================================================
// normalizeKey Tests
// =============================================================================

describe('normalizeKey', () => {
  it('should lowercase regular keys', () => {
    expect(normalizeKey('A')).toBe('a');
    expect(normalizeKey('Z')).toBe('z');
    expect(normalizeKey('K')).toBe('k');
  });

  it('should normalize space', () => {
    expect(normalizeKey(' ')).toBe('space');
  });

  it('should normalize arrow keys', () => {
    expect(normalizeKey('ArrowUp')).toBe('up');
    expect(normalizeKey('ArrowDown')).toBe('down');
    expect(normalizeKey('ArrowLeft')).toBe('left');
    expect(normalizeKey('ArrowRight')).toBe('right');
  });

  it('should normalize special keys', () => {
    expect(normalizeKey('Escape')).toBe('escape');
    expect(normalizeKey('Enter')).toBe('enter');
    expect(normalizeKey('Tab')).toBe('tab');
    expect(normalizeKey('Backspace')).toBe('backspace');
    expect(normalizeKey('Delete')).toBe('delete');
  });

  it('should return lowercase for unknown keys', () => {
    expect(normalizeKey('F1')).toBe('f1');
    expect(normalizeKey('PageUp')).toBe('pageup');
  });
});

// =============================================================================
// parseShortcutString Tests
// =============================================================================

describe('parseShortcutString', () => {
  it('should parse single key', () => {
    const result = parseShortcutString('K');
    expect(result.keys).toHaveLength(1);
    expect(result.keys[0].key).toBe('k');
    expect(result.isChord).toBe(false);
  });

  it('should parse chord sequences', () => {
    const result = parseShortcutString('G D');
    expect(result.keys).toHaveLength(2);
    expect(result.keys[0].key).toBe('g');
    expect(result.keys[1].key).toBe('d');
    expect(result.isChord).toBe(true);
  });

  it('should parse Cmd modifier', () => {
    const result = parseShortcutString('Cmd+K');
    expect(result.keys).toHaveLength(1);
    expect(result.keys[0].key).toBe('k');
    expect(result.keys[0].modifiers).toContain('meta');
  });

  it('should parse Ctrl modifier', () => {
    const result = parseShortcutString('Ctrl+K');
    expect(result.keys).toHaveLength(1);
    expect(result.keys[0].key).toBe('k');
    expect(result.keys[0].modifiers).toContain('ctrl');
  });

  it('should parse Alt modifier', () => {
    const result = parseShortcutString('Alt+K');
    expect(result.keys).toHaveLength(1);
    expect(result.keys[0].modifiers).toContain('alt');
  });

  it('should parse Shift modifier', () => {
    const result = parseShortcutString('Shift+A');
    expect(result.keys).toHaveLength(1);
    expect(result.keys[0].modifiers).toContain('shift');
  });

  it('should parse multiple modifiers', () => {
    const result = parseShortcutString('Cmd+Shift+S');
    expect(result.keys).toHaveLength(1);
    expect(result.keys[0].modifiers).toContain('meta');
    expect(result.keys[0].modifiers).toContain('shift');
    expect(result.keys[0].key).toBe('s');
  });

  it('should handle empty string', () => {
    const result = parseShortcutString('');
    expect(result.keys).toHaveLength(0);
    expect(result.isChord).toBe(false);
  });

  it('should parse special key symbols', () => {
    const result = parseShortcutString('/');
    expect(result.keys[0].key).toBe('/');
  });

  it('should parse question mark', () => {
    const result = parseShortcutString('?');
    expect(result.keys[0].key).toBe('?');
  });
});

// =============================================================================
// formatShortcutSequence Tests
// =============================================================================

describe('formatShortcutSequence', () => {
  // Mock navigator for platform detection
  const originalNavigator = global.navigator;
  
  beforeEach(() => {
    Object.defineProperty(global, 'navigator', {
      value: { platform: 'MacIntel' },
      writable: true,
    });
  });
  
  afterAll(() => {
    Object.defineProperty(global, 'navigator', {
      value: originalNavigator,
      writable: true,
    });
  });

  it('should format single key', () => {
    const sequence: ShortcutSequence = {
      keys: [{ key: 'k' }],
      isChord: false,
    };
    expect(formatShortcutSequence(sequence)).toBe('K');
  });

  it('should format chord sequence with spaces', () => {
    const sequence: ShortcutSequence = {
      keys: [{ key: 'g' }, { key: 'd' }],
      isChord: true,
    };
    expect(formatShortcutSequence(sequence)).toBe('G D');
  });

  it('should format modifier keys on Mac', () => {
    const sequence: ShortcutSequence = {
      keys: [{ key: 'k', modifiers: ['meta'] }],
      isChord: false,
    };
    expect(formatShortcutSequence(sequence)).toBe('⌘+K');
  });

  it('should format multiple modifiers on Mac', () => {
    const sequence: ShortcutSequence = {
      keys: [{ key: 's', modifiers: ['meta', 'shift'] }],
      isChord: false,
    };
    const formatted = formatShortcutSequence(sequence);
    expect(formatted).toContain('⌘');
    expect(formatted).toContain('⇧');
    expect(formatted).toContain('S');
  });

  it('should format space key', () => {
    const sequence: ShortcutSequence = {
      keys: [{ key: 'space' }],
      isChord: false,
    };
    expect(formatShortcutSequence(sequence)).toBe('␣');
  });
});

// =============================================================================
// matchesKey Tests
// =============================================================================

describe('matchesKey', () => {
  it('should match simple key', () => {
    const event = new KeyboardEvent('keydown', { key: 'k' });
    const shortcutKey: ShortcutKey = { key: 'k' };
    expect(matchesKey(event, shortcutKey)).toBe(true);
  });

  it('should not match different key', () => {
    const event = new KeyboardEvent('keydown', { key: 'j' });
    const shortcutKey: ShortcutKey = { key: 'k' };
    expect(matchesKey(event, shortcutKey)).toBe(false);
  });

  it('should match with meta modifier', () => {
    const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
    const shortcutKey: ShortcutKey = { key: 'k', modifiers: ['meta'] };
    expect(matchesKey(event, shortcutKey)).toBe(true);
  });

  it('should not match when modifier is missing', () => {
    const event = new KeyboardEvent('keydown', { key: 'k' });
    const shortcutKey: ShortcutKey = { key: 'k', modifiers: ['meta'] };
    expect(matchesKey(event, shortcutKey)).toBe(false);
  });

  it('should not match when extra modifier is present for non-chord', () => {
    const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
    const shortcutKey: ShortcutKey = { key: 'k' };
    expect(matchesKey(event, shortcutKey)).toBe(false);
  });

  it('should match with multiple modifiers', () => {
    const event = new KeyboardEvent('keydown', { key: 's', metaKey: true, shiftKey: true });
    const shortcutKey: ShortcutKey = { key: 's', modifiers: ['meta', 'shift'] };
    expect(matchesKey(event, shortcutKey)).toBe(true);
  });
});

// =============================================================================
// sequencesMatch Tests
// =============================================================================

describe('sequencesMatch', () => {
  it('should match identical sequences', () => {
    const a: ShortcutKey[] = [{ key: 'g' }, { key: 'd' }];
    const b: ShortcutKey[] = [{ key: 'g' }, { key: 'd' }];
    expect(sequencesMatch(a, b)).toBe(true);
  });

  it('should not match different length sequences', () => {
    const a: ShortcutKey[] = [{ key: 'g' }];
    const b: ShortcutKey[] = [{ key: 'g' }, { key: 'd' }];
    expect(sequencesMatch(a, b)).toBe(false);
  });

  it('should not match different keys', () => {
    const a: ShortcutKey[] = [{ key: 'g' }, { key: 'd' }];
    const b: ShortcutKey[] = [{ key: 'g' }, { key: 'r' }];
    expect(sequencesMatch(a, b)).toBe(false);
  });

  it('should match sequences with same modifiers', () => {
    const a: ShortcutKey[] = [{ key: 's', modifiers: ['meta', 'shift'] }];
    const b: ShortcutKey[] = [{ key: 's', modifiers: ['shift', 'meta'] }];
    expect(sequencesMatch(a, b)).toBe(true);
  });

  it('should not match sequences with different modifiers', () => {
    const a: ShortcutKey[] = [{ key: 's', modifiers: ['meta'] }];
    const b: ShortcutKey[] = [{ key: 's', modifiers: ['ctrl'] }];
    expect(sequencesMatch(a, b)).toBe(false);
  });
});

// =============================================================================
// useKeyboardShortcutsStore Tests
// =============================================================================

describe('useKeyboardShortcutsStore', () => {
  describe('registerShortcut', () => {
    it('should register a shortcut', () => {
      const shortcut: Shortcut = {
        id: 'test-shortcut',
        label: 'Test Shortcut',
        category: 'actions',
        sequence: parseShortcutString('T S'),
        scope: 'global',
        handler: jest.fn(),
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      
      expect(useKeyboardShortcutsStore.getState().shortcuts.get('test-shortcut')).toBeDefined();
    });

    it('should update existing shortcut on re-register', () => {
      const shortcut1: Shortcut = {
        id: 'test-shortcut',
        label: 'Original',
        category: 'actions',
        sequence: parseShortcutString('T S'),
        scope: 'global',
        handler: jest.fn(),
      };
      
      const shortcut2: Shortcut = {
        id: 'test-shortcut',
        label: 'Updated',
        category: 'actions',
        sequence: parseShortcutString('T U'),
        scope: 'global',
        handler: jest.fn(),
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut1);
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut2);
      
      const stored = useKeyboardShortcutsStore.getState().shortcuts.get('test-shortcut');
      expect(stored?.label).toBe('Updated');
    });
  });

  describe('registerShortcuts', () => {
    it('should register multiple shortcuts', () => {
      const shortcuts: Shortcut[] = [
        {
          id: 'shortcut-1',
          label: 'Shortcut 1',
          category: 'actions',
          sequence: parseShortcutString('A'),
          scope: 'global',
          handler: jest.fn(),
        },
        {
          id: 'shortcut-2',
          label: 'Shortcut 2',
          category: 'navigation',
          sequence: parseShortcutString('B'),
          scope: 'global',
          handler: jest.fn(),
        },
      ];
      
      useKeyboardShortcutsStore.getState().registerShortcuts(shortcuts);
      
      expect(useKeyboardShortcutsStore.getState().shortcuts.size).toBe(2);
    });
  });

  describe('unregisterShortcut', () => {
    it('should remove a shortcut', () => {
      const shortcut: Shortcut = {
        id: 'to-remove',
        label: 'To Remove',
        category: 'actions',
        sequence: parseShortcutString('R'),
        scope: 'global',
        handler: jest.fn(),
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      useKeyboardShortcutsStore.getState().unregisterShortcut('to-remove');
      
      expect(useKeyboardShortcutsStore.getState().shortcuts.get('to-remove')).toBeUndefined();
    });
  });

  describe('scope management', () => {
    it('should push scope', () => {
      useKeyboardShortcutsStore.getState().pushScope('form');
      expect(useKeyboardShortcutsStore.getState().activeScope).toBe('form');
      expect(useKeyboardShortcutsStore.getState().scopeStack).toContain('form');
    });

    it('should pop scope', () => {
      useKeyboardShortcutsStore.getState().pushScope('form');
      useKeyboardShortcutsStore.getState().pushScope('modal');
      useKeyboardShortcutsStore.getState().popScope();
      
      expect(useKeyboardShortcutsStore.getState().activeScope).toBe('form');
    });

    it('should default to global when stack is empty', () => {
      useKeyboardShortcutsStore.getState().popScope();
      expect(useKeyboardShortcutsStore.getState().activeScope).toBe('global');
    });
  });

  describe('overrides', () => {
    it('should set override', () => {
      useKeyboardShortcutsStore.getState().setOverride({
        id: 'nav-dashboard',
        sequence: parseShortcutString('H D'),
      });
      
      expect(useKeyboardShortcutsStore.getState().overrides).toHaveLength(1);
    });

    it('should replace existing override', () => {
      useKeyboardShortcutsStore.getState().setOverride({
        id: 'nav-dashboard',
        sequence: parseShortcutString('H D'),
      });
      
      useKeyboardShortcutsStore.getState().setOverride({
        id: 'nav-dashboard',
        sequence: parseShortcutString('H H'),
      });
      
      expect(useKeyboardShortcutsStore.getState().overrides).toHaveLength(1);
      expect(useKeyboardShortcutsStore.getState().overrides[0].sequence.keys[1].key).toBe('h');
    });

    it('should remove override', () => {
      useKeyboardShortcutsStore.getState().setOverride({
        id: 'nav-dashboard',
        sequence: parseShortcutString('H D'),
      });
      
      useKeyboardShortcutsStore.getState().removeOverride('nav-dashboard');
      
      expect(useKeyboardShortcutsStore.getState().overrides).toHaveLength(0);
    });

    it('should reset all overrides', () => {
      useKeyboardShortcutsStore.getState().setOverride({
        id: 'nav-dashboard',
        sequence: parseShortcutString('H D'),
      });
      useKeyboardShortcutsStore.getState().setOverride({
        id: 'nav-rfq',
        sequence: parseShortcutString('H R'),
      });
      
      useKeyboardShortcutsStore.getState().resetOverrides();
      
      expect(useKeyboardShortcutsStore.getState().overrides).toHaveLength(0);
    });
  });

  describe('enable/disable', () => {
    it('should set enabled state', () => {
      useKeyboardShortcutsStore.getState().setEnabled(false);
      expect(useKeyboardShortcutsStore.getState().isEnabled).toBe(false);
      
      useKeyboardShortcutsStore.getState().setEnabled(true);
      expect(useKeyboardShortcutsStore.getState().isEnabled).toBe(true);
    });
  });

  describe('toggleHelp', () => {
    it('should toggle help visibility', () => {
      expect(useKeyboardShortcutsStore.getState().showHelp).toBe(false);
      
      useKeyboardShortcutsStore.getState().toggleHelp();
      expect(useKeyboardShortcutsStore.getState().showHelp).toBe(true);
      
      useKeyboardShortcutsStore.getState().toggleHelp();
      expect(useKeyboardShortcutsStore.getState().showHelp).toBe(false);
    });
  });

  describe('getShortcutsByCategory', () => {
    it('should return shortcuts by category', () => {
      const shortcuts: Shortcut[] = [
        {
          id: 'nav-1',
          label: 'Nav 1',
          category: 'navigation',
          sequence: parseShortcutString('G A'),
          scope: 'global',
          handler: jest.fn(),
        },
        {
          id: 'action-1',
          label: 'Action 1',
          category: 'actions',
          sequence: parseShortcutString('A'),
          scope: 'global',
          handler: jest.fn(),
        },
      ];
      
      useKeyboardShortcutsStore.getState().registerShortcuts(shortcuts);
      
      const navShortcuts = useKeyboardShortcutsStore.getState().getShortcutsByCategory('navigation');
      expect(navShortcuts).toHaveLength(1);
      expect(navShortcuts[0].id).toBe('nav-1');
    });
  });

  describe('getShortcutsByScope', () => {
    it('should return shortcuts by scope', () => {
      const shortcuts: Shortcut[] = [
        {
          id: 'global-1',
          label: 'Global 1',
          category: 'navigation',
          sequence: parseShortcutString('G A'),
          scope: 'global',
          handler: jest.fn(),
        },
        {
          id: 'form-1',
          label: 'Form 1',
          category: 'editing',
          sequence: parseShortcutString('Cmd+S'),
          scope: 'form',
          handler: jest.fn(),
        },
      ];
      
      useKeyboardShortcutsStore.getState().registerShortcuts(shortcuts);
      
      const formShortcuts = useKeyboardShortcutsStore.getState().getShortcutsByScope('form');
      expect(formShortcuts).toHaveLength(1);
      expect(formShortcuts[0].id).toBe('form-1');
    });
  });

  describe('getEffectiveSequence', () => {
    it('should return original sequence when no override', () => {
      const shortcut: Shortcut = {
        id: 'test-seq',
        label: 'Test',
        category: 'actions',
        sequence: parseShortcutString('G T'),
        scope: 'global',
        handler: jest.fn(),
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      
      const effective = useKeyboardShortcutsStore.getState().getEffectiveSequence('test-seq');
      expect(effective?.keys[0].key).toBe('g');
      expect(effective?.keys[1].key).toBe('t');
    });

    it('should return override sequence when set', () => {
      const shortcut: Shortcut = {
        id: 'test-seq',
        label: 'Test',
        category: 'actions',
        sequence: parseShortcutString('G T'),
        scope: 'global',
        handler: jest.fn(),
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      useKeyboardShortcutsStore.getState().setOverride({
        id: 'test-seq',
        sequence: parseShortcutString('H H'),
      });
      
      const effective = useKeyboardShortcutsStore.getState().getEffectiveSequence('test-seq');
      expect(effective?.keys[0].key).toBe('h');
      expect(effective?.keys[1].key).toBe('h');
    });
  });

  describe('findShortcutBySequence', () => {
    it('should find shortcut by sequence', () => {
      const shortcut: Shortcut = {
        id: 'find-me',
        label: 'Find Me',
        category: 'actions',
        sequence: parseShortcutString('F M'),
        scope: 'global',
        handler: jest.fn(),
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      
      const found = useKeyboardShortcutsStore.getState().findShortcutBySequence([
        { key: 'f' },
        { key: 'm' },
      ]);
      
      expect(found?.id).toBe('find-me');
    });

    it('should not find disabled shortcut', () => {
      const shortcut: Shortcut = {
        id: 'disabled',
        label: 'Disabled',
        category: 'actions',
        sequence: parseShortcutString('D D'),
        scope: 'global',
        handler: jest.fn(),
        enabled: false,
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      
      const found = useKeyboardShortcutsStore.getState().findShortcutBySequence([
        { key: 'd' },
        { key: 'd' },
      ]);
      
      expect(found).toBeUndefined();
    });

    it('should respect when condition', () => {
      const shortcut: Shortcut = {
        id: 'conditional',
        label: 'Conditional',
        category: 'actions',
        sequence: parseShortcutString('C C'),
        scope: 'global',
        handler: jest.fn(),
        when: () => false,
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      
      const found = useKeyboardShortcutsStore.getState().findShortcutBySequence([
        { key: 'c' },
        { key: 'c' },
      ]);
      
      expect(found).toBeUndefined();
    });
  });

  describe('handleKeyDown', () => {
    it('should execute matching shortcut', () => {
      const handler = jest.fn();
      const shortcut: Shortcut = {
        id: 'simple',
        label: 'Simple',
        category: 'actions',
        sequence: parseShortcutString('Cmd+K'),
        scope: 'global',
        handler,
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      
      const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
      const handled = useKeyboardShortcutsStore.getState().handleKeyDown(event);
      
      expect(handled).toBe(true);
      expect(handler).toHaveBeenCalled();
    });

    it('should not execute when disabled', () => {
      const handler = jest.fn();
      const shortcut: Shortcut = {
        id: 'disabled-test',
        label: 'Disabled Test',
        category: 'actions',
        sequence: parseShortcutString('Cmd+D'),
        scope: 'global',
        handler,
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      useKeyboardShortcutsStore.getState().setEnabled(false);
      
      const event = new KeyboardEvent('keydown', { key: 'd', metaKey: true });
      const handled = useKeyboardShortcutsStore.getState().handleKeyDown(event);
      
      expect(handled).toBe(false);
      expect(handler).not.toHaveBeenCalled();
    });

    it('should handle chord sequences', () => {
      const handler = jest.fn();
      const shortcut: Shortcut = {
        id: 'chord-test',
        label: 'Chord Test',
        category: 'navigation',
        sequence: parseShortcutString('G T'),
        scope: 'global',
        handler,
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      
      // First key of chord
      const event1 = new KeyboardEvent('keydown', { key: 'g' });
      useKeyboardShortcutsStore.getState().handleKeyDown(event1);
      
      expect(useKeyboardShortcutsStore.getState().isChordActive).toBe(true);
      expect(handler).not.toHaveBeenCalled();
      
      // Second key of chord
      const event2 = new KeyboardEvent('keydown', { key: 't' });
      useKeyboardShortcutsStore.getState().handleKeyDown(event2);
      
      expect(handler).toHaveBeenCalled();
      expect(useKeyboardShortcutsStore.getState().isChordActive).toBe(false);
    });

    it('should reset chord on timeout', () => {
      const shortcut: Shortcut = {
        id: 'timeout-test',
        label: 'Timeout Test',
        category: 'navigation',
        sequence: parseShortcutString('T T'),
        scope: 'global',
        handler: jest.fn(),
      };
      
      useKeyboardShortcutsStore.getState().registerShortcut(shortcut);
      
      // First key
      const event1 = new KeyboardEvent('keydown', { key: 't' });
      useKeyboardShortcutsStore.getState().handleKeyDown(event1);
      
      // Simulate timeout
      useKeyboardShortcutsStore.setState({
        lastChordTime: Date.now() - 2000, // 2 seconds ago
      });
      
      // Next key should reset
      const event2 = new KeyboardEvent('keydown', { key: 'x' });
      useKeyboardShortcutsStore.getState().handleKeyDown(event2);
      
      expect(useKeyboardShortcutsStore.getState().chordBuffer).toHaveLength(0);
    });
  });

  describe('formatSequence', () => {
    it('should format sequence using store method', () => {
      const sequence = parseShortcutString('G D');
      const formatted = useKeyboardShortcutsStore.getState().formatSequence(sequence);
      expect(formatted).toBe('G D');
    });
  });
});

// =============================================================================
// Hooks Tests
// =============================================================================

describe('useKeyboardShortcuts hook', () => {
  it('should add and remove event listener', () => {
    const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
    const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');
    
    const { unmount } = renderHook(() => useKeyboardShortcuts());
    
    expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function), { capture: true });
    
    unmount();
    
    expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function), { capture: true });
    
    addEventListenerSpy.mockRestore();
    removeEventListenerSpy.mockRestore();
  });
});

describe('useShortcut hook', () => {
  it('should register and unregister shortcut', () => {
    const handler = jest.fn();
    
    const { unmount } = renderHook(() => 
      useShortcut('test-hook', 'Cmd+T', handler, {
        label: 'Test Hook',
        category: 'actions',
      })
    );
    
    expect(useKeyboardShortcutsStore.getState().shortcuts.get('test-hook')).toBeDefined();
    
    unmount();
    
    expect(useKeyboardShortcutsStore.getState().shortcuts.get('test-hook')).toBeUndefined();
  });
});

describe('useShortcutScope hook', () => {
  it('should push and pop scope', () => {
    const { unmount } = renderHook(() => useShortcutScope('form'));
    
    expect(useKeyboardShortcutsStore.getState().activeScope).toBe('form');
    
    unmount();
    
    expect(useKeyboardShortcutsStore.getState().activeScope).toBe('global');
  });
});

describe('useDisableShortcuts hook', () => {
  it('should disable and re-enable shortcuts', () => {
    const { unmount } = renderHook(() => useDisableShortcuts());
    
    expect(useKeyboardShortcutsStore.getState().isEnabled).toBe(false);
    
    unmount();
    
    expect(useKeyboardShortcutsStore.getState().isEnabled).toBe(true);
  });
});

describe('useFormattedShortcuts hook', () => {
  it('should return formatted shortcuts', () => {
    const shortcuts: Shortcut[] = [
      {
        id: 'nav-test',
        label: 'Navigation Test',
        description: 'Test description',
        category: 'navigation',
        sequence: parseShortcutString('G N'),
        scope: 'global',
        handler: jest.fn(),
      },
    ];
    
    useKeyboardShortcutsStore.getState().registerShortcuts(shortcuts);
    
    const { result } = renderHook(() => useFormattedShortcuts());
    
    expect(result.current.all).toHaveLength(1);
    expect(result.current.all[0].label).toBe('Navigation Test');
    expect(result.current.all[0].shortcut).toBe('G N');
    expect(result.current.byCategory.navigation).toHaveLength(1);
  });
});

// =============================================================================
// initializeKeyboardShortcuts Tests
// =============================================================================

describe('initializeKeyboardShortcuts', () => {
  it('should initialize with handlers', () => {
    const handlers: Record<string, () => void> = {
      'nav-dashboard': jest.fn(),
      'nav-rfq': jest.fn(),
    };
    
    initializeKeyboardShortcuts(handlers);
    
    expect(useKeyboardShortcutsStore.getState().shortcuts.size).toBeGreaterThan(0);
    expect(useKeyboardShortcutsStore.getState().shortcuts.get('nav-dashboard')).toBeDefined();
  });

  it('should provide fallback handler for missing handlers', () => {
    const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
    
    initializeKeyboardShortcuts({});
    
    const shortcut = useKeyboardShortcutsStore.getState().shortcuts.get('nav-dashboard');
    shortcut?.handler();
    
    expect(consoleSpy).toHaveBeenCalledWith('No handler for shortcut: nav-dashboard');
    
    consoleSpy.mockRestore();
  });
});

// =============================================================================
// defaultShortcuts Tests
// =============================================================================

describe('defaultShortcuts', () => {
  it('should include navigation shortcuts', () => {
    const navShortcuts = defaultShortcuts.filter(s => s.category === 'navigation');
    expect(navShortcuts.length).toBeGreaterThan(0);
  });

  it('should include action shortcuts', () => {
    const actionShortcuts = defaultShortcuts.filter(s => s.category === 'actions');
    expect(actionShortcuts.length).toBeGreaterThan(0);
  });

  it('should include approval shortcuts', () => {
    const approvalShortcuts = defaultShortcuts.filter(s => s.category === 'approvals');
    expect(approvalShortcuts.length).toBeGreaterThan(0);
  });

  it('should include export shortcuts', () => {
    const exportShortcuts = defaultShortcuts.filter(s => s.category === 'exports');
    expect(exportShortcuts.length).toBeGreaterThan(0);
  });

  it('should include task shortcuts', () => {
    const taskShortcuts = defaultShortcuts.filter(s => s.category === 'tasks');
    expect(taskShortcuts.length).toBeGreaterThan(0);
  });

  it('should include UI shortcuts', () => {
    const uiShortcuts = defaultShortcuts.filter(s => s.category === 'ui');
    expect(uiShortcuts.length).toBeGreaterThan(0);
  });

  it('should include help shortcuts', () => {
    const helpShortcuts = defaultShortcuts.filter(s => s.category === 'help');
    expect(helpShortcuts.length).toBeGreaterThan(0);
  });

  it('should have unique IDs', () => {
    const ids = defaultShortcuts.map(s => s.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });

  it('should have valid sequences', () => {
    for (const shortcut of defaultShortcuts) {
      expect(shortcut.sequence.keys.length).toBeGreaterThan(0);
    }
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('Keyboard Shortcuts Integration', () => {
  it('should handle complete workflow', () => {
    const dashboardHandler = jest.fn();
    
    // Initialize
    initializeKeyboardShortcuts({
      'nav-dashboard': dashboardHandler,
    });
    
    // Trigger chord G D
    const event1 = new KeyboardEvent('keydown', { key: 'g' });
    useKeyboardShortcutsStore.getState().handleKeyDown(event1);
    
    const event2 = new KeyboardEvent('keydown', { key: 'd' });
    useKeyboardShortcutsStore.getState().handleKeyDown(event2);
    
    expect(dashboardHandler).toHaveBeenCalled();
  });

  it('should respect scope precedence', () => {
    const globalHandler = jest.fn();
    const formHandler = jest.fn();
    
    useKeyboardShortcutsStore.getState().registerShortcuts([
      {
        id: 'global-escape',
        label: 'Global Escape',
        category: 'ui',
        sequence: parseShortcutString('escape'),
        scope: 'global',
        handler: globalHandler,
      },
      {
        id: 'form-escape',
        label: 'Form Escape',
        category: 'editing',
        sequence: parseShortcutString('escape'),
        scope: 'form',
        handler: formHandler,
        priority: 10,
      },
    ]);
    
    // Push form scope
    useKeyboardShortcutsStore.getState().pushScope('form');
    
    // Trigger escape
    const event = new KeyboardEvent('keydown', { key: 'Escape' });
    useKeyboardShortcutsStore.getState().handleKeyDown(event);
    
    // Form handler should be called (higher priority + more specific scope)
    expect(formHandler).toHaveBeenCalled();
    expect(globalHandler).not.toHaveBeenCalled();
  });

  it('should handle override customization', () => {
    const handler = jest.fn();
    
    useKeyboardShortcutsStore.getState().registerShortcut({
      id: 'custom-override',
      label: 'Custom Override',
      category: 'actions',
      sequence: parseShortcutString('A A'),
      scope: 'global',
      handler,
    });
    
    // Set override to B B
    useKeyboardShortcutsStore.getState().setOverride({
      id: 'custom-override',
      sequence: parseShortcutString('B B'),
    });
    
    // Original sequence should not work
    const event1 = new KeyboardEvent('keydown', { key: 'a' });
    useKeyboardShortcutsStore.getState().handleKeyDown(event1);
    
    const event2 = new KeyboardEvent('keydown', { key: 'a' });
    useKeyboardShortcutsStore.getState().handleKeyDown(event2);
    
    expect(handler).not.toHaveBeenCalled();
    
    // Reset chord buffer
    useKeyboardShortcutsStore.getState().resetChordBuffer();
    
    // New sequence should work
    const event3 = new KeyboardEvent('keydown', { key: 'b' });
    useKeyboardShortcutsStore.getState().handleKeyDown(event3);
    
    const event4 = new KeyboardEvent('keydown', { key: 'b' });
    useKeyboardShortcutsStore.getState().handleKeyDown(event4);
    
    expect(handler).toHaveBeenCalled();
  });
});
