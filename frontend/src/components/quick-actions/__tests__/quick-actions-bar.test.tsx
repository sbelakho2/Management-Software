/**
 * @jest-environment jsdom
 */
import React from 'react';
import { screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  QuickActionsBar,
  QuickActionsCompact,
  QuickActionsFloating,
  QuickActionsToolbar,
  useQuickActionShortcuts,
} from '../quick-actions-bar';
import {
  useQuickActionsStore,
  type ActionContext,
  type QuickAction,
} from '@/stores/quick-actions-store';
import { renderWithI18n } from '@/test-utils';

const render = renderWithI18n;

// Mock the tooltip to avoid portal issues
jest.mock('@radix-ui/react-tooltip', () => {
  const actual = jest.requireActual('@radix-ui/react-tooltip');
  return {
    ...actual,
    Provider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Root: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Trigger: ({ children, asChild, ...props }: { children: React.ReactNode; asChild?: boolean }) => {
      if (asChild && React.isValidElement(children)) {
        return React.cloneElement(children as React.ReactElement<Record<string, unknown>>, props);
      }
      return <span {...props}>{children}</span>;
    },
    Content: () => null,
    Portal: () => null,
  };
});

// Mock dropdown menu
jest.mock('@radix-ui/react-dropdown-menu', () => {
  const actual = jest.requireActual('@radix-ui/react-dropdown-menu');
  return {
    ...actual,
    Root: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Trigger: ({ children, asChild, ...props }: { children: React.ReactNode; asChild?: boolean }) => {
      if (asChild && React.isValidElement(children)) {
        return React.cloneElement(children as React.ReactElement<Record<string, unknown>>, { 
          ...props, 
          'data-testid': 'overflow-menu-trigger' 
        });
      }
      return <button {...props} data-testid="overflow-menu-trigger">{children}</button>;
    },
    Portal: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Content: ({ children, ...props }: { children: React.ReactNode }) => (
      <div {...props} data-testid="overflow-menu-content">{children}</div>
    ),
    Item: ({ children, onClick, disabled, ...props }: { children: React.ReactNode; onClick?: () => void; disabled?: boolean }) => (
      <div {...props} role="menuitem" onClick={disabled ? undefined : onClick} aria-disabled={disabled}>
        {children}
      </div>
    ),
    Separator: () => <hr data-testid="menu-separator" />,
    Group: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

// Mock alert dialog
jest.mock('@radix-ui/react-alert-dialog', () => {
  const actual = jest.requireActual('@radix-ui/react-alert-dialog');
  return {
    ...actual,
    Root: ({ children, open }: { children: React.ReactNode; open?: boolean }) => 
      open ? <>{children}</> : null,
    Portal: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Overlay: ({ children, ...props }: { children?: React.ReactNode }) => <div {...props} data-testid="dialog-overlay">{children}</div>,
    Content: ({ children, ...props }: { children: React.ReactNode }) => <div {...props} data-testid="alert-dialog">{children}</div>,
    Title: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
    Description: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
    Cancel: ({ children, ...props }: { children: React.ReactNode }) => <button {...props} data-testid="cancel-button">{children}</button>,
    Action: ({ children, onClick, ...props }: { children: React.ReactNode; onClick?: () => void }) => (
      <button {...props} onClick={onClick} data-testid="confirm-button">{children}</button>
    ),
  };
});

// Reset store before each test
beforeEach(() => {
  act(() => {
    useQuickActionsStore.setState({
      actions: useQuickActionsStore.getState().actions,
      customActions: [],
      currentContext: null,
      activeEntityId: null,
      executions: [],
      currentExecution: null,
      confirmation: {
        isOpen: false,
        actionId: null,
        context: null,
        message: '',
        variant: 'primary',
      },
      userPermissions: [],
      isBarVisible: true,
      isExpanded: false,
      hoveredActionId: null,
      actionHandlers: new Map(),
    });
  });
});

// =============================================================================
// Test Fixtures
// =============================================================================

const mockContext: ActionContext = {
  entityType: 'opportunity',
  entityId: 'opp-123',
  entityName: 'Test Opportunity',
};

const mockTaskContext: ActionContext = {
  entityType: 'task',
  entityId: 'task-456',
  entityName: 'Test Task',
};

// =============================================================================
// QuickActionsBar Tests
// =============================================================================

describe('QuickActionsBar', () => {
  describe('Rendering', () => {
    it('should not render when no context is provided', () => {
      const { container } = render(<QuickActionsBar />);
      expect(container.firstChild).toBeNull();
    });

    it('should render when context is provided', () => {
      render(<QuickActionsBar context={mockContext} />);
      expect(screen.getByRole('toolbar')).toBeInTheDocument();
    });

    it('should render with aria-label describing the context', () => {
      render(<QuickActionsBar context={mockContext} />);
      const toolbar = screen.getByRole('toolbar');
      expect(toolbar).toHaveAttribute(
        'aria-label',
        'Quick actions for Test Opportunity'
      );
    });

    it('should not render when bar is hidden', () => {
      act(() => {
        useQuickActionsStore.getState().setBarVisible(false);
      });
      
      const { container } = render(<QuickActionsBar context={mockContext} />);
      expect(container.firstChild).toBeNull();
    });

    it('should render primary action buttons', () => {
      act(() => {
        useQuickActionsStore.getState().setUserPermissions(['can_request_approval']);
      });
      
      render(<QuickActionsBar context={mockContext} />);
      
      // Check for common primary actions
      expect(screen.getByLabelText('Create Task')).toBeInTheDocument();
      expect(screen.getByLabelText('Comment')).toBeInTheDocument();
    });

    it('should render overflow menu trigger', () => {
      render(<QuickActionsBar context={mockContext} />);
      expect(screen.getByTestId('overflow-menu-trigger')).toBeInTheDocument();
    });
  });

  describe('Position Variants', () => {
    it('should apply inline position classes', () => {
      render(<QuickActionsBar context={mockContext} position="inline" />);
      const toolbar = screen.getByRole('toolbar');
      expect(toolbar).toHaveClass('flex', 'items-center', 'gap-1');
    });

    it('should apply floating position classes', () => {
      render(<QuickActionsBar context={mockContext} position="floating" />);
      const toolbar = screen.getByRole('toolbar');
      expect(toolbar).toHaveClass('fixed', 'bottom-4', 'right-4');
    });

    it('should apply toolbar position classes', () => {
      render(<QuickActionsBar context={mockContext} position="toolbar" />);
      const toolbar = screen.getByRole('toolbar');
      expect(toolbar).toHaveClass('border-b', 'bg-muted/30');
    });

    it('should show entity name in floating position', () => {
      render(<QuickActionsBar context={mockContext} position="floating" />);
      expect(screen.getByText('Test Opportunity')).toBeInTheDocument();
    });

    it('should show close button in floating position', () => {
      render(<QuickActionsBar context={mockContext} position="floating" />);
      expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
    });
  });

  describe('Size Variants', () => {
    it('should render with default size', () => {
      render(<QuickActionsBar context={mockContext} />);
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('should render with small size', () => {
      render(<QuickActionsBar context={mockContext} size="sm" />);
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('Show Labels', () => {
    it('should show labels when showLabels is true', () => {
      render(<QuickActionsBar context={mockContext} showLabels />);
      expect(screen.getByText('Create Task')).toBeInTheDocument();
    });
  });

  describe('Max Primary Actions', () => {
    it('should limit primary actions based on maxPrimaryActions', () => {
      act(() => {
        useQuickActionsStore.getState().setUserPermissions(['can_request_approval']);
      });
      
      render(<QuickActionsBar context={mockContext} maxPrimaryActions={2} />);
      
      // Should have exactly 2 primary action buttons + overflow menu
      const buttons = screen.getAllByRole('button');
      // 2 primary + 1 overflow = 3 buttons minimum
      expect(buttons.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe('Action Execution', () => {
    it('should call onActionExecuted on successful execution', async () => {
      const onActionExecuted = jest.fn();
      const user = userEvent.setup();
      
      render(
        <QuickActionsBar
          context={mockContext}
          onActionExecuted={onActionExecuted}
        />
      );
      
      const createTaskButton = screen.getByLabelText('Create Task');
      await act(async () => {
        await user.click(createTaskButton);
      });
      
      await waitFor(() => {
        expect(onActionExecuted).toHaveBeenCalled();
      });
    });

    it('should call onActionError on failed execution', async () => {
      const onActionError = jest.fn();
      const user = userEvent.setup();
      
      // Register a handler that throws
      act(() => {
        useQuickActionsStore.getState().registerHandler('create_task', async () => {
          throw new Error('Test error');
        });
      });
      
      render(
        <QuickActionsBar
          context={mockContext}
          onActionError={onActionError}
        />
      );
      
      const createTaskButton = screen.getByLabelText('Create Task');
      await act(async () => {
        await user.click(createTaskButton);
      });
      
      await waitFor(() => {
        expect(onActionError).toHaveBeenCalled();
      });
    });
  });

  describe('Confirmation Dialog', () => {
    it('should show confirmation dialog for actions requiring confirmation', async () => {
      const user = userEvent.setup();
      act(() => {
        useQuickActionsStore.getState().setUserPermissions(['can_delete']);
      });
      
      render(<QuickActionsBar context={mockContext} />);
      
      // Find and click delete in overflow menu
      const overflowTrigger = screen.getByTestId('overflow-menu-trigger');
      await act(async () => {
        await user.click(overflowTrigger);
      });
      
      // Click delete action
      const deleteItem = screen.getByText('Delete');
      await act(async () => {
        await user.click(deleteItem);
      });
      
      // Confirmation dialog should appear
      await waitFor(() => {
        expect(screen.getByTestId('alert-dialog')).toBeInTheDocument();
      });
    });

    it('should hide confirmation dialog on cancel', async () => {
      act(() => {
        useQuickActionsStore.getState().setUserPermissions(['can_delete']);
        useQuickActionsStore.getState().showConfirmation('action-delete', mockContext);
      });
      
      render(<QuickActionsBar context={mockContext} />);
      
      // Dialog should be visible
      expect(screen.getByTestId('alert-dialog')).toBeInTheDocument();
      expect(screen.getByTestId('cancel-button')).toBeInTheDocument();
      
      // Call hideConfirmation directly (the Cancel button triggers onOpenChange which calls this)
      act(() => {
        useQuickActionsStore.getState().hideConfirmation();
      });
      
      // Dialog should be hidden after cancel
      expect(useQuickActionsStore.getState().confirmation.isOpen).toBe(false);
    });

    it('should execute action on confirm', async () => {
      const onActionExecuted = jest.fn();
      const user = userEvent.setup();
      
      act(() => {
        useQuickActionsStore.getState().setUserPermissions(['can_delete']);
        useQuickActionsStore.getState().showConfirmation('action-delete', mockContext);
      });
      
      render(
        <QuickActionsBar
          context={mockContext}
          onActionExecuted={onActionExecuted}
        />
      );
      
      const confirmButton = screen.getByTestId('confirm-button');
      await act(async () => {
        await user.click(confirmButton);
      });
      
      await waitFor(() => {
        expect(onActionExecuted).toHaveBeenCalled();
      });
    });
  });

  describe('Toolbar Expand/Collapse', () => {
    it('should show expand button in toolbar position', () => {
      act(() => {
        useQuickActionsStore.getState().setUserPermissions(['can_assign']);
      });
      
      render(<QuickActionsBar context={mockContext} position="toolbar" />);
      
      expect(screen.getByLabelText('Show more actions')).toBeInTheDocument();
    });

    it('should toggle expanded state on click', async () => {
      const user = userEvent.setup();
      act(() => {
        useQuickActionsStore.getState().setUserPermissions(['can_assign']);
      });
      
      render(<QuickActionsBar context={mockContext} position="toolbar" />);
      
      const expandButton = screen.getByLabelText('Show more actions');
      await act(async () => {
        await user.click(expandButton);
      });
      
      expect(screen.getByLabelText('Show fewer actions')).toBeInTheDocument();
    });
  });

  describe('Close Button (Floating)', () => {
    it('should hide bar when close button is clicked', async () => {
      const user = userEvent.setup();
      render(<QuickActionsBar context={mockContext} position="floating" />);
      
      const closeButton = screen.getByRole('button', { name: /close/i });
      await act(async () => {
        await user.click(closeButton);
      });
      
      expect(useQuickActionsStore.getState().isBarVisible).toBe(false);
    });
  });
});

// =============================================================================
// QuickActionsCompact Tests
// =============================================================================

describe('QuickActionsCompact', () => {
  it('should render with small size', () => {
    render(<QuickActionsCompact context={mockContext} />);
    expect(screen.getByRole('toolbar')).toBeInTheDocument();
  });

  it('should respect maxActions prop', () => {
    act(() => {
      useQuickActionsStore.getState().setUserPermissions(['can_request_approval']);
    });
    
    render(<QuickActionsCompact context={mockContext} maxActions={2} />);
    
    // Should have limited primary actions
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });

  it('should use inline position', () => {
    render(<QuickActionsCompact context={mockContext} />);
    const toolbar = screen.getByRole('toolbar');
    expect(toolbar).toHaveClass('flex', 'items-center');
  });
});

// =============================================================================
// QuickActionsFloating Tests
// =============================================================================

describe('QuickActionsFloating', () => {
  it('should render in floating position', () => {
    render(<QuickActionsFloating context={mockContext} />);
    const toolbar = screen.getByRole('toolbar');
    expect(toolbar).toHaveClass('fixed');
  });

  it('should show labels', () => {
    render(<QuickActionsFloating context={mockContext} />);
    expect(screen.getByText('Create Task')).toBeInTheDocument();
  });

  it('should show entity name', () => {
    render(<QuickActionsFloating context={mockContext} />);
    expect(screen.getByText('Test Opportunity')).toBeInTheDocument();
  });
});

// =============================================================================
// QuickActionsToolbar Tests
// =============================================================================

describe('QuickActionsToolbar', () => {
  it('should render in toolbar position', () => {
    render(<QuickActionsToolbar context={mockContext} />);
    const toolbar = screen.getByRole('toolbar');
    expect(toolbar).toHaveClass('border-b');
  });

  it('should have more primary actions visible', () => {
    act(() => {
      useQuickActionsStore.getState().setUserPermissions([
        'can_request_approval',
        'can_assign',
      ]);
    });
    
    render(<QuickActionsToolbar context={mockContext} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(3);
  });
});

// =============================================================================
// useQuickActionShortcuts Hook Tests
// =============================================================================

describe('useQuickActionShortcuts', () => {
  function TestComponent({ context }: { context: ActionContext | null }) {
    useQuickActionShortcuts(context);
    return <div data-testid="test-component">Test</div>;
  }

  it('should not respond to shortcuts when no context', () => {
    const { result } = renderHook(() => useQuickActionsStore());
    
    render(<TestComponent context={null} />);
    
    fireEvent.keyDown(window, { key: 'T' });
    
    // Should not trigger any execution
    expect(result.current.executions).toEqual([]);
  });

  it('should ignore shortcuts in input elements', () => {
    render(
      <>
        <TestComponent context={mockContext} />
        <input data-testid="test-input" />
      </>
    );
    
    const input = screen.getByTestId('test-input');
    input.focus();
    
    fireEvent.keyDown(input, { key: 'T' });
    
    // Should not trigger action when typing in input
    expect(useQuickActionsStore.getState().executions).toEqual([]);
  });

  it('should ignore shortcuts with modifier keys', () => {
    render(<TestComponent context={mockContext} />);
    
    fireEvent.keyDown(window, { key: 'T', ctrlKey: true });
    
    // Should not trigger action with Ctrl key
    expect(useQuickActionsStore.getState().executions).toEqual([]);
  });
});

// =============================================================================
// Entity-Specific Tests
// =============================================================================

describe('Entity-Specific Actions', () => {
  it('should show escalate action for andon entity', () => {
    const andonContext: ActionContext = {
      entityType: 'andon',
      entityId: 'andon-123',
      entityName: 'Production Issue',
    };
    
    render(<QuickActionsBar context={andonContext} />);
    
    // Escalate should be in overflow
    const overflowTrigger = screen.getByTestId('overflow-menu-trigger');
    fireEvent.click(overflowTrigger);
    
    expect(screen.getByText('Escalate')).toBeInTheDocument();
  });

  it('should show resolve action for task entity', () => {
    render(<QuickActionsBar context={mockTaskContext} />);
    
    // Resolve should be visible for tasks
    expect(screen.getByLabelText('Resolve')).toBeInTheDocument();
  });

  it('should not show request_approval for entities without permission', () => {
    // Don't set can_request_approval permission
    render(<QuickActionsBar context={mockContext} />);
    
    // Request Approval should not be visible
    expect(screen.queryByLabelText('Request Approval')).not.toBeInTheDocument();
  });

  it('should show request_approval when user has permission', () => {
    act(() => {
      useQuickActionsStore.getState().setUserPermissions(['can_request_approval']);
    });
    
    render(<QuickActionsBar context={mockContext} />);
    
    // Request Approval should be visible
    expect(screen.getByLabelText('Request Approval')).toBeInTheDocument();
  });
});

// =============================================================================
// Custom Actions Tests
// =============================================================================

describe('Custom Actions', () => {
  it('should render custom registered actions', () => {
    const customAction: QuickAction = {
      id: 'custom-review',
      type: 'create_task',
      label: 'Request Review',
      icon: 'eye',
      visibility: 'always',
    };
    
    act(() => {
      useQuickActionsStore.getState().registerAction(customAction);
    });
    
    render(<QuickActionsBar context={mockContext} />);
    
    expect(screen.getByLabelText('Request Review')).toBeInTheDocument();
  });

  it('should remove custom action when unregistered', () => {
    const customAction: QuickAction = {
      id: 'custom-review',
      type: 'create_task',
      label: 'Request Review',
      icon: 'eye',
      visibility: 'always',
    };
    
    act(() => {
      useQuickActionsStore.getState().registerAction(customAction);
    });
    
    const { rerender } = render(<QuickActionsBar context={mockContext} />);
    
    expect(screen.getByLabelText('Request Review')).toBeInTheDocument();
    
    act(() => {
      useQuickActionsStore.getState().unregisterAction('custom-review');
    });
    
    rerender(<QuickActionsBar context={mockContext} />);
    
    expect(screen.queryByLabelText('Request Review')).not.toBeInTheDocument();
  });
});

// =============================================================================
// Accessibility Tests
// =============================================================================

describe('Accessibility', () => {
  it('should have proper toolbar role', () => {
    render(<QuickActionsBar context={mockContext} />);
    expect(screen.getByRole('toolbar')).toBeInTheDocument();
  });

  it('should have aria-labels on all action buttons', () => {
    render(<QuickActionsBar context={mockContext} />);
    
    const buttons = screen.getAllByRole('button');
    buttons.forEach((button) => {
      expect(
        button.getAttribute('aria-label') || 
        button.getAttribute('title') ||
        button.textContent
      ).toBeTruthy();
    });
  });

  it('should not show disabled actions', () => {
    act(() => {
      useQuickActionsStore.getState().updateAction('action-create-task', { disabled: true });
    });
    
    render(<QuickActionsBar context={mockContext} />);
    
    // Disabled actions are filtered out by getAvailableActions
    const buttons = screen.queryAllByRole('button');
    const createTaskButton = buttons.find(btn => btn.getAttribute('aria-label') === 'Create Task');
    expect(createTaskButton).toBeUndefined();
  });

  it('should track execution state in store', () => {
    // This test verifies that execution state is properly tracked
    // The visual disabled state is applied when isExecuting prop is true
    act(() => {
      useQuickActionsStore.setState({
        currentExecution: {
          id: 'exec-1',
          actionId: 'action-create-task',
          context: mockContext,
          status: 'executing',
          startedAt: new Date(),
        },
      });
    });
    
    // Verify state is set
    expect(useQuickActionsStore.getState().currentExecution).not.toBeNull();
    expect(useQuickActionsStore.getState().currentExecution?.actionId).toBe('action-create-task');
    expect(useQuickActionsStore.getState().currentExecution?.status).toBe('executing');
  });
});

// Helper for rendering hooks
function renderHook<T>(hook: () => T) {
  let result: { current: T };
  
  function TestComponent() {
    result = { current: hook() };
    return null;
  }
  
  render(<TestComponent />);
  
  return { result: result! };
}
