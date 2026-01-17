'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X, AlertCircle } from 'lucide-react';
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
import { useQualityStore } from '@/stores';
import { useI18n } from '@/contexts/i18n-context';

export default function NewNCRPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const { createNCR } = useQualityStore();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const [form, setForm] = React.useState({
    title: '',
    description: '',
    severity: 'minor',
    productId: '',
    workOrderId: '',
    location: '',
    detectedBy: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title || !form.description) {
      toast({
        title: 'Validation Error',
        description: 'Title and Description are required.',
        variant: 'destructive',
      });
      return;
    }

    setIsSubmitting(true);
    try {
      await createNCR({
        title: form.title,
        description: form.description,
        severity: form.severity as any,
        product_id: form.productId || undefined,
        work_order_id: form.workOrderId || undefined,
      });
      toast({
        title: 'NCR Created',
        description: `NCR has been successfully recorded.`,
      });
      router.push('/quality?tab=ncrs');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create NCR.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">New NCR</h1>
            <p className="text-muted-foreground">Report a new non-conformance</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => router.back()} disabled={isSubmitting}>
            <X className="h-4 w-4 mr-2" />
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            <Save className="h-4 w-4 mr-2" />
            {isSubmitting ? 'Creating...' : 'Create NCR'}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>Non-Conformance Details</CardTitle>
            <CardDescription>Describe the issue and its context</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Issue Title *</Label>
              <Input
                id="title"
                placeholder="e.g., Dimensional deviation in bracket holes"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="severity">Severity</Label>
                <Select
                  value={form.severity}
                  onValueChange={(value) => setForm({ ...form, severity: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="minor">Minor</SelectItem>
                    <SelectItem value="major">Major</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="location">Location/Station</Label>
                <Input
                  id="location"
                  placeholder="e.g., Assembly Line 2"
                  value={form.location}
                  onChange={(e) => setForm({ ...form, location: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="productId">Related Product</Label>
                <Input
                  id="productId"
                  placeholder="Part Number"
                  value={form.productId}
                  onChange={(e) => setForm({ ...form, productId: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="workOrderId">Related Work Order</Label>
                <Input
                  id="workOrderId"
                  placeholder="WO Number"
                  value={form.workOrderId}
                  onChange={(e) => setForm({ ...form, workOrderId: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description of Non-Conformance *</Label>
              <Textarea
                id="description"
                placeholder="Provide detailed information about the discrepancy..."
                rows={5}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                required
              />
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
