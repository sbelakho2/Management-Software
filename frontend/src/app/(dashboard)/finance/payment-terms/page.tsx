'use client';

import * as React from 'react';
import { useI18n } from '@/contexts/i18n-context';
import { useFinanceStore } from '@/stores';
import { 
  Calendar,
  Plus,
  RefreshCw,
  Loader2,
  Edit,
  Percent,
  Clock,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import { FINANCE_ROLES } from '@/lib/page-access';
import { PageGuard } from '@/components/layout/page-guard';
import type { PaymentTerm } from '@/types';

export default function PaymentTermsPage() {
  const { t } = useI18n();
  const {
    paymentTerms,
    loading,
    fetchPaymentTerms,
    createPaymentTerm,
    updatePaymentTerm,
  } = useFinanceStore();

  const [showAddDialog, setShowAddDialog] = React.useState(false);
  const [editingTerm, setEditingTerm] = React.useState<PaymentTerm | null>(null);

  const [formData, setFormData] = React.useState({
    code: '',
    name: '',
    days_due: 30,
    discount_percent: 0,
    discount_days: 0,
    description: '',
    is_active: true,
  });

  React.useEffect(() => {
    fetchPaymentTerms();
  }, [fetchPaymentTerms]);

  React.useEffect(() => {
    if (editingTerm) {
      setFormData({
        code: editingTerm.code,
        name: editingTerm.name,
        days_due: editingTerm.days_due,
        discount_percent: editingTerm.discount_percent,
        discount_days: editingTerm.discount_days,
        description: editingTerm.description || '',
        is_active: editingTerm.is_active,
      });
    } else {
      setFormData({
        code: '',
        name: '',
        days_due: 30,
        discount_percent: 0,
        discount_days: 0,
        description: '',
        is_active: true,
      });
    }
  }, [editingTerm]);

  const handleSubmit = async () => {
    if (editingTerm) {
      await updatePaymentTerm(editingTerm.id, formData);
      setEditingTerm(null);
    } else {
      await createPaymentTerm(formData);
      setShowAddDialog(false);
    }
    setFormData({
      code: '',
      name: '',
      days_due: 30,
      discount_percent: 0,
      discount_days: 0,
      description: '',
      is_active: true,
    });
  };

  const FormContent = () => (
    <div className="grid gap-4 py-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label>Code</Label>
          <Input
            value={formData.code}
            onChange={(e) => setFormData((prev) => ({ ...prev, code: e.target.value.toUpperCase() }))}
            placeholder="NET30"
            disabled={!!editingTerm}
          />
        </div>
        <div className="grid gap-2">
          <Label>Name</Label>
          <Input
            value={formData.name}
            onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
            placeholder="Net 30 Days"
          />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="grid gap-2">
          <Label className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Days Due
          </Label>
          <Input
            type="number"
            value={formData.days_due}
            onChange={(e) => setFormData((prev) => ({ ...prev, days_due: parseInt(e.target.value) || 0 }))}
          />
        </div>
        <div className="grid gap-2">
          <Label className="flex items-center gap-2">
            <Percent className="h-4 w-4" />
            Early Discount %
          </Label>
          <Input
            type="number"
            step="0.01"
            value={formData.discount_percent}
            onChange={(e) => setFormData((prev) => ({ ...prev, discount_percent: parseFloat(e.target.value) || 0 }))}
          />
        </div>
        <div className="grid gap-2">
          <Label>Discount Days</Label>
          <Input
            type="number"
            value={formData.discount_days}
            onChange={(e) => setFormData((prev) => ({ ...prev, discount_days: parseInt(e.target.value) || 0 }))}
          />
        </div>
      </div>
      <div className="grid gap-2">
        <Label>Description</Label>
        <Textarea
          value={formData.description}
          onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
          placeholder="Payment terms description..."
          rows={3}
        />
      </div>
      <div className="flex items-center gap-2">
        <Switch
          checked={formData.is_active}
          onCheckedChange={(checked) => setFormData((prev) => ({ ...prev, is_active: checked }))}
        />
        <Label>Active</Label>
      </div>
    </div>
  );

  return (
    <PageGuard requiredRoles={FINANCE_ROLES}>
      <div className="space-y-8 page-fade-in pb-12">
        {/* Header */}
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              Payment Terms
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">
              Configure payment terms for customers and suppliers
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" size="sm" onClick={() => fetchPaymentTerms()} disabled={loading}>
              <RefreshCw className={cn('h-4 w-4 mr-2', loading && 'animate-spin')} />
              Refresh
            </Button>
            <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
              <DialogTrigger asChild>
                <Button size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Payment Term
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Payment Term</DialogTitle>
                </DialogHeader>
                <FormContent />
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowAddDialog(false)}>Cancel</Button>
                  <Button onClick={handleSubmit} disabled={loading}>
                    {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                    Create
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Payment Terms Grid */}
        {loading && paymentTerms.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : paymentTerms.length === 0 ? (
          <Card className="rounded-rams-sm border-rams-line bg-rams-module">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Calendar className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">No payment terms configured</p>
              <Button size="sm" className="mt-4" onClick={() => setShowAddDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add First Payment Term
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {paymentTerms.map((term) => (
              <Card key={term.id} className="rounded-rams-sm border-rams-line bg-rams-module">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base font-semibold">{term.name}</CardTitle>
                      <p className="text-xs text-muted-foreground font-mono">{term.code}</p>
                    </div>
                    <Badge variant={term.is_active ? 'default' : 'secondary'}>
                      {term.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="p-2 rounded bg-muted/50">
                      <p className="text-2xl font-bold">{term.days_due}</p>
                      <p className="text-xs text-muted-foreground">Days Due</p>
                    </div>
                    {term.discount_percent > 0 ? (
                      <>
                        <div className="p-2 rounded bg-emerald-500/10">
                          <p className="text-2xl font-bold text-emerald-500">{term.discount_percent}%</p>
                          <p className="text-xs text-muted-foreground">Discount</p>
                        </div>
                        <div className="p-2 rounded bg-muted/50">
                          <p className="text-2xl font-bold">{term.discount_days}</p>
                          <p className="text-xs text-muted-foreground">Days</p>
                        </div>
                      </>
                    ) : (
                      <div className="col-span-2 p-2 rounded bg-muted/50">
                        <p className="text-sm text-muted-foreground">No early payment discount</p>
                      </div>
                    )}
                  </div>
                  {term.description && (
                    <p className="text-sm text-muted-foreground">{term.description}</p>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => setEditingTerm(term as unknown as PaymentTerm)}
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Edit Dialog */}
        <Dialog open={!!editingTerm} onOpenChange={(open) => !open && setEditingTerm(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Payment Term</DialogTitle>
            </DialogHeader>
            <FormContent />
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingTerm(null)}>Cancel</Button>
              <Button onClick={handleSubmit} disabled={loading}>
                {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </PageGuard>
  );
}
