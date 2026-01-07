/**
 * Keyboard Shortcuts System
 * 
 * A comprehensive keyboard shortcuts hook for power-user navigation,
 * approvals, task completion, and exports.
 * 
 * Features:
 * - Global and scoped shortcuts
 * - Chord sequences (e.g., "G D" for Go to Dashboard)
 * - Modifier key support (Cmd/Ctrl, Shift, Alt)
 * - Conflict detection
 * - Context-aware enabling/disabling
 * - Customizable shortcuts with persistence
 */

import { useEffect, useCallback, useRef, useMemo } from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// =============================================================================
// Types
// =============================================================================

export type ShortcutModifier = 'ctrl' | 'meta' | 'alt' | 'shift';
export type ShortcutScope = 'global' | 'modal' | 'form' | 'list' | 'table' | 'editor';
export type ShortcutCategory = 
  | 'navigation' 
  | 'actions' 
  | 'editing' 
  | 'approvals' 
  | 'exports' 
  | 'tasks' 
  | 'ui' 
  | 'help';

export interface ShortcutKey {
  key: string;
  modifiers?: ShortcutModifier[];
}

export interface ShortcutSequence {
  keys: ShortcutKey[];
  isChord: boolean; // true = press in sequence, false = hold together
}

export interface Shortcut {
  id: string;
  label: string;
  description?: string;
  category: ShortcutCategory;
  sequence: ShortcutSequence;
  scope: ShortcutScope;
  handler: () => void | Promise<void>;
  enabled?: boolean;
  when?: () => boolean; // Conditional enabling
  priority?: number; // Higher priority wins conflicts
}

export interface ShortcutOverride {
  id: string;
  sequence: ShortcutSequence;
}

export interface ShortcutsState {
  shortcuts: Map<string, Shortcut>;
  overrides: ShortcutOverride[];
  chordBuffer: ShortcutKey[];
  chordTimeout: number;
  isChordActive: boolean;
  lastChordTime: number;
  activeScope: ShortcutScope;
  scopeStack: ShortcutScope[];
  isEnabled: boolean;
  showHelp: boolean;
  
  // Actions
  registerShortcut: (shortcut: Shortcut) => void;
  registerShortcuts: (shortcuts: Shortcut[]) => void;
  unregisterShortcut: (id: string) => void;
  setOverride: (override: ShortcutOverride) => void;
  removeOverride: (id: string) => void;
  resetOverrides: () => void;
  pushScope: (scope: ShortcutScope) => void;
  popScope: () => void;
  setEnabled: (enabled: boolean) => void;
  toggleHelp: () => void;
  getShortcutsByCategory: (category: ShortcutCategory) => Shortcut[];
  getShortcutsByScope: (scope: ShortcutScope) => Shortcut[];
  getShortcutById: (id: string) => Shortcut | undefined;
  getEffectiveSequence: (id: string) => ShortcutSequence | undefined;
  findShortcutBySequence: (sequence: ShortcutKey[]) => Shortcut | undefined;
  handleKeyDown: (event: KeyboardEvent) => boolean;
  resetChordBuffer: () => void;
  formatSequence: (sequence: ShortcutSequence) => string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Normalize a key to lowercase and handle special cases
 */
export function normalizeKey(key: string): string {
  const keyMap: Record<string, string> = {
    ' ': 'space',
    'ArrowUp': 'up',
    'ArrowDown': 'down',
    'ArrowLeft': 'left',
    'ArrowRight': 'right',
    'Escape': 'escape',
    'Enter': 'enter',
    'Tab': 'tab',
    'Backspace': 'backspace',
    'Delete': 'delete',
  };
  
  return keyMap[key] || key.toLowerCase();
}

/**
 * Parse a shortcut string into a ShortcutSequence
 * Examples:
 * - "G D" -> chord sequence [G, D]
 * - "Cmd+K" -> single key with modifier
 * - "Ctrl+Shift+S" -> single key with multiple modifiers
 */
export function parseShortcutString(shortcutStr: string): ShortcutSequence {
  if (!shortcutStr) {
    return { keys: [], isChord: false };
  }
  
  // Check if it's a chord (space-separated without modifiers)
  const parts = shortcutStr.split(' ');
  
  if (parts.length > 1 && !parts.some(p => p.includes('+'))) {
    // It's a chord sequence
    return {
      keys: parts.map(key => ({ key: normalizeKey(key) })),
      isChord: true,
    };
  }
  
  // Parse modifier+key combinations
  const keys: ShortcutKey[] = [];
  
  for (const part of parts) {
    const segments = part.split('+');
    const modifiers: ShortcutModifier[] = [];
    let key = '';
    
    for (const segment of segments) {
      const lower = segment.toLowerCase();
      if (lower === 'cmd' || lower === 'meta' || lower === '⌘') {
        modifiers.push('meta');
      } else if (lower === 'ctrl' || lower === 'control' || lower === '⌃') {
        modifiers.push('ctrl');
      } else if (lower === 'alt' || lower === 'option' || lower === '⌥') {
        modifiers.push('alt');
      } else if (lower === 'shift' || lower === '⇧') {
        modifiers.push('shift');
      } else {
        key = normalizeKey(segment);
      }
    }
    
    keys.push({ key, modifiers: modifiers.length > 0 ? modifiers : undefined });
  }
  
  return { keys, isChord: false };
}

/**
 * Format a ShortcutSequence to a display string
 */
export function formatShortcutSequence(sequence: ShortcutSequence): string {
  const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform);
  
  return sequence.keys.map(shortcutKey => {
    const parts: string[] = [];
    
    if (shortcutKey.modifiers) {
      for (const mod of shortcutKey.modifiers) {
        switch (mod) {
          case 'meta':
            parts.push(isMac ? '⌘' : 'Ctrl');
            break;
          case 'ctrl':
            parts.push(isMac ? '⌃' : 'Ctrl');
            break;
          case 'alt':
            parts.push(isMac ? '⌥' : 'Alt');
            break;
          case 'shift':
            parts.push(isMac ? '⇧' : 'Shift');
            break;
        }
      }
    }
    
    // Format key
    const key = shortcutKey.key.toUpperCase();
    parts.push(key === 'SPACE' ? '␣' : key);
    
    return parts.join(sequence.isChord ? '' : '+');
  }).join(sequence.isChord ? ' ' : ' ');
}

/**
 * Check if a keyboard event matches a ShortcutKey
 */
export function matchesKey(event: KeyboardEvent, shortcutKey: ShortcutKey): boolean {
  const eventKey = normalizeKey(event.key);
  
  if (eventKey !== shortcutKey.key) {
    return false;
  }
  
  const expectedModifiers = shortcutKey.modifiers || [];
  
  // Check each modifier
  const hasCtrl = event.ctrlKey && expectedModifiers.includes('ctrl');
  const hasMeta = event.metaKey && expectedModifiers.includes('meta');
  const hasAlt = event.altKey && expectedModifiers.includes('alt');
  const hasShift = event.shiftKey && expectedModifiers.includes('shift');
  
  // Check for unexpected modifiers (unless it's a chord)
  if (!expectedModifiers.length) {
    // For chords, no modifiers should be pressed
    if (event.ctrlKey || event.metaKey || event.altKey) {
      return false;
    }
    // Shift is okay for uppercase letters
  } else {
    // For modifier-based shortcuts, verify exact match
    const ctrlExpected = expectedModifiers.includes('ctrl');
    const metaExpected = expectedModifiers.includes('meta');
    const altExpected = expectedModifiers.includes('alt');
    const shiftExpected = expectedModifiers.includes('shift');
    
    if (event.ctrlKey !== ctrlExpected && !metaExpected) return false;
    if (event.metaKey !== metaExpected && !ctrlExpected) return false;
    if (event.altKey !== altExpected) return false;
    if (event.shiftKey !== shiftExpected) return false;
  }
  
  return true;
}

/**
 * Check if two ShortcutSequences match
 */
export function sequencesMatch(a: ShortcutKey[], b: ShortcutKey[]): boolean {
  if (a.length !== b.length) return false;
  
  for (let i = 0; i < a.length; i++) {
    if (a[i].key !== b[i].key) return false;
    
    const aModifiers = a[i].modifiers || [];
    const bModifiers = b[i].modifiers || [];
    
    if (aModifiers.length !== bModifiers.length) return false;
    if (!aModifiers.every(m => bModifiers.includes(m))) return false;
  }
  
  return true;
}

// =============================================================================
// Default Shortcuts
// =============================================================================

const defaultShortcuts: Omit<Shortcut, 'handler'>[] = [
  // Navigation
  {
    id: 'nav-dashboard',
    label: 'Go to Dashboard',
    description: 'Navigate to the main dashboard',
    category: 'navigation',
    sequence: parseShortcutString('G D'),
    scope: 'global',
  },
  {
    id: 'nav-rfq',
    label: 'Go to RFQs',
    description: 'Navigate to RFQ pipeline',
    category: 'navigation',
    sequence: parseShortcutString('G R'),
    scope: 'global',
  },
  {
    id: 'nav-work-orders',
    label: 'Go to Work Orders',
    description: 'Navigate to work orders',
    category: 'navigation',
    sequence: parseShortcutString('G W'),
    scope: 'global',
  },
  {
    id: 'nav-quality',
    label: 'Go to Quality',
    description: 'Navigate to quality management',
    category: 'navigation',
    sequence: parseShortcutString('G Q'),
    scope: 'global',
  },
  {
    id: 'nav-andon',
    label: 'Go to Andon',
    description: 'Navigate to andon board',
    category: 'navigation',
    sequence: parseShortcutString('G A'),
    scope: 'global',
  },
  {
    id: 'nav-learning',
    label: 'Go to Learning',
    description: 'Navigate to learning center',
    category: 'navigation',
    sequence: parseShortcutString('G L'),
    scope: 'global',
  },
  {
    id: 'nav-settings',
    label: 'Go to Settings',
    description: 'Navigate to settings',
    category: 'navigation',
    sequence: parseShortcutString('G S'),
    scope: 'global',
  },
  
  // Actions
  {
    id: 'action-new-rfq',
    label: 'New RFQ',
    description: 'Create a new RFQ',
    category: 'actions',
    sequence: parseShortcutString('N R'),
    scope: 'global',
  },
  {
    id: 'action-new-work-order',
    label: 'New Work Order',
    description: 'Create a new work order',
    category: 'actions',
    sequence: parseShortcutString('N W'),
    scope: 'global',
  },
  {
    id: 'action-new-task',
    label: 'New Task',
    description: 'Create a new task',
    category: 'actions',
    sequence: parseShortcutString('N T'),
    scope: 'global',
  },
  {
    id: 'action-search',
    label: 'Search',
    description: 'Open global search',
    category: 'actions',
    sequence: parseShortcutString('/'),
    scope: 'global',
  },
  {
    id: 'action-command-palette',
    label: 'Command Palette',
    description: 'Open command palette',
    category: 'actions',
    sequence: parseShortcutString('Cmd+K'),
    scope: 'global',
  },
  
  // Tasks
  {
    id: 'task-complete',
    label: 'Complete Task',
    description: 'Mark current task as complete',
    category: 'tasks',
    sequence: parseShortcutString('X'),
    scope: 'list',
  },
  {
    id: 'task-assign',
    label: 'Assign Task',
    description: 'Assign task to someone',
    category: 'tasks',
    sequence: parseShortcutString('A'),
    scope: 'list',
  },
  {
    id: 'task-due-date',
    label: 'Set Due Date',
    description: 'Set task due date',
    category: 'tasks',
    sequence: parseShortcutString('D'),
    scope: 'list',
  },
  {
    id: 'task-priority',
    label: 'Set Priority',
    description: 'Change task priority',
    category: 'tasks',
    sequence: parseShortcutString('P'),
    scope: 'list',
  },
  
  // Approvals
  {
    id: 'approval-approve',
    label: 'Approve',
    description: 'Approve current item',
    category: 'approvals',
    sequence: parseShortcutString('Shift+A'),
    scope: 'global',
  },
  {
    id: 'approval-reject',
    label: 'Reject',
    description: 'Reject current item',
    category: 'approvals',
    sequence: parseShortcutString('Shift+R'),
    scope: 'global',
  },
  {
    id: 'approval-request',
    label: 'Request Approval',
    description: 'Request approval for current item',
    category: 'approvals',
    sequence: parseShortcutString('Shift+Q'),
    scope: 'global',
  },
  
  // Exports
  {
    id: 'export-pdf',
    label: 'Export PDF',
    description: 'Export current view as PDF',
    category: 'exports',
    sequence: parseShortcutString('Cmd+P'),
    scope: 'global',
  },
  {
    id: 'export-csv',
    label: 'Export CSV',
    description: 'Export data as CSV',
    category: 'exports',
    sequence: parseShortcutString('Cmd+Shift+E'),
    scope: 'global',
  },
  
  // Editing
  {
    id: 'edit-save',
    label: 'Save',
    description: 'Save current changes',
    category: 'editing',
    sequence: parseShortcutString('Cmd+S'),
    scope: 'form',
  },
  {
    id: 'edit-cancel',
    label: 'Cancel',
    description: 'Cancel current changes',
    category: 'editing',
    sequence: parseShortcutString('escape'),
    scope: 'form',
  },
  {
    id: 'edit-undo',
    label: 'Undo',
    description: 'Undo last change',
    category: 'editing',
    sequence: parseShortcutString('Cmd+Z'),
    scope: 'editor',
  },
  {
    id: 'edit-redo',
    label: 'Redo',
    description: 'Redo last change',
    category: 'editing',
    sequence: parseShortcutString('Cmd+Shift+Z'),
    scope: 'editor',
  },
  
  // UI
  {
    id: 'ui-toggle-theme',
    label: 'Toggle Theme',
    description: 'Switch between light and dark theme',
    category: 'ui',
    sequence: parseShortcutString('T D'),
    scope: 'global',
  },
  {
    id: 'ui-toggle-sidebar',
    label: 'Toggle Sidebar',
    description: 'Show/hide sidebar',
    category: 'ui',
    sequence: parseShortcutString('T S'),
    scope: 'global',
  },
  {
    id: 'ui-toggle-compact',
    label: 'Toggle Compact Mode',
    description: 'Switch density mode',
    category: 'ui',
    sequence: parseShortcutString('T C'),
    scope: 'global',
  },
  
  // Help
  {
    id: 'help-shortcuts',
    label: 'Show Shortcuts',
    description: 'Show all keyboard shortcuts',
    category: 'help',
    sequence: parseShortcutString('?'),
    scope: 'global',
  },
  {
    id: 'help-documentation',
    label: 'Documentation',
    description: 'Open documentation',
    category: 'help',
    sequence: parseShortcutString('H D'),
    scope: 'global',
  },
];

// =============================================================================
// Store
// =============================================================================

export const useKeyboardShortcutsStore = create<ShortcutsState>()(
  persist(
    (set, get) => ({
      shortcuts: new Map(),
      overrides: [],
      chordBuffer: [],
      chordTimeout: 1000, // 1 second for chord input
      isChordActive: false,
      lastChordTime: 0,
      activeScope: 'global',
      scopeStack: ['global'],
      isEnabled: true,
      showHelp: false,
      
      registerShortcut: (shortcut: Shortcut) => {
        set(state => {
          const newShortcuts = new Map(state.shortcuts);
          newShortcuts.set(shortcut.id, shortcut);
          return { shortcuts: newShortcuts };
        });
      },
      
      registerShortcuts: (shortcuts: Shortcut[]) => {
        set(state => {
          const newShortcuts = new Map(state.shortcuts);
          for (const shortcut of shortcuts) {
            newShortcuts.set(shortcut.id, shortcut);
          }
          return { shortcuts: newShortcuts };
        });
      },
      
      unregisterShortcut: (id: string) => {
        set(state => {
          const newShortcuts = new Map(state.shortcuts);
          newShortcuts.delete(id);
          return { shortcuts: newShortcuts };
        });
      },
      
      setOverride: (override: ShortcutOverride) => {
        set(state => ({
          overrides: [
            ...state.overrides.filter(o => o.id !== override.id),
            override,
          ],
        }));
      },
      
      removeOverride: (id: string) => {
        set(state => ({
          overrides: state.overrides.filter(o => o.id !== id),
        }));
      },
      
      resetOverrides: () => {
        set({ overrides: [] });
      },
      
      pushScope: (scope: ShortcutScope) => {
        set(state => ({
          scopeStack: [...state.scopeStack, scope],
          activeScope: scope,
        }));
      },
      
      popScope: () => {
        set(state => {
          const newStack = state.scopeStack.slice(0, -1);
          if (newStack.length === 0) {
            newStack.push('global');
          }
          return {
            scopeStack: newStack,
            activeScope: newStack[newStack.length - 1],
          };
        });
      },
      
      setEnabled: (enabled: boolean) => {
        set({ isEnabled: enabled });
      },
      
      toggleHelp: () => {
        set(state => ({ showHelp: !state.showHelp }));
      },
      
      getShortcutsByCategory: (category: ShortcutCategory) => {
        const { shortcuts } = get();
        return Array.from(shortcuts.values()).filter(s => s.category === category);
      },
      
      getShortcutsByScope: (scope: ShortcutScope) => {
        const { shortcuts } = get();
        return Array.from(shortcuts.values()).filter(s => s.scope === scope);
      },
      
      getShortcutById: (id: string) => {
        return get().shortcuts.get(id);
      },
      
      getEffectiveSequence: (id: string) => {
        const { shortcuts, overrides } = get();
        const override = overrides.find(o => o.id === id);
        if (override) {
          return override.sequence;
        }
        const shortcut = shortcuts.get(id);
        return shortcut?.sequence;
      },
      
      findShortcutBySequence: (sequence: ShortcutKey[]) => {
        const { shortcuts, overrides, activeScope, scopeStack } = get();
        
        // Check all shortcuts that match the sequence
        const matches: Shortcut[] = [];
        
        for (const shortcut of shortcuts.values()) {
          if (!shortcut.enabled && shortcut.enabled !== undefined) continue;
          if (shortcut.when && !shortcut.when()) continue;
          
          // Check if scope matches (current scope or global)
          const isInScope = shortcut.scope === activeScope || 
            shortcut.scope === 'global' ||
            scopeStack.includes(shortcut.scope);
          
          if (!isInScope) continue;
          
          // Get effective sequence (with override)
          const override = overrides.find(o => o.id === shortcut.id);
          const effectiveSequence = override?.sequence || shortcut.sequence;
          
          if (sequencesMatch(sequence, effectiveSequence.keys)) {
            matches.push(shortcut);
          }
        }
        
        if (matches.length === 0) return undefined;
        
        // Return the highest priority match
        // Prefer more specific scope over global
        matches.sort((a, b) => {
          // Priority first
          const priorityDiff = (b.priority || 0) - (a.priority || 0);
          if (priorityDiff !== 0) return priorityDiff;
          
          // Then scope specificity
          if (a.scope !== 'global' && b.scope === 'global') return -1;
          if (a.scope === 'global' && b.scope !== 'global') return 1;
          
          return 0;
        });
        
        return matches[0];
      },
      
      handleKeyDown: (event: KeyboardEvent) => {
        const state = get();
        
        if (!state.isEnabled) return false;
        
        // Skip if we're in an input field (unless it's a global shortcut with modifiers)
        const target = event.target as HTMLElement | null;
        const isInInput = target ? (
          target.tagName === 'INPUT' || 
          target.tagName === 'TEXTAREA' || 
          target.isContentEditable
        ) : false;
        
        const now = Date.now();
        const eventKey: ShortcutKey = {
          key: normalizeKey(event.key),
          modifiers: [
            ...(event.ctrlKey ? ['ctrl' as ShortcutModifier] : []),
            ...(event.metaKey ? ['meta' as ShortcutModifier] : []),
            ...(event.altKey ? ['alt' as ShortcutModifier] : []),
            ...(event.shiftKey ? ['shift' as ShortcutModifier] : []),
          ].filter(Boolean) as ShortcutModifier[] | undefined,
        };
        
        // Clean up modifiers if empty
        if (eventKey.modifiers?.length === 0) {
          eventKey.modifiers = undefined;
        }
        
        // Check if chord has timed out
        if (state.isChordActive && now - state.lastChordTime > state.chordTimeout) {
          set({ chordBuffer: [], isChordActive: false });
        }
        
        // Handle chord sequences
        const currentBuffer = state.isChordActive ? [...state.chordBuffer] : [];
        
        // Skip modifier-only keys
        if (['control', 'meta', 'alt', 'shift'].includes(eventKey.key)) {
          return false;
        }
        
        // For chord sequences, we need to handle non-modifier keys
        const hasModifiers = eventKey.modifiers && eventKey.modifiers.length > 0;
        
        // If in input and no modifiers, don't process chords
        if (isInInput && !hasModifiers) {
          return false;
        }
        
        // Try with just this key (single key shortcut or modifier shortcut)
        let shortcut = state.findShortcutBySequence([eventKey]);
        
        if (!shortcut) {
          // Try as part of a chord sequence
          const newBuffer = [...currentBuffer, eventKey];
          shortcut = state.findShortcutBySequence(newBuffer);
          
          if (!shortcut) {
            // Check if this could be a prefix of any chord
            let isPotentialChord = false;
            
            for (const s of state.shortcuts.values()) {
              // Get effective sequence (with override)
              const override = state.overrides.find(o => o.id === s.id);
              const effectiveSequence = override?.sequence || s.sequence;
              
              if (effectiveSequence.isChord && effectiveSequence.keys.length > newBuffer.length) {
                let matches = true;
                for (let i = 0; i < newBuffer.length; i++) {
                  if (newBuffer[i].key !== effectiveSequence.keys[i].key) {
                    matches = false;
                    break;
                  }
                }
                if (matches) {
                  isPotentialChord = true;
                  break;
                }
              }
            }
            
            if (isPotentialChord) {
              // Save to chord buffer
              set({
                chordBuffer: newBuffer,
                isChordActive: true,
                lastChordTime: now,
              });
              event.preventDefault();
              return true;
            } else if (currentBuffer.length > 0) {
              // Not a chord, reset buffer
              set({ chordBuffer: [], isChordActive: false });
            }
            
            return false;
          }
        }
        
        // Found a matching shortcut
        set({ chordBuffer: [], isChordActive: false });
        
        // Execute the shortcut
        event.preventDefault();
        event.stopPropagation();
        
        try {
          shortcut.handler();
        } catch (error) {
          console.error(`Error executing shortcut ${shortcut.id}:`, error);
        }
        
        return true;
      },
      
      resetChordBuffer: () => {
        set({ chordBuffer: [], isChordActive: false });
      },
      
      formatSequence: (sequence: ShortcutSequence) => {
        return formatShortcutSequence(sequence);
      },
    }),
    {
      name: 'keyboard-shortcuts',
      partialize: (state) => ({
        overrides: state.overrides,
      }),
    }
  )
);

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook to use global keyboard shortcuts
 */
export function useKeyboardShortcuts(): void {
  const handleKeyDown = useKeyboardShortcutsStore(state => state.handleKeyDown);
  
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      handleKeyDown(event);
    };
    
    window.addEventListener('keydown', handler, { capture: true });
    
    return () => {
      window.removeEventListener('keydown', handler, { capture: true });
    };
  }, [handleKeyDown]);
}

/**
 * Hook to register a temporary shortcut
 */
export function useShortcut(
  id: string,
  shortcut: string,
  handler: () => void,
  options?: {
    label?: string;
    description?: string;
    category?: ShortcutCategory;
    scope?: ShortcutScope;
    enabled?: boolean;
    when?: () => boolean;
  }
): void {
  const registerShortcut = useKeyboardShortcutsStore(state => state.registerShortcut);
  const unregisterShortcut = useKeyboardShortcutsStore(state => state.unregisterShortcut);
  
  const shortcutObj = useMemo((): Shortcut => ({
    id,
    label: options?.label || id,
    description: options?.description,
    category: options?.category || 'actions',
    sequence: parseShortcutString(shortcut),
    scope: options?.scope || 'global',
    handler,
    enabled: options?.enabled,
    when: options?.when,
  }), [id, shortcut, handler, options?.label, options?.description, options?.category, options?.scope, options?.enabled, options?.when]);
  
  useEffect(() => {
    registerShortcut(shortcutObj);
    
    return () => {
      unregisterShortcut(id);
    };
  }, [shortcutObj, id, registerShortcut, unregisterShortcut]);
}

/**
 * Hook to manage scope
 */
export function useShortcutScope(scope: ShortcutScope): void {
  const pushScope = useKeyboardShortcutsStore(state => state.pushScope);
  const popScope = useKeyboardShortcutsStore(state => state.popScope);
  
  useEffect(() => {
    pushScope(scope);
    
    return () => {
      popScope();
    };
  }, [scope, pushScope, popScope]);
}

/**
 * Hook to temporarily disable shortcuts
 */
export function useDisableShortcuts(): void {
  const setEnabled = useKeyboardShortcutsStore(state => state.setEnabled);
  
  useEffect(() => {
    setEnabled(false);
    
    return () => {
      setEnabled(true);
    };
  }, [setEnabled]);
}

/**
 * Get formatted shortcuts for display
 */
export function useFormattedShortcuts(): {
  byCategory: Record<ShortcutCategory, Array<{ id: string; label: string; shortcut: string }>>;
  all: Array<{ id: string; label: string; description?: string; shortcut: string; category: ShortcutCategory }>;
} {
  const shortcuts = useKeyboardShortcutsStore(state => state.shortcuts);
  const formatSequence = useKeyboardShortcutsStore(state => state.formatSequence);
  const getEffectiveSequence = useKeyboardShortcutsStore(state => state.getEffectiveSequence);
  
  return useMemo(() => {
    const all: Array<{ id: string; label: string; description?: string; shortcut: string; category: ShortcutCategory }> = [];
    const byCategory: Record<ShortcutCategory, Array<{ id: string; label: string; shortcut: string }>> = {
      navigation: [],
      actions: [],
      editing: [],
      approvals: [],
      exports: [],
      tasks: [],
      ui: [],
      help: [],
    };
    
    for (const [id, shortcut] of shortcuts) {
      const sequence = getEffectiveSequence(id);
      if (!sequence) continue;
      
      const formatted = formatSequence(sequence);
      
      all.push({
        id,
        label: shortcut.label,
        description: shortcut.description,
        shortcut: formatted,
        category: shortcut.category,
      });
      
      byCategory[shortcut.category].push({
        id,
        label: shortcut.label,
        shortcut: formatted,
      });
    }
    
    return { byCategory, all };
  }, [shortcuts, formatSequence, getEffectiveSequence]);
}

// =============================================================================
// Initialize Default Shortcuts
// =============================================================================

/**
 * Initialize the keyboard shortcuts system with default shortcuts
 * Call this once at app startup with handlers
 */
export function initializeKeyboardShortcuts(handlers: Record<string, () => void | Promise<void>>): void {
  const store = useKeyboardShortcutsStore.getState();
  
  const shortcuts: Shortcut[] = defaultShortcuts.map(s => ({
    ...s,
    handler: handlers[s.id] || (() => console.warn(`No handler for shortcut: ${s.id}`)),
  }));
  
  store.registerShortcuts(shortcuts);
}

// =============================================================================
// Export Types and Utils
// =============================================================================

export type {
  Shortcut,
  ShortcutKey,
  ShortcutSequence,
  ShortcutOverride,
  ShortcutsState,
};

export {
  defaultShortcuts,
  formatShortcutSequence as formatShortcut,
};
