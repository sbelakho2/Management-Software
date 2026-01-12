'use client';

import * as React from 'react';
import { Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ArrowLeft,
  Save,
  Send,
  Plus,
  Trash2,
  Calculator,
  Percent,
  DollarSign,
  Copy,
  FileText,
  AlertCircle,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { cn, formatCurrency, formatDate, generateId } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

// Types
interface QuoteLineItem {
  id: string;
  partNumber: string;
  description: string;
  quantity: number;
  unitOfMeasure: string;
  unitPrice: number;
  cost?: number;
  leadTimeDays?: number;
  notes?: string;
}

interface QuoteFormData {
  rfqId?: string;
  validUntil: string;
  discountType: 'percentage' | 'amount';
  discountValue: number;
  taxRate: number;
  termsAndConditions: string;
  notes: string;
  lineItems: QuoteLineItem[];
}

// Mock RFQ data (would come from API based on rfq param)
const mockRFQLineItems = [
  { partNumber: 'AER-001', description: 'Precision bracket - Type A', quantity: 200, unitOfMeasure: 'pcs' },
  { partNumber: 'AER-002', description: 'Precision bracket - Type B', quantity: 200, unitOfMeasure: 'pcs' },
  { partNumber: 'AER-003', description: 'Mounting plate assembly', quantity: 100, unitOfMeasure: 'pcs' },
];

const defaultTerms = `1. Payment Terms: Net 30 days from invoice date
2. Validity: This quote is valid for 30 days from the date of issue
3. Delivery: FOB Destination, freight prepaid
4. Lead Time: As specified per line item
5. Warranty: Standard 12-month warranty on all parts`;

function QuoteLineItemRow({ 
  item, 
  onChange, 
  onRemove 
}: { 
  item: QuoteLineItem; 
  onChange: (item: QuoteLineItem) => void;
  onRemove: () => void;
}) {
  const extendedPrice = item.quantity * item.unitPrice;
  const margin = item.cost ? ((item.unitPrice - item.cost) / item.unitPrice) * 100 : null;

  return (
    <tr className="border-b">
      <td className="py-2 px-2">
        <Input
          value={item.partNumber}
          onChange={(e) => onChange({ ...item, partNumber: e.target.value })}
          placeholder="Part #"
          className="w-28"
        />
      </td>
      <td className="py-2 px-2">
        <Input
          value={item.description}
          onChange={(e) => onChange({ ...item, description: e.target.value })}
          placeholder="Description"
          className="min-w-[200px]"
        />
      </td>
      <td className="py-2 px-2">
        <Input
          type="number"
          value={item.quantity}
          onChange={(e) => onChange({ ...item, quantity: parseFloat(e.target.value) || 0 })}
          className="w-20 text-right"
        />
      </td>
      <td className="py-2 px-2">
        <Select value={item.unitOfMeasure} onValueChange={(v) => onChange({ ...item, unitOfMeasure: v })}>
          <SelectTrigger className="w-20">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="pcs">pcs</SelectItem>
            <SelectItem value="ea">ea</SelectItem>
            <SelectItem value="kg">kg</SelectItem>
            <SelectItem value="m">m</SelectItem>
            <SelectItem value="ft">ft</SelectItem>
            <SelectItem value="lot">lot</SelectItem>
          </SelectContent>
        </Select>
      </td>
      <td className="py-2 px-2">
        <div className="relative">
          <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="number"
            value={item.unitPrice}
            onChange={(e) => onChange({ ...item, unitPrice: parseFloat(e.target.value) || 0 })}
            className="w-28 pl-7 text-right"
            step="0.01"
          />
        </div>
      </td>
      <td className="py-2 px-2 text-right font-medium">
        {formatCurrency(extendedPrice)}
      </td>
      <td className="py-2 px-2">
        <div className="relative">
          <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="number"
            value={item.cost || ''}
            onChange={(e) => onChange({ ...item, cost: parseFloat(e.target.value) || undefined })}
            placeholder="Cost"
            className="w-24 pl-7 text-right"
            step="0.01"
          />
        </div>
      </td>
      <td className="py-2 px-2 text-right">
        {margin !== null ? (
          <span className={cn(
            'font-medium',
            margin >= 30 ? 'text-success' : margin >= 15 ? 'text-warning' : 'text-danger'
          )}>
            {margin.toFixed(1)}%
          </span>
        ) : '-'}
      </td>
      <td className="py-2 px-2">
        <Input
          type="number"
          value={item.leadTimeDays || ''}
          onChange={(e) => onChange({ ...item, leadTimeDays: parseInt(e.target.value) || undefined })}
          placeholder="Days"
          className="w-16 text-right"
        />
      </td>
      <td className="py-2 px-2">
        <Button variant="ghost" size="icon-sm" onClick={onRemove}>
          <Trash2 className="h-4 w-4 text-muted-foreground hover:text-danger" />
        </Button>
      </td>
    </tr>
  );
}

function NewQuotePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const rfqId = searchParams.get('rfq');
  
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSaving, setIsSaving] = React.useState(false);
  const [showSubmitDialog, setShowSubmitDialog] = React.useState(false);
  
  const [formData, setFormData] = React.useState<QuoteFormData>({
    rfqId: rfqId || undefined,
    validUntil: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    discountType: 'percentage',
    discountValue: 0,
    taxRate: 0,
    termsAndConditions: defaultTerms,
    notes: '',
    lineItems: [],
  });

  // Load RFQ data and initialize line items
  React.useEffect(() => {
    const timer = setTimeout(() => {
      if (rfqId) {
        // Pre-populate from RFQ line items
        setFormData((prev) => ({
          ...prev,
          lineItems: mockRFQLineItems.map((item) => ({
            id: generateId(),
            partNumber: item.partNumber,
            description: item.description,
            quantity: item.quantity,
            unitOfMeasure: item.unitOfMeasure,
            unitPrice: 0,
            cost: undefined,
            leadTimeDays: undefined,
            notes: undefined,
          })),
        }));
      }
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, [rfqId]);

  // Calculate totals
  const calculations = React.useMemo(() => {
    const subtotal = formData.lineItems.reduce(
      (sum, item) => sum + item.quantity * item.unitPrice,
      0
    );
    const discount = formData.discountType === 'percentage'
      ? subtotal * (formData.discountValue / 100)
      : formData.discountValue;
    const afterDiscount = subtotal - discount;
    const tax = afterDiscount * (formData.taxRate / 100);
    const total = afterDiscount + tax;
    const totalCost = formData.lineItems.reduce(
      (sum, item) => sum + item.quantity * (item.cost || 0),
      0
    );
    const margin = total > 0 ? ((total - totalCost) / total) * 100 : 0;

    return { subtotal, discount, afterDiscount, tax, total, totalCost, margin };
  }, [formData.lineItems, formData.discountType, formData.discountValue, formData.taxRate]);

  const handleAddLineItem = () => {
    setFormData((prev) => ({
      ...prev,
      lineItems: [
        ...prev.lineItems,
        {
          id: generateId(),
          partNumber: '',
          description: '',
          quantity: 1,
          unitOfMeasure: 'pcs',
          unitPrice: 0,
        },
      ],
    }));
  };

  const handleUpdateLineItem = (id: string, item: QuoteLineItem) => {
    setFormData((prev) => ({
      ...prev,
      lineItems: prev.lineItems.map((li) => (li.id === id ? item : li)),
    }));
  };

  const handleRemoveLineItem = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      lineItems: prev.lineItems.filter((li) => li.id !== id),
    }));
  };

  const handleSave = async (asDraft = true) => {
    setIsSaving(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      toast({
        title: asDraft ? 'Quote saved as draft' : 'Quote submitted for approval',
        description: 'Q-2024-0113',
      });
      router.push('/quotes');
    } catch {
      toast({
        variant: 'destructive',
        title: 'Error saving quote',
        description: 'Please try again.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <Skeleton className="h-8 w-48" />
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">New Quote</h1>
            {rfqId && (
              <p className="text-muted-foreground">
                For RFQ: <Link href={`/pipeline/${rfqId}`} className="text-primary hover:underline">RFQ-2024-0089</Link>
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => handleSave(true)} disabled={isSaving}>
            <Save className="mr-2 h-4 w-4" />
            Save Draft
          </Button>
          <Button onClick={() => setShowSubmitDialog(true)} disabled={isSaving}>
            <Send className="mr-2 h-4 w-4" />
            Submit for Approval
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Line Items */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Line Items</CardTitle>
                <CardDescription>Add products and pricing</CardDescription>
              </div>
              <Button size="sm" onClick={handleAddLineItem}>
                <Plus className="mr-2 h-4 w-4" />
                Add Item
              </Button>
            </CardHeader>
            <CardContent>
              {formData.lineItems.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed rounded-lg">
                  <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-medium">No line items</h3>
                  <p className="text-muted-foreground">Add items to your quote</p>
                  <Button className="mt-4" onClick={handleAddLineItem}>
                    <Plus className="mr-2 h-4 w-4" />
                    Add First Item
                  </Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="py-2 px-2 text-left font-medium">Part #</th>
                        <th className="py-2 px-2 text-left font-medium">Description</th>
                        <th className="py-2 px-2 text-right font-medium">Qty</th>
                        <th className="py-2 px-2 text-left font-medium">UoM</th>
                        <th className="py-2 px-2 text-right font-medium">Unit Price</th>
                        <th className="py-2 px-2 text-right font-medium">Extended</th>
                        <th className="py-2 px-2 text-right font-medium">Cost</th>
                        <th className="py-2 px-2 text-right font-medium">Margin</th>
                        <th className="py-2 px-2 text-right font-medium">Lead</th>
                        <th className="py-2 px-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {formData.lineItems.map((item) => (
                        <QuoteLineItemRow
                          key={item.id}
                          item={item}
                          onChange={(updated) => handleUpdateLineItem(item.id, updated)}
                          onRemove={() => handleRemoveLineItem(item.id)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Terms & Notes */}
          <Card>
            <CardHeader>
              <CardTitle>Terms & Notes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Terms and Conditions</Label>
                <Textarea
                  value={formData.termsAndConditions}
                  onChange={(e) => setFormData((prev) => ({ ...prev, termsAndConditions: e.target.value }))}
                  rows={6}
                  className="mt-1.5 font-mono text-sm"
                />
              </div>
              <div>
                <Label>Internal Notes</Label>
                <Textarea
                  value={formData.notes}
                  onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
                  placeholder="Notes for internal use only (not visible to customer)"
                  rows={3}
                  className="mt-1.5"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - Quote Summary */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calculator className="h-5 w-5" />
                Quote Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Valid Until</Label>
                <Input
                  type="date"
                  value={formData.validUntil}
                  onChange={(e) => setFormData((prev) => ({ ...prev, validUntil: e.target.value }))}
                  className="mt-1.5"
                />
              </div>

              <div className="border-t pt-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span className="font-medium">{formatCurrency(calculations.subtotal)}</span>
                </div>

                <div className="flex items-center gap-2">
                  <Label className="w-20">Discount</Label>
                  <Select 
                    value={formData.discountType} 
                    onValueChange={(v: 'percentage' | 'amount') => setFormData((prev) => ({ ...prev, discountType: v }))}
                  >
                    <SelectTrigger className="w-16">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="percentage">%</SelectItem>
                      <SelectItem value="amount">$</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input
                    type="number"
                    value={formData.discountValue || ''}
                    onChange={(e) => setFormData((prev) => ({ ...prev, discountValue: parseFloat(e.target.value) || 0 }))}
                    className="w-20 text-right"
                    step={formData.discountType === 'percentage' ? '0.1' : '0.01'}
                  />
                </div>
                {calculations.discount > 0 && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>Discount</span>
                    <span>-{formatCurrency(calculations.discount)}</span>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <Label className="w-20">Tax Rate</Label>
                  <div className="relative flex-1">
                    <Input
                      type="number"
                      value={formData.taxRate || ''}
                      onChange={(e) => setFormData((prev) => ({ ...prev, taxRate: parseFloat(e.target.value) || 0 }))}
                      className="pr-8 text-right"
                      step="0.1"
                    />
                    <Percent className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
                {calculations.tax > 0 && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>Tax</span>
                    <span>{formatCurrency(calculations.tax)}</span>
                  </div>
                )}

                <div className="flex justify-between border-t pt-3 text-lg font-bold">
                  <span>Total</span>
                  <span>{formatCurrency(calculations.total)}</span>
                </div>
              </div>

              <div className="border-t pt-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total Cost</span>
                  <span>{formatCurrency(calculations.totalCost)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Overall Margin</span>
                  <span className={cn(
                    'font-medium',
                    calculations.margin >= 30 ? 'text-success' : 
                    calculations.margin >= 15 ? 'text-warning' : 'text-danger'
                  )}>
                    {calculations.margin.toFixed(1)}%
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Validation */}
          {formData.lineItems.length > 0 && formData.lineItems.some((item) => item.unitPrice === 0) && (
            <Card className="border-warning">
              <CardContent className="py-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-warning">Incomplete pricing</p>
                    <p className="text-sm text-muted-foreground">
                      Some line items have $0.00 unit price
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Submit Dialog */}
      <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit Quote for Approval</DialogTitle>
            <DialogDescription>
              This quote will be sent to your manager for approval before it can be sent to the customer.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="bg-muted rounded-lg p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total</span>
                <span className="font-bold">{formatCurrency(calculations.total)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Margin</span>
                <span className={cn(
                  'font-medium',
                  calculations.margin >= 30 ? 'text-success' : 
                  calculations.margin >= 15 ? 'text-warning' : 'text-danger'
                )}>
                  {calculations.margin.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Valid Until</span>
                <span>{formatDate(new Date(formData.validUntil))}</span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSubmitDialog(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              setShowSubmitDialog(false);
              handleSave(false);
            }} disabled={isSaving}>
              Submit for Approval
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function NewQuotePage() {
  return (
    <Suspense fallback={
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <div className="h-8 w-8 bg-muted animate-pulse rounded" />
          <div className="h-6 w-48 bg-muted animate-pulse rounded" />
        </div>
        <div className="h-96 bg-muted animate-pulse rounded-lg" />
      </div>
    }>
      <NewQuotePageContent />
    </Suspense>
  );
}
