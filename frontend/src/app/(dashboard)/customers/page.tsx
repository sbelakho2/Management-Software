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

interface Customer {
  id: string;
  name: string;
  code: string;
  status: 'active' | 'inactive' | 'prospect';
  industry: string;
  primaryContact?: {
    name: string;
    email: string;
    phone: string;
  };
  location: {
    city: string;
    state: string;
    country: string;
  };
  stats: {
    totalRFQs: number;
    openRFQs: number;
    totalRevenue: number;
    winRate: number;
  };
  lastActivityAt: string;
  createdAt: string;
}

const mockCustomers: Customer[] = [
  {
    id: '1',
    name: 'Aerospace Dynamics Inc.',
    code: 'AERO-001',
    status: 'active',
    industry: 'Aerospace',
    primaryContact: {
      name: 'Michael Roberts',
      email: 'mroberts@aerospacedynamics.com',
      phone: '+1 (555) 234-5678',
    },
    location: { city: 'Los Angeles', state: 'CA', country: 'USA' },
    stats: { totalRFQs: 45, openRFQs: 3, totalRevenue: 1250000, winRate: 72 },
    lastActivityAt: '2024-01-12T10:00:00Z',
    createdAt: '2022-03-15',
  },
  {
    id: '2',
    name: 'TechCorp Manufacturing',
    code: 'TECH-001',
    status: 'active',
    industry: 'Electronics',
    primaryContact: {
      name: 'Jennifer Smith',
      email: 'jsmith@techcorp.com',
      phone: '+1 (555) 345-6789',
    },
    location: { city: 'Austin', state: 'TX', country: 'USA' },
    stats: { totalRFQs: 28, openRFQs: 2, totalRevenue: 890000, winRate: 65 },
    lastActivityAt: '2024-01-11T14:30:00Z',
    createdAt: '2022-06-20',
  },
  {
    id: '3',
    name: 'Global Defense Systems',
    code: 'GDS-001',
    status: 'active',
    industry: 'Defense',
    primaryContact: {
      name: 'Robert Johnson',
      email: 'rjohnson@globaldefense.com',
      phone: '+1 (555) 456-7890',
    },
    location: { city: 'Washington', state: 'DC', country: 'USA' },
    stats: { totalRFQs: 62, openRFQs: 5, totalRevenue: 2150000, winRate: 78 },
    lastActivityAt: '2024-01-10T09:15:00Z',
    createdAt: '2021-11-08',
  },
  {
    id: '4',
    name: 'Industrial Solutions Ltd.',
    code: 'ISL-001',
    status: 'inactive',
    industry: 'Industrial',
    primaryContact: {
      name: 'David Brown',
      email: 'dbrown@industrialsolutions.com',
      phone: '+1 (555) 567-8901',
    },
    location: { city: 'Chicago', state: 'IL', country: 'USA' },
    stats: { totalRFQs: 12, openRFQs: 0, totalRevenue: 245000, winRate: 50 },
    lastActivityAt: '2023-09-15T11:00:00Z',
    createdAt: '2023-02-10',
  },
  {
    id: '5',
    name: 'Precision Parts Co.',
    code: 'PPC-001',
    status: 'active',
    industry: 'Automotive',
    primaryContact: {
      name: 'Sarah Wilson',
      email: 'swilson@precisionparts.com',
      phone: '+1 (555) 678-9012',
    },
    location: { city: 'Detroit', state: 'MI', country: 'USA' },
    stats: { totalRFQs: 34, openRFQs: 1, totalRevenue: 675000, winRate: 68 },
    lastActivityAt: '2024-01-09T16:45:00Z',
    createdAt: '2022-08-25',
  },
  {
    id: '6',
    name: 'MedTech Innovations',
    code: 'MTI-001',
    status: 'prospect',
    industry: 'Medical',
    location: { city: 'Boston', state: 'MA', country: 'USA' },
    stats: { totalRFQs: 2, openRFQs: 1, totalRevenue: 0, winRate: 0 },
    lastActivityAt: '2024-01-08T10:00:00Z',
    createdAt: '2024-01-05',
  },
];

const statusConfig = {
  active: { label: 'Active', variant: 'success' as const },
  inactive: { label: 'Inactive', variant: 'secondary' as const },
  prospect: { label: 'Prospect', variant: 'warning' as const },
};

function CustomerStats({ customers }: { customers: Customer[] }) {
  const stats = React.useMemo(() => {
    const active = customers.filter((c) => c.status === 'active').length;
    const prospects = customers.filter((c) => c.status === 'prospect').length;
    const totalRevenue = customers.reduce((sum, c) => sum + c.stats.totalRevenue, 0);
    const avgWinRate = customers.filter((c) => c.stats.winRate > 0).length > 0
      ? customers.filter((c) => c.stats.winRate > 0).reduce((sum, c) => sum + c.stats.winRate, 0) / 
        customers.filter((c) => c.stats.winRate > 0).length
      : 0;
    return { active, prospects, totalRevenue, avgWinRate };
  }, [customers]);

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-success/10">
              <Building2 className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.active}</p>
              <p className="text-sm text-muted-foreground">Active Customers</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/10">
              <Users className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.prospects}</p>
              <p className="text-sm text-muted-foreground">Prospects</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <DollarSign className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">{formatCurrency(stats.totalRevenue)}</p>
              <p className="text-sm text-muted-foreground">Total Revenue</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-secondary/50">
              <TrendingUp className="h-5 w-5 text-foreground" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.avgWinRate.toFixed(0)}%</p>
              <p className="text-sm text-muted-foreground">Avg. Win Rate</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function CustomerCard({ customer }: { customer: Customer }) {
  const router = useRouter();
  const config = statusConfig[customer.status];

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
            <span>{customer.location.city}, {customer.location.state}</span>
          </div>
          {customer.primaryContact && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Users className="h-4 w-4" />
              <span>{customer.primaryContact.name}</span>
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t grid grid-cols-3 gap-2 text-center">
          <div>
            <p className="text-lg font-bold">{customer.stats.totalRFQs}</p>
            <p className="text-xs text-muted-foreground">RFQs</p>
          </div>
          <div>
            <p className="text-lg font-bold">{formatCurrency(customer.stats.totalRevenue, 'MAD', 'fr-MA').replace(/,00/g, '')}</p>
            <p className="text-xs text-muted-foreground">Revenue</p>
          </div>
          <div>
            <p className={cn(
              'text-lg font-bold',
              customer.stats.winRate >= 70 ? 'text-success' : 
              customer.stats.winRate >= 50 ? 'text-warning' : 'text-muted-foreground'
            )}>
              {customer.stats.winRate}%
            </p>
            <p className="text-xs text-muted-foreground">Win Rate</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CustomerRow({ customer }: { customer: Customer }) {
  const router = useRouter();
  const config = statusConfig[customer.status];

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
        {customer.location.city}, {customer.location.state}
      </td>
      <td className="py-3 px-4">
        {customer.primaryContact ? (
          <div className="text-sm">
            <p>{customer.primaryContact.name}</p>
            <p className="text-muted-foreground">{customer.primaryContact.email}</p>
          </div>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td className="py-3 px-4 text-center">{customer.stats.totalRFQs}</td>
      <td className="py-3 px-4 text-right font-medium">
        {formatCurrency(customer.stats.totalRevenue)}
      </td>
      <td className="py-3 px-4 text-center">
        <span className={cn(
          'font-medium',
          customer.stats.winRate >= 70 ? 'text-success' : 
          customer.stats.winRate >= 50 ? 'text-warning' : 'text-muted-foreground'
        )}>
          {customer.stats.winRate > 0 ? `${customer.stats.winRate}%` : '—'}
        </span>
      </td>
      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push(`/customers/${customer.id}`)}>
              <Eye className="mr-2 h-4 w-4" />
              View
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/customers/${customer.id}/edit`)}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push(`/pipeline/new?customer=${customer.id}`)}>
              <FileText className="mr-2 h-4 w-4" />
              Create RFQ
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {customer.status === 'active' ? (
              <DropdownMenuItem className="text-warning">
                <Archive className="mr-2 h-4 w-4" />
                Deactivate
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem className="text-success">
                <Building2 className="mr-2 h-4 w-4" />
                Activate
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

export default function CustomersPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [industryFilter, setIndustryFilter] = React.useState<string>('all');
  const [viewMode, setViewMode] = React.useState<'grid' | 'list'>('grid');

  const industries = React.useMemo(() => {
    return [...new Set(mockCustomers.map((c) => c.industry))];
  }, []);

  const filteredCustomers = React.useMemo(() => {
    return mockCustomers.filter((customer) => {
      const matchesSearch = searchQuery === '' ||
        customer.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        customer.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
        customer.primaryContact?.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'all' || customer.status === statusFilter;
      const matchesIndustry = industryFilter === 'all' || customer.industry === industryFilter;
      return matchesSearch && matchesStatus && matchesIndustry;
    });
  }, [searchQuery, statusFilter, industryFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Customers</h1>
          <p className="text-muted-foreground">Manage customer relationships and track activity</p>
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem>Export as CSV</DropdownMenuItem>
              <DropdownMenuItem>Export as Excel</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="outline">
            <Upload className="mr-2 h-4 w-4" />
            Import
          </Button>
          <Button onClick={() => router.push('/customers/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Add Customer
          </Button>
        </div>
      </div>

      {/* Stats */}
      <CustomerStats customers={mockCustomers} />

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
                    <SelectItem key={industry} value={industry}>{industry}</SelectItem>
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
      {viewMode === 'grid' ? (
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

      {filteredCustomers.length === 0 && (
        <div className="text-center py-12">
          <Building2 className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-medium">No customers found</h3>
          <p className="text-muted-foreground">
            {searchQuery || statusFilter !== 'all' || industryFilter !== 'all'
              ? 'Try adjusting your filters'
              : 'Add your first customer to get started'}
          </p>
          {!searchQuery && statusFilter === 'all' && industryFilter === 'all' && (
            <Button className="mt-4" onClick={() => router.push('/customers/new')}>
              <Plus className="mr-2 h-4 w-4" />
              Add Customer
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
