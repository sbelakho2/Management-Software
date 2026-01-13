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

export default function RegisterPage() {
  const router = useRouter();
  const { register, isLoading, error, clearError } = useAuthStore();
  
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
      setLocalError('Please fill in all fields');
      return;
    }

    if (password.length < 8) {
      setLocalError('Password must be at least 8 characters long');
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
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight text-foreground bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
          Create Account
        </h2>
        <p className="mt-2 text-sm text-muted-foreground font-medium">
          Request access to the Sensei OS enterprise platform
        </p>
      </div>

      {(error || localError) && (
        <Alert variant="destructive" className="bg-destructive/10 border-destructive/20 text-destructive animate-in slide-in-from-top-2 duration-300">
          <AlertDescription className="font-medium">{error || localError}</AlertDescription>
        </Alert>
      )}

      <form className="space-y-6" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="fullName" className="text-xs font-bold uppercase tracking-widest text-muted-foreground/70">
            Full Name
          </Label>
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted-foreground/50 group-focus-within:text-primary transition-colors">
              <User className="h-4 w-4" />
            </div>
            <Input
              id="fullName"
              type="text"
              placeholder="John Doe"
              required
              className="pl-10 h-12 bg-background/50 border-border/50 focus:border-primary/50 transition-all rounded-xl"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

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
          <Label htmlFor="password" className="text-xs font-bold uppercase tracking-widest text-muted-foreground/70">
            Password
          </Label>
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted-foreground/50 group-focus-within:text-primary transition-colors">
              <Lock className="h-4 w-4" />
            </div>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              autoComplete="new-password"
              required
              className="pl-10 h-12 bg-background/50 border-border/50 focus:border-primary/50 transition-all rounded-xl"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
          </div>
          <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/40">
            Minimum 8 characters with enterprise complexity
          </p>
        </div>

        <Button
          type="submit"
          className="w-full h-12 text-base rounded-xl premium-shimmer"
          loading={isLoading}
          size="xl"
        >
          {isLoading ? 'Processing...' : 'Request Access'}
        </Button>
      </form>

      <div className="text-center pt-4">
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
