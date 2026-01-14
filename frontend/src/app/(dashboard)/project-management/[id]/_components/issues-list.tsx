'use client';

import * as React from 'react';
import { useProjectManagementStore, type Issue, type IssueType, type IssueSeverity, type IssuePriority, type IssueStatus } from '@/stores/project-management-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Plus, Search, AlertCircle, MessageSquare, Clock, User as UserIcon, Tag } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn, formatRelativeTime } from '@/lib/utils';
import { Separator } from '@/components/ui/separator';
import { Card, CardContent } from '@/components/ui/card';

interface IssuesListProps {
  projectId: string;
}

const typeIcons: Record<IssueType, React.ReactNode> = {
  bug: <AlertCircle className="h-4 w-4 text-red-500" />,
  improvement: <Plus className="h-4 w-4 text-blue-500" />,
  task: <Clock className="h-4 w-4 text-gray-500" />,
  question: <MessageSquare className="h-4 w-4 text-purple-500" />,
  incident: <AlertCircle className="h-4 w-4 text-orange-500" />,
  ncr: <AlertCircle className="h-4 w-4 text-yellow-600" />,
  safety: <AlertCircle className="h-4 w-4 text-red-600 font-bold" />,
};

const severityColors: Record<IssueSeverity, string> = {
  wishlist: 'bg-gray-100 text-gray-800',
  minor: 'bg-blue-100 text-blue-800',
  normal: 'bg-green-100 text-green-800',
  important: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
};

export function IssuesList({ projectId }: IssuesListProps) {
  const { 
    issues, fetchIssues, createIssue, updateIssue,
    commentsByIssueId, fetchIssueComments, createIssueComment,
    selectedProject
  } = useProjectManagementStore();
  
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedIssue, setSelectedIssue] = React.useState<Issue | null>(null);
  const [isSheetOpen, setIsSheetOpen] = React.useState(false);
  const [viewMode, setViewMode] = React.useState<'list' | 'create' | 'detail'>('list');
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // New Issue Form State
  const [newIssueSubject, setNewIssueSubject] = React.useState('');
  const [newIssueDescription, setNewIssueDescription] = React.useState('');
  const [newIssueType, setNewIssueType] = React.useState<IssueType>('bug');
  const [newIssueSeverity, setNewIssueSeverity] = React.useState<IssueSeverity>('normal');
  
  // Comment form state
  const [newCommentContent, setNewCommentContent] = React.useState('');

  React.useEffect(() => {
    if (projectId) {
      fetchIssues(projectId);
    }
  }, [projectId, fetchIssues]);

  const filteredIssues = issues.filter(i => 
    i.project_id === projectId && 
    (i.subject.toLowerCase().includes(searchQuery.toLowerCase()) || 
     i.ref.toString().includes(searchQuery))
  );

  const handleCreateIssue = async () => {
    if (!newIssueSubject.trim()) return;

    setIsSubmitting(true);
    try {
      await createIssue({
        project_id: projectId,
        subject: newIssueSubject,
        description: newIssueDescription || null,
        issue_type: newIssueType,
        severity: newIssueSeverity,
        status: 'new',
        priority: 'normal',
      });
      setNewIssueSubject('');
      setNewIssueDescription('');
      setViewMode('list');
      setIsSheetOpen(false);
    } catch (error) {
      console.error('Failed to create issue:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleIssueClick = async (issue: Issue) => {
    setSelectedIssue(issue);
    setViewMode('detail');
    setIsSheetOpen(true);
    fetchIssueComments(issue.id);
  };

  const handleUpdateIssue = async (updates: Partial<Issue>) => {
    if (!selectedIssue) return;
    try {
      const updated = await updateIssue(selectedIssue.id, updates);
      setSelectedIssue(updated);
    } catch (error) {
      console.error('Failed to update issue:', error);
    }
  };

  const handleAddComment = async () => {
    if (!selectedIssue || !newCommentContent.trim()) return;
    try {
      await createIssueComment(selectedIssue.id, newCommentContent);
      setNewCommentContent('');
    } catch (error) {
      console.error('Failed to add comment:', error);
    }
  };

  const currentComments = selectedIssue ? (commentsByIssueId[selectedIssue.id] || []) : [];

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Issues</h2>
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input 
              placeholder="Search issues..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 w-[250px]" 
            />
          </div>
          <Button onClick={() => { setViewMode('create'); setIsSheetOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" /> New Issue
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 h-[calc(100vh-200px)]">
        <div className="space-y-2 pr-4">
          {filteredIssues.length === 0 && (
            <div className="text-center py-10 border-2 border-dashed rounded-lg text-muted-foreground">
              No issues found.
            </div>
          )}
          {filteredIssues.map(issue => (
            <Card key={issue.id} className="hover:bg-accent/50 cursor-pointer transition-colors" onClick={() => handleIssueClick(issue)}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-1">{typeIcons[issue.issue_type]}</div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-muted-foreground">IS-{issue.ref}</span>
                        <h3 className="font-medium text-sm">{issue.subject}</h3>
                      </div>
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        <Badge variant="outline" className={cn("text-[10px] uppercase", severityColors[issue.severity])}>
                          {issue.severity}
                        </Badge>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" /> {formatRelativeTime(issue.created_at)}
                        </span>
                        <Badge className="capitalize text-[10px]">{issue.status.replace('_', ' ')}</Badge>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </ScrollArea>

      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent className="w-[500px] sm:max-w-[540px] overflow-y-auto">
          {viewMode === 'create' && (
            <>
              <SheetHeader>
                <SheetTitle>Create New Issue</SheetTitle>
                <SheetDescription>Report a bug, improvement, or other tracked item.</SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Subject *</label>
                  <Input 
                    placeholder="Brief summary of the issue"
                    value={newIssueSubject}
                    onChange={(e) => setNewIssueSubject(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Description</label>
                  <Textarea 
                    placeholder="Steps to reproduce, expected vs actual behavior..."
                    value={newIssueDescription}
                    onChange={(e) => setNewIssueDescription(e.target.value)}
                    rows={4}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Type</label>
                    <Select value={newIssueType} onValueChange={(v) => setNewIssueType(v as IssueType)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="bug">Bug</SelectItem>
                        <SelectItem value="improvement">Improvement</SelectItem>
                        <SelectItem value="task">Task</SelectItem>
                        <SelectItem value="question">Question</SelectItem>
                        <SelectItem value="incident">Incident</SelectItem>
                        <SelectItem value="ncr">NCR</SelectItem>
                        <SelectItem value="safety">Safety</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Severity</label>
                    <Select value={newIssueSeverity} onValueChange={(v) => setNewIssueSeverity(v as IssueSeverity)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="wishlist">Wishlist</SelectItem>
                        <SelectItem value="minor">Minor</SelectItem>
                        <SelectItem value="normal">Normal</SelectItem>
                        <SelectItem value="important">Important</SelectItem>
                        <SelectItem value="critical">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex justify-end gap-2 pt-4">
                  <Button variant="outline" onClick={() => setIsSheetOpen(false)}>Cancel</Button>
                  <Button onClick={handleCreateIssue} disabled={isSubmitting}>
                    {isSubmitting ? 'Creating...' : 'Create Issue'}
                  </Button>
                </div>
              </div>
            </>
          )}

          {viewMode === 'detail' && selectedIssue && (
            <>
              <SheetHeader>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline">IS-{selectedIssue.ref}</Badge>
                  <Badge className="capitalize">{selectedIssue.status.replace('_', ' ')}</Badge>
                </div>
                <SheetTitle className="text-xl">{selectedIssue.subject}</SheetTitle>
              </SheetHeader>
              
              <div className="mt-6 space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Status</label>
                    <Select 
                      defaultValue={selectedIssue.status} 
                      onValueChange={(v) => handleUpdateIssue({ status: v as IssueStatus })}
                    >
                      <SelectTrigger className="capitalize">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="new">New</SelectItem>
                        <SelectItem value="in_progress">In Progress</SelectItem>
                        <SelectItem value="ready_for_test">Ready for Test</SelectItem>
                        <SelectItem value="closed">Closed</SelectItem>
                        <SelectItem value="rejected">Rejected</SelectItem>
                        <SelectItem value="postponed">Postponed</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Severity</label>
                    <Select 
                      defaultValue={selectedIssue.severity}
                      onValueChange={(v) => handleUpdateIssue({ severity: v as IssueSeverity })}
                    >
                      <SelectTrigger className="capitalize">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="wishlist">Wishlist</SelectItem>
                        <SelectItem value="minor">Minor</SelectItem>
                        <SelectItem value="normal">Normal</SelectItem>
                        <SelectItem value="important">Important</SelectItem>
                        <SelectItem value="critical">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Description</label>
                  <Textarea 
                    placeholder="Add a description..."
                    defaultValue={selectedIssue.description ?? ''}
                    onBlur={(e) => handleUpdateIssue({ description: e.target.value })}
                    rows={4}
                  />
                </div>

                <Separator />

                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" />
                    <h3 className="font-medium">Comments</h3>
                    <Badge variant="secondary">{currentComments.length}</Badge>
                  </div>
                  
                  <div className="space-y-3">
                    {currentComments.map((comment) => (
                      <div key={comment.id} className="p-3 bg-secondary/30 rounded-md">
                        <p className="text-sm">{comment.content}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(comment.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    ))}
                    
                    <div className="flex items-start gap-2">
                      <Textarea 
                        placeholder="Add a comment..."
                        value={newCommentContent}
                        onChange={(e) => setNewCommentContent(e.target.value)}
                        rows={2}
                      />
                      <Button size="sm" onClick={handleAddComment}>
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
