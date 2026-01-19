'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Plus, Trash2, Search, Save, Send, DollarSign } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
import { apiClient } from '@/api/client';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';
interface RequisitionLine {
  id: string;
  product_id: string;
  product_name: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  estimated_unit_price: number;
  notes: string;
}

interface Product {
  id: string;
  name: string;
  sku: string;
  unit_of_measure: string;
  standard_cost: number;
}

export default function NewPurchaseRequisitionPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = React.useState(false);
  const [products, setProducts] = React.useState<Product[]>([]);
  const [searchQuery, setSearchQuery] = React.useState('');
  
  // Form state
  const [justification, setJustification] = React.useState('');
  const [priority, setPriority] = React.useState<'low' | 'medium' | 'high' | 'urgent'>('medium');
  const [requiredDate, setRequiredDate] = React.useState('');
  const [lines, setLines] = React.useState<RequisitionLine[]>([]);

  // Fetch products for selection
  React.useEffect(() => {
    const fetchProducts = async () => {
      try {
        const res = await apiClient.get('/products');
        const data = (res as { data: Product[] })?.data || (res as Product[]) || [];
        setProducts(data);
      } catch (error) {
        console.error('Failed to fetch products:', error);
      }
    };
    fetchProducts();
  }, []);

  const addLine = () => {
    const newLine: RequisitionLine = {
      id: crypto.randomUUID(),
      product_id: '',
      product_name: '',
      description: '',
      quantity: 1,
      unit_of_measure: 'EA',
      estimated_unit_price: 0,
      notes: '',
    };
    setLines([...lines, newLine]);
  };

  const removeLine = (id: string) => {
    setLines(lines.filter(line => line.id !== id));
  };

  const updateLine = (id: string, updates: Partial<RequisitionLine>) => {
    setLines(lines.map(line => 
      line.id === id ? { ...line, ...updates } : line
    ));
  };

  const handleProductSelect = (lineId: string, productId: string) => {
    const product = products.find(p => p.id === productId);
    if (product) {
      updateLine(lineId, {
        product_id: productId,
        product_name: product.name,
        unit_of_measure: product.unit_of_measure || 'EA',
        estimated_unit_price: product.standard_cost || 0,
      });
    }
  };

  const calculateTotal = () => {
    return lines.reduce((sum, line) => sum + (line.quantity * line.estimated_unit_price), 0);
  };

  const handleSubmit = async (asDraft: boolean = true) => {
    if (lines.length === 0) {
      toast({
        title: t('pages.purchase.requisitionNew.error'),
        description: t('pages.purchase.requisitionNew.addLineItemError'),
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const payload = {
        justification,
        priority,
        required_date: requiredDate || null,
        status: asDraft ? 'draft' : 'submitted',
        lines: lines.map(line => ({
          product_id: line.product_id || null,
          description: line.description || line.product_name,
          quantity: line.quantity,
          unit_of_measure: line.unit_of_measure,
          estimated_unit_price: line.estimated_unit_price,
          notes: line.notes,
        })),
      };

      await apiClient.post('/purchase/requisitions', payload);
      
      toast({
        title: t('pages.purchase.requisitionNew.success'),
        description: asDraft ? t('pages.purchase.requisitionNew.savedAsDraft') : t('pages.purchase.requisitionNew.submittedForApproval'),
      });
      
      router.push('/purchase');
    } catch (error) {
      console.error('Failed to create requisition:', error);
      toast({
        title: t('pages.purchase.requisitionNew.error'),
        description: t('pages.purchase.requisitionNew.createFailed'),
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const filteredProducts = products.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.sku?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" asChild>
            <Link href="/purchase">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              {t('pages.purchase.requisitionNew.title')}
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('pages.purchase.requisitionNew.subtitle')}</span>
              <span className="opacity-30">|</span>
              <span>{t('pages.purchase.requisitionNew.station')}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            variant="outline" 
            size="default"
            className="rounded-rams-sm border-rams-line h-10 px-6 transition-none"
            onClick={() => handleSubmit(true)}
            disabled={loading}
          >
            <Save className="mr-2 h-3.5 w-3.5" />
            {t('pages.purchase.requisitionNew.saveDraft')}
          </Button>
          <Button 
            size="default"
            className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none"
            onClick={() => handleSubmit(false)}
            disabled={loading}
          >
            <Send className="mr-2 h-3.5 w-3.5" />
            {t('pages.purchase.requisitionNew.submitForApproval')}
          </Button>
        </div>
      </div>

      {/* Form */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Form */}
        <div className="lg:col-span-2 space-y-8">
          {/* Requisition Details */}
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.purchase.requisitionNew.requisitionParameters')}</CardTitle>
            </CardHeader>
            <CardContent className="p-8 space-y-8">
              <div className="space-y-2">
                <Label htmlFor="justification" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.purchase.requisitionNew.businessJustification')}</Label>
                <Textarea
                  id="justification"
                  placeholder={t('pages.purchase.requisitionNew.justificationPlaceholder')}
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  className="min-h-[120px] rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed"
                />
              </div>
              <div className="grid gap-8 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="priority" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.purchase.requisitionNew.priorityLayer')}</Label>
                  <Select value={priority} onValueChange={(v: any) => setPriority(v)}>
                    <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">{t('pages.purchase.requisitionNew.priorities.low')}</SelectItem>
                      <SelectItem value="medium">{t('pages.purchase.requisitionNew.priorities.medium')}</SelectItem>
                      <SelectItem value="high">{t('pages.purchase.requisitionNew.priorities.high')}</SelectItem>
                      <SelectItem value="urgent">{t('pages.purchase.requisitionNew.priorities.urgent')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="required_date" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.purchase.requisitionNew.thresholdDate')}</Label>
                  <Input
                    id="required_date"
                    type="date"
                    value={requiredDate}
                    onChange={(e) => setRequiredDate(e.target.value)}
                    className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Line Items */}
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b border-rams-line bg-rams-panel/20 p-6">
              <div>
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.purchase.requisitionNew.resourceLineIntel')}</CardTitle>
              </div>
              <Button variant="outline" size="sm" onClick={addLine} className="rounded-rams-sm border-rams-line h-8 text-[9px] font-black uppercase tracking-widest">
                <Plus className="mr-2 h-3.5 w-3.5" />
                {t('pages.purchase.requisitionNew.addNode')}
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {lines.length === 0 ? (
                <div className="text-center py-24 bg-rams-module relative overflow-hidden">
                  <Plus className="h-12 w-12 text-muted-foreground/20 mx-auto mb-4 relative z-10" />
                  <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60 relative z-10">{t('pages.purchase.requisitionNew.zeroResourceNodes')}</p>
                  <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1 relative z-10">{t('pages.purchase.requisitionNew.initializeItemsUsing')}</p>
                  <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('pages.purchase.requisitionNew.tableHeaders.productNodeDesc')}</TableHead>
                        <TableHead className="w-24">{t('pages.purchase.requisitionNew.tableHeaders.magnitude')}</TableHead>
                        <TableHead className="w-20">{t('pages.purchase.requisitionNew.tableHeaders.uom')}</TableHead>
                        <TableHead className="w-32">{t('pages.purchase.requisitionNew.tableHeaders.estPrice')}</TableHead>
                        <TableHead className="w-32">{t('pages.purchase.requisitionNew.tableHeaders.subtotal')}</TableHead>
                        <TableHead className="w-10"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {lines.map((line) => (
                        <TableRow key={line.id} className="transition-none hover:bg-rams-panel">
                          <TableCell>
                            <div className="space-y-2">
                              <Select
                                value={line.product_id}
                                onValueChange={(v) => handleProductSelect(line.id, v)}
                              >
                                <SelectTrigger className="h-9 rounded-none bg-rams-panel border-rams-line text-[10px] font-bold uppercase">
                                  <SelectValue placeholder={t('pages.purchase.requisitionNew.selectProductNode')} />
                                </SelectTrigger>
                                <SelectContent>
                                  {filteredProducts.slice(0, 50).map((product) => (
                                    <SelectItem key={product.id} value={product.id}>
                                      {product.name.toUpperCase()} ({product.sku})
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              <Input
                                placeholder={t('pages.purchase.requisitionNew.orDefineManualSpec')}
                                value={line.description}
                                onChange={(e) => updateLine(line.id, { description: e.target.value })}
                                className="h-8 rounded-none bg-rams-panel border-rams-line text-[9px] font-medium uppercase"
                              />
                            </div>
                          </TableCell>
                          <TableCell>
                            <Input
                              type="number"
                              min={1}
                              value={line.quantity}
                              onChange={(e) => updateLine(line.id, { quantity: parseInt(e.target.value) || 1 })}
                              className="h-9 rounded-none bg-rams-panel border-rams-line text-[10px] font-mono font-bold"
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              value={line.unit_of_measure}
                              onChange={(e) => updateLine(line.id, { unit_of_measure: e.target.value.toUpperCase() })}
                              className="h-9 rounded-none bg-rams-panel border-rams-line text-[10px] font-bold"
                            />
                          </TableCell>
                          <TableCell>
                            <div className="relative">
                              <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground/30" />
                              <Input
                                type="number"
                                step="0.01"
                                min={0}
                                value={line.estimated_unit_price}
                                onChange={(e) => updateLine(line.id, { estimated_unit_price: parseFloat(e.target.value) || 0 })}
                                className="pl-7 h-9 rounded-none bg-rams-panel border-rams-line text-[10px] font-mono font-bold"
                              />
                            </div>
                          </TableCell>
                          <TableCell className="font-mono font-bold text-xs tabular-nums text-foreground/80">
                            ${(line.quantity * line.estimated_unit_price).toFixed(2)}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground/20 hover:text-rams-red hover:bg-rams-red/5 rounded-none transition-none"
                              onClick={() => removeLine(line.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-8">
          {/* Summary */}
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.purchase.requisitionNew.fiscalSummary')}</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <span>{t('pages.purchase.requisitionNew.resourceNodes')}</span>
                <span className="font-mono font-bold text-foreground/80">{lines.length}</span>
              </div>
              <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                <span>{t('pages.purchase.requisitionNew.totalMagnitude')}</span>
                <span className="font-mono font-bold text-foreground/80 tabular-nums">{lines.reduce((sum, l) => sum + l.quantity, 0)}</span>
              </div>
              <div className="border-t border-rams-line pt-6">
                <div className="flex justify-between items-end">
                  <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">{t('pages.purchase.requisitionNew.estimatedProtocolTotal')}</span>
                  <span className="text-3xl font-mono font-bold text-rams-orange tabular-nums">
                    ${calculateTotal().toFixed(2)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Add Products */}
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.purchase.requisitionNew.nodeInjection')}</CardTitle>
              <CardDescription className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('pages.purchase.requisitionNew.nodeInjectionDesc')}</CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="relative group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 transition-colors group-focus-within:text-rams-orange" />
                <Input
                  placeholder={t('pages.purchase.requisitionNew.searchProductNodes')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[10px]"
                />
              </div>
              <div className="max-h-[400px] overflow-y-auto space-y-1 pr-2 scrollbar-hide">
                {filteredProducts.slice(0, 10).map((product) => (
                  <div
                    key={product.id}
                    className="flex items-center justify-between p-4 bg-rams-panel/20 border border-rams-line hover:bg-rams-panel hover:border-rams-orange/40 transition-none cursor-pointer group"
                    onClick={() => {
                      const newLine: RequisitionLine = {
                        id: crypto.randomUUID(),
                        product_id: product.id,
                        product_name: product.name,
                        description: '',
                        quantity: 1,
                        unit_of_measure: product.unit_of_measure || 'EA',
                        estimated_unit_price: product.standard_cost || 0,
                        notes: '',
                      };
                      setLines([...lines, newLine]);
                    }}
                  >
                    <div>
                      <p className="text-[11px] font-black uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{product.name}</p>
                      <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">{product.sku}</p>
                    </div>
                    <Plus className="h-3.5 w-3.5 text-muted-foreground/20 group-hover:text-rams-orange transition-none" />
                  </div>
                ))}
                {filteredProducts.length === 0 && (
                  <div className="text-center py-12 text-muted-foreground/20 border border-dashed border-rams-line">
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest">{t('pages.purchase.requisitionNew.zeroNodesFound')}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
