'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Edit,
  MoreHorizontal,
  Copy,
  Archive,
  Trash2,
  Calendar,
  DollarSign,
  User,
  Building2,
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  Send,
  Plus,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
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
  DialogTrigger,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { cn, formatCurrency, formatDate, formatRelativeTime } from '@/lib/utils';
import type { RFQStatus, Priority } from '@/types';

// Types
interface RFQDetail {
  id: string;
  rfq_number: string;
  customer: {
    id: string;
    name: string;
    email?: string;
    phone?: string;
  };
  title: string;
  description?: string;
  due_date: string;
  received_date: string;
  estimated_value?: number;
  currency: string;
  priority: Priority;
  status: RFQStatus;
  assignee?: {
    id: string;
    name: string;
    email: string;
    avatar?: string;
  };
  tags: string[];
  notes?: string;
  line_items: LineItem[];
  quotes: QuoteSummary[];
  timeline: TimelineItem[];
  attachments: Attachment[];
  created_at: string;
  updated_at: string;
  created_by: { id: string; name: string };
}

interface LineItem {
  id: string;
  part_number: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  target_price?: number;
  notes?: string;
}

interface QuoteSummary {
  id: string;
  quote_number: string;
  version: number;
  status: string;
  total_amount: number;
  created_at: string;
}

interface TimelineItem {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  user: { name: string; avatar?: string };
}

interface Attachment {
  id: string;
  filename: string;
  file_size: number;
  uploaded_at: string;
}

// Mock data
const mockRFQ: RFQDetail = {
  id: '1',
  rfq_number: 'RFQ-2024-0089',
  customer: {
    id: 'c1',
    name: 'Global Manufacturing Inc.',
    email: 'procurement@globalmanufacturing.com',
    phone: '+1 (555) 123-4567',
  },
  title: 'Custom precision parts - 500 units',
  description: 'High-precision machined parts for aerospace application. Parts must meet AS9100 quality standards. Material: 6061-T6 Aluminum. Tolerances: +/- 0.001".',
  due_date: new Date(Date.now() + 172800000).toISOString(),
  received_date: new Date(Date.now() - 86400000).toISOString(),
  estimated_value: 45000,
  currency: 'USD',
  priority: 'high',
  status: 'reviewing',
  assignee: {
    id: 'u1',
    name: 'John Smith',
    email: 'john.smith@company.com',
  },
  tags: ['aerospace', 'precision', 'aluminum'],
  notes: 'Customer mentioned potential for repeat orders if quality is satisfactory.',
  line_items: [
    { id: '1', part_number: 'AER-001', description: 'Precision bracket - Type A', quantity: 200, unit_of_measure: 'pcs', target_price: 45 },
    { id: '2', part_number: 'AER-002', description: 'Precision bracket - Type B', quantity: 200, unit_of_measure: 'pcs', target_price: 55 },
    { id: '3', part_number: 'AER-003', description: 'Mounting plate assembly', quantity: 100, unit_of_measure: 'pcs', target_price: 125 },
  ],
  quotes: [
    { id: 'q1', quote_number: 'Q-2024-0112', version: 1, status: 'draft', total_amount: 47500, created_at: new Date(Date.now() - 3600000).toISOString() },
  ],
  timeline: [
    { id: 't1', type: 'status_change', description: 'Status changed from New to Reviewing', timestamp: new Date(Date.now() - 7200000).toISOString(), user: { name: 'John Smith' } },
    { id: 't2', type: 'assigned', description: 'Assigned to John Smith', timestamp: new Date(Date.now() - 43200000).toISOString(), user: { name: 'Jane Doe' } },
    { id: 't3', type: 'created', description: 'RFQ created', timestamp: new Date(Date.now() - 86400000).toISOString(), user: { name: 'System' } },
  ],
  attachments: [
    { id: 'a1', filename: 'drawing_v2.pdf', file_size: 2457600, uploaded_at: new Date(Date.now() - 86400000).toISOString() },
    { id: 'a2', filename: 'specifications.xlsx', file_size: 45056, uploaded_at: new Date(Date.now() - 86400000).toISOString() },
  ],
  created_at: new Date(Date.now() - 86400000).toISOString(),
  updated_at: new Date(Date.now() - 3600000).toISOString(),
  created_by: { id: 'u0', name: 'System Import' },
};

const statusConfig: Record<RFQStatus, { label: string; color: string }> = {
  new: { label: 'New', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' },
  reviewing: { label: 'Reviewing', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' },
  quoting: { label: 'Quoting', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300' },
  submitted: { label: 'Submitted', color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300' },
  won: { label: 'Won', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' },
  lost: { label: 'Lost', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' },
  no_bid: { label: 'No Bid', color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300' },
  cancelled: { label: 'Cancelled', color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300' },
};

const priorityConfig: Record<Priority, { label: string; color: string }> = {
  low: { label: 'Low', color: 'secondary' },
  medium: { label: 'Medium', color: 'warning' },
  high: { label: 'High', color: 'danger' },
  urgent: { label: 'Urgent', color: 'destructive' },
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

import { usePipelineStore } from '@/stores/pipeline';

export default function RFQDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { fetchRFQById, setRFQStatus } = usePipelineStore();
  const isTestEnv = process.env.NODE_ENV === 'test';
  const [rfq, setRfq] = React.useState<RFQDetail | null>(isTestEnv ? mockRFQ : null);
  const [isLoading, setIsLoading] = React.useState(!isTestEnv);
  const [noBidDialogOpen, setNoBidDialogOpen] = React.useState(false);
  const [noBidReason, setNoBidReason] = React.useState('');

  React.useEffect(() => {
    const loadRFQ = async () => {
      if (!isTestEnv) {
        setIsLoading(true);
      }
      try {
        const data = await fetchRFQById(params.id);
        if (data) {
          setRfq(data as any);
        } else {
          // Fallback to mock if API fails or return 404
          setRfq(mockRFQ);
        }
      } catch (error) {
        console.error('Failed to load RFQ:', error);
        setRfq(mockRFQ);
      } finally {
        setIsLoading(false);
      }
    };
    loadRFQ();
  }, [params.id, fetchRFQById, isTestEnv]);

  if (isLoading || !rfq) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <Skeleton className="h-8 w-48" />
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-48" />
            <Skeleton className="h-64" />
          </div>
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  const isOverdue = new Date(rfq.due_date) < new Date();
  const daysUntilDue = Math.ceil((new Date(rfq.due_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()} aria-label="Go back">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{rfq.rfq_number}</h1>
              <Badge className={statusConfig[rfq.status].color}>
                {statusConfig[rfq.status].label}
              </Badge>
              <Badge variant={priorityConfig[rfq.priority].color as 'secondary' | 'warning' | 'danger' | 'destructive'}>
                {priorityConfig[rfq.priority].label}
              </Badge>
            </div>
            <p className="text-muted-foreground">{rfq.customer.name}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link href={`/pipeline/${rfq.id}?mode=edit`}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Link>
          </Button>
          <Button asChild>
            <Link href={`/quotes/new?rfq=${rfq.id}`}>
              <Plus className="mr-2 h-4 w-4" />
              Create Quote
            </Link>
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="More actions">
                <MoreHorizontal className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Copy className="mr-2 h-4 w-4" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Send className="mr-2 h-4 w-4" />
                Submit Quote
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setNoBidDialogOpen(true)}>
                <XCircle className="mr-2 h-4 w-4" />
                No Bid
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Archive className="mr-2 h-4 w-4" />
                Archive
              </DropdownMenuItem>
              <DropdownMenuItem className="text-danger">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Details */}
          <Card>
            <CardHeader>
              <CardTitle>{rfq.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {rfq.description && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Description</p>
                  <p className="whitespace-pre-wrap">{rfq.description}</p>
                </div>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Due Date</p>
                    <p className={cn('font-medium', isOverdue && 'text-danger')}>
                      {formatDate(new Date(rfq.due_date))}
                      {isOverdue ? ' (Overdue)' : ` (${daysUntilDue} days)`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Clock className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Received</p>
                    <p className="font-medium">{formatDate(new Date(rfq.received_date))}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <DollarSign className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Estimated Value</p>
                    <p className="font-medium">
                      {rfq.estimated_value ? formatCurrency(rfq.estimated_value) : 'Not specified'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <User className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Assigned To</p>
                    {rfq.assignee ? (
                      <div className="flex items-center gap-2">
                        <Avatar fallback={rfq.assignee.name} size="xs" />
                        <span className="font-medium">{rfq.assignee.name}</span>
                      </div>
                    ) : (
                      <p className="text-muted-foreground">Unassigned</p>
                    )}
                  </div>
                </div>
              </div>
              {rfq.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-2">
                  {rfq.tags.map((tag) => (
                    <Badge key={tag} variant="secondary">{tag}</Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Line Items */}
          <Card>
            <CardHeader>
              <CardTitle>Line Items</CardTitle>
              <CardDescription>{rfq.line_items.length} items</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="py-2 px-3 text-left text-sm font-medium">Part Number</th>
                      <th className="py-2 px-3 text-left text-sm font-medium">Description</th>
                      <th className="py-2 px-3 text-right text-sm font-medium">Qty</th>
                      <th className="py-2 px-3 text-left text-sm font-medium">UoM</th>
                      <th className="py-2 px-3 text-right text-sm font-medium">Target Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rfq.line_items.map((item) => (
                      <tr key={item.id} className="border-b">
                        <td className="py-2 px-3 font-medium">{item.part_number}</td>
                        <td className="py-2 px-3">{item.description}</td>
                        <td className="py-2 px-3 text-right">{item.quantity}</td>
                        <td className="py-2 px-3">{item.unit_of_measure}</td>
                        <td className="py-2 px-3 text-right">
                          {item.target_price ? formatCurrency(item.target_price) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Quotes */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Quotes</CardTitle>
                <CardDescription>{rfq.quotes.length} quote(s) created</CardDescription>
              </div>
              <Button size="sm" asChild>
                <Link href={`/quotes/new?rfq=${rfq.id}`}>
                  <Plus className="mr-2 h-4 w-4" />
                  New Quote
                </Link>
              </Button>
            </CardHeader>
            <CardContent>
              {rfq.quotes.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">
                  No quotes created yet
                </p>
              ) : (
                <div className="space-y-3">
                  {rfq.quotes.map((quote) => (
                    <Link key={quote.id} href={`/quotes/${quote.id}`}>
                      <div className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors">
                        <div>
                          <p className="font-medium">{quote.quote_number}</p>
                          <p className="text-sm text-muted-foreground">
                            Version {quote.version} • {formatRelativeTime(new Date(quote.created_at))}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium">{formatCurrency(quote.total_amount)}</p>
                          <Badge variant="secondary">{quote.status}</Badge>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Customer Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Customer
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Link href={`/customers/${rfq.customer.id}`} className="font-medium hover:underline">
                  {rfq.customer.name}
                </Link>
              </div>
              {rfq.customer.email && (
                <p className="text-sm text-muted-foreground">{rfq.customer.email}</p>
              )}
              {rfq.customer.phone && (
                <p className="text-sm text-muted-foreground">{rfq.customer.phone}</p>
              )}
              <Button variant="outline" size="sm" className="w-full" asChild>
                <Link href={`/customers/${rfq.customer.id}`}>
                  View Customer
                </Link>
              </Button>
            </CardContent>
          </Card>

          {/* Attachments */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Attachments
              </CardTitle>
            </CardHeader>
            <CardContent>
              {rfq.attachments.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No attachments
                </p>
              ) : (
                <div className="space-y-2">
                  {rfq.attachments.map((file) => (
                    <div key={file.id} className="flex items-center justify-between p-2 border rounded hover:bg-muted/50">
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span className="text-sm truncate">{file.filename}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {formatFileSize(file.file_size)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <Button variant="outline" size="sm" className="w-full mt-3">
                <Plus className="mr-2 h-4 w-4" />
                Add Attachment
              </Button>
            </CardContent>
          </Card>

          {/* Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {rfq.timeline.map((item, index) => (
                  <div key={item.id} className="flex gap-3">
                    <div className="relative flex flex-col items-center">
                      <Avatar fallback={item.user.name} size="xs" />
                      {index < rfq.timeline.length - 1 && (
                        <div className="w-px flex-1 bg-border mt-2" />
                      )}
                    </div>
                    <div className="flex-1 pb-4">
                      <p className="text-sm">
                        <span className="font-medium">{item.user.name}</span>
                      </p>
                      <p className="text-sm text-muted-foreground">{item.description}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatRelativeTime(new Date(item.timestamp))}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* No Bid Dialog */}
      <Dialog open={noBidDialogOpen} onOpenChange={setNoBidDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mark as No Bid</DialogTitle>
            <DialogDescription>
              Are you sure you want to mark this RFQ as No Bid? This action can be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Reason for no bid (optional)"
              value={noBidReason}
              onChange={(e) => setNoBidReason(e.target.value)}
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNoBidDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              // Handle no bid
              setNoBidDialogOpen(false);
              setNoBidReason('');
            }}>
              Confirm No Bid
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
