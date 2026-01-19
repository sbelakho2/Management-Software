'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores';
import {
  ArrowLeft,
  Search,
  Shield,
  Brain,
  Eye,
  EyeOff,
  Users,
  Settings,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Edit,
  Save,
  RefreshCw,
  Loader2,
  ChevronDown,
  ChevronRight,
  BarChart3,
  Lightbulb,
  TrendingUp,
  Factory,
  Package,
  Wrench,
  DollarSign,
  FileText,
  Timer,
  Lock,
  Unlock,
  Info,
  Filter,
  Download,
  Upload,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge, BadgeProps } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { cn, formatDate } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

// ============================================================================
// Types and Interfaces
// ============================================================================

interface InsightCategory {
  id: string;
  nameKey: string;
  descriptionKey: string;
  icon: React.ReactNode;
  insights: Insight[];
}

interface Insight {
  id: string;
  nameKey: string;
  descriptionKey: string;
  sensitivity: 'low' | 'medium' | 'high' | 'critical';
  category: string;
}

interface Role {
  id: string;
  name: string;
  nameKey: string;
  level: number;
  descriptionKey: string;
  defaultInsights: string[];
  customInsights: string[];
}

interface RoleInsightMapping {
  roleId: string;
  insightId: string;
  enabled: boolean;
  customized: boolean;
  modifiedAt?: string;
  modifiedBy?: string;
}

interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: 'grant' | 'revoke' | 'bulk_update';
  roleId: string;
  insightId?: string;
  performedBy: string;
  previousValue?: boolean;
  newValue?: boolean;
  reason?: string;
}

// ============================================================================
// Mock Data - Replace with API calls
// ============================================================================

const SENSITIVITY_CONFIG: Record<string, { labelKey: string; variant: BadgeProps['variant']; descriptionKey: string }> = {
  low: { labelKey: 'settings.roleInsights.sensitivity.low', variant: 'success', descriptionKey: 'settings.roleInsights.sensitivity.lowDesc' },
  medium: { labelKey: 'settings.roleInsights.sensitivity.medium', variant: 'warning', descriptionKey: 'settings.roleInsights.sensitivity.mediumDesc' },
  high: { labelKey: 'settings.roleInsights.sensitivity.high', variant: 'danger', descriptionKey: 'settings.roleInsights.sensitivity.highDesc' },
  critical: { labelKey: 'settings.roleInsights.sensitivity.critical', variant: 'destructive', descriptionKey: 'settings.roleInsights.sensitivity.criticalDesc' },
};

const INSIGHT_CATEGORIES: InsightCategory[] = [
  {
    id: 'production',
    nameKey: 'settings.roleInsights.categories.production.name',
    descriptionKey: 'settings.roleInsights.categories.production.description',
    icon: <Factory className="h-4 w-4" />,
    insights: [
      { id: 'production_efficiency', nameKey: 'settings.roleInsights.insights.production_efficiency.name', descriptionKey: 'settings.roleInsights.insights.production_efficiency.description', sensitivity: 'medium', category: 'production' },
      { id: 'production_bottlenecks', nameKey: 'settings.roleInsights.insights.production_bottlenecks.name', descriptionKey: 'settings.roleInsights.insights.production_bottlenecks.description', sensitivity: 'medium', category: 'production' },
      { id: 'downtime_analysis', nameKey: 'settings.roleInsights.insights.downtime_analysis.name', descriptionKey: 'settings.roleInsights.insights.downtime_analysis.description', sensitivity: 'medium', category: 'production' },
      { id: 'capacity_utilization', nameKey: 'settings.roleInsights.insights.capacity_utilization.name', descriptionKey: 'settings.roleInsights.insights.capacity_utilization.description', sensitivity: 'medium', category: 'production' },
      { id: 'production_forecasts', nameKey: 'settings.roleInsights.insights.production_forecasts.name', descriptionKey: 'settings.roleInsights.insights.production_forecasts.description', sensitivity: 'high', category: 'production' },
    ],
  },
  {
    id: 'quality',
    nameKey: 'settings.roleInsights.categories.quality.name',
    descriptionKey: 'settings.roleInsights.categories.quality.description',
    icon: <CheckCircle className="h-4 w-4" />,
    insights: [
      { id: 'quality_metrics', nameKey: 'settings.roleInsights.insights.quality_metrics.name', descriptionKey: 'settings.roleInsights.insights.quality_metrics.description', sensitivity: 'medium', category: 'quality' },
      { id: 'spc_analysis', nameKey: 'settings.roleInsights.insights.spc_analysis.name', descriptionKey: 'settings.roleInsights.insights.spc_analysis.description', sensitivity: 'medium', category: 'quality' },
      { id: 'defect_predictions', nameKey: 'settings.roleInsights.insights.defect_predictions.name', descriptionKey: 'settings.roleInsights.insights.defect_predictions.description', sensitivity: 'high', category: 'quality' },
      { id: 'compliance_status', nameKey: 'settings.roleInsights.insights.compliance_status.name', descriptionKey: 'settings.roleInsights.insights.compliance_status.description', sensitivity: 'high', category: 'quality' },
      { id: 'audit_readiness', nameKey: 'settings.roleInsights.insights.audit_readiness.name', descriptionKey: 'settings.roleInsights.insights.audit_readiness.description', sensitivity: 'high', category: 'quality' },
    ],
  },
  {
    id: 'inventory',
    nameKey: 'settings.roleInsights.categories.inventory.name',
    descriptionKey: 'settings.roleInsights.categories.inventory.description',
    icon: <Package className="h-4 w-4" />,
    insights: [
      { id: 'inventory_levels', nameKey: 'settings.roleInsights.insights.inventory_levels.name', descriptionKey: 'settings.roleInsights.insights.inventory_levels.description', sensitivity: 'medium', category: 'inventory' },
      { id: 'reorder_recommendations', nameKey: 'settings.roleInsights.insights.reorder_recommendations.name', descriptionKey: 'settings.roleInsights.insights.reorder_recommendations.description', sensitivity: 'medium', category: 'inventory' },
      { id: 'supplier_performance', nameKey: 'settings.roleInsights.insights.supplier_performance.name', descriptionKey: 'settings.roleInsights.insights.supplier_performance.description', sensitivity: 'high', category: 'inventory' },
      { id: 'supply_chain_risks', nameKey: 'settings.roleInsights.insights.supply_chain_risks.name', descriptionKey: 'settings.roleInsights.insights.supply_chain_risks.description', sensitivity: 'high', category: 'inventory' },
      { id: 'cost_optimization', nameKey: 'settings.roleInsights.insights.cost_optimization.name', descriptionKey: 'settings.roleInsights.insights.cost_optimization.description', sensitivity: 'high', category: 'inventory' },
    ],
  },
  {
    id: 'maintenance',
    nameKey: 'settings.roleInsights.categories.maintenance.name',
    descriptionKey: 'settings.roleInsights.categories.maintenance.description',
    icon: <Wrench className="h-4 w-4" />,
    insights: [
      { id: 'equipment_health', nameKey: 'settings.roleInsights.insights.equipment_health.name', descriptionKey: 'settings.roleInsights.insights.equipment_health.description', sensitivity: 'low', category: 'maintenance' },
      { id: 'predictive_maintenance', nameKey: 'settings.roleInsights.insights.predictive_maintenance.name', descriptionKey: 'settings.roleInsights.insights.predictive_maintenance.description', sensitivity: 'medium', category: 'maintenance' },
      { id: 'maintenance_costs', nameKey: 'settings.roleInsights.insights.maintenance_costs.name', descriptionKey: 'settings.roleInsights.insights.maintenance_costs.description', sensitivity: 'high', category: 'maintenance' },
      { id: 'asset_lifecycle', nameKey: 'settings.roleInsights.insights.asset_lifecycle.name', descriptionKey: 'settings.roleInsights.insights.asset_lifecycle.description', sensitivity: 'high', category: 'maintenance' },
      { id: 'reliability_metrics', nameKey: 'settings.roleInsights.insights.reliability_metrics.name', descriptionKey: 'settings.roleInsights.insights.reliability_metrics.description', sensitivity: 'medium', category: 'maintenance' },
    ],
  },
  {
    id: 'financial',
    nameKey: 'settings.roleInsights.categories.financial.name',
    descriptionKey: 'settings.roleInsights.categories.financial.description',
    icon: <DollarSign className="h-4 w-4" />,
    insights: [
      { id: 'cost_analysis', nameKey: 'settings.roleInsights.insights.cost_analysis.name', descriptionKey: 'settings.roleInsights.insights.cost_analysis.description', sensitivity: 'high', category: 'financial' },
      { id: 'profitability', nameKey: 'settings.roleInsights.insights.profitability.name', descriptionKey: 'settings.roleInsights.insights.profitability.description', sensitivity: 'critical', category: 'financial' },
      { id: 'margin_trends', nameKey: 'settings.roleInsights.insights.margin_trends.name', descriptionKey: 'settings.roleInsights.insights.margin_trends.description', sensitivity: 'critical', category: 'financial' },
      { id: 'revenue_forecasts', nameKey: 'settings.roleInsights.insights.revenue_forecasts.name', descriptionKey: 'settings.roleInsights.insights.revenue_forecasts.description', sensitivity: 'critical', category: 'financial' },
      { id: 'cash_flow_insights', nameKey: 'settings.roleInsights.insights.cash_flow_insights.name', descriptionKey: 'settings.roleInsights.insights.cash_flow_insights.description', sensitivity: 'critical', category: 'financial' },
    ],
  },
  {
    id: 'workforce',
    nameKey: 'settings.roleInsights.categories.workforce.name',
    descriptionKey: 'settings.roleInsights.categories.workforce.description',
    icon: <Users className="h-4 w-4" />,
    insights: [
      { id: 'workforce_productivity', nameKey: 'settings.roleInsights.insights.workforce_productivity.name', descriptionKey: 'settings.roleInsights.insights.workforce_productivity.description', sensitivity: 'medium', category: 'workforce' },
      { id: 'attendance_patterns', nameKey: 'settings.roleInsights.insights.attendance_patterns.name', descriptionKey: 'settings.roleInsights.insights.attendance_patterns.description', sensitivity: 'high', category: 'workforce' },
      { id: 'skill_gaps', nameKey: 'settings.roleInsights.insights.skill_gaps.name', descriptionKey: 'settings.roleInsights.insights.skill_gaps.description', sensitivity: 'medium', category: 'workforce' },
      { id: 'retention_risks', nameKey: 'settings.roleInsights.insights.retention_risks.name', descriptionKey: 'settings.roleInsights.insights.retention_risks.description', sensitivity: 'critical', category: 'workforce' },
      { id: 'compensation_insights', nameKey: 'settings.roleInsights.insights.compensation_insights.name', descriptionKey: 'settings.roleInsights.insights.compensation_insights.description', sensitivity: 'critical', category: 'workforce' },
    ],
  },
  {
    id: 'sales',
    nameKey: 'settings.roleInsights.categories.sales.name',
    descriptionKey: 'settings.roleInsights.categories.sales.description',
    icon: <TrendingUp className="h-4 w-4" />,
    insights: [
      { id: 'sales_pipeline', nameKey: 'settings.roleInsights.insights.sales_pipeline.name', descriptionKey: 'settings.roleInsights.insights.sales_pipeline.description', sensitivity: 'medium', category: 'sales' },
      { id: 'win_loss_analysis', nameKey: 'settings.roleInsights.insights.win_loss_analysis.name', descriptionKey: 'settings.roleInsights.insights.win_loss_analysis.description', sensitivity: 'high', category: 'sales' },
      { id: 'customer_insights', nameKey: 'settings.roleInsights.insights.customer_insights.name', descriptionKey: 'settings.roleInsights.insights.customer_insights.description', sensitivity: 'high', category: 'sales' },
      { id: 'quote_optimization', nameKey: 'settings.roleInsights.insights.quote_optimization.name', descriptionKey: 'settings.roleInsights.insights.quote_optimization.description', sensitivity: 'high', category: 'sales' },
      { id: 'market_trends', nameKey: 'settings.roleInsights.insights.market_trends.name', descriptionKey: 'settings.roleInsights.insights.market_trends.description', sensitivity: 'high', category: 'sales' },
    ],
  },
  {
    id: 'strategic',
    nameKey: 'settings.roleInsights.categories.strategic.name',
    descriptionKey: 'settings.roleInsights.categories.strategic.description',
    icon: <Lightbulb className="h-4 w-4" />,
    insights: [
      { id: 'kpi_dashboard', nameKey: 'settings.roleInsights.insights.kpi_dashboard.name', descriptionKey: 'settings.roleInsights.insights.kpi_dashboard.description', sensitivity: 'high', category: 'strategic' },
      { id: 'competitive_analysis', nameKey: 'settings.roleInsights.insights.competitive_analysis.name', descriptionKey: 'settings.roleInsights.insights.competitive_analysis.description', sensitivity: 'critical', category: 'strategic' },
      { id: 'strategic_recommendations', nameKey: 'settings.roleInsights.insights.strategic_recommendations.name', descriptionKey: 'settings.roleInsights.insights.strategic_recommendations.description', sensitivity: 'critical', category: 'strategic' },
      { id: 'risk_assessment', nameKey: 'settings.roleInsights.insights.risk_assessment.name', descriptionKey: 'settings.roleInsights.insights.risk_assessment.description', sensitivity: 'critical', category: 'strategic' },
      { id: 'scenario_planning', nameKey: 'settings.roleInsights.insights.scenario_planning.name', descriptionKey: 'settings.roleInsights.insights.scenario_planning.description', sensitivity: 'critical', category: 'strategic' },
    ],
  },
];

const ROLES: Role[] = [
  { id: 'admin', name: 'admin', nameKey: 'settings.roleInsights.roles.admin.name', level: 0, descriptionKey: 'settings.roleInsights.roles.admin.description', defaultInsights: ['*'], customInsights: [] },
  { id: 'ceo', name: 'ceo', nameKey: 'settings.roleInsights.roles.ceo.name', level: 5, descriptionKey: 'settings.roleInsights.roles.ceo.description', defaultInsights: ['*'], customInsights: [] },
  { id: 'gm', name: 'gm', nameKey: 'settings.roleInsights.roles.gm.name', level: 10, descriptionKey: 'settings.roleInsights.roles.gm.description', defaultInsights: ['production_*', 'quality_*', 'inventory_*', 'kpi_dashboard'], customInsights: [] },
  { id: 'exec', name: 'exec', nameKey: 'settings.roleInsights.roles.exec.name', level: 15, descriptionKey: 'settings.roleInsights.roles.exec.description', defaultInsights: ['kpi_dashboard', 'strategic_*', 'financial_*'], customInsights: [] },
  { id: 'finance', name: 'finance', nameKey: 'settings.roleInsights.roles.finance.name', level: 20, descriptionKey: 'settings.roleInsights.roles.finance.description', defaultInsights: ['financial_*', 'cost_*'], customInsights: [] },
  { id: 'hr', name: 'hr', nameKey: 'settings.roleInsights.roles.hr.name', level: 20, descriptionKey: 'settings.roleInsights.roles.hr.description', defaultInsights: ['workforce_*'], customInsights: [] },
  { id: 'ops', name: 'ops', nameKey: 'settings.roleInsights.roles.ops.name', level: 20, descriptionKey: 'settings.roleInsights.roles.ops.description', defaultInsights: ['production_*', 'quality_*', 'inventory_*'], customInsights: [] },
  { id: 'quality', name: 'quality', nameKey: 'settings.roleInsights.roles.quality.name', level: 20, descriptionKey: 'settings.roleInsights.roles.quality.description', defaultInsights: ['quality_*', 'spc_*', 'compliance_*'], customInsights: [] },
  { id: 'it', name: 'it', nameKey: 'settings.roleInsights.roles.it.name', level: 20, descriptionKey: 'settings.roleInsights.roles.it.description', defaultInsights: ['equipment_health', 'reliability_*'], customInsights: [] },
  { id: 'accountant', name: 'accountant', nameKey: 'settings.roleInsights.roles.accountant.name', level: 30, descriptionKey: 'settings.roleInsights.roles.accountant.description', defaultInsights: ['cost_analysis', 'cash_flow_insights'], customInsights: [] },
  { id: 'auditor', name: 'auditor', nameKey: 'settings.roleInsights.roles.auditor.name', level: 30, descriptionKey: 'settings.roleInsights.roles.auditor.description', defaultInsights: ['compliance_*', 'audit_*', 'financial_*'], customInsights: [] },
  { id: 'sales_engineer', name: 'sales_engineer', nameKey: 'settings.roleInsights.roles.sales_engineer.name', level: 35, descriptionKey: 'settings.roleInsights.roles.sales_engineer.description', defaultInsights: ['quote_optimization', 'customer_insights'], customInsights: [] },
  { id: 'estimator', name: 'estimator', nameKey: 'settings.roleInsights.roles.estimator.name', level: 35, descriptionKey: 'settings.roleInsights.roles.estimator.description', defaultInsights: ['cost_analysis', 'quote_optimization'], customInsights: [] },
  { id: 'sales', name: 'sales', nameKey: 'settings.roleInsights.roles.sales.name', level: 40, descriptionKey: 'settings.roleInsights.roles.sales.description', defaultInsights: ['sales_*', 'customer_insights'], customInsights: [] },
  { id: 'purchasing', name: 'purchasing', nameKey: 'settings.roleInsights.roles.purchasing.name', level: 40, descriptionKey: 'settings.roleInsights.roles.purchasing.description', defaultInsights: ['inventory_*', 'supplier_*'], customInsights: [] },
  { id: 'supply_chain', name: 'supply_chain', nameKey: 'settings.roleInsights.roles.supply_chain.name', level: 40, descriptionKey: 'settings.roleInsights.roles.supply_chain.description', defaultInsights: ['inventory_*', 'supply_chain_*'], customInsights: [] },
  { id: 'logistics', name: 'logistics', nameKey: 'settings.roleInsights.roles.logistics.name', level: 45, descriptionKey: 'settings.roleInsights.roles.logistics.description', defaultInsights: ['inventory_levels', 'reorder_recommendations'], customInsights: [] },
  { id: 'warehouse', name: 'warehouse', nameKey: 'settings.roleInsights.roles.warehouse.name', level: 45, descriptionKey: 'settings.roleInsights.roles.warehouse.description', defaultInsights: ['inventory_levels'], customInsights: [] },
  { id: 'maintenance', name: 'maintenance', nameKey: 'settings.roleInsights.roles.maintenance.name', level: 50, descriptionKey: 'settings.roleInsights.roles.maintenance.description', defaultInsights: ['equipment_*', 'predictive_*', 'reliability_*'], customInsights: [] },
  { id: 'engineering', name: 'engineering', nameKey: 'settings.roleInsights.roles.engineering.name', level: 50, descriptionKey: 'settings.roleInsights.roles.engineering.description', defaultInsights: ['production_*', 'quality_*', 'equipment_*'], customInsights: [] },
  { id: 'supervisor', name: 'supervisor', nameKey: 'settings.roleInsights.roles.supervisor.name', level: 60, descriptionKey: 'settings.roleInsights.roles.supervisor.description', defaultInsights: ['production_efficiency', 'workforce_productivity', 'quality_metrics'], customInsights: [] },
  { id: 'team_lead', name: 'team_lead', nameKey: 'settings.roleInsights.roles.team_lead.name', level: 70, descriptionKey: 'settings.roleInsights.roles.team_lead.description', defaultInsights: ['production_efficiency', 'quality_metrics'], customInsights: [] },
  { id: 'operator', name: 'operator', nameKey: 'settings.roleInsights.roles.operator.name', level: 80, descriptionKey: 'settings.roleInsights.roles.operator.description', defaultInsights: ['production_efficiency', 'equipment_health'], customInsights: [] },
  { id: 'viewer', name: 'viewer', nameKey: 'settings.roleInsights.roles.viewer.name', level: 100, descriptionKey: 'settings.roleInsights.roles.viewer.description', defaultInsights: ['kpi_dashboard'], customInsights: [] },
];

const mockAuditLog: AuditLogEntry[] = [
  { id: '1', timestamp: '2024-01-15T14:30:00Z', action: 'grant', roleId: 'supervisor', insightId: 'defect_predictions', performedBy: 'admin@sensei.ma', previousValue: false, newValue: true, reason: 'settings.roleInsights.audit.sampleReasons.qualityImprovement' },
  { id: '2', timestamp: '2024-01-15T12:45:00Z', action: 'revoke', roleId: 'sales', insightId: 'profitability', performedBy: 'admin@sensei.ma', previousValue: true, newValue: false, reason: 'settings.roleInsights.audit.sampleReasons.dataSensitivity' },
  { id: '3', timestamp: '2024-01-14T18:20:00Z', action: 'bulk_update', roleId: 'maintenance', performedBy: 'admin@sensei.ma', reason: 'settings.roleInsights.audit.sampleReasons.expandedMaintenance' },
];

// ============================================================================
// Component: Role Insight Matrix
// ============================================================================

function RoleInsightMatrix({
  roles,
  categories,
  mappings,
  onToggle,
  selectedRole,
  onSelectRole,
}: {
  roles: Role[];
  categories: InsightCategory[];
  mappings: Map<string, boolean>;
  onToggle: (roleId: string, insightId: string, enabled: boolean) => void;
  selectedRole: string | null;
  onSelectRole: (roleId: string | null) => void;
}) {
  const { t } = useI18n();
  const [expandedCategories, setExpandedCategories] = React.useState<Set<string>>(new Set(['production', 'quality']));
  const [searchQuery, setSearchQuery] = React.useState('');
  const [sensitivityFilter, setSensitivityFilter] = React.useState<string>('all');

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  const getInsightName = (insight: Insight) => t(insight.nameKey);
  const getInsightDescription = (insight: Insight) => t(insight.descriptionKey);
  const getCategoryName = (category: InsightCategory) => t(category.nameKey);

  const filteredCategories = categories.map((cat) => ({
    ...cat,
    insights: cat.insights.filter((insight) => {
      const matchesSearch = searchQuery === '' || 
        getInsightName(insight).toLowerCase().includes(searchQuery.toLowerCase()) ||
        getInsightDescription(insight).toLowerCase().includes(searchQuery.toLowerCase());
      const matchesSensitivity = sensitivityFilter === 'all' || insight.sensitivity === sensitivityFilter;
      return matchesSearch && matchesSensitivity;
    }),
  })).filter((cat) => cat.insights.length > 0);

  const getMappingKey = (roleId: string, insightId: string) => `${roleId}:${insightId}`;
  
  const isEnabled = (roleId: string, insightId: string) => {
    const role = roles.find((r) => r.id === roleId);
    if (!role) return false;
    if (role.id === 'admin' || role.id === 'ceo') return true;
    const key = getMappingKey(roleId, insightId);
    return mappings.get(key) ?? role.defaultInsights.some((pattern) => {
      if (pattern === '*') return true;
      if (pattern.endsWith('*')) {
        return insightId.startsWith(pattern.slice(0, -1));
      }
      return pattern === insightId;
    });
  };

  const displayRoles = selectedRole ? roles.filter((r) => r.id === selectedRole) : roles;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={t('settings.roleInsights.filters.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        <Select value={sensitivityFilter} onValueChange={setSensitivityFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder={t('settings.roleInsights.filters.sensitivityPlaceholder')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('settings.roleInsights.filters.allSensitivities')}</SelectItem>
            <SelectItem value="low">{t('settings.roleInsights.sensitivity.low')}</SelectItem>
            <SelectItem value="medium">{t('settings.roleInsights.sensitivity.medium')}</SelectItem>
            <SelectItem value="high">{t('settings.roleInsights.sensitivity.high')}</SelectItem>
            <SelectItem value="critical">{t('settings.roleInsights.sensitivity.critical')}</SelectItem>
          </SelectContent>
        </Select>
        <Select value={selectedRole || 'all'} onValueChange={(v) => onSelectRole(v === 'all' ? null : v)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder={t('settings.roleInsights.filters.rolePlaceholder')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('settings.roleInsights.filters.allRoles')}</SelectItem>
            {roles.map((role) => (
              <SelectItem key={role.id} value={role.id}>
                {t(role.nameKey)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Matrix */}
      <ScrollArea className="h-[600px] border rounded-lg">
        <Table>
          <TableHeader className="sticky top-0 bg-background z-10">
            <TableRow>
              <TableHead className="w-[300px] sticky left-0 bg-background">{t('settings.roleInsights.table.insightHeader')}</TableHead>
              {displayRoles.map((role) => (
                <TableHead key={role.id} className="text-center min-w-[100px]">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="cursor-help">{t(role.nameKey)}</span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="font-medium">{t(role.descriptionKey)}</p>
                        <p className="text-xs text-muted-foreground">{t('settings.roleInsights.tooltip.level', { level: role.level })}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredCategories.map((category) => (
              <React.Fragment key={category.id}>
                <TableRow className="bg-muted/50 hover:bg-muted/70">
                  <TableCell colSpan={displayRoles.length + 1} className="sticky left-0 bg-muted/50">
                    <Collapsible open={expandedCategories.has(category.id)}>
                      <CollapsibleTrigger
                        className="flex items-center gap-2 font-medium w-full text-left"
                        onClick={() => toggleCategory(category.id)}
                      >
                        {expandedCategories.has(category.id) ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                        {category.icon}
                        <span>{getCategoryName(category)}</span>
                        <Badge variant="secondary" className="ml-2">{category.insights.length}</Badge>
                      </CollapsibleTrigger>
                    </Collapsible>
                  </TableCell>
                </TableRow>
                {expandedCategories.has(category.id) && category.insights.map((insight) => (
                  <TableRow key={insight.id}>
                    <TableCell className="sticky left-0 bg-background">
                      <div className="flex items-center gap-2">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{getInsightName(insight)}</span>
                                <Badge variant={SENSITIVITY_CONFIG[insight.sensitivity].variant}>
                                  {t(SENSITIVITY_CONFIG[insight.sensitivity].labelKey)}
                                </Badge>
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>{getInsightDescription(insight)}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    </TableCell>
                    {displayRoles.map((role) => {
                      const enabled = isEnabled(role.id, insight.id);
                      const isLocked = role.id === 'admin' || role.id === 'ceo';
                      return (
                        <TableCell key={`${role.id}-${insight.id}`} className="text-center">
                          {isLocked ? (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Lock className="h-4 w-4 mx-auto text-muted-foreground" />
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>{t('settings.roleInsights.tooltip.locked', { role: t(role.nameKey) })}</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          ) : (
                            <Checkbox
                              checked={enabled}
                              onCheckedChange={(checked) => onToggle(role.id, insight.id, checked === true)}
                              className="mx-auto"
                            />
                          )}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
    </div>
  );
}

// ============================================================================
// Component: Role Card
// ============================================================================

function RoleCard({
  role,
  categories,
  mappings,
  onEdit,
}: {
  role: Role;
  categories: InsightCategory[];
  mappings: Map<string, boolean>;
  onEdit: (roleId: string) => void;
}) {
  const { t } = useI18n();
  const allInsights = categories.flatMap((c) => c.insights);
  const enabledCount = allInsights.filter((insight) => {
    if (role.id === 'admin' || role.id === 'ceo') return true;
    const key = `${role.id}:${insight.id}`;
    return mappings.get(key) ?? role.defaultInsights.some((pattern) => {
      if (pattern === '*') return true;
      if (pattern.endsWith('*')) return insight.id.startsWith(pattern.slice(0, -1));
      return pattern === insight.id;
    });
  }).length;

  const getLevelColor = (level: number) => {
    if (level <= 10) return 'text-red-500';
    if (level <= 30) return 'text-orange-500';
    if (level <= 50) return 'text-yellow-500';
    if (level <= 70) return 'text-blue-500';
    return 'text-gray-500';
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{t(role.nameKey)}</CardTitle>
          <Badge variant={role.level <= 20 ? 'danger' : role.level <= 50 ? 'warning' : 'secondary'}>
            {t('settings.roleInsights.roleCard.levelBadge', { level: role.level })}
          </Badge>
        </div>
        <CardDescription>{t(role.descriptionKey)}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{t('settings.roleInsights.roleCard.insightsAccess')}</span>
            <span className="font-medium">{enabledCount} / {allInsights.length}</span>
          </div>
          <div className="w-full bg-secondary rounded-full h-2">
            <div
              className={cn('h-2 rounded-full transition-all', getLevelColor(role.level).replace('text-', 'bg-'))}
              style={{ width: `${(enabledCount / allInsights.length) * 100}%` }}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => onEdit(role.id)}
            disabled={role.id === 'admin' || role.id === 'ceo'}
          >
            {role.id === 'admin' || role.id === 'ceo' ? (
              <>
                <Lock className="h-4 w-4 mr-2" />
                {t('settings.roleInsights.roleCard.fullAccess')}
              </>
            ) : (
              <>
                <Edit className="h-4 w-4 mr-2" />
                {t('settings.roleInsights.roleCard.editMappings')}
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Component: Audit Log Table
// ============================================================================

function AuditLogTable({ logs }: { logs: AuditLogEntry[] }) {
  const { t } = useI18n();
  const getActionBadge = (action: AuditLogEntry['action']) => {
    switch (action) {
      case 'grant':
        return <Badge variant="success"><CheckCircle className="h-3 w-3 mr-1" />{t('settings.roleInsights.audit.actions.grant')}</Badge>;
      case 'revoke':
        return <Badge variant="danger"><XCircle className="h-3 w-3 mr-1" />{t('settings.roleInsights.audit.actions.revoke')}</Badge>;
      case 'bulk_update':
        return <Badge variant="warning"><RefreshCw className="h-3 w-3 mr-1" />{t('settings.roleInsights.audit.actions.bulkUpdate')}</Badge>;
    }
  };

  const getRoleLabel = (roleId: string) => {
    const role = ROLES.find((r) => r.id === roleId);
    return role ? t(role.nameKey) : roleId;
  };

  const getInsightLabel = (insightId?: string) => {
    if (!insightId) return t('na');
    const insight = INSIGHT_CATEGORIES.flatMap((c) => c.insights).find((item) => item.id === insightId);
    return insight ? t(insight.nameKey) : insightId;
  };

  const getReasonLabel = (reason?: string) => {
    if (!reason) return t('na');
    if (reason.startsWith('settings.')) return t(reason);
    return reason;
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t('settings.roleInsights.audit.headers.timestamp')}</TableHead>
          <TableHead>{t('settings.roleInsights.audit.headers.action')}</TableHead>
          <TableHead>{t('settings.roleInsights.audit.headers.role')}</TableHead>
          <TableHead>{t('settings.roleInsights.audit.headers.insight')}</TableHead>
          <TableHead>{t('settings.roleInsights.audit.headers.performedBy')}</TableHead>
          <TableHead>{t('settings.roleInsights.audit.headers.reason')}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {logs.map((log) => (
          <TableRow key={log.id}>
            <TableCell className="whitespace-nowrap">{formatDate(log.timestamp)}</TableCell>
            <TableCell>{getActionBadge(log.action)}</TableCell>
            <TableCell className="font-medium">{getRoleLabel(log.roleId)}</TableCell>
            <TableCell>{getInsightLabel(log.insightId)}</TableCell>
            <TableCell>{log.performedBy}</TableCell>
            <TableCell className="max-w-[200px] truncate">{getReasonLabel(log.reason)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function RoleInsightsPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { t } = useI18n();
  
  const [isLoading, setIsLoading] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [hasChanges, setHasChanges] = React.useState(false);
  const [selectedRole, setSelectedRole] = React.useState<string | null>(null);
  const [mappings, setMappings] = React.useState<Map<string, boolean>>(new Map());
  const [showSaveDialog, setShowSaveDialog] = React.useState(false);
  const [saveReason, setSaveReason] = React.useState('');

  // Check admin access
  React.useEffect(() => {
    if (user && user.role !== 'admin' && user.role !== 'ceo') {
      router.push('/settings');
    }
  }, [user, router]);

  const handleToggle = (roleId: string, insightId: string, enabled: boolean) => {
    setMappings((prev) => {
      const next = new Map(prev);
      next.set(`${roleId}:${insightId}`, enabled);
      return next;
    });
    setHasChanges(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Would save to API
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setHasChanges(false);
      setShowSaveDialog(false);
      setSaveReason('');
    } catch (error) {
      console.error('Failed to save mappings:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleExport = () => {
    const exportData = {
      timestamp: new Date().toISOString(),
      roles: ROLES.map((role) => ({
        id: role.id,
        name: t(role.nameKey),
        insights: INSIGHT_CATEGORIES.flatMap((c) => c.insights)
          .filter((insight) => {
            if (role.id === 'admin' || role.id === 'ceo') return true;
            const key = `${role.id}:${insight.id}`;
            return mappings.get(key) ?? role.defaultInsights.some((pattern) => {
              if (pattern === '*') return true;
              if (pattern.endsWith('*')) return insight.id.startsWith(pattern.slice(0, -1));
              return pattern === insight.id;
            });
          })
          .map((i) => i.id),
      })),
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${t('settings.roleInsights.exportFilePrefix')}-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="container max-w-7xl py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{t('settings.roleInsights.title')}</h1>
            <p className="text-muted-foreground">{t('settings.roleInsights.subtitle')}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            {t('settings.roleInsights.export')}
          </Button>
          {hasChanges && (
            <Button onClick={() => setShowSaveDialog(true)} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-2" />
              )}
              {t('settings.roleInsights.saveChanges')}
            </Button>
          )}
        </div>
      </div>

      {/* Info Banner */}
      <Card className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
        <CardContent className="flex items-start gap-3 py-4">
          <Info className="h-5 w-5 text-blue-500 mt-0.5" />
          <div className="space-y-1">
            <p className="font-medium text-blue-900 dark:text-blue-100">{t('settings.roleInsights.infoTitle')}</p>
            <p className="text-sm text-blue-700 dark:text-blue-300">{t('settings.roleInsights.infoBody')}</p>
          </div>
        </CardContent>
      </Card>

      {/* Main Content */}
      <Tabs defaultValue="matrix" className="space-y-4">
        <TabsList>
          <TabsTrigger value="matrix">
            <BarChart3 className="h-4 w-4 mr-2" />
            {t('settings.roleInsights.tabs.matrix')}
          </TabsTrigger>
          <TabsTrigger value="roles">
            <Users className="h-4 w-4 mr-2" />
            {t('settings.roleInsights.tabs.roles')}
          </TabsTrigger>
          <TabsTrigger value="audit">
            <FileText className="h-4 w-4 mr-2" />
            {t('settings.roleInsights.tabs.audit')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="matrix" className="space-y-4">
          <RoleInsightMatrix
            roles={ROLES}
            categories={INSIGHT_CATEGORIES}
            mappings={mappings}
            onToggle={handleToggle}
            selectedRole={selectedRole}
            onSelectRole={setSelectedRole}
          />
        </TabsContent>

        <TabsContent value="roles" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {ROLES.map((role) => (
              <RoleCard
                key={role.id}
                role={role}
                categories={INSIGHT_CATEGORIES}
                mappings={mappings}
                onEdit={(roleId) => {
                  setSelectedRole(roleId);
                  // Switch to matrix view with role selected
                  const tabsElement = document.querySelector('[data-state="active"][value="matrix"]');
                  if (!tabsElement) {
                    document.querySelector('[value="matrix"]')?.dispatchEvent(new Event('click'));
                  }
                }}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="audit" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.roleInsights.audit.title')}</CardTitle>
              <CardDescription>
                {t('settings.roleInsights.audit.description')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AuditLogTable logs={mockAuditLog} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Save Dialog */}
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('settings.roleInsights.saveDialog.title')}</DialogTitle>
            <DialogDescription>
              {t('settings.roleInsights.saveDialog.description')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="reason">{t('settings.roleInsights.saveDialog.reasonLabel')}</Label>
              <Input
                id="reason"
                placeholder={t('settings.roleInsights.saveDialog.reasonPlaceholder')}
                value={saveReason}
                onChange={(e) => setSaveReason(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSaveDialog(false)}>
              {t('settings.roleInsights.saveDialog.cancel')}
            </Button>
            <Button onClick={handleSave} disabled={!saveReason.trim() || isSaving}>
              {isSaving ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-2" />
              )}
              {t('settings.roleInsights.saveDialog.saveAudit')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
