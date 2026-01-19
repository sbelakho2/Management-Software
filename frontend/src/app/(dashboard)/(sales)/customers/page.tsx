'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  Edit,
  Building2,
  Mail,
  Phone,
  MapPin,
  DollarSign,
  FileText,
  Users,
  TrendingUp,
  Archive,
  Download,
  Upload,
} from 'lucide-react';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn, formatCurrency, formatDate, getInitials } from '@/lib/utils';
import { useCustomersStore } from '@/stores/customers';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

const statusConfig = {
  active: { labelKey: 'pages.customers.status.active', variant: 'success' as const },
  inactive: { labelKey: 'pages.customers.status.inactive', variant: 'secondary' as const },
  prospect: { labelKey: 'pages.customers.status.prospect', variant: 'warning' as const },
};

function CustomerStats({ customers }: { customers: any[] }) {
  const { t } = useI18n();
  const stats = React.useMemo(() => {
    const active = customers.filter((c) => c.status === 'active').length;
    const prospects = customers.filter((c) => c.status === 'prospect').length;
    const totalRevenue = customers.reduce((sum, c) => sum + (c.total_revenue || 0), 0);
    const avgWinRate = customers.filter((c) => (c.win_rate || 0) > 0).length > 0
      ? customers.filter((c) => (c.win_rate || 0) > 0).reduce((sum, c) => sum + c.win_rate, 0) / 
        customers.filter((c) => (c.win_rate || 0) > 0).length
      : 0;
    return { active, prospects, totalRevenue, avgWinRate };
  }, [customers]);

  return (
    <div className="grid gap-0 md:grid-cols-4 border border-rams-line bg-rams-line">
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.customers.stats.activeNodes')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.active}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.customers.stats.prospectivePartners')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{stats.prospects}</p>
      </div>
      <div className="bg-rams-module p-6 border-r border-b border-rams-line last:border-r-0">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.customers.stats.aggregatedRevenue')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{formatCurrency(stats.totalRevenue)}</p>
      </div>
      <div className="bg-rams-module p-6 border-b border-rams-line">
        <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('pages.customers.stats.meanConversionPulse')}</p>
        <p className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{stats.avgWinRate.toFixed(1)}%</p>
      </div>
    </div>
  );
}

function CustomerCard({ customer }: { customer: any }) {
  const router = useRouter();
  const { t } = useI18n();
  const config = (statusConfig as any)[customer.status] || statusConfig.active;

  return (
    <Card 
      className="rounded-rams-sm group cursor-pointer"
      onClick={() => router.push(`/customers/${customer.id}`)}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-4">
            <Avatar className="h-12 w-12 rounded-none border border-rams-line">
              <AvatarImage src={customer.logo_url} />
              <AvatarFallback className="bg-rams-panel text-muted-foreground font-mono font-black">{getInitials(customer.name)}</AvatarFallback>
            </Avatar>
            <div>
              <h3 className="font-sans font-black text-sm uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{customer.name}</h3>
              <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-0.5">{t('pages.customers.nodeId')}: {customer.code || customer.id.substring(0, 4)}</p>
            </div>
          </div>
          <Badge variant={config.variant} size="sm">{t(config.labelKey).toUpperCase()}</Badge>
        </div>

        <div className="space-y-3 mb-6">
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground/60 font-medium">
            <Building2 className="h-3.5 w-3.5 text-muted-foreground/30" />
            <span className="truncate">{customer.industry || t('common.notClassified')}</span>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground/60 font-medium">
            <MapPin className="h-3.5 w-3.5 text-muted-foreground/30" />
            <span className="truncate">{customer.location_city || t('common.unknown')}</span>
          </div>
          {customer.primary_contact_name && (
            <div className="flex items-center gap-3 text-[10px] text-muted-foreground/60 font-medium">
              <Users className="h-3.5 w-3.5 text-muted-foreground/30" />
              <span>{customer.primary_contact_name}</span>
            </div>
          )}
        </div>

        <div className="pt-6 border-t border-rams-line grid grid-cols-3 gap-2">
          <div>
            <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40 mb-1">{t('pages.customers.metrics.rfqs')}</p>
            <p className="text-sm font-mono font-bold tabular-nums text-foreground/80">{customer.total_rfqs || 0}</p>
          </div>
          <div>
            <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40 mb-1">{t('pages.customers.metrics.revenue')}</p>
            <p className="text-sm font-mono font-bold tabular-nums text-foreground/80">{formatCurrency(customer.total_revenue || 0)}</p>
          </div>
          <div>
            <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40 mb-1">{t('pages.customers.metrics.winRate')}</p>
            <p className="text-sm font-mono font-bold tabular-nums text-rams-green">{(customer.win_rate || 0).toFixed(1)}%</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CustomerRow({ customer }: { customer: any }) {
  const router = useRouter();
  const { t } = useI18n();
  const config = (statusConfig as any)[customer.status] || statusConfig.active;

  return (
    <TableRow 
      className="transition-none cursor-pointer group"
      onClick={() => router.push(`/customers/${customer.id}`)}
    >
      <TableCell>
        <div className="flex items-center gap-3">
          <Avatar className="h-8 w-8 rounded-none border border-rams-line">
            <AvatarFallback className="bg-rams-panel text-muted-foreground font-mono font-black text-[10px]">
              {getInitials(customer.name)}
            </AvatarFallback>
          </Avatar>
          <div>
            <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{customer.name}</p>
            <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest">{customer.code}</p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant={config.variant} size="sm">{t(config.labelKey).toUpperCase()}</Badge>
      </TableCell>
      <TableCell className="text-[10px] font-medium text-muted-foreground/60 uppercase">{customer.industry}</TableCell>
      <TableCell className="text-[10px] font-medium text-muted-foreground/60 uppercase">
        {customer.location_city || '—'}, {customer.location_state || '—'}
      </TableCell>
      <TableCell>
        {customer.primary_contact_name ? (
          <div className="text-[10px] font-medium">
            <p className="text-foreground/80">{customer.primary_contact_name.toUpperCase()}</p>
            <p className="text-muted-foreground/40 font-mono lowercase">{customer.primary_contact_email}</p>
          </div>
        ) : (
          <span className="text-muted-foreground/20">—</span>
        )}
      </TableCell>
      <TableCell className="text-center font-mono font-bold tabular-nums">{customer.total_rfqs || 0}</TableCell>
      <TableCell className="text-right font-mono font-bold tabular-nums">
        {formatCurrency(customer.total_revenue || 0)}
      </TableCell>
      <TableCell className="text-center">
        <span className={cn(
          'font-mono font-bold tabular-nums',
          (customer.win_rate || 0) >= 70 ? 'text-rams-green' : 
          (customer.win_rate || 0) >= 50 ? 'text-rams-orange' : 'text-muted-foreground/40'
        )}>
          {customer.win_rate > 0 ? `${customer.win_rate}%` : '—'}
        </span>
      </TableCell>
      <TableCell onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push(`/customers/${customer.id}`)}>
              <Eye className="mr-2 h-3.5 w-3.5" />
              {t('pages.customers.actions.analyze')}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/customers/${customer.id}?mode=edit`)}>
              <Edit className="mr-2 h-3.5 w-3.5" />
              {t('pages.customers.actions.modify')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

export default function CustomersPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { customers, loading, fetchCustomers } = useCustomersStore();
  const customersList = React.useMemo(() => (Array.isArray(customers) ? customers : []), [customers]);
  
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [industryFilter, setIndustryFilter] = React.useState<string>('all');
  const [viewMode, setViewMode] = React.useState<'grid' | 'list'>('grid');

  React.useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  const industries = React.useMemo(() => {
    return [...new Set(customersList.map((c) => c.industry).filter(Boolean))];
  }, [customersList]);

  const filteredCustomers = React.useMemo(() => {
    return customersList.map(c => ({
      ...c,
      code: (c as any).account_number || '',
      location_city: (c as any).city || '',
      location_state: (c as any).country || '', // Mapping country to state if state is missing
      total_rfqs: 0, // Backend doesn't provide these yet in list view
      total_revenue: 0,
      win_rate: 0,
    })).filter((customer) => {
      const matchesSearch = searchQuery === '' ||
        customer.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        customer.code.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'all' || customer.status === statusFilter;
      const matchesIndustry = industryFilter === 'all' || (customer.industry || '').toLowerCase() === industryFilter.toLowerCase();
      return matchesSearch && matchesStatus && matchesIndustry;
    });
  }, [customersList, searchQuery, statusFilter, industryFilter]);

  return (
    <div className="space-y-8 page-fade-in pb-12" data-testid="customers-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
            {t('pages.customers.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.customers.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>STATION: CRM-01</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm" onClick={() => {}}>
            <Download className="mr-2 h-3.5 w-3.5" />
            {t('pages.customers.exportIntel')}
          </Button>
          <Button size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase" onClick={() => router.push('/customers/new')}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            {t('pages.customers.initializeNode')}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <CustomerStats customers={customersList} />

      {/* Filters & View Toggle */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-4 flex-wrap max-w-4xl">
          <div className="relative flex-1 min-w-[240px] group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 transition-colors group-focus-within:text-rams-orange" />
            <Input
              placeholder={t('pages.customers.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-10 text-[10px]"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px] h-10 text-[10px]">
              <Filter className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder="STATUS_STATE" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('pages.customers.filters.allStates')}</SelectItem>
              <SelectItem value="active">{t('pages.customers.filters.active')}</SelectItem>
              <SelectItem value="inactive">{t('pages.customers.filters.inactive')}</SelectItem>
              <SelectItem value="prospect">{t('pages.customers.filters.prospect')}</SelectItem>
            </SelectContent>
          </Select>
          <Select value={industryFilter} onValueChange={setIndustryFilter}>
            <SelectTrigger className="w-[180px] h-10 text-[10px]">
              <Building2 className="mr-2 h-3.5 w-3.5 opacity-40" />
              <SelectValue placeholder="INDUSTRY_CAT" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('pages.customers.filters.allIndustries')}</SelectItem>
              {industries.map((industry) => (
                <SelectItem key={industry} value={industry as string}>{String(industry).toUpperCase()}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1 bg-rams-panel p-1 border border-rams-line rounded-rams-sm">
          <Button
            variant={viewMode === 'grid' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('grid')}
            className={cn("h-8 px-3 rounded-none", viewMode === 'grid' ? "bg-rams-orange text-black" : "text-muted-foreground")}
          >
            {t('pages.customers.viewModes.grid')}
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('list')}
            className={cn("h-8 px-3 rounded-none", viewMode === 'list' ? "bg-rams-orange text-black" : "text-muted-foreground")}
          >
            {t('pages.customers.viewModes.table')}
          </Button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="industrial-panel p-6 space-y-4">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 bg-rams-panel border border-rams-line animate-pulse" />
                <div className="space-y-2 flex-1">
                  <div className="h-3 w-1/2 bg-rams-panel animate-pulse" />
                  <div className="h-2 w-1/4 bg-rams-panel animate-pulse" />
                </div>
              </div>
              <div className="h-20 bg-rams-panel animate-pulse" />
            </div>
          ))}
        </div>
      ) : filteredCustomers.length === 0 ? (
        <div className="py-24 text-center border border-dashed border-rams-line bg-rams-panel/20">
          <Building2 className="mx-auto h-12 w-12 text-muted-foreground/20" />
          <div className="mt-4">
            <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60">{t('pages.customers.emptyState.title')}</p>
            <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-1">{t('pages.customers.emptyState.description')}</p>
          </div>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filteredCustomers.map((customer) => (
            <CustomerCard key={customer.id} customer={customer} />
          ))}
        </div>
      ) : (
        <Card className="rounded-rams-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('pages.customers.table.accountIdentifier')}</TableHead>
                <TableHead>{t('pages.customers.table.statusState')}</TableHead>
                <TableHead>{t('pages.customers.table.industryCat')}</TableHead>
                <TableHead>{t('pages.customers.table.locationNode')}</TableHead>
                <TableHead>{t('pages.customers.table.primaryContact')}</TableHead>
                <TableHead className="text-center">{t('pages.customers.table.rfqs')}</TableHead>
                <TableHead className="text-right">{t('pages.customers.table.totalVal')}</TableHead>
                <TableHead className="text-center">{t('pages.customers.table.winKpi')}</TableHead>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCustomers.map((customer) => (
                <CustomerRow key={customer.id} customer={customer} />
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
