'use client';

import * as React from 'react';
import { Suspense, useState, useEffect, useCallback, useMemo } from 'react';
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
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Eye,
  Download,
  History,
  Info,
  Lightbulb,
  Shield,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { cn, formatCurrency, formatDate, generateId } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { useI18n } from '@/contexts/i18n-context';
import { useQuoteStore } from '@/stores/quote';

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
  materialCost?: number;
  laborCost?: number;
  overheadCost?: number;
}

interface QuoteAssumption {
  id: string;
  category: 'technical' | 'commercial' | 'delivery' | 'quality';
  description: string;
  impact: 'high' | 'medium' | 'low';
  verified: boolean;
}

interface PreReleaseCheck {
  id: string;
  category: 'pricing' | 'margin' | 'completeness' | 'compliance';
  description: string;
  status: 'pass' | 'warn' | 'fail';
  message: string;
}

interface QuoteFormData {
  rfqId?: string;
  quoteNumber?: string;
  version: number;
  validUntil: string;
  discountType: 'percentage' | 'amount';
  discountValue: number;
  taxRate: number;
  termsAndConditions: string;
  notes: string;
  internalNotes: string;
  lineItems: QuoteLineItem[];
  assumptions: QuoteAssumption[];
}

// Mock data
const defaultTerms = `1. Payment Terms: Net 30 days from invoice date
2. Validity: This quote is valid for 30 days from the date of issue
3. Delivery: FOB Destination, freight prepaid
4. Lead Time: As specified per line item
5. Warranty: Standard 12-month warranty on all parts
6. Changes: Any changes to this quote must be approved in writing`;

const defaultAssumptions: QuoteAssumption[] = [
  {
    id: '1',
    category: 'technical',
    description: 'Drawings provided are final and will not change',
    impact: 'high',
    verified: false,
  },
  {
    id: '2',
    category: 'delivery',
    description: 'Standard packaging is acceptable',
    impact: 'medium',
    verified: false,
  },
  {
    id: '3',
    category: 'quality',
    description: 'Standard inspection process applies',
    impact: 'medium',
    verified: false,
  },
];

// Line Item Row Component
function QuoteLineItemRow({ 
  item, 
  onChange, 
  onRemove,
  showDetailedCosting,
}: { 
  item: QuoteLineItem; 
  onChange: (item: QuoteLineItem) => void;
  onRemove: () => void;
  showDetailedCosting: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const extendedPrice = item.quantity * item.unitPrice;
  
  const totalCost = (item.cost || 0) + 
    (item.materialCost || 0) + 
    (item.laborCost || 0) + 
    (item.overheadCost || 0);
  
  const margin = item.unitPrice > 0 && totalCost > 0
    ? ((item.unitPrice * item.quantity - totalCost * item.quantity) / (item.unitPrice * item.quantity)) * 100
    : null;

  const marginColor = margin !== null
    ? margin >= 30 ? 'text-success' : margin >= 15 ? 'text-warning' : 'text-danger'
    : 'text-muted-foreground';

  return (
    <>
      <tr className="border-b hover:bg-muted/30" data-testid="quote-line-item">
        <td className="py-2 px-2">
          {showDetailedCosting && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
          )}
        </td>
        <td className="py-2 px-2">
          <Input
            value={item.partNumber}
            onChange={(e) => onChange({ ...item, partNumber: e.target.value })}
            placeholder="Part #"
            className="w-28"
            data-testid="part-number-input"
          />
        </td>
        <td className="py-2 px-2">
          <Input
            value={item.description}
            onChange={(e) => onChange({ ...item, description: e.target.value })}
            placeholder="Description"
            className="min-w-[200px]"
            data-testid="description-input"
          />
        </td>
        <td className="py-2 px-2">
          <Input
            type="number"
            value={item.quantity}
            onChange={(e) => onChange({ ...item, quantity: parseFloat(e.target.value) || 0 })}
            className="w-20 text-right"
            data-testid="quantity-input"
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
              data-testid="unit-price-input"
            />
          </div>
        </td>
        <td className="py-2 px-2 text-right font-medium" data-testid="extended-price">
          {formatCurrency(extendedPrice)}
        </td>
        {showDetailedCosting && (
          <>
            <td className="py-2 px-2 text-right">
              {formatCurrency(totalCost * item.quantity)}
            </td>
            <td className="py-2 px-2 text-right">
              <span className={cn('font-medium', marginColor)}>
                {margin !== null ? `${margin.toFixed(1)}%` : '-'}
              </span>
            </td>
          </>
        )}
        <td className="py-2 px-2">
          <Input
            type="number"
            value={item.leadTimeDays || ''}
            onChange={(e) => onChange({ ...item, leadTimeDays: parseInt(e.target.value) || undefined })}
            placeholder="Days"
            className="w-16 text-right"
            data-testid="lead-time-input"
          />
        </td>
        <td className="py-2 px-2">
          <Button variant="ghost" size="icon-sm" onClick={onRemove} data-testid="remove-line-item">
            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-danger" />
          </Button>
        </td>
      </tr>
      {isExpanded && showDetailedCosting && (
        <tr className="bg-muted/20">
          <td colSpan={11} className="py-4 px-8">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label className="text-xs">Material Cost</Label>
                <div className="relative mt-1">
                  <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
                  <Input
                    type="number"
                    value={item.materialCost || ''}
                    onChange={(e) => onChange({ ...item, materialCost: parseFloat(e.target.value) || undefined })}
                    className="pl-6 text-sm"
                    step="0.01"
                    placeholder="0.00"
                  />
                </div>
              </div>
              <div>
                <Label className="text-xs">Labor Cost</Label>
                <div className="relative mt-1">
                  <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
                  <Input
                    type="number"
                    value={item.laborCost || ''}
                    onChange={(e) => onChange({ ...item, laborCost: parseFloat(e.target.value) || undefined })}
                    className="pl-6 text-sm"
                    step="0.01"
                    placeholder="0.00"
                  />
                </div>
              </div>
              <div>
                <Label className="text-xs">Overhead Cost</Label>
                <div className="relative mt-1">
                  <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
                  <Input
                    type="number"
                    value={item.overheadCost || ''}
                    onChange={(e) => onChange({ ...item, overheadCost: parseFloat(e.target.value) || undefined })}
                    className="pl-6 text-sm"
                    step="0.01"
                    placeholder="0.00"
                  />
                </div>
              </div>
            </div>
            <div className="mt-3">
              <Label className="text-xs">Line Item Notes</Label>
              <Textarea
                value={item.notes || ''}
                onChange={(e) => onChange({ ...item, notes: e.target.value })}
                placeholder="Internal notes for this line item"
                rows={2}
                className="mt-1 text-sm"
              />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// Assumptions Panel Component
function AssumptionsPanel({
  assumptions,
  onChange,
}: {
  assumptions: QuoteAssumption[];
  onChange: (assumptions: QuoteAssumption[]) => void;
}) {
  const handleToggleVerified = (id: string) => {
    onChange(assumptions.map(a => a.id === id ? { ...a, verified: !a.verified } : a));
  };

  const handleAdd = () => {
    onChange([
      ...assumptions,
      {
        id: generateId(),
        category: 'technical',
        description: '',
        impact: 'medium',
        verified: false,
      },
    ]);
  };

  const handleRemove = (id: string) => {
    onChange(assumptions.filter(a => a.id !== id));
  };

  const handleUpdate = (id: string, updates: Partial<QuoteAssumption>) => {
    onChange(assumptions.map(a => a.id === id ? { ...a, ...updates } : a));
  };

  const categoryColors = {
    technical: 'bg-blue-100 text-blue-800',
    commercial: 'bg-purple-100 text-purple-800',
    delivery: 'bg-orange-100 text-orange-800',
    quality: 'bg-green-100 text-green-800',
  };

  const impactColors = {
    high: 'text-danger',
    medium: 'text-warning',
    low: 'text-muted-foreground',
  };

  return (
    <Card className="border-2 border-primary/20" data-testid="assumptions-panel">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-primary" />
            <CardTitle>Assumptions</CardTitle>
          </div>
          <Button size="sm" variant="outline" onClick={handleAdd}>
            <Plus className="mr-2 h-4 w-4" />
            Add
          </Button>
        </div>
        <CardDescription>
          Key assumptions that underpin this quote. All must be verified before submission.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {assumptions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>No assumptions defined</p>
            <p className="text-sm mt-1">Add assumptions to document quote basis</p>
          </div>
        ) : (
          assumptions.map((assumption) => (
            <div
              key={assumption.id}
              className={cn(
                'p-3 rounded-lg border-2',
                assumption.verified ? 'bg-success/5 border-success/20' : 'bg-muted/50 border-border'
              )}
              data-testid="assumption-item"
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 flex-1">
                  <Select
                    value={assumption.category}
                    onValueChange={(v: QuoteAssumption['category']) => handleUpdate(assumption.id, { category: v })}
                  >
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="technical">Technical</SelectItem>
                      <SelectItem value="commercial">Commercial</SelectItem>
                      <SelectItem value="delivery">Delivery</SelectItem>
                      <SelectItem value="quality">Quality</SelectItem>
                    </SelectContent>
                  </Select>
                  <Badge className={categoryColors[assumption.category]}>
                    {assumption.category}
                  </Badge>
                  <span className={cn('text-sm font-medium', impactColors[assumption.impact])}>
                    {assumption.impact.toUpperCase()} impact
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => handleToggleVerified(assumption.id)}
                    data-testid="verify-assumption"
                  >
                    {assumption.verified ? (
                      <CheckCircle className="h-4 w-4 text-success" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => handleRemove(assumption.id)}
                  >
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </div>
              </div>
              <Textarea
                value={assumption.description}
                onChange={(e) => handleUpdate(assumption.id, { description: e.target.value })}
                placeholder="Describe the assumption..."
                rows={2}
                className="text-sm"
                data-testid="assumption-description"
              />
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

// Pre-Release Checks Component
function PreReleaseChecks({ checks }: { checks: PreReleaseCheck[] }) {
  const statusIcons = {
    pass: <CheckCircle className="h-5 w-5 text-success" />,
    warn: <AlertCircle className="h-5 w-5 text-warning" />,
    fail: <XCircle className="h-5 w-5 text-danger" />,
  };

  const statusColors = {
    pass: 'border-success/20 bg-success/5',
    warn: 'border-warning/20 bg-warning/5',
    fail: 'border-danger/20 bg-danger/5',
  };

  const passCount = checks.filter(c => c.status === 'pass').length;
  const warnCount = checks.filter(c => c.status === 'warn').length;
  const failCount = checks.filter(c => c.status === 'fail').length;

  return (
    <Card className="border-2 border-primary/20" data-testid="pre-release-checks">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <CardTitle>Pre-Release Checks</CardTitle>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Badge variant="default" className="bg-success">
              {passCount} Pass
            </Badge>
            {warnCount > 0 && (
              <Badge variant="warning">{warnCount} Warn</Badge>
            )}
            {failCount > 0 && (
              <Badge variant="destructive">{failCount} Fail</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {checks.map((check) => (
          <div
            key={check.id}
            className={cn('p-3 rounded-lg border-2 flex items-start gap-3', statusColors[check.status])}
            data-testid="check-item"
          >
            {statusIcons[check.status]}
            <div className="flex-1">
              <p className="font-medium text-sm">{check.description}</p>
              <p className="text-xs text-muted-foreground mt-1">{check.message}</p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// Main Component
function NewQuotePageRefinedContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const { t } = useI18n();
  const { saveQuote, submitQuote, isLoading: isSaving } = useQuoteStore();
  
  const rfqId = searchParams.get('rfq');
  const [isLoading, setIsLoading] = useState(true);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [showDetailedCosting, setShowDetailedCosting] = useState(false);
  const [showInternalCosting, setShowInternalCosting] = useState(true);
  
  const [formData, setFormData] = useState<QuoteFormData>({
    rfqId: rfqId || undefined,
    version: 1,
    validUntil: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    discountType: 'percentage',
    discountValue: 0,
    taxRate: 0,
    termsAndConditions: defaultTerms,
    notes: '',
    internalNotes: '',
    lineItems: [],
    assumptions: [...defaultAssumptions],
  });

  // Load RFQ data
  useEffect(() => {
    const timer = setTimeout(() => {
      if (rfqId) {
        // Mock RFQ line items
        const mockLineItems = [
          { partNumber: 'AER-001', description: 'Precision bracket - Type A', quantity: 200, unitOfMeasure: 'pcs' },
          { partNumber: 'AER-002', description: 'Precision bracket - Type B', quantity: 200, unitOfMeasure: 'pcs' },
          { partNumber: 'AER-003', description: 'Mounting plate assembly', quantity: 100, unitOfMeasure: 'pcs' },
        ];
        
        setFormData((prev) => ({
          ...prev,
          quoteNumber: 'Q-2024-0113',
          lineItems: mockLineItems.map((item) => ({
            id: generateId(),
            partNumber: item.partNumber,
            description: item.description,
            quantity: item.quantity,
            unitOfMeasure: item.unitOfMeasure,
            unitPrice: 0,
          })),
        }));
      }
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, [rfqId]);

  // Calculate totals
  const calculations = useMemo(() => {
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
    
    const totalCost = formData.lineItems.reduce((sum, item) => {
      const itemCost = (item.cost || 0) + 
        (item.materialCost || 0) + 
        (item.laborCost || 0) + 
        (item.overheadCost || 0);
      return sum + item.quantity * itemCost;
    }, 0);
    
    const margin = total > 0 ? ((total - totalCost) / total) * 100 : 0;

    return { subtotal, discount, afterDiscount, tax, total, totalCost, margin };
  }, [formData.lineItems, formData.discountType, formData.discountValue, formData.taxRate]);

  // Pre-release checks
  const preReleaseChecks: PreReleaseCheck[] = useMemo(() => {
    const checks: PreReleaseCheck[] = [];

    // Pricing completeness
    const incompleteItems = formData.lineItems.filter(item => item.unitPrice === 0).length;
    checks.push({
      id: 'pricing-complete',
      category: 'completeness',
      description: 'All line items have pricing',
      status: incompleteItems === 0 ? 'pass' : 'fail',
      message: incompleteItems > 0 ? `${incompleteItems} items missing pricing` : 'All items priced',
    });

    // Margin check
    const marginFloor = 15;
    checks.push({
      id: 'margin-check',
      category: 'margin',
      description: `Margin meets minimum threshold (${marginFloor}%)`,
      status: calculations.margin >= marginFloor ? 'pass' : calculations.margin >= 10 ? 'warn' : 'fail',
      message: `Current margin: ${calculations.margin.toFixed(1)}%`,
    });

    // Assumptions verified
    const unverifiedAssumptions = formData.assumptions.filter(a => !a.verified).length;
    checks.push({
      id: 'assumptions-verified',
      category: 'completeness',
      description: 'All assumptions verified',
      status: unverifiedAssumptions === 0 ? 'pass' : 'warn',
      message: unverifiedAssumptions > 0 ? `${unverifiedAssumptions} assumptions not verified` : 'All verified',
    });

    // Terms defined
    checks.push({
      id: 'terms-defined',
      category: 'compliance',
      description: 'Terms and conditions defined',
      status: formData.termsAndConditions.length > 0 ? 'pass' : 'fail',
      message: formData.termsAndConditions.length > 0 ? 'Terms defined' : 'Terms missing',
    });

    // Lead times specified
    const missingLeadTimes = formData.lineItems.filter(item => !item.leadTimeDays).length;
    checks.push({
      id: 'lead-times',
      category: 'completeness',
      description: 'Lead times specified for all items',
      status: missingLeadTimes === 0 ? 'pass' : 'warn',
      message: missingLeadTimes > 0 ? `${missingLeadTimes} items missing lead times` : 'All lead times specified',
    });

    return checks;
  }, [formData, calculations.margin]);

  const canSubmit = preReleaseChecks.filter(c => c.status === 'fail').length === 0;

  // Handlers
  const handleAddLineItem = useCallback(() => {
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
  }, []);

  const handleUpdateLineItem = useCallback((id: string, item: QuoteLineItem) => {
    setFormData((prev) => ({
      ...prev,
      lineItems: prev.lineItems.map((li) => (li.id === id ? item : li)),
    }));
  }, []);

  const handleRemoveLineItem = useCallback((id: string) => {
    setFormData((prev) => ({
      ...prev,
      lineItems: prev.lineItems.filter((li) => li.id !== id),
    }));
  }, []);

  const handleSave = async (asDraft = true) => {
    try {
      if (asDraft) {
        await saveQuote(formData);
        toast({
          title: t('pages.quotes.toast.savedDraft'),
          description: formData.quoteNumber || 'Draft saved successfully',
        });
      } else {
        await submitQuote(formData);
        toast({
          title: t('pages.quotes.toast.submitted'),
          description: formData.quoteNumber || 'Quote submitted successfully',
        });
        router.push('/quotes');
      }
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('pages.quotes.toast.saveFailed'),
        description: t('pages.quotes.toast.tryAgain'),
      });
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
    <div className="space-y-6" data-testid="quote-builder-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-heading font-bold tracking-tight ">{t('pages.quotes.new.newQuote')}</h1>
              {formData.quoteNumber && (
                <Badge variant="outline" className="text-sm">
                  {formData.quoteNumber} v{formData.version}
                </Badge>
              )}
            </div>
            {rfqId && (
              <p className="text-muted-foreground">
                For RFQ: <Link href={`/pipeline/${rfqId}`} className="text-primary hover:underline">RFQ-2024-0089</Link>
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon">
                  <History className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>View Version History</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <Button variant="outline" onClick={() => handleSave(true)} disabled={isSaving} data-testid="save-draft-button">
            <Save className="mr-2 h-4 w-4" />
            Save Draft
          </Button>
          <Button 
            onClick={() => setShowSubmitDialog(true)} 
            disabled={isSaving || !canSubmit}
            data-testid="submit-button"
          >
            <Send className="mr-2 h-4 w-4" />
            Submit for Approval
          </Button>
        </div>
      </div>

      {/* Assumptions Panel - Always Visible */}
      <AssumptionsPanel
        assumptions={formData.assumptions}
        onChange={(assumptions) => setFormData(prev => ({ ...prev, assumptions }))}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Line Items */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>{t('pages.quotes.new.lineItems')}</CardTitle>
                <CardDescription>Add products and pricing</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowDetailedCosting(!showDetailedCosting)}
                      >
                        <Calculator className="mr-2 h-4 w-4" />
                        {showDetailedCosting ? 'Simple' : 'Detailed'} View
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Toggle detailed cost breakdown</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <Button size="sm" onClick={handleAddLineItem} data-testid="add-line-item">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Item
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {formData.lineItems.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed rounded-lg">
                  <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-medium">{t('pages.quotes.new.noLineItems')}</h3>
                  <p className="text-muted-foreground">{t('pages.quotes.new.addItemsToQuote')}</p>
                  <Button className="mt-4" onClick={handleAddLineItem}>
                    <Plus className="mr-2 h-4 w-4" />
                    Add First Item
                  </Button>
                </div>
              ) : (
                <div className="overflow-x-auto" data-testid="line-items-table">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="py-2 px-2 w-8"></th>
                        <th className="py-2 px-2 text-left font-medium">Part #</th>
                        <th className="py-2 px-2 text-left font-medium">Description</th>
                        <th className="py-2 px-2 text-right font-medium">Qty</th>
                        <th className="py-2 px-2 text-left font-medium">UoM</th>
                        <th className="py-2 px-2 text-right font-medium">{t('pages.quotes.new.unitPrice')}</th>
                        <th className="py-2 px-2 text-right font-medium">Extended</th>
                        {showDetailedCosting && (
                          <>
                            <th className="py-2 px-2 text-right font-medium">{t('pages.quotes.new.totalCost')}</th>
                            <th className="py-2 px-2 text-right font-medium">Margin</th>
                          </>
                        )}
                        <th className="py-2 px-2 text-right font-medium">Lead</th>
                        <th className="py-2 px-2 w-8"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {formData.lineItems.map((item) => (
                        <QuoteLineItemRow
                          key={item.id}
                          item={item}
                          onChange={(updated) => handleUpdateLineItem(item.id, updated)}
                          onRemove={() => handleRemoveLineItem(item.id)}
                          showDetailedCosting={showDetailedCosting}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Internal Costing - Collapsible */}
          <Collapsible open={showInternalCosting} onOpenChange={setShowInternalCosting}>
            <Card>
              <CardHeader>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" className="w-full justify-between p-0 hover:bg-transparent">
                    <CardTitle>{t('pages.quotes.new.internalCostingAnalysis')}</CardTitle>
                    {showInternalCosting ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </Button>
                </CollapsibleTrigger>
              </CardHeader>
              <CollapsibleContent>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-muted/50 rounded-lg">
                      <p className="text-sm text-muted-foreground">{t('pages.quotes.new.totalRevenue')}</p>
                      <p className="text-3xl font-heading font-bold tracking-tight ">{formatCurrency(calculations.total)}</p>
                    </div>
                    <div className="p-4 bg-muted/50 rounded-lg">
                      <p className="text-sm text-muted-foreground">{t('pages.quotes.new.totalCost')}</p>
                      <p className="text-3xl font-heading font-bold tracking-tight ">{formatCurrency(calculations.totalCost)}</p>
                    </div>
                    <div className="p-4 bg-muted/50 rounded-lg">
                      <p className="text-sm text-muted-foreground">{t('pages.quotes.new.grossProfit')}</p>
                      <p className="text-3xl font-heading font-bold tracking-tight ">{formatCurrency(calculations.total - calculations.totalCost)}</p>
                    </div>
                    <div className="p-4 bg-muted/50 rounded-lg">
                      <p className="text-sm text-muted-foreground">Margin %</p>
                      <p className={cn(
                        'text-3xl font-heading font-bold tracking-tight ',
                        calculations.margin >= 30 ? 'text-success' : 
                        calculations.margin >= 15 ? 'text-warning' : 'text-danger'
                      )}>
                        {calculations.margin.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                  <Separator />
                  <div className="text-sm space-y-1">
                    <p className="text-muted-foreground">
                      <Info className="inline h-3 w-3 mr-1" />
                      Internal costing information is not visible to customers
                    </p>
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>

          {/* Terms & Notes */}
          <Card>
            <CardHeader>
              <CardTitle>Terms & Notes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Terms and Conditions (Customer-Visible)</Label>
                <Textarea
                  value={formData.termsAndConditions}
                  onChange={(e) => setFormData((prev) => ({ ...prev, termsAndConditions: e.target.value }))}
                  rows={6}
                  className="mt-1.5 font-mono text-sm"
                  data-testid="terms-input"
                />
              </div>
              <div>
                <Label>Internal Notes (Private)</Label>
                <Textarea
                  value={formData.internalNotes}
                  onChange={(e) => setFormData((prev) => ({ ...prev, internalNotes: e.target.value }))}
                  placeholder="Notes for internal use only (not visible to customer)"
                  rows={3}
                  className="mt-1.5"
                  data-testid="internal-notes-input"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quote Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calculator className="h-5 w-5" />
                Quote Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>{t('pages.quotes.new.validUntil')}</Label>
                <Input
                  type="date"
                  value={formData.validUntil}
                  onChange={(e) => setFormData((prev) => ({ ...prev, validUntil: e.target.value }))}
                  className="mt-1.5"
                  data-testid="valid-until-input"
                />
              </div>

              <Separator />

              <div className="space-y-3">
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
                    data-testid="discount-input"
                  />
                </div>
                {calculations.discount > 0 && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>Discount</span>
                    <span>-{formatCurrency(calculations.discount)}</span>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <Label className="w-20">{t('pages.quotes.new.taxRate')}</Label>
                  <div className="relative flex-1">
                    <Input
                      type="number"
                      value={formData.taxRate || ''}
                      onChange={(e) => setFormData((prev) => ({ ...prev, taxRate: parseFloat(e.target.value) || 0 }))}
                      className="pr-8 text-right"
                      step="0.1"
                      data-testid="tax-rate-input"
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
                  <span data-testid="total-price">{formatCurrency(calculations.total)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Pre-Release Checks */}
          <PreReleaseChecks checks={preReleaseChecks} />

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">{t('pages.quotes.new.quickActions')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start" size="sm">
                <Eye className="mr-2 h-4 w-4" />
                Preview PDF
              </Button>
              <Button variant="outline" className="w-full justify-start" size="sm">
                <Copy className="mr-2 h-4 w-4" />
                Duplicate Quote
              </Button>
              <Button variant="outline" className="w-full justify-start" size="sm">
                <Download className="mr-2 h-4 w-4" />
                Export to Excel
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Submit Dialog */}
      <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('pages.quotes.new.submitForApproval')}</DialogTitle>
            <DialogDescription>
              This quote will be sent to your manager for approval before it can be sent to the customer.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
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
              <div className="flex justify-between">
                <span className="text-muted-foreground">Assumptions Verified</span>
                <span>
                  {formData.assumptions.filter(a => a.verified).length} / {formData.assumptions.length}
                </span>
              </div>
            </div>
            {preReleaseChecks.some(c => c.status === 'warn') && (
              <div className="bg-warning/10 border border-warning/20 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-warning">Warnings Present</p>
                    <p className="text-sm text-muted-foreground">
                      Some checks have warnings. Review before submitting.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSubmitDialog(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              setShowSubmitDialog(false);
              handleSave(false);
            }} disabled={isSaving} data-testid="confirm-submit">
              Submit for Approval
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function NewQuotePageRefined() {
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
      <NewQuotePageRefinedContent />
    </Suspense>
  );
}
