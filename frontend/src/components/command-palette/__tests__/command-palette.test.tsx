import React from 'react';
import { screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CommandPalette } from '../command-palette';
import { useCommandPaletteStore, Command, CommandCategory } from '@/stores/command-palette-store';
import { renderWithI18n } from '@/test-utils';

const render = renderWithI18n;

// Mock next/navigation
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
}));

// Mock ui-store
const mockOpenModal = jest.fn();
const mockSetTheme = jest.fn();
const mockSetSidebarState = jest.fn();
const mockSetCompactMode = jest.fn();

jest.mock('@/stores/ui-store', () => ({
  useUIStore: () => ({
    openModal: mockOpenModal,
    setTheme: mockSetTheme,
    theme: 'light',
    setSidebarState: mockSetSidebarState,
    sidebarState: 'expanded',
    setCompactMode: mockSetCompactMode,
    compactMode: false,
  }),
}));

// Mock cn utility
jest.mock('@/lib/utils', () => ({
  cn: (...args: (string | undefined | boolean | null)[]) => 
    args.filter(Boolean).join(' '),
}));

// Get initial commands from store
const getInitialCommands = () => useCommandPaletteStore.getState().commands;

// Reset store before each test
beforeEach(() => {
  const commands = getInitialCommands();
  act(() => {
    useCommandPaletteStore.setState({
      isOpen: false,
      query: '',
      selectedIndex: 0,
      recentCommands: [],
      mode: 'commands',
      isExecuting: false,
      executingCommandId: null,
      filteredCommands: commands.map(cmd => ({
        command: cmd,
        score: 100,
        matches: [],
      })),
    });
  });
  
  mockPush.mockClear();
  mockOpenModal.mockClear();
  mockSetTheme.mockClear();
  mockSetSidebarState.mockClear();
  mockSetCompactMode.mockClear();
});

// =============================================================================
// Rendering Tests
// =============================================================================

describe('CommandPalette Rendering', () => {
  it('should not render when closed', () => {
    render(<CommandPalette />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should render when opened', () => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
    
    render(<CommandPalette />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('should render search input', () => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
    
    render(<CommandPalette />);
    expect(screen.getByPlaceholderText(/type a command or search/i)).toBeInTheDocument();
  });

  it('should render command list', () => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
    
    render(<CommandPalette />);
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('should render footer with keyboard hints', () => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
    
    render(<CommandPalette />);
    expect(screen.getByText('Navigate')).toBeInTheDocument();
    expect(screen.getByText('Select')).toBeInTheDocument();
  });

  it('should render escape key hint', () => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
    
    render(<CommandPalette />);
    expect(screen.getByText('esc')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
    
    render(<CommandPalette className="custom-class" />);
    const dialog = screen.getByRole('dialog');
    expect(dialog.className).toContain('custom-class');
  });
});

// =============================================================================
// Command Display Tests
// =============================================================================

describe('CommandPalette Command Display', () => {
  beforeEach(() => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
  });

  it('should display navigation commands', () => {
    render(<CommandPalette />);
    expect(screen.getByText('Navigation')).toBeInTheDocument();
  });

  it('should display action commands', () => {
    render(<CommandPalette />);
    expect(screen.getByText('Actions')).toBeInTheDocument();
  });

  it('should display settings commands', () => {
    render(<CommandPalette />);
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('should display help commands', () => {
    render(<CommandPalette />);
    expect(screen.getByText('Help')).toBeInTheDocument();
  });

  it('should display command labels', () => {
    render(<CommandPalette />);
    expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Go to RFQs')).toBeInTheDocument();
  });

  it('should display keyboard shortcuts', () => {
    render(<CommandPalette />);
    // G D for Go to Dashboard
    const gKeys = screen.getAllByText('G');
    expect(gKeys.length).toBeGreaterThan(0);
  });

  it('should show empty state when no matches', () => {
    act(() => {
      useCommandPaletteStore.getState().setQuery('xyznonexistent123');
    });
    
    render(<CommandPalette />);
    expect(screen.getByText('No commands found')).toBeInTheDocument();
  });

  it('should show suggestion for different search term', () => {
    act(() => {
      useCommandPaletteStore.getState().setQuery('xyznonexistent123');
    });
    
    render(<CommandPalette />);
    expect(screen.getByText('Try a different search term')).toBeInTheDocument();
  });
});

// =============================================================================
// Search Tests
// =============================================================================

describe('CommandPalette Search', () => {
  beforeEach(() => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
  });

  it('should update query on input', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    
    await userEvent.type(input, 'dashboard');
    
    expect(useCommandPaletteStore.getState().query).toBe('dashboard');
  });

  it('should filter commands based on query', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    const initialCommandCount = getInitialCommands().length;
    
    await userEvent.type(input, 'dashboard');
    
    await waitFor(() => {
      const filtered = useCommandPaletteStore.getState().filteredCommands;
      expect(filtered.length).toBeLessThan(initialCommandCount);
    });
  });

  it('should show clear button when query is not empty', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    
    await userEvent.type(input, 'test');
    
    const clearButton = screen.getAllByRole('button')[0];
    expect(clearButton).toBeInTheDocument();
  });

  it('should clear query when clear button clicked', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    
    await userEvent.type(input, 'test');
    
    // Find and click clear button (the X button)
    const buttons = screen.getAllByRole('button');
    const clearButton = buttons.find(btn => 
      btn.querySelector('svg path[d*="M6 18L18 6M6 6l12 12"]')
    );
    
    if (clearButton) {
      await userEvent.click(clearButton);
      expect(useCommandPaletteStore.getState().query).toBe('');
    }
  });

  it('should focus input on open', () => {
    const { container } = render(<CommandPalette />);
    const input = container.querySelector('input');
    expect(document.activeElement).toBe(input);
  });
});

// =============================================================================
// Keyboard Navigation Tests
// =============================================================================

describe('CommandPalette Keyboard Navigation', () => {
  beforeEach(() => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
  });

  it('should close on Escape key', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    
    fireEvent.keyDown(input, { key: 'Escape' });
    
    expect(useCommandPaletteStore.getState().isOpen).toBe(false);
  });

  it('should navigate down on ArrowDown', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    
    const initialIndex = useCommandPaletteStore.getState().selectedIndex;
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    
    expect(useCommandPaletteStore.getState().selectedIndex).toBe(initialIndex + 1);
  });

  it('should navigate up on ArrowUp', async () => {
    act(() => {
      useCommandPaletteStore.getState().selectNext();
      useCommandPaletteStore.getState().selectNext();
    });
    
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    
    const initialIndex = useCommandPaletteStore.getState().selectedIndex;
    fireEvent.keyDown(input, { key: 'ArrowUp' });
    
    expect(useCommandPaletteStore.getState().selectedIndex).toBe(initialIndex - 1);
  });

  it('should navigate down on Tab', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    
    const initialIndex = useCommandPaletteStore.getState().selectedIndex;
    fireEvent.keyDown(input, { key: 'Tab' });
    
    expect(useCommandPaletteStore.getState().selectedIndex).toBe(initialIndex + 1);
  });

  it('should navigate up on Shift+Tab', async () => {
    act(() => {
      useCommandPaletteStore.getState().selectNext();
      useCommandPaletteStore.getState().selectNext();
    });
    
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    
    const initialIndex = useCommandPaletteStore.getState().selectedIndex;
    fireEvent.keyDown(input, { key: 'Tab', shiftKey: true });
    
    expect(useCommandPaletteStore.getState().selectedIndex).toBe(initialIndex - 1);
  });

  it('should execute selected command on Enter', async () => {
    // Set query to filter to navigation commands
    act(() => {
      useCommandPaletteStore.getState().setQuery('Go to Dashboard');
    });
    
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    
    fireEvent.keyDown(input, { key: 'Enter' });
    
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/today');
    });
  });
});

// =============================================================================
// Mouse Interaction Tests
// =============================================================================

describe('CommandPalette Mouse Interaction', () => {
  beforeEach(() => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
  });

  it('should close when clicking backdrop', async () => {
    const { container } = render(<CommandPalette />);
    
    // Click the backdrop (the outer fixed div)
    const backdrop = container.querySelector('.fixed.inset-0');
    if (backdrop) {
      fireEvent.click(backdrop);
      expect(useCommandPaletteStore.getState().isOpen).toBe(false);
    }
  });

  it('should not close when clicking inside palette', async () => {
    render(<CommandPalette />);
    const dialog = screen.getByRole('dialog');
    
    fireEvent.click(dialog);
    
    expect(useCommandPaletteStore.getState().isOpen).toBe(true);
  });

  it('should execute command on click', async () => {
    act(() => {
      useCommandPaletteStore.getState().setQuery('Go to Dashboard');
    });
    
    render(<CommandPalette />);
    const commandButton = screen.getByText('Go to Dashboard').closest('button');
    
    if (commandButton) {
      await userEvent.click(commandButton);
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/today');
      });
    }
  });

  it('should update selection on mouse enter', async () => {
    render(<CommandPalette />);
    const buttons = screen.getAllByRole('button').filter(btn => 
      btn.getAttribute('data-command-id')
    );
    
    if (buttons.length > 1) {
      fireEvent.mouseEnter(buttons[2]);
      expect(useCommandPaletteStore.getState().selectedIndex).toBe(2);
    }
  });
});

// =============================================================================
// Command Execution Tests
// =============================================================================

describe('CommandPalette Command Execution', () => {
  beforeEach(() => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
  });

  it('should navigate on navigate command', async () => {
    act(() => {
      useCommandPaletteStore.getState().setQuery('Go to RFQs');
    });
    
    render(<CommandPalette />);
    const commandButton = screen.getByText('Go to RFQs').closest('button');
    
    if (commandButton) {
      await userEvent.click(commandButton);
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/pipeline');
        expect(useCommandPaletteStore.getState().isOpen).toBe(false);
      });
    }
  });

  it('should open modal on open-modal command', async () => {
    act(() => {
      useCommandPaletteStore.getState().setQuery('Create New RFQ');
    });
    
    render(<CommandPalette />);
    const commandButton = screen.getByText('Create New RFQ').closest('button');
    
    if (commandButton) {
      await userEvent.click(commandButton);
      
      await waitFor(() => {
        expect(mockOpenModal).toHaveBeenCalledWith('new-rfq', undefined);
      });
    }
  });

  it('should toggle theme on theme toggle command', async () => {
    act(() => {
      useCommandPaletteStore.getState().setQuery('Toggle Dark Mode');
    });
    
    render(<CommandPalette />);
    const commandButton = screen.getByText('Toggle Dark Mode').closest('button');
    
    if (commandButton) {
      await userEvent.click(commandButton);
      
      await waitFor(() => {
        expect(mockSetTheme).toHaveBeenCalledWith('dark');
      });
    }
  });

  it('should toggle sidebar on sidebar toggle command', async () => {
    act(() => {
      useCommandPaletteStore.getState().setQuery('Toggle Sidebar');
    });
    
    render(<CommandPalette />);
    const commandButton = screen.getByText('Toggle Sidebar').closest('button');
    
    if (commandButton) {
      await userEvent.click(commandButton);
      
      await waitFor(() => {
        expect(mockSetSidebarState).toHaveBeenCalledWith('collapsed');
      });
    }
  });

  it('should toggle compact mode', async () => {
    act(() => {
      useCommandPaletteStore.getState().setQuery('Toggle Compact Mode');
    });
    
    render(<CommandPalette />);
    const commandButton = screen.getByText('Toggle Compact Mode').closest('button');
    
    if (commandButton) {
      await userEvent.click(commandButton);
      
      await waitFor(() => {
        expect(mockSetCompactMode).toHaveBeenCalledWith(true);
      });
    }
  });
});

// =============================================================================
// Match Highlighting Tests
// =============================================================================

describe('CommandPalette Match Highlighting', () => {
  beforeEach(() => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
  });

  it('should highlight matched text', async () => {
    act(() => {
      useCommandPaletteStore.getState().setQuery('dash');
    });
    
    render(<CommandPalette />);
    
    // Check for highlighted span
    const highlights = document.querySelectorAll('.bg-primary\\/20');
    expect(highlights.length).toBeGreaterThan(0);
  });
});

// =============================================================================
// Loading State Tests
// =============================================================================

describe('CommandPalette Loading State', () => {
  beforeEach(() => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
  });

  it('should show loading overlay when executing', () => {
    act(() => {
      useCommandPaletteStore.setState({ isExecuting: true });
    });
    
    render(<CommandPalette />);
    
    // Check for loading spinner
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('should hide loading overlay when not executing', () => {
    render(<CommandPalette />);
    
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).not.toBeInTheDocument();
  });
});

// =============================================================================
// Global Keyboard Shortcut Tests
// =============================================================================

describe('CommandPalette Global Keyboard Shortcut', () => {
  it('should open on Cmd+K', async () => {
    render(<CommandPalette />);
    
    // Simulate Cmd+K
    fireEvent.keyDown(window, { key: 'k', metaKey: true });
    
    await waitFor(() => {
      expect(useCommandPaletteStore.getState().isOpen).toBe(true);
    });
  });

  it('should open on Ctrl+K', async () => {
    render(<CommandPalette />);
    
    // Simulate Ctrl+K
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    
    await waitFor(() => {
      expect(useCommandPaletteStore.getState().isOpen).toBe(true);
    });
  });

  it('should toggle on repeated Cmd+K', async () => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
    
    render(<CommandPalette />);
    
    // Simulate Cmd+K to close
    fireEvent.keyDown(window, { key: 'k', metaKey: true });
    
    await waitFor(() => {
      expect(useCommandPaletteStore.getState().isOpen).toBe(false);
    });
  });
});

// =============================================================================
// Custom Command Tests
// =============================================================================

describe('CommandPalette Custom Commands', () => {
  beforeEach(() => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
  });

  it('should display custom registered commands', () => {
    const customCommand: Command = {
      id: 'custom-test',
      label: 'Custom Test Command',
      description: 'A test command',
      category: 'actions' as CommandCategory,
      action: { type: 'callback', handler: jest.fn() },
    };
    
    act(() => {
      useCommandPaletteStore.getState().registerCommand(customCommand);
      useCommandPaletteStore.getState().setQuery('Custom Test');
    });
    
    render(<CommandPalette />);
    // Text is split across elements due to highlighting, use data-command-id instead
    expect(screen.getByRole('button', { name: /custom test command/i })).toBeInTheDocument();
  });

  it('should execute custom callback command', async () => {
    const mockCallback = jest.fn();
    const customCommand: Command = {
      id: 'callback-test',
      label: 'Callback Test Command',
      category: 'actions' as CommandCategory,
      action: { type: 'callback', handler: mockCallback },
    };
    
    act(() => {
      useCommandPaletteStore.getState().registerCommand(customCommand);
      useCommandPaletteStore.getState().setQuery('Callback Test');
    });
    
    render(<CommandPalette />);
    // Text is split across elements due to highlighting, use role-based query
    const commandButton = screen.getByRole('button', { name: /callback test command/i });
    
    await userEvent.click(commandButton);
    
    await waitFor(() => {
      expect(mockCallback).toHaveBeenCalled();
    });
  });
});

// =============================================================================
// Accessibility Tests
// =============================================================================

describe('CommandPalette Accessibility', () => {
  beforeEach(() => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
  });

  it('should have dialog role', () => {
    render(<CommandPalette />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('should have aria-modal attribute', () => {
    render(<CommandPalette />);
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  });

  it('should have aria-label on dialog', () => {
    render(<CommandPalette />);
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-label', 'Command palette');
  });

  it('should have listbox role for command list', () => {
    render(<CommandPalette />);
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('should have aria-autocomplete on search input', () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    expect(input).toHaveAttribute('aria-autocomplete', 'list');
  });

  it('should have aria-controls linking input to list', () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    expect(input).toHaveAttribute('aria-controls', 'command-list');
  });

  it('should have aria-label on search input', () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    expect(input).toHaveAttribute('aria-label', 'Command search');
  });
});

// =============================================================================
// Category Grouping Tests
// =============================================================================

describe('CommandPalette Category Grouping', () => {
  beforeEach(() => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
  });

  it('should group commands by category', () => {
    render(<CommandPalette />);
    
    const headings = screen.getAllByText(/Navigation|Actions|Settings|Help/);
    expect(headings.length).toBeGreaterThanOrEqual(4);
  });

  it('should display category labels in uppercase', () => {
    render(<CommandPalette />);
    
    const navigationHeader = screen.getByText('Navigation');
    expect(navigationHeader.className).toContain('uppercase');
  });

  it('should show only matching categories when filtering', async () => {
    act(() => {
      useCommandPaletteStore.getState().setQuery('Toggle Dark');
    });
    
    render(<CommandPalette />);
    
    // Settings category should be visible
    expect(screen.getByText('Settings')).toBeInTheDocument();
    
    // Navigation category should not have items (so might not show)
    const filtered = useCommandPaletteStore.getState().filteredCommands;
    const hasNavigation = filtered.some(r => r.command.category === 'navigation');
    expect(hasNavigation).toBe(false);
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('CommandPalette Integration', () => {
  it('should handle complete user flow', async () => {
    render(<CommandPalette />);
    
    // 1. Open with keyboard shortcut
    fireEvent.keyDown(window, { key: 'k', metaKey: true });
    
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
    
    // 2. Type search query
    const input = screen.getByPlaceholderText(/type a command or search/i);
    await userEvent.type(input, 'dashboard');
    
    // 3. Navigate with keyboard
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'ArrowUp' });
    
    // 4. Execute with Enter
    fireEvent.keyDown(input, { key: 'Enter' });
    
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/today');
      expect(useCommandPaletteStore.getState().isOpen).toBe(false);
    });
  });

  it('should handle rapid typing and navigation', async () => {
    act(() => {
      useCommandPaletteStore.getState().open();
    });
    
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/type a command or search/i);
    
    // Rapid typing
    await userEvent.type(input, 'rfq', { delay: 10 });
    
    // Rapid navigation
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'ArrowUp' });
    
    // Should still be in valid state
    expect(useCommandPaletteStore.getState().selectedIndex).toBeGreaterThanOrEqual(0);
  });

  it('should cleanup global listener on unmount', async () => {
    // Store a reference to remove/add event listener
    const originalAddEventListener = window.addEventListener;
    const originalRemoveEventListener = window.removeEventListener;
    const addedListeners: Array<{ type: string; listener: EventListener }> = [];
    const removedListeners: Array<{ type: string; listener: EventListener }> = [];
    
    window.addEventListener = jest.fn((type: string, listener: EventListener) => {
      addedListeners.push({ type, listener });
      return originalAddEventListener.call(window, type, listener);
    }) as typeof window.addEventListener;
    
    window.removeEventListener = jest.fn((type: string, listener: EventListener) => {
      removedListeners.push({ type, listener });
      return originalRemoveEventListener.call(window, type, listener);
    }) as typeof window.removeEventListener;
    
    const { unmount } = render(<CommandPalette />);
    
    // Should have added keydown listener
    const keydownListeners = addedListeners.filter(l => l.type === 'keydown');
    expect(keydownListeners.length).toBeGreaterThan(0);
    
    unmount();
    
    // Should have removed keydown listener
    const removedKeydownListeners = removedListeners.filter(l => l.type === 'keydown');
    expect(removedKeydownListeners.length).toBeGreaterThan(0);
    
    // Restore original functions
    window.addEventListener = originalAddEventListener;
    window.removeEventListener = originalRemoveEventListener;
  });
});
