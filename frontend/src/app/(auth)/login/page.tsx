'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/stores';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Mail, Lock, Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';
import { getSafeRedirectPath } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';
import { cn } from '@/lib/utils';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isLoading, error, clearError } = useAuthStore();
  const { t, isRTL } = useI18n();
  
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);
  const [localError, setLocalError] = React.useState<string | null>(null);

  // Use safe redirect to prevent open redirect vulnerability
  const from = getSafeRedirectPath(searchParams.get('from'), '/today');

  // Clear any stale tokens when landing on login page
  // This prevents "session expired" flash when tokens are invalid
  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      } catch {
        // localStorage not available
      }
    }
  }, []);

  React.useEffect(() => {
    return () => clearError();
  }, [clearError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email || !password) {
      setLocalError('Please fill in all fields');
      return;
    }

    try {
      await login(email, password);
      router.push(from);
    } catch (err) {
      // Error is handled by the store
    }
  };

  return (
    <div className={cn("space-y-8", isRTL && "text-right")}>
      <div>
        <h2 className="text-3xl font-heading font-bold tracking-tight text-foreground ">
          {t('auth.welcomeBack')}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground font-medium">
          {t('auth.loginSubtitle')}
        </p>
      </div>

      {(error || localError) && (
        <Alert variant="destructive" className="bg-destructive/10 border-destructive/20 text-destructive animate-in slide-in-from-top-2 duration-300 rounded-2xl">
          <AlertDescription className="font-bold uppercase tracking-widest text-[10px]">{error || localError}</AlertDescription>
        </Alert>
      )}

      <form className="space-y-6" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="email" className={cn(
            "text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50",
            isRTL ? "mr-1" : "ml-1"
          )}>
            {t('auth.email')}
          </Label>
          <div className="relative group">
            <div className={cn(
              "absolute inset-y-0 flex items-center pointer-events-none text-muted-foreground/30 group-focus-within:text-primary transition-colors",
              isRTL ? "right-0 pr-4" : "left-0 pl-4"
            )}>
              <Mail className="h-4 w-4" />
            </div>
            <Input
              id="email"
              type="email"
              placeholder="name@company.com"
              autoComplete="email"
              required
              className={isRTL ? "pr-11" : "pl-11"}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        <div className="space-y-2">
          <div className={cn("flex items-center justify-between", isRTL ? "mr-1" : "ml-1")}>
            <Label htmlFor="password" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50">
              {t('auth.password')}
            </Label>
            <Link
              href="/forgot-password"
              className="text-[10px] font-bold text-primary hover:text-primary/80 transition-colors uppercase tracking-[0.2em]"
            >
              {t('auth.forgotPassword')}
            </Link>
          </div>
          <div className="relative group">
            <div className={cn(
              "absolute inset-y-0 flex items-center pointer-events-none text-muted-foreground/30 group-focus-within:text-primary transition-colors",
              isRTL ? "right-0 pr-4" : "left-0 pl-4"
            )}>
              <Lock className="h-4 w-4" />
            </div>
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              className={isRTL ? "pr-11 pl-11" : "pl-11 pr-11"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
            <button
              type="button"
              className={cn(
                "absolute inset-y-0 flex items-center text-muted-foreground/30 hover:text-primary transition-colors",
                isRTL ? "left-0 pl-4" : "right-0 pr-4"
              )}
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? t('accessibility.hidePassword') : t('accessibility.showPassword')}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        <Button
          type="submit"
          className="w-full premium-shimmer"
          loading={isLoading}
          size="xl"
        >
          {isLoading ? t('auth.authenticating') : t('auth.signIn')}
        </Button>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center" aria-hidden="true">
          <div className="w-full border-t border-border/30"></div>
        </div>
        <div className="relative flex justify-center text-xs uppercase tracking-[0.2em] font-bold">
          <span className="bg-transparent px-4 text-muted-foreground/40">
            {t('auth.secureAccess')}
          </span>
        </div>
      </div>

      <div className="text-center">
        <Link
          href="/register"
          className="text-sm font-bold text-muted-foreground hover:text-primary transition-all group inline-flex items-center gap-2"
        >
          <span>{t('auth.needAccess')}</span>
          <span className={cn(
            "text-primary transition-transform",
            isRTL ? "group-hover:-translate-x-1" : "group-hover:translate-x-1"
          )}>
            {t('auth.contactAdmin')} {isRTL ? '←' : '→'}
          </span>
        </Link>
      </div>
    </div>
  );
}
