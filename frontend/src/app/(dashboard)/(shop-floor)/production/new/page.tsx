'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X, Factory } from 'lucide-react';
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
        title: 'Validation Error',
        description: 'Please fill in all required fields.',
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
        title: 'Work Order Created',
        description: `Order ${form.orderNumber} has been scheduled.`,
      });
      router.push('/production');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create work order.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">New Execution Node</h1>
            <p className="text-muted-foreground font-medium text-sm">Schedule and establish a new organizational production run</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary h-12 px-8" onClick={() => router.back()} disabled={isSubmitting}>Abort</Button>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine h-12 px-8 font-bold" onClick={handleSubmit} disabled={isSubmitting}>
            <Save className="h-4 w-4 mr-2" />
            {isSubmitting ? 'Synchronizing...' : 'Establish Order'}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium overflow-hidden">
          <CardHeader className="pb-8 border-b border-border/5 bg-muted/5 p-8">
            <CardTitle className="text-lg font-heading">Operational Parameters</CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Specify product nodes, magnitude, and strategic horizons</CardDescription>
          </CardHeader>
          <CardContent className="space-y-8 p-8">
            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-3">
                <Label htmlFor="orderNumber" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Work Order Identity</Label>
                <Input
                  id="orderNumber"
                  value={form.orderNumber}
                  readOnly
                  className="h-12 rounded-2xl bg-muted/20 border-border/50 text-muted-foreground/60 font-mono font-bold"
                />
              </div>
              <div className="space-y-3">
                <Label htmlFor="priority" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Priority Layer</Label>
                <Select
                  value={form.priority}
                  onValueChange={(value) => setForm({ ...form, priority: value })}
                >
                  <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-2xl shadow-premium">
                    <SelectItem value="low" className="rounded-xl m-1">Low Velocity</SelectItem>
                    <SelectItem value="normal" className="rounded-xl m-1">Standard Node</SelectItem>
                    <SelectItem value="high" className="rounded-xl m-1">High Priority</SelectItem>
                    <SelectItem value="urgent" className="rounded-xl m-1">Urgent Escalation</SelectItem>
                    <SelectItem value="critical" className="rounded-xl m-1">Critical Threshold</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-3">
              <Label htmlFor="product" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Target Product Node *</Label>
              <Select
                value={form.productId}
                onValueChange={(value) => setForm({ ...form, productId: value })}
              >
                <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft">
                  <SelectValue placeholder="Identify target product in mesh..." />
                </SelectTrigger>
                <SelectContent className="rounded-2xl shadow-premium">
                  {products.map((p) => (
                    <SelectItem key={p.id} value={String(p.id)} className="rounded-xl m-1">
                      {(p as any).partNumber || (p as any).part_number} - {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-3">
                <Label htmlFor="quantity" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Magnitude (Quantity) *</Label>
                <Input
                  id="quantity"
                  type="number"
                  min="1"
                  className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft"
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
                  required
                />
              </div>
              <div className="space-y-3">
                <Label htmlFor="dueDate" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Temporal Horizon *</Label>
                <div className="relative">
                  <Input
                    id="dueDate"
                    type="date"
                    className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft"
                    value={form.dueDate}
                    onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
                    required
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <Label htmlFor="notes" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Production Intel & Notes</Label>
              <Textarea
                id="notes"
                placeholder="Incorporate special instructions for the shop floor nodes..."
                className="rounded-[1.5rem] bg-background/50 border-border/50 shadow-inner-soft focus:border-primary/50 transition-all min-h-[120px] resize-none"
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
