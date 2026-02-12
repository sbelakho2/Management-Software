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
import { useI18n } from '@/contexts/i18n-context';
import { useToast } from '@/hooks/use-toast';

import { accountApi } from '@/api/accounts';
import { contactApi, type ContactResponse } from '@/api/contacts';
import { rfqApi } from '@/api/rfq';

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

const statusConfig = {
  active: { labelKey: 'pages.customers.status.active', variant: 'success' as const },
  inactive: { labelKey: 'pages.customers.status.inactive', variant: 'secondary' as const },
  prospect: { labelKey: 'pages.customers.status.prospect', variant: 'warning' as const },
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

import { useCustomersStore } from '@/stores/customers';

/** Map backend account status to the UI status type. */
function mapStatus(apiStatus: string): 'active' | 'inactive' | 'prospect' {
  const s = apiStatus?.toLowerCase() ?? '';
  if (s === 'active' || s === 'approved') return 'active';
  if (s === 'inactive' || s === 'closed' || s === 'blacklisted') return 'inactive';
  return 'prospect';
}

/** Map backend RFQ status to the limited set the UI understands. */
function mapRfqStatus(apiStatus: string): 'new' | 'reviewing' | 'quoting' | 'submitted' | 'won' | 'lost' {
  const s = apiStatus?.toLowerCase() ?? '';
  if (s === 'won' || s === 'accepted') return 'won';
  if (s === 'lost' || s === 'no_bid') return 'lost';
  if (s === 'quoting' || s === 'quoted') return 'quoting';
  if (s === 'submitted' || s === 'sent') return 'submitted';
  if (s === 'reviewing' || s === 'in_review') return 'reviewing';
  return 'new';
}

export default function CustomerDetailPage() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useParams();
  const { toast } = useToast();
  const { updateCustomer } = useCustomersStore();
  const [isLoading, setIsLoading] = React.useState(true);
  const [customer, setCustomer] = React.useState<Customer | null>(null);
  const [showDeactivateDialog, setShowDeactivateDialog] = React.useState(false);
  const [isEditing, setIsEditing] = React.useState(false);

  React.useEffect(() => {
    const customerId = params.id as string;
    if (!customerId) return;

    let cancelled = false;
    const load = async () => {
      setIsLoading(true);
      try {
        // Fetch account, contacts, and RFQs in parallel
        const [accountData, contactsRes, rfqsRes] = await Promise.all([
          accountApi.get(customerId),
          contactApi.list({ account_id: customerId, limit: 50 } as any),
          rfqApi.list({ customer_id: customerId, limit: 10 } as any),
        ]);
        if (cancelled) return;

        const acct = accountData as any;

        // Map contacts from API shape → local Contact shape
        const contacts: Contact[] = (contactsRes?.items ?? []).map((c: ContactResponse) => ({
          id: String(c.id),
          name: c.display_name || `${c.first_name} ${c.last_name}`.trim(),
          title: c.job_title ?? '',
          email: c.email ?? '',
          phone: c.phone_mobile || c.phone_work || '',
          isPrimary: false, // will be refined below if account has primary_contact_id
        }));

        // Map RFQs from API shape → local RFQ shape
        const rfqItems = rfqsRes?.items ?? [];
        const recentRFQs: RFQ[] = rfqItems.map((r: any) => ({
          id: String(r.id),
          rfqNumber: r.rfq_number ?? `RFQ-${String(r.id).slice(0, 8)}`,
          title: r.title ?? r.description ?? '',
          status: mapRfqStatus(r.status),
          value: r.estimated_value ?? r.total ?? 0,
          createdAt: r.created_at ?? '',
        }));

        // Compute stats from real RFQ data
        const totalRFQs = rfqsRes?.total ?? rfqItems.length;
        const openStatuses = ['new', 'reviewing', 'quoting'];
        const openRFQs = rfqItems.filter((r: any) => openStatuses.includes(mapRfqStatus(r.status))).length;
        const wonRfqs = rfqItems.filter((r: any) => mapRfqStatus(r.status) === 'won');
        const decidedRfqs = rfqItems.filter((r: any) => ['won', 'lost'].includes(mapRfqStatus(r.status)));
        const totalRevenue = wonRfqs.reduce((s: number, r: any) => s + (r.estimated_value ?? r.total ?? 0), 0);
        const avgOrderValue = wonRfqs.length > 0 ? totalRevenue / wonRfqs.length : 0;
        const winRate = decidedRfqs.length > 0 ? Math.round((wonRfqs.length / decidedRfqs.length) * 100) : 0;

        setCustomer({
          id: String(acct.id),
          name: acct.name ?? '',
          code: acct.account_number ?? '',
          status: mapStatus(acct.status),
          industry: acct.industry ?? '',
          website: acct.website ?? undefined,
          address: {
            street: [acct.address_line1, acct.address_line2].filter(Boolean).join(', '),
            city: acct.city ?? '',
            state: acct.state_province ?? '',
            postalCode: acct.postal_code ?? '',
            country: acct.country ?? '',
          },
          contacts,
          stats: { totalRFQs, openRFQs, totalRevenue, avgOrderValue, winRate },
          recentRFQs,
          recentActivity: [], // populated from timeline when available
          notes: acct.internal_notes ?? acct.description ?? undefined,
          createdAt: acct.created_at ?? '',
          updatedAt: acct.updated_at ?? '',
        });
      } catch (err) {
        console.error('Failed to load customer:', err);
        if (!cancelled) setCustomer(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [params.id]);

  const handleDeactivate = async () => {
    if (!customer) return;
    try {
      await accountApi.update(customer.id, { status: 'inactive' });
      setCustomer((prev) => prev ? { ...prev, status: 'inactive' } : prev);
      toast({
        title: t('pages.customers.detail.deactivated') || 'Customer deactivated',
        description: `${customer.name} has been deactivated`,
      });
    } catch {
      toast({ title: 'Error', description: 'Failed to deactivate customer', variant: 'destructive' as any });
    }
    setShowDeactivateDialog(false);
  };

  if (isLoading) {
    return <CustomerDetailSkeleton />;
  }

  if (!customer) {
    return (
      <div className="text-center py-12">
        <h2 className="text-lg font-medium">{t('pages.customers.detail.notFound')}</h2>
        <Button className="mt-4" onClick={() => router.push('/customers')}>
          {t('pages.customers.detail.backToCustomers')}
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
            <AvatarFallback className="bg-rams-panel text-muted-foreground text-lg">
              {getInitials(customer.name)}
            </AvatarFallback>
          </Avatar>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-heading font-bold tracking-tight ">{customer.name}</h1>
              <Badge variant={config.variant}>{t(config.labelKey)}</Badge>
            </div>
            <p className="text-muted-foreground">{customer.code} • {customer.industry}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setIsEditing(true)}>
            <Edit className="mr-2 h-4 w-4" />
            {t('common.edit')}
          </Button>
          <Button onClick={() => router.push(`/pipeline/new?customer=${customer.id}`)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('pages.customers.detail.newRfq')}
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
                {t('pages.customers.detail.viewAllRfqs')}
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Users className="mr-2 h-4 w-4" />
                {t('pages.customers.detail.manageContacts')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {customer.status === 'active' ? (
                <DropdownMenuItem onClick={() => setShowDeactivateDialog(true)} className="text-warning">
                  <Archive className="mr-2 h-4 w-4" />
                  {t('pages.customers.detail.deactivate')}
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem className="text-success">
                  <CheckCircle className="mr-2 h-4 w-4" />
                  {t('pages.customers.detail.activate')}
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
            <p className="text-3xl font-heading font-bold tracking-tight ">{customer.stats.totalRFQs}</p>
            <p className="text-sm text-muted-foreground">{t('pages.customers.detail.stats.totalRfqs')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-3xl font-heading font-bold tracking-tight ">{customer.stats.openRFQs}</p>
            <p className="text-sm text-muted-foreground">{t('pages.customers.detail.stats.openRfqs')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-3xl font-heading font-bold tracking-tight ">{formatCurrency(customer.stats.totalRevenue)}</p>
            <p className="text-sm text-muted-foreground">{t('pages.customers.detail.stats.totalRevenue')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-3xl font-heading font-bold tracking-tight ">{formatCurrency(customer.stats.avgOrderValue)}</p>
            <p className="text-sm text-muted-foreground">{t('pages.customers.detail.stats.avgOrder')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className={cn(
              'text-3xl font-heading font-bold tracking-tight ',
              customer.stats.winRate >= 70 ? 'text-success' : 
              customer.stats.winRate >= 50 ? 'text-warning' : 'text-danger'
            )}>
              {customer.stats.winRate}%
            </p>
            <p className="text-sm text-muted-foreground">{t('pages.customers.detail.stats.winRate')}</p>
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
                <CardTitle>{t('pages.customers.detail.recentRfqs')}</CardTitle>
                <CardDescription>{t('pages.customers.detail.recentRfqsDesc')}</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => router.push(`/pipeline?customer=${customer.id}`)}>
                {t('pages.customers.detail.viewAll')}
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
                      className="flex items-center justify-between px-4 py-3 hover:bg-rams-panel transition-none"
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
                <CardTitle>{t('pages.customers.detail.contacts')}</CardTitle>
                <CardDescription>{customer.contacts.length} {t('pages.customers.detail.contactsCount')}</CardDescription>
              </div>
              <Button variant="outline" size="sm">
                <Plus className="mr-2 h-4 w-4" />
                {t('pages.customers.detail.addContact')}
              </Button>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                {customer.contacts.map((contact) => (
                  <div key={contact.id} className="border border-rams-line rounded-rams-sm p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <Avatar>
                          <AvatarFallback>{getInitials(contact.name)}</AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{contact.name}</p>
                            {contact.isPrimary && (
                              <Badge variant="secondary" size="sm">{t('pages.customers.detail.primaryBadge')}</Badge>
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
            <Card className="border-rams-orange/50 bg-rams-orange/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  {t('pages.customers.detail.notes')}
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
                {t('pages.customers.detail.companyInfo')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">{t('pages.customers.detail.address')}</p>
                <p className="text-sm mt-1">
                  {customer.address.street}<br />
                  {customer.address.city}, {customer.address.state} {customer.address.postalCode}<br />
                  {customer.address.country}
                </p>
              </div>
              {customer.website && (
                <div>
                  <p className="text-sm text-muted-foreground">{t('pages.customers.detail.website')}</p>
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
                  <p className="text-sm text-muted-foreground">{t('pages.customers.detail.primaryContact')}</p>
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
                {t('pages.customers.detail.recentActivity')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {customer.recentActivity.map((activity) => {
                  const Icon = activityIcons[activity.type];
                  return (
                    <div key={activity.id} className="flex items-start gap-3">
                      <div className="p-1.5 rounded-rams-sm bg-rams-panel border border-rams-line">
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
                <span className="text-muted-foreground">{t('pages.customers.detail.created')}</span>
                <span>{formatDate(new Date(customer.createdAt))}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t('pages.customers.detail.lastUpdated')}</span>
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
            <DialogTitle>{t('pages.customers.detail.deactivateDialog.title')}</DialogTitle>
            <DialogDescription>
              {t('pages.customers.detail.deactivateDialog.description', { name: customer.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeactivateDialog(false)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleDeactivate}>
              {t('pages.customers.detail.deactivateDialog.confirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
