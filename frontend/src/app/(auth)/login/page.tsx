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

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isLoading, error, clearError } = useAuthStore();
  
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);
  const [localError, setLocalError] = React.useState<string | null>(null);

  const from = searchParams.get('from') || '/today';

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
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight text-foreground bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
          Welcome back
        </h2>
        <p className="mt-2 text-sm text-muted-foreground font-medium">
          Enter your credentials to access the command center
        </p>
      </div>

      {(error || localError) && (
        <Alert variant="destructive" className="bg-destructive/10 border-destructive/20 text-destructive animate-in slide-in-from-top-2 duration-300">
          <AlertDescription className="font-medium">{error || localError}</AlertDescription>
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
              autoComplete="email"
              required
              className="pl-10 h-12 bg-background/50 border-border/50 focus:border-primary/50 transition-all rounded-xl"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password" className="text-xs font-bold uppercase tracking-widest text-muted-foreground/70">
              Password
            </Label>
            <Link
              href="/forgot-password"
              className="text-xs font-bold text-primary hover:text-primary/80 transition-colors uppercase tracking-widest"
            >
              Forgot?
            </Link>
          </div>
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted-foreground/50 group-focus-within:text-primary transition-colors">
              <Lock className="h-4 w-4" />
            </div>
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              className="pl-10 pr-10 h-12 bg-background/50 border-border/50 focus:border-primary/50 transition-all rounded-xl"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
            <button
              type="button"
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground/40 hover:text-primary transition-colors"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
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
          className="w-full h-12 text-base rounded-xl premium-shimmer"
          loading={isLoading}
          size="xl"
        >
          {isLoading ? 'Authenticating...' : 'Sign In'}
        </Button>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center" aria-hidden="true">
          <div className="w-full border-t border-border/30"></div>
        </div>
        <div className="relative flex justify-center text-xs uppercase tracking-[0.2em] font-bold">
          <span className="bg-transparent px-4 text-muted-foreground/40">
            Secure Access
          </span>
        </div>
      </div>

      <div className="text-center">
        <Link
          href="/register"
          className="text-sm font-bold text-muted-foreground hover:text-primary transition-all group inline-flex items-center gap-2"
        >
          <span>Need access?</span>
          <span className="text-primary group-hover:translate-x-1 transition-transform">Contact Administrator &rarr;</span>
        </Link>
      </div>
    </div>
  );
}
