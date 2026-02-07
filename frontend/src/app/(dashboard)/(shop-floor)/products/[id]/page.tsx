'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  Edit,
  MoreHorizontal,
  Package,
  DollarSign,
  TrendingUp,
  Boxes,
  Clock,
  Copy,
  Archive,
  Layers,
  BarChart3,
  AlertTriangle,
  History,
  FileText,
  Settings,
  Plus,
  Minus,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn, formatCurrency, formatNumber, formatDate } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { useI18n } from '@/contexts/i18n-context';

interface BOMItem {
  id: string;
  partNumber: string;
  name: string;
  quantity: number;
  unitOfMeasure: string;
  unitCost: number;
}

interface InventoryTransaction {
  id: string;
  type: 'in' | 'out' | 'adjustment';
  quantity: number;
  reference: string;
  notes?: string;
  createdAt: string;
  createdBy: string;
}

interface Product {
  id: string;
  partNumber: string;
  name: string;
  description: string;
  category: string;
  status: 'active' | 'inactive' | 'discontinued';
  unitOfMeasure: string;
  standardCost: number;
  listPrice: number;
  inventoryQty: number;
  reorderPoint: number;
  leadTimeDays: number;
  minimumOrderQty: number;
  specifications?: Record<string, string>;
  bom: BOMItem[];
  recentTransactions: InventoryTransaction[];
  stats: {
    totalSold: number;
    revenue: number;
    quotedCount: number;
    wonCount: number;
  };
  createdAt: string;
  updatedAt: string;
}

const mockProduct: Product = {
  id: '1',
  partNumber: 'AER-001',
  name: 'Precision Bracket Type A',
  description: 'High-precision aluminum bracket for aerospace applications. Manufactured from 6061-T6 aluminum with tight tolerances for critical assemblies.',
  category: 'Brackets',
  status: 'active',
  unitOfMeasure: 'pcs',
  standardCost: 145.00,
  listPrice: 245.00,
  inventoryQty: 500,
  reorderPoint: 100,
  leadTimeDays: 21,
  minimumOrderQty: 50,
  specifications: {
    'Material': '6061-T6 Aluminum',
    'Finish': 'Type II Anodize',
    'Tolerance': '±0.005"',
    'Weight': '0.45 kg',
    'Dimensions': '150mm x 75mm x 25mm',
    'Certification': 'AS9100D',
  },
  bom: [
    { id: '1', partNumber: 'RAW-AL-6061', name: 'Aluminum Bar 6061-T6', quantity: 0.75, unitOfMeasure: 'kg', unitCost: 45.00 },
    { id: '2', partNumber: 'FST-100', name: 'Insert Nut M6', quantity: 4, unitOfMeasure: 'pcs', unitCost: 2.50 },
    { id: '3', partNumber: 'CHM-ANOD', name: 'Anodizing Service', quantity: 1, unitOfMeasure: 'pcs', unitCost: 25.00 },
  ],
  recentTransactions: [
    { id: '1', type: 'out', quantity: -50, reference: 'WO-2024-0089', notes: 'Work order shipment', createdAt: '2024-01-10T14:30:00Z', createdBy: 'John Doe' },
    { id: '2', type: 'in', quantity: 200, reference: 'PO-2024-0045', notes: 'Received from production', createdAt: '2024-01-08T09:15:00Z', createdBy: 'Maria Garcia' },
    { id: '3', type: 'adjustment', quantity: -5, reference: 'INV-ADJ-001', notes: 'Inventory count adjustment', createdAt: '2024-01-05T11:00:00Z', createdBy: 'Sarah Chen' },
    { id: '4', type: 'out', quantity: -100, reference: 'WO-2024-0078', notes: 'Work order shipment', createdAt: '2024-01-03T16:45:00Z', createdBy: 'John Doe' },
  ],
  stats: {
    totalSold: 2450,
    revenue: 600250,
    quotedCount: 45,
    wonCount: 32,
  },
  createdAt: '2022-03-15',
  updatedAt: '2024-01-10T14:30:00Z',
};

const statusConfig = {
  active: { labelKey: 'common.active', variant: 'success' as const },
  inactive: { labelKey: 'common.inactive', variant: 'secondary' as const },
  discontinued: { labelKey: 'common.discontinued', variant: 'danger' as const },
};

function ProductDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10" />
        <Skeleton className="h-8 w-48" />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Skeleton className="h-48" />
          <Skeleton className="h-64" />
        </div>
        <div className="space-y-6">
          <Skeleton className="h-48" />
          <Skeleton className="h-32" />
        </div>
      </div>
    </div>
  );
}

import { useProductStore } from '@/stores/products';

export default function ProductDetailPage() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useParams();
  const { toast } = useToast();
  const { currentProduct, fetchProduct } = useProductStore();
  const [isLoading, setIsLoading] = React.useState(true);
  const [product, setProduct] = React.useState<Product | null>(null);
  const [showAdjustDialog, setShowAdjustDialog] = React.useState(false);
  const [adjustmentQty, setAdjustmentQty] = React.useState(0);
  const [adjustmentNotes, setAdjustmentNotes] = React.useState('');
  const [isEditing, setIsEditing] = React.useState(false);

  React.useEffect(() => {
    const loadData = async () => {
      if (params.id) {
        setIsLoading(true);
        try {
          await fetchProduct(Number(params.id));
        } catch (err) {
          console.error('Failed to load product:', err);
          // Fallback to mock
          setProduct(mockProduct);
        } finally {
          setIsLoading(false);
        }
      }
    };
    loadData();
  }, [params.id, fetchProduct]);

  React.useEffect(() => {
    if (currentProduct) {
      setProduct({
        ...currentProduct,
        id: String(currentProduct.id),
        partNumber: currentProduct.part_number,
        unitOfMeasure: currentProduct.unit_of_measure,
        standardCost: currentProduct.standard_cost,
        listPrice: currentProduct.list_price,
        inventoryQty: (currentProduct as any).inventory_qty || 0,
        reorderPoint: currentProduct.reorder_point,
        leadTimeDays: currentProduct.lead_time_days,
        minimumOrderQty: (currentProduct as any).minimum_order_qty || 0,
        bom: (currentProduct as any).bom || [],
        recentTransactions: (currentProduct as any).recent_transactions || [],
        stats: (currentProduct as any).stats || { totalSold: 0, revenue: 0, quotedCount: 0, wonCount: 0 },
        createdAt: currentProduct.created_at,
        updatedAt: currentProduct.updated_at,
      } as any);
    }
  }, [currentProduct]);

  const handleAdjustInventory = () => {
    toast({
      title: 'Inventory adjusted',
      description: `${adjustmentQty > 0 ? '+' : ''}${adjustmentQty} ${mockProduct.unitOfMeasure}`,
    });
    setShowAdjustDialog(false);
    setAdjustmentQty(0);
    setAdjustmentNotes('');
  };

  if (isLoading) {
    return <ProductDetailSkeleton />;
  }

  if (!product) {
    return (
      <div className="text-center py-12">
        <h2 className="text-lg font-medium">{t('modules.products.detail.notFound')}</h2>
        <Button className="mt-4" onClick={() => router.push('/products')}>
          {t('modules.products.detail.backToProducts')}
        </Button>
      </div>
    );
  }

  const config = statusConfig[product.status];
  const margin = ((product.listPrice - product.standardCost) / product.listPrice) * 100;
  const isLowStock = product.inventoryQty <= product.reorderPoint;
  const winRate = product.stats.quotedCount > 0 
    ? (product.stats.wonCount / product.stats.quotedCount) * 100 
    : 0;
  const bomCost = (product.bom ?? []).reduce((sum, item) => sum + item.quantity * item.unitCost, 0);

  return (
    <div className="space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.push('/products')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm font-bold text-rams-orange tracking-tight tabular-nums">{product.partNumber}</span>
              <Badge variant={config.variant} size="sm">{t(config.labelKey).toUpperCase()}</Badge>
              {isLowStock && product.status === 'active' && (
                <Badge variant="warning" size="sm" className="gap-1.5 h-4 px-1 rounded-none font-black text-[8px] uppercase tracking-widest">
                  <AlertTriangle className="h-2.5 w-2.5" />
                  STOCK_LOW
                </Badge>
              )}
            </div>
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90 mt-1">{product.name}</h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => setIsEditing(true)}>
            <Edit className="mr-2 h-3.5 w-3.5" />
            {t('modules.products.detail.refineMasterData')}
          </Button>
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => setShowAdjustDialog(true)}>
            <Boxes className="mr-2 h-3.5 w-3.5" />
            {t('modules.products.detail.adjustInventory')}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-10 w-10 border border-rams-line rounded-rams-sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Copy className="mr-2 h-3.5 w-3.5" /> {t('modules.products.detail.cloneNode')}
              </DropdownMenuItem>
              <DropdownMenuItem>
                <BarChart3 className="mr-2 h-3.5 w-3.5" /> {t('modules.products.detail.analyzeIntel')}
              </DropdownMenuItem>
              <DropdownMenuItem>
                <History className="mr-2 h-3.5 w-3.5" /> {t('modules.products.detail.viewLogs')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {product.status === 'active' ? (
                <DropdownMenuItem className="text-rams-red">
                  <Archive className="mr-2 h-3.5 w-3.5" /> {t('modules.products.detail.deauthorize')}
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem className="text-rams-green">
                  <Package className="mr-2 h-3.5 w-3.5" /> {t('modules.products.detail.authorize')}
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid gap-px border border-rams-line bg-rams-line sm:grid-cols-5">
        <div className="bg-rams-module p-6 text-center space-y-2 group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50">{t('modules.products.detail.stats.marketValuation')}</p>
          <p className="text-2xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{formatCurrency(product.listPrice)}</p>
        </div>
        <div className="bg-rams-module p-6 text-center space-y-2 group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50">{t('modules.products.detail.stats.fiscalMargin')}</p>
          <p className={cn(
            'text-2xl font-mono font-bold tracking-tight tabular-nums',
            margin >= 40 ? 'text-rams-green' : margin >= 25 ? 'text-rams-orange' : 'text-rams-red'
          )}>
            {margin.toFixed(1)}%
          </p>
        </div>
        <div className="bg-rams-module p-6 text-center space-y-2 group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50">{t('modules.products.detail.stats.nodeMagnitude')}</p>
          <p className={cn('text-2xl font-mono font-bold tracking-tight tabular-nums', isLowStock && 'text-rams-red')}>
            {formatNumber(product.inventoryQty)}
          </p>
        </div>
        <div className="bg-rams-module p-6 text-center space-y-2 group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50">{t('modules.products.detail.stats.totalCycles')}</p>
          <p className="text-2xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{formatNumber(product.stats.totalSold)}</p>
        </div>
        <div className="bg-rams-module p-6 text-center space-y-2 group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50">{t('modules.products.detail.stats.winProbability')}</p>
          <p className="text-2xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{winRate.toFixed(0)}%</p>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-8">
          {/* Description */}
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('modules.products.detail.contextualIntelligence')}</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <p className="text-xs font-medium text-muted-foreground uppercase leading-relaxed">{product.description}</p>
            </CardContent>
          </Card>

          {/* Specifications */}
          {product.specifications && (
            <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                  <Settings className="h-4 w-4 text-rams-orange" />
                  {t('modules.products.detail.nodeSpecifications')}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="grid gap-px bg-rams-line sm:grid-cols-2 border-t border-rams-line">
                  {Object.entries(product.specifications).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center p-4 bg-rams-module hover:bg-rams-panel transition-none">
                      <dt className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40">{key}</dt>
                      <dd className="text-[11px] font-bold text-foreground/80 uppercase">{value}</dd>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Bill of Materials */}
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b border-rams-line bg-rams-panel/20 p-6">
              <div>
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                  <Layers className="h-4 w-4 text-rams-orange" />
                  {t('modules.products.detail.billOfMaterials')}
                </CardTitle>
                <CardDescription className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('modules.products.detail.bomDescription')}</CardDescription>
              </div>
              <Button variant="outline" size="sm" className="rounded-rams-sm border-rams-line h-8 text-[9px] font-black uppercase tracking-widest">
                <Plus className="mr-2 h-3.5 w-3.5" />
                {t('modules.products.detail.addComponent')}
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>PART_NODE</TableHead>
                      <TableHead>SPECIFICATION</TableHead>
                      <TableHead className="text-right">MAGNITUDE</TableHead>
                      <TableHead>UOM</TableHead>
                      <TableHead className="text-right">UNIT_COST</TableHead>
                      <TableHead className="text-right">EXTENDED</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {product.bom.map((item) => (
                      <TableRow key={item.id} className="transition-none hover:bg-rams-panel">
                        <TableCell className="font-mono font-bold text-rams-orange text-[10px] tabular-nums">{item.partNumber}</TableCell>
                        <TableCell className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{item.name}</TableCell>
                        <TableCell className="text-right font-mono font-bold tabular-nums text-foreground/70">{item.quantity}</TableCell>
                        <TableCell className="text-[10px] font-bold text-muted-foreground/40 uppercase">{item.unitOfMeasure}</TableCell>
                        <TableCell className="text-right font-mono font-bold tabular-nums text-muted-foreground/60">{formatCurrency(item.unitCost)}</TableCell>
                        <TableCell className="text-right font-mono font-bold tabular-nums text-foreground/90">{formatCurrency(item.quantity * item.unitCost)}</TableCell>
                      </TableRow>
                    ))}
                    <TableRow className="bg-rams-panel/30">
                      <TableCell colSpan={5} className="text-right text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">Aggregated BOM Protocol Cost</TableCell>
                      <TableCell className="text-right font-mono font-bold text-sm text-rams-orange tabular-nums">{formatCurrency(bomCost)}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          {/* Inventory Transactions */}
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b border-rams-line bg-rams-panel/20 p-6">
              <div>
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                  <History className="h-4 w-4 text-rams-orange" />
                  {t('modules.products.detail.nodeTelemetry')}
                </CardTitle>
              </div>
              <Button variant="outline" size="sm" className="rounded-rams-sm border-rams-line h-8 text-[9px] font-black uppercase tracking-widest">
                {t('modules.products.detail.viewAllCycles')}
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-rams-line/30">
                {product.recentTransactions.map((tx) => (
                  <div key={tx.id} className="flex items-center justify-between px-6 py-4 hover:bg-rams-panel transition-none group">
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        'w-8 h-8 rounded-none border flex items-center justify-center transition-none',
                        tx.type === 'in' ? 'bg-rams-green/5 border-rams-green/20 text-rams-green' : 
                        tx.type === 'out' ? 'bg-rams-red/5 border-rams-red/20 text-rams-red' : 
                        'bg-rams-panel border-rams-line text-muted-foreground/40'
                      )}>
                        {tx.type === 'in' ? (
                          <Plus className="h-4 w-4" />
                        ) : tx.type === 'out' ? (
                          <Minus className="h-4 w-4" />
                        ) : (
                          <Settings className="h-4 w-4" />
                        )}
                      </div>
                      <div>
                        <p className="font-mono font-bold text-xs tabular-nums text-foreground/80 group-hover:text-rams-orange transition-none">{tx.reference}</p>
                        <p className="text-[10px] text-muted-foreground/40 uppercase font-medium mt-0.5">{tx.notes}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={cn(
                        'font-mono font-bold text-sm tabular-nums',
                        tx.quantity > 0 ? 'text-rams-green' : 'text-rams-red'
                      )}>
                        {tx.quantity > 0 ? '+' : ''}{tx.quantity}
                      </p>
                      <p className="text-[9px] font-mono font-bold uppercase text-muted-foreground/20">{formatDate(new Date(tx.createdAt)).toUpperCase()}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-8">
          {/* Pricing */}
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-rams-orange" />
                {t('modules.products.detail.fiscalParameters')}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <span>{t('modules.products.detail.standardCostProtocol')}</span>
                <span className="font-mono font-bold text-foreground/80">{formatCurrency(product.standardCost)}</span>
              </div>
              <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <span>{t('modules.products.detail.strategicListPrice')}</span>
                <span className="font-mono font-bold text-foreground/80">{formatCurrency(product.listPrice)}</span>
              </div>
              <div className="border-t border-rams-line pt-4">
                <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest">
                  <span className="text-muted-foreground/40">{t('modules.products.detail.fiscalMarginKpi')}</span>
                  <span className={cn(
                    'font-mono font-bold text-lg tabular-nums',
                    margin >= 40 ? 'text-rams-green' : margin >= 25 ? 'text-rams-orange' : 'text-rams-red'
                  )}>
                    {margin.toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">
                <span>{t('modules.products.detail.bomSyncCost')}</span>
                <span className="font-mono font-bold">{formatCurrency(bomCost)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Inventory */}
          <Card className={cn("rounded-rams-sm border bg-rams-module shadow-none", isLowStock && product.status === 'active' ? 'border-rams-red/30 bg-rams-red/5' : 'border-rams-line')}>
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                <Boxes className="h-4 w-4 text-rams-orange" />
                {t('modules.products.detail.magnitudePulse')}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <span>{t('modules.products.detail.authorizedInventory')}</span>
                <span className={cn('font-mono font-bold text-lg tabular-nums', isLowStock && 'text-rams-red')}>
                  {formatNumber(product.inventoryQty)} {product.unitOfMeasure.toUpperCase()}
                </span>
              </div>
              <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">
                <span>{t('modules.products.detail.reorderThreshold')}</span>
                <span className="font-mono font-bold">{formatNumber(product.reorderPoint)} {product.unitOfMeasure.toUpperCase()}</span>
              </div>
              <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">
                <span>{t('modules.products.detail.minimumSyncMagnitude')}</span>
                <span className="font-mono font-bold">{formatNumber(product.minimumOrderQty)} {product.unitOfMeasure.toUpperCase()}</span>
              </div>
              {isLowStock && product.status === 'active' && (
                <div className="flex items-center gap-3 p-3 bg-rams-red/5 border border-rams-red/20 text-rams-red mt-4">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <p className="text-[9px] font-black uppercase tracking-widest">{t('modules.products.detail.thresholdBreach')}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Lead Time */}
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
                <Clock className="h-4 w-4 text-rams-orange" />
                {t('modules.products.detail.temporalVelocity')}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{product.leadTimeDays} {t('common.days')}</p>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('modules.products.detail.standardManufacturingHorizon')}</p>
            </CardContent>
          </Card>

          {/* Meta */}
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardContent className="p-6 space-y-4 text-[10px] font-black uppercase tracking-widest">
              <div className="flex justify-between">
                <span className="text-muted-foreground/40">{t('modules.products.detail.taxonomyNode')}</span>
                <span className="text-foreground/70">{product.category}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground/40">{t('modules.products.detail.unitProtocol')}</span>
                <span className="text-foreground/70">{product.unitOfMeasure}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground/40">{t('modules.products.detail.nodeInitialized')}</span>
                <span className="text-foreground/70 font-mono">{formatDate(new Date(product.createdAt)).toUpperCase()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground/40">{t('modules.products.detail.latestSync')}</span>
                <span className="text-foreground/70 font-mono">{formatDate(new Date(product.updatedAt)).toUpperCase()}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Adjust Inventory Dialog */}
      <Dialog open={showAdjustDialog} onOpenChange={setShowAdjustDialog}>
        <DialogContent className="rounded-rams-sm border-rams-line bg-rams-module">
          <DialogHeader className="border-b border-rams-line pb-4">
            <DialogTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('modules.products.detail.adjustDialog.title')}</DialogTitle>
            <DialogDescription className="text-[10px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
              Current registered stock: {formatNumber(product.inventoryQty)} {product.unitOfMeasure.toUpperCase()}
            </DialogDescription>
          </DialogHeader>
          <div className="py-8 space-y-8">
            <div className="space-y-4">
              <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">Adjustment Magnitude</Label>
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="icon"
                  className="rounded-none border-rams-line h-12 w-12 hover:bg-rams-panel transition-none"
                  onClick={() => setAdjustmentQty((prev) => prev - 1)}
                >
                  <Minus className="h-4 w-4" />
                </Button>
                <Input
                  type="number"
                  value={adjustmentQty}
                  onChange={(e) => setAdjustmentQty(parseInt(e.target.value) || 0)}
                  className="h-12 rounded-none border-rams-line bg-rams-panel text-center text-xl font-mono font-bold tabular-nums"
                />
                <Button
                  variant="outline"
                  size="icon"
                  className="rounded-none border-rams-line h-12 w-12 hover:bg-rams-panel transition-none"
                  onClick={() => setAdjustmentQty((prev) => prev + 1)}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-[9px] font-mono font-black uppercase text-muted-foreground/30 text-center tracking-widest">
                PROJECTED_NEW_MAGNITUDE: {formatNumber(product.inventoryQty + adjustmentQty)} {product.unitOfMeasure.toUpperCase()}
              </p>
            </div>
            <div className="space-y-2">
              <Label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">Protocol Reason / Notes</Label>
              <Input
                value={adjustmentNotes}
                onChange={(e) => setAdjustmentNotes(e.target.value)}
                placeholder="Reason for adjustment protocol..."
                className="h-10 rounded-none border-rams-line bg-rams-panel text-[11px] uppercase font-medium"
              />
            </div>
          </div>
          <DialogFooter className="border-t border-rams-line pt-4">
            <Button variant="ghost" className="rounded-none text-[9px] font-black uppercase tracking-widest h-10 px-6 transition-none" onClick={() => setShowAdjustDialog(false)}>
              {t('common.abortProtocol')}
            </Button>
            <Button onClick={handleAdjustInventory} disabled={adjustmentQty === 0} className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[9px] h-10 px-8 transition-none">
              {t('modules.products.detail.adjustDialog.apply')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
