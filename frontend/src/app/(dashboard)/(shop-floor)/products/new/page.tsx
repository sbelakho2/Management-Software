'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X, Package, Loader2, DollarSign } from 'lucide-react';
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
import { useToast } from '@/hooks/use-toast';
import { useProductStore } from '@/stores/products';
import { useI18n } from '@/contexts/i18n-context';

export default function NewProductPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const { createProduct } = useProductStore();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const [form, setForm] = React.useState({
    partNumber: '',
    name: '',
    description: '',
    category: '',
    status: 'active',
    unitOfMeasure: 'ea',
    standardCost: 0,
    listPrice: 0,
    reorderPoint: 0,
    leadTimeDays: 7,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.partNumber || !form.name) {
      toast({
        title: t('products.new.requiredParams') || 'Required Parameters missing',
        description: t('products.new.providePartAndName') || 'Please provide at least a Part Node Identity and Product Name.',
        variant: 'destructive',
      });
      return;
    }

    setIsSubmitting(true);
    try {
      await createProduct({
        part_number: form.partNumber,
        name: form.name,
        description: form.description,
        category: form.category,
        status: form.status,
        unit_of_measure: form.unitOfMeasure,
        standard_cost: form.standardCost,
        list_price: form.listPrice,
        reorder_point: form.reorderPoint,
        lead_time_days: form.leadTimeDays,
      } as any);
      
      toast({
        title: t('products.new.nodeSynchronized') || 'Node Synchronized',
        description: t('products.new.establishedSuccess', { name: form.name }) || `${form.name} has been successfully established in the catalog.`,
      });
      router.push('/products');
    } catch (error) {
      toast({
        title: t('products.new.syncFailed') || 'Synchronization Failed',
        description: t('products.new.failedToEstablish') || 'Failed to establish product node. Please re-authenticate.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('products.new.title') || 'Initialize Catalog Node'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('products.new.subtitle') || 'Global Product Intelligence Mesh'}</span>
              <span className="opacity-30">|</span>
              <span>STATION: CATALOG-ENTRY-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.back()} disabled={isSubmitting}>
            {t('common.abort') || 'ABORT'}
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting} size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                {t('common.synchronizing') || 'SYNCHRONIZING...'}
              </>
            ) : (
              <>
                <Save className="mr-2 h-3.5 w-3.5" />
                {t('products.new.establishNode') || 'ESTABLISH_NODE'}
              </>
            )}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-8">
        <div className="grid gap-8 md:grid-cols-2">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-3">
                <Package className="h-4 w-4 text-rams-orange" />
                {t('products.new.basicIdentification') || 'Basic Identification'}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-8 p-8">
              <div className="grid gap-8 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="partNumber" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.new.partNodeIdentity') || 'Part Node Identity'} *</Label>
                  <Input
                    id="partNumber"
                    value={form.partNumber}
                    onChange={(e) => setForm({ ...form, partNumber: e.target.value.toUpperCase() })}
                    placeholder="e.g. PN-2024-001"
                    className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="category" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.new.taxonomyCategory') || 'Taxonomy Category'}</Label>
                  <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                    <SelectTrigger id="category" className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                      <SelectValue placeholder="Select node group" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="electronics">ELECTRONICS</SelectItem>
                      <SelectItem value="mechanical">MECHANICAL</SelectItem>
                      <SelectItem value="assembly">ASSEMBLY</SelectItem>
                      <SelectItem value="raw_material">RAW_MATERIAL_NODE</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="name" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.new.strategicName') || 'Strategic Name'} *</Label>
                <Input
                  id="name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Intelligence Node Description"
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.new.detailedContext') || 'Detailed Context'}</Label>
                <Textarea
                  id="description"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Incorporate technical specifications and required outcomes..."
                  className="rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed h-48 resize-none"
                  rows={4}
                />
              </div>
            </CardContent>
          </Card>

          <div className="space-y-8">
            <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('products.new.supplyDynamics') || 'Supply Dynamics'}</CardTitle>
              </CardHeader>
              <CardContent className="p-8 space-y-8">
                <div className="grid gap-8 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="uom" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.new.unitProtocol') || 'Unit Protocol'}</Label>
                    <Input
                      id="uom"
                      value={form.unitOfMeasure}
                      onChange={(e) => setForm({ ...form, unitOfMeasure: e.target.value.toUpperCase() })}
                      placeholder="EA, KG, etc."
                      className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="leadTime" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.new.temporalLead') || 'Temporal Lead (Days)'}</Label>
                    <Input
                      id="leadTime"
                      type="number"
                      value={form.leadTimeDays}
                      onChange={(e) => setForm({ ...form, leadTimeDays: Number(e.target.value) })}
                      className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reorderPoint" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">Reorder Magnitude</Label>
                  <Input
                    id="reorderPoint"
                    type="number"
                    value={form.reorderPoint}
                    onChange={(e) => setForm({ ...form, reorderPoint: Number(e.target.value) })}
                    className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">Financial Parameters</CardTitle>
              </CardHeader>
              <CardContent className="p-8 space-y-8">
                <div className="grid gap-8 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="standardCost" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">Standard Cost Protocol</Label>
                    <div className="relative">
                      <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/20" />
                      <Input
                        id="standardCost"
                        type="number"
                        step="0.01"
                        value={form.standardCost}
                        onChange={(e) => setForm({ ...form, standardCost: Number(e.target.value) })}
                        className="pl-9 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="listPrice" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">Strategic List Price</Label>
                    <div className="relative">
                      <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/20" />
                      <Input
                        id="listPrice"
                        type="number"
                        step="0.01"
                        value={form.listPrice}
                        onChange={(e) => setForm({ ...form, listPrice: Number(e.target.value) })}
                        className="pl-9 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                      />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </form>
    </div>
  );
}
