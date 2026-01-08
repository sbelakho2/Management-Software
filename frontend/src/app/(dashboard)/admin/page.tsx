'use client';

import * as React from 'react';
import {
  Settings,
  Shield,
  FileText,
  Users,
  GraduationCap,
  Flag,
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
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
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

// Types
type GateStatus = 'active' | 'inactive';
type ApprovalType = 'quote' | 'change_order' | 'invoice' | 'purchase' | 'expense';
type TemplateType = 'a3' | 'obeya' | 'email' | 'report';
type RoleType = 'operator' | 'team_lead' | 'supervisor' | 'gm' | 'admin';

interface Gate {
  id: string;
  name: string;
  phase: string;
  description: string;
  required_approvers: number;
  bypass_roles: RoleType[];
  conditions: string[];
  status: GateStatus;
  order: number;
}

interface ApprovalWorkflow {
  id: string;
  type: ApprovalType;
  name: string;
  threshold_amount?: number;
  required_roles: RoleType[];
  sequence_required: boolean;
  timeout_hours: number;
  auto_escalate: boolean;
  escalation_roles: RoleType[];
  is_active: boolean;
}

interface Template {
  id: string;
  type: TemplateType;
  name: string;
  description: string;
  content: string;
  sections?: string[];
  variables: string[];
  is_default: boolean;
  created_by: string;
  last_modified: string;
}

interface Role {
  id: string;
  name: RoleType;
  display_name: string;
  description: string;
  permissions: string[];
  member_count: number;
  can_approve: boolean;
  hierarchy_level: number;
}

interface LearningCadence {
  id: string;
  name: string;
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  duration_minutes: number;
  mandatory: boolean;
  target_roles: RoleType[];
  topics: string[];
  reminder_days_before: number;
  is_active: boolean;
}

interface FeatureFlag {
  id: string;
  key: string;
  name: string;
  description: string;
  enabled: boolean;
  rollout_percentage: number;
  target_roles?: RoleType[];
  requires_restart: boolean;
  category: 'feature' | 'experiment' | 'killswitch';
}

export default function AdminPage() {
  const [activeTab, setActiveTab] = React.useState('gates');
  
  // Gates State
  const [gates, setGates] = React.useState<Gate[]>([
    {
      id: '1',
      name: 'Quote Review Gate',
      phase: 'Phase 1 - Quote to Cash',
      description: 'Requires GM approval for quotes over $50,000',
      required_approvers: 1,
      bypass_roles: ['admin'],
      conditions: ['amount > 50000', 'new_customer === true'],
      status: 'active',
      order: 1,
    },
    {
      id: '2',
      name: 'Production Release Gate',
      phase: 'Phase 3 - Production',
      description: 'Quality and supervisor approval before production start',
      required_approvers: 2,
      bypass_roles: ['admin', 'gm'],
      conditions: ['routing_complete === true', 'materials_available === true'],
      status: 'active',
      order: 2,
    },
    {
      id: '3',
      name: 'Change Order Gate',
      phase: 'Phase 1 - Quote to Cash',
      description: 'Approval required for scope or pricing changes',
      required_approvers: 1,
      bypass_roles: ['admin', 'gm'],
      conditions: ['change_amount > 5000', 'impacts_deadline === true'],
      status: 'active',
      order: 3,
    },
  ]);

  // Approvals State
  const [approvals, setApprovals] = React.useState<ApprovalWorkflow[]>([
    {
      id: '1',
      type: 'quote',
      name: 'Standard Quote Approval',
      threshold_amount: 50000,
      required_roles: ['gm'],
      sequence_required: false,
      timeout_hours: 24,
      auto_escalate: true,
      escalation_roles: ['admin'],
      is_active: true,
    },
    {
      id: '2',
      type: 'purchase',
      name: 'Purchase Order Approval',
      threshold_amount: 10000,
      required_roles: ['supervisor', 'gm'],
      sequence_required: true,
      timeout_hours: 48,
      auto_escalate: true,
      escalation_roles: ['admin'],
      is_active: true,
    },
    {
      id: '3',
      type: 'expense',
      name: 'Expense Report Approval',
      threshold_amount: 1000,
      required_roles: ['supervisor'],
      sequence_required: false,
      timeout_hours: 72,
      auto_escalate: false,
      escalation_roles: ['gm'],
      is_active: true,
    },
  ]);

  // Templates State
  const [templates, setTemplates] = React.useState<Template[]>([
    {
      id: '1',
      type: 'a3',
      name: 'Problem Solving A3',
      description: 'Standard 8-step problem solving template',
      content: '',
      sections: ['Background', 'Current Condition', 'Goal', 'Root Cause Analysis', 'Countermeasures', 'Implementation Plan', 'Follow-up', 'Reflection'],
      variables: ['problem_statement', 'target_date', 'owner', 'team'],
      is_default: true,
      created_by: 'Admin',
      last_modified: '2026-01-05',
    },
    {
      id: '2',
      type: 'obeya',
      name: 'Project Obeya Template',
      description: 'Standard project visual management room',
      content: '',
      sections: ['SQDCP Metrics', 'Action Items', 'Risks & Issues', 'Timeline', 'Team'],
      variables: ['project_name', 'start_date', 'end_date', 'pm_name'],
      is_default: true,
      created_by: 'Admin',
      last_modified: '2026-01-04',
    },
    {
      id: '3',
      type: 'email',
      name: 'Quote Approval Notification',
      description: 'Email sent when quote requires approval',
      content: 'A quote requiring your approval has been submitted...',
      variables: ['quote_number', 'customer_name', 'amount', 'requester', 'deadline'],
      is_default: true,
      created_by: 'Admin',
      last_modified: '2026-01-03',
    },
  ]);

  // Roles State
  const [roles, setRoles] = React.useState<Role[]>([
    {
      id: '1',
      name: 'operator',
      display_name: 'Operator',
      description: 'Shop floor operators',
      permissions: ['view_production', 'log_time', 'report_issues', 'view_training'],
      member_count: 45,
      can_approve: false,
      hierarchy_level: 1,
    },
    {
      id: '2',
      name: 'team_lead',
      display_name: 'Team Lead',
      description: 'Team leaders on the shop floor',
      permissions: ['view_production', 'log_time', 'report_issues', 'view_training', 'assign_work', 'close_andon'],
      member_count: 8,
      can_approve: false,
      hierarchy_level: 2,
    },
    {
      id: '3',
      name: 'supervisor',
      display_name: 'Supervisor',
      description: 'Department supervisors',
      permissions: ['all_team_lead', 'approve_time', 'manage_schedule', 'approve_expense', 'view_analytics'],
      member_count: 5,
      can_approve: true,
      hierarchy_level: 3,
    },
    {
      id: '4',
      name: 'gm',
      display_name: 'General Manager',
      description: 'General management',
      permissions: ['all_supervisor', 'approve_quotes', 'approve_purchases', 'view_financials', 'manage_gates'],
      member_count: 2,
      can_approve: true,
      hierarchy_level: 4,
    },
    {
      id: '5',
      name: 'admin',
      display_name: 'Administrator',
      description: 'System administrators',
      permissions: ['all_access', 'manage_users', 'manage_system', 'bypass_gates', 'configure_features'],
      member_count: 1,
      can_approve: true,
      hierarchy_level: 5,
    },
  ]);

  // Learning State
  const [learningCadences, setLearningCadences] = React.useState<LearningCadence[]>([
    {
      id: '1',
      name: 'Daily Shift Start Meeting',
      frequency: 'daily',
      duration_minutes: 15,
      mandatory: true,
      target_roles: ['operator', 'team_lead', 'supervisor'],
      topics: ['Safety Review', 'Yesterday Performance', 'Today Goals', 'Open Issues'],
      reminder_days_before: 0,
      is_active: true,
    },
    {
      id: '2',
      name: 'Weekly Team Learning',
      frequency: 'weekly',
      duration_minutes: 60,
      mandatory: true,
      target_roles: ['operator', 'team_lead'],
      topics: ['Skill Training', 'Quality Standards', 'New Procedures', 'Continuous Improvement'],
      reminder_days_before: 1,
      is_active: true,
    },
    {
      id: '3',
      name: 'Monthly A3 Review',
      frequency: 'monthly',
      duration_minutes: 120,
      mandatory: false,
      target_roles: ['team_lead', 'supervisor', 'gm'],
      topics: ['A3 Presentations', 'Problem Solving Review', 'Best Practices Sharing'],
      reminder_days_before: 3,
      is_active: true,
    },
    {
      id: '4',
      name: 'Quarterly Strategy Review',
      frequency: 'quarterly',
      duration_minutes: 240,
      mandatory: true,
      target_roles: ['supervisor', 'gm', 'admin'],
      topics: ['Performance Review', 'Strategic Planning', 'Resource Allocation', 'Improvement Initiatives'],
      reminder_days_before: 7,
      is_active: true,
    },
  ]);

  // Feature Flags State
  const [featureFlags, setFeatureFlags] = React.useState<FeatureFlag[]>([
    {
      id: '1',
      key: 'FEATURE_PHASE_2_NPI',
      name: 'Phase 2 - NPI Module',
      description: 'Enable New Product Introduction features',
      enabled: false,
      rollout_percentage: 0,
      requires_restart: true,
      category: 'feature',
    },
    {
      id: '2',
      key: 'FEATURE_PHASE_3_PRODUCTION',
      name: 'Phase 3 - Production Module',
      description: 'Enable Production Management features',
      enabled: true,
      rollout_percentage: 100,
      requires_restart: true,
      category: 'feature',
    },
    {
      id: '3',
      key: 'FEATURE_AI_SUGGESTIONS',
      name: 'AI-Powered Suggestions',
      description: 'Enable ML-based recommendations and insights',
      enabled: true,
      rollout_percentage: 100,
      target_roles: ['supervisor', 'gm', 'admin'],
      requires_restart: false,
      category: 'feature',
    },
    {
      id: '4',
      key: 'FEATURE_OFFLINE_MODE',
      name: 'Offline Mode (PWA)',
      description: 'Enable progressive web app offline capabilities',
      enabled: false,
      rollout_percentage: 50,
      requires_restart: false,
      category: 'experiment',
    },
    {
      id: '5',
      key: 'DISABLE_BACKGROUND_JOBS',
      name: 'Kill Switch - Background Jobs',
      description: 'Emergency disable of background processing',
      enabled: false,
      rollout_percentage: 0,
      requires_restart: false,
      category: 'killswitch',
    },
  ]);

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
    <div className="space-y-6">
      {/* Header */}
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
        <TabsList className="grid w-full grid-cols-6">
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
        </TabsList>

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
                    Modified {template.last_modified} by {template.created_by}
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
                                  onCheckedChange={(checked) => {
                                    setFeatureFlags((flags) =>
                                      flags.map((f) =>
                                        f.id === flag.id ? { ...f, enabled: checked } : f
                                      )
                                    );
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
      </Tabs>
    </div>
  );
}
