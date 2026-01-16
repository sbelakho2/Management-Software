'use client';

import * as React from 'react';
import { useMrpStore } from '@/stores';
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

export default function MpsPage() {
  const {
    mpsPlans,
    mpsLines,
    fetchMpsPlans,
    fetchMpsLines,
    createMpsPlan,
    createMpsLine,
    loading,
  } = useMrpStore();

  const [planForm, setPlanForm] = React.useState({
    name: '',
    periodStart: '',
    periodEnd: '',
    horizonDays: '30',
    notes: '',
  });

  const [lineForm, setLineForm] = React.useState({
    planId: '',
    productId: '',
    bucketDate: '',
    quantity: '',
    sourceType: '',
  });

  React.useEffect(() => {
    fetchMpsPlans();
  }, [fetchMpsPlans]);

  React.useEffect(() => {
    if (!lineForm.planId && mpsPlans.length > 0) {
      setLineForm((prev) => ({ ...prev, planId: mpsPlans[0].id }));
    }
  }, [mpsPlans, lineForm.planId]);

  React.useEffect(() => {
    if (lineForm.planId) {
      fetchMpsLines(lineForm.planId);
    }
  }, [fetchMpsLines, lineForm.planId]);

  const handleCreatePlan = async () => {
    if (!planForm.name || !planForm.periodStart || !planForm.periodEnd) {
      return;
    }
    await createMpsPlan({
      name: planForm.name,
      period_start: planForm.periodStart,
      period_end: planForm.periodEnd,
      horizon_days: Number(planForm.horizonDays || 30),
      notes: planForm.notes || undefined,
      status: 'draft',
    });
    setPlanForm({ name: '', periodStart: '', periodEnd: '', horizonDays: '30', notes: '' });
  };

  const handleCreateLine = async () => {
    if (!lineForm.planId || !lineForm.productId || !lineForm.bucketDate || lineForm.quantity === '') {
      return;
    }
    await createMpsLine(lineForm.planId, {
      product_id: Number(lineForm.productId),
      bucket_date: lineForm.bucketDate,
      quantity: Number(lineForm.quantity),
      source_type: lineForm.sourceType || undefined,
    });
    setLineForm((prev) => ({ ...prev, productId: '', bucketDate: '', quantity: '', sourceType: '' }));
  };

  return (
    <div className="space-y-8 page-fade-in">
      <div>
        <h1 className="text-4xl font-heading font-bold tracking-tight">Master Production Schedule</h1>
        <p className="text-muted-foreground">Plan demand buckets and align MRP inputs</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-base">Create MPS Plan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">Plan Name</label>
                <Input value={planForm.name} onChange={(e) => setPlanForm((prev) => ({ ...prev, name: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Period Start</label>
                <Input type="date" value={planForm.periodStart} onChange={(e) => setPlanForm((prev) => ({ ...prev, periodStart: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Period End</label>
                <Input type="date" value={planForm.periodEnd} onChange={(e) => setPlanForm((prev) => ({ ...prev, periodEnd: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Horizon Days</label>
                <Input type="number" value={planForm.horizonDays} onChange={(e) => setPlanForm((prev) => ({ ...prev, horizonDays: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Notes</label>
                <Input value={planForm.notes} onChange={(e) => setPlanForm((prev) => ({ ...prev, notes: e.target.value }))} />
              </div>
            </div>
            <Button onClick={handleCreatePlan} disabled={loading} className="w-full">Create Plan</Button>
          </CardContent>
        </Card>

        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-base">Add MPS Line</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-muted-foreground">Plan</label>
                <Select value={lineForm.planId} onValueChange={(value) => setLineForm((prev) => ({ ...prev, planId: value }))}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select plan" />
                  </SelectTrigger>
                  <SelectContent>
                    {mpsPlans.map((plan) => (
                      <SelectItem key={plan.id} value={plan.id}>{plan.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Product ID</label>
                <Input value={lineForm.productId} onChange={(e) => setLineForm((prev) => ({ ...prev, productId: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Bucket Date</label>
                <Input type="date" value={lineForm.bucketDate} onChange={(e) => setLineForm((prev) => ({ ...prev, bucketDate: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Quantity</label>
                <Input type="number" value={lineForm.quantity} onChange={(e) => setLineForm((prev) => ({ ...prev, quantity: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">Source</label>
                <Input value={lineForm.sourceType} onChange={(e) => setLineForm((prev) => ({ ...prev, sourceType: e.target.value }))} placeholder="forecast" />
              </div>
            </div>
            <Button onClick={handleCreateLine} disabled={loading || mpsPlans.length === 0} className="w-full">Add Line</Button>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-base">Plans</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">Plan</th>
                <th className="py-3 px-4 text-left font-medium">Period</th>
                <th className="py-3 px-4 text-left font-medium">Horizon</th>
                <th className="py-3 px-4 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {mpsPlans.length === 0 ? (
                <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">No plans created.</td></tr>
              ) : (
                mpsPlans.map((plan) => (
                  <tr key={plan.id} className="border-b hover:bg-muted/50">
                    <td className="py-3 px-4 font-medium">{plan.name}</td>
                    <td className="py-3 px-4 text-muted-foreground">{plan.period_start} - {plan.period_end}</td>
                    <td className="py-3 px-4 text-muted-foreground">{plan.horizon_days} days</td>
                    <td className="py-3 px-4">
                      <Badge variant={plan.status === 'published' ? 'success' : 'secondary'}>{plan.status}</Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-base">Plan Lines</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-3 px-4 text-left font-medium">Bucket</th>
                <th className="py-3 px-4 text-left font-medium">Product</th>
                <th className="py-3 px-4 text-left font-medium">Quantity</th>
                <th className="py-3 px-4 text-left font-medium">Source</th>
              </tr>
            </thead>
            <tbody>
              {mpsLines.length === 0 ? (
                <tr><td colSpan={4} className="py-8 text-center text-muted-foreground">No plan lines.</td></tr>
              ) : (
                mpsLines.map((line) => (
                  <tr key={line.id} className="border-b hover:bg-muted/50">
                    <td className="py-3 px-4 text-muted-foreground">{line.bucket_date}</td>
                    <td className="py-3 px-4 text-muted-foreground">{line.product_id}</td>
                    <td className="py-3 px-4 font-medium">{line.quantity}</td>
                    <td className="py-3 px-4 text-muted-foreground">{line.source_type || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
