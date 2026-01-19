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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn, formatDate, getInitials } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

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

const roleConfig: Record<TeamMember['role'], { labelKey: string; variant: BadgeProps['variant']; descriptionKey: string }> = {
  admin: { labelKey: 'settings.team.roles.admin', variant: 'danger', descriptionKey: 'settings.team.roles.adminDesc' },
  manager: { labelKey: 'settings.team.roles.manager', variant: 'warning', descriptionKey: 'settings.team.roles.managerDesc' },
  user: { labelKey: 'settings.team.roles.user', variant: 'default', descriptionKey: 'settings.team.roles.userDesc' },
  viewer: { labelKey: 'settings.team.roles.viewer', variant: 'secondary', descriptionKey: 'settings.team.roles.viewerDesc' },
};

const statusConfig: Record<TeamMember['status'], { labelKey: string; variant: BadgeProps['variant']; icon: typeof CheckCircle }> = {
  active: { labelKey: 'settings.team.status.active', variant: 'success', icon: CheckCircle },
  invited: { labelKey: 'settings.team.status.invited', variant: 'warning', icon: Clock },
  disabled: { labelKey: 'settings.team.status.disabled', variant: 'secondary', icon: Ban },
};

function InviteDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { t } = useI18n();
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
          <DialogTitle>{t('settings.team.inviteDialog.title')}</DialogTitle>
          <DialogDescription>{t('settings.team.inviteDialog.description')}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="email">{t('settings.team.inviteDialog.emailLabel')}</Label>
            <Input
              id="email"
              type="email"
              placeholder={t('settings.team.inviteDialog.emailPlaceholder')}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="role">{t('settings.team.inviteDialog.roleLabel')}</Label>
            <Select value={role} onValueChange={(v) => setRole(v as TeamMember['role'])}>
              <SelectTrigger id="role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(roleConfig).map(([key, cfg]) => (
                  <SelectItem key={key} value={key}>
                    <div className="flex items-center gap-2">
                      <Badge variant={cfg.variant} size="sm">{t(cfg.labelKey)}</Badge>
                      <span className="text-xs text-muted-foreground">{t(cfg.descriptionKey)}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="department">{t('settings.team.inviteDialog.departmentLabel')}</Label>
            <Select value={department} onValueChange={setDepartment}>
              <SelectTrigger id="department">
                <SelectValue placeholder={t('settings.team.inviteDialog.departmentPlaceholder')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Management">{t('settings.team.departments.management')}</SelectItem>
                <SelectItem value="Engineering">{t('settings.team.departments.engineering')}</SelectItem>
                <SelectItem value="Production">{t('settings.team.departments.production')}</SelectItem>
                <SelectItem value="Quality">{t('settings.team.departments.quality')}</SelectItem>
                <SelectItem value="Sales">{t('settings.team.departments.sales')}</SelectItem>
                <SelectItem value="Warehouse">{t('settings.team.departments.warehouse')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
          <Button onClick={handleInvite} disabled={!email}>
            <Mail className="mr-2 h-4 w-4" />
            {t('settings.team.inviteDialog.sendInvitation')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MemberRow({ member }: { member: TeamMember }) {
  const { t } = useI18n();
  const roleCfg = roleConfig[member.role];
  const statusCfg = statusConfig[member.status];
  const StatusIcon = statusCfg.icon;

  return (
    <TableRow className="transition-none cursor-help group">
      <TableCell>
        <div className="flex items-center gap-4">
          <Avatar className="h-9 w-9 rounded-none border border-rams-line">
            <AvatarFallback className="bg-rams-panel text-muted-foreground/40 font-mono font-black text-xs">{getInitials(member.name)}</AvatarFallback>
          </Avatar>
          <div>
            <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{member.name}</p>
            <p className="text-[9px] font-mono font-bold text-muted-foreground/40 lowercase">{member.email}</p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant={roleCfg.variant} size="sm">{t(roleCfg.labelKey).toUpperCase()}</Badge>
      </TableCell>
      <TableCell className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">{member.department}</TableCell>
      <TableCell>
        <Badge variant={statusCfg.variant} size="sm" className="gap-1.5 h-4 px-1 rounded-none font-black text-[8px] uppercase tracking-widest">
          <StatusIcon className="h-2.5 w-2.5" />
          {t(statusCfg.labelKey)}
        </Badge>
      </TableCell>
      <TableCell className="text-[10px] font-mono font-bold text-muted-foreground/40 uppercase">
        {member.lastActive 
          ? formatDate(new Date(member.lastActive)).toUpperCase()
          : member.invitedAt 
            ? t('settings.team.invitedAt', { date: formatDate(new Date(member.invitedAt)).toUpperCase() })
            : t('settings.team.valueUnavailable')}
      </TableCell>
      <TableCell onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-rams-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Edit className="mr-2 h-3.5 w-3.5" /> {t('settings.team.actions.refineNode')}
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Key className="mr-2 h-3.5 w-3.5" /> {t('settings.team.actions.rotateRole')}
            </DropdownMenuItem>
            {member.status === 'invited' && (
              <DropdownMenuItem>
                <RefreshCw className="mr-2 h-3.5 w-3.5" /> {t('settings.team.actions.resendSync')}
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            {member.status === 'active' ? (
              <DropdownMenuItem className="text-rams-red">
                <Ban className="mr-2 h-3.5 w-3.5" /> {t('settings.team.actions.deauthorize')}
              </DropdownMenuItem>
            ) : member.status === 'disabled' ? (
              <DropdownMenuItem className="text-rams-green">
                <CheckCircle className="mr-2 h-3.5 w-3.5" /> {t('settings.team.actions.reauthorize')}
              </DropdownMenuItem>
            ) : null}
            <DropdownMenuItem className="text-rams-red">
              <Trash2 className="mr-2 h-3.5 w-3.5" /> {t('settings.team.actions.terminateProtocol')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

export default function TeamSettingsPage() {
  const { t } = useI18n();
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
    <div className="space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              {t('settings.team.title')}
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">{t('settings.team.subtitle')}</p>
          </div>
        </div>
        <Button onClick={() => setInviteOpen(true)} size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
          <UserPlus className="mr-2 h-3.5 w-3.5" />
          {t('settings.team.inviteProtocol')}
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-0 sm:grid-cols-3 border border-rams-line bg-rams-line">
        <div className="bg-rams-module p-6 border-r group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('settings.team.intelligenceNodes')}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-foreground/90 tabular-nums">{mockMembers.length}</div>
          <p className="text-[9px] font-mono font-bold text-muted-foreground/40 uppercase tracking-widest mt-2">{t('settings.team.totalRegistry')}</p>
        </div>
        <div className="bg-rams-module p-6 border-r group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('settings.team.activeOperatives')}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-green tabular-nums">{activeCount}</div>
          <p className="text-[9px] font-mono font-bold text-rams-green uppercase tracking-widest mt-2">{t('settings.team.pulseNominal')}</p>
        </div>
        <div className="bg-rams-module p-6 group hover:bg-rams-panel transition-none cursor-help">
          <p className="text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/50 mb-4">{t('settings.team.pendingSync')}</p>
          <div className="text-3xl font-mono font-bold tracking-tight text-rams-orange tabular-nums">{invitedCount}</div>
          <p className="text-[9px] font-mono font-bold text-rams-orange uppercase tracking-widest mt-2">{t('settings.team.waitingForGate')}</p>
        </div>
      </div>

      {/* Filters & Table */}
      <Card className="rounded-rams-sm overflow-hidden border-rams-line shadow-none">
        <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
          <div className="flex flex-col lg:flex-row gap-6">
            <div className="relative flex-1 group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 transition-colors group-focus-within:text-rams-orange" />
              <Input
                placeholder={t('settings.team.searchPlaceholder')}
                className="pl-10 h-10 text-[10px] bg-rams-panel"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex flex-wrap gap-1 bg-rams-panel p-1 border border-rams-line rounded-none">
              <Select value={roleFilter} onValueChange={setRoleFilter}>
                <SelectTrigger className="w-36 h-8 rounded-none border-none bg-transparent text-[9px] font-black uppercase tracking-widest">
                  <SelectValue placeholder={t('settings.team.filters.role')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('settings.team.filters.allRoles')}</SelectItem>
                  {Object.entries(roleConfig).map(([key, cfg]) => (
                    <SelectItem key={key} value={key}>{t(cfg.labelKey).toUpperCase()}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="w-px bg-rams-line/30" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-36 h-8 rounded-none border-none bg-transparent text-[9px] font-black uppercase tracking-widest">
                  <SelectValue placeholder={t('settings.team.filters.status')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('settings.team.filters.allStatus')}</SelectItem>
                  {Object.entries(statusConfig).map(([key, cfg]) => (
                    <SelectItem key={key} value={key}>{t(cfg.labelKey).toUpperCase()}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('settings.team.table.operativeIdentity')}</TableHead>
                  <TableHead>{t('settings.team.table.accessLayer')}</TableHead>
                  <TableHead>{t('settings.team.table.departmentNode')}</TableHead>
                  <TableHead>{t('settings.team.table.syncStatus')}</TableHead>
                  <TableHead>{t('settings.team.table.lastPulse')}</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((member) => (
                  <MemberRow key={member.id} member={member} />
                ))}
              </TableBody>
            </Table>
          </div>
          {filtered.length === 0 && (
            <div className="text-center py-24 bg-rams-module relative overflow-hidden">
              <Users className="h-12 w-12 text-muted-foreground/20 mx-auto mb-4 relative z-10" />
              <p className="text-[11px] font-black uppercase tracking-tight text-foreground/60 relative z-10">{t('settings.team.zeroOperativesIdentified')}</p>
              <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Roles Grid */}
      <div className="grid gap-px border border-rams-line bg-rams-line sm:grid-cols-2 lg:grid-cols-4">
        {Object.entries(roleConfig).map(([key, cfg]) => (
          <div key={key} className="p-6 bg-rams-module hover:bg-rams-panel transition-none group cursor-help">
            <Badge variant={cfg.variant} size="sm" className="mb-4 h-4 px-1 rounded-none text-[8px] font-black uppercase tracking-widest">{cfg.label.toUpperCase()}</Badge>
            <p className="text-[10px] font-medium text-muted-foreground/60 leading-relaxed uppercase">{cfg.description}</p>
          </div>
        ))}
      </div>

      <InviteDialog open={inviteOpen} onOpenChange={setInviteOpen} />
    </div>
  );
}
