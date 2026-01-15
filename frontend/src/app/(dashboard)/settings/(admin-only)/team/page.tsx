'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores';
import {
  ArrowLeft,
  Plus,
  Search,
  MoreHorizontal,
  Mail,
  Shield,
  UserPlus,
  Users,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Edit,
  Trash2,
  Key,
  Ban,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge, BadgeProps } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn, formatDate, getInitials } from '@/lib/utils';

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'manager' | 'user' | 'viewer';
  department: string;
  status: 'active' | 'invited' | 'disabled';
  lastActive?: string;
  invitedAt?: string;
}

const mockMembers: TeamMember[] = [
  { id: '1', name: 'John Doe', email: 'john.doe@sensei.ma', role: 'admin', department: 'Management', status: 'active', lastActive: '2024-01-15T14:30:00Z' },
  { id: '2', name: 'Sarah Chen', email: 'sarah.chen@sensei.ma', role: 'manager', department: 'Quality', status: 'active', lastActive: '2024-01-15T12:45:00Z' },
  { id: '3', name: 'Maria Garcia', email: 'maria.garcia@sensei.ma', role: 'user', department: 'Production', status: 'active', lastActive: '2024-01-14T18:20:00Z' },
  { id: '4', name: 'David Lee', email: 'david.lee@sensei.ma', role: 'user', department: 'Engineering', status: 'active', lastActive: '2024-01-15T09:00:00Z' },
  { id: '5', name: 'Emily Rodriguez', email: 'emily.r@sensei.ma', role: 'viewer', department: 'Sales', status: 'invited', invitedAt: '2024-01-10T10:00:00Z' },
  { id: '6', name: 'Michael Brown', email: 'mbrown@sensei.ma', role: 'user', department: 'Warehouse', status: 'disabled' },
];

const roleConfig: Record<TeamMember['role'], { label: string; variant: BadgeProps['variant']; description: string }> = {
  admin: { label: 'Admin', variant: 'danger', description: 'Full access to all features and settings' },
  manager: { label: 'Manager', variant: 'warning', description: 'Can manage team and approve workflows' },
  user: { label: 'User', variant: 'default', description: 'Standard access to assigned features' },
  viewer: { label: 'Viewer', variant: 'secondary', description: 'Read-only access' },
};

const statusConfig: Record<TeamMember['status'], { label: string; variant: BadgeProps['variant']; icon: typeof CheckCircle }> = {
  active: { label: 'Active', variant: 'success', icon: CheckCircle },
  invited: { label: 'Invited', variant: 'warning', icon: Clock },
  disabled: { label: 'Disabled', variant: 'secondary', icon: Ban },
};

function InviteDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [email, setEmail] = React.useState('');
  const [role, setRole] = React.useState<TeamMember['role']>('user');
  const [department, setDepartment] = React.useState('');

  const handleInvite = () => {
    // Would send invitation via API
    onOpenChange(false);
    setEmail('');
    setRole('user');
    setDepartment('');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invite Team Member</DialogTitle>
          <DialogDescription>
            Send an invitation to join your organization
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              placeholder="colleague@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Select value={role} onValueChange={(v) => setRole(v as TeamMember['role'])}>
              <SelectTrigger id="role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(roleConfig).map(([key, cfg]) => (
                  <SelectItem key={key} value={key}>
                    <div className="flex items-center gap-2">
                      <Badge variant={cfg.variant} size="sm">{cfg.label}</Badge>
                      <span className="text-xs text-muted-foreground">{cfg.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="department">Department</Label>
            <Select value={department} onValueChange={setDepartment}>
              <SelectTrigger id="department">
                <SelectValue placeholder="Select department" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Management">Management</SelectItem>
                <SelectItem value="Engineering">Engineering</SelectItem>
                <SelectItem value="Production">Production</SelectItem>
                <SelectItem value="Quality">Quality</SelectItem>
                <SelectItem value="Sales">Sales</SelectItem>
                <SelectItem value="Warehouse">Warehouse</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleInvite} disabled={!email}>
            <Mail className="mr-2 h-4 w-4" />
            Send Invitation
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MemberRow({ member }: { member: TeamMember }) {
  const roleCfg = roleConfig[member.role];
  const statusCfg = statusConfig[member.status];
  const StatusIcon = statusCfg.icon;

  return (
    <tr className="border-b last:border-0 hover:bg-muted/50">
      <td className="p-3">
        <div className="flex items-center gap-3">
          <Avatar>
            <AvatarFallback>{getInitials(member.name)}</AvatarFallback>
          </Avatar>
          <div>
            <p className="font-medium">{member.name}</p>
            <p className="text-sm text-muted-foreground">{member.email}</p>
          </div>
        </div>
      </td>
      <td className="p-3">
        <Badge variant={roleCfg.variant} size="sm">{roleCfg.label}</Badge>
      </td>
      <td className="p-3 text-sm">{member.department}</td>
      <td className="p-3">
        <Badge variant={statusCfg.variant} size="sm" className="gap-1">
          <StatusIcon className="h-3 w-3" />
          {statusCfg.label}
        </Badge>
      </td>
      <td className="p-3 text-sm text-muted-foreground">
        {member.lastActive 
          ? formatDate(new Date(member.lastActive), { month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric' })
          : member.invitedAt 
            ? `Invited ${formatDate(new Date(member.invitedAt), { month: 'short', day: 'numeric' })}`
            : '—'}
      </td>
      <td className="p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Key className="mr-2 h-4 w-4" />
              Change Role
            </DropdownMenuItem>
            {member.status === 'invited' && (
              <DropdownMenuItem>
                <RefreshCw className="mr-2 h-4 w-4" />
                Resend Invitation
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            {member.status === 'active' ? (
              <DropdownMenuItem className="text-warning">
                <Ban className="mr-2 h-4 w-4" />
                Disable Account
              </DropdownMenuItem>
            ) : member.status === 'disabled' ? (
              <DropdownMenuItem className="text-success">
                <CheckCircle className="mr-2 h-4 w-4" />
                Re-enable Account
              </DropdownMenuItem>
            ) : null}
            <DropdownMenuItem className="text-danger">
              <Trash2 className="mr-2 h-4 w-4" />
              Remove
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

export default function TeamSettingsPage() {
  const router = useRouter();
  const [search, setSearch] = React.useState('');
  const [roleFilter, setRoleFilter] = React.useState('all');
  const [statusFilter, setStatusFilter] = React.useState('all');
  const [inviteOpen, setInviteOpen] = React.useState(false);

  const filtered = mockMembers.filter(member => {
    if (search && !member.name.toLowerCase().includes(search.toLowerCase()) && 
        !member.email.toLowerCase().includes(search.toLowerCase())) return false;
    if (roleFilter !== 'all' && member.role !== roleFilter) return false;
    if (statusFilter !== 'all' && member.status !== statusFilter) return false;
    return true;
  });

  const activeCount = mockMembers.filter(m => m.status === 'active').length;
  const invitedCount = mockMembers.filter(m => m.status === 'invited').length;

  return (
    <div className="space-y-8 page-fade-in max-w-5xl">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 hover:text-primary transition-all" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              Personnel Directory
            </h1>
            <p className="text-muted-foreground font-medium text-sm">Manage organizational hierarchy, access layers, and identity nodes</p>
          </div>
        </div>
        <Button onClick={() => setInviteOpen(true)} className="rounded-2xl shadow-glow subtle-shine h-12 px-8" size="lg">
          <UserPlus className="mr-2 h-5 w-5" />
          Invite Protocol
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-6 sm:grid-cols-3">
        <Card className="hover:border-primary/20 transition-colors">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="p-3 bg-primary/10 rounded-2xl shadow-sm">
              <Users className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">{mockMembers.length}</p>
              <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-muted-foreground/60">Total Intelligence Nodes</p>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:border-success/20 transition-colors">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="p-3 bg-success/10 rounded-2xl shadow-sm">
              <CheckCircle className="h-6 w-6 text-success" />
            </div>
            <div>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-success to-success/70">{activeCount}</p>
              <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-muted-foreground/60">Active Operatives</p>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:border-warning/20 transition-colors">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="p-3 bg-warning/10 rounded-2xl shadow-sm">
              <Clock className="h-6 w-6 text-warning" />
            </div>
            <div>
              <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-warning to-warning/70">{invitedCount}</p>
              <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-muted-foreground/60">Pending Sync</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters & Table */}
      <Card className="overflow-hidden">
        <CardHeader className="border-b border-border/40 bg-muted/5 p-6">
          <div className="flex flex-col lg:flex-row gap-6">
            <div className="relative flex-1 group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40 group-focus-within:text-primary transition-colors" />
              <Input
                placeholder="Search operatives by name or intelligence tag..."
                className="pl-11 h-12 bg-background/50 border-border/50"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex flex-wrap gap-3">
              <Select value={roleFilter} onValueChange={setRoleFilter}>
                <SelectTrigger className="w-40 h-12 rounded-xl bg-background border-border/50">
                  <SelectValue placeholder="Access Role" />
                </SelectTrigger>
                <SelectContent className="rounded-2xl shadow-premium">
                  <SelectItem value="all" className="rounded-xl m-1">All Roles</SelectItem>
                  {Object.entries(roleConfig).map(([key, cfg]) => (
                    <SelectItem key={key} value={key} className="rounded-xl m-1">{cfg.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-40 h-12 rounded-xl bg-background border-border/50">
                  <SelectValue placeholder="Node Status" />
                </SelectTrigger>
                <SelectContent className="rounded-2xl shadow-premium">
                  <SelectItem value="all" className="rounded-xl m-1">All Status</SelectItem>
                  {Object.entries(statusConfig).map(([key, cfg]) => (
                    <SelectItem key={key} value={key} className="rounded-xl m-1">{cfg.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th>Operative Identity</th>
                  <th>Access Authorization</th>
                  <th>Department Node</th>
                  <th>Sync Status</th>
                  <th>Last Pulse</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((member) => (
                  <MemberRow key={member.id} member={member} />
                ))}
              </tbody>
            </table>
          </div>
          {filtered.length === 0 && (
            <div className="text-center py-20 bg-muted/5">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-[2rem] bg-muted mb-6 shadow-inner-soft">
                <Users className="h-10 w-10 text-muted-foreground/30" />
              </div>
              <p className="text-sm font-heading font-bold text-muted-foreground/60 tracking-tight">No operatives identified within current search parameters</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Roles Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading flex items-center gap-3">
            <Shield className="h-5 w-5 text-primary/60" />
            Access Layer Definitions
          </CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Parameters for organizational permission nodes</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(roleConfig).map(([key, cfg]) => (
              <div key={key} className="p-5 rounded-2xl border border-border/40 bg-muted/30 group hover:border-primary/20 transition-all">
                <Badge variant={cfg.variant} size="lg" className="mb-4">{cfg.label}</Badge>
                <p className="text-xs font-medium text-muted-foreground/80 leading-relaxed">{cfg.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <InviteDialog open={inviteOpen} onOpenChange={setInviteOpen} />
    </div>
  );
}
