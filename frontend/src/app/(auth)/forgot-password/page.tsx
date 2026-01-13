'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import { authApi } from '@/api';

export default function ForgotPasswordPage() {
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
      setError((err as Error).message || 'Failed to send reset email');
    } finally {
      setIsLoading(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="space-y-8 text-center animate-in fade-in zoom-in-95 duration-500">
        <div className="flex justify-center">
          <div className="rounded-full bg-success/10 p-4 border border-success/20 shadow-lg shadow-success/10">
            <CheckCircle2 className="h-10 w-10 text-success" />
          </div>
        </div>
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-foreground bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Verification Sent
          </h2>
          <p className="mt-2 text-sm text-muted-foreground font-medium max-w-[280px] mx-auto">
            Instructions have been dispatched to <span className="text-foreground font-bold">{email}</span>
          </p>
        </div>
        <div className="pt-4">
          <Link
            href="/login"
            className="text-sm font-bold text-muted-foreground hover:text-primary transition-all group inline-flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
            <span>Back to sign in</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight text-foreground bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
          Reset Access
        </h2>
        <p className="mt-2 text-sm text-muted-foreground font-medium">
          Enter your email to receive recovery instructions
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="bg-destructive/10 border-destructive/20 text-destructive animate-in slide-in-from-top-2 duration-300">
          <AlertDescription className="font-medium">{error}</AlertDescription>
        </Alert>
      )}

      <form className="space-y-6" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="email" className="text-xs font-bold uppercase tracking-widest text-muted-foreground/70">
            Email address
          </Label>
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted-foreground/50 group-focus-within:text-primary transition-colors">
              <Mail className="h-4 w-4" />
            </div>
            <Input
              id="email"
              type="email"
              placeholder="name@company.com"
              required
              className="pl-10 h-12 bg-background/50 border-border/50 focus:border-primary/50 transition-all rounded-xl"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        <Button
          type="submit"
          className="w-full h-12 text-base rounded-xl premium-shimmer"
          loading={isLoading}
          disabled={!email}
          size="xl"
        >
          {isLoading ? 'Dispatching...' : 'Send Instructions'}
        </Button>
      </form>

      <div className="text-center pt-4">
        <Link
          href="/login"
          className="text-sm font-bold text-muted-foreground hover:text-primary transition-all group inline-flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
          <span>Return to sign in</span>
        </Link>
      </div>
    </div>
  );
}
