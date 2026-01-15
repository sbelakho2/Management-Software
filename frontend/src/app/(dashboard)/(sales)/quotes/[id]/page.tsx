'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  Edit,
  Copy,
  MoreHorizontal,
  FileText,
  Send,
  CheckCircle,
  XCircle,
  Clock,
  Download,
  History,
  MessageSquare,
  Paperclip,
  Building2,
  Mail,
  Phone,
  User,
  Calendar,
  DollarSign,
  TrendingUp,
  Printer,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { cn, formatCurrency, formatDate, formatDateTime, getInitials } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface QuoteLineItem {
  id: string;
  partNumber: string;
  description: string;
  quantity: number;
  unitOfMeasure: string;
  unitPrice: number;
  extendedPrice: number;
  leadTimeDays: number;
}

interface QuoteVersion {
  version: number;
  createdAt: string;
  createdBy: string;
  changes: string;
}

interface Quote {
  id: string;
  quoteNumber: string;
  rfqId: string;
  rfqNumber: string;
  status: 'draft' | 'pending_approval' | 'approved' | 'sent' | 'accepted' | 'rejected' | 'expired';
  version: number;
  customer: {
    id: string;
    name: string;
    contact: {
      name: string;
      email: string;
      phone: string;
    };
  };
  lineItems: QuoteLineItem[];
  subtotal: number;
  discount: number;
  tax: number;
  total: number;
  margin: number;
  validUntil: string;
  termsAndConditions: string;
  notes: string;
  createdAt: string;
  createdBy: {
    name: string;
    avatar?: string;
  };
  approvedBy?: {
    name: string;
    approvedAt: string;
  };
  sentAt?: string;
  versions: QuoteVersion[];
}

const mockQuote: Quote = {
  id: '1',
  quoteNumber: 'Q-2024-0112',
  rfqId: 'rfq-1',
  rfqNumber: 'RFQ-2024-0089',
  status: 'sent',
  version: 2,
  customer: {
    id: 'cust-1',
    name: 'Aerospace Dynamics Inc.',
    contact: {
      name: 'Michael Roberts',
      email: 'mroberts@aerospacedynamics.com',
      phone: '+1 (555) 234-5678',
    },
  },
  lineItems: [
    { id: '1', partNumber: 'AER-001', description: 'Precision bracket - Type A', quantity: 200, unitOfMeasure: 'pcs', unitPrice: 245.00, extendedPrice: 49000, leadTimeDays: 21 },
    { id: '2', partNumber: 'AER-002', description: 'Precision bracket - Type B', quantity: 200, unitOfMeasure: 'pcs', unitPrice: 285.00, extendedPrice: 57000, leadTimeDays: 21 },
    { id: '3', partNumber: 'AER-003', description: 'Mounting plate assembly', quantity: 100, unitOfMeasure: 'pcs', unitPrice: 185.00, extendedPrice: 18500, leadTimeDays: 14 },
  ],
  subtotal: 124500,
  discount: 0,
  tax: 0,
  total: 124500,
  margin: 28.5,
  validUntil: '2024-02-15',
  termsAndConditions: `1. Payment Terms: Net 30 days from invoice date
2. Validity: This quote is valid for 30 days from the date of issue
3. Delivery: FOB Destination, freight prepaid
4. Lead Time: As specified per line item
5. Warranty: Standard 12-month warranty on all parts`,
  notes: 'Customer requested expedited shipping if possible.',
  createdAt: '2024-01-10T09:30:00Z',
  createdBy: { name: 'Sarah Chen' },
  approvedBy: {
    name: 'David Wilson',
    approvedAt: '2024-01-11T14:20:00Z',
  },
  sentAt: '2024-01-12T10:00:00Z',
  versions: [
    { version: 1, createdAt: '2024-01-10T09:30:00Z', createdBy: 'Sarah Chen', changes: 'Initial version' },
    { version: 2, createdAt: '2024-01-11T11:45:00Z', createdBy: 'Sarah Chen', changes: 'Updated pricing per customer feedback' },
  ],
};

const statusConfig: Record<Quote['status'], { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'danger' | 'outline'; icon: typeof Clock }> = {
  draft: { label: 'Draft', variant: 'secondary', icon: FileText },
  pending_approval: { label: 'Pending Approval', variant: 'warning', icon: Clock },
  approved: { label: 'Approved', variant: 'default', icon: CheckCircle },
  sent: { label: 'Sent', variant: 'default', icon: Send },
  accepted: { label: 'Accepted', variant: 'success', icon: CheckCircle },
  rejected: { label: 'Rejected', variant: 'danger', icon: XCircle },
  expired: { label: 'Expired', variant: 'outline', icon: Calendar },
};

function QuoteDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10" />
        <Skeleton className="h-8 w-48" />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Skeleton className="h-64" />
          <Skeleton className="h-48" />
        </div>
        <div className="space-y-6">
          <Skeleton className="h-48" />
          <Skeleton className="h-32" />
        </div>
      </div>
    </div>
  );
}

export default function QuoteDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = React.useState(true);
  const [quote, setQuote] = React.useState<Quote | null>(null);
  const [showActionDialog, setShowActionDialog] = React.useState<'approve' | 'reject' | 'won' | 'lost' | null>(null);
  const [actionReason, setActionReason] = React.useState('');
  const [isEditing, setIsEditing] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setQuote(mockQuote);
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, [params.id]);

  const handleAction = async (action: string) => {
    toast({
      title: `Quote ${action}`,
      description: `Quote ${mockQuote.quoteNumber} has been ${action}`,
    });
    setShowActionDialog(null);
    setActionReason('');
  };

  if (isLoading) {
    return <QuoteDetailSkeleton />;
  }

  if (!quote) {
    return (
      <div className="text-center py-12">
        <h2 className="text-lg font-medium">Quote not found</h2>
        <Button className="mt-4" onClick={() => router.push('/quotes')}>
          Back to Quotes
        </Button>
      </div>
    );
  }

  const config = statusConfig[quote.status];
  const StatusIcon = config.icon;
  const isExpiringSoon = new Date(quote.validUntil) <= new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{quote.quoteNumber}</h1>
              <Badge variant={config.variant} className="gap-1">
                <StatusIcon className="h-3 w-3" />
                {config.label}
              </Badge>
              <Badge variant="outline">v{quote.version}</Badge>
            </div>
            <p className="text-muted-foreground">
              For RFQ:{' '}
              <Link href={`/pipeline/${quote.rfqId}`} className="text-primary hover:underline">
                {quote.rfqNumber}
              </Link>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {quote.status === 'draft' && (
            <Button variant="outline" onClick={() => setIsEditing(true)}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Button>
          )}
          <Button variant="outline">
            <Printer className="mr-2 h-4 w-4" />
            Print
          </Button>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export PDF
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Copy className="mr-2 h-4 w-4" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem>
                <History className="mr-2 h-4 w-4" />
                View History
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {quote.status === 'draft' && (
                <DropdownMenuItem onClick={() => setShowActionDialog('approve')}>
                  <Send className="mr-2 h-4 w-4" />
                  Submit for Approval
                </DropdownMenuItem>
              )}
              {quote.status === 'pending_approval' && (
                <>
                  <DropdownMenuItem onClick={() => setShowActionDialog('approve')} className="text-success">
                    <CheckCircle className="mr-2 h-4 w-4" />
                    Approve
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setShowActionDialog('reject')} className="text-danger">
                    <XCircle className="mr-2 h-4 w-4" />
                    Reject
                  </DropdownMenuItem>
                </>
              )}
              {quote.status === 'approved' && (
                <DropdownMenuItem>
                  <Send className="mr-2 h-4 w-4" />
                  Send to Customer
                </DropdownMenuItem>
              )}
              {quote.status === 'sent' && (
                <>
                  <DropdownMenuItem onClick={() => setShowActionDialog('won')} className="text-success">
                    <CheckCircle className="mr-2 h-4 w-4" />
                    Mark Won
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setShowActionDialog('lost')} className="text-danger">
                    <XCircle className="mr-2 h-4 w-4" />
                    Mark Lost
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Summary */}
          <div className="grid gap-4 sm:grid-cols-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Total</span>
                </div>
                <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{formatCurrency(quote.total)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Margin</span>
                </div>
                <p className={cn(
                  'text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1',
                  quote.margin >= 30 ? 'text-success' : quote.margin >= 20 ? 'text-warning' : 'text-danger'
                )}>
                  {quote.margin.toFixed(1)}%
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Valid Until</span>
                </div>
                <p className={cn('text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1', isExpiringSoon && 'from-warning to-warning/70')}>
                  {formatDate(new Date(quote.validUntil), { month: 'short', day: 'numeric' })}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Line Items</span>
                </div>
                <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{quote.lineItems.length}</p>
              </CardContent>
            </Card>
          </div>

          {/* Line Items */}
          <Card>
            <CardHeader>
              <CardTitle>Line Items</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="py-3 px-4 text-left font-medium">Part #</th>
                      <th className="py-3 px-4 text-left font-medium">Description</th>
                      <th className="py-3 px-4 text-right font-medium">Qty</th>
                      <th className="py-3 px-4 text-left font-medium">UoM</th>
                      <th className="py-3 px-4 text-right font-medium">Unit Price</th>
                      <th className="py-3 px-4 text-right font-medium">Extended</th>
                      <th className="py-3 px-4 text-right font-medium">Lead Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {quote.lineItems.map((item) => (
                      <tr key={item.id} className="border-b">
                        <td className="py-3 px-4 font-mono text-sm">{item.partNumber}</td>
                        <td className="py-3 px-4">{item.description}</td>
                        <td className="py-3 px-4 text-right">{item.quantity}</td>
                        <td className="py-3 px-4">{item.unitOfMeasure}</td>
                        <td className="py-3 px-4 text-right">{formatCurrency(item.unitPrice)}</td>
                        <td className="py-3 px-4 text-right font-medium">{formatCurrency(item.extendedPrice)}</td>
                        <td className="py-3 px-4 text-right">{item.leadTimeDays} days</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t bg-muted/30">
                      <td colSpan={5} className="py-3 px-4 text-right font-medium">Subtotal</td>
                      <td className="py-3 px-4 text-right font-medium">{formatCurrency(quote.subtotal)}</td>
                      <td></td>
                    </tr>
                    {quote.discount > 0 && (
                      <tr>
                        <td colSpan={5} className="py-2 px-4 text-right text-muted-foreground">Discount</td>
                        <td className="py-2 px-4 text-right text-muted-foreground">-{formatCurrency(quote.discount)}</td>
                        <td></td>
                      </tr>
                    )}
                    {quote.tax > 0 && (
                      <tr>
                        <td colSpan={5} className="py-2 px-4 text-right text-muted-foreground">Tax</td>
                        <td className="py-2 px-4 text-right text-muted-foreground">{formatCurrency(quote.tax)}</td>
                        <td></td>
                      </tr>
                    )}
                    <tr className="border-t-2 font-bold">
                      <td colSpan={5} className="py-3 px-4 text-right">Total</td>
                      <td className="py-3 px-4 text-right">{formatCurrency(quote.total)}</td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Terms */}
          <Card>
            <CardHeader>
              <CardTitle>Terms & Conditions</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap font-sans text-sm">{quote.termsAndConditions}</pre>
            </CardContent>
          </Card>

          {/* Internal Notes */}
          {quote.notes && (
            <Card className="border-warning/50 bg-warning/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Internal Notes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{quote.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Customer */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                Customer
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Link href={`/customers/${quote.customer.id}`} className="font-medium hover:underline">
                  {quote.customer.name}
                </Link>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span>{quote.customer.contact.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <a href={`mailto:${quote.customer.contact.email}`} className="text-primary hover:underline">
                    {quote.customer.contact.email}
                  </a>
                </div>
                <div className="flex items-center gap-2">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <span>{quote.customer.contact.phone}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Approval Info */}
          {quote.approvedBy && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-success" />
                  Approval
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <Avatar size="sm">
                    <AvatarFallback>{getInitials(quote.approvedBy.name)}</AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="font-medium">{quote.approvedBy.name}</p>
                    <p className="text-muted-foreground">{formatDateTime(quote.approvedBy.approvedAt)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Version History */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-4 w-4" />
                Version History
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {quote.versions.map((version) => (
                  <div key={version.version} className="flex items-start gap-3">
                    <div className={cn(
                      'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium',
                      version.version === quote.version 
                        ? 'bg-primary text-primary-foreground' 
                        : 'bg-muted'
                    )}>
                      {version.version}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{version.changes}</p>
                      <p className="text-xs text-muted-foreground">
                        {version.createdBy} • {formatDateTime(version.createdAt)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Meta */}
          <Card>
            <CardContent className="pt-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span>{formatDateTime(quote.createdAt)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created By</span>
                <div className="flex items-center gap-2">
                  <Avatar size="xs">
                    <AvatarImage src={quote.createdBy.avatar} />
                    <AvatarFallback>{getInitials(quote.createdBy.name)}</AvatarFallback>
                  </Avatar>
                  <span>{quote.createdBy.name}</span>
                </div>
              </div>
              {quote.sentAt && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Sent</span>
                  <span>{formatDateTime(quote.sentAt)}</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Action Dialogs */}
      <Dialog open={showActionDialog !== null} onOpenChange={() => setShowActionDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {showActionDialog === 'approve' && 'Submit for Approval'}
              {showActionDialog === 'reject' && 'Reject Quote'}
              {showActionDialog === 'won' && 'Mark Quote as Won'}
              {showActionDialog === 'lost' && 'Mark Quote as Lost'}
            </DialogTitle>
            <DialogDescription>
              {showActionDialog === 'approve' && 'This quote will be sent to your manager for approval.'}
              {showActionDialog === 'reject' && 'Provide a reason for rejecting this quote.'}
              {showActionDialog === 'won' && 'Congratulations! Mark this quote as won to close it.'}
              {showActionDialog === 'lost' && 'Provide a reason for losing this quote.'}
            </DialogDescription>
          </DialogHeader>
          {(showActionDialog === 'reject' || showActionDialog === 'lost') && (
            <div className="py-4">
              <Textarea
                placeholder="Reason..."
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                rows={3}
              />
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowActionDialog(null)}>
              Cancel
            </Button>
            <Button
              variant={showActionDialog === 'reject' || showActionDialog === 'lost' ? 'destructive' : 'default'}
              onClick={() => handleAction(showActionDialog || '')}
            >
              {showActionDialog === 'approve' && 'Submit'}
              {showActionDialog === 'reject' && 'Reject'}
              {showActionDialog === 'won' && 'Mark Won'}
              {showActionDialog === 'lost' && 'Mark Lost'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
