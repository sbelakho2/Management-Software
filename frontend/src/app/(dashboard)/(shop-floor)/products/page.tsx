'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  Edit,
  Copy,
  Package,
  Boxes,
  DollarSign,
  TrendingUp,
  Archive,
  Download,
  Upload,
  BarChart3,
  Layers,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn, formatCurrency, formatNumber } from '@/lib/utils';
import { useProductStore } from '@/stores/products';
import type { Product as APIProduct } from '@/api/products';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

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
  totalSold: number;
  revenue: number;
}


const statusConfig = {
  active: { labelKey: 'common.active', variant: 'success' as const },
  inactive: { labelKey: 'common.inactive', variant: 'secondary' as const },
  discontinued: { labelKey: 'pages.products.status.discontinued', variant: 'danger' as const },
};

function ProductStats({ products }: { products: Product[] }) {
  const { t } = useI18n();
  const stats = React.useMemo(() => {
    const active = products.filter((p) => p.status === 'active').length;
    const lowStock = products.filter((p) => p.inventoryQty <= p.reorderPoint && p.status === 'active').length;
    const totalRevenue = products.reduce((sum, p) => sum + p.revenue, 0);
    const avgMargin = products.length > 0
      ? products.reduce((sum, p) => sum + ((p.listPrice - p.standardCost) / p.listPrice) * 100, 0) / products.length
      : 0;
    return { active, lowStock, totalRevenue, avgMargin };
  }, [products]);

  return (
    <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.products.stats.activeInventoryNodes')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.active}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.products.stats.stockAbnormalities')}</p>
        <p className={cn('text-3xl font-mono font-bold tracking-tight tabular-nums', stats.lowStock > 0 ? 'text-rams-red' : 'text-foreground/90')}>
          {stats.lowStock}
        </p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.products.stats.aggregatedRevenue')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{formatCurrency(stats.totalRevenue)}</p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-line">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.products.stats.meanMarginKPI')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{stats.avgMargin.toFixed(1)}%</p>
      </div>
    </div>
  );
}

function ProductRow({ product }: { product: Product }) {
  const router = useRouter();
  const { t } = useI18n();
  const config = statusConfig[product.status];
  const margin = ((product.listPrice - product.standardCost) / product.listPrice) * 100;
  const isLowStock = product.inventoryQty <= product.reorderPoint && product.status === 'active';

  return (
    <TableRow 
      className="transition-none cursor-pointer group"
      onClick={() => router.push(`/products/${product.id}`)}
    >
      <TableCell>
        <div>
          <p className="font-mono font-bold text-rams-orange tabular-nums">{product.partNumber}</p>
          <p className="text-[11px] font-sans font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{product.name}</p>
        </div>
      </TableCell>
      <TableCell className="font-sans font-bold text-[11px] uppercase tracking-tight text-muted-foreground/60">{product.category}</TableCell>
      <TableCell>
        <Badge variant={config.variant} size="sm">{t(config.labelKey).toUpperCase()}</Badge>
      </TableCell>
      <TableCell className="text-right font-mono font-bold tabular-nums">{formatCurrency(product.standardCost)}</TableCell>
      <TableCell className="text-right font-mono font-bold tabular-nums">{formatCurrency(product.listPrice)}</TableCell>
      <TableCell className="text-right">
        <span className={cn(
          'font-mono font-bold tabular-nums',
          margin >= 40 ? 'text-rams-green' : margin >= 25 ? 'text-rams-orange' : 'text-rams-red'
        )}>
          {margin.toFixed(1)}%
        </span>
      </TableCell>
      <TableCell className="text-center">
        <span className={cn('font-mono font-bold tabular-nums', isLowStock ? 'text-rams-red' : 'text-foreground/80')}>
          {formatNumber(product.inventoryQty)}
          {isLowStock && ' ⚠'}
        </span>
      </TableCell>
      <TableCell className="text-center font-mono text-[10px] text-muted-foreground/40">{product.leadTimeDays}D</TableCell>
      <TableCell className="text-right font-mono font-bold tabular-nums text-muted-foreground/60">{formatNumber(product.totalSold)}</TableCell>
      <TableCell onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push(`/products/${product.id}`)}>
              <Eye className="mr-2 h-3.5 w-3.5" /> {t('common.viewDetails')}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/products/${product.id}?mode=edit`)}>
              <Edit className="mr-2 h-3.5 w-3.5" /> {t('common.edit')}
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Copy className="mr-2 h-3.5 w-3.5" /> {t('common.duplicate')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Layers className="mr-2 h-3.5 w-3.5" /> {t('pages.products.viewBom')}
            </DropdownMenuItem>
            <DropdownMenuItem>
              <BarChart3 className="mr-2 h-3.5 w-3.5" /> {t('pages.products.viewAnalytics')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {product.status === 'active' ? (
              <DropdownMenuItem className="text-rams-red">
                <Archive className="mr-2 h-3.5 w-3.5" /> {t('common.deactivate')}
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem className="text-rams-green">
                <Package className="mr-2 h-3.5 w-3.5" /> {t('common.activate')}
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

export default function ProductsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { products, loading, fetchProducts } = useProductStore();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [categoryFilter, setCategoryFilter] = React.useState<string>('all');
  const [stockFilter, setStockFilter] = React.useState<string>('all');

  React.useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const mappedProducts = React.useMemo(() => {
    return products.map(p => ({
      ...p,
      id: p.id.toString(),
      partNumber: p.part_number,
      description: (p as any).full_part_number || (p as any).description,
      category: (p as any).product_family || (p as any).category?.name || 'Uncategorized',
      status: p.status as 'active' | 'inactive' | 'discontinued',
      unitOfMeasure: (p as any).unit_of_measure || 'ea',
      standardCost: (p as any).standard_cost || (p as any).cost || 0,
      listPrice: (p as any).list_price || ((p as any).cost || 0) * 1.5,
      inventoryQty: (p as any).inventoryQty || 100,
      reorderPoint: (p as any).reorder_point || 20,
      leadTimeDays: p.lead_time_days,
      totalSold: (p as any).totalSold || 0,
      revenue: (p as any).revenue || 0,
    }));
  }, [products]);

  const categories = React.useMemo(() => {
    return [...new Set(mappedProducts.map((p) => p.category))];
  }, [mappedProducts]);

  const filteredProducts = React.useMemo(() => {
    return mappedProducts.filter((product) => {
      const matchesSearch = searchQuery === '' ||
        product.partNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        product.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        product.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'all' || product.status === statusFilter;
      const matchesCategory = categoryFilter === 'all' || product.category === categoryFilter;
      const matchesStock = stockFilter === 'all' || 
        (stockFilter === 'low' && product.inventoryQty <= product.reorderPoint && product.status === 'active') ||
        (stockFilter === 'out' && product.inventoryQty === 0);
      return matchesSearch && matchesStatus && matchesCategory && matchesStock;
    });
  }, [mappedProducts, searchQuery, statusFilter, categoryFilter, stockFilter]);

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="products-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.products.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.products.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.products.station')}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm" onClick={() => {}}>
            <Download className="mr-2 h-3.5 w-3.5" />
            {t('pages.products.exportIntel')}
          </Button>
          <Button variant="outline" size="default" className="rounded-rams-sm" onClick={() => {}}>
            <Upload className="mr-2 h-3.5 w-3.5" />
            {t('pages.products.import')}
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase" onClick={() => router.push('/products/new')}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            {t('pages.products.initializeNode')}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <ProductStats products={mappedProducts} />

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-4 flex-wrap max-w-4xl">
          <div className="relative flex-1 min-w-[240px] group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 transition-colors group-focus-within:text-rams-orange" />
            <Input
              placeholder={t('common.search')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-10 text-[10px]"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px] h-10 text-[10px]">
              <Filter className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder={t('common.status')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.allStatus')}</SelectItem>
              <SelectItem value="active">{t('common.active')}</SelectItem>
              <SelectItem value="inactive">{t('common.inactive')}</SelectItem>
              <SelectItem value="discontinued">{t('pages.products.status.discontinued')}</SelectItem>
            </SelectContent>
          </Select>
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-[160px] h-10 text-[10px]">
              <Layers className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder={t('common.category')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.allCategories')}</SelectItem>
              {categories.map((category) => (
                <SelectItem key={category} value={category}>{category.toUpperCase()}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={stockFilter} onValueChange={setStockFilter}>
            <SelectTrigger className="w-[140px] h-10 text-[10px]">
              <Package className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder={t('pages.products.stockLevel')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('pages.products.allStock')}</SelectItem>
              <SelectItem value="low">{t('pages.products.lowStock')}</SelectItem>
              <SelectItem value="out">{t('pages.products.outOfStock')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Table */}
      <Card className="rounded-rams-sm overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('pages.products.table.product')}</TableHead>
                <TableHead>{t('common.category')}</TableHead>
                <TableHead>{t('common.status')}</TableHead>
                <TableHead className="text-right">{t('pages.products.table.standardCost')}</TableHead>
                <TableHead className="text-right">{t('pages.products.table.listPrice')}</TableHead>
                <TableHead className="text-right">{t('pages.products.table.margin')}</TableHead>
                <TableHead className="text-center">{t('pages.products.table.inventory')}</TableHead>
                <TableHead className="text-center">{t('pages.products.table.leadTime')}</TableHead>
                <TableHead className="text-right">{t('pages.products.table.totalSold')}</TableHead>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredProducts.map((product) => (
                <ProductRow key={product.id} product={product} />
              ))}
            </TableBody>
          </Table>
        </div>
        {filteredProducts.length === 0 && (
          <div className="text-center py-24">
            <Package className="mx-auto h-12 w-12 text-muted-foreground/20" />
            <div className="mt-4">
              <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">{t('pages.products.emptyState.title')}</p>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">{t('pages.products.emptyState.description')}</p>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
