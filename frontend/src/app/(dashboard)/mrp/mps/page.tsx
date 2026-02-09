'use client';

import * as React from 'react';
import { useMrpStore } from '@/stores';
import { useI18n } from '@/contexts/i18n-context';
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
  const { t } = useI18n();
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
      product_id: lineForm.productId,
      bucket_date: lineForm.bucketDate,
      quantity: Number(lineForm.quantity),
      source_type: lineForm.sourceType || undefined,
    });
    setLineForm((prev) => ({ ...prev, productId: '', bucketDate: '', quantity: '', sourceType: '' }));
  };

  return (
    <div className="space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.mrp.mps.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.mrp.mps.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.mrp.mps.station')}</span>
          </p>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        <Card className="rounded-rams-sm">
          <CardHeader>
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.mrp.mps.initializePlanProtocol')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <div className="md:col-span-2 space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.mrp.mps.planIdentity')}</label>
                <Input placeholder={t('pages.mrp.mps.planPlaceholder')} value={planForm.name} onChange={(e) => setPlanForm((prev) => ({ ...prev, name: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.mrp.mps.periodStart')}</label>
                <Input type="date" value={planForm.periodStart} onChange={(e) => setPlanForm((prev) => ({ ...prev, periodStart: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.mrp.mps.periodEnd')}</label>
                <Input type="date" value={planForm.periodEnd} onChange={(e) => setPlanForm((prev) => ({ ...prev, periodEnd: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.mrp.mps.horizonDays')}</label>
                <Input type="number" value={planForm.horizonDays} onChange={(e) => setPlanForm((prev) => ({ ...prev, horizonDays: e.target.value }))} />
              </div>
              <div className="md:col-span-2 space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.mrp.mps.protocolNotes')}</label>
                <Input value={planForm.notes} onChange={(e) => setPlanForm((prev) => ({ ...prev, notes: e.target.value }))} />
              </div>
            </div>
            <Button className="w-full rounded-rams-sm bg-rams-orange text-black font-black uppercase h-10 transition-none" onClick={handleCreatePlan} disabled={loading}>
              {t('pages.mrp.mps.initializeProtocol')}
            </Button>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm">
          <CardHeader>
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.mrp.mps.demandBucketInjection')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <div className="md:col-span-2 space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.mrp.mps.activePlanNode')}</label>
                <Select value={lineForm.planId} onValueChange={(v) => setLineForm((prev) => ({ ...prev, planId: v }))}>
                  <SelectTrigger className="text-[10px] h-10">
                    <SelectValue placeholder={t('pages.mrp.mps.selectProtocol')} />
                  </SelectTrigger>
                  <SelectContent>
                    {mpsPlans.map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.name.toUpperCase()}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.mrp.mps.productId')}</label>
                <Input type="number" value={lineForm.productId} onChange={(e) => setLineForm((prev) => ({ ...prev, productId: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.mrp.mps.bucketDate')}</label>
                <Input type="date" value={lineForm.bucketDate} onChange={(e) => setLineForm((prev) => ({ ...prev, bucketDate: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.mrp.mps.quantityTarget')}</label>
                <Input type="number" value={lineForm.quantity} onChange={(e) => setLineForm((prev) => ({ ...prev, quantity: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <label className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.mrp.mps.sourceType')}</label>
                <Input value={lineForm.sourceType} onChange={(e) => setLineForm((prev) => ({ ...prev, sourceType: e.target.value }))} />
              </div>
            </div>
            <Button className="w-full rounded-rams-sm bg-rams-orange text-black font-black uppercase h-10 transition-none" onClick={handleCreateLine} disabled={loading}>
              {t('pages.mrp.mps.injectDemand')}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-rams-sm overflow-hidden">
        <CardHeader className="bg-rams-panel/30 border-b border-rams-line">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.mrp.mps.table.planProtocolRegistry')}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full border-separate border-spacing-0">
              <thead>
                <tr className="bg-rams-panel">
                  <th className="px-6 py-3 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('pages.mrp.mps.table.planIdentity')}</th>
                  <th className="px-6 py-3 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('pages.mrp.mps.table.periodRange')}</th>
                  <th className="px-6 py-3 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('pages.mrp.mps.table.horizonState')}</th>
                  <th className="px-6 py-3 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('pages.mrp.mps.table.statusNode')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rams-line/30">
                {mpsPlans.map((plan) => (
                  <tr key={plan.id} className="hover:bg-rams-panel/50 transition-none cursor-help">
                    <td className="px-6 py-4">
                      <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{plan.name}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-mono text-[10px] font-bold text-muted-foreground/60">{plan.period_start} - {plan.period_end}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-mono text-[10px] font-bold tabular-nums text-muted-foreground/60">{plan.horizon_days} {t('pages.mrp.mps.table.days')}</p>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant="outline" className="rounded-none border-rams-line font-black text-[8px] uppercase tracking-widest px-1.5 h-4 bg-rams-panel">
                        {plan.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
                {mpsPlans.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center">
                      <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">{t('pages.mrp.mps.table.zeroProtocols')}</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-rams-sm overflow-hidden">
        <CardHeader className="bg-rams-panel/30 border-b border-rams-line">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.mrp.mps.table.planLineExposure')}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full border-separate border-spacing-0">
              <thead>
                <tr className="bg-rams-panel">
                  <th className="px-6 py-3 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('pages.mrp.mps.table.bucketDate')}</th>
                  <th className="px-6 py-3 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('pages.mrp.mps.table.productNode')}</th>
                  <th className="px-6 py-3 text-right text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('pages.mrp.mps.table.quantity')}</th>
                  <th className="px-6 py-3 text-left text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 border-b border-rams-line">{t('pages.mrp.mps.table.sourceStream')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rams-line/30">
                {mpsLines.map((line) => (
                  <tr key={line.id} className="hover:bg-rams-panel/50 transition-none cursor-help">
                    <td className="px-6 py-4">
                      <p className="font-mono text-[10px] font-bold text-muted-foreground/60">{line.bucket_date}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-mono text-[10px] font-bold text-foreground/80">{t('pages.mrp.mps.table.productPrefix')}{line.product_id}</p>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <p className="font-mono font-bold tabular-nums">{line.quantity}</p>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant="secondary" className="rounded-none border-rams-line font-black text-[8px] uppercase tracking-widest px-1.5 h-4">
                        {line.source_type || t('pages.mrp.mps.table.manual')}
                      </Badge>
                    </td>
                  </tr>
                ))}
                {mpsLines.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center">
                      <p className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">{t('pages.mrp.mps.table.zeroDemandLines')}</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
