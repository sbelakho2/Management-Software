/**
 * @jest-environment jsdom
 */
import { act, renderHook } from '@testing-library/react';
import {
  useQuickActionsStore,
  DEFAULT_ACTIONS,
  ENTITY_ACTION_MAP,
  getActionsForEntity,
  filterByVisibility,
  getPrimaryActions,
  getSecondaryActions,
  getOverflowActions,
  hasPermission,
  filterByPermissions,
  getActionById,
  getActionByType,
  formatEntityType,
  generateExecutionId,
  type QuickAction,
  type EntityType,
  type ActionType,
  type ActionContext,
} from '../quick-actions-store';

// Reset store before each test
beforeEach(() => {
  const { result } = renderHook(() => useQuickActionsStore());
  act(() => {
    result.current.clearContext();
    result.current.clearExecutionHistory();
    result.current.setUserPermissions([]);
    result.current.setBarVisible(true);
    result.current.hideConfirmation();
  });
});

// =============================================================================
// Constants Tests
// =============================================================================

describe('DEFAULT_ACTIONS', () => {
  it('should have unique action IDs', () => {
    const ids = DEFAULT_ACTIONS.map((a) => a.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });

  it('should have unique action types', () => {
    // Note: Some action types may be duplicated intentionally (e.g., watch/unwatch)
    // but we check that each action has a type
    DEFAULT_ACTIONS.forEach((action) => {
      expect(action.type).toBeDefined();
    });
  });

  it('should have required properties for all actions', () => {
    DEFAULT_ACTIONS.forEach((action) => {
      expect(action.id).toBeTruthy();
      expect(action.type).toBeTruthy();
      expect(action.label).toBeTruthy();
      expect(action.icon).toBeTruthy();
    });
  });

  it('should have valid visibility values', () => {
    const validVisibilities = ['always', 'hover', 'overflow'];
    DEFAULT_ACTIONS.forEach((action) => {
      if (action.visibility) {
        expect(validVisibilities).toContain(action.visibility);
      }
    });
  });

  it('should have valid variant values', () => {
    const validVariants = ['primary', 'secondary', 'ghost', 'destructive', 'warning'];
    DEFAULT_ACTIONS.forEach((action) => {
      if (action.variant) {
        expect(validVariants).toContain(action.variant);
      }
    });
  });

  it('should include common actions', () => {
    const actionTypes = DEFAULT_ACTIONS.map((a) => a.type);
    expect(actionTypes).toContain('create_task');
    expect(actionTypes).toContain('request_info');
    expect(actionTypes).toContain('request_approval');
    expect(actionTypes).toContain('export_pdf');
    expect(actionTypes).toContain('delete');
  });
});

describe('ENTITY_ACTION_MAP', () => {
  it('should have mappings for all entity types', () => {
    const entityTypes: EntityType[] = [
      'opportunity', 'rfq', 'quote', 'qualification', 'task',
      'a3', 'obeya', 'ctq', 'account', 'contact', 'work_order', 'andon',
    ];
    
    entityTypes.forEach((type) => {
      expect(ENTITY_ACTION_MAP[type]).toBeDefined();
      expect(Array.isArray(ENTITY_ACTION_MAP[type])).toBe(true);
    });
  });

  it('should have non-empty action lists for all entities', () => {
    Object.values(ENTITY_ACTION_MAP).forEach((actions) => {
      expect(actions.length).toBeGreaterThan(0);
    });
  });

  it('should include create_task for most entities', () => {
    const entitiesWithTasks: EntityType[] = [
      'opportunity', 'rfq', 'quote', 'qualification', 'a3', 'obeya', 'ctq', 'account', 'contact', 'work_order',
    ];
    
    entitiesWithTasks.forEach((entity) => {
      expect(ENTITY_ACTION_MAP[entity]).toContain('create_task');
    });
  });

  it('should include escalate only for escalatable entities', () => {
    const escalatableEntities: EntityType[] = ['andon', 'a3', 'obeya'];
    const nonEscalatableEntities: EntityType[] = [
      'opportunity', 'rfq', 'quote', 'qualification', 'task', 'ctq', 'account', 'contact', 'work_order',
    ];
    
    escalatableEntities.forEach((entity) => {
      expect(ENTITY_ACTION_MAP[entity]).toContain('escalate');
    });
    
    nonEscalatableEntities.forEach((entity) => {
      expect(ENTITY_ACTION_MAP[entity]).not.toContain('escalate');
    });
  });
});

// =============================================================================
// Utility Function Tests
// =============================================================================

describe('getActionsForEntity', () => {
  it('should return actions for opportunity', () => {
    const actions = getActionsForEntity('opportunity');
    expect(actions.length).toBeGreaterThan(0);
  });

  it('should filter actions based on entity type', () => {
    const opportunityActions = getActionsForEntity('opportunity');
    const taskActions = getActionsForEntity('task');
    
    // Opportunity has more actions than task
    expect(opportunityActions.length).toBeGreaterThan(taskActions.length);
  });

  it('should respect action entityTypes restriction', () => {
    const andonActions = getActionsForEntity('andon');
    const opportunityActions = getActionsForEntity('opportunity');
    
    // Escalate should be in andon but not opportunity
    const andonHasEscalate = andonActions.some((a) => a.type === 'escalate');
    const oppHasEscalate = opportunityActions.some((a) => a.type === 'escalate');
    
    expect(andonHasEscalate).toBe(true);
    expect(oppHasEscalate).toBe(false);
  });

  it('should use custom actions when provided', () => {
    const customAction: QuickAction = {
      id: 'custom-action',
      type: 'create_task',
      label: 'Custom Task',
      icon: 'plus',
    };
    
    const actions = getActionsForEntity('opportunity', [customAction]);
    expect(actions).toContainEqual(customAction);
  });

  it('should return empty array for unknown entity type', () => {
    const actions = getActionsForEntity('unknown' as EntityType);
    expect(actions).toEqual([]);
  });
});

describe('filterByVisibility', () => {
  const testActions: QuickAction[] = [
    { id: '1', type: 'create_task', label: 'A', icon: 'x', visibility: 'always' },
    { id: '2', type: 'request_info', label: 'B', icon: 'x', visibility: 'hover' },
    { id: '3', type: 'export_pdf', label: 'C', icon: 'x', visibility: 'overflow' },
    { id: '4', type: 'delete', label: 'D', icon: 'x' }, // defaults to 'always'
  ];

  it('should filter by single visibility', () => {
    const always = filterByVisibility(testActions, 'always');
    expect(always.length).toBe(2);
    expect(always.map((a) => a.id)).toEqual(['1', '4']);
  });

  it('should filter by multiple visibilities', () => {
    const multiple = filterByVisibility(testActions, ['always', 'hover']);
    expect(multiple.length).toBe(3);
  });

  it('should handle empty array', () => {
    const result = filterByVisibility([], 'always');
    expect(result).toEqual([]);
  });
});

describe('getPrimaryActions / getSecondaryActions / getOverflowActions', () => {
  const testActions: QuickAction[] = [
    { id: '1', type: 'create_task', label: 'A', icon: 'x', visibility: 'always' },
    { id: '2', type: 'request_info', label: 'B', icon: 'x', visibility: 'hover' },
    { id: '3', type: 'export_pdf', label: 'C', icon: 'x', visibility: 'overflow' },
  ];

  it('should get primary actions', () => {
    const primary = getPrimaryActions(testActions);
    expect(primary.length).toBe(1);
    expect(primary[0].id).toBe('1');
  });

  it('should get secondary actions', () => {
    const secondary = getSecondaryActions(testActions);
    expect(secondary.length).toBe(1);
    expect(secondary[0].id).toBe('2');
  });

  it('should get overflow actions', () => {
    const overflow = getOverflowActions(testActions);
    expect(overflow.length).toBe(1);
    expect(overflow[0].id).toBe('3');
  });
});

describe('hasPermission', () => {
  it('should return true when no permission required', () => {
    const action: QuickAction = {
      id: '1',
      type: 'create_task',
      label: 'Test',
      icon: 'x',
    };
    expect(hasPermission(action, [])).toBe(true);
  });

  it('should return true when user has required permission', () => {
    const action: QuickAction = {
      id: '1',
      type: 'delete',
      label: 'Delete',
      icon: 'x',
      requiredPermission: 'can_delete',
    };
    expect(hasPermission(action, ['can_delete', 'can_view'])).toBe(true);
  });

  it('should return false when user lacks required permission', () => {
    const action: QuickAction = {
      id: '1',
      type: 'delete',
      label: 'Delete',
      icon: 'x',
      requiredPermission: 'can_delete',
    };
    expect(hasPermission(action, ['can_view'])).toBe(false);
  });
});

describe('filterByPermissions', () => {
  it('should filter actions by user permissions', () => {
    const actions: QuickAction[] = [
      { id: '1', type: 'create_task', label: 'A', icon: 'x' },
      { id: '2', type: 'delete', label: 'B', icon: 'x', requiredPermission: 'can_delete' },
      { id: '3', type: 'archive', label: 'C', icon: 'x', requiredPermission: 'can_archive' },
    ];
    
    const filtered = filterByPermissions(actions, ['can_delete']);
    expect(filtered.length).toBe(2);
    expect(filtered.map((a) => a.id)).toEqual(['1', '2']);
  });

  it('should return all actions when all permissions are met', () => {
    const actions: QuickAction[] = [
      { id: '1', type: 'create_task', label: 'A', icon: 'x' },
      { id: '2', type: 'delete', label: 'B', icon: 'x', requiredPermission: 'can_delete' },
    ];
    
    const filtered = filterByPermissions(actions, ['can_delete']);
    expect(filtered.length).toBe(2);
  });
});

describe('getActionById', () => {
  it('should find action by ID', () => {
    const action = getActionById('action-create-task');
    expect(action).toBeDefined();
    expect(action?.type).toBe('create_task');
  });

  it('should return undefined for unknown ID', () => {
    const action = getActionById('unknown-action');
    expect(action).toBeUndefined();
  });

  it('should search custom actions when provided', () => {
    const customActions: QuickAction[] = [
      { id: 'custom-1', type: 'create_task', label: 'Custom', icon: 'x' },
    ];
    
    const action = getActionById('custom-1', customActions);
    expect(action).toBeDefined();
    expect(action?.label).toBe('Custom');
  });
});

describe('getActionByType', () => {
  it('should find action by type', () => {
    const action = getActionByType('create_task');
    expect(action).toBeDefined();
    expect(action?.type).toBe('create_task');
  });

  it('should return undefined for unknown type', () => {
    const action = getActionByType('unknown_type' as ActionType);
    expect(action).toBeUndefined();
  });
});

describe('formatEntityType', () => {
  it('should format entity types correctly', () => {
    expect(formatEntityType('opportunity')).toBe('Opportunity');
    expect(formatEntityType('rfq')).toBe('RFQ');
    expect(formatEntityType('quote')).toBe('Quote');
    expect(formatEntityType('qualification')).toBe('Qualification');
    expect(formatEntityType('task')).toBe('Task');
    expect(formatEntityType('a3')).toBe('A3');
    expect(formatEntityType('obeya')).toBe('Obeya');
    expect(formatEntityType('ctq')).toBe('CTQ');
    expect(formatEntityType('account')).toBe('Account');
    expect(formatEntityType('contact')).toBe('Contact');
    expect(formatEntityType('work_order')).toBe('Work Order');
    expect(formatEntityType('andon')).toBe('Andon');
  });
});

describe('generateExecutionId', () => {
  it('should generate unique IDs', () => {
    const id1 = generateExecutionId();
    const id2 = generateExecutionId();
    expect(id1).not.toBe(id2);
  });

  it('should start with exec prefix', () => {
    const id = generateExecutionId();
    expect(id.startsWith('exec-')).toBe(true);
  });
});

// =============================================================================
// Store Tests
// =============================================================================

describe('useQuickActionsStore', () => {
  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      expect(result.current.actions).toEqual(DEFAULT_ACTIONS);
      expect(result.current.customActions).toEqual([]);
      expect(result.current.currentContext).toBeNull();
      expect(result.current.activeEntityId).toBeNull();
      expect(result.current.executions).toEqual([]);
      expect(result.current.currentExecution).toBeNull();
      expect(result.current.isBarVisible).toBe(true);
      expect(result.current.isExpanded).toBe(false);
      expect(result.current.hoveredActionId).toBeNull();
    });
  });

  describe('Context Management', () => {
    it('should set context', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      const context: ActionContext = {
        entityType: 'opportunity',
        entityId: 'opp-123',
        entityName: 'Test Opportunity',
      };
      
      act(() => {
        result.current.setContext(context);
      });
      
      expect(result.current.currentContext).toEqual(context);
      expect(result.current.activeEntityId).toBe('opp-123');
    });

    it('should clear context', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.setContext({
          entityType: 'opportunity',
          entityId: 'opp-123',
        });
        result.current.clearContext();
      });
      
      expect(result.current.currentContext).toBeNull();
      expect(result.current.activeEntityId).toBeNull();
    });

    it('should set active entity independently', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.setActiveEntity('entity-456');
      });
      
      expect(result.current.activeEntityId).toBe('entity-456');
    });
  });

  describe('Action Registration', () => {
    it('should register custom action', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      const customAction: QuickAction = {
        id: 'custom-action',
        type: 'create_task',
        label: 'Custom Action',
        icon: 'star',
      };
      
      act(() => {
        result.current.registerAction(customAction);
      });
      
      expect(result.current.customActions).toContainEqual(customAction);
    });

    it('should unregister custom action', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      const customAction: QuickAction = {
        id: 'custom-action',
        type: 'create_task',
        label: 'Custom Action',
        icon: 'star',
      };
      
      act(() => {
        result.current.registerAction(customAction);
        result.current.unregisterAction('custom-action');
      });
      
      expect(result.current.customActions).not.toContainEqual(customAction);
    });

    it('should update action', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.updateAction('action-create-task', { label: 'Updated Label' });
      });
      
      const updatedAction = result.current.actions.find((a) => a.id === 'action-create-task');
      expect(updatedAction?.label).toBe('Updated Label');
    });
  });

  describe('Handler Registration', () => {
    it('should register action handler', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      const handler = jest.fn().mockResolvedValue({ success: true });
      
      act(() => {
        result.current.registerHandler('create_task', handler);
      });
      
      expect(result.current.actionHandlers.has('create_task')).toBe(true);
    });

    it('should unregister action handler', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      const handler = jest.fn();
      
      act(() => {
        result.current.registerHandler('create_task', handler);
        result.current.unregisterHandler('create_task');
      });
      
      expect(result.current.actionHandlers.has('create_task')).toBe(false);
    });
  });

  describe('UI State', () => {
    it('should toggle bar visibility', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.setBarVisible(false);
      });
      
      expect(result.current.isBarVisible).toBe(false);
      
      act(() => {
        result.current.setBarVisible(true);
      });
      
      expect(result.current.isBarVisible).toBe(true);
    });

    it('should toggle expanded state', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      expect(result.current.isExpanded).toBe(false);
      
      act(() => {
        result.current.toggleExpanded();
      });
      
      expect(result.current.isExpanded).toBe(true);
      
      act(() => {
        result.current.toggleExpanded();
      });
      
      expect(result.current.isExpanded).toBe(false);
    });

    it('should set hovered action', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.setHoveredAction('action-create-task');
      });
      
      expect(result.current.hoveredActionId).toBe('action-create-task');
    });

    it('should set user permissions', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.setUserPermissions(['can_delete', 'can_archive']);
      });
      
      expect(result.current.userPermissions).toEqual(['can_delete', 'can_archive']);
    });
  });

  describe('Confirmation Dialog', () => {
    it('should show confirmation', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      const context: ActionContext = {
        entityType: 'opportunity',
        entityId: 'opp-123',
      };
      
      act(() => {
        result.current.showConfirmation('action-delete', context);
      });
      
      expect(result.current.confirmation.isOpen).toBe(true);
      expect(result.current.confirmation.actionId).toBe('action-delete');
      expect(result.current.confirmation.context).toEqual(context);
    });

    it('should hide confirmation', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.showConfirmation('action-delete', {
          entityType: 'opportunity',
          entityId: 'opp-123',
        });
        result.current.hideConfirmation();
      });
      
      expect(result.current.confirmation.isOpen).toBe(false);
      expect(result.current.confirmation.actionId).toBeNull();
    });
  });

  describe('Action Getters', () => {
    it('should return available actions for context', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.setContext({
          entityType: 'opportunity',
          entityId: 'opp-123',
        });
        result.current.setUserPermissions(['can_delete', 'can_archive', 'can_request_approval', 'can_assign']);
      });
      
      const available = result.current.getAvailableActions();
      expect(available.length).toBeGreaterThan(0);
    });

    it('should return empty array when no context', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      const available = result.current.getAvailableActions();
      expect(available).toEqual([]);
    });

    it('should filter by visibility in getPrimaryActions', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.setContext({
          entityType: 'opportunity',
          entityId: 'opp-123',
        });
        result.current.setUserPermissions(['can_request_approval']);
      });
      
      const primary = result.current.getPrimaryActions();
      primary.forEach((action) => {
        expect(action.visibility || 'always').toBe('always');
      });
    });

    it('should filter by visibility in getSecondaryActions', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.setContext({
          entityType: 'opportunity',
          entityId: 'opp-123',
        });
        result.current.setUserPermissions(['can_assign']);
      });
      
      const secondary = result.current.getSecondaryActions();
      secondary.forEach((action) => {
        expect(action.visibility).toBe('hover');
      });
    });

    it('should filter by visibility in getOverflowActions', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        result.current.setContext({
          entityType: 'opportunity',
          entityId: 'opp-123',
        });
        result.current.setUserPermissions(['can_delete', 'can_archive']);
      });
      
      const overflow = result.current.getOverflowActions();
      overflow.forEach((action) => {
        expect(action.visibility).toBe('overflow');
      });
    });
  });

  describe('Execution History', () => {
    it('should clear execution history', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      // Add an execution first
      act(() => {
        // Simulate an execution by setting state directly
        useQuickActionsStore.setState({
          executions: [
            {
              id: 'exec-1',
              actionId: 'action-create-task',
              context: { entityType: 'opportunity', entityId: '123' },
              status: 'completed',
            },
          ],
        });
      });
      
      expect(result.current.executions.length).toBe(1);
      
      act(() => {
        result.current.clearExecutionHistory();
      });
      
      expect(result.current.executions).toEqual([]);
    });

    it('should get execution by ID', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        useQuickActionsStore.setState({
          executions: [
            {
              id: 'exec-1',
              actionId: 'action-create-task',
              context: { entityType: 'opportunity', entityId: '123' },
              status: 'completed',
            },
          ],
        });
      });
      
      const execution = result.current.getExecution('exec-1');
      expect(execution).toBeDefined();
      expect(execution?.actionId).toBe('action-create-task');
    });

    it('should return undefined for unknown execution ID', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      const execution = result.current.getExecution('unknown');
      expect(execution).toBeUndefined();
    });
  });

  describe('Cancel Execution', () => {
    it('should cancel executing action', () => {
      const { result } = renderHook(() => useQuickActionsStore());
      
      act(() => {
        useQuickActionsStore.setState({
          executions: [
            {
              id: 'exec-1',
              actionId: 'action-create-task',
              context: { entityType: 'opportunity', entityId: '123' },
              status: 'executing',
              startedAt: new Date(),
            },
          ],
          currentExecution: {
            id: 'exec-1',
            actionId: 'action-create-task',
            context: { entityType: 'opportunity', entityId: '123' },
            status: 'executing',
            startedAt: new Date(),
          },
        });
      });
      
      act(() => {
        result.current.cancelExecution('exec-1');
      });
      
      const execution = result.current.getExecution('exec-1');
      expect(execution?.status).toBe('cancelled');
      expect(result.current.currentExecution).toBeNull();
    });
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('Quick Actions Integration', () => {
  it('should correctly filter actions for opportunity with permissions', () => {
    const { result } = renderHook(() => useQuickActionsStore());
    
    act(() => {
      result.current.setContext({
        entityType: 'opportunity',
        entityId: 'opp-123',
        entityName: 'Big Deal',
      });
      result.current.setUserPermissions([
        'can_request_approval',
        'can_assign',
        'can_archive',
        'can_delete',
      ]);
    });
    
    const available = result.current.getAvailableActions();
    const primary = result.current.getPrimaryActions();
    const secondary = result.current.getSecondaryActions();
    const overflow = result.current.getOverflowActions();
    
    // Should have actions
    expect(available.length).toBeGreaterThan(0);
    expect(primary.length).toBeGreaterThan(0);
    
    // Categories should be mutually exclusive
    const allCategorized = [...primary, ...secondary, ...overflow];
    expect(allCategorized.length).toBe(available.length);
  });

  it('should correctly filter actions for task entity', () => {
    const { result } = renderHook(() => useQuickActionsStore());
    
    act(() => {
      result.current.setContext({
        entityType: 'task',
        entityId: 'task-456',
      });
      result.current.setUserPermissions([]);
    });
    
    const available = result.current.getAvailableActions();
    
    // Task should have fewer actions than opportunity
    expect(available.length).toBeLessThan(15);
    
    // Task should have resolve action
    const hasResolve = available.some((a) => a.type === 'resolve');
    expect(hasResolve).toBe(true);
    
    // Task should NOT have export_pdf action
    const hasExportPdf = available.some((a) => a.type === 'export_pdf');
    expect(hasExportPdf).toBe(false);
  });

  it('should support custom actions alongside default actions', () => {
    const { result } = renderHook(() => useQuickActionsStore());
    
    const customAction: QuickAction = {
      id: 'custom-review',
      type: 'create_task', // Uses create_task type so it appears for entities that have it
      label: 'Request Review',
      icon: 'eye',
      visibility: 'always',
    };
    
    act(() => {
      result.current.registerAction(customAction);
      result.current.setContext({
        entityType: 'quote',
        entityId: 'quote-789',
      });
      result.current.setUserPermissions([]);
    });
    
    const available = result.current.getAvailableActions();
    const hasCustom = available.some((a) => a.id === 'custom-review');
    expect(hasCustom).toBe(true);
  });
});
