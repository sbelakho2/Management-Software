'use client';

import * as React from 'react';
import {
  Settings,
  Shield,
  FileText,
  Users,
  GraduationCap,
  Flag,
  GitBranch,
  CheckCircle2,
  AlertCircle,
  Plus,
  Save,
  Trash2,
  Edit,
  Lock,
  Unlock,
  ChevronDown,
  Clock,
  Target,
  History,
} from 'lucide-react';
import { format } from 'date-fns';

const formatDate = (dateString: string) => {
  try {
    return format(new Date(dateString), 'MMM d, yyyy HH:mm');
  } catch {
    return dateString;
  }
};
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import { apiClient } from '@/api/client';
import { useAdminStore } from '@/stores/admin';
import {
  computeLineageLayout,
  makeNodeKey,
  type LineageEdge as LayoutLineageEdge,
  type LineageNode as LayoutLineageNode,
} from '@/lib/lineage-layout';

type ApiEnvelope<T> = {
  success: boolean;
  message?: string | null;
  data?: T | null;
  errors?: string[] | null;
};

type LineageGraph = {
  root_entity_type: string;
  root_entity_id: string;
  nodes: Array<{ entity_type: string; entity_id: string }>;
  edges: Array<{
    source_entity_type: string;
    source_entity_id: string;
    target_entity_type: string;
    target_entity_id: string;
    relationship_type: string;
  }>;
};

export default function AdminPage() {
  const [activeTab, setActiveTab] = React.useState('gates');

  // Store Hooks
  const {
    gates,
    approvals,
    templates,
    roles,
    learningCadences,
    featureFlags,
    auditLogs,
    isLoading,
    fetchGates,
    fetchApprovals,
    fetchTemplates,
    fetchRoles,
    fetchLearningCadences,
    fetchFeatureFlags,
    fetchAuditLogs,
    toggleGateStatus,
    toggleApprovalStatus,
    toggleLearningCadenceStatus,
    updateFeatureFlag,
    toggleFeatureFlag,
  } = useAdminStore();

  // Fetch data on mount
  React.useEffect(() => {
    fetchGates();
    fetchApprovals();
    fetchTemplates();
    fetchRoles();
    fetchLearningCadences();
    fetchFeatureFlags();
    fetchAuditLogs();
  }, []);

  // Lineage State
  const [lineageQuery, setLineageQuery] = React.useState({ entityType: '', entityId: '', maxDepth: 3 });
  const [lineageLoading, setLineageLoading] = React.useState(false);
  const [lineageError, setLineageError] = React.useState<string | null>(null);
  const [lineageGraph, setLineageGraph] = React.useState<LineageGraph | null>(null);

  // No local state for templates, roles, etc. - using store instead

  // Dialog States
  const [editGateDialog, setEditGateDialog] = React.useState(false);
  const [editApprovalDialog, setEditApprovalDialog] = React.useState(false);
  const [editTemplateDialog, setEditTemplateDialog] = React.useState(false);
  const [editRoleDialog, setEditRoleDialog] = React.useState(false);
  const [editLearningDialog, setEditLearningDialog] = React.useState(false);

  // Status Badge
  const StatusBadge = ({ status }: { status: 'active' | 'inactive' | boolean }) => {
    const isActive = status === 'active' || status === true;
    return (
      <Badge variant={isActive ? 'default' : 'secondary'} className="gap-1">
        {isActive ? <CheckCircle2 className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
        {isActive ? 'Active' : 'Inactive'}
      </Badge>
    );
  };

  return (
    <div className="space-y-6" data-testid="admin-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">System Administration</h1>
          <p className="text-muted-foreground">
            Configure gates, approvals, templates, roles, and system features
          </p>
        </div>
        <Button variant="outline" className="gap-2">
          <Save className="h-4 w-4" />
          Save All Changes
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-9">
          <TabsTrigger value="gates" className="gap-2">
            <Shield className="h-4 w-4" />
            Gates
          </TabsTrigger>
          <TabsTrigger value="approvals" className="gap-2">
            <CheckCircle2 className="h-4 w-4" />
            Approvals
          </TabsTrigger>
          <TabsTrigger value="templates" className="gap-2">
            <FileText className="h-4 w-4" />
            Templates
          </TabsTrigger>
          <TabsTrigger value="roles" className="gap-2">
            <Users className="h-4 w-4" />
            Roles
          </TabsTrigger>
          <TabsTrigger value="learning" className="gap-2">
            <GraduationCap className="h-4 w-4" />
            Learning
          </TabsTrigger>
          <TabsTrigger value="features" className="gap-2">
            <Flag className="h-4 w-4" />
            Features
          </TabsTrigger>
          <TabsTrigger value="lineage" className="gap-2">
            <GitBranch className="h-4 w-4" />
            Lineage
          </TabsTrigger>
          <TabsTrigger value="audit" className="gap-2">
            <History className="h-4 w-4" />
            Audit
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-2">
            <Lock className="h-4 w-4" />
            Security
          </TabsTrigger>
        </TabsList>

        {/* Lineage Tab */}
        <TabsContent value="lineage" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Data Lineage Graph</CardTitle>
              <CardDescription>
                Visualize entity-to-entity relationships from the Data Lineage Service.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <div className="space-y-1">
                  <Label>Entity Type</Label>
                  <Input
                    value={lineageQuery.entityType}
                    onChange={(e) => setLineageQuery((s) => ({ ...s, entityType: e.target.value }))}
                    placeholder="e.g., work_order"
                    data-testid="admin-lineage-entity-type"
                  />
                </div>
                <div className="space-y-1">
                  <Label>Entity ID</Label>
                  <Input
                    value={lineageQuery.entityId}
                    onChange={(e) => setLineageQuery((s) => ({ ...s, entityId: e.target.value }))}
                    placeholder="e.g., 123"
                    data-testid="admin-lineage-entity-id"
                  />
                </div>
                <div className="space-y-1">
                  <Label>Max Depth</Label>
                  <Input
                    type="number"
                    min={0}
                    max={10}
                    value={lineageQuery.maxDepth}
                    onChange={(e) => setLineageQuery((s) => ({ ...s, maxDepth: Number(e.target.value || 0) }))}
                    data-testid="admin-lineage-max-depth"
                  />
                </div>
                <div className="flex items-end">
                  <Button
                    className="w-full"
                    onClick={async () => {
                      const entityType = lineageQuery.entityType.trim();
                      const entityId = lineageQuery.entityId.trim();
                      if (!entityType || !entityId) {
                        setLineageError('Entity type and entity id are required.');
                        return;
                      }

                      setLineageError(null);
                      setLineageLoading(true);
                      try {
                        const res = await apiClient.get<ApiEnvelope<LineageGraph>>(
                          `/data-lineage/graph?entity_type=${encodeURIComponent(entityType)}&entity_id=${encodeURIComponent(entityId)}&max_depth=${encodeURIComponent(String(lineageQuery.maxDepth))}`
                        );
                        if (!res.success || !res.data) {
                          setLineageGraph(null);
                          setLineageError(res.message || 'Failed to load lineage graph');
                          return;
                        }
                        setLineageGraph(res.data);
                      } catch (e) {
                        setLineageGraph(null);
                        setLineageError(e instanceof Error ? e.message : 'Failed to load lineage graph');
                      } finally {
                        setLineageLoading(false);
                      }
                    }}
                    disabled={lineageLoading}
                    data-testid="admin-lineage-load"
                  >
                    {lineageLoading ? 'Loading…' : 'Load Graph'}
                  </Button>
                </div>
              </div>

              {lineageError ? (
                <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm">
                  <AlertCircle className="mt-0.5 h-4 w-4 text-destructive" />
                  <div className="text-destructive">{lineageError}</div>
                </div>
              ) : null}

              {lineageGraph ? (
                (() => {
                  const nodes: LayoutLineageNode[] = lineageGraph.nodes.map((n) => ({
                    entity_type: n.entity_type,
                    entity_id: n.entity_id,
                  }));
                  const edges: LayoutLineageEdge[] = lineageGraph.edges.map((e) => ({
                    source_entity_type: e.source_entity_type,
                    source_entity_id: e.source_entity_id,
                    target_entity_type: e.target_entity_type,
                    target_entity_id: e.target_entity_id,
                    relationship_type: e.relationship_type,
                  }));

                  const layout = computeLineageLayout({
                    rootEntityType: lineageGraph.root_entity_type,
                    rootEntityId: lineageGraph.root_entity_id,
                    nodes,
                    edges,
                    maxDepth: lineageQuery.maxDepth,
                  });

                  const nodeBox = { w: 190, h: 56 };
                  const byKey = new Map(layout.nodes.map((n) => [n.key, n] as const));

                  return (
                    <div className="rounded-md border">
                      <div className="border-b p-3 text-sm text-muted-foreground">
                        Root: <span className="font-medium text-foreground">{lineageGraph.root_entity_type}:{lineageGraph.root_entity_id}</span> • Nodes: {layout.nodes.length} • Edges: {lineageGraph.edges.length}
                      </div>
                      <div className="max-h-[520px] overflow-auto p-3">
                        <div className="relative" style={{ width: layout.width, height: layout.height }}>
                          <svg className="absolute inset-0" width={layout.width} height={layout.height}>
                            {edges.map((e, idx) => {
                              const srcKey = makeNodeKey(e.source_entity_type, e.source_entity_id);
                              const dstKey = makeNodeKey(e.target_entity_type, e.target_entity_id);
                              const src = byKey.get(srcKey);
                              const dst = byKey.get(dstKey);
                              if (!src || !dst) return null;
                              const x1 = src.x + nodeBox.w / 2;
                              const y1 = src.y + nodeBox.h / 2;
                              const x2 = dst.x + nodeBox.w / 2;
                              const y2 = dst.y + nodeBox.h / 2;
                              return (
                                <line
                                  key={`${idx}-${srcKey}-${dstKey}`}
                                  x1={x1}
                                  y1={y1}
                                  x2={x2}
                                  y2={y2}
                                  stroke="currentColor"
                                  className="text-muted-foreground"
                                  strokeWidth={1}
                                />
                              );
                            })}
                          </svg>

                          {layout.nodes.map((n) => (
                            <div
                              key={n.key}
                              className="absolute rounded-md border bg-background p-2"
                              style={{ left: n.x, top: n.y, width: nodeBox.w, height: nodeBox.h }}
                              data-testid={`admin-lineage-node-${n.key}`}
                            >
                              <div className="text-xs text-muted-foreground">Depth {n.depth}</div>
                              <div className="truncate text-sm font-medium">{n.entity_type}</div>
                              <div className="truncate text-xs text-muted-foreground">{n.entity_id}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })()
              ) : (
                <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
                  Enter an entity type/id and load a graph.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Gates Tab */}
        <TabsContent value="gates" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Quality Gates Configuration</CardTitle>
                  <CardDescription>
                    Define approval gates and conditions for critical workflows
                  </CardDescription>
                </div>
                <Button className="gap-2" onClick={() => setEditGateDialog(true)}>
                  <Plus className="h-4 w-4" />
                  Add Gate
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">Order</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Phase</TableHead>
                    <TableHead>Required Approvers</TableHead>
                    <TableHead>Bypass Roles</TableHead>
                    <TableHead>Conditions</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {gates.map((gate) => (
                    <TableRow key={gate.id}>
                      <TableCell className="font-medium">{gate.order}</TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{gate.name}</div>
                          <div className="text-xs text-muted-foreground">{gate.description}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{gate.phase}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Users className="h-3 w-3 text-muted-foreground" />
                          {gate.required_approvers}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {gate.bypass_roles.map((role) => (
                            <Badge key={role} variant="secondary" className="text-xs">
                              {role}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs text-muted-foreground">
                          {gate.conditions.length} condition{gate.conditions.length !== 1 ? 's' : ''}
                        </div>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={gate.status} />
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <ChevronDown className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Edit className="mr-2 h-4 w-4" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              {gate.status === 'active' ? (
                                <>
                                  <Lock className="mr-2 h-4 w-4" />
                                  Deactivate
                                </>
                              ) : (
                                <>
                                  <Unlock className="mr-2 h-4 w-4" />
                                  Activate
                                </>
                              )}
                            </DropdownMenuItem>
                            <DropdownMenuItem className="text-destructive">
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Approvals Tab */}
        <TabsContent value="approvals" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Approval Workflows</CardTitle>
                  <CardDescription>
                    Configure approval chains, thresholds, and escalations
                  </CardDescription>
                </div>
                <Button className="gap-2" onClick={() => setEditApprovalDialog(true)}>
                  <Plus className="h-4 w-4" />
                  Add Workflow
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Threshold</TableHead>
                    <TableHead>Required Roles</TableHead>
                    <TableHead>Sequence</TableHead>
                    <TableHead>Timeout</TableHead>
                    <TableHead>Auto-Escalate</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {approvals.map((approval) => (
                    <TableRow key={approval.id}>
                      <TableCell>
                        <Badge variant="outline">{approval.type}</Badge>
                      </TableCell>
                      <TableCell className="font-medium">{approval.name}</TableCell>
                      <TableCell>
                        {approval.threshold_amount ? `$${approval.threshold_amount.toLocaleString()}` : 'All'}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {approval.required_roles.map((role) => (
                            <Badge key={role} variant="secondary" className="text-xs">
                              {role}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={approval.sequence_required ? 'default' : 'outline'}>
                          {approval.sequence_required ? 'Sequential' : 'Parallel'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm">
                          <Clock className="h-3 w-3 text-muted-foreground" />
                          {approval.timeout_hours}h
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={approval.auto_escalate ? 'default' : 'secondary'}>
                          {approval.auto_escalate ? 'Yes' : 'No'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={approval.is_active} />
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <ChevronDown className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Edit className="mr-2 h-4 w-4" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              {approval.is_active ? 'Deactivate' : 'Activate'}
                            </DropdownMenuItem>
                            <DropdownMenuItem className="text-destructive">
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {templates.map((template) => (
              <Card key={template.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <Badge variant="outline">{template.type}</Badge>
                    {template.is_default && (
                      <Badge variant="default" className="text-xs">
                        Default
                      </Badge>
                    )}
                  </div>
                  <CardTitle className="text-lg">{template.name}</CardTitle>
                  <CardDescription>{template.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {template.sections && (
                    <div>
                      <div className="text-xs font-medium text-muted-foreground mb-1">
                        Sections ({template.sections.length})
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {template.sections.slice(0, 3).map((section, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">
                            {section}
                          </Badge>
                        ))}
                        {template.sections.length > 3 && (
                          <Badge variant="secondary" className="text-xs">
                            +{template.sections.length - 3} more
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1">
                      Variables ({template.variables.length})
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {template.variables.slice(0, 3).map((variable, idx) => (
                        <code key={idx} className="text-xs bg-muted px-1 py-0.5 rounded">
                          {variable}
                        </code>
                      ))}
                      {template.variables.length > 3 && (
                        <Badge variant="secondary" className="text-xs">
                          +{template.variables.length - 3}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="pt-2 text-xs text-muted-foreground">
                    Modified {template.updated_at} by {template.created_by}
                  </div>
                  <div className="flex gap-2 pt-2">
                    <Button variant="outline" size="sm" className="flex-1 gap-1">
                      <Edit className="h-3 w-3" />
                      Edit
                    </Button>
                    <Button variant="outline" size="sm" className="flex-1 gap-1">
                      <FileText className="h-3 w-3" />
                      Preview
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <Button className="w-full gap-2" onClick={() => setEditTemplateDialog(true)}>
            <Plus className="h-4 w-4" />
            Create New Template
          </Button>
        </TabsContent>

        {/* Roles Tab */}
        <TabsContent value="roles" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Role & Permission Management</CardTitle>
                  <CardDescription>
                    Define roles, permissions, and hierarchy levels
                  </CardDescription>
                </div>
                <Button className="gap-2" onClick={() => setEditRoleDialog(true)}>
                  <Plus className="h-4 w-4" />
                  Add Role
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Level</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Members</TableHead>
                    <TableHead>Permissions</TableHead>
                    <TableHead>Can Approve</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {roles
                    .sort((a, b) => b.hierarchy_level - a.hierarchy_level)
                    .map((role) => (
                      <TableRow key={role.id}>
                        <TableCell>
                          <Badge variant="outline">L{role.hierarchy_level}</Badge>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{role.display_name}</div>
                            <div className="text-xs text-muted-foreground">{role.name}</div>
                          </div>
                        </TableCell>
                        <TableCell className="max-w-xs">
                          <div className="text-sm text-muted-foreground truncate">
                            {role.description}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Users className="h-3 w-3 text-muted-foreground" />
                            {role.member_count}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {role.permissions.slice(0, 2).map((perm, idx) => (
                              <Badge key={idx} variant="secondary" className="text-xs">
                                {perm}
                              </Badge>
                            ))}
                            {role.permissions.length > 2 && (
                              <Badge variant="secondary" className="text-xs">
                                +{role.permissions.length - 2}
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={role.can_approve ? 'default' : 'secondary'}>
                            {role.can_approve ? 'Yes' : 'No'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="sm">
                                <ChevronDown className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem>
                                <Edit className="mr-2 h-4 w-4" />
                                Edit Permissions
                              </DropdownMenuItem>
                              <DropdownMenuItem>
                                <Users className="mr-2 h-4 w-4" />
                                View Members
                              </DropdownMenuItem>
                              {role.hierarchy_level < 4 && (
                                <DropdownMenuItem className="text-destructive">
                                  <Trash2 className="mr-2 h-4 w-4" />
                                  Delete
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Learning Tab */}
        <TabsContent value="learning" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Learning Cadence Configuration</CardTitle>
                  <CardDescription>
                    Define recurring learning sessions and micro-lessons
                  </CardDescription>
                </div>
                <Button className="gap-2" onClick={() => setEditLearningDialog(true)}>
                  <Plus className="h-4 w-4" />
                  Add Cadence
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Frequency</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Target Roles</TableHead>
                    <TableHead>Topics</TableHead>
                    <TableHead>Mandatory</TableHead>
                    <TableHead>Reminder</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {learningCadences.map((cadence) => (
                    <TableRow key={cadence.id}>
                      <TableCell className="font-medium">{cadence.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {cadence.frequency}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm">
                          <Clock className="h-3 w-3 text-muted-foreground" />
                          {cadence.duration_minutes} min
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {cadence.target_roles.slice(0, 2).map((role) => (
                            <Badge key={role} variant="secondary" className="text-xs">
                              {role}
                            </Badge>
                          ))}
                          {cadence.target_roles.length > 2 && (
                            <Badge variant="secondary" className="text-xs">
                              +{cadence.target_roles.length - 2}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs text-muted-foreground">
                          {cadence.topics.length} topic{cadence.topics.length !== 1 ? 's' : ''}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={cadence.mandatory ? 'destructive' : 'secondary'}>
                          {cadence.mandatory ? 'Required' : 'Optional'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {cadence.reminder_days_before}d before
                        </div>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={cadence.is_active} />
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <ChevronDown className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Edit className="mr-2 h-4 w-4" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              {cadence.is_active ? 'Deactivate' : 'Activate'}
                            </DropdownMenuItem>
                            <DropdownMenuItem className="text-destructive">
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Features Tab */}
        <TabsContent value="features" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Feature Flags Management</CardTitle>
              <CardDescription>
                Enable or disable features, experiments, and emergency killswitches
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {['feature', 'experiment', 'killswitch'].map((category) => (
                <div key={category}>
                  <h3 className="text-sm font-semibold mb-3 capitalize flex items-center gap-2">
                    {category === 'killswitch' ? (
                      <AlertCircle className="h-4 w-4 text-destructive" />
                    ) : (
                      <Flag className="h-4 w-4" />
                    )}
                    {category === 'killswitch' ? 'Emergency Kill Switches' : `${category}s`}
                  </h3>
                  <div className="space-y-2">
                    {featureFlags
                      .filter((flag) => flag.category === category)
                      .map((flag) => (
                        <Card key={flag.id} className={flag.enabled && category === 'killswitch' ? 'border-destructive' : ''}>
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 space-y-2">
                                <div className="flex items-center gap-2">
                                  <code className="text-xs bg-muted px-2 py-1 rounded">
                                    {flag.key}
                                  </code>
                                  {flag.requires_restart && (
                                    <Badge variant="outline" className="text-xs">
                                      Requires Restart
                                    </Badge>
                                  )}
                                </div>
                                <div>
                                  <div className="font-medium">{flag.name}</div>
                                  <div className="text-sm text-muted-foreground">
                                    {flag.description}
                                  </div>
                                </div>
                                {flag.target_roles && (
                                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                    <Target className="h-3 w-3" />
                                    Target:{' '}
                                    {flag.target_roles.map((role) => (
                                      <Badge key={role} variant="secondary" className="text-xs">
                                        {role}
                                      </Badge>
                                    ))}
                                  </div>
                                )}
                                {flag.rollout_percentage < 100 && (
                                  <div className="flex items-center gap-2">
                                    <div className="text-xs text-muted-foreground">
                                      Rollout: {flag.rollout_percentage}%
                                    </div>
                                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden max-w-xs">
                                      <div
                                        className="h-full bg-primary"
                                        style={{ width: `${flag.rollout_percentage}%` }}
                                      />
                                    </div>
                                  </div>
                                )}
                              </div>
                              <div className="flex items-center gap-3">
                                <Switch
                                  checked={flag.enabled}
                                  onCheckedChange={() => {
                                    toggleFeatureFlag(flag.id);
                                  }}
                                />
                                <Button variant="ghost" size="sm">
                                  <Edit className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Tab */}
        <TabsContent value="audit" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>System Audit Log</CardTitle>
              <CardDescription>
                Track system changes, user logins, and critical actions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Entity</TableHead>
                    <TableHead>Changes</TableHead>
                    <TableHead>IP Address</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditLogs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="text-xs font-mono">{formatDate(log.created_at)}</TableCell>
                      <TableCell>{log.user_email}</TableCell>
                      <TableCell>
                        <Badge variant={log.action === 'CREATE' ? 'default' : log.action === 'UPDATE' ? 'outline' : 'secondary'}>
                          {log.action}
                        </Badge>
                      </TableCell>
                      <TableCell>{log.entity_type}</TableCell>
                      <TableCell className="text-sm">
                        {typeof log.extra_data === 'string' ? log.extra_data : JSON.stringify(log.extra_data)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{log.ip_address || 'N/A'}</TableCell>
                    </TableRow>
                  ))}
                  {auditLogs.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                        No audit logs found.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Single Sign-On (SSO)</CardTitle>
                <CardDescription>Configure enterprise authentication providers</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>SAML 2.0 Integration</Label>
                    <p className="text-xs text-muted-foreground">Enable SSO via Okta, Azure AD, or Ping</p>
                  </div>
                  <Switch />
                </div>
                <div className="space-y-2">
                  <Label>Identity Provider URL</Label>
                  <Input placeholder="https://sso.yourcompany.com/..." />
                </div>
                <div className="space-y-2">
                  <Label>Service Provider Metadata</Label>
                  <div className="p-2 bg-muted rounded border text-xs font-mono overflow-auto max-h-32">
                    {`<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="https://sensei.starzm.com/saml">
  <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    ...
  </md:SPSSODescriptor>
</md:EntityDescriptor>`}
                  </div>
                </div>
                <Button variant="outline" className="w-full">Download Metadata XML</Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Security Hardening</CardTitle>
                <CardDescription>Session and multi-factor authentication policies</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Enforce 2FA</Label>
                    <p className="text-xs text-muted-foreground">Require TOTP for all users</p>
                  </div>
                  <Switch checked={true} />
                </div>
                <div className="space-y-2">
                  <Label>Session Timeout (Minutes)</Label>
                  <Input type="number" defaultValue={60} />
                </div>
                <div className="space-y-2">
                  <Label>IP Access Control</Label>
                  <Textarea placeholder="Allowlist IPs (one per line)" />
                </div>
                <Button className="w-full">Update Security Policies</Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
