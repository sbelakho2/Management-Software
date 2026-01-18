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
          <div className="rounded-none bg-rams-green/5 p-5 border border-rams-green/20">
            <CheckCircle2 className="h-10 w-10 text-rams-green" />
          </div>
        </div>
        <div>
          <h2 className="text-2xl font-sans font-black uppercase tracking-tight text-foreground/90">
            {t('auth.verificationSent')}
          </h2>
          <p className="mt-2 text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-muted-foreground/40 max-w-[280px] mx-auto leading-relaxed">
            {t('auth.instructionsDispatched')} <span className="text-foreground/80 font-black">{email.toUpperCase()}</span>
          </p>
        </div>
        <div className="pt-4">
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

  return (
    <div className={cn("space-y-8", isRTL && "text-right")}>
      <div>
        <h2 className="text-2xl font-sans font-black uppercase tracking-tight text-foreground/90">
          {t('auth.resetAccess')}
        </h2>
        <p className="mt-2 text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-muted-foreground/40">
          {t('auth.enterEmailForRecovery')}
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="bg-rams-red/5 border-rams-red/20 text-rams-red animate-in slide-in-from-top-2 duration-300 rounded-rams-sm">
          <AlertDescription className="font-mono font-black uppercase tracking-widest text-[9px]">{error}</AlertDescription>
        </Alert>
      )}

      <form className="space-y-6" onSubmit={handleSubmit}>
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
              required
              className={cn("rounded-rams-sm border-rams-border bg-rams-panel transition-none", isRTL ? "pr-11" : "pl-11")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        <Button
          type="submit"
          className="w-full rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest h-12 transition-none border border-black/10 hover:bg-rams-orange/90"
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
          className="text-[10px] font-black text-muted-foreground/60 hover:text-rams-orange transition-none group inline-flex items-center gap-3 uppercase tracking-widest"
        >
          <ArrowLeft className={cn("h-3.5 w-3.5 transition-transform", isRTL ? "rotate-180 group-hover:translate-x-1" : "group-hover:-translate-x-1")} />
          <span>{t('auth.returnToSignIn')}</span>
        </Link>
      </div>
    </div>
  );
}
