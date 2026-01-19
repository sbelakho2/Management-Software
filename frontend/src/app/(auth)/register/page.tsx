'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Mail, Lock, User, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useI18n } from '@/contexts/i18n-context';
import { cn } from '@/lib/utils';

export default function RegisterPage() {
  const router = useRouter();
  const { register, isLoading, error, clearError, resetAuth } = useAuthStore();
  const { t, isRTL } = useI18n();
  
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [fullName, setFullName] = React.useState('');
  const [localError, setLocalError] = React.useState<string | null>(null);
  const [showStoreError, setShowStoreError] = React.useState(false);

  // Clear any stale auth state on mount
  React.useEffect(() => {
    resetAuth();
  }, [resetAuth]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();
    setShowStoreError(true); // Show errors only after user attempts registration

    if (!email || !password || !fullName) {
      setLocalError(t('validation.fillAllFields'));
      return;
    }

    if (password.length < 8) {
      setLocalError(t('validation.passwordMinLength'));
      return;
    }

    try {
      await register(email, password, fullName);
      router.push('/today');
    } catch (err) {
      // Error is handled by the store
    }
  };

  // Only show store error if user has attempted registration
  const displayError = localError || (showStoreError ? error : null);

  return (
    <div className={cn("space-y-8", isRTL && "text-right")}>
      <div>
        <h2 className="text-2xl font-sans font-black uppercase tracking-tight text-foreground/90">
          {t('auth.createAccount')}
        </h2>
        <p className="mt-2 text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-muted-foreground/40">
          {t('auth.requestAccessSubtitle')}
        </p>
      </div>

      {displayError && (
        <Alert variant="destructive" className="bg-rams-red/5 border-rams-red/20 text-rams-red rounded-rams-sm">
          <AlertDescription className="font-mono font-black uppercase tracking-widest text-[9px]">{displayError}</AlertDescription>
        </Alert>
      )}

      <form className="space-y-6" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="fullName" className={cn(
            "text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/40",
            isRTL ? "mr-1" : "ml-1"
          )}>
            {t('forms.fullName')}
          </Label>
          <div className="relative group">
            <div className={cn(
              "absolute inset-y-0 flex items-center pointer-events-none text-muted-foreground/20 group-focus-within:text-rams-orange transition-colors",
              isRTL ? "right-0 pr-4" : "left-0 pl-4"
            )}>
              <User className="h-4 w-4" />
            </div>
            <Input
              id="fullName"
              type="text"
              placeholder={t('forms.fullNamePlaceholder')}
              required
              className={cn("rounded-rams-sm border-rams-line bg-rams-panel transition-none uppercase", isRTL ? "pr-11" : "pl-11")}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="email" className={cn(
            "text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/40",
            isRTL ? "mr-1" : "ml-1"
          )}>
            {t('auth.email')}
          </Label>
          <div className="relative group">
            <div className={cn(
              "absolute inset-y-0 flex items-center pointer-events-none text-muted-foreground/20 group-focus-within:text-rams-orange transition-colors",
              isRTL ? "right-0 pr-4" : "left-0 pl-4"
            )}>
              <Mail className="h-4 w-4" />
            </div>
            <Input
              id="email"
              type="email"
              placeholder="USER_IDENTIFIER@COMPANY.COM"
              autoComplete="email"
              required
              className={cn("rounded-rams-sm border-rams-line bg-rams-panel transition-none", isRTL ? "pr-11" : "pl-11")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="password" className={cn(
            "text-[9px] font-black uppercase tracking-[0.25em] text-muted-foreground/40",
            isRTL ? "mr-1" : "ml-1"
          )}>
            {t('auth.password')}
          </Label>
          <div className="relative group">
            <div className={cn(
              "absolute inset-y-0 flex items-center pointer-events-none text-muted-foreground/20 group-focus-within:text-rams-orange transition-colors",
              isRTL ? "right-0 pr-4" : "left-0 pl-4"
            )}>
              <Lock className="h-4 w-4" />
            </div>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              autoComplete="new-password"
              required
              className={cn("rounded-rams-sm border-rams-line bg-rams-panel transition-none", isRTL ? "pr-11" : "pl-11")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
          </div>
          <p className={cn(
            "text-[8px] uppercase tracking-[0.2em] font-black text-muted-foreground/30",
            isRTL ? "mr-1" : "ml-1"
          )}>
            {t('auth.passwordRequirements')}
          </p>
        </div>

        <Button
          type="submit"
          className="w-full rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest h-12 transition-none border border-black/10 hover:bg-rams-orange/90"
          loading={isLoading}
          size="xl"
        >
          {isLoading ? t('auth.processing') : t('auth.requestAccess')}
        </Button>
      </form>

      <div className="text-center pt-4">
        <Link
          href="/login"
          className="text-[10px] font-black text-muted-foreground/60 hover:text-rams-orange transition-none group inline-flex items-center gap-3 uppercase tracking-widest"
        >
          <ArrowLeft className={cn("h-3.5 w-3.5 transition-transform", isRTL ? "rotate-180 group-hover:translate-x-1" : "group-hover:-translate-x-1")} />
          <span>{t('auth.backToSignIn')}</span>
        </Link>
      </div>
    </div>
  );
}
