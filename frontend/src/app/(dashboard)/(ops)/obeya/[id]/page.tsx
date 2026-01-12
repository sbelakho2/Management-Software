'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Edit,
  Trash2,
  Plus,
  MessageSquare,
  User,
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle,
  Flag,
  TrendingUp,
  FileText,
  Link as LinkIcon,
  Paperclip,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

type ObeyaCategory = 
  | 'issue' | 'action' | 'risk' | 'decision' | 'milestone' 
  | 'kpi' | 'escalation' | 'information' | 'lesson_learned'
  | 'metrics' | 'schedule' | 'quality' | 'cost' | 'safety' 
  | 'morale' | 'delivery' | 'strategy';

type ObeyaStatus = 'new' | 'in_progress' | 'blocked' | 'waiting' | 'completed' | 'cancelled';
type ObeyaPriority = 'low' | 'medium' | 'high' | 'critical';

interface ObeyaComment {
  id: string;
  item_id: string;
  author_id: string;
  author_name: string;
  content: string;
  parent_id?: string;
  is_status_change: boolean;
  old_status?: string;
  new_status?: string;
  is_pinned: boolean;
  is_edited: boolean;
  edited_at?: string;
  mentions?: string[];
  attachments?: any[];
  created_at: string;
}

interface ObeyaItem {
  id: string;
  board: string;
  column?: string;
  position: number;
  title: string;
  description?: string;
  category: ObeyaCategory;
  status: ObeyaStatus;
  priority: ObeyaPriority;
  color?: string;
  assigned_to_id?: string;
  assigned_to_name?: string;
  due_date?: string;
  target_date?: string;
  completed_at?: string;
  blocked_reason?: string;
  resolution?: string;
  decision_outcome?: string;
  decision_rationale?: string;
  kpi_target?: string;
  kpi_actual?: string;
  kpi_unit?: string;
  kpi_trend?: 'improving' | 'stable' | 'declining';
  is_escalated: boolean;
  escalated_to_id?: string;
  escalated_to_name?: string;
  escalated_at?: string;
  escalation_reason?: string;
  days_open?: number;
  days_overdue?: number;
  attachments?: any[];
  links?: any[];
  tags?: string[];
  meeting_date?: string;
  meeting_type?: string;
  notes?: string;
  comments_count: number;
  created_at: string;
  updated_at: string;
  created_by_id: string;
  created_by_name: string;
}

const statusBadgeVariant: Record<ObeyaStatus, 'default' | 'secondary' | 'warning' | 'destructive' | 'success'> = {
  new: 'secondary',
  in_progress: 'default',
  blocked: 'destructive',
  waiting: 'warning',
  completed: 'success',
  cancelled: 'secondary',
};

const priorityBadgeVariant: Record<ObeyaPriority, 'default' | 'secondary' | 'warning' | 'destructive'> = {
  low: 'secondary',
  medium: 'default',
  high: 'warning',
  critical: 'destructive',
};

export default function ObeyaItemDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [item, setItem] = useState<ObeyaItem | null>(null);
  const [comments, setComments] = useState<ObeyaComment[]>([]);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showCommentDialog, setShowCommentDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isAddingComment, setIsAddingComment] = useState(false);
  const [commentText, setCommentText] = useState('');

  useEffect(() => {
    fetchItem();
    fetchComments();
  }, [params.id]);

  const fetchItem = async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call
      // const response = await fetch(`/api/v1/obeya/items/${params.id}`);
      // const data = await response.json();
      // setItem(data);

      // Mock data
      setTimeout(() => {
        setItem({
          id: params.id as string,
          board: 'daily',
          column: 'in_progress',
          position: 1,
          title: 'CMM inspection program update for bracket tolerances',
          description: 'Need to update the CMM inspection program to accommodate new tolerance requirements from engineering change order ECO-2024-089. Current program does not properly measure the revised mounting hole positions.',
          category: 'action',
          status: 'in_progress',
          priority: 'high',
          color: 'yellow',
          assigned_to_id: 'user-1',
          assigned_to_name: 'John Smith',
          due_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
          target_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
          days_open: 5,
          days_overdue: 0,
          is_escalated: false,
          tags: ['CMM', 'inspection', 'tolerance', 'ECO'],
          meeting_date: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
          meeting_type: 'daily',
          notes: 'Discussed with engineering team. Need to coordinate with quality manager before implementation.',
          comments_count: 3,
          attachments: [
            { id: 'att-1', name: 'ECO-2024-089.pdf', size: 245678 },
            { id: 'att-2', name: 'current_inspection_program.txt', size: 12345 },
          ],
          links: [
            { id: 'link-1', url: 'https://example.com/eco/2024-089', title: 'ECO-2024-089 Details' },
          ],
          created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
          created_by_id: 'user-1',
          created_by_name: 'John Smith',
        });
        setIsLoading(false);
      }, 500);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch Obeya item details',
        variant: 'destructive',
      });
      setIsLoading(false);
    }
  };

  const fetchComments = async () => {
    try {
      // TODO: Replace with actual API call
      // const response = await fetch(`/api/v1/obeya/items/${params.id}/comments`);
      // const data = await response.json();
      // setComments(data);

      // Mock data
      setTimeout(() => {
        setComments([
          {
            id: 'c1',
            item_id: params.id as string,
            author_id: 'user-1',
            author_name: 'John Smith',
            content: 'Started working on this. Will have initial draft ready by EOD tomorrow.',
            is_status_change: true,
            old_status: 'new',
            new_status: 'in_progress',
            is_pinned: false,
            is_edited: false,
            created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
          },
          {
            id: 'c2',
            item_id: params.id as string,
            author_id: 'user-2',
            author_name: 'Sarah Johnson',
            content: 'Please make sure to review the latest ECO revision before updating the program. There were some changes to the tolerance stack-up analysis.',
            is_status_change: false,
            is_pinned: true,
            is_edited: false,
            created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
          },
          {
            id: 'c3',
            item_id: params.id as string,
            author_id: 'user-1',
            author_name: 'John Smith',
            content: 'Good catch @Sarah. I will coordinate with engineering to get the final rev before I finalize the program.',
            is_status_change: false,
            is_pinned: false,
            is_edited: false,
            mentions: ['user-2'],
            created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
          },
        ]);
      }, 300);
    } catch (error) {
      console.error('Failed to fetch comments:', error);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/obeya/items/${params.id}`, { method: 'DELETE' });

      setTimeout(() => {
        toast({
          title: 'Success',
          description: 'Obeya item deleted successfully',
        });
        router.push('/obeya');
      }, 500);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete Obeya item',
        variant: 'destructive',
      });
      setIsDeleting(false);
    }
  };

  const handleAddComment = async () => {
    if (!commentText.trim()) return;

    setIsAddingComment(true);
    try {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/obeya/items/${params.id}/comments`, {
      //   method: 'POST',
      //   body: JSON.stringify({ content: commentText }),
      // });

      setTimeout(() => {
        toast({
          title: 'Success',
          description: 'Comment added successfully',
        });
        setShowCommentDialog(false);
        setCommentText('');
        fetchComments();
        setIsAddingComment(false);
      }, 500);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to add comment',
        variant: 'destructive',
      });
      setIsAddingComment(false);
    }
  };

  const formatRelativeTime = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-96" />
            <Skeleton className="h-4 w-64" />
          </div>
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!item) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] space-y-4">
        <FileText className="h-16 w-16 text-muted-foreground" />
        <div className="text-center">
          <h2 className="text-2xl font-bold">Item Not Found</h2>
          <p className="text-muted-foreground mt-2">
            The Obeya item you're looking for doesn't exist or has been deleted.
          </p>
        </div>
        <Button onClick={() => router.push('/obeya')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Obeya Board
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push('/obeya')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{item.title}</h1>
              {item.is_escalated && (
                <Badge variant="destructive" className="gap-1">
                  <Flag className="h-3 w-3" />
                  Escalated
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={statusBadgeVariant[item.status]}>
                {item.status.replace('_', ' ')}
              </Badge>
              <Badge variant={priorityBadgeVariant[item.priority]}>
                {item.priority}
              </Badge>
              <Badge variant="outline">
                {item.category.replace('_', ' ')}
              </Badge>
              {item.tags?.map(tag => (
                <Badge key={tag} variant="secondary">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => router.push(`/obeya/${params.id}/edit`)}>
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button variant="destructive" onClick={() => setShowDeleteDialog(true)}>
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Status Alerts */}
      {item.days_overdue && item.days_overdue > 0 && (
        <Card className="border-destructive bg-destructive/5">
          <CardContent className="pt-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium">Overdue by {item.days_overdue} days</p>
              <p className="text-sm text-muted-foreground">
                Due date was {new Date(item.due_date!).toLocaleDateString()}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {item.status === 'blocked' && item.blocked_reason && (
        <Card className="border-warning bg-warning/5">
          <CardContent className="pt-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            <div>
              <p className="font-medium">Blocked</p>
              <p className="text-sm text-muted-foreground">{item.blocked_reason}</p>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        {/* Main Content */}
        <div className="md:col-span-2 space-y-6">
          {/* Description */}
          <Card>
            <CardHeader>
              <CardTitle>Description</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {item.description || 'No description provided.'}
              </p>
            </CardContent>
          </Card>

          {/* KPI Details (if applicable) */}
          {item.category === 'kpi' && (
            <Card>
              <CardHeader>
                <CardTitle>KPI Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-sm font-medium">Target</Label>
                    <p className="text-2xl font-bold">
                      {item.kpi_target} {item.kpi_unit}
                    </p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Actual</Label>
                    <p className="text-2xl font-bold">
                      {item.kpi_actual} {item.kpi_unit}
                    </p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Trend</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <TrendingUp className={cn(
                        'h-5 w-5',
                        item.kpi_trend === 'improving' ? 'text-success' :
                        item.kpi_trend === 'declining' ? 'text-destructive' :
                        'text-muted-foreground'
                      )} />
                      <span className="capitalize">{item.kpi_trend}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Decision Details (if applicable) */}
          {item.category === 'decision' && item.decision_outcome && (
            <Card>
              <CardHeader>
                <CardTitle>Decision Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="text-sm font-medium">Outcome</Label>
                  <p className="text-sm text-muted-foreground mt-1">{item.decision_outcome}</p>
                </div>
                {item.decision_rationale && (
                  <div>
                    <Label className="text-sm font-medium">Rationale</Label>
                    <p className="text-sm text-muted-foreground mt-1">{item.decision_rationale}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Resolution (if completed) */}
          {item.status === 'completed' && item.resolution && (
            <Card className="border-success bg-success/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-success" />
                  Resolution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{item.resolution}</p>
              </CardContent>
            </Card>
          )}

          {/* Attachments */}
          {item.attachments && item.attachments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Paperclip className="h-4 w-4" />
                  Attachments ({item.attachments.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {item.attachments.map((file: any) => (
                  <div key={file.id} className="flex items-center justify-between p-2 border rounded hover:bg-muted/50">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">{file.name}</p>
                        <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">Download</Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Links */}
          {item.links && item.links.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LinkIcon className="h-4 w-4" />
                  Related Links ({item.links.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {item.links.map((link: any) => (
                  <a
                    key={link.id}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 p-2 border rounded hover:bg-muted/50 text-primary hover:underline"
                  >
                    <LinkIcon className="h-4 w-4" />
                    <span className="text-sm">{link.title || link.url}</span>
                  </a>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Comments */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Discussion ({comments.length})
                </CardTitle>
                <Button onClick={() => setShowCommentDialog(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Comment
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {comments.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  No comments yet. Start the discussion!
                </p>
              ) : (
                comments.map((comment) => (
                  <div key={comment.id} className="space-y-2">
                    <div className="flex items-start gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">{comment.author_name}</span>
                          <span className="text-xs text-muted-foreground">
                            {formatRelativeTime(comment.created_at)}
                          </span>
                          {comment.is_pinned && (
                            <Badge variant="secondary" className="text-xs">Pinned</Badge>
                          )}
                          {comment.is_status_change && (
                            <Badge variant="outline" className="text-xs">
                              Status: {comment.old_status} → {comment.new_status}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">
                          {comment.content}
                        </p>
                      </div>
                    </div>
                    {comment !== comments[comments.length - 1] && <Separator />}
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Notes */}
          {item.notes && (
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{item.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Assignment & Dates */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {item.assigned_to_name && (
                <div>
                  <Label className="text-sm font-medium flex items-center gap-2">
                    <User className="h-4 w-4" />
                    Assigned To
                  </Label>
                  <p className="text-sm mt-1">{item.assigned_to_name}</p>
                </div>
              )}
              {item.due_date && (
                <div>
                  <Label className="text-sm font-medium flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Due Date
                  </Label>
                  <p className="text-sm mt-1">
                    {new Date(item.due_date).toLocaleDateString()}
                  </p>
                </div>
              )}
              {item.target_date && (
                <div>
                  <Label className="text-sm font-medium flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Target Date
                  </Label>
                  <p className="text-sm mt-1">
                    {new Date(item.target_date).toLocaleDateString()}
                  </p>
                </div>
              )}
              <Separator />
              <div>
                <Label className="text-sm font-medium flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Days Open
                </Label>
                <p className="text-sm mt-1">{item.days_open} days</p>
              </div>
              {item.meeting_date && (
                <div>
                  <Label className="text-sm font-medium flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Meeting
                  </Label>
                  <p className="text-sm mt-1">
                    {new Date(item.meeting_date).toLocaleDateString()}
                  </p>
                  {item.meeting_type && (
                    <Badge variant="outline" size="sm" className="mt-1 capitalize">
                      {item.meeting_type}
                    </Badge>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Escalation Info */}
          {item.is_escalated && (
            <Card className="border-destructive">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Flag className="h-4 w-4" />
                  Escalation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {item.escalated_to_name && (
                  <div>
                    <Label className="text-sm font-medium">Escalated To</Label>
                    <p className="text-sm mt-1">{item.escalated_to_name}</p>
                  </div>
                )}
                {item.escalated_at && (
                  <div>
                    <Label className="text-sm font-medium">Escalated On</Label>
                    <p className="text-sm mt-1">
                      {new Date(item.escalated_at).toLocaleDateString()}
                    </p>
                  </div>
                )}
                {item.escalation_reason && (
                  <div>
                    <Label className="text-sm font-medium">Reason</Label>
                    <p className="text-sm text-muted-foreground mt-1">
                      {item.escalation_reason}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Metadata */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-xs text-muted-foreground">
              <div>
                <Label className="text-xs font-medium">Created</Label>
                <p className="mt-1">{new Date(item.created_at).toLocaleString()}</p>
                <p className="mt-1">by {item.created_by_name}</p>
              </div>
              <div>
                <Label className="text-xs font-medium">Last Updated</Label>
                <p className="mt-1">{new Date(item.updated_at).toLocaleString()}</p>
              </div>
              <div>
                <Label className="text-xs font-medium">Board</Label>
                <p className="mt-1 capitalize">{item.board}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Obeya Item</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this item? This action cannot be undone and will also delete all comments.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? 'Deleting...' : 'Delete Item'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Comment Dialog */}
      <Dialog open={showCommentDialog} onOpenChange={setShowCommentDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Comment</DialogTitle>
            <DialogDescription>
              Share updates, ask questions, or provide feedback on this item.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="comment">Comment</Label>
              <Textarea
                id="comment"
                placeholder="Write your comment here..."
                rows={5}
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCommentDialog(false)} disabled={isAddingComment}>
              Cancel
            </Button>
            <Button onClick={handleAddComment} disabled={isAddingComment || !commentText.trim()}>
              {isAddingComment ? 'Adding...' : 'Add Comment'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
