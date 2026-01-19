'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import { apiClient } from '@/api/client';
import { useAdminStore } from '@/stores/admin';
import { cn } from '@/lib/utils';
import {
  computeLineageLayout,
  makeNodeKey,
  type LineageEdge as LayoutLineageEdge,
  type LineageNode as LayoutLineageNode,
} from '@/lib/lineage-layout';
import { AmbientStatus } from '@/components/ui/stat-card';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';

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
  const { t } = useI18n();
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
        {isActive ? t('common.active') : t('common.inactive')}
      </Badge>
    );
  };

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="admin-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90 flex items-center gap-3">
            <Shield className="h-6 w-6 text-rams-orange" />
            {t('pages.admin.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.admin.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: SYSTEM-ADMIN-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <AmbientStatus status="operational" label={t('pages.admin.coreConfigSynced') || 'Core Configuration Synchronized'} />
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none">
            <Save className="mr-2 h-3.5 w-3.5" />
            {t('pages.admin.saveConfiguration') || 'SAVE_CONFIGURATION'}
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-8 animate-in fade-in duration-700">
        <TabsList className="bg-rams-panel border border-rams-line p-1 rounded-rams-sm w-fit overflow-x-auto scrollbar-hide">
          <TabsTrigger value="gates">{t('pages.admin.tabs.qualityGates') || 'QUALITY_GATES'}</TabsTrigger>
          <TabsTrigger value="approvals">{t('pages.admin.tabs.approvalSync') || 'APPROVAL_SYNC'}</TabsTrigger>
          <TabsTrigger value="templates">{t('pages.admin.tabs.docTemplates') || 'DOC_TEMPLATES'}</TabsTrigger>
          <TabsTrigger value="roles">{t('pages.admin.tabs.accessLayers') || 'ACCESS_LAYERS'}</TabsTrigger>
          <TabsTrigger value="learning">{t('pages.admin.tabs.learningCadence') || 'LEARNING_CADENCE'}</TabsTrigger>
          <TabsTrigger value="features">{t('pages.admin.tabs.featureNodes') || 'FEATURE_NODES'}</TabsTrigger>
          <TabsTrigger value="lineage">{t('pages.admin.tabs.dataLineage') || 'DATA_LINEAGE'}</TabsTrigger>
          <TabsTrigger value="audit">{t('pages.admin.tabs.systemLogs') || 'SYSTEM_LOGS'}</TabsTrigger>
          <TabsTrigger value="security">{t('pages.admin.tabs.hardening') || 'HARDENING'}</TabsTrigger>
        </TabsList>

        {/* Lineage Tab */}
        <TabsContent value="lineage" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.admin.lineage.title') || 'Organizational Data Lineage'}</CardTitle>
              <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">
                {t('pages.admin.lineage.description') || 'Visualize entity-to-entity relationship nodes from the Data Lineage Intelligence Service.'}
              </p>
            </CardHeader>
            <CardContent className="p-8 space-y-8 bg-rams-module">
              <div className="grid gap-px border border-rams-line bg-rams-line md:grid-cols-4">
                <div className="bg-rams-panel/20 p-4 space-y-2">
                  <Label className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">ENTITY_TYPE</Label>
                  <Input
                    value={lineageQuery.entityType}
                    onChange={(e) => setLineageQuery((s) => ({ ...s, entityType: e.target.value }))}
                    placeholder="e.g. work_order"
                    className="bg-rams-panel border-rams-line h-9 text-[10px] font-mono uppercase"
                    data-testid="admin-lineage-entity-type"
                  />
                </div>
                <div className="bg-rams-panel/20 p-4 space-y-2">
                  <Label className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">ENTITY_ID</Label>
                  <Input
                    value={lineageQuery.entityId}
                    onChange={(e) => setLineageQuery((s) => ({ ...s, entityId: e.target.value }))}
                    placeholder="e.g. 123"
                    className="bg-rams-panel border-rams-line h-9 text-[10px] font-mono"
                    data-testid="admin-lineage-entity-id"
                  />
                </div>
                <div className="bg-rams-panel/20 p-4 space-y-2">
                  <Label className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">MAX_DEPTH</Label>
                  <Input
                    type="number"
                    min={0}
                    max={10}
                    value={lineageQuery.maxDepth}
                    onChange={(e) => setLineageQuery((s) => ({ ...s, maxDepth: Number(e.target.value || 0) }))}
                    className="bg-rams-panel border-rams-line h-9 text-[10px] font-mono"
                    data-testid="admin-lineage-max-depth"
                  />
                </div>
                <div className="bg-rams-panel/20 p-4 flex items-end">
                  <Button
                    className="w-full rounded-none bg-rams-orange text-black font-black uppercase tracking-widest text-[9px] h-9"
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
                    {lineageLoading ? (t('pages.admin.lineage.syncing') || 'SYNCING...') : (t('pages.admin.lineage.loadGraph') || 'LOAD_GRAPH')}
                  </Button>
                </div>
              </div>

              {lineageError ? (
                <div className="p-6 bg-rams-red/5 border border-rams-red/20 flex gap-4 animate-in slide-in-from-top-2">
                  <AlertCircle className="h-5 w-5 text-rams-red shrink-0" />
                  <div className="text-xs font-medium text-rams-red uppercase leading-relaxed">{lineageError}</div>
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
                    <div className="rounded-none border border-rams-line bg-rams-panel/10">
                      <div className="border-b border-rams-line p-4 text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-[0.2em]">
                        Root Node: <span className="text-foreground/60">{lineageGraph.root_entity_type}:{lineageGraph.root_entity_id}</span> • Clusters: {layout.nodes.length} • Sync_Links: {lineageGraph.edges.length}
                      </div>
                      <div className="max-h-[600px] overflow-auto p-8 bg-rams-panel/5 relative">
                        <div className="relative z-10" style={{ width: layout.width, height: layout.height }}>
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
                                  className="text-muted-foreground/20"
                                  strokeWidth={1}
                                />
                              );
                            })}
                          </svg>

                          {layout.nodes.map((n) => (
                            <div
                              key={n.key}
                              className="absolute rounded-none border border-rams-line bg-rams-module p-3 group hover:border-rams-orange transition-none"
                              style={{ left: n.x, top: n.y, width: nodeBox.w, height: nodeBox.h }}
                              data-testid={`admin-lineage-node-${n.key}`}
                            >
                              <div className="text-[8px] font-mono font-black text-muted-foreground/30 uppercase tracking-tighter">DEPTH_{n.depth}</div>
                              <div className="truncate text-[11px] font-sans font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{n.entity_type}</div>
                              <div className="truncate text-[9px] font-mono font-bold text-muted-foreground/40 uppercase mt-0.5">{n.entity_id}</div>
                            </div>
                          ))}
                        </div>
                        <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
                      </div>
                    </div>
                  );
                })()
              ) : (
                <div className="rounded-none border border-dashed border-rams-line p-24 text-center bg-rams-panel/5">
                  <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">Enter intelligence node parameters and execute synchronization protocol.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Gates Tab */}
        <TabsContent value="gates" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.admin.gates.title') || 'Quality Gate Protocols'}</CardTitle>
                  <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('pages.admin.gates.description') || 'Define approval gates and threshold conditions for critical sync points'}</p>
                </div>
                <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[9px] h-9 px-4 transition-none" onClick={() => setEditGateDialog(true)}>
                  <Plus className="h-3.5 w-3.5 mr-2" />
                  {t('pages.admin.gates.initializeGate') || 'INITIALIZE_GATE'}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">{t('pages.admin.gates.table.order')}</TableHead>
                      <TableHead>{t('pages.admin.gates.table.identity')}</TableHead>
                      <TableHead>{t('pages.admin.gates.table.phase')}</TableHead>
                      <TableHead>{t('pages.admin.gates.table.authCount')}</TableHead>
                      <TableHead>{t('pages.admin.gates.table.bypassLayers')}</TableHead>
                      <TableHead>{t('pages.admin.gates.table.conditions')}</TableHead>
                      <TableHead>{t('pages.admin.gates.table.syncStatus')}</TableHead>
                      <TableHead className="w-10"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {gates.map((gate) => (
                      <TableRow key={gate.id} className="transition-none hover:bg-rams-panel">
                        <TableCell className="font-mono font-bold text-rams-orange">{gate.order}</TableCell>
                        <TableCell>
                          <div className="space-y-0.5">
                            <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{gate.name}</p>
                            <p className="text-[9px] text-muted-foreground/40 uppercase truncate max-w-xs">{gate.description}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="rounded-none border-rams-line text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel">{gate.phase}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 text-[10px] font-mono font-bold text-foreground/70">
                            <Users className="h-3 w-3 opacity-40" />
                            {gate.required_approvers}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {gate.bypass_roles.map((role) => (
                              <Badge key={role} variant="secondary" className="rounded-none text-[7px] font-black uppercase tracking-tighter px-1 h-3.5">
                                {role}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="text-[9px] font-mono font-bold uppercase text-muted-foreground/40">
                            {gate.conditions.length} RULES_ACTIVE
                          </span>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={gate.status} />
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-rams-sm">
                                <ChevronDown className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem>
                                <Edit className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.gates.actions.refine')}
                              </DropdownMenuItem>
                              <DropdownMenuItem>
                                {gate.status === 'active' ? (
                                  <>
                                    <Lock className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.gates.actions.deauthorize')}
                                  </>
                                ) : (
                                  <>
                                    <Unlock className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.gates.actions.authorize')}
                                  </>
                                )}
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem className="text-rams-red">
                                <Trash2 className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.gates.actions.terminate')}
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Approvals Tab */}
        <TabsContent value="approvals" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.admin.approvals.title') || 'Approval Workflows'}</CardTitle>
                  <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('pages.admin.approvals.description') || 'Configure approval chains, fiscal thresholds, and automated escalations'}</p>
                </div>
                <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[9px] h-9 px-4 transition-none" onClick={() => setEditApprovalDialog(true)}>
                  <Plus className="h-3.5 w-3.5 mr-2" />
                  {t('pages.admin.approvals.initializeWorkflow') || 'INITIALIZE_WORKFLOW'}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('pages.admin.approvals.table.type')}</TableHead>
                      <TableHead>{t('pages.admin.approvals.table.identity')}</TableHead>
                      <TableHead>{t('pages.admin.approvals.table.threshold')}</TableHead>
                      <TableHead>{t('pages.admin.approvals.table.requiredRoles')}</TableHead>
                      <TableHead>{t('pages.admin.approvals.table.sequence')}</TableHead>
                      <TableHead>{t('pages.admin.approvals.table.timeout')}</TableHead>
                      <TableHead>{t('pages.admin.approvals.table.escalate')}</TableHead>
                      <TableHead>{t('pages.admin.approvals.table.syncStatus')}</TableHead>
                      <TableHead className="w-10"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {approvals.map((approval) => (
                      <TableRow key={approval.id} className="transition-none hover:bg-rams-panel">
                        <TableCell>
                          <Badge variant="outline" className="rounded-none border-rams-line text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel">{approval.type}</Badge>
                        </TableCell>
                        <TableCell className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{approval.name}</TableCell>
                        <TableCell className="font-mono font-bold text-foreground/70 tabular-nums">
                          {approval.threshold_amount ? `$${approval.threshold_amount.toLocaleString()}` : 'FULL_SCOPE'}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {approval.required_roles.map((role) => (
                              <Badge key={role} variant="secondary" className="rounded-none text-[7px] font-black uppercase tracking-tighter px-1 h-3.5">
                                {role}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={approval.sequence_required ? 'default' : 'outline'} className="rounded-none text-[8px] font-black uppercase tracking-widest h-4 px-1">
                            {approval.sequence_required ? 'SEQUENTIAL' : 'PARALLEL'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 text-[10px] font-mono font-bold text-muted-foreground/60">
                            <Clock className="h-3 w-3 opacity-40" />
                            {approval.timeout_hours}H
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={approval.auto_escalate ? 'default' : 'secondary'} className="rounded-none text-[8px] font-black uppercase tracking-widest h-4 px-1">
                            {approval.auto_escalate ? 'YES' : 'NO'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={approval.is_active} />
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-rams-sm">
                                <ChevronDown className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem>
                                <Edit className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.approvals.actions.refine')}
                              </DropdownMenuItem>
                              <DropdownMenuItem>
                                {approval.is_active ? t('pages.admin.approvals.actions.deauthorize') : t('pages.admin.approvals.actions.authorize')}
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem className="text-rams-red">
                                <Trash2 className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.approvals.actions.terminate')}
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="grid gap-px border border-rams-line bg-rams-line md:grid-cols-2 lg:grid-cols-3">
            {templates.map((template) => (
              <Card key={template.id} className="rounded-none border-0 bg-rams-module hover:bg-rams-panel/50 transition-none group cursor-help">
                <CardHeader className="pb-4">
                  <div className="flex items-center justify-between mb-4">
                    <Badge variant="outline" className="rounded-none border-rams-line text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel">{template.type}</Badge>
                    {template.is_default && (
                      <Badge variant="default" className="rounded-none h-4 px-1 text-[8px] font-black uppercase">DEFAULT_NODE</Badge>
                    )}
                  </div>
                  <CardTitle className="font-sans font-black text-sm uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{template.name}</CardTitle>
                  <CardDescription className="text-[10px] text-muted-foreground/40 mt-1 uppercase leading-relaxed font-medium line-clamp-2">{template.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {template.sections && (
                    <div className="space-y-2">
                      <div className="text-[8px] font-black uppercase tracking-[0.2em] text-muted-foreground/30">Protocol_Sections ({template.sections.length})</div>
                      <div className="flex flex-wrap gap-1">
                        {template.sections.slice(0, 3).map((section, idx) => (
                          <Badge key={idx} variant="secondary" className="rounded-none text-[7px] font-black uppercase tracking-tighter px-1 h-3.5 bg-rams-panel">
                            {section}
                          </Badge>
                        ))}
                        {template.sections.length > 3 && (
                          <Badge variant="secondary" className="rounded-none text-[7px] font-black uppercase tracking-tighter px-1 h-3.5">
                            +{template.sections.length - 3}
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}
                  <div className="space-y-2">
                    <div className="text-[8px] font-black uppercase tracking-[0.2em] text-muted-foreground/30">Variable_Nodes ({template.variables.length})</div>
                    <div className="flex flex-wrap gap-1">
                      {template.variables.slice(0, 3).map((variable, idx) => (
                        <code key={idx} className="text-[9px] bg-rams-panel border border-rams-line px-1.5 py-0.5 font-mono text-foreground/60 uppercase tracking-tighter">
                          {variable}
                        </code>
                      ))}
                      {template.variables.length > 3 && (
                        <Badge variant="secondary" className="rounded-none text-[7px] font-black uppercase tracking-tighter px-1 h-3.5">
                          +{template.variables.length - 3}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="pt-6 border-t border-rams-line text-[9px] font-mono font-bold text-muted-foreground/20 uppercase tracking-widest">
                    SYNCED {template.updated_at.toUpperCase()} — BY {template.created_by.toUpperCase()}
                  </div>
                  <div className="flex gap-1 pt-2">
                    <Button variant="outline" size="sm" className="flex-1 rounded-none border-rams-line text-[9px] font-black uppercase h-8 transition-none">
                      <Edit className="h-3 w-3 mr-2" />
                      REFINE
                    </Button>
                    <Button variant="outline" size="sm" className="flex-1 rounded-none border-rams-line text-[9px] font-black uppercase h-8 transition-none">
                      <FileText className="h-3 w-3 mr-2" />
                      PREVIEW
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <Button className="w-full rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest h-12 transition-none" onClick={() => setEditTemplateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            {t('pages.admin.templates.initializeTemplate') || 'INITIALIZE_NEW_TEMPLATE'}
          </Button>
        </TabsContent>

        {/* Roles Tab */}
        <TabsContent value="roles" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.admin.roles.title') || 'Access Layer Configuration'}</CardTitle>
                  <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('pages.admin.roles.description') || 'Define organizational roles, sync permissions, and hierarchical authorization levels'}</p>
                </div>
                <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[9px] h-9 px-4 transition-none" onClick={() => setEditRoleDialog(true)}>
                  <Plus className="h-3.5 w-3.5 mr-2" />
                  {t('pages.admin.roles.initializeRole') || 'INITIALIZE_ROLE'}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">{t('pages.admin.roles.table.level')}</TableHead>
                      <TableHead>{t('pages.admin.roles.table.identity')}</TableHead>
                      <TableHead>{t('pages.admin.roles.table.specification')}</TableHead>
                      <TableHead>{t('pages.admin.roles.table.nodeCount')}</TableHead>
                      <TableHead>{t('pages.admin.roles.table.authSync')}</TableHead>
                      <TableHead>{t('pages.admin.roles.table.approvalGates')}</TableHead>
                      <TableHead className="w-10"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {roles
                      .sort((a, b) => b.hierarchy_level - a.hierarchy_level)
                      .map((role) => (
                        <TableRow key={role.id} className="transition-none hover:bg-rams-panel">
                          <TableCell>
                            <Badge variant="outline" className="rounded-none border-rams-line font-mono text-[9px] h-4 px-1">L{role.hierarchy_level}</Badge>
                          </TableCell>
                          <TableCell>
                            <div className="space-y-0.5">
                              <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{role.display_name}</p>
                              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase">{role.name}</p>
                            </div>
                          </TableCell>
                          <TableCell className="max-w-xs">
                            <p className="text-[10px] font-medium text-muted-foreground/60 uppercase truncate">{role.description}</p>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2 text-[10px] font-mono font-bold text-foreground/70">
                              <Users className="h-3 w-3 opacity-40" />
                              {role.member_count}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {(role.permissions ?? []).slice(0, 2).map((perm, idx) => (
                                <Badge key={idx} variant="secondary" className="rounded-none text-[7px] font-black uppercase tracking-tighter px-1 h-3.5 bg-rams-panel">
                                  {perm}
                                </Badge>
                              ))}
                              {(role.permissions?.length ?? 0) > 2 && (
                                <Badge variant="secondary" className="rounded-none text-[7px] font-black uppercase tracking-tighter px-1 h-3.5">
                                  +{role.permissions.length - 2}
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant={role.can_approve ? 'default' : 'secondary'} className="rounded-none text-[8px] font-black uppercase tracking-widest h-4 px-1">
                              {role.can_approve ? t('pages.admin.roles.authorized') : t('pages.admin.roles.restricted')}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8 rounded-rams-sm">
                                  <ChevronDown className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem>
                                  <Edit className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.roles.actions.refineAuth')}
                                </DropdownMenuItem>
                                <DropdownMenuItem>
                                  <Users className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.roles.actions.syncMembers')}
                                </DropdownMenuItem>
                                {role.hierarchy_level < 4 && (
                                  <DropdownMenuItem className="text-rams-red">
                                    <Trash2 className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.roles.actions.terminateLayer')}
                                  </DropdownMenuItem>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Learning Tab */}
        <TabsContent value="learning" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.admin.learning.title') || 'Learning Cadence Synchronization'}</CardTitle>
                  <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('pages.admin.learning.description') || 'Manage recurring intelligence micro-drills and specialized training protocols'}</p>
                </div>
                <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[9px] h-9 px-4 transition-none" onClick={() => setEditLearningDialog(true)}>
                  <Plus className="h-3.5 w-3.5 mr-2" />
                  {t('pages.admin.learning.initializeCadence') || 'INITIALIZE_CADENCE'}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('pages.admin.learning.table.identity')}</TableHead>
                      <TableHead>{t('pages.admin.learning.table.pulse')}</TableHead>
                      <TableHead>{t('pages.admin.learning.table.duration')}</TableHead>
                      <TableHead>{t('pages.admin.learning.table.targetLayers')}</TableHead>
                      <TableHead>{t('pages.admin.learning.table.topicNodes')}</TableHead>
                      <TableHead>{t('pages.admin.learning.table.requirement')}</TableHead>
                      <TableHead>{t('pages.admin.learning.table.reminder')}</TableHead>
                      <TableHead>{t('pages.admin.learning.table.syncStatus')}</TableHead>
                      <TableHead className="w-10"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {learningCadences.map((cadence) => (
                      <TableRow key={cadence.id} className="transition-none hover:bg-rams-panel">
                        <TableCell className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{cadence.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="rounded-none border-rams-line text-[8px] font-black uppercase tracking-widest px-1.5 h-4 bg-rams-panel">
                            {cadence.frequency}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 text-[10px] font-mono font-bold text-muted-foreground/60">
                            <Clock className="h-3 w-3 opacity-40" />
                            {cadence.duration_minutes}M
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {(cadence.target_roles ?? []).slice(0, 2).map((role) => (
                              <Badge key={role} variant="secondary" className="rounded-none text-[7px] font-black uppercase tracking-tighter px-1 h-3.5 bg-rams-panel">
                                {role}
                              </Badge>
                            ))}
                            {(cadence.target_roles?.length ?? 0) > 2 && (
                              <Badge variant="secondary" className="rounded-none text-[7px] font-black uppercase tracking-tighter px-1 h-3.5">
                                +{cadence.target_roles.length - 2}
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="text-[9px] font-mono font-bold uppercase text-muted-foreground/40">
                            {(cadence.topics?.length ?? 0)} {t('pages.admin.learning.syclosActive')}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={cadence.mandatory ? 'destructive' : 'secondary'} className="rounded-none text-[8px] font-black uppercase tracking-widest h-4 px-1">
                            {cadence.mandatory ? t('pages.admin.learning.mandatory') : t('pages.admin.learning.optional')}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="text-[10px] font-mono font-bold text-muted-foreground/60 uppercase">
                            T-{cadence.reminder_days_before}D SYNC
                          </div>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={cadence.is_active} />
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-rams-sm">
                                <ChevronDown className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem>
                                <Edit className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.learning.actions.refine')}
                              </DropdownMenuItem>
                              <DropdownMenuItem>
                                {cadence.is_active ? t('pages.admin.learning.actions.deauthorize') : t('pages.admin.learning.actions.authorize')}
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem className="text-rams-red">
                                <Trash2 className="mr-2 h-3.5 w-3.5" /> {t('pages.admin.learning.actions.terminate')}
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Features Tab */}
        <TabsContent value="features" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.admin.features.title') || 'Feature Node Orchestration'}</CardTitle>
              <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('pages.admin.features.description') || 'Manage modular capabilities, experimental branches, and emergency killswitches'}</p>
            </CardHeader>
            <CardContent className="p-8 space-y-12 bg-rams-module">
              {['feature', 'experiment', 'killswitch'].map((category) => (
                <div key={category} className="space-y-6">
                  <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70 flex items-center gap-4">
                    <div className={cn("h-1.5 w-1.5 rounded-none", category === 'killswitch' ? "bg-rams-red" : "bg-rams-orange")} />
                    {category === 'killswitch' ? t('pages.admin.features.emergencyKillSwitches') : t(`pages.admin.features.${category}s`)}
                    <div className="h-px flex-1 bg-rams-line/30" />
                  </h3>
                  <div className="grid gap-1 md:grid-cols-2">
                    {featureFlags
                      .filter((flag) => flag.category === category)
                      .map((flag) => (
                        <Card key={flag.id} className={cn("rounded-none border-rams-line bg-rams-panel/20 transition-none group hover:bg-rams-panel/40", flag.enabled && category === 'killswitch' ? 'border-rams-red bg-rams-red/5' : '')}>
                          <CardContent className="p-5">
                            <div className="flex items-start justify-between gap-6">
                              <div className="flex-1 space-y-4">
                                <div className="flex items-center gap-3">
                                  <code className="text-[9px] font-mono font-black bg-rams-panel border border-rams-line px-2 py-0.5 text-foreground/40 uppercase tracking-tighter">
                                    {flag.key}
                                  </code>
                                  {flag.requires_restart && (
                                    <Badge variant="outline" className="rounded-none border-rams-orange/20 bg-rams-orange/5 text-rams-orange text-[7px] font-black uppercase tracking-tighter h-3.5 px-1">SYNC_REQUIRED</Badge>
                                  )}
                                </div>
                                <div>
                                  <div className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{flag.name}</div>
                                  <div className="text-[10px] text-muted-foreground/60 mt-1 uppercase leading-relaxed font-medium">
                                    {flag.description}
                                  </div>
                                </div>
                                {flag.target_roles && (
                                  <div className="flex items-center gap-2 text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">
                                    <Target className="h-3 w-3 opacity-40" />
                                    SYNC_LAYERS:{' '}
                                    {flag.target_roles.map((role) => (
                                      <span key={role} className="text-foreground/60">{role}</span>
                                    ))}
                                  </div>
                                )}
                                {flag.rollout_percentage < 100 && (
                                  <div className="space-y-1.5">
                                    <div className="flex justify-between text-[8px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                                      <span>Deployment_Spread</span>
                                      <span>{flag.rollout_percentage}%</span>
                                    </div>
                                    <div className="h-1 bg-rams-panel border border-rams-line overflow-hidden">
                                      <div
                                        className="h-full bg-rams-orange"
                                        style={{ width: `${flag.rollout_percentage}%` }}
                                      />
                                    </div>
                                  </div>
                                )}
                              </div>
                              <div className="flex flex-col items-center gap-4">
                                <Switch
                                  checked={flag.enabled}
                                  onCheckedChange={() => {
                                    toggleFeatureFlag(flag.id);
                                  }}
                                />
                                <Button variant="ghost" size="icon" className="h-8 w-8 rounded-none border border-transparent hover:border-rams-line hover:bg-rams-panel transition-none">
                                  <Edit className="h-3.5 w-3.5 opacity-40" />
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
        <TabsContent value="audit" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.admin.audit.title') || 'System Telemetry Log'}</CardTitle>
              <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('pages.admin.audit.description') || 'Immutable trace of organizational shifts, authentication events, and protocol mutations'}</p>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('pages.admin.audit.table.timestamp')}</TableHead>
                      <TableHead>{t('pages.admin.audit.table.operative')}</TableHead>
                      <TableHead>{t('pages.admin.audit.table.mutation')}</TableHead>
                      <TableHead>{t('pages.admin.audit.table.entityNode')}</TableHead>
                      <TableHead>{t('pages.admin.audit.table.deltaLog')}</TableHead>
                      <TableHead>{t('pages.admin.audit.table.ipAddress')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {auditLogs.map((log) => (
                      <TableRow key={log.id} className="transition-none hover:bg-rams-panel">
                        <TableCell className="text-[10px] font-mono font-bold text-muted-foreground/60 tabular-nums uppercase">{formatDate(log.created_at)}</TableCell>
                        <TableCell className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{log.user_email}</TableCell>
                        <TableCell>
                          <Badge variant={log.action === 'CREATE' ? 'default' : log.action === 'UPDATE' ? 'outline' : 'secondary'} className="rounded-none text-[8px] font-black uppercase tracking-widest h-4 px-1">
                            {log.action}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase">{log.entity_type}</TableCell>
                        <TableCell className="max-w-md">
                          <code className="text-[10px] font-mono text-foreground/60 uppercase tracking-tighter truncate block">
                            {typeof log.extra_data === 'string' ? log.extra_data : JSON.stringify(log.extra_data)}
                          </code>
                        </TableCell>
                        <TableCell className="text-[10px] font-mono text-muted-foreground/30 tabular-nums">{log.ip_address || '—'}</TableCell>
                      </TableRow>
                    ))}
                    {auditLogs.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-24">
                          <History className="h-12 w-12 text-muted-foreground/20 mx-auto mb-4 opacity-20" />
                          <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">{t('pages.admin.audit.empty')}</p>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="grid gap-8 md:grid-cols-2">
            <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.admin.security.sso.title') || 'Single Sign-On (SSO)'}</CardTitle>
                <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('pages.admin.security.sso.description') || 'Synchronize identity with enterprise authentication clusters'}</p>
              </CardHeader>
              <CardContent className="p-8 space-y-8">
                <div className="flex items-center justify-between p-5 bg-rams-panel/20 border border-rams-line group">
                  <div>
                    <Label className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">SAML 2.0 Integration</Label>
                    <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">Sync via Okta, Azure AD, or Ping Intelligence</p>
                  </div>
                  <Switch />
                </div>
                <div className="space-y-2">
                  <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">Identity Provider Pulse URL</Label>
                  <Input placeholder="https://sso.yourcompany.com/..." className="bg-rams-panel border-rams-line h-10 text-[11px] font-mono" />
                </div>
                <div className="space-y-2">
                  <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">SP_METADATA_MANIFEST</Label>
                  <pre className="p-4 bg-rams-panel border border-rams-line text-[9px] font-mono text-muted-foreground/60 overflow-auto max-h-40 rounded-none uppercase tracking-tighter">
                    {`<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="https://sensei.starzm.com/saml">
  <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    ...
  </md:SPSSODescriptor>
</md:EntityDescriptor>`}
                  </pre>
                </div>
                <Button variant="outline" className="w-full rounded-none border-rams-line text-[9px] font-black uppercase tracking-widest h-10 transition-none">{t('pages.admin.security.downloadManifest') || 'DOWNLOAD_MANIFEST_XML'}</Button>
              </CardContent>
            </Card>

            <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.admin.security.hardening.title') || 'Infrastructure Hardening'}</CardTitle>
                <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('pages.admin.security.hardening.description') || 'Global session policies and multi-factor authorization enforcement'}</p>
              </CardHeader>
              <CardContent className="p-8 space-y-8">
                <div className="flex items-center justify-between p-5 bg-rams-panel/20 border border-rams-line group">
                  <div>
                    <Label className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">Enforce Global 2FA</Label>
                    <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">Require TOTP sync for all authenticated operatives</p>
                  </div>
                  <Switch checked={true} />
                </div>
                <div className="space-y-2">
                  <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">Pulse Timeout Threshold (Minutes)</Label>
                  <Input type="number" defaultValue={60} className="bg-rams-panel border-rams-line h-10 text-[11px] font-mono" />
                </div>
                <div className="space-y-2">
                  <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">IP Access Restricted Nodes</Label>
                  <Textarea placeholder="ALLOWLIST_IPS (ONE_PER_LINE)" className="bg-rams-panel border-rams-line text-[11px] font-mono uppercase h-32" />
                </div>
                <Button className="w-full rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-12 transition-none">{t('pages.admin.security.commitPolicies') || 'COMMIT_SECURITY_POLICIES'}</Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
