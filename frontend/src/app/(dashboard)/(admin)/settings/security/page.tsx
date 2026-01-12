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
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push('/settings')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Security</h1>
          <p className="text-muted-foreground">Manage your security settings and sessions</p>
        </div>
      </div>

      {/* Password */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Key className="h-4 w-4" />
            Password
          </CardTitle>
          <CardDescription>Manage your password</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-sm">Password</p>
              <p className="text-xs text-muted-foreground">Last changed 3 days ago</p>
            </div>
            <Button variant="outline" onClick={() => setPasswordDialogOpen(true)}>
              Change Password
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Two-Factor Authentication */}
      <Card className={cn(is2FAEnabled ? 'border-success/50' : 'border-warning/50')}>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Smartphone className="h-4 w-4" />
            Two-Factor Authentication
            {is2FAEnabled ? (
              <Badge variant="success" size="sm" className="ml-2">Enabled</Badge>
            ) : (
              <Badge variant="warning" size="sm" className="ml-2">Disabled</Badge>
            )}
          </CardTitle>
          <CardDescription>Add an extra layer of security to your account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-sm">Authenticator App</p>
              <p className="text-xs text-muted-foreground">
                {is2FAEnabled 
                  ? 'Use your authenticator app to generate one-time codes'
                  : 'Enable 2FA for additional security'}
              </p>
            </div>
            <Switch checked={is2FAEnabled} onCheckedChange={setIs2FAEnabled} />
          </div>
          {is2FAEnabled && (
            <>
              <div className="flex items-center justify-between pt-4 border-t">
                <div>
                  <p className="font-medium text-sm">Recovery Codes</p>
                  <p className="text-xs text-muted-foreground">Backup codes for account recovery</p>
                </div>
                <Button variant="outline" size="sm">View Codes</Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Active Sessions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Monitor className="h-4 w-4" />
            Active Sessions
          </CardTitle>
          <CardDescription>Manage your active sessions across devices</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {mockSessions.map((session) => (
            <div 
              key={session.id} 
              className={cn(
                'flex items-center justify-between p-3 border rounded-lg',
                session.isCurrent && 'border-primary bg-primary/5'
              )}
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-muted rounded-lg">
                  {session.device === 'Mobile' ? (
                    <Smartphone className="h-5 w-5" />
                  ) : (
                    <Monitor className="h-5 w-5" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-sm">{session.browser}</p>
                    {session.isCurrent && (
                      <Badge variant="success" size="sm">Current</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Globe className="h-3 w-3" />
                    {session.location} • {session.ip}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    Last active {formatDate(new Date(session.lastActive), { month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric' })}
                  </div>
                </div>
              </div>
              {!session.isCurrent && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="text-danger hover:text-danger"
                  onClick={() => handleRevokeSession(session)}
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Revoke
                </Button>
              )}
            </div>
          ))}
          <Button variant="outline" className="w-full text-danger hover:text-danger">
            <LogOut className="mr-2 h-4 w-4" />
            Sign Out All Other Sessions
          </Button>
        </CardContent>
      </Card>

      {/* Login Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Recent Activity
          </CardTitle>
          <CardDescription>Your recent security events</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockActivity.map((activity) => {
              const config = activityConfig[activity.action];
              const Icon = config.icon;
              return (
                <div key={activity.id} className="flex items-start gap-3 pb-4 border-b last:border-0 last:pb-0">
                  <div className={cn('p-2 rounded-lg bg-muted', config.color)}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{config.label}</p>
                    <p className="text-xs text-muted-foreground">{activity.device}</p>
                    <p className="text-xs text-muted-foreground">
                      {activity.location} • {activity.ip}
                    </p>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatDate(new Date(activity.timestamp), { month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric' })}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Security Recommendations */}
      <Card className="border-warning/50 bg-warning/5">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-warning" />
            Security Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-3">
            <CheckCircle className="h-4 w-4 text-success" />
            <span className="text-sm">Two-factor authentication is enabled</span>
          </div>
          <div className="flex items-center gap-3">
            <CheckCircle className="h-4 w-4 text-success" />
            <span className="text-sm">Password was changed recently</span>
          </div>
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-4 w-4 text-warning" />
            <span className="text-sm">Consider reviewing old sessions and revoking unused ones</span>
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
