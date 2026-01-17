'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
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
  active: { label: 'Active', variant: 'success' as const },
  inactive: { label: 'Inactive', variant: 'secondary' as const },
  discontinued: { label: 'Discontinued', variant: 'danger' as const },
};

function ProductStats({ products }: { products: Product[] }) {
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
    <div className="grid gap-4 md:grid-cols-4">
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-success/60">Active Products</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{stats.active}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-success/10 text-success">
              <Package className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className={cn("text-[10px] font-bold uppercase tracking-widest", stats.lowStock > 0 ? "text-warning/60" : "text-muted-foreground/60")}>Low Stock</p>
              <p className={cn("text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br mt-1", stats.lowStock > 0 ? "from-warning to-warning/70" : "from-foreground to-foreground/70")}>
                {stats.lowStock}
              </p>
            </div>
            <div className={cn("p-3 rounded-2xl shadow-sm", stats.lowStock > 0 ? "bg-warning/10 text-warning" : "bg-muted text-muted-foreground")}>
              <Boxes className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-primary/60">Total Revenue</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{formatCurrency(stats.totalRevenue)}</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-primary/10 text-primary">
              <DollarSign className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Avg. Margin</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{stats.avgMargin.toFixed(1)}%</p>
            </div>
            <div className="p-3 rounded-2xl shadow-sm bg-muted/30 text-foreground">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ProductRow({ product }: { product: Product }) {
  const router = useRouter();
  const config = statusConfig[product.status];
  const margin = ((product.listPrice - product.standardCost) / product.listPrice) * 100;
  const isLowStock = product.inventoryQty <= product.reorderPoint && product.status === 'active';

  return (
    <tr 
      className="border-b hover:bg-muted/50 cursor-pointer transition-colors"
      onClick={() => router.push(`/products/${product.id}`)}
    >
      <td className="py-3 px-4">
        <div>
          <p className="font-mono font-medium">{product.partNumber}</p>
          <p className="text-sm text-muted-foreground">{product.name}</p>
        </div>
      </td>
      <td className="py-3 px-4 text-muted-foreground">{product.category}</td>
      <td className="py-3 px-4">
        <Badge variant={config.variant}>{config.label}</Badge>
      </td>
      <td className="py-3 px-4 text-right">{formatCurrency(product.standardCost)}</td>
      <td className="py-3 px-4 text-right font-medium">{formatCurrency(product.listPrice)}</td>
      <td className="py-3 px-4 text-right">
        <span className={cn(
          'font-medium',
          margin >= 40 ? 'text-success' : margin >= 25 ? 'text-warning' : 'text-danger'
        )}>
          {margin.toFixed(1)}%
        </span>
      </td>
      <td className="py-3 px-4 text-right">
        <span className={cn(isLowStock && 'text-warning font-medium')}>
          {formatNumber(product.inventoryQty)}
          {isLowStock && ' ⚠'}
        </span>
      </td>
      <td className="py-3 px-4 text-center">{product.leadTimeDays}d</td>
      <td className="py-3 px-4 text-right">{formatNumber(product.totalSold)}</td>
      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push(`/products/${product.id}`)}>
              <Eye className="mr-2 h-4 w-4" />
              View
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/products/${product.id}?mode=edit`)}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Copy className="mr-2 h-4 w-4" />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Layers className="mr-2 h-4 w-4" />
              View BOM
            </DropdownMenuItem>
            <DropdownMenuItem>
              <BarChart3 className="mr-2 h-4 w-4" />
              View Analytics
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
      </td>
    </tr>
  );
}

export default function ProductsPage() {
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
    <div className="space-y-8 page-fade-in" data-testid="products-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Product Portfolio
          </h1>
          <p className="text-muted-foreground font-medium">Manage manufacturing specifications and master data intelligence</p>
        </div>
        <div className="flex items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
                <Download className="mr-2 h-4 w-4" />
                Export Intel
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="rounded-2xl shadow-premium">
              <DropdownMenuItem className="rounded-xl m-1">Export as CSV</DropdownMenuItem>
              <DropdownMenuItem className="rounded-xl m-1">Export as Excel</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            <Upload className="mr-2 h-4 w-4" />
            Import
          </Button>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine" onClick={() => router.push('/products/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Add Product
          </Button>
        </div>
      </div>

      {/* Stats */}
      <ProductStats products={mappedProducts} />

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search products..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="discontinued">Discontinued</SelectItem>
                </SelectContent>
              </Select>
              <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All categories</SelectItem>
                  {categories.map((category) => (
                    <SelectItem key={category} value={category}>{category}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={stockFilter} onValueChange={setStockFilter}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Stock" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All stock</SelectItem>
                  <SelectItem value="low">Low stock</SelectItem>
                  <SelectItem value="out">Out of stock</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-3 px-4 text-left font-medium">Product</th>
                  <th className="py-3 px-4 text-left font-medium">Category</th>
                  <th className="py-3 px-4 text-left font-medium">Status</th>
                  <th className="py-3 px-4 text-right font-medium">Cost</th>
                  <th className="py-3 px-4 text-right font-medium">Price</th>
                  <th className="py-3 px-4 text-right font-medium">Margin</th>
                  <th className="py-3 px-4 text-right font-medium">Inventory</th>
                  <th className="py-3 px-4 text-center font-medium">Lead Time</th>
                  <th className="py-3 px-4 text-right font-medium">Total Sold</th>
                  <th className="py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((product) => (
                  <ProductRow key={product.id} product={product} />
                ))}
              </tbody>
            </table>
          </div>
          {filteredProducts.length === 0 && (
            <div className="text-center py-12">
              <Package className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-medium">No products found</h3>
              <p className="text-muted-foreground">
                {searchQuery || statusFilter !== 'all' || categoryFilter !== 'all' || stockFilter !== 'all'
                  ? 'Try adjusting your filters'
                  : 'Add your first product to get started'}
              </p>
              {!searchQuery && statusFilter === 'all' && categoryFilter === 'all' && stockFilter === 'all' && (
                <Button className="mt-4" onClick={() => router.push('/products/new')}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Product
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
