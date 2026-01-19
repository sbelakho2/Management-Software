'use client';

import * as React from 'react';
import { useFinanceStore } from '@/stores';
import { useI18n } from '@/contexts/i18n-context';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

export default function CostingPage() {
  const { t } = useI18n();
  const {
    standardCosts,
    costRollups,
    fetchStandardCosts,
    fetchCostRollups,
    upsertStandardCost,
    createCostRollup,
    loading,
  } = useFinanceStore();

  const [standardForm, setStandardForm] = React.useState({
    sku: '',
    currency: 'USD',
    effectiveDate: '',
    materialUnitCost: '',
    laborUnitCost: '',
    overheadUnitCost: '',
  });

  const [rollupForm, setRollupForm] = React.useState({
    workOrderId: '',
    finishedSku: '',
    currency: 'USD',
    plannedQuantity: '',
    completedQuantity: '',
    actualMaterialCost: '',
    actualLaborCost: '',
    actualOverheadCost: '',
    relievedActualCost: '',
    varianceMaterial: '',
    varianceLabor: '',
    varianceOverhead: '',
    varianceTotal: '',
  });

  React.useEffect(() => {
    fetchStandardCosts();
    fetchCostRollups();
  }, [fetchCostRollups, fetchStandardCosts]);

  const handleSaveStandard = async () => {
    if (!standardForm.sku || !standardForm.effectiveDate) {
      return;
    }
    await upsertStandardCost({
      sku: standardForm.sku,
      currency: standardForm.currency,
      effective_date: standardForm.effectiveDate,
      material_unit_cost: Number(standardForm.materialUnitCost || 0),
      labor_unit_cost: Number(standardForm.laborUnitCost || 0),
      overhead_unit_cost: Number(standardForm.overheadUnitCost || 0),
    });
    setStandardForm({
      sku: '',
      currency: 'USD',
      effectiveDate: '',
      materialUnitCost: '',
      laborUnitCost: '',
      overheadUnitCost: '',
    });
  };

  const handleCreateRollup = async () => {
    if (!rollupForm.workOrderId || !rollupForm.finishedSku) {
      return;
    }
    await createCostRollup({
      work_order_id: rollupForm.workOrderId,
      finished_sku: rollupForm.finishedSku,
      currency: rollupForm.currency,
      planned_quantity: Number(rollupForm.plannedQuantity || 0),
      completed_quantity: Number(rollupForm.completedQuantity || 0),
      actual_material_cost: Number(rollupForm.actualMaterialCost || 0),
      actual_labor_cost: Number(rollupForm.actualLaborCost || 0),
      actual_overhead_cost: Number(rollupForm.actualOverheadCost || 0),
      relieved_actual_cost: Number(rollupForm.relievedActualCost || 0),
      variance_material: Number(rollupForm.varianceMaterial || 0),
      variance_labor: Number(rollupForm.varianceLabor || 0),
      variance_overhead: Number(rollupForm.varianceOverhead || 0),
      variance_total: Number(rollupForm.varianceTotal || 0),
    });
    setRollupForm({
      workOrderId: '',
      finishedSku: '',
      currency: 'USD',
      plannedQuantity: '',
      completedQuantity: '',
      actualMaterialCost: '',
      actualLaborCost: '',
      actualOverheadCost: '',
      relievedActualCost: '',
      varianceMaterial: '',
      varianceLabor: '',
      varianceOverhead: '',
      varianceTotal: '',
    });
  };

  return (
    <div className="space-y-8 page-fade-in">
      <div className="border-b border-rams-line pb-6">
        <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('pages.finance.costing.title') || 'Costing Rollups'}</h1>
        <p className="text-2xs font-mono uppercase tracking-widest text-rams-muted">{t('pages.finance.costing.subtitle') || 'Persist standard costs and track variance rollups'}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="border-b border-rams-line">
            <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.costing.standardCost') || 'Standard Cost'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.sku') || 'SKU'}</label>
                <Input value={standardForm.sku} onChange={(e) => setStandardForm((prev) => ({ ...prev, sku: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.currency') || 'Currency'}</label>
                <Input value={standardForm.currency} onChange={(e) => setStandardForm((prev) => ({ ...prev, currency: e.target.value.toUpperCase() }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.effectiveDate') || 'Effective Date'}</label>
                <Input type="date" value={standardForm.effectiveDate} onChange={(e) => setStandardForm((prev) => ({ ...prev, effectiveDate: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.materialUnitCost') || 'Material Unit Cost'}</label>
                <Input type="number" value={standardForm.materialUnitCost} onChange={(e) => setStandardForm((prev) => ({ ...prev, materialUnitCost: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.laborUnitCost') || 'Labor Unit Cost'}</label>
                <Input type="number" value={standardForm.laborUnitCost} onChange={(e) => setStandardForm((prev) => ({ ...prev, laborUnitCost: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.overheadUnitCost') || 'Overhead Unit Cost'}</label>
                <Input type="number" value={standardForm.overheadUnitCost} onChange={(e) => setStandardForm((prev) => ({ ...prev, overheadUnitCost: e.target.value }))} />
              </div>
            </div>
            <Button onClick={handleSaveStandard} disabled={loading} className="w-full">{t('pages.finance.costing.saveStandardCost') || 'Save Standard Cost'}</Button>
          </CardContent>
        </Card>

        <Card className="rounded-rams-sm border-rams-line bg-rams-module">
          <CardHeader className="border-b border-rams-line">
            <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.costing.costRollupEntry') || 'Cost Rollup Entry'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.workOrder') || 'Work Order'}</label>
                <Input value={rollupForm.workOrderId} onChange={(e) => setRollupForm((prev) => ({ ...prev, workOrderId: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.finishedSku') || 'Finished SKU'}</label>
                <Input value={rollupForm.finishedSku} onChange={(e) => setRollupForm((prev) => ({ ...prev, finishedSku: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.plannedQty') || 'Planned Qty'}</label>
                <Input type="number" value={rollupForm.plannedQuantity} onChange={(e) => setRollupForm((prev) => ({ ...prev, plannedQuantity: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.completedQty') || 'Completed Qty'}</label>
                <Input type="number" value={rollupForm.completedQuantity} onChange={(e) => setRollupForm((prev) => ({ ...prev, completedQuantity: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.actualMaterial') || 'Actual Material'}</label>
                <Input type="number" value={rollupForm.actualMaterialCost} onChange={(e) => setRollupForm((prev) => ({ ...prev, actualMaterialCost: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.actualLabor') || 'Actual Labor'}</label>
                <Input type="number" value={rollupForm.actualLaborCost} onChange={(e) => setRollupForm((prev) => ({ ...prev, actualLaborCost: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.actualOverhead') || 'Actual Overhead'}</label>
                <Input type="number" value={rollupForm.actualOverheadCost} onChange={(e) => setRollupForm((prev) => ({ ...prev, actualOverheadCost: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.relievedCost') || 'Relieved Cost'}</label>
                <Input type="number" value={rollupForm.relievedActualCost} onChange={(e) => setRollupForm((prev) => ({ ...prev, relievedActualCost: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.varianceMaterial') || 'Variance Material'}</label>
                <Input type="number" value={rollupForm.varianceMaterial} onChange={(e) => setRollupForm((prev) => ({ ...prev, varianceMaterial: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.varianceLabor') || 'Variance Labor'}</label>
                <Input type="number" value={rollupForm.varianceLabor} onChange={(e) => setRollupForm((prev) => ({ ...prev, varianceLabor: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.varianceOverhead') || 'Variance Overhead'}</label>
                <Input type="number" value={rollupForm.varianceOverhead} onChange={(e) => setRollupForm((prev) => ({ ...prev, varianceOverhead: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground">{t('pages.finance.costing.varianceTotal') || 'Variance Total'}</label>
                <Input type="number" value={rollupForm.varianceTotal} onChange={(e) => setRollupForm((prev) => ({ ...prev, varianceTotal: e.target.value }))} />
              </div>
            </div>
            <Button onClick={handleCreateRollup} disabled={loading} className="w-full">{t('pages.finance.costing.recordRollup') || 'Record Rollup'}</Button>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-rams-sm border-rams-line bg-rams-module">
        <CardHeader className="border-b border-rams-line">
          <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.costing.standardCosts') || 'Standard Costs'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-rams-line bg-rams-panel">
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.costing.sku') || 'SKU'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.costing.effective') || 'Effective'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.costing.totalUnit') || 'Total Unit'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.costing.currency') || 'Currency'}</th>
              </tr>
            </thead>
            <tbody>
              {standardCosts.length === 0 ? (
                <tr><td colSpan={4} className="py-8 text-center text-rams-muted">{t('pages.finance.costing.noStandardCosts') || 'No standard costs.'}</td></tr>
              ) : (
                standardCosts.map((cost: any) => (
                  <tr key={cost.id} className="border-b border-rams-line hover:bg-rams-panel transition-none">
                    <td className="py-3 px-4 font-medium">{cost.sku}</td>
                    <td className="py-3 px-4 text-muted-foreground">{cost.effective_date}</td>
                    <td className="py-3 px-4 text-muted-foreground">{cost.total_unit_cost}</td>
                    <td className="py-3 px-4"><Badge variant="secondary">{cost.currency}</Badge></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card className="rounded-rams-sm border-rams-line bg-rams-module">
        <CardHeader className="border-b border-rams-line">
          <CardTitle className="text-2xs font-mono font-bold uppercase tracking-widest text-rams-muted">{t('pages.finance.costing.costRollups') || 'Cost Rollups'}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-rams-line bg-rams-panel">
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.costing.workOrder') || 'Work Order'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.costing.sku') || 'SKU'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.costing.variance') || 'Variance'}</th>
                <th className="py-3 px-4 text-left font-medium">{t('pages.finance.costing.currency') || 'Currency'}</th>
              </tr>
            </thead>
            <tbody>
              {costRollups.length === 0 ? (
                <tr><td colSpan={4} className="py-8 text-center text-rams-muted">{t('pages.finance.costing.noRollups') || 'No rollups recorded.'}</td></tr>
              ) : (
                costRollups.map((rollup: any) => (
                  <tr key={rollup.id} className="border-b border-rams-line hover:bg-rams-panel transition-none">
                    <td className="py-3 px-4 font-medium">{rollup.work_order_id}</td>
                    <td className="py-3 px-4 text-muted-foreground">{rollup.finished_sku}</td>
                    <td className="py-3 px-4 text-muted-foreground">{rollup.variance_total}</td>
                    <td className="py-3 px-4"><Badge variant="secondary">{rollup.currency}</Badge></td>
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
