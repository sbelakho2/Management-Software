'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
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
import { cn, formatCurrency, formatDate, getInitials } from '@/lib/utils';
import { useCustomersStore } from '@/stores/customers';
import { StatCard, StatSection, AmbientStatus } from '@/components/ui/stat-card';

const statusConfig = {
  active: { label: 'Active', variant: 'success' as const },
  inactive: { label: 'Inactive', variant: 'secondary' as const },
  prospect: { label: 'Prospect', variant: 'warning' as const },
};

function CustomerStats({ customers }: { customers: any[] }) {
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
    <div className="grid gap-4 md:grid-cols-4">
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-success/60">Active Intelligence Nodes</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{stats.active}</p>
            </div>
            <div className="p-3 rounded-2xl bg-success/10 text-success shadow-sm">
              <Building2 className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-warning/60">Prospective Partners</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{stats.prospects}</p>
            </div>
            <div className="p-3 rounded-2xl bg-warning/10 text-warning shadow-sm">
              <Users className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-primary/60">Aggregated Revenue</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{formatCurrency(stats.totalRevenue)}</p>
            </div>
            <div className="p-3 rounded-2xl bg-primary/10 text-primary shadow-sm">
              <DollarSign className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">Mean Conversion Pulse</p>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">{stats.avgWinRate.toFixed(0)}%</p>
            </div>
            <div className="p-3 rounded-2xl bg-secondary/50 text-foreground shadow-sm">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function CustomerCard({ customer }: { customer: any }) {
  const router = useRouter();
  const config = (statusConfig as any)[customer.status] || statusConfig.active;

  return (
    <Card 
      className="hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => router.push(`/customers/${customer.id}`)}
    >
      <CardContent className="pt-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <Avatar size="lg">
              <AvatarFallback className="bg-primary/10 text-primary">
                {getInitials(customer.name)}
              </AvatarFallback>
            </Avatar>
            <div>
              <h3 className="font-semibold">{customer.name}</h3>
              <p className="text-sm text-muted-foreground">{customer.code}</p>
            </div>
          </div>
          <Badge variant={config.variant}>{config.label}</Badge>
        </div>

        <div className="mt-4 space-y-2 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Building2 className="h-4 w-4" />
            <span>{customer.industry}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <MapPin className="h-4 w-4" />
            <span>{customer.location_city || 'N/A'}, {customer.location_state || 'N/A'}</span>
          </div>
          {customer.primary_contact_name && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Users className="h-4 w-4" />
              <span>{customer.primary_contact_name}</span>
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t grid grid-cols-3 gap-2 text-center">
          <div>
            <p className="text-lg font-bold">{customer.total_rfqs || 0}</p>
            <p className="text-xs text-muted-foreground">RFQs</p>
          </div>
          <div>
            <p className="text-lg font-bold">{formatCurrency(customer.total_revenue || 0)}</p>
            <p className="text-xs text-muted-foreground">Revenue</p>
          </div>
          <div>
            <p className={cn(
              'text-lg font-bold',
              (customer.win_rate || 0) >= 70 ? 'text-success' : 
              (customer.win_rate || 0) >= 50 ? 'text-warning' : 'text-muted-foreground'
            )}>
              {customer.win_rate || 0}%
            </p>
            <p className="text-xs text-muted-foreground">Win Rate</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CustomerRow({ customer }: { customer: any }) {
  const router = useRouter();
  const config = (statusConfig as any)[customer.status] || statusConfig.active;

  return (
    <tr 
      className="border-b hover:bg-muted/50 cursor-pointer transition-colors"
      onClick={() => router.push(`/customers/${customer.id}`)}
    >
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          <Avatar>
            <AvatarFallback className="bg-primary/10 text-primary">
              {getInitials(customer.name)}
            </AvatarFallback>
          </Avatar>
          <div>
            <p className="font-medium">{customer.name}</p>
            <p className="text-sm text-muted-foreground">{customer.code}</p>
          </div>
        </div>
      </td>
      <td className="py-3 px-4">
        <Badge variant={config.variant}>{config.label}</Badge>
      </td>
      <td className="py-3 px-4 text-muted-foreground">{customer.industry}</td>
      <td className="py-3 px-4 text-muted-foreground">
        {customer.location_city || '—'}, {customer.location_state || '—'}
      </td>
      <td className="py-3 px-4">
        {customer.primary_contact_name ? (
          <div className="text-sm">
            <p>{customer.primary_contact_name}</p>
            <p className="text-muted-foreground">{customer.primary_contact_email}</p>
          </div>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td className="py-3 px-4 text-center">{customer.total_rfqs || 0}</td>
      <td className="py-3 px-4 text-right font-medium">
        {formatCurrency(customer.total_revenue || 0)}
      </td>
      <td className="py-3 px-4 text-center">
        <span className={cn(
          'font-medium',
          (customer.win_rate || 0) >= 70 ? 'text-success' : 
          (customer.win_rate || 0) >= 50 ? 'text-warning' : 'text-muted-foreground'
        )}>
          {customer.win_rate > 0 ? `${customer.win_rate}%` : '—'}
        </span>
      </td>
      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push(`/customers/${customer.id}`)}>
              <Eye className="mr-2 h-4 w-4" />
              View
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/customers/${customer.id}?mode=edit`)}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

export default function CustomersPage() {
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
    <div className="space-y-8 page-fade-in" data-testid="customers-page">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Account Management
          </h1>
          <p className="text-muted-foreground font-medium">Strategic customer relationships and account intelligence</p>
        </div>
        <div className="flex items-center gap-3">
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine" onClick={() => router.push('/customers/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Add Customer
          </Button>
        </div>
      </div>

      {/* Stats */}
      <CustomerStats customers={customersList} />

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search customers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="prospect">Prospect</SelectItem>
                </SelectContent>
              </Select>
              <Select value={industryFilter} onValueChange={setIndustryFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Industry" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All industries</SelectItem>
                  {industries.map((industry) => (
                    <SelectItem key={industry} value={industry as string}>{industry}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex border rounded-md">
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'ghost'}
                  size="sm"
                  className="rounded-r-none"
                  onClick={() => setViewMode('grid')}
                >
                  Grid
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'default' : 'ghost'}
                  size="sm"
                  className="rounded-l-none"
                  onClick={() => setViewMode('list')}
                >
                  List
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Content */}
      {loading ? (
        <div className="text-center py-12 text-muted-foreground">Loading customers...</div>
      ) : viewMode === 'grid' ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredCustomers.map((customer) => (
            <CustomerCard key={customer.id} customer={customer} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="py-3 px-4 text-left font-medium">Customer</th>
                    <th className="py-3 px-4 text-left font-medium">Status</th>
                    <th className="py-3 px-4 text-left font-medium">Industry</th>
                    <th className="py-3 px-4 text-left font-medium">Location</th>
                    <th className="py-3 px-4 text-left font-medium">Primary Contact</th>
                    <th className="py-3 px-4 text-center font-medium">RFQs</th>
                    <th className="py-3 px-4 text-right font-medium">Revenue</th>
                    <th className="py-3 px-4 text-center font-medium">Win Rate</th>
                    <th className="py-3 px-4 w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCustomers.map((customer) => (
                    <CustomerRow key={customer.id} customer={customer} />
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {!loading && filteredCustomers.length === 0 && (
        <div className="text-center py-12">
          <Building2 className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-medium">No customers found</h3>
          <p className="text-muted-foreground">
            {searchQuery || statusFilter !== 'all' || industryFilter !== 'all'
              ? 'Try adjusting your filters'
              : 'Add your first customer to get started'}
          </p>
        </div>
      )}
    </div>
  );
}
