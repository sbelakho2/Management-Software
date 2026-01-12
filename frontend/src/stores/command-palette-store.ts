import { create } from 'zustand';

// =============================================================================
// Types
// =============================================================================

export type CommandCategory = 
  | 'navigation'
  | 'actions'
  | 'search'
  | 'settings'
  | 'help'
  | 'recent';

export type CommandAction = 
  | { type: 'navigate'; path: string }
  | { type: 'callback'; handler: () => void | Promise<void> }
  | { type: 'open-modal'; modalId: string; data?: Record<string, unknown> }
  | { type: 'toggle'; settingKey: string }
  | { type: 'search'; searchType: string };

export interface Command {
  id: string;
  label: string;
  description?: string;
  category: CommandCategory;
  icon?: string;
  keywords?: string[];
  shortcut?: string;
  action: CommandAction;
  disabled?: boolean;
  hidden?: boolean;
  section?: string;
}

export interface CommandGroup {
  id: string;
  label: string;
  commands: Command[];
  priority?: number;
}

export interface CommandSearchResult {
  command: Command;
  score: number;
  matches: Array<{
    indices: Array<[number, number]>;
    value: string;
    key: string;
  }>;
}

// =============================================================================
// State Interface
// =============================================================================

interface CommandPaletteState {
  // Open/Close state
  isOpen: boolean;
  
  // Search
  query: string;
  
  // Selection
  selectedIndex: number;
  
  // Commands
  commands: Command[];
  filteredCommands: CommandSearchResult[];
  
  // History
  recentCommands: string[];
  maxRecentCommands: number;
  
  // Mode
  mode: 'commands' | 'search' | 'goto';
  searchPrefix: string;
  
  // Loading state for async commands
  isExecuting: boolean;
  executingCommandId: string | null;
  
  // Actions
  open: (mode?: 'commands' | 'search' | 'goto') => void;
  close: () => void;
  toggle: () => void;
  
  setQuery: (query: string) => void;
  clearQuery: () => void;
  
  selectNext: () => void;
  selectPrevious: () => void;
  selectFirst: () => void;
  selectIndex: (index: number) => void;
  
  executeSelected: () => Promise<void>;
  executeCommand: (commandId: string) => Promise<void>;
  
  registerCommand: (command: Command) => void;
  registerCommands: (commands: Command[]) => void;
  unregisterCommand: (commandId: string) => void;
  
  clearRecentCommands: () => void;
}

// =============================================================================
// Fuzzy Search Implementation
// =============================================================================

/**
 * Calculate fuzzy match score between query and text
 * Higher score = better match
 * Returns 0 if no match
 */
function fuzzyMatch(query: string, text: string): { score: number; indices: Array<[number, number]> } {
  const queryLower = query.toLowerCase();
  const textLower = text.toLowerCase();
  
  if (query.length === 0) {
    return { score: 1, indices: [] };
  }
  
  if (textLower.includes(queryLower)) {
    // Exact substring match - high score
    const startIndex = textLower.indexOf(queryLower);
    const score = 100 + (query.length / text.length) * 50;
    return {
      score: startIndex === 0 ? score + 25 : score, // Bonus for prefix match
      indices: [[startIndex, startIndex + query.length - 1]],
    };
  }
  
  // Fuzzy match using character-by-character matching
  let queryIndex = 0;
  let score = 0;
  const indices: Array<[number, number]> = [];
  let consecutiveMatches = 0;
  let lastMatchIndex = -2;
  let matchStart = -1;
  
  for (let i = 0; i < textLower.length && queryIndex < queryLower.length; i++) {
    if (textLower[i] === queryLower[queryIndex]) {
      // Character match
      score += 10;
      
      // Bonus for consecutive matches
      if (i === lastMatchIndex + 1) {
        consecutiveMatches++;
        score += consecutiveMatches * 5;
      } else {
        // End of consecutive run, record the range
        if (matchStart !== -1) {
          indices.push([matchStart, lastMatchIndex]);
        }
        consecutiveMatches = 0;
        matchStart = i;
      }
      
      // Bonus for word boundary matches
      if (i === 0 || text[i - 1] === ' ' || text[i - 1] === '-' || text[i - 1] === '_') {
        score += 15;
      }
      
      // Bonus for camelCase matches
      if (i > 0 && text[i] === text[i].toUpperCase() && text[i - 1] === text[i - 1].toLowerCase()) {
        score += 10;
      }
      
      lastMatchIndex = i;
      queryIndex++;
    }
  }
  
  // Record last match range
  if (matchStart !== -1 && lastMatchIndex >= matchStart) {
    indices.push([matchStart, lastMatchIndex]);
  }
  
  // If not all query characters were matched, no match
  if (queryIndex < queryLower.length) {
    return { score: 0, indices: [] };
  }
  
  // Adjust score based on text length (shorter matches are better)
  score = score * (query.length / text.length);
  
  return { score, indices };
}

/**
 * Search commands with fuzzy matching
 */
function searchCommands(
  commands: Command[],
  query: string
): CommandSearchResult[] {
  if (!query.trim()) {
    // Return all non-hidden commands, prioritizing recent
    return commands
      .filter(cmd => !cmd.hidden && !cmd.disabled)
      .map(command => ({
        command,
        score: 1,
        matches: [],
      }));
  }
  
  const results: CommandSearchResult[] = [];
  
  for (const command of commands) {
    if (command.hidden || command.disabled) {
      continue;
    }
    
    // Match against label
    const labelMatch = fuzzyMatch(query, command.label);
    
    // Match against description
    const descMatch = command.description
      ? fuzzyMatch(query, command.description)
      : { score: 0, indices: [] };
    
    // Match against keywords
    let keywordScore = 0;
    let keywordIndices: Array<[number, number]> = [];
    for (const keyword of command.keywords || []) {
      const kwMatch = fuzzyMatch(query, keyword);
      if (kwMatch.score > keywordScore) {
        keywordScore = kwMatch.score;
        keywordIndices = kwMatch.indices;
      }
    }
    
    // Best score wins
    const bestScore = Math.max(labelMatch.score, descMatch.score * 0.8, keywordScore * 0.9);
    
    if (bestScore > 0) {
      const matches: CommandSearchResult['matches'] = [];
      
      if (labelMatch.score > 0) {
        matches.push({
          key: 'label',
          value: command.label,
          indices: labelMatch.indices,
        });
      }
      if (descMatch.score > 0 && command.description) {
        matches.push({
          key: 'description',
          value: command.description,
          indices: descMatch.indices,
        });
      }
      
      results.push({
        command,
        score: bestScore,
        matches,
      });
    }
  }
  
  // Sort by score (highest first)
  results.sort((a, b) => b.score - a.score);
  
  return results;
}

// =============================================================================
// Default Commands
// =============================================================================

const defaultCommands: Command[] = [
  // Navigation
  {
    id: 'nav-dashboard',
    label: 'Go to Dashboard',
    description: 'Navigate to the main dashboard',
    category: 'navigation',
    icon: 'home',
    keywords: ['home', 'main', 'overview'],
    shortcut: 'G D',
    action: { type: 'navigate', path: '/today' },
  },
  {
    id: 'nav-rfq',
    label: 'Go to RFQs',
    description: 'View and manage RFQ pipeline',
    category: 'navigation',
    icon: 'file-text',
    keywords: ['quote', 'request', 'pipeline'],
    shortcut: 'G R',
    action: { type: 'navigate', path: '/pipeline' },
  },
  {
    id: 'nav-work-orders',
    label: 'Go to Work Orders',
    description: 'View production work orders',
    category: 'navigation',
    icon: 'clipboard-list',
    keywords: ['production', 'manufacturing', 'jobs'],
    shortcut: 'G W',
    action: { type: 'navigate', path: '/production' },
  },
  {
    id: 'nav-quality',
    label: 'Go to Quality',
    description: 'Quality management and inspections',
    category: 'navigation',
    icon: 'check-circle',
    keywords: ['inspection', 'qc', 'control'],
    shortcut: 'G Q',
    action: { type: 'navigate', path: '/quality' },
  },
  {
    id: 'nav-andon',
    label: 'Go to Andon Board',
    description: 'Real-time production status',
    category: 'navigation',
    icon: 'activity',
    keywords: ['status', 'production', 'alerts', 'live'],
    shortcut: 'G A',
    action: { type: 'navigate', path: '/andon' },
  },
  {
    id: 'nav-learning',
    label: 'Go to Training',
    description: 'Training and learning content',
    category: 'navigation',
    icon: 'book-open',
    keywords: ['training', 'education', 'tps', 'course', 'learning'],
    shortcut: 'G L',
    action: { type: 'navigate', path: '/training' },
  },
  {
    id: 'nav-settings',
    label: 'Go to Settings',
    description: 'Application settings and preferences',
    category: 'settings',
    icon: 'settings',
    keywords: ['preferences', 'config', 'options'],
    shortcut: 'G S',
    action: { type: 'navigate', path: '/settings' },
  },
  
  // Actions
  {
    id: 'action-new-rfq',
    label: 'Create New RFQ',
    description: 'Start a new request for quote',
    category: 'actions',
    icon: 'plus-circle',
    keywords: ['add', 'create', 'new', 'quote'],
    shortcut: 'N R',
    action: { type: 'open-modal', modalId: 'new-rfq' },
  },
  {
    id: 'action-new-work-order',
    label: 'Create Work Order',
    description: 'Create a new production work order',
    category: 'actions',
    icon: 'plus-circle',
    keywords: ['add', 'create', 'new', 'production'],
    shortcut: 'N W',
    action: { type: 'open-modal', modalId: 'new-work-order' },
  },
  {
    id: 'action-new-task',
    label: 'Create Task',
    description: 'Create a new task',
    category: 'actions',
    icon: 'plus',
    keywords: ['add', 'create', 'new', 'todo'],
    shortcut: 'N T',
    action: { type: 'open-modal', modalId: 'new-task' },
  },
  {
    id: 'action-search',
    label: 'Search Everything',
    description: 'Global search across all content',
    category: 'search',
    icon: 'search',
    keywords: ['find', 'lookup', 'query'],
    shortcut: '/',
    action: { type: 'search', searchType: 'global' },
  },
  {
    id: 'action-quick-action',
    label: 'Quick Action',
    description: 'Perform a quick action',
    category: 'actions',
    icon: 'zap',
    keywords: ['fast', 'quick', 'shortcut'],
    action: { type: 'open-modal', modalId: 'quick-action' },
  },
  
  // Settings
  {
    id: 'settings-toggle-theme',
    label: 'Toggle Dark Mode',
    description: 'Switch between light and dark theme',
    category: 'settings',
    icon: 'moon',
    keywords: ['dark', 'light', 'theme', 'appearance'],
    shortcut: 'T D',
    action: { type: 'toggle', settingKey: 'theme' },
  },
  {
    id: 'settings-toggle-sidebar',
    label: 'Toggle Sidebar',
    description: 'Expand or collapse the sidebar',
    category: 'settings',
    icon: 'sidebar',
    keywords: ['menu', 'navigation', 'collapse', 'expand'],
    shortcut: 'T S',
    action: { type: 'toggle', settingKey: 'sidebar' },
  },
  {
    id: 'settings-toggle-compact',
    label: 'Toggle Compact Mode',
    description: 'Switch between compact and spacious layout',
    category: 'settings',
    icon: 'minimize',
    keywords: ['density', 'layout', 'spacing'],
    shortcut: 'T C',
    action: { type: 'toggle', settingKey: 'compactMode' },
  },
  
  // Help
  {
    id: 'help-shortcuts',
    label: 'Keyboard Shortcuts',
    description: 'View all keyboard shortcuts',
    category: 'help',
    icon: 'keyboard',
    keywords: ['keys', 'hotkeys', 'bindings'],
    shortcut: '?',
    action: { type: 'open-modal', modalId: 'keyboard-shortcuts' },
  },
  {
    id: 'help-docs',
    label: 'Documentation',
    description: 'Open documentation',
    category: 'help',
    icon: 'book',
    keywords: ['help', 'guide', 'manual', 'docs'],
    action: { type: 'open-external', url: 'https://docs.sensei-os.com' },
  },
  {
    id: 'help-support',
    label: 'Contact Support',
    description: 'Get help from support team',
    category: 'help',
    icon: 'help-circle',
    keywords: ['contact', 'assistance', 'ticket'],
    action: { type: 'open-modal', modalId: 'support' },
  },
];

// =============================================================================
// Store
// =============================================================================

export const useCommandPaletteStore = create<CommandPaletteState>((set, get) => ({
  // Initial state
  isOpen: false,
  query: '',
  selectedIndex: 0,
  commands: defaultCommands,
  filteredCommands: [],
  recentCommands: [],
  maxRecentCommands: 10,
  mode: 'commands',
  searchPrefix: '',
  isExecuting: false,
  executingCommandId: null,
  
  // Actions
  open: (mode = 'commands') => {
    set({ isOpen: true, mode, query: '', selectedIndex: 0 });
    // Update filtered commands
    const { commands, recentCommands } = get();
    const filtered = searchCommands(commands, '');
    
    // Prioritize recent commands
    const prioritized = filtered.sort((a, b) => {
      const aRecent = recentCommands.indexOf(a.command.id);
      const bRecent = recentCommands.indexOf(b.command.id);
      
      if (aRecent >= 0 && bRecent >= 0) {
        return aRecent - bRecent;
      }
      if (aRecent >= 0) return -1;
      if (bRecent >= 0) return 1;
      
      return b.score - a.score;
    });
    
    set({ filteredCommands: prioritized });
  },
  
  close: () => {
    set({
      isOpen: false,
      query: '',
      selectedIndex: 0,
      isExecuting: false,
      executingCommandId: null,
    });
  },
  
  toggle: () => {
    const { isOpen, open, close } = get();
    if (isOpen) {
      close();
    } else {
      open();
    }
  },
  
  setQuery: (query) => {
    const { commands, recentCommands } = get();
    const filtered = searchCommands(commands, query);
    
    // Prioritize recent commands for empty query
    const prioritized = query
      ? filtered
      : filtered.sort((a, b) => {
          const aRecent = recentCommands.indexOf(a.command.id);
          const bRecent = recentCommands.indexOf(b.command.id);
          
          if (aRecent >= 0 && bRecent >= 0) {
            return aRecent - bRecent;
          }
          if (aRecent >= 0) return -1;
          if (bRecent >= 0) return 1;
          
          return b.score - a.score;
        });
    
    set({
      query,
      filteredCommands: prioritized,
      selectedIndex: 0,
    });
  },
  
  clearQuery: () => {
    const { setQuery } = get();
    setQuery('');
  },
  
  selectNext: () => {
    const { selectedIndex, filteredCommands } = get();
    const maxIndex = filteredCommands.length - 1;
    set({ selectedIndex: Math.min(selectedIndex + 1, maxIndex) });
  },
  
  selectPrevious: () => {
    const { selectedIndex } = get();
    set({ selectedIndex: Math.max(selectedIndex - 1, 0) });
  },
  
  selectFirst: () => {
    set({ selectedIndex: 0 });
  },
  
  selectIndex: (index) => {
    const { filteredCommands } = get();
    if (index >= 0 && index < filteredCommands.length) {
      set({ selectedIndex: index });
    }
  },
  
  executeSelected: async () => {
    const { filteredCommands, selectedIndex, executeCommand } = get();
    const selected = filteredCommands[selectedIndex];
    
    if (selected) {
      await executeCommand(selected.command.id);
    }
  },
  
  executeCommand: async (commandId) => {
    const { commands, recentCommands, maxRecentCommands, close } = get();
    const command = commands.find(c => c.id === commandId);
    
    if (!command || command.disabled) {
      return;
    }
    
    set({ isExecuting: true, executingCommandId: commandId });
    
    try {
      // Execute the action
      const { action } = command;
      
      switch (action.type) {
        case 'navigate':
          // Navigation will be handled by the component using router
          // Store just emits the intent
          break;
        case 'callback':
          await action.handler();
          break;
        case 'open-modal':
          // Modal will be handled by the component
          break;
        case 'toggle':
          // Toggle will be handled by the component
          break;
        case 'search':
          // Search will be handled by the component
          break;
      }
      
      // Add to recent commands
      const newRecent = [
        commandId,
        ...recentCommands.filter(id => id !== commandId),
      ].slice(0, maxRecentCommands);
      
      set({ recentCommands: newRecent });
      
      // Close the palette after execution
      close();
    } catch (error) {
      console.error('Error executing command:', error);
    } finally {
      set({ isExecuting: false, executingCommandId: null });
    }
  },
  
  registerCommand: (command) => {
    set(state => ({
      commands: [...state.commands.filter(c => c.id !== command.id), command],
    }));
  },
  
  registerCommands: (newCommands) => {
    set(state => {
      const existingIds = new Set(newCommands.map(c => c.id));
      const filtered = state.commands.filter(c => !existingIds.has(c.id));
      return {
        commands: [...filtered, ...newCommands],
      };
    });
  },
  
  unregisterCommand: (commandId) => {
    set(state => ({
      commands: state.commands.filter(c => c.id !== commandId),
    }));
  },
  
  clearRecentCommands: () => {
    set({ recentCommands: [] });
  },
}));

// =============================================================================
// Selectors
// =============================================================================

export const selectIsOpen = (state: CommandPaletteState) => state.isOpen;
export const selectQuery = (state: CommandPaletteState) => state.query;
export const selectFilteredCommands = (state: CommandPaletteState) => state.filteredCommands;
export const selectSelectedIndex = (state: CommandPaletteState) => state.selectedIndex;
export const selectSelectedCommand = (state: CommandPaletteState) => 
  state.filteredCommands[state.selectedIndex];
export const selectIsExecuting = (state: CommandPaletteState) => state.isExecuting;

// =============================================================================
// Hooks
// =============================================================================

export function useCommandPalette() {
  const store = useCommandPaletteStore();
  return {
    isOpen: store.isOpen,
    query: store.query,
    filteredCommands: store.filteredCommands,
    selectedIndex: store.selectedIndex,
    selectedCommand: store.filteredCommands[store.selectedIndex],
    isExecuting: store.isExecuting,
    open: store.open,
    close: store.close,
    toggle: store.toggle,
    setQuery: store.setQuery,
    selectNext: store.selectNext,
    selectPrevious: store.selectPrevious,
    selectIndex: store.selectIndex,
    executeSelected: store.executeSelected,
    executeCommand: store.executeCommand,
    registerCommand: store.registerCommand,
    registerCommands: store.registerCommands,
    unregisterCommand: store.unregisterCommand,
  };
}
