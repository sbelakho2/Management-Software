'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X, Package } from 'lucide-react';
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
        title: 'Required Parameters missing',
        description: 'Please provide at least a Part Node Identity and Product Name.',
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
        title: 'Node Synchronized',
        description: `${form.name} has been successfully established in the catalog.`,
      });
      router.push('/products');
    } catch (error) {
      toast({
        title: 'Synchronization Failed',
        description: 'Failed to establish product node. Please re-authenticate.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">New Catalog Node</h1>
            <p className="text-muted-foreground font-medium text-sm">Incorporate a new item into the global product intelligence mesh</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary h-12 px-8" onClick={() => router.back()} disabled={isSubmitting}>
            Abort
          </Button>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine h-12 px-8 font-bold" onClick={handleSubmit} disabled={isSubmitting}>
            <Save className="h-4 w-4 mr-2" />
            {isSubmitting ? 'Synchronizing...' : 'Establish Node'}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-8">
        <div className="grid gap-8 md:grid-cols-2">
          <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium overflow-hidden">
            <CardHeader className="pb-8 border-b border-border/5 bg-muted/5 p-8">
              <CardTitle className="text-lg font-heading">Basic Identification</CardTitle>
              <CardDescription className="text-xs font-medium uppercase tracking-wider">Primary node parameters and categorization</CardDescription>
            </CardHeader>
            <CardContent className="space-y-8 p-8">
              <div className="grid gap-8 sm:grid-cols-2">
                <div className="space-y-3">
                  <Label htmlFor="partNumber" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Part Node Identity *</Label>
                  <Input
                    id="partNumber"
                    value={form.partNumber}
                    onChange={(e) => setForm({ ...form, partNumber: e.target.value })}
                    placeholder="e.g. PN-2024-001"
                    className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50"
                    required
                  />
                </div>
                <div className="space-y-3">
                  <Label htmlFor="category" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Taxonomy Category</Label>
                  <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                    <SelectTrigger id="category" className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft">
                      <SelectValue placeholder="Select node group" />
                    </SelectTrigger>
                    <SelectContent className="rounded-2xl shadow-premium">
                      <SelectItem value="electronics" className="rounded-xl m-1">Electronics</SelectItem>
                      <SelectItem value="mechanical" className="rounded-xl m-1">Mechanical</SelectItem>
                      <SelectItem value="assembly" className="rounded-xl m-1">Assembly</SelectItem>
                      <SelectItem value="raw_material" className="rounded-xl m-1">Raw Material Node</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-3">
                <Label htmlFor="name" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Strategic Name *</Label>
                <Input
                  id="name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Intelligence Node Description"
                  className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft"
                  required
                />
              </div>
              <div className="space-y-3">
                <Label htmlFor="description" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Detailed Context</Label>
                <Textarea
                  id="description"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Incorporate technical specifications and required outcomes..."
                  className="rounded-[1.5rem] bg-background/50 border-border/50 shadow-inner-soft focus:border-primary/50 transition-all min-h-[120px] resize-none"
                  rows={4}
                />
              </div>
            </CardContent>
          </Card>

          <div className="space-y-8">
            <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium">
              <CardHeader className="p-8 pb-4">
                <CardTitle className="text-lg font-heading">Supply Dynamics</CardTitle>
                <CardDescription className="text-xs font-medium uppercase tracking-wider">Inventory thresholds and temporal parameters</CardDescription>
              </CardHeader>
              <CardContent className="p-8 pt-0 space-y-8">
                <div className="grid gap-8 sm:grid-cols-2">
                  <div className="space-y-3">
                    <Label htmlFor="uom" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Unit Protocol</Label>
                    <Input
                      id="uom"
                      value={form.unitOfMeasure}
                      onChange={(e) => setForm({ ...form, unitOfMeasure: e.target.value })}
                      placeholder="ea, kg, etc."
                      className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft"
                    />
                  </div>
                  <div className="space-y-3">
                    <Label htmlFor="leadTime" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Temporal Lead (Days)</Label>
                    <Input
                      id="leadTime"
                      type="number"
                      value={form.leadTimeDays}
                      onChange={(e) => setForm({ ...form, leadTimeDays: Number(e.target.value) })}
                      className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft"
                    />
                  </div>
                </div>
                <div className="space-y-3">
                  <Label htmlFor="reorderPoint" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Reorder Magnitude</Label>
                  <Input
                    id="reorderPoint"
                    type="number"
                    value={form.reorderPoint}
                    onChange={(e) => setForm({ ...form, reorderPoint: Number(e.target.value) })}
                    className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft"
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium">
              <CardHeader className="p-8 pb-4">
                <CardTitle className="text-lg font-heading">Financial Parameters</CardTitle>
                <CardDescription className="text-xs font-medium uppercase tracking-wider">Magnitude valuation and cost architecture</CardDescription>
              </CardHeader>
              <CardContent className="p-8 pt-0 space-y-8">
                <div className="grid gap-8 sm:grid-cols-2">
                  <div className="space-y-3">
                    <Label htmlFor="standardCost" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Standard Cost Protocol</Label>
                    <div className="relative">
                      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground/30 text-sm">$</div>
                      <Input
                        id="standardCost"
                        type="number"
                        step="0.01"
                        value={form.standardCost}
                        onChange={(e) => setForm({ ...form, standardCost: Number(e.target.value) })}
                        className="pl-8 h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft"
                      />
                    </div>
                  </div>
                  <div className="space-y-3">
                    <Label htmlFor="listPrice" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Strategic List Price</Label>
                    <div className="relative">
                      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground/30 text-sm">$</div>
                      <Input
                        id="listPrice"
                        type="number"
                        step="0.01"
                        value={form.listPrice}
                        onChange={(e) => setForm({ ...form, listPrice: Number(e.target.value) })}
                        className="pl-8 h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft"
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
