'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
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
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push('/settings')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Team Members</h1>
          <p className="text-muted-foreground">Manage users and their access</p>
        </div>
        <Button onClick={() => setInviteOpen(true)}>
          <UserPlus className="mr-2 h-4 w-4" />
          Invite Member
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Users className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">{mockMembers.length}</p>
              <p className="text-sm text-muted-foreground">Total Members</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-success/10 rounded-lg">
              <CheckCircle className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold">{activeCount}</p>
              <p className="text-sm text-muted-foreground">Active Users</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-warning/10 rounded-lg">
              <Clock className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold">{invitedCount}</p>
              <p className="text-sm text-muted-foreground">Pending Invitations</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters & Table */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search members..."
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                {Object.entries(roleConfig).map(([key, cfg]) => (
                  <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                {Object.entries(statusConfig).map(([key, cfg]) => (
                  <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left p-3 font-medium text-sm">Member</th>
                  <th className="text-left p-3 font-medium text-sm">Role</th>
                  <th className="text-left p-3 font-medium text-sm">Department</th>
                  <th className="text-left p-3 font-medium text-sm">Status</th>
                  <th className="text-left p-3 font-medium text-sm">Last Active</th>
                  <th className="p-3 w-10"></th>
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
            <div className="text-center py-12 text-muted-foreground">
              <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No members found</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Roles Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Role Permissions
          </CardTitle>
          <CardDescription>Overview of what each role can do</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(roleConfig).map(([key, cfg]) => (
              <div key={key} className="p-3 border rounded-lg">
                <Badge variant={cfg.variant} size="sm" className="mb-2">{cfg.label}</Badge>
                <p className="text-sm text-muted-foreground">{cfg.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <InviteDialog open={inviteOpen} onOpenChange={setInviteOpen} />
    </div>
  );
}
