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
  login_success: { labelKey: 'settings.security.activity.loginSuccess', icon: CheckCircle, color: 'text-rams-green' },
  login_failed: { labelKey: 'settings.security.activity.loginFailed', icon: XCircle, color: 'text-rams-red' },
  logout: { labelKey: 'settings.security.activity.logout', icon: LogOut, color: 'text-muted-foreground' },
  password_changed: { labelKey: 'settings.security.activity.passwordChanged', icon: Key, color: 'text-rams-orange' },
  '2fa_enabled': { labelKey: 'settings.security.activity.twoFactorEnabled', icon: Shield, color: 'text-rams-green' },
};

function ChangePasswordDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { t } = useI18n();
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
          <DialogTitle>{t('settings.security.changePassword')}</DialogTitle>
          <DialogDescription>{t('settings.security.changePasswordDesc')}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="currentPassword">{t('settings.security.currentPassword')}</Label>
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
            <Label htmlFor="newPassword">{t('settings.security.newPassword')}</Label>
            <div className="relative">
              <Input
                id="newPassword"
                type={showPasswords ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            {newPassword && !isStrongPassword && (
              <p className="text-xs text-rams-red">{t('settings.security.passwordStrengthHint')}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">{t('settings.security.confirmPassword')}</Label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showPasswords ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>
            {confirmPassword && !passwordsMatch && (
              <p className="text-xs text-rams-red">{t('settings.security.passwordsDoNotMatch')}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowPasswords(!showPasswords)}
              className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              {showPasswords ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              {showPasswords ? t('settings.security.passwordVisibility.hide') : t('settings.security.passwordVisibility.show')} {t('settings.security.passwordVisibility.label')}
            </button>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
          <Button 
            onClick={handleSubmit} 
            disabled={!currentPassword || !passwordsMatch || !isStrongPassword || isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('settings.security.changingPassword')}
              </>
            ) : (
              t('settings.security.changePassword')
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
    <div className="space-y-8 animate-in fade-in duration-150 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              {t('settings.security.title')}
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">{t('settings.security.subtitle')}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Password */}
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Key className="h-4 w-4 text-rams-orange" />
              {t('settings.security.authenticationKeys')}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="p-5 rounded-none bg-rams-panel/40 border border-rams-line flex items-center justify-between group">
              <div>
                <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 transition-none group-hover:text-rams-orange">{t('settings.security.accessPassword')}</p>
                <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1">{t('settings.security.lastRotated')}</p>
              </div>
              <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line text-[9px] font-black uppercase tracking-widest h-10 px-6 transition-none" onClick={() => setPasswordDialogOpen(true)}>
                {t('settings.security.updateKeys')}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Two-Factor Authentication */}
        <Card className={cn("rounded-rams-sm border bg-rams-module", is2FAEnabled ? 'border-rams-green/30 bg-rams-green/5' : 'border-rams-orange/30 bg-rams-orange/5')}>
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Smartphone className="h-4 w-4 text-rams-orange" />
              {t('settings.security.verificationLayer')}
              {is2FAEnabled ? (
                <Badge variant="success" size="sm" className="ml-auto h-4 px-1 text-[8px] font-black uppercase">{t('settings.security.active')}</Badge>
              ) : (
                <Badge variant="warning" size="sm" className="ml-auto h-4 px-1 text-[8px] font-black uppercase">{t('settings.security.atRisk')}</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-4">
            <div className="p-5 rounded-none bg-rams-panel/40 border border-rams-line flex items-center justify-between">
              <div className="flex-1">
                <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{t('settings.security.authenticatorProtocol')}</p>
                <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40 mt-1 leading-relaxed">
                  {is2FAEnabled 
                    ? t('settings.security.syncedWithToken')
                    : t('settings.security.enable2faDesc')}
                </p>
              </div>
              <Switch 
                checked={is2FAEnabled} 
                onCheckedChange={setIs2FAEnabled}
              />
            </div>
          </CardContent>
        </Card>

        {/* Active Sessions */}
        <Card className="lg:col-span-2 rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Monitor className="h-4 w-4 text-rams-orange" />
              {t('settings.security.activeIntelligenceNodes')}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-line/30">
              {mockSessions.map((session) => (
                <div 
                  key={session.id} 
                  className={cn(
                    'flex items-center justify-between p-6 transition-none group',
                    session.isCurrent ? 'bg-rams-panel/40 shadow-[inset_2px_0_0_0_#2D8C3C]' : 'hover:bg-rams-panel/20'
                  )}
                >
                  <div className="flex items-center gap-6">
                    <div className={cn('p-3 rounded-none border border-rams-line transition-none', session.isCurrent ? 'bg-rams-module text-rams-green' : 'bg-rams-panel text-muted-foreground/40')}>
                      {session.device === 'Mobile' ? (
                        <Smartphone className="h-5 w-5" />
                      ) : (
                        <Monitor className="h-5 w-5" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-4">
                        <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{session.browser}</p>
                        {session.isCurrent && (
                          <Badge variant="success" size="sm" className="h-4 px-1 text-[8px] font-black uppercase tracking-widest">{t('settings.security.primaryNode')}</Badge>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 mt-2">
                        <div className="flex items-center gap-2 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                          <Globe className="h-3 w-3" />
                          {session.location.toUpperCase()} • {session.ip}
                        </div>
                        <div className="flex items-center gap-2 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                          <Clock className="h-3 w-3" />
                          {t('settings.security.pulse')}: {formatDate(new Date(session.lastActive)).toUpperCase()}
                        </div>
                      </div>
                    </div>
                  </div>
                  {!session.isCurrent && (
                    <Button 
                      variant="ghost" 
                      size="default" 
                      className="text-rams-red hover:bg-rams-red/5 rounded-rams-sm px-4 h-9 text-[9px] font-black uppercase tracking-widest transition-none border border-transparent hover:border-rams-red/20"
                      onClick={() => handleRevokeSession(session)}
                    >
                      <LogOut className="mr-2 h-3.5 w-3.5" />
                      {t('settings.security.terminateNode')}
                    </Button>
                  )}
                </div>
              ))}
            </div>
            <div className="p-6 bg-rams-panel/10 border-t border-rams-line">
              <Button variant="outline" className="w-full h-12 text-rams-red hover:bg-rams-red/5 border-rams-red/20 rounded-rams-sm text-[10px] font-black uppercase tracking-widest transition-none">
                <LogOut className="mr-2 h-4 w-4" />
                {t('settings.security.terminateAllRemoteSessions')}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Login Activity */}
        <Card className="lg:col-span-2 rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
              <Shield className="h-4 w-4 text-rams-orange" />
              {t('settings.security.eventTelemetryLog')}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-rams-line/30">
              {mockActivity.map((activity) => {
                const config = activityConfig[activity.action];
                const Icon = config.icon;
                return (
                  <div key={activity.id} className="flex items-center gap-6 p-5 hover:bg-rams-panel/40 transition-none group">
                    <div className={cn('p-2.5 rounded-none border border-rams-line transition-none bg-rams-panel', config.color)}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t(config.labelKey)}</p>
                      <div className="flex items-center gap-4 mt-1 text-[9px] font-mono font-bold uppercase tracking-widest text-muted-foreground/40">
                        <span>{activity.device.toUpperCase()}</span>
                        <span className="opacity-30">•</span>
                        <span>{activity.location.toUpperCase()}</span>
                      </div>
                    </div>
                    <div className="text-[10px] font-mono font-bold uppercase tracking-tighter text-muted-foreground/30">
                      {formatDate(new Date(activity.timestamp)).toUpperCase()}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Security Recommendations */}
      <Card className="rounded-rams-sm border border-rams-orange/30 bg-rams-orange/5">
        <CardHeader className="bg-rams-orange/10 border-b border-rams-orange/20">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rams-orange" />
            {t('settings.security.securitySyncRecommendations')}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          {[
            { labelKey: 'settings.security.securityRecommendation1', status: 'success' },
            { labelKey: 'settings.security.securityRecommendation2', status: 'success' },
            { labelKey: 'settings.security.securityRecommendation3', status: 'warning' },
          ].map((item, idx) => (
            <div key={idx} className="flex items-center gap-4 p-4 bg-rams-module border border-rams-line group">
              <div className={cn('p-2 rounded-none border transition-none', 
                item.status === 'success' ? 'bg-rams-green/5 text-rams-green border-rams-green/20' : 'bg-rams-orange/5 text-rams-orange border-rams-orange/20'
              )}>
                {item.status === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
              </div>
              <span className="text-[11px] font-medium uppercase text-foreground/70">{t(item.labelKey)}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <ChangePasswordDialog 
        open={passwordDialogOpen} 
        onOpenChange={setPasswordDialogOpen} 
      />

      <AlertDialog open={revokeDialogOpen} onOpenChange={setRevokeDialogOpen}>
        <AlertDialogContent className="rounded-rams-sm border-rams-line bg-rams-module">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('settings.security.terminateNodeAuthorization')}</AlertDialogTitle>
            <AlertDialogDescription className="text-xs font-medium uppercase leading-relaxed text-muted-foreground/60">
              {t('settings.security.terminateNodeDescription', { location: selectedSession?.location?.toUpperCase() ?? '' })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="border-t border-rams-line pt-4 mt-2">
            <AlertDialogCancel className="rounded-none text-[9px] font-black uppercase tracking-widest h-9">{t('settings.security.cancelProtocol')}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmRevokeSession} className="rounded-none bg-rams-red text-white hover:bg-rams-red/90 text-[9px] font-black uppercase tracking-widest h-9">
              {t('settings.security.terminateNode')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
