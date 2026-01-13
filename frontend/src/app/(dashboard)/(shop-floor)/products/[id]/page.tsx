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
import { cn, formatCurrency, formatNumber, formatDate } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

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
  active: { label: 'Active', variant: 'success' as const },
  inactive: { label: 'Inactive', variant: 'secondary' as const },
  discontinued: { label: 'Discontinued', variant: 'danger' as const },
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

export default function ProductDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = React.useState(true);
  const [product, setProduct] = React.useState<Product | null>(null);
  const [showAdjustDialog, setShowAdjustDialog] = React.useState(false);
  const [adjustmentQty, setAdjustmentQty] = React.useState(0);
  const [adjustmentNotes, setAdjustmentNotes] = React.useState('');
  const [isEditing, setIsEditing] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setProduct(mockProduct);
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, [params.id]);

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
        <h2 className="text-lg font-medium">Product not found</h2>
        <Button className="mt-4" onClick={() => router.push('/products')}>
          Back to Products
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
  const bomCost = product.bom.reduce((sum, item) => sum + item.quantity * item.unitCost, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-lg text-muted-foreground">{product.partNumber}</span>
              <Badge variant={config.variant}>{config.label}</Badge>
              {isLowStock && product.status === 'active' && (
                <Badge variant="warning" className="gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Low Stock
                </Badge>
              )}
            </div>
            <h1 className="text-2xl font-bold">{product.name}</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setIsEditing(true)}>
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button variant="outline" onClick={() => setShowAdjustDialog(true)}>
            <Boxes className="mr-2 h-4 w-4" />
            Adjust Inventory
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Copy className="mr-2 h-4 w-4" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem>
                <BarChart3 className="mr-2 h-4 w-4" />
                View Analytics
              </DropdownMenuItem>
              <DropdownMenuItem>
                <History className="mr-2 h-4 w-4" />
                View History
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {product.status === 'active' ? (
                <DropdownMenuItem className="text-warning">
                  <Archive className="mr-2 h-4 w-4" />
                  Deactivate
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem className="text-success">
                  <Package className="mr-2 h-4 w-4" />
                  Activate
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-5">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{formatCurrency(product.listPrice)}</p>
            <p className="text-sm text-muted-foreground">List Price</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className={cn(
              'text-2xl font-bold',
              margin >= 40 ? 'text-success' : margin >= 25 ? 'text-warning' : 'text-danger'
            )}>
              {margin.toFixed(1)}%
            </p>
            <p className="text-sm text-muted-foreground">Margin</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className={cn('text-2xl font-bold', isLowStock && 'text-warning')}>
              {formatNumber(product.inventoryQty)}
            </p>
            <p className="text-sm text-muted-foreground">In Stock</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{formatNumber(product.stats.totalSold)}</p>
            <p className="text-sm text-muted-foreground">Total Sold</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{winRate.toFixed(0)}%</p>
            <p className="text-sm text-muted-foreground">Win Rate</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <Card>
            <CardHeader>
              <CardTitle>Description</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">{product.description}</p>
            </CardContent>
          </Card>

          {/* Specifications */}
          {product.specifications && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Specifications
                </CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid gap-2 sm:grid-cols-2">
                  {Object.entries(product.specifications).map(([key, value]) => (
                    <div key={key} className="flex justify-between border-b py-2">
                      <dt className="text-muted-foreground">{key}</dt>
                      <dd className="font-medium">{value}</dd>
                    </div>
                  ))}
                </dl>
              </CardContent>
            </Card>
          )}

          {/* Bill of Materials */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  Bill of Materials
                </CardTitle>
                <CardDescription>Components required to manufacture this product</CardDescription>
              </div>
              <Button variant="outline" size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add Component
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="py-3 px-4 text-left font-medium">Part #</th>
                      <th className="py-3 px-4 text-left font-medium">Name</th>
                      <th className="py-3 px-4 text-right font-medium">Qty</th>
                      <th className="py-3 px-4 text-left font-medium">UoM</th>
                      <th className="py-3 px-4 text-right font-medium">Unit Cost</th>
                      <th className="py-3 px-4 text-right font-medium">Extended</th>
                    </tr>
                  </thead>
                  <tbody>
                    {product.bom.map((item) => (
                      <tr key={item.id} className="border-b">
                        <td className="py-3 px-4 font-mono text-sm">{item.partNumber}</td>
                        <td className="py-3 px-4">{item.name}</td>
                        <td className="py-3 px-4 text-right">{item.quantity}</td>
                        <td className="py-3 px-4">{item.unitOfMeasure}</td>
                        <td className="py-3 px-4 text-right">{formatCurrency(item.unitCost)}</td>
                        <td className="py-3 px-4 text-right font-medium">{formatCurrency(item.quantity * item.unitCost)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-muted/30 font-bold">
                      <td colSpan={5} className="py-3 px-4 text-right">Total BOM Cost</td>
                      <td className="py-3 px-4 text-right">{formatCurrency(bomCost)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Inventory Transactions */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Recent Inventory Activity
                </CardTitle>
              </div>
              <Button variant="outline" size="sm">
                View All
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y">
                {product.recentTransactions.map((tx) => (
                  <div key={tx.id} className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        'w-8 h-8 rounded-full flex items-center justify-center',
                        tx.type === 'in' ? 'bg-success/10' : 
                        tx.type === 'out' ? 'bg-danger/10' : 'bg-warning/10'
                      )}>
                        {tx.type === 'in' ? (
                          <Plus className={cn('h-4 w-4 text-success')} />
                        ) : tx.type === 'out' ? (
                          <Minus className={cn('h-4 w-4 text-danger')} />
                        ) : (
                          <Settings className={cn('h-4 w-4 text-warning')} />
                        )}
                      </div>
                      <div>
                        <p className="font-medium">{tx.reference}</p>
                        <p className="text-sm text-muted-foreground">{tx.notes}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={cn(
                        'font-mono font-medium',
                        tx.quantity > 0 ? 'text-success' : 'text-danger'
                      )}>
                        {tx.quantity > 0 ? '+' : ''}{tx.quantity}
                      </p>
                      <p className="text-sm text-muted-foreground">{formatDate(new Date(tx.createdAt))}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Pricing */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                Pricing
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Standard Cost</span>
                <span className="font-medium">{formatCurrency(product.standardCost)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">List Price</span>
                <span className="font-medium">{formatCurrency(product.listPrice)}</span>
              </div>
              <div className="flex justify-between border-t pt-3">
                <span className="text-muted-foreground">Margin</span>
                <span className={cn(
                  'font-medium',
                  margin >= 40 ? 'text-success' : margin >= 25 ? 'text-warning' : 'text-danger'
                )}>
                  {margin.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">BOM Cost</span>
                <span>{formatCurrency(bomCost)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Inventory */}
          <Card className={cn(isLowStock && product.status === 'active' && 'border-warning')}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Boxes className="h-4 w-4" />
                Inventory
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">On Hand</span>
                <span className={cn('font-medium', isLowStock && 'text-warning')}>
                  {formatNumber(product.inventoryQty)} {product.unitOfMeasure}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Reorder Point</span>
                <span>{formatNumber(product.reorderPoint)} {product.unitOfMeasure}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Min. Order Qty</span>
                <span>{formatNumber(product.minimumOrderQty)} {product.unitOfMeasure}</span>
              </div>
              {isLowStock && product.status === 'active' && (
                <div className="flex items-center gap-2 text-warning bg-warning/10 p-2 rounded text-sm">
                  <AlertTriangle className="h-4 w-4" />
                  Below reorder point
                </div>
              )}
            </CardContent>
          </Card>

          {/* Lead Time */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Lead Time
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{product.leadTimeDays} days</p>
              <p className="text-sm text-muted-foreground">Standard manufacturing time</p>
            </CardContent>
          </Card>

          {/* Meta */}
          <Card>
            <CardContent className="pt-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Category</span>
                <span>{product.category}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Unit of Measure</span>
                <span>{product.unitOfMeasure}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span>{formatDate(new Date(product.createdAt))}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Last Updated</span>
                <span>{formatDate(new Date(product.updatedAt))}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Adjust Inventory Dialog */}
      <Dialog open={showAdjustDialog} onOpenChange={setShowAdjustDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Adjust Inventory</DialogTitle>
            <DialogDescription>
              Current stock: {formatNumber(product.inventoryQty)} {product.unitOfMeasure}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <Label>Adjustment Quantity</Label>
              <div className="flex items-center gap-2 mt-1.5">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setAdjustmentQty((prev) => prev - 1)}
                >
                  <Minus className="h-4 w-4" />
                </Button>
                <Input
                  type="number"
                  value={adjustmentQty}
                  onChange={(e) => setAdjustmentQty(parseInt(e.target.value) || 0)}
                  className="text-center"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setAdjustmentQty((prev) => prev + 1)}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                New stock: {formatNumber(product.inventoryQty + adjustmentQty)} {product.unitOfMeasure}
              </p>
            </div>
            <div>
              <Label>Notes</Label>
              <Input
                value={adjustmentNotes}
                onChange={(e) => setAdjustmentNotes(e.target.value)}
                placeholder="Reason for adjustment"
                className="mt-1.5"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAdjustDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAdjustInventory} disabled={adjustmentQty === 0}>
              Apply Adjustment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
