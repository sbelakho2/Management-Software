'use client';

import * as React from 'react';
import {
  Play,
  Send,
  CheckCircle,
  XCircle,
  Archive,
  Pause,
  RotateCcw,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
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
import { Textarea } from '@/components/ui/textarea';
import { useA3Store } from '@/stores/a3';
import { useToast } from '@/hooks/use-toast';
import { useI18n } from '@/contexts/i18n-context';

interface A3WorkflowActionsProps {
  a3Id: string;
  currentStatus: string;
  onStatusChange?: () => void;
}

type WorkflowAction = 'start' | 'submit_for_review' | 'approve' | 'reject' | 'implement' | 'close' | 'cancel';

const WORKFLOW_CONFIG: Record<string, {
  availableActions: WorkflowAction[];
  statusLabel: string;
  statusColor: string;
}> = {
  draft: {
    availableActions: ['start', 'cancel'],
    statusLabel: 'Draft',
    statusColor: 'bg-gray-500',
  },
  in_progress: {
    availableActions: ['submit_for_review', 'cancel'],
    statusLabel: 'In Progress',
    statusColor: 'bg-blue-500',
  },
  under_review: {
    availableActions: ['approve', 'reject'],
    statusLabel: 'Under Review',
    statusColor: 'bg-yellow-500',
  },
  approved: {
    availableActions: ['implement'],
    statusLabel: 'Approved',
    statusColor: 'bg-green-500',
  },
  implementing: {
    availableActions: ['close'],
    statusLabel: 'Implementing',
    statusColor: 'bg-purple-500',
  },
  rejected: {
    availableActions: ['start'],
    statusLabel: 'Rejected',
    statusColor: 'bg-red-500',
  },
  closed: {
    availableActions: [],
    statusLabel: 'Closed',
    statusColor: 'bg-gray-700',
  },
  cancelled: {
    availableActions: [],
    statusLabel: 'Cancelled',
    statusColor: 'bg-gray-400',
  },
};

const ACTION_CONFIG: Record<WorkflowAction, {
  label: string;
  icon: React.ReactNode;
  variant: 'default' | 'destructive' | 'outline' | 'secondary';
  requiresComment: boolean;
  confirmTitle: string;
  confirmDescription: string;
}> = {
  start: {
    label: 'Start A3',
    icon: <Play className="h-4 w-4" />,
    variant: 'default',
    requiresComment: false,
    confirmTitle: 'Start A3 Analysis?',
    confirmDescription: 'This will move the A3 to "In Progress" status. You can begin working on the analysis.',
  },
  submit_for_review: {
    label: 'Submit for Review',
    icon: <Send className="h-4 w-4" />,
    variant: 'default',
    requiresComment: false,
    confirmTitle: 'Submit for Review?',
    confirmDescription: 'This A3 will be submitted for review by your sponsor or coach. Make sure all sections are complete.',
  },
  approve: {
    label: 'Approve',
    icon: <CheckCircle className="h-4 w-4" />,
    variant: 'default',
    requiresComment: true,
    confirmTitle: 'Approve A3?',
    confirmDescription: 'Approving this A3 confirms the analysis is sound and countermeasures can be implemented.',
  },
  reject: {
    label: 'Request Changes',
    icon: <XCircle className="h-4 w-4" />,
    variant: 'destructive',
    requiresComment: true,
    confirmTitle: 'Request Changes?',
    confirmDescription: 'Please provide feedback on what needs to be improved before the A3 can be approved.',
  },
  implement: {
    label: 'Begin Implementation',
    icon: <RotateCcw className="h-4 w-4" />,
    variant: 'default',
    requiresComment: false,
    confirmTitle: 'Begin Implementation?',
    confirmDescription: 'This will mark the A3 as being implemented. Track progress through the implementation plan.',
  },
  close: {
    label: 'Close A3',
    icon: <Archive className="h-4 w-4" />,
    variant: 'secondary',
    requiresComment: true,
    confirmTitle: 'Close A3?',
    confirmDescription: 'Closing the A3 indicates implementation is complete. Please add any final notes or lessons learned.',
  },
  cancel: {
    label: 'Cancel A3',
    icon: <Pause className="h-4 w-4" />,
    variant: 'outline',
    requiresComment: true,
    confirmTitle: 'Cancel A3?',
    confirmDescription: 'Are you sure you want to cancel this A3? Please provide a reason for cancellation.',
  },
};

export function A3WorkflowActions({ a3Id, currentStatus, onStatusChange }: A3WorkflowActionsProps) {
  const { t } = useI18n();
  const { toast } = useToast();
  const { 
    updateA3,
    submitForReview, 
    approve, 
    reject,
  } = useA3Store();

  const [selectedAction, setSelectedAction] = React.useState<WorkflowAction | null>(null);
  const [comment, setComment] = React.useState('');
  const [isProcessing, setIsProcessing] = React.useState(false);

  const config = WORKFLOW_CONFIG[currentStatus] || WORKFLOW_CONFIG.draft;
  const actionConfig = selectedAction ? ACTION_CONFIG[selectedAction] : null;

  const handleAction = async () => {
    if (!selectedAction) return;

    setIsProcessing(true);
    try {
      switch (selectedAction) {
        case 'start':
          // Start: move from draft to in_progress
          await updateA3(a3Id, { status: 'in_progress' as any });
          break;
        case 'submit_for_review':
          await submitForReview(a3Id);
          break;
        case 'approve':
          await approve(a3Id, comment || undefined);
          break;
        case 'reject':
          await reject(a3Id, comment);
          break;
        case 'close':
          // Close: move to closed status
          await updateA3(a3Id, { status: 'closed' as any });
          break;
        case 'cancel':
          // Cancel: move to cancelled status
          await updateA3(a3Id, { status: 'cancelled' as any });
          break;
        case 'implement':
          // Implement: move to implemented status
          await updateA3(a3Id, { status: 'implemented' as any });
          break;
      }

      toast({
        title: 'Success',
        description: `A3 ${selectedAction.replace('_', ' ')} completed`,
      });

      onStatusChange?.();
    } catch (error) {
      toast({
        title: 'Error',
        description: `Failed to ${selectedAction.replace('_', ' ')} A3`,
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
      setSelectedAction(null);
      setComment('');
    }
  };

  if (config.availableActions.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Archive className="h-4 w-4" />
        <span>This A3 is {config.statusLabel.toLowerCase()} and no further actions are available.</span>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground mr-2">
          Workflow Actions:
        </span>
        {config.availableActions.map((action) => {
          const actionCfg = ACTION_CONFIG[action];
          return (
            <Button
              key={action}
              variant={actionCfg.variant}
              size="sm"
              className="gap-2"
              onClick={() => setSelectedAction(action)}
            >
              {actionCfg.icon}
              {actionCfg.label}
            </Button>
          );
        })}
      </div>

      <AlertDialog open={!!selectedAction} onOpenChange={(open) => !open && setSelectedAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              {actionConfig?.icon}
              {actionConfig?.confirmTitle}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {actionConfig?.confirmDescription}
            </AlertDialogDescription>
          </AlertDialogHeader>

          {actionConfig?.requiresComment && (
            <div className="py-4">
              <Textarea
                placeholder={
                  selectedAction === 'reject'
                    ? 'Please describe what needs to be improved...'
                    : selectedAction === 'cancel'
                    ? 'Please provide a reason for cancellation...'
                    : 'Add any notes or comments (optional)...'
                }
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={4}
              />
              {(selectedAction === 'reject' || selectedAction === 'cancel') && !comment && (
                <p className="text-xs text-destructive mt-2 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  A comment is required for this action
                </p>
              )}
            </div>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel disabled={isProcessing}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleAction}
              disabled={
                isProcessing ||
                ((selectedAction === 'reject' || selectedAction === 'cancel') && !comment)
              }
            >
              {isProcessing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Processing...
                </>
              ) : (
                'Confirm'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
