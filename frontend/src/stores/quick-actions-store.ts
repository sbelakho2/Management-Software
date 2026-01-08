import { create } from 'zustand';

// =============================================================================
// Types
// =============================================================================

export type EntityType =
  | 'opportunity'
  | 'rfq'
  | 'quote'
  | 'qualification'
  | 'task'
  | 'a3'
  | 'obeya'
  | 'ctq'
  | 'account'
  | 'contact'
  | 'work_order'
  | 'andon';

export type ActionType =
  | 'create_task'
  | 'request_info'
  | 'request_approval'
  | 'export_pdf'
  | 'export_csv'
  | 'duplicate'
  | 'create_from_template'
  | 'archive'
  | 'delete'
  | 'assign'
  | 'change_status'
  | 'add_comment'
  | 'add_attachment'
  | 'escalate'
  | 'resolve'
  | 'print'
  | 'share'
  | 'watch'
  | 'unwatch';

export type ActionVisibility = 'always' | 'hover' | 'overflow';

export type ActionVariant = 'primary' | 'secondary' | 'ghost' | 'destructive' | 'warning';

export interface QuickAction {
  id: string;
  type: ActionType;
  label: string;
  icon: string;
  shortcut?: string;
  description?: string;
  variant?: ActionVariant;
  visibility?: ActionVisibility;
  confirmationRequired?: boolean;
  confirmationMessage?: string;
  disabled?: boolean;
  disabledReason?: string;
  requiredPermission?: string;
  entityTypes?: EntityType[];
}

export interface ActionContext {
  entityType: EntityType;
  entityId: string;
  entityName?: string;
  additionalData?: Record<string, unknown>;
}

export interface ActionExecution {
  id: string;
  actionId: string;
  context: ActionContext;
  status: 'pending' | 'executing' | 'completed' | 'failed' | 'cancelled';
  startedAt?: Date;
  completedAt?: Date;
  error?: string;
  result?: unknown;
}

export interface ConfirmationState {
  isOpen: boolean;
  actionId: string | null;
  context: ActionContext | null;
  message: string;
  variant: ActionVariant;
}

// =============================================================================
// Action Configuration
// =============================================================================

export const DEFAULT_ACTIONS: QuickAction[] = [
  {
    id: 'action-create-task',
    type: 'create_task',
    label: 'Create Task',
    icon: 'plus-circle',
    shortcut: 'T',
    description: 'Create a new task linked to this item',
    variant: 'primary',
    visibility: 'always',
  },
  {
    id: 'action-request-info',
    type: 'request_info',
    label: 'Request Info',
    icon: 'message-circle',
    shortcut: 'I',
    description: 'Request missing information from team members',
    variant: 'secondary',
    visibility: 'always',
  },
  {
    id: 'action-request-approval',
    type: 'request_approval',
    label: 'Request Approval',
    icon: 'check-circle',
    shortcut: 'A',
    description: 'Submit for approval',
    variant: 'primary',
    visibility: 'always',
    requiredPermission: 'can_request_approval',
  },
  {
    id: 'action-export-pdf',
    type: 'export_pdf',
    label: 'Export PDF',
    icon: 'file-text',
    shortcut: 'P',
    description: 'Export as PDF document',
    variant: 'ghost',
    visibility: 'hover',
  },
  {
    id: 'action-export-csv',
    type: 'export_csv',
    label: 'Export CSV',
    icon: 'table',
    description: 'Export as CSV file',
    variant: 'ghost',
    visibility: 'overflow',
  },
  {
    id: 'action-duplicate',
    type: 'duplicate',
    label: 'Duplicate',
    icon: 'copy',
    shortcut: 'D',
    description: 'Create a copy of this item',
    variant: 'ghost',
    visibility: 'overflow',
  },
  {
    id: 'action-create-from-template',
    type: 'create_from_template',
    label: 'Use as Template',
    icon: 'layout-template',
    description: 'Create a new item using this as a template',
    variant: 'ghost',
    visibility: 'overflow',
  },
  {
    id: 'action-assign',
    type: 'assign',
    label: 'Assign',
    icon: 'user-plus',
    shortcut: 'O',
    description: 'Assign to a team member',
    variant: 'ghost',
    visibility: 'hover',
    requiredPermission: 'can_assign',
  },
  {
    id: 'action-change-status',
    type: 'change_status',
    label: 'Change Status',
    icon: 'refresh-cw',
    shortcut: 'S',
    description: 'Change the status of this item',
    variant: 'ghost',
    visibility: 'hover',
  },
  {
    id: 'action-add-comment',
    type: 'add_comment',
    label: 'Comment',
    icon: 'message-square',
    shortcut: 'C',
    description: 'Add a comment',
    variant: 'ghost',
    visibility: 'always',
  },
  {
    id: 'action-add-attachment',
    type: 'add_attachment',
    label: 'Attach File',
    icon: 'paperclip',
    description: 'Attach a file to this item',
    variant: 'ghost',
    visibility: 'hover',
  },
  {
    id: 'action-escalate',
    type: 'escalate',
    label: 'Escalate',
    icon: 'alert-triangle',
    description: 'Escalate this item for urgent attention',
    variant: 'warning',
    visibility: 'overflow',
    confirmationRequired: true,
    confirmationMessage: 'Are you sure you want to escalate this item? This will notify relevant stakeholders.',
    entityTypes: ['andon', 'a3', 'task'],
  },
  {
    id: 'action-resolve',
    type: 'resolve',
    label: 'Resolve',
    icon: 'check-square',
    description: 'Mark this item as resolved',
    variant: 'secondary',
    visibility: 'always',
    entityTypes: ['andon', 'a3', 'task'],
  },
  {
    id: 'action-print',
    type: 'print',
    label: 'Print',
    icon: 'printer',
    description: 'Print this item',
    variant: 'ghost',
    visibility: 'overflow',
  },
  {
    id: 'action-share',
    type: 'share',
    label: 'Share',
    icon: 'share-2',
    description: 'Share a link to this item',
    variant: 'ghost',
    visibility: 'overflow',
  },
  {
    id: 'action-watch',
    type: 'watch',
    label: 'Watch',
    icon: 'eye',
    description: 'Get notifications for changes',
    variant: 'ghost',
    visibility: 'overflow',
  },
  {
    id: 'action-unwatch',
    type: 'unwatch',
    label: 'Unwatch',
    icon: 'eye-off',
    description: 'Stop receiving notifications',
    variant: 'ghost',
    visibility: 'overflow',
  },
  {
    id: 'action-archive',
    type: 'archive',
    label: 'Archive',
    icon: 'archive',
    description: 'Archive this item',
    variant: 'ghost',
    visibility: 'overflow',
    confirmationRequired: true,
    confirmationMessage: 'Are you sure you want to archive this item?',
    requiredPermission: 'can_archive',
  },
  {
    id: 'action-delete',
    type: 'delete',
    label: 'Delete',
    icon: 'trash-2',
    description: 'Permanently delete this item',
    variant: 'destructive',
    visibility: 'overflow',
    confirmationRequired: true,
    confirmationMessage: 'Are you sure you want to delete this item? This action cannot be undone.',
    requiredPermission: 'can_delete',
  },
];

// =============================================================================
// Entity-Action Mapping
// =============================================================================

export const ENTITY_ACTION_MAP: Record<EntityType, ActionType[]> = {
  opportunity: [
    'create_task', 'request_info', 'request_approval', 'export_pdf', 'export_csv',
    'duplicate', 'assign', 'change_status', 'add_comment', 'add_attachment',
    'print', 'share', 'watch', 'unwatch', 'archive', 'delete',
  ],
  rfq: [
    'create_task', 'request_info', 'export_pdf', 'duplicate', 'create_from_template',
    'assign', 'change_status', 'add_comment', 'add_attachment',
    'print', 'share', 'watch', 'unwatch', 'archive', 'delete',
  ],
  quote: [
    'create_task', 'request_info', 'request_approval', 'export_pdf',
    'duplicate', 'create_from_template', 'assign', 'change_status',
    'add_comment', 'add_attachment', 'print', 'share', 'watch', 'unwatch', 'archive',
  ],
  qualification: [
    'create_task', 'request_info', 'request_approval', 'export_pdf',
    'assign', 'change_status', 'add_comment', 'add_attachment',
    'share', 'watch', 'unwatch', 'archive',
  ],
  task: [
    'assign', 'change_status', 'add_comment', 'add_attachment',
    'duplicate', 'resolve', 'watch', 'unwatch', 'delete',
  ],
  a3: [
    'create_task', 'request_info', 'export_pdf', 'assign', 'change_status',
    'add_comment', 'add_attachment', 'escalate', 'resolve',
    'print', 'share', 'watch', 'unwatch', 'archive',
  ],
  obeya: [
    'create_task', 'request_info', 'export_pdf', 'assign', 'change_status',
    'add_comment', 'add_attachment', 'escalate',
    'share', 'watch', 'unwatch',
  ],
  ctq: [
    'create_task', 'request_info', 'export_pdf', 'assign', 'change_status',
    'add_comment', 'add_attachment', 'share', 'watch', 'unwatch', 'archive',
  ],
  account: [
    'create_task', 'export_csv', 'add_comment', 'add_attachment',
    'share', 'watch', 'unwatch', 'archive', 'delete',
  ],
  contact: [
    'create_task', 'add_comment', 'add_attachment',
    'share', 'watch', 'unwatch', 'archive', 'delete',
  ],
  work_order: [
    'create_task', 'request_info', 'export_pdf', 'assign', 'change_status',
    'add_comment', 'add_attachment', 'print', 'watch', 'unwatch',
  ],
  andon: [
    'create_task', 'assign', 'change_status', 'add_comment', 'add_attachment',
    'escalate', 'resolve', 'watch', 'unwatch',
  ],
};

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get actions available for a specific entity type
 */
export function getActionsForEntity(
  entityType: EntityType,
  allActions: QuickAction[] = DEFAULT_ACTIONS
): QuickAction[] {
  const allowedActionTypes = ENTITY_ACTION_MAP[entityType] || [];
  
  return allActions.filter((action) => {
    // Check if action type is allowed for this entity
    if (!allowedActionTypes.includes(action.type)) {
      return false;
    }
    
    // Check if action has specific entity type restrictions
    if (action.entityTypes && action.entityTypes.length > 0) {
      return action.entityTypes.includes(entityType);
    }
    
    return true;
  });
}

/**
 * Filter actions by visibility level
 */
export function filterByVisibility(
  actions: QuickAction[],
  visibility: ActionVisibility | ActionVisibility[]
): QuickAction[] {
  const visibilities = Array.isArray(visibility) ? visibility : [visibility];
  return actions.filter((action) =>
    visibilities.includes(action.visibility || 'always')
  );
}

/**
 * Get primary actions (always visible)
 */
export function getPrimaryActions(actions: QuickAction[]): QuickAction[] {
  return filterByVisibility(actions, 'always');
}

/**
 * Get secondary actions (visible on hover)
 */
export function getSecondaryActions(actions: QuickAction[]): QuickAction[] {
  return filterByVisibility(actions, 'hover');
}

/**
 * Get overflow actions (in dropdown menu)
 */
export function getOverflowActions(actions: QuickAction[]): QuickAction[] {
  return filterByVisibility(actions, 'overflow');
}

/**
 * Check if user has permission to execute action
 */
export function hasPermission(
  action: QuickAction,
  userPermissions: string[]
): boolean {
  if (!action.requiredPermission) {
    return true;
  }
  return userPermissions.includes(action.requiredPermission);
}

/**
 * Filter actions by user permissions
 */
export function filterByPermissions(
  actions: QuickAction[],
  userPermissions: string[]
): QuickAction[] {
  return actions.filter((action) => hasPermission(action, userPermissions));
}

/**
 * Get action by ID
 */
export function getActionById(
  actionId: string,
  actions: QuickAction[] = DEFAULT_ACTIONS
): QuickAction | undefined {
  return actions.find((action) => action.id === actionId);
}

/**
 * Get action by type
 */
export function getActionByType(
  actionType: ActionType,
  actions: QuickAction[] = DEFAULT_ACTIONS
): QuickAction | undefined {
  return actions.find((action) => action.type === actionType);
}

/**
 * Format entity name for display
 */
export function formatEntityType(entityType: EntityType): string {
  const mapping: Record<EntityType, string> = {
    opportunity: 'Opportunity',
    rfq: 'RFQ',
    quote: 'Quote',
    qualification: 'Qualification',
    task: 'Task',
    a3: 'A3',
    obeya: 'Obeya',
    ctq: 'CTQ',
    account: 'Account',
    contact: 'Contact',
    work_order: 'Work Order',
    andon: 'Andon',
  };
  return mapping[entityType] || entityType;
}

/**
 * Generate unique execution ID
 */
export function generateExecutionId(): string {
  return `exec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// =============================================================================
// State Interface
// =============================================================================

interface QuickActionsState {
  // Configuration
  actions: QuickAction[];
  customActions: QuickAction[];
  
  // Current context
  currentContext: ActionContext | null;
  activeEntityId: string | null;
  
  // Execution tracking
  executions: ActionExecution[];
  currentExecution: ActionExecution | null;
  
  // Confirmation dialog
  confirmation: ConfirmationState;
  
  // User permissions (would come from auth in real app)
  userPermissions: string[];
  
  // UI state
  isBarVisible: boolean;
  isExpanded: boolean;
  hoveredActionId: string | null;
  
  // Callbacks registry
  actionHandlers: Map<ActionType, (context: ActionContext) => Promise<unknown>>;
  
  // Actions
  setContext: (context: ActionContext | null) => void;
  clearContext: () => void;
  
  setActiveEntity: (entityId: string | null) => void;
  
  registerAction: (action: QuickAction) => void;
  unregisterAction: (actionId: string) => void;
  updateAction: (actionId: string, updates: Partial<QuickAction>) => void;
  
  registerHandler: (actionType: ActionType, handler: (context: ActionContext) => Promise<unknown>) => void;
  unregisterHandler: (actionType: ActionType) => void;
  
  executeAction: (actionId: string, context?: ActionContext) => Promise<void>;
  cancelExecution: (executionId: string) => void;
  
  showConfirmation: (actionId: string, context: ActionContext) => void;
  hideConfirmation: () => void;
  confirmAction: () => Promise<void>;
  
  setBarVisible: (visible: boolean) => void;
  toggleExpanded: () => void;
  setHoveredAction: (actionId: string | null) => void;
  
  setUserPermissions: (permissions: string[]) => void;
  
  getAvailableActions: () => QuickAction[];
  getPrimaryActions: () => QuickAction[];
  getSecondaryActions: () => QuickAction[];
  getOverflowActions: () => QuickAction[];
  
  clearExecutionHistory: () => void;
  getExecution: (executionId: string) => ActionExecution | undefined;
}

// =============================================================================
// Store Implementation
// =============================================================================

export const useQuickActionsStore = create<QuickActionsState>((set, get) => ({
  // Initial state
  actions: [...DEFAULT_ACTIONS],
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
  
  // Context management
  setContext: (context) => {
    set({
      currentContext: context,
      activeEntityId: context?.entityId || null,
    });
  },
  
  clearContext: () => {
    set({
      currentContext: null,
      activeEntityId: null,
    });
  },
  
  setActiveEntity: (entityId) => {
    set({ activeEntityId: entityId });
  },
  
  // Action registration
  registerAction: (action) => {
    set((state) => ({
      customActions: [...state.customActions, action],
    }));
  },
  
  unregisterAction: (actionId) => {
    set((state) => ({
      customActions: state.customActions.filter((a) => a.id !== actionId),
    }));
  },
  
  updateAction: (actionId, updates) => {
    set((state) => ({
      actions: state.actions.map((a) =>
        a.id === actionId ? { ...a, ...updates } : a
      ),
      customActions: state.customActions.map((a) =>
        a.id === actionId ? { ...a, ...updates } : a
      ),
    }));
  },
  
  // Handler registration
  registerHandler: (actionType, handler) => {
    const { actionHandlers } = get();
    const newHandlers = new Map(actionHandlers);
    newHandlers.set(actionType, handler);
    set({ actionHandlers: newHandlers });
  },
  
  unregisterHandler: (actionType) => {
    const { actionHandlers } = get();
    const newHandlers = new Map(actionHandlers);
    newHandlers.delete(actionType);
    set({ actionHandlers: newHandlers });
  },
  
  // Action execution
  executeAction: async (actionId, contextOverride) => {
    const state = get();
    const allActions = [...state.actions, ...state.customActions];
    const action = allActions.find((a) => a.id === actionId);
    
    if (!action) {
      console.error(`Action not found: ${actionId}`);
      return;
    }
    
    const context = contextOverride || state.currentContext;
    if (!context) {
      console.error('No context provided for action execution');
      return;
    }
    
    // Check if action is disabled
    if (action.disabled) {
      console.warn(`Action is disabled: ${actionId}`);
      return;
    }
    
    // Check permissions
    if (!hasPermission(action, state.userPermissions)) {
      console.warn(`Insufficient permissions for action: ${actionId}`);
      return;
    }
    
    // Check if confirmation is required
    if (action.confirmationRequired) {
      get().showConfirmation(actionId, context);
      return;
    }
    
    // Execute the action
    await get().performExecution(actionId, action, context);
  },
  
  cancelExecution: (executionId) => {
    set((state) => ({
      executions: state.executions.map((e) =>
        e.id === executionId && e.status === 'executing'
          ? { ...e, status: 'cancelled' as const, completedAt: new Date() }
          : e
      ),
      currentExecution:
        state.currentExecution?.id === executionId
          ? null
          : state.currentExecution,
    }));
  },
  
  // Confirmation dialog
  showConfirmation: (actionId, context) => {
    const state = get();
    const allActions = [...state.actions, ...state.customActions];
    const action = allActions.find((a) => a.id === actionId);
    
    if (!action) return;
    
    set({
      confirmation: {
        isOpen: true,
        actionId,
        context,
        message: action.confirmationMessage || `Are you sure you want to ${action.label.toLowerCase()}?`,
        variant: action.variant || 'primary',
      },
    });
  },
  
  hideConfirmation: () => {
    set({
      confirmation: {
        isOpen: false,
        actionId: null,
        context: null,
        message: '',
        variant: 'primary',
      },
    });
  },
  
  confirmAction: async () => {
    const { confirmation } = get();
    if (!confirmation.actionId || !confirmation.context) return;
    
    const state = get();
    const allActions = [...state.actions, ...state.customActions];
    const action = allActions.find((a) => a.id === confirmation.actionId);
    
    if (!action) return;
    
    get().hideConfirmation();
    await get().performExecution(confirmation.actionId, action, confirmation.context);
  },
  
  // UI state
  setBarVisible: (visible) => {
    set({ isBarVisible: visible });
  },
  
  toggleExpanded: () => {
    set((state) => ({ isExpanded: !state.isExpanded }));
  },
  
  setHoveredAction: (actionId) => {
    set({ hoveredActionId: actionId });
  },
  
  setUserPermissions: (permissions) => {
    set({ userPermissions: permissions });
  },
  
  // Getters for filtered actions
  getAvailableActions: () => {
    const state = get();
    const { currentContext, userPermissions, actions, customActions } = state;
    
    if (!currentContext) return [];
    
    const allActions = [...actions, ...customActions];
    const entityActions = getActionsForEntity(currentContext.entityType, allActions);
    
    return filterByPermissions(entityActions, userPermissions).filter(
      (action) => !action.hidden && !action.disabled
    );
  },
  
  getPrimaryActions: () => {
    const available = get().getAvailableActions();
    return filterByVisibility(available, 'always');
  },
  
  getSecondaryActions: () => {
    const available = get().getAvailableActions();
    return filterByVisibility(available, 'hover');
  },
  
  getOverflowActions: () => {
    const available = get().getAvailableActions();
    return filterByVisibility(available, 'overflow');
  },
  
  // Execution history
  clearExecutionHistory: () => {
    set({ executions: [] });
  },
  
  getExecution: (executionId) => {
    return get().executions.find((e) => e.id === executionId);
  },
}));

// Internal helper added to store prototype
const performExecution = async (
  actionId: string,
  action: QuickAction,
  context: ActionContext
) => {
  const state = useQuickActionsStore.getState();
  const executionId = generateExecutionId();
  
  const execution: ActionExecution = {
    id: executionId,
    actionId,
    context,
    status: 'executing',
    startedAt: new Date(),
  };
  
  useQuickActionsStore.setState((s) => ({
    executions: [...s.executions, execution],
    currentExecution: execution,
  }));
  
  try {
    const handler = state.actionHandlers.get(action.type);
    let result: unknown;
    
    if (handler) {
      result = await handler(context);
    } else {
      // Default behavior - log action
      console.log(`Executing action: ${action.label}`, context);
      result = { success: true };
    }
    
    useQuickActionsStore.setState((s) => ({
      executions: s.executions.map((e) =>
        e.id === executionId
          ? { ...e, status: 'completed' as const, completedAt: new Date(), result }
          : e
      ),
      currentExecution: null,
    }));
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    
    useQuickActionsStore.setState((s) => ({
      executions: s.executions.map((e) =>
        e.id === executionId
          ? { ...e, status: 'failed' as const, completedAt: new Date(), error: errorMessage }
          : e
      ),
      currentExecution: null,
    }));
    
    throw error;
  }
};

// Add performExecution to the store
// This is a workaround since we can't reference the store from within create()
Object.assign(useQuickActionsStore.getState(), { performExecution });

// =============================================================================
// Selectors
// =============================================================================

export const selectCurrentContext = (state: QuickActionsState) => state.currentContext;
export const selectIsBarVisible = (state: QuickActionsState) => state.isBarVisible;
export const selectIsExpanded = (state: QuickActionsState) => state.isExpanded;
export const selectConfirmation = (state: QuickActionsState) => state.confirmation;
export const selectCurrentExecution = (state: QuickActionsState) => state.currentExecution;
export const selectExecutions = (state: QuickActionsState) => state.executions;
export const selectHoveredActionId = (state: QuickActionsState) => state.hoveredActionId;
export const selectUserPermissions = (state: QuickActionsState) => state.userPermissions;
