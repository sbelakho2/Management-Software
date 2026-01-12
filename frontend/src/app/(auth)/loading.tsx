import { Loader2 } from 'lucide-react';

export default function AuthLoading() {
  return (
    <div className="flex h-screen items-center justify-center bg-gradient-to-br from-background to-muted">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}
