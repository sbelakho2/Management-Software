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
  const { register, isLoading, error, clearError } = useAuthStore();
  const { t, isRTL } = useI18n();
  
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [fullName, setFullName] = React.useState('');
  const [localError, setLocalError] = React.useState<string | null>(null);

  React.useEffect(() => {
    return () => clearError();
  }, [clearError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

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

  return (
    <div className={cn("space-y-8", isRTL && "text-right")}>
      <div>
        <h2 className="text-3xl font-heading font-bold tracking-tight text-foreground ">
          {t('auth.createAccount')}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground font-medium">
          {t('auth.requestAccessSubtitle')}
        </p>
      </div>

      {(error || localError) && (
        <Alert variant="destructive" className="bg-destructive/10 border-destructive/20 text-destructive animate-in slide-in-from-top-2 duration-300 rounded-2xl">
          <AlertDescription className="font-bold uppercase tracking-widest text-[10px]">{error || localError}</AlertDescription>
        </Alert>
      )}

      <form className="space-y-6" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="fullName" className={cn(
            "text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50",
            isRTL ? "mr-1" : "ml-1"
          )}>
            {t('forms.fullName')}
          </Label>
          <div className="relative group">
            <div className={cn(
              "absolute inset-y-0 flex items-center pointer-events-none text-muted-foreground/30 group-focus-within:text-primary transition-colors",
              isRTL ? "right-0 pr-4" : "left-0 pl-4"
            )}>
              <User className="h-4 w-4" />
            </div>
            <Input
              id="fullName"
              type="text"
              placeholder={t('forms.fullNamePlaceholder')}
              required
              className={isRTL ? "pr-11" : "pl-11"}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

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
          <Label htmlFor="password" className={cn(
            "text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50",
            isRTL ? "mr-1" : "ml-1"
          )}>
            {t('auth.password')}
          </Label>
          <div className="relative group">
            <div className={cn(
              "absolute inset-y-0 flex items-center pointer-events-none text-muted-foreground/30 group-focus-within:text-primary transition-colors",
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
              className={isRTL ? "pr-11" : "pl-11"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
          </div>
          <p className={cn(
            "text-[9px] uppercase tracking-[0.2em] font-bold text-muted-foreground/30",
            isRTL ? "mr-1" : "ml-1"
          )}>
            {t('auth.passwordRequirements')}
          </p>
        </div>

        <Button
          type="submit"
          className="w-full premium-shimmer"
          loading={isLoading}
          size="xl"
        >
          {isLoading ? t('auth.processing') : t('auth.requestAccess')}
        </Button>
      </form>

      <div className="text-center pt-4">
        <Link
          href="/login"
          className="text-sm font-bold text-muted-foreground hover:text-primary transition-all group inline-flex items-center gap-2"
        >
          <ArrowLeft className={cn("h-4 w-4 transition-transform", isRTL ? "rotate-180 group-hover:translate-x-1" : "group-hover:-translate-x-1")} />
          <span>{t('auth.backToSignIn')}</span>
        </Link>
      </div>
    </div>
  );
}
