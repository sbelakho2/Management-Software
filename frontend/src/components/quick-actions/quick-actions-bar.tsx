'use client';

import * as React from 'react';
import {
  Plus,
  MessageCircle,
  CheckCircle,
  FileText,
  Table,
  Copy,
  LayoutTemplate,
  Archive,
  Trash2,
  UserPlus,
  RefreshCw,
  MessageSquare,
  Paperclip,
  AlertTriangle,
  CheckSquare,
  Printer,
  Share2,
  Eye,
  EyeOff,
  MoreHorizontal,
  X,
  Loader2,
  ChevronDown,
  ChevronUp,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  useQuickActionsStore,
  type QuickAction,
  type ActionContext,
  type ActionVariant,
  formatEntityType,
} from '@/stores/quick-actions-store';

// =============================================================================
// Icon Mapping
// =============================================================================

const iconMap: Record<string, LucideIcon> = {
  'plus-circle': Plus,
  'message-circle': MessageCircle,
  'check-circle': CheckCircle,
  'file-text': FileText,
  table: Table,
  copy: Copy,
  'layout-template': LayoutTemplate,
  archive: Archive,
  'trash-2': Trash2,
  'user-plus': UserPlus,
  'refresh-cw': RefreshCw,
  'message-square': MessageSquare,
  paperclip: Paperclip,
  'alert-triangle': AlertTriangle,
  'check-square': CheckSquare,
  printer: Printer,
  'share-2': Share2,
  eye: Eye,
  'eye-off': EyeOff,
};

function getIcon(iconName: string): LucideIcon {
  return iconMap[iconName] || Plus;
}

// =============================================================================
// Sub-Components
// =============================================================================

interface ActionButtonProps {
  action: QuickAction;
  size?: 'sm' | 'default';
  showLabel?: boolean;
  onClick: () => void;
  isExecuting?: boolean;
}

function ActionButton({
  action,
  size = 'default',
  showLabel = false,
  onClick,
  isExecuting = false,
}: ActionButtonProps) {
  const Icon = getIcon(action.icon);
  
  const variantMap: Record<ActionVariant, 'default' | 'secondary' | 'ghost' | 'destructive' | 'warning'> = {
    primary: 'default',
    secondary: 'secondary',
    ghost: 'ghost',
    destructive: 'destructive',
    warning: 'warning',
  };
  
  const buttonVariant = variantMap[action.variant || 'ghost'];
  const buttonSize = size === 'sm' ? 'icon-sm' : 'icon';
  
  const button = (
    <Button
      variant={buttonVariant}
      size={showLabel ? (size === 'sm' ? 'sm' : 'default') : buttonSize}
      onClick={onClick}
      disabled={action.disabled || isExecuting}
      aria-label={action.label}
      className={cn(
        'transition-all duration-200',
        isExecuting && 'opacity-70'
      )}
    >
      {isExecuting ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Icon className={cn('h-4 w-4', showLabel && 'mr-2')} />
      )}
      {showLabel && action.label}
    </Button>
  );
  
  if (showLabel) {
    return button;
  }
  
  return (
    <Tooltip>
      <TooltipTrigger asChild>{button}</TooltipTrigger>
      <TooltipContent side="bottom" className="flex flex-col gap-1">
        <span className="font-medium">{action.label}</span>
        {action.description && (
          <span className="text-xs text-muted-foreground">{action.description}</span>
        )}
        {action.shortcut && (
          <span className="text-xs">
            Shortcut: <kbd className="rounded bg-muted px-1">{action.shortcut}</kbd>
          </span>
        )}
      </TooltipContent>
    </Tooltip>
  );
}

interface OverflowMenuProps {
  actions: QuickAction[];
  onActionClick: (actionId: string) => void;
  executingActionId?: string | null;
}

function OverflowMenu({ actions, onActionClick, executingActionId }: OverflowMenuProps) {
  if (actions.length === 0) {
    return null;
  }
  
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="More actions">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        {actions.map((action, index) => {
          const Icon = getIcon(action.icon);
          const isExecuting = executingActionId === action.id;
          
          // Add separator before destructive actions
          const needsSeparator =
            index > 0 &&
            action.variant === 'destructive' &&
            actions[index - 1]?.variant !== 'destructive';
          
          return (
            <React.Fragment key={action.id}>
              {needsSeparator && <DropdownMenuSeparator />}
              <DropdownMenuItem
                onClick={() => onActionClick(action.id)}
                disabled={action.disabled || isExecuting}
                className={cn(
                  'cursor-pointer',
                  action.variant === 'destructive' && 'text-destructive focus:text-destructive',
                  action.variant === 'warning' && 'text-warning focus:text-warning'
                )}
              >
                {isExecuting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Icon className="mr-2 h-4 w-4" />
                )}
                <span className="flex-1">{action.label}</span>
                {action.shortcut && (
                  <kbd className="ml-auto text-xs text-muted-foreground">
                    {action.shortcut}
                  </kbd>
                )}
              </DropdownMenuItem>
            </React.Fragment>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export interface QuickActionsBarProps {
  context?: ActionContext;
  className?: string;
  position?: 'inline' | 'floating' | 'toolbar';
  size?: 'sm' | 'default';
  showLabels?: boolean;
  maxPrimaryActions?: number;
  onActionExecuted?: (actionId: string, result: unknown) => void;
  onActionError?: (actionId: string, error: Error) => void;
}

export function QuickActionsBar({
  context: contextProp,
  className,
  position = 'inline',
  size = 'default',
  showLabels = false,
  maxPrimaryActions = 4,
  onActionExecuted,
  onActionError,
}: QuickActionsBarProps) {
  const {
    currentContext: storeContext,
    setContext,
    confirmation,
    hideConfirmation,
    confirmAction,
    currentExecution,
    isBarVisible,
    isExpanded,
    toggleExpanded,
    setHoveredAction,
    executeAction,
    getPrimaryActions,
    getSecondaryActions,
    getOverflowActions,
  } = useQuickActionsStore();
  
  // Use prop context if provided, otherwise use store context
  const context = contextProp || storeContext;
  
  // Set context from prop if provided
  React.useEffect(() => {
    if (contextProp) {
      setContext(contextProp);
    }
  }, [contextProp, setContext]);
  
  // Get filtered actions
  const primaryActions = getPrimaryActions().slice(0, maxPrimaryActions);
  const secondaryActions = getSecondaryActions();
  const overflowActions = getOverflowActions();
  
  // Combine extra primary actions into overflow
  const extraPrimaryActions = getPrimaryActions().slice(maxPrimaryActions);
  const allOverflowActions = [...secondaryActions, ...extraPrimaryActions, ...overflowActions];
  
  const handleActionClick = React.useCallback(
    async (actionId: string) => {
      if (!context) return;
      
      try {
        await executeAction(actionId, context);
        onActionExecuted?.(actionId, { success: true });
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Unknown error');
        onActionError?.(actionId, err);
      }
    },
    [context, executeAction, onActionExecuted, onActionError]
  );
  
  const handleConfirm = React.useCallback(async () => {
    try {
      await confirmAction();
      if (confirmation.actionId) {
        onActionExecuted?.(confirmation.actionId, { success: true });
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Unknown error');
      if (confirmation.actionId) {
        onActionError?.(confirmation.actionId, err);
      }
    }
  }, [confirmAction, confirmation.actionId, onActionExecuted, onActionError]);
  
  // Don't render if no context or bar is hidden
  if (!context || !isBarVisible) {
    return null;
  }
  
  // No actions available
  if (primaryActions.length === 0 && allOverflowActions.length === 0) {
    return null;
  }
  
  const positionClasses = {
    inline: 'flex items-center gap-1',
    floating:
      'fixed bottom-4 right-4 z-50 flex items-center gap-1 rounded-lg border bg-background p-2 shadow-lg',
    toolbar:
      'flex items-center gap-1 border-b bg-muted/30 px-4 py-2',
  };
  
  return (
    <TooltipProvider delayDuration={300}>
      <div
        className={cn(positionClasses[position], className)}
        role="toolbar"
        aria-label={`Quick actions for ${context.entityName || formatEntityType(context.entityType)}`}
        onMouseEnter={() => setHoveredAction(null)}
      >
        {/* Context indicator for floating position */}
        {position === 'floating' && context.entityName && (
          <span className="mr-2 text-sm text-muted-foreground">
            {context.entityName}
          </span>
        )}
        
        {/* Primary actions */}
        {primaryActions.map((action) => (
          <ActionButton
            key={action.id}
            action={action}
            size={size}
            showLabel={showLabels}
            onClick={() => handleActionClick(action.id)}
            isExecuting={currentExecution?.actionId === action.id}
          />
        ))}
        
        {/* Expand/collapse for toolbar position */}
        {position === 'toolbar' && secondaryActions.length > 0 && (
          <Button
            variant="ghost"
            size={size === 'sm' ? 'icon-sm' : 'icon'}
            onClick={toggleExpanded}
            aria-label={isExpanded ? 'Show fewer actions' : 'Show more actions'}
            aria-expanded={isExpanded}
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        )}
        
        {/* Expanded secondary actions */}
        {position === 'toolbar' && isExpanded && (
          <>
            <div className="mx-2 h-4 w-px bg-border" />
            {secondaryActions.map((action) => (
              <ActionButton
                key={action.id}
                action={action}
                size={size}
                showLabel={showLabels}
                onClick={() => handleActionClick(action.id)}
                isExecuting={currentExecution?.actionId === action.id}
              />
            ))}
          </>
        )}
        
        {/* Overflow menu */}
        <OverflowMenu
          actions={position === 'toolbar' && isExpanded ? overflowActions : allOverflowActions}
          onActionClick={handleActionClick}
          executingActionId={currentExecution?.actionId}
        />
        
        {/* Close button for floating position */}
        {position === 'floating' && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => useQuickActionsStore.getState().setBarVisible(false)}
            aria-label="Close quick actions"
            className="ml-2"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      
      {/* Confirmation Dialog */}
      <AlertDialog open={confirmation.isOpen} onOpenChange={(open) => !open && hideConfirmation()}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Action</AlertDialogTitle>
            <AlertDialogDescription>{confirmation.message}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirm}
              className={cn(
                confirmation.variant === 'destructive' &&
                  'bg-destructive text-destructive-foreground hover:bg-destructive/90',
                confirmation.variant === 'warning' &&
                  'bg-warning text-warning-foreground hover:bg-warning/90'
              )}
            >
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </TooltipProvider>
  );
}

// =============================================================================
// Compact Variant
// =============================================================================

export interface QuickActionsCompactProps {
  context: ActionContext;
  className?: string;
  maxActions?: number;
}

export function QuickActionsCompact({
  context,
  className,
  maxActions = 3,
}: QuickActionsCompactProps) {
  return (
    <QuickActionsBar
      context={context}
      className={className}
      position="inline"
      size="sm"
      maxPrimaryActions={maxActions}
    />
  );
}

// =============================================================================
// Floating Variant
// =============================================================================

export interface QuickActionsFloatingProps {
  context: ActionContext;
  className?: string;
}

export function QuickActionsFloating({
  context,
  className,
}: QuickActionsFloatingProps) {
  return (
    <QuickActionsBar
      context={context}
      className={className}
      position="floating"
      showLabels
    />
  );
}

// =============================================================================
// Toolbar Variant
// =============================================================================

export interface QuickActionsToolbarProps {
  context: ActionContext;
  className?: string;
}

export function QuickActionsToolbar({
  context,
  className,
}: QuickActionsToolbarProps) {
  return (
    <QuickActionsBar
      context={context}
      className={className}
      position="toolbar"
      maxPrimaryActions={6}
    />
  );
}

// =============================================================================
// Hook for keyboard shortcuts
// =============================================================================

export function useQuickActionShortcuts(context: ActionContext | null) {
  const { executeAction, getAvailableActions } = useQuickActionsStore();
  
  React.useEffect(() => {
    if (!context) return;
    
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if typing in an input
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.target instanceof HTMLSelectElement
      ) {
        return;
      }
      
      // Ignore if modifier keys are pressed (except for known combinations)
      if (event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }
      
      const actions = getAvailableActions();
      const key = event.key.toUpperCase();
      
      const matchingAction = actions.find(
        (action) => action.shortcut?.toUpperCase() === key
      );
      
      if (matchingAction) {
        event.preventDefault();
        executeAction(matchingAction.id, context);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [context, executeAction, getAvailableActions]);
}

export default QuickActionsBar;
