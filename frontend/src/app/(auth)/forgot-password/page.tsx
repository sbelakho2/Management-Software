'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import { authApi } from '@/api';
import { useI18n } from '@/contexts/i18n-context';
import { cn } from '@/lib/utils';

export default function ForgotPasswordPage() {
  const { t, isRTL } = useI18n();
  const [email, setEmail] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await authApi.requestPasswordReset({ email });
      setIsSubmitted(true);
    } catch (err) {
      setError((err as Error).message || t('auth.resetEmailFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className={cn("space-y-8 text-center animate-in fade-in zoom-in-95 duration-500", isRTL && "text-right")}>
        <div className="flex justify-center">
          <div className="rounded-full bg-success/10 p-5 border border-success/20 shadow-glow">
            <CheckCircle2 className="h-10 w-10 text-success" />
          </div>
        </div>
        <div>
          <h2 className="text-3xl font-heading font-bold tracking-tight text-foreground ">
            {t('auth.verificationSent')}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground font-medium max-w-[280px] mx-auto">
            {t('auth.instructionsDispatched')} <span className="text-foreground font-bold">{email}</span>
          </p>
        </div>
        <div className="pt-4">
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

  return (
    <div className={cn("space-y-8", isRTL && "text-right")}>
      <div>
        <h2 className="text-3xl font-heading font-bold tracking-tight text-foreground ">
          {t('auth.resetAccess')}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground font-medium">
          {t('auth.enterEmailForRecovery')}
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="bg-destructive/10 border-destructive/20 text-destructive animate-in slide-in-from-top-2 duration-300 rounded-2xl">
          <AlertDescription className="font-bold uppercase tracking-widest text-[10px]">{error}</AlertDescription>
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
              required
              className={isRTL ? "pr-11" : "pl-11"}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        <Button
          type="submit"
          className="w-full premium-shimmer"
          loading={isLoading}
          disabled={!email}
          size="xl"
        >
          {isLoading ? t('auth.dispatching') : t('auth.sendInstructions')}
        </Button>
      </form>

      <div className="text-center pt-4">
        <Link
          href="/login"
          className="text-sm font-bold text-muted-foreground hover:text-primary transition-all group inline-flex items-center gap-2"
        >
          <ArrowLeft className={cn("h-4 w-4 transition-transform", isRTL ? "rotate-180 group-hover:translate-x-1" : "group-hover:-translate-x-1")} />
          <span>{t('auth.returnToSignIn')}</span>
        </Link>
      </div>
    </div>
  );
}
