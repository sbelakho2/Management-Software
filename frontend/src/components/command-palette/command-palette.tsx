'use client';

import React, { useEffect, useRef, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { 
  useCommandPaletteStore,
  Command,
  CommandSearchResult,
  CommandCategory,
} from '@/stores/command-palette-store';
import { useUIStore } from '@/stores/ui-store';
import { cn } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

// =============================================================================
// Icons
// =============================================================================

const icons: Record<string, React.ReactNode> = {
  home: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  ),
  'file-text': (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  'clipboard-list': (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
    </svg>
  ),
  'check-circle': (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  activity: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  ),
  'book-open': (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  ),
  settings: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  'plus-circle': (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  plus: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  ),
  search: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  zap: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  moon: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  ),
  sidebar: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
    </svg>
  ),
  minimize: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
    </svg>
  ),
  keyboard: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
    </svg>
  ),
  book: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  ),
  'help-circle': (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  default: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
};

function getIcon(iconName?: string): React.ReactNode {
  if (!iconName) return icons.default;
  return icons[iconName] || icons.default;
}

// =============================================================================
// Category Labels
// =============================================================================

const categoryLabels: Record<CommandCategory, string> = {
  navigation: 'Navigation',
  actions: 'Actions',
  search: 'Search',
  settings: 'Settings',
  help: 'Help',
  recent: 'Recent',
};

// =============================================================================
// Highlighted Text Component
// =============================================================================

interface HighlightedTextProps {
  text: string;
  indices: Array<[number, number]>;
}

function HighlightedText({ text, indices }: HighlightedTextProps) {
  if (!indices || indices.length === 0) {
    return <span>{text}</span>;
  }

  const result: React.ReactNode[] = [];
  let lastIndex = 0;

  for (const [start, end] of indices) {
    if (start > lastIndex) {
      result.push(
        <span key={`text-${lastIndex}`}>{text.slice(lastIndex, start)}</span>
      );
    }
    result.push(
      <span 
        key={`highlight-${start}`} 
        className="bg-primary/20 text-primary font-medium"
      >
        {text.slice(start, end + 1)}
      </span>
    );
    lastIndex = end + 1;
  }

  if (lastIndex < text.length) {
    result.push(<span key={`text-${lastIndex}`}>{text.slice(lastIndex)}</span>);
  }

  return <>{result}</>;
}

// =============================================================================
// Command Item Component
// =============================================================================

interface CommandItemProps {
  result: CommandSearchResult;
  isSelected: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
}

function CommandItem({ result, isSelected, onClick, onMouseEnter }: CommandItemProps) {
  const { command, matches } = result;
  
  // Find label match indices
  const labelMatch = matches.find(m => m.key === 'label');
  const labelIndices = labelMatch?.indices || [];
  
  return (
    <button
      type="button"
      className={cn(
        'w-full flex items-center gap-3 px-4 py-3 text-left',
        'transition-colors duration-150',
        isSelected 
          ? 'bg-primary/10 text-primary' 
          : 'text-foreground hover:bg-muted'
      )}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      data-command-id={command.id}
    >
      {/* Icon */}
      <span className={cn(
        'flex-shrink-0 opacity-70',
        isSelected && 'opacity-100'
      )}>
        {getIcon(command.icon)}
      </span>
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">
          <HighlightedText text={command.label} indices={labelIndices} />
        </div>
        {command.description && (
          <div className="text-sm text-muted-foreground truncate">
            {command.description}
          </div>
        )}
      </div>
      
      {/* Shortcut */}
      {command.shortcut && (
        <div className="flex-shrink-0 flex items-center gap-1">
          {command.shortcut.split(' ').map((key, i) => (
            <kbd
              key={i}
              className={cn(
                'px-1.5 py-0.5 text-xs font-mono rounded',
                'bg-muted border border-border',
                isSelected && 'bg-primary/20 border-primary/30'
              )}
            >
              {key}
            </kbd>
          ))}
        </div>
      )}
    </button>
  );
}

// =============================================================================
// Command Group Component
// =============================================================================

interface CommandGroupProps {
  category: CommandCategory;
  results: CommandSearchResult[];
  selectedIndex: number;
  globalIndexOffset: number;
  onSelect: (index: number) => void;
  onExecute: (commandId: string) => void;
}

function CommandGroup({ 
  category, 
  results, 
  selectedIndex, 
  globalIndexOffset,
  onSelect,
  onExecute,
}: CommandGroupProps) {
  if (results.length === 0) return null;
  
  return (
    <div className="py-2">
      <div className="px-4 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        {categoryLabels[category]}
      </div>
      {results.map((result, index) => {
        const globalIndex = globalIndexOffset + index;
        return (
          <CommandItem
            key={result.command.id}
            result={result}
            isSelected={globalIndex === selectedIndex}
            onClick={() => onExecute(result.command.id)}
            onMouseEnter={() => onSelect(globalIndex)}
          />
        );
      })}
    </div>
  );
}

// =============================================================================
// Command Palette Component
// =============================================================================

export interface CommandPaletteProps {
  className?: string;
}

export function CommandPalette({ className }: CommandPaletteProps) {
  const router = useRouter();
  const { t } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  
  const {
    isOpen,
    query,
    filteredCommands,
    selectedIndex,
    isExecuting,
    close,
    setQuery,
    selectNext,
    selectPrevious,
    selectIndex,
    executeCommand,
  } = useCommandPaletteStore();
  
  const { openModal, setTheme, theme, setSidebarState, sidebarState, setCompactMode, compactMode } = useUIStore();
  
  // Group commands by category
  const groupedCommands = useMemo(() => {
    const groups: Record<CommandCategory, CommandSearchResult[]> = {
      recent: [],
      navigation: [],
      actions: [],
      search: [],
      settings: [],
      help: [],
    };
    
    for (const result of filteredCommands) {
      const category = result.command.category;
      if (groups[category]) {
        groups[category].push(result);
      }
    }
    
    return groups;
  }, [filteredCommands]);
  
  // Calculate global indices for grouped display
  const categoryOrder: CommandCategory[] = ['recent', 'navigation', 'actions', 'search', 'settings', 'help'];
  const categoryOffsets = useMemo(() => {
    const offsets: Record<CommandCategory, number> = {
      recent: 0,
      navigation: 0,
      actions: 0,
      search: 0,
      settings: 0,
      help: 0,
    };
    
    let offset = 0;
    for (const category of categoryOrder) {
      offsets[category] = offset;
      offset += groupedCommands[category].length;
    }
    
    return offsets;
  }, [groupedCommands]);
  
  // Handle command execution with action types
  const handleExecuteCommand = useCallback(async (commandId: string) => {
    const command = filteredCommands.find(r => r.command.id === commandId)?.command;
    if (!command) return;
    
    const { action } = command;
    
    switch (action.type) {
      case 'navigate':
        close();
        router.push(action.path);
        break;
      case 'open-modal':
        close();
        openModal(action.modalId, action.data);
        break;
      case 'toggle':
        if (action.settingKey === 'theme') {
          setTheme(theme === 'dark' ? 'light' : 'dark');
        } else if (action.settingKey === 'sidebar') {
          setSidebarState(sidebarState === 'expanded' ? 'collapsed' : 'expanded');
        } else if (action.settingKey === 'compactMode') {
          setCompactMode(!compactMode);
        }
        close();
        break;
      case 'search':
        // Handle search mode
        close();
        break;
      case 'callback':
        await executeCommand(commandId);
        break;
      default:
        await executeCommand(commandId);
    }
  }, [filteredCommands, close, router, openModal, setTheme, theme, setSidebarState, sidebarState, setCompactMode, compactMode, executeCommand]);
  
  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        selectNext();
        break;
      case 'ArrowUp':
        e.preventDefault();
        selectPrevious();
        break;
      case 'Enter':
        e.preventDefault();
        const selected = filteredCommands[selectedIndex];
        if (selected) {
          handleExecuteCommand(selected.command.id);
        }
        break;
      case 'Escape':
        e.preventDefault();
        close();
        break;
      case 'Tab':
        e.preventDefault();
        if (e.shiftKey) {
          selectPrevious();
        } else {
          selectNext();
        }
        break;
    }
  }, [selectNext, selectPrevious, selectedIndex, filteredCommands, handleExecuteCommand, close]);
  
  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);
  
  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current && isOpen) {
      const selectedElement = listRef.current.querySelector(
        `[data-command-id="${filteredCommands[selectedIndex]?.command.id}"]`
      );
      if (selectedElement && typeof selectedElement.scrollIntoView === 'function') {
        selectedElement.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex, isOpen, filteredCommands]);
  
  // Global keyboard shortcut to open command palette
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        useCommandPaletteStore.getState().toggle();
      }
    };
    
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);
  
  if (!isOpen) return null;
  
  return (
    <div 
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          close();
        }
      }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" />
      
      {/* Command Palette */}
      <div 
        className={cn(
          'relative w-full max-w-xl mx-4',
          'bg-popover border border-border rounded-xl shadow-2xl',
          'animate-in fade-in-0 zoom-in-95 duration-200',
          className
        )}
        role="dialog"
        aria-modal="true"
        aria-label={t('components.commandPalette.ariaLabel')}
      >
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <span className="text-muted-foreground">
            {icons.search}
          </span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('components.commandPalette.placeholder')}
            className={cn(
              'flex-1 bg-transparent text-foreground placeholder:text-muted-foreground',
              'focus:outline-none text-base'
            )}
            aria-label={t('components.commandPalette.searchAriaLabel')}
            aria-autocomplete="list"
            aria-controls="command-list"
            aria-activedescendant={
              filteredCommands[selectedIndex]?.command.id
            }
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
          <kbd className="px-2 py-1 text-xs font-mono text-muted-foreground bg-muted rounded border border-border">
            esc
          </kbd>
        </div>
        
        {/* Command List */}
        <div 
          ref={listRef}
          id="command-list"
          role="listbox"
          className="max-h-[50vh] overflow-y-auto"
        >
          {filteredCommands.length === 0 ? (
            <div className="px-4 py-8 text-center text-muted-foreground">
              <p className="text-sm">{t('components.commandPalette.noCommandsFound')}</p>
              <p className="text-xs mt-1">{t('components.commandPalette.tryDifferentSearch')}</p>
            </div>
          ) : (
            <>
              {categoryOrder.map(category => (
                <CommandGroup
                  key={category}
                  category={category}
                  results={groupedCommands[category]}
                  selectedIndex={selectedIndex}
                  globalIndexOffset={categoryOffsets[category]}
                  onSelect={selectIndex}
                  onExecute={handleExecuteCommand}
                />
              ))}
            </>
          )}
        </div>
        
        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-border text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-muted rounded border border-border">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-muted rounded border border-border">↓</kbd>
              <span className="ml-1">Navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-muted rounded border border-border">↵</kbd>
              <span className="ml-1">Select</span>
            </span>
          </div>
          <div className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-muted rounded border border-border">⌘</kbd>
            <kbd className="px-1.5 py-0.5 bg-muted rounded border border-border">K</kbd>
            <span className="ml-1">{t('components.commandPalette.toToggle')}</span>
          </div>
        </div>
        
        {/* Loading overlay */}
        {isExecuting && (
          <div className="absolute inset-0 bg-background/50 flex items-center justify-center rounded-xl">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        )}
      </div>
    </div>
  );
}

export default CommandPalette;
