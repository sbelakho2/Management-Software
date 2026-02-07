'use client';

import * as React from 'react';
import {
  Database,
  Upload,
  Check,
  AlertCircle,
  Loader2,
  Play,
  Eye,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Server,
  Users,
  Package,
  Truck,
  DollarSign,
  ShieldCheck,
  Building2,
  Settings,
  ChevronRight,
} from 'lucide-react';
import { format } from 'date-fns';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
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
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import { apiClient } from '@/api/client';
import { ContentCard, SectionHeader } from '@/components/ui/content-card';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

// ============================================================================
// Types
// ============================================================================

interface EntityTypeInfo {
  value: string;
  label: string;
  category: string;
  description: string;
  has_dependencies: boolean;
  dependencies: string[];
}

interface EntityTypesResponse {
  categories: Record<string, EntityTypeInfo[]>;
  total_types: number;
  import_order: string[];
}

interface ImportPreviewItem {
  entity_type: string;
  source_count: number;
  existing_count: number;
  delta: number;
  estimated_imports: number;
  estimated_updates: number;
}

interface ImportPreviewResponse {
  previews: ImportPreviewItem[];
  total_source_records: number;
  total_existing_records: number;
  estimated_duration_minutes: number;
}

interface ImportResultItem {
  entity_type: string;
  total_source: number;
  imported: number;
  updated: number;
  skipped: number;
  failed: number;
  success_rate: number;
  duration_seconds: number;
  errors: string[];
}

interface ImportBatchResponse {
  batch_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  total_duration_seconds: number;
  total_imported: number;
  total_updated: number;
  total_failed: number;
  entity_results: ImportResultItem[];
}

interface ConnectionTestResponse {
  success: boolean;
  message: string;
  database_name: string | null;
  tables_found: number | null;
  version: string | null;
}

// ============================================================================
// Category Icons & Colors
// ============================================================================

const CATEGORY_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  master_data: { icon: Settings, color: 'text-blue-500', label: 'Master Data' },
  warehouse: { icon: Building2, color: 'text-amber-500', label: 'Warehouse/WMS' },
  products: { icon: Package, color: 'text-purple-500', label: 'Products' },
  hr: { icon: Users, color: 'text-green-500', label: 'Human Resources' },
  partners: { icon: Building2, color: 'text-indigo-500', label: 'Partners' },
  purchasing: { icon: Truck, color: 'text-orange-500', label: 'Purchasing' },
  sales: { icon: DollarSign, color: 'text-emerald-500', label: 'Sales' },
  shipping: { icon: Truck, color: 'text-cyan-500', label: 'Shipping' },
  finance: { icon: DollarSign, color: 'text-yellow-500', label: 'Finance' },
  quality: { icon: ShieldCheck, color: 'text-red-500', label: 'Quality' },
};

// ============================================================================
// Component
// ============================================================================

export default function StarzImportPage() {
  // State
  const [connectionStatus, setConnectionStatus] = React.useState<ConnectionTestResponse | null>(null);
  const [entityTypes, setEntityTypes] = React.useState<EntityTypesResponse | null>(null);
  const [selectedTypes, setSelectedTypes] = React.useState<Set<string>>(new Set());
  const [preview, setPreview] = React.useState<ImportPreviewResponse | null>(null);
  const [importResult, setImportResult] = React.useState<ImportBatchResponse | null>(null);
  const [onConflict, setOnConflict] = React.useState<string>('skip');
  
  // Loading states
  const [testingConnection, setTestingConnection] = React.useState(false);
  const [loadingTypes, setLoadingTypes] = React.useState(false);
  const [loadingPreview, setLoadingPreview] = React.useState(false);
  const [importing, setImporting] = React.useState(false);
  
  // Dialog states
  const [showPreviewDialog, setShowPreviewDialog] = React.useState(false);
  const [showResultDialog, setShowResultDialog] = React.useState(false);

  // =========================================================================
  // Data Loading
  // =========================================================================

  const testConnection = async () => {
    setTestingConnection(true);
    try {
      const resp = await apiClient.post<ConnectionTestResponse>('/admin/import/starz-erp/test-connection', {});
      setConnectionStatus(resp);
    } catch (err) {
      setConnectionStatus({
        success: false,
        message: 'Failed to test connection',
        database_name: null,
        tables_found: null,
        version: null,
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const loadEntityTypes = async () => {
    setLoadingTypes(true);
    try {
      const resp = await apiClient.get<EntityTypesResponse>('/admin/import/starz-erp/entity-types');
      setEntityTypes(resp);
    } catch (err) {
      console.error('Failed to load entity types:', err);
    } finally {
      setLoadingTypes(false);
    }
  };

  const loadPreview = async () => {
    setLoadingPreview(true);
    try {
      const types = selectedTypes.size > 0 ? Array.from(selectedTypes) : undefined;
      const resp = await apiClient.post<ImportPreviewResponse>('/admin/import/starz-erp/preview', {
        entity_types: types,
        on_conflict: onConflict,
      });
      setPreview(resp);
      setShowPreviewDialog(true);
    } catch (err) {
      console.error('Failed to load preview:', err);
    } finally {
      setLoadingPreview(false);
    }
  };

  const executeImport = async () => {
    setImporting(true);
    setShowPreviewDialog(false);
    try {
      const types = selectedTypes.size > 0 ? Array.from(selectedTypes) : undefined;
      const resp = await apiClient.post<ImportBatchResponse>('/admin/import/starz-erp/execute', {
        entity_types: types,
        on_conflict: onConflict,
        dry_run: false,
      });
      setImportResult(resp);
      setShowResultDialog(true);
    } catch (err) {
      console.error('Import failed:', err);
    } finally {
      setImporting(false);
    }
  };

  const importCategory = async (category: string) => {
    setImporting(true);
    try {
      const endpoint = `/admin/import/starz-erp/import/${category.replace('_', '-')}`;
      const resp = await apiClient.post<ImportBatchResponse>(endpoint, {
        on_conflict: onConflict,
      });
      setImportResult(resp);
      setShowResultDialog(true);
    } catch (err) {
      console.error(`Import ${category} failed:`, err);
    } finally {
      setImporting(false);
    }
  };

  // =========================================================================
  // Selection Helpers
  // =========================================================================

  const toggleType = (type: string) => {
    const newSet = new Set(selectedTypes);
    if (newSet.has(type)) {
      newSet.delete(type);
    } else {
      newSet.add(type);
    }
    setSelectedTypes(newSet);
  };

  const selectCategory = (category: string) => {
    if (!entityTypes) return;
    const types = entityTypes.categories[category] || [];
    const newSet = new Set(selectedTypes);
    types.forEach(t => newSet.add(t.value));
    setSelectedTypes(newSet);
  };

  const deselectCategory = (category: string) => {
    if (!entityTypes) return;
    const types = entityTypes.categories[category] || [];
    const newSet = new Set(selectedTypes);
    types.forEach(t => newSet.delete(t.value));
    setSelectedTypes(newSet);
  };

  const selectAll = () => {
    if (!entityTypes) return;
    const all = new Set<string>();
    Object.values(entityTypes.categories).forEach(types => {
      types.forEach(t => all.add(t.value));
    });
    setSelectedTypes(all);
  };

  const deselectAll = () => {
    setSelectedTypes(new Set());
  };

  // =========================================================================
  // Effects
  // =========================================================================

  React.useEffect(() => {
    loadEntityTypes();
  }, []);

  // =========================================================================
  // Render
  // =========================================================================

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight uppercase text-foreground font-mono">
            STARZ ERP DATA IMPORT
          </h1>
          <p className="text-muted-foreground mt-1">
            Migrate data from legacy starzERP MySQL database to Sensei OS
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={testConnection}
            disabled={testingConnection}
          >
            {testingConnection ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Server className="h-4 w-4 mr-2" />
            )}
            Test Connection
          </Button>
        </div>
      </div>

      {/* Connection Status */}
      {connectionStatus && (
        <Card className={cn(
          'border-l-4',
          connectionStatus.success ? 'border-l-green-500' : 'border-l-red-500'
        )}>
          <CardContent className="flex items-center gap-4 py-4">
            {connectionStatus.success ? (
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            ) : (
              <XCircle className="h-8 w-8 text-red-500" />
            )}
            <div className="flex-1">
              <p className="font-semibold">{connectionStatus.message}</p>
              {connectionStatus.success && (
                <p className="text-sm text-muted-foreground">
                  Database: {connectionStatus.database_name} • 
                  Tables: {connectionStatus.tables_found} • 
                  Version: {connectionStatus.version}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Overview */}
      <StatSection label="IMPORT OVERVIEW" columns={4}>
        <StatCard
          label="ENTITY TYPES"
          value={entityTypes?.total_types ?? 0}
          icon={Database}
          iconColor="info"
        />
        <StatCard
          label="SELECTED"
          value={selectedTypes.size}
          icon={Check}
          iconColor="success"
        />
        <StatCard
          label="CATEGORIES"
          value={entityTypes ? Object.keys(entityTypes.categories).length : 0}
          icon={Package}
          iconColor="primary"
        />
        <StatCard
          label="CONFLICT MODE"
          value={onConflict.toUpperCase()}
          icon={Settings}
          iconColor="warning"
        />
      </StatSection>

      {/* Import Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Import Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Conflict Resolution</Label>
              <Select value={onConflict} onValueChange={setOnConflict}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="skip">Skip Existing</SelectItem>
                  <SelectItem value="update">Update Existing</SelectItem>
                  <SelectItem value="fail">Fail on Conflict</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                How to handle records that already exist
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2 pt-4 border-t">
            <Button variant="outline" onClick={selectAll}>
              Select All
            </Button>
            <Button variant="outline" onClick={deselectAll}>
              Deselect All
            </Button>
            <div className="flex-1" />
            <Button
              variant="outline"
              onClick={loadPreview}
              disabled={loadingPreview || selectedTypes.size === 0}
            >
              {loadingPreview ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Eye className="h-4 w-4 mr-2" />
              )}
              Preview Import
            </Button>
            <Button
              onClick={executeImport}
              disabled={importing || selectedTypes.size === 0}
              className="bg-rams-orange hover:bg-rams-orange/90"
            >
              {importing ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Execute Import
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Entity Categories */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {loadingTypes ? (
          <div className="col-span-2 flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : entityTypes ? (
          Object.entries(entityTypes.categories).map(([category, types]) => {
            const config = CATEGORY_CONFIG[category] || {
              icon: Database,
              color: 'text-gray-500',
              label: category,
            };
            const Icon = config.icon;
            const selectedCount = types.filter(t => selectedTypes.has(t.value)).length;
            const allSelected = selectedCount === types.length;
            
            return (
              <Card key={category}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <Icon className={cn('h-5 w-5', config.color)} />
                      {config.label}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">
                        {selectedCount}/{types.length}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => allSelected ? deselectCategory(category) : selectCategory(category)}
                      >
                        {allSelected ? 'Deselect' : 'Select All'}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => importCategory(category)}
                        disabled={importing}
                      >
                        <Upload className="h-3 w-3 mr-1" />
                        Import
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {types.map(type => (
                      <div
                        key={type.value}
                        className={cn(
                          'flex items-center gap-3 p-2 rounded-md cursor-pointer transition-colors',
                          selectedTypes.has(type.value)
                            ? 'bg-primary/10'
                            : 'hover:bg-muted'
                        )}
                        onClick={() => toggleType(type.value)}
                      >
                        <Checkbox
                          checked={selectedTypes.has(type.value)}
                          onCheckedChange={() => toggleType(type.value)}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm">{type.label}</p>
                          <p className="text-xs text-muted-foreground truncate">
                            {type.description}
                          </p>
                        </div>
                        {type.has_dependencies && (
                          <Badge variant="outline" className="text-xs">
                            {type.dependencies.length} deps
                          </Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })
        ) : null}
      </div>

      {/* Preview Dialog */}
      <Dialog open={showPreviewDialog} onOpenChange={setShowPreviewDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Import Preview
            </DialogTitle>
            <DialogDescription>
              Review the data that will be imported from starzERP
            </DialogDescription>
          </DialogHeader>
          
          {preview && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{preview.total_source_records}</div>
                    <div className="text-sm text-muted-foreground">Source Records</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{preview.total_existing_records}</div>
                    <div className="text-sm text-muted-foreground">Existing Records</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{preview.estimated_duration_minutes} min</div>
                    <div className="text-sm text-muted-foreground">Est. Duration</div>
                  </CardContent>
                </Card>
              </div>
              
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Entity Type</TableHead>
                    <TableHead className="text-right">Source</TableHead>
                    <TableHead className="text-right">Existing</TableHead>
                    <TableHead className="text-right">Delta</TableHead>
                    <TableHead className="text-right">Est. Imports</TableHead>
                    <TableHead className="text-right">Est. Updates</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.previews.map(p => (
                    <TableRow key={p.entity_type}>
                      <TableCell className="font-medium">{p.entity_type}</TableCell>
                      <TableCell className="text-right">{p.source_count}</TableCell>
                      <TableCell className="text-right">{p.existing_count}</TableCell>
                      <TableCell className="text-right">
                        <span className={cn(
                          p.delta > 0 ? 'text-green-500' : p.delta < 0 ? 'text-red-500' : ''
                        )}>
                          {p.delta > 0 ? '+' : ''}{p.delta}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">{p.estimated_imports}</TableCell>
                      <TableCell className="text-right">{p.estimated_updates}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPreviewDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={executeImport}
              disabled={importing}
              className="bg-rams-orange hover:bg-rams-orange/90"
            >
              {importing ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Start Import
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Result Dialog */}
      <Dialog open={showResultDialog} onOpenChange={setShowResultDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {importResult?.status === 'completed' ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : importResult?.status === 'failed' ? (
                <XCircle className="h-5 w-5 text-red-500" />
              ) : (
                <Loader2 className="h-5 w-5 animate-spin" />
              )}
              Import Results
            </DialogTitle>
            <DialogDescription>
              Batch ID: {importResult?.batch_id}
            </DialogDescription>
          </DialogHeader>
          
          {importResult && (
            <div className="space-y-4">
              <div className="grid grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-green-500">{importResult.total_imported}</div>
                    <div className="text-sm text-muted-foreground">Imported</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-blue-500">{importResult.total_updated}</div>
                    <div className="text-sm text-muted-foreground">Updated</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-red-500">{importResult.total_failed}</div>
                    <div className="text-sm text-muted-foreground">Failed</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{importResult.total_duration_seconds.toFixed(1)}s</div>
                    <div className="text-sm text-muted-foreground">Duration</div>
                  </CardContent>
                </Card>
              </div>
              
              <Accordion type="single" collapsible className="w-full">
                {importResult.entity_results.map((er, idx) => (
                  <AccordionItem key={er.entity_type} value={`item-${idx}`}>
                    <AccordionTrigger>
                      <div className="flex items-center gap-4 flex-1">
                        <span className="font-medium">{er.entity_type}</span>
                        <Badge variant={er.failed > 0 ? 'destructive' : 'default'}>
                          {er.success_rate.toFixed(1)}%
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          {er.imported} imported, {er.updated} updated, {er.failed} failed
                        </span>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="space-y-2">
                        <div className="grid grid-cols-5 gap-2 text-sm">
                          <div>Source: {er.total_source}</div>
                          <div className="text-green-500">Imported: {er.imported}</div>
                          <div className="text-blue-500">Updated: {er.updated}</div>
                          <div className="text-muted-foreground">Skipped: {er.skipped}</div>
                          <div className="text-red-500">Failed: {er.failed}</div>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Duration: {er.duration_seconds.toFixed(2)}s
                        </div>
                        {er.errors.length > 0 && (
                          <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded text-sm">
                            <p className="font-medium text-red-600 dark:text-red-400 mb-1">Errors:</p>
                            <ul className="list-disc list-inside space-y-1">
                              {er.errors.slice(0, 5).map((error, i) => (
                                <li key={i} className="text-red-600 dark:text-red-400 text-xs">{error}</li>
                              ))}
                              {er.errors.length > 5 && (
                                <li className="text-red-600 dark:text-red-400 text-xs">
                                  ... and {er.errors.length - 5} more errors
                                </li>
                              )}
                            </ul>
                          </div>
                        )}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>
          )}
          
          <DialogFooter>
            <Button onClick={() => setShowResultDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Progress Overlay */}
      {importing && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <Card className="w-96">
            <CardContent className="pt-6 text-center space-y-4">
              <Loader2 className="h-12 w-12 animate-spin mx-auto text-rams-orange" />
              <h3 className="text-lg font-semibold">Importing Data...</h3>
              <p className="text-sm text-muted-foreground">
                Please wait while we migrate data from starzERP.
                This may take several minutes.
              </p>
              <Progress value={undefined} className="w-full" />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
