'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X, Factory, Loader2 } from 'lucide-react';
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
import { useProductionStore } from '@/stores/production';
import { useProductStore } from '@/stores/products';
import { useI18n } from '@/contexts/i18n-context';

export default function NewWorkOrderPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const { createWorkOrder } = useProductionStore();
  const { products } = useProductStore();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const [form, setForm] = React.useState({
    orderNumber: `WO-${new Date().getFullYear()}-${Math.floor(Math.random() * 10000)}`,
    productId: '',
    quantity: 1,
    dueDate: '',
    priority: 'normal',
    notes: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.productId || form.quantity <= 0 || !form.dueDate) {
      toast({
        title: t('production.new.validationError') || 'Validation Error',
        description: t('production.new.fillRequired') || 'Please fill in all required fields.',
        variant: 'destructive',
      });
      return;
    }

    setIsSubmitting(true);
    try {
      await createWorkOrder({
        work_order_number: form.orderNumber,
        product_id: Number(form.productId),
        quantity_ordered: form.quantity,
        priority: form.priority as any,
        scheduled_end: form.dueDate,
        notes: form.notes,
      });
      toast({
        title: t('production.new.workOrderCreated') || 'Work Order Created',
        description: t('production.new.orderScheduled', { orderNumber: form.orderNumber }) || `Order ${form.orderNumber} has been scheduled.`,
      });
      router.push('/production');
    } catch (error) {
      toast({
        title: t('common.error') || 'Error',
        description: t('production.new.createFailed') || 'Failed to create work order.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('production.new.title') || 'Initialize Execution Node'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('production.new.subtitle') || 'Production Schedule Entry'}</span>
              <span className="opacity-30">|</span>
              <span>STATION: SCHEDULING-01</span>
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
                {t('production.new.establishOrder') || 'ESTABLISH_ORDER'}
              </>
            )}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="animate-in fade-in slide-in-from-bottom-2 duration-500">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('production.new.operationalParameters') || 'Operational Parameters'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-8 p-8">
            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="orderNumber" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('production.new.workOrderIdentity') || 'Work Order Identity'}</Label>
                <Input
                  id="orderNumber"
                  value={form.orderNumber}
                  readOnly
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-muted-foreground/40 font-mono font-bold text-[11px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="priority" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('production.new.priorityLayer') || 'Priority Layer'}</Label>
                <Select
                  value={form.priority}
                  onValueChange={(value) => setForm({ ...form, priority: value })}
                >
                  <SelectTrigger id="priority" className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">{t('production.new.priorities.low')}</SelectItem>
                    <SelectItem value="normal">{t('production.new.priorities.normal')}</SelectItem>
                    <SelectItem value="high">{t('production.new.priorities.high')}</SelectItem>
                    <SelectItem value="urgent">{t('production.new.priorities.urgent')}</SelectItem>
                    <SelectItem value="critical">{t('production.new.priorities.critical')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="product" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('production.new.targetProduct') || 'Target Product Node'} *</Label>
              <Select
                value={form.productId}
                onValueChange={(value) => setForm({ ...form, productId: value })}
              >
                <SelectTrigger id="product" className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                  <SelectValue placeholder="IDENTIFY_TARGET_PRODUCT..." />
                </SelectTrigger>
                <SelectContent>
                  {products.map((p) => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      {((p as any).partNumber || (p as any).part_number || '').toUpperCase()} - {p.name.toUpperCase()}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="quantity" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('production.new.magnitude') || 'Magnitude (Quantity)'} *</Label>
                <Input
                  id="quantity"
                  type="number"
                  min="1"
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="dueDate" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('production.new.temporalHorizon') || 'Temporal Horizon'} *</Label>
                <div className="relative">
                  <Input
                    id="dueDate"
                    type="date"
                    className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                    value={form.dueDate}
                    onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
                    required
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('production.new.notesLabel')}</Label>
              <Textarea
                id="notes"
                placeholder="INCORPORATE_SPECIAL_INSTRUCTIONS..."
                className="rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed h-32 resize-none"
                rows={4}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
