'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Shield,
  Key,
  Smartphone,
  Monitor,
  Lock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Globe,
  Clock,
  LogOut,
  Save,
  Loader2,
  Eye,
  EyeOff,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { cn, formatDate } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

interface Session {
  id: string;
  device: string;
  browser: string;
  location: string;
  ip: string;
  lastActive: string;
  isCurrent: boolean;
}

interface LoginActivity {
  id: string;
  action: 'login_success' | 'login_failed' | 'logout' | 'password_changed' | '2fa_enabled';
  device: string;
  location: string;
  ip: string;
  timestamp: string;
}

const mockSessions: Session[] = [
  { id: '1', device: 'Desktop', browser: 'Chrome 120', location: 'Casablanca, Morocco', ip: '196.200.x.x', lastActive: '2024-01-15T14:30:00Z', isCurrent: true },
  { id: '2', device: 'Mobile', browser: 'Safari 17', location: 'Casablanca, Morocco', ip: '196.200.x.x', lastActive: '2024-01-14T18:00:00Z', isCurrent: false },
  { id: '3', device: 'Desktop', browser: 'Firefox 121', location: 'Paris, France', ip: '90.120.x.x', lastActive: '2024-01-10T10:00:00Z', isCurrent: false },
];

const mockActivity: LoginActivity[] = [
  { id: '1', action: 'login_success', device: 'Chrome on Windows', location: 'Casablanca, Morocco', ip: '196.200.x.x', timestamp: '2024-01-15T09:00:00Z' },
  { id: '2', action: 'password_changed', device: 'Chrome on Windows', location: 'Casablanca, Morocco', ip: '196.200.x.x', timestamp: '2024-01-12T14:30:00Z' },
  { id: '3', action: 'login_failed', device: 'Unknown', location: 'Unknown', ip: '45.33.x.x', timestamp: '2024-01-11T23:45:00Z' },
  { id: '4', action: '2fa_enabled', device: 'Chrome on Windows', location: 'Casablanca, Morocco', ip: '196.200.x.x', timestamp: '2024-01-10T11:00:00Z' },
  { id: '5', action: 'login_success', device: 'Safari on iPhone', location: 'Casablanca, Morocco', ip: '196.200.x.x', timestamp: '2024-01-09T08:30:00Z' },
];

const activityConfig = {
  login_success: { label: 'Successful login', icon: CheckCircle, color: 'text-success' },
  login_failed: { label: 'Failed login attempt', icon: XCircle, color: 'text-danger' },
  logout: { label: 'Logged out', icon: LogOut, color: 'text-muted-foreground' },
  password_changed: { label: 'Password changed', icon: Key, color: 'text-warning' },
  '2fa_enabled': { label: '2FA enabled', icon: Shield, color: 'text-success' },
};

function ChangePasswordDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [currentPassword, setCurrentPassword] = React.useState('');
  const [newPassword, setNewPassword] = React.useState('');
  const [confirmPassword, setConfirmPassword] = React.useState('');
  const [showPasswords, setShowPasswords] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);

  const passwordsMatch = newPassword === confirmPassword;
  const isStrongPassword = newPassword.length >= 8 && /[A-Z]/.test(newPassword) && /[0-9]/.test(newPassword);

  const handleSubmit = async () => {
    if (!passwordsMatch || !isStrongPassword) return;
    setIsLoading(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsLoading(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change Password</DialogTitle>
          <DialogDescription>
            Enter your current password and a new password
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="currentPassword">Current Password</Label>
            <div className="relative">
              <Input
                id="currentPassword"
                type={showPasswords ? 'text' : 'password'}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="newPassword">New Password</Label>
            <div className="relative">
              <Input
                id="newPassword"
                type={showPasswords ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            {newPassword && !isStrongPassword && (
              <p className="text-xs text-danger">Password must be at least 8 characters with uppercase and number</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm New Password</Label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showPasswords ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>
            {confirmPassword && !passwordsMatch && (
              <p className="text-xs text-danger">Passwords do not match</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowPasswords(!showPasswords)}
              className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              {showPasswords ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              {showPasswords ? 'Hide' : 'Show'} passwords
            </button>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button 
            onClick={handleSubmit} 
            disabled={!currentPassword || !passwordsMatch || !isStrongPassword || isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Changing...
              </>
            ) : (
              'Change Password'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function SecuritySettingsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [is2FAEnabled, setIs2FAEnabled] = React.useState(true);
  const [passwordDialogOpen, setPasswordDialogOpen] = React.useState(false);
  const [revokeDialogOpen, setRevokeDialogOpen] = React.useState(false);
  const [selectedSession, setSelectedSession] = React.useState<Session | null>(null);

  const handleRevokeSession = (session: Session) => {
    setSelectedSession(session);
    setRevokeDialogOpen(true);
  };

  const confirmRevokeSession = () => {
    // Would revoke session via API
    setRevokeDialogOpen(false);
    setSelectedSession(null);
  };

  return (
    <div className="space-y-8 page-fade-in max-w-4xl">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 hover:text-primary transition-all" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-3xl font-heading font-bold tracking-tight ">
              Security Protocol
            </h1>
            <p className="text-muted-foreground font-medium text-sm">Manage authentication layers and active organizational sessions</p>
          </div>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Password */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <Key className="h-5 w-5 text-primary/60" />
              Authentication
            </CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Access credentials and encryption keys</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="p-5 rounded-2xl bg-muted/30 border border-border/40 flex items-center justify-between">
              <div>
                <p className="font-heading font-bold text-sm tracking-tight">Access Password</p>
                <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">Last rotated 3 days ago</p>
              </div>
              <Button variant="outline" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary" onClick={() => setPasswordDialogOpen(true)}>
                Update Keys
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Two-Factor Authentication */}
        <Card className={cn("lg:col-span-1", is2FAEnabled ? 'border-success/20 bg-success/[0.02]' : 'border-warning/20 bg-warning/[0.02]')}>
          <CardHeader>
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <Smartphone className="h-5 w-5 text-primary/60" />
              Verification Layer
              {is2FAEnabled ? (
                <Badge variant="success" size="sm" className="ml-auto">Active</Badge>
              ) : (
                <Badge variant="warning" size="sm" className="ml-auto">At Risk</Badge>
              )}
            </CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Multi-factor identity synchronization</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-5 rounded-2xl bg-background/50 border border-border/40 flex items-center justify-between">
              <div className="flex-1">
                <p className="font-heading font-bold text-sm tracking-tight">Authenticator Protocol</p>
                <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">
                  {is2FAEnabled 
                    ? 'Synchronized with external token generator'
                    : 'Enable 2FA for industrial-grade security'}
                </p>
              </div>
              <Switch 
                checked={is2FAEnabled} 
                onCheckedChange={setIs2FAEnabled}
                className="data-[state=checked]:bg-success"
              />
            </div>
          </CardContent>
        </Card>

        {/* Active Sessions */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <Monitor className="h-5 w-5 text-primary/60" />
              Active Intelligence Nodes
            </CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Authorized devices currently connected to the OS</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-0">
            {mockSessions.map((session) => (
              <div 
                key={session.id} 
                className={cn(
                  'flex items-center justify-between p-5 rounded-2xl border transition-all duration-300 group',
                  session.isCurrent ? 'border-primary/30 bg-primary/5 shadow-sm' : 'border-border/40 hover:border-primary/20'
                )}
              >
                <div className="flex items-center gap-5">
                  <div className={cn('p-3 rounded-xl shadow-inner-soft transition-transform duration-500 group-hover:scale-110', session.isCurrent ? 'bg-primary text-primary-foreground shadow-glow' : 'bg-muted text-muted-foreground')}>
                    {session.device === 'Mobile' ? (
                      <Smartphone className="h-5 w-5" />
                    ) : (
                      <Monitor className="h-5 w-5" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-3">
                      <p className="font-heading font-bold text-sm tracking-tight">{session.browser}</p>
                      {session.isCurrent && (
                        <Badge variant="success" size="sm">Primary Node</Badge>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1">
                      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
                        <Globe className="h-3 w-3" />
                        {session.location} • {session.ip}
                      </div>
                      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
                        <Clock className="h-3 w-3" />
                        Last Activity: {formatDate(new Date(session.lastActive), { month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric' })}
                      </div>
                    </div>
                  </div>
                </div>
                {!session.isCurrent && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-danger hover:text-danger hover:bg-danger/10 rounded-xl px-4"
                    onClick={() => handleRevokeSession(session)}
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    De-authorize
                  </Button>
                )}
              </div>
            ))}
            <div className="pt-4">
              <Button variant="outline" className="w-full h-12 text-danger hover:text-danger hover:bg-danger/5 border-danger/20 rounded-xl font-heading">
                <LogOut className="mr-2 h-4 w-4" />
                Terminate All Remote Sessions
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Login Activity */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg font-heading flex items-center gap-3">
              <Shield className="h-5 w-5 text-primary/60" />
              Event Telemetry
            </CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Historical log of security-related events</CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-2">
              {mockActivity.map((activity) => {
                const config = activityConfig[activity.action];
                const Icon = config.icon;
                return (
                  <div key={activity.id} className="flex items-center gap-5 p-4 rounded-xl hover:bg-muted/30 transition-colors border-b border-border/10 last:border-0">
                    <div className={cn('p-2.5 rounded-lg shadow-sm', config.color, 'bg-background')}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <p className="font-heading font-bold text-sm tracking-tight">{config.label}</p>
                      <div className="flex items-center gap-3 mt-0.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
                        <span>{activity.device}</span>
                        <span>•</span>
                        <span>{activity.location}</span>
                      </div>
                    </div>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">
                      {formatDate(new Date(activity.timestamp), { month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric' })}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Security Recommendations */}
      <Card className="border-warning/20 bg-warning/[0.02]">
        <CardHeader>
          <CardTitle className="text-lg font-heading flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-warning" />
            Security Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 p-4 rounded-xl bg-background/50 border border-border/40">
            <div className="p-2 rounded-lg bg-success/10 text-success">
              <CheckCircle className="h-5 w-5" />
            </div>
            <span className="text-sm font-medium">Two-factor authentication is active and synchronized</span>
          </div>
          <div className="flex items-center gap-4 p-4 rounded-xl bg-background/50 border border-border/40">
            <div className="p-2 rounded-lg bg-success/10 text-success">
              <CheckCircle className="h-5 w-5" />
            </div>
            <span className="text-sm font-medium">Identity credentials rotated within recommended threshold</span>
          </div>
          <div className="flex items-center gap-4 p-4 rounded-xl bg-background/50 border border-border/40">
            <div className="p-2 rounded-lg bg-warning/10 text-warning">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <span className="text-sm font-medium">Consider terminating legacy sessions to minimize surface area</span>
          </div>
        </CardContent>
      </Card>

      <ChangePasswordDialog 
        open={passwordDialogOpen} 
        onOpenChange={setPasswordDialogOpen} 
      />

      <AlertDialog open={revokeDialogOpen} onOpenChange={setRevokeDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke Session</AlertDialogTitle>
            <AlertDialogDescription>
              This will sign out the device in {selectedSession?.location}. Are you sure?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmRevokeSession} className="bg-danger text-danger-foreground hover:bg-danger/90">
              Revoke Session
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
