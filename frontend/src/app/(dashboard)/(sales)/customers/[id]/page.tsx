'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  Edit,
  MoreHorizontal,
  Building2,
  Mail,
  Phone,
  MapPin,
  Globe,
  User,
  Plus,
  FileText,
  DollarSign,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  Send,
  Calendar,
  Archive,
  Users,
  MessageSquare,
  Paperclip,
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
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { cn, formatCurrency, formatDate, formatDateTime, formatRelativeTime, getInitials } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface Contact {
  id: string;
  name: string;
  title: string;
  email: string;
  phone: string;
  isPrimary: boolean;
}

interface RFQ {
  id: string;
  rfqNumber: string;
  title: string;
  status: 'new' | 'reviewing' | 'quoting' | 'submitted' | 'won' | 'lost';
  value: number;
  createdAt: string;
}

interface Activity {
  id: string;
  type: 'rfq_created' | 'quote_sent' | 'quote_accepted' | 'quote_rejected' | 'contact_added' | 'note_added';
  description: string;
  user: string;
  createdAt: string;
}

interface Customer {
  id: string;
  name: string;
  code: string;
  status: 'active' | 'inactive' | 'prospect';
  industry: string;
  website?: string;
  address: {
    street: string;
    city: string;
    state: string;
    postalCode: string;
    country: string;
  };
  contacts: Contact[];
  stats: {
    totalRFQs: number;
    openRFQs: number;
    totalRevenue: number;
    avgOrderValue: number;
    winRate: number;
  };
  recentRFQs: RFQ[];
  recentActivity: Activity[];
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

const mockCustomer: Customer = {
  id: '1',
  name: 'Aerospace Dynamics Inc.',
  code: 'AERO-001',
  status: 'active',
  industry: 'Aerospace',
  website: 'https://aerospacedynamics.com',
  address: {
    street: '1234 Aviation Blvd',
    city: 'Los Angeles',
    state: 'CA',
    postalCode: '90045',
    country: 'USA',
  },
  contacts: [
    { id: '1', name: 'Michael Roberts', title: 'Procurement Manager', email: 'mroberts@aerospacedynamics.com', phone: '+1 (555) 234-5678', isPrimary: true },
    { id: '2', name: 'Sarah Johnson', title: 'Engineering Lead', email: 'sjohnson@aerospacedynamics.com', phone: '+1 (555) 234-5679', isPrimary: false },
    { id: '3', name: 'David Lee', title: 'Quality Manager', email: 'dlee@aerospacedynamics.com', phone: '+1 (555) 234-5680', isPrimary: false },
  ],
  stats: {
    totalRFQs: 45,
    openRFQs: 3,
    totalRevenue: 1250000,
    avgOrderValue: 42000,
    winRate: 72,
  },
  recentRFQs: [
    { id: '1', rfqNumber: 'RFQ-2024-0089', title: 'Precision brackets for aircraft assembly', status: 'quoting', value: 124500, createdAt: '2024-01-10' },
    { id: '2', rfqNumber: 'RFQ-2024-0072', title: 'Landing gear components', status: 'submitted', value: 89000, createdAt: '2024-01-05' },
    { id: '3', rfqNumber: 'RFQ-2023-0445', title: 'Structural fasteners', status: 'won', value: 156000, createdAt: '2023-12-15' },
    { id: '4', rfqNumber: 'RFQ-2023-0398', title: 'Hydraulic fittings', status: 'lost', value: 67500, createdAt: '2023-11-20' },
  ],
  recentActivity: [
    { id: '1', type: 'quote_sent', description: 'Quote Q-2024-0112 sent to customer', user: 'Sarah Chen', createdAt: '2024-01-12T10:00:00Z' },
    { id: '2', type: 'rfq_created', description: 'RFQ-2024-0089 received', user: 'System', createdAt: '2024-01-10T09:30:00Z' },
    { id: '3', type: 'quote_accepted', description: 'Quote Q-2023-0445 accepted by customer', user: 'System', createdAt: '2023-12-20T14:00:00Z' },
    { id: '4', type: 'contact_added', description: 'New contact David Lee added', user: 'John Doe', createdAt: '2023-12-01T11:00:00Z' },
  ],
  notes: 'Preferred customer - always prioritize their RFQs. They have specific AS9100 quality requirements.',
  createdAt: '2022-03-15',
  updatedAt: '2024-01-12T10:00:00Z',
};

const statusConfig = {
  active: { label: 'Active', variant: 'success' as const },
  inactive: { label: 'Inactive', variant: 'secondary' as const },
  prospect: { label: 'Prospect', variant: 'warning' as const },
};

const rfqStatusConfig = {
  new: { label: 'New', variant: 'default' as const },
  reviewing: { label: 'Reviewing', variant: 'secondary' as const },
  quoting: { label: 'Quoting', variant: 'warning' as const },
  submitted: { label: 'Submitted', variant: 'default' as const },
  won: { label: 'Won', variant: 'success' as const },
  lost: { label: 'Lost', variant: 'danger' as const },
};

const activityIcons = {
  rfq_created: FileText,
  quote_sent: Send,
  quote_accepted: CheckCircle,
  quote_rejected: XCircle,
  contact_added: User,
  note_added: MessageSquare,
};

function CustomerDetailSkeleton() {
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
        <div className="space-y-6">
          <Skeleton className="h-48" />
          <Skeleton className="h-32" />
        </div>
      </div>
    </div>
  );
}

export default function CustomerDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = React.useState(true);
  const [customer, setCustomer] = React.useState<Customer | null>(null);
  const [showDeactivateDialog, setShowDeactivateDialog] = React.useState(false);
  const [isEditing, setIsEditing] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setCustomer(mockCustomer);
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, [params.id]);

  const handleDeactivate = () => {
    toast({
      title: 'Customer deactivated',
      description: `${mockCustomer.name} has been deactivated`,
    });
    setShowDeactivateDialog(false);
  };

  if (isLoading) {
    return <CustomerDetailSkeleton />;
  }

  if (!customer) {
    return (
      <div className="text-center py-12">
        <h2 className="text-lg font-medium">Customer not found</h2>
        <Button className="mt-4" onClick={() => router.push('/customers')}>
          Back to Customers
        </Button>
      </div>
    );
  }

  const primaryContact = customer.contacts.find((c) => c.isPrimary);
  const config = statusConfig[customer.status];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <Avatar size="lg">
            <AvatarFallback className="bg-primary/10 text-primary text-lg">
              {getInitials(customer.name)}
            </AvatarFallback>
          </Avatar>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{customer.name}</h1>
              <Badge variant={config.variant}>{config.label}</Badge>
            </div>
            <p className="text-muted-foreground">{customer.code} • {customer.industry}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setIsEditing(true)}>
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button onClick={() => router.push(`/pipeline/new?customer=${customer.id}`)}>
            <Plus className="mr-2 h-4 w-4" />
            New RFQ
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <FileText className="mr-2 h-4 w-4" />
                View All RFQs
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Users className="mr-2 h-4 w-4" />
                Manage Contacts
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {customer.status === 'active' ? (
                <DropdownMenuItem onClick={() => setShowDeactivateDialog(true)} className="text-warning">
                  <Archive className="mr-2 h-4 w-4" />
                  Deactivate
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem className="text-success">
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Activate
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-5">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{customer.stats.totalRFQs}</p>
            <p className="text-sm text-muted-foreground">Total RFQs</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{customer.stats.openRFQs}</p>
            <p className="text-sm text-muted-foreground">Open RFQs</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{formatCurrency(customer.stats.totalRevenue)}</p>
            <p className="text-sm text-muted-foreground">Total Revenue</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{formatCurrency(customer.stats.avgOrderValue)}</p>
            <p className="text-sm text-muted-foreground">Avg Order</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className={cn(
              'text-2xl font-bold',
              customer.stats.winRate >= 70 ? 'text-success' : 
              customer.stats.winRate >= 50 ? 'text-warning' : 'text-danger'
            )}>
              {customer.stats.winRate}%
            </p>
            <p className="text-sm text-muted-foreground">Win Rate</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Recent RFQs */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Recent RFQs</CardTitle>
                <CardDescription>Latest requests from this customer</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => router.push(`/pipeline?customer=${customer.id}`)}>
                View All
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y">
                {customer.recentRFQs.map((rfq) => {
                  const statusCfg = rfqStatusConfig[rfq.status];
                  return (
                    <Link
                      key={rfq.id}
                      href={`/pipeline/${rfq.id}`}
                      className="flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{rfq.rfqNumber}</span>
                          <Badge variant={statusCfg.variant} size="sm">{statusCfg.label}</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">{rfq.title}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">{formatCurrency(rfq.value)}</p>
                        <p className="text-sm text-muted-foreground">{formatDate(new Date(rfq.createdAt))}</p>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Contacts */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Contacts</CardTitle>
                <CardDescription>{customer.contacts.length} contacts</CardDescription>
              </div>
              <Button variant="outline" size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add Contact
              </Button>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                {customer.contacts.map((contact) => (
                  <div key={contact.id} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <Avatar>
                          <AvatarFallback>{getInitials(contact.name)}</AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{contact.name}</p>
                            {contact.isPrimary && (
                              <Badge variant="secondary" size="sm">Primary</Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground">{contact.title}</p>
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 space-y-1 text-sm">
                      <a href={`mailto:${contact.email}`} className="flex items-center gap-2 text-primary hover:underline">
                        <Mail className="h-4 w-4" />
                        {contact.email}
                      </a>
                      <a href={`tel:${contact.phone}`} className="flex items-center gap-2 text-muted-foreground hover:text-foreground">
                        <Phone className="h-4 w-4" />
                        {contact.phone}
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          {customer.notes && (
            <Card className="border-warning/50 bg-warning/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Notes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{customer.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Company Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                Company Info
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Address</p>
                <p className="text-sm mt-1">
                  {customer.address.street}<br />
                  {customer.address.city}, {customer.address.state} {customer.address.postalCode}<br />
                  {customer.address.country}
                </p>
              </div>
              {customer.website && (
                <div>
                  <p className="text-sm text-muted-foreground">Website</p>
                  <a 
                    href={customer.website} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline flex items-center gap-1"
                  >
                    <Globe className="h-4 w-4" />
                    {customer.website.replace('https://', '')}
                  </a>
                </div>
              )}
              {primaryContact && (
                <div>
                  <p className="text-sm text-muted-foreground">Primary Contact</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Avatar size="sm">
                      <AvatarFallback>{getInitials(primaryContact.name)}</AvatarFallback>
                    </Avatar>
                    <div className="text-sm">
                      <p className="font-medium">{primaryContact.name}</p>
                      <p className="text-muted-foreground">{primaryContact.title}</p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {customer.recentActivity.map((activity) => {
                  const Icon = activityIcons[activity.type];
                  return (
                    <div key={activity.id} className="flex items-start gap-3">
                      <div className="p-1.5 rounded-full bg-muted">
                        <Icon className="h-3 w-3" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm">{activity.description}</p>
                        <p className="text-xs text-muted-foreground">
                          {activity.user} • {formatRelativeTime(activity.createdAt)}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Meta */}
          <Card>
            <CardContent className="pt-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span>{formatDate(new Date(customer.createdAt))}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Last Updated</span>
                <span>{formatRelativeTime(customer.updatedAt)}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Deactivate Dialog */}
      <Dialog open={showDeactivateDialog} onOpenChange={setShowDeactivateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deactivate Customer</DialogTitle>
            <DialogDescription>
              Are you sure you want to deactivate {customer.name}? They will no longer appear in search results or be available for new RFQs.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeactivateDialog(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeactivate}>
              Deactivate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
