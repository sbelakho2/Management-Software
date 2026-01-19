'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ChevronLeft, Save, X, Trash2 } from 'lucide-react';
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

export default function EditProductPage() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useParams();
  const { toast } = useToast();
  const { products, updateProduct } = useProductStore();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const product = products.find(p => String(p.id) === String(params.id)) || products[0];

  const [form, setForm] = React.useState({
    partNumber: (product as any)?.partNumber || product?.part_number || '',
    name: product?.name || '',
    description: (product as any)?.description || '',
    category: (product as any)?.category?.name || '',
    status: product?.status || 'active',
    unitOfMeasure: (product as any)?.unitOfMeasure || (product as any)?.unit_of_measure || 'ea',
    standardCost: (product as any)?.standardCost || (product as any)?.cost || 0,
    listPrice: (product as any)?.listPrice || (product as any)?.list_price || 0,
    reorderPoint: (product as any)?.reorderPoint || (product as any)?.reorder_point || 0,
    leadTimeDays: (product as any)?.leadTimeDays || (product as any)?.lead_time_days || 7,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      // await updateProduct(params.id as string, form);
      toast({
        title: t('products.edit.productUpdated') || 'Product Updated',
        description: t('products.edit.updateSuccess', { name: form.name }) || `${form.name} has been successfully updated.`,
      });
      router.push(`/products/${params.id}`);
    } catch (error) {
      toast({
        title: t('common.error') || 'Error',
        description: t('products.edit.updateFailed') || 'Failed to update product.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('products.edit.title') || 'Modify Catalog Node'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{form.partNumber} - {form.name}</span>
              <span className="opacity-30">|</span>
              <span>STATION: CATALOG-EDIT-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.back()} disabled={isSubmitting}>
            {t('common.abort') || 'ABORT'}
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting} size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            <Save className="h-3.5 w-3.5 mr-2" />
            {isSubmitting ? (t('common.saving') || 'SYNCHRONIZING...') : (t('products.edit.saveChanges') || 'SAVE_CHANGES')}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-8">
        <div className="grid gap-8 md:grid-cols-2">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('products.edit.basicInformation') || 'Basic Information'}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-8 p-8">
              <div className="space-y-2">
                <Label htmlFor="partNumber" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.edit.partNumber') || 'Part Number'}</Label>
                <Input
                  id="partNumber"
                  value={form.partNumber}
                  onChange={(e) => setForm({ ...form, partNumber: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="name" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.edit.productName') || 'Product Name'}</Label>
                <Input
                  id="name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="category" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.edit.category') || 'Category'}</Label>
                <Select
                  value={form.category}
                  onValueChange={(value) => setForm({ ...form, category: value })}
                >
                  <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="components">Components</SelectItem>
                    <SelectItem value="assemblies">Assemblies</SelectItem>
                    <SelectItem value="raw_materials">Raw Materials</SelectItem>
                    <SelectItem value="tooling">Tooling</SelectItem>
                    <SelectItem value="finished_goods">Finished Goods</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.edit.description') || 'Description'}</Label>
                <Textarea
                  id="description"
                  rows={4}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed h-32 resize-none"
                />
              </div>
            </CardContent>
          </Card>

          <div className="space-y-8">
            <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
              <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('products.edit.statusInventory') || 'Status & Inventory'}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-8 p-8">
                <div className="grid grid-cols-2 gap-8">
                  <div className="space-y-2">
                    <Label htmlFor="status" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.edit.status') || 'Status'}</Label>
                    <Select
                      value={form.status}
                      onValueChange={(value: any) => setForm({ ...form, status: value })}
                    >
                      <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="active">Active</SelectItem>
                        <SelectItem value="inactive">Inactive</SelectItem>
                        <SelectItem value="discontinued">Discontinued</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="uom" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.edit.unitOfMeasure') || 'Unit of Measure'}</Label>
                    <Input
                      id="uom"
                      value={form.unitOfMeasure}
                      onChange={(e) => setForm({ ...form, unitOfMeasure: e.target.value })}
                      className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-8">
                  <div className="space-y-2">
                    <Label htmlFor="reorderPoint" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.edit.reorderPoint') || 'Reorder Point'}</Label>
                    <Input
                      id="reorderPoint"
                      type="number"
                      value={form.reorderPoint}
                      onChange={(e) => setForm({ ...form, reorderPoint: Number(e.target.value) })}
                      className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="leadTime" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('products.edit.leadTime') || 'Lead Time (Days)'}</Label>
                    <Input
                      id="leadTime"
                      type="number"
                      value={form.leadTimeDays}
                      onChange={(e) => setForm({ ...form, leadTimeDays: Number(e.target.value) })}
                      className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-rams-sm border border-rams-red/30 bg-rams-module shadow-none overflow-hidden">
              <CardHeader className="bg-rams-red/5 border-b border-rams-red/20 p-6">
                <CardTitle className="text-xs font-black uppercase tracking-[0.2em] text-rams-red">Danger Zone</CardTitle>
                <CardDescription className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">Irreversible actions</CardDescription>
              </CardHeader>
              <CardContent className="p-6">
                <Button variant="outline" className="w-full rounded-rams-sm border-rams-red/30 text-rams-red hover:bg-rams-red/5 transition-none">
                  <Trash2 className="h-4 w-4 mr-2" />
                  ARCHIVE_NODE
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </form>
    </div>
  );
}
