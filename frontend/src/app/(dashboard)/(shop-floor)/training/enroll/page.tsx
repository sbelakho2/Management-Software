'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, GraduationCap, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
export default function EnrollTrainingPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const programs = [
    { id: '1', title: 'Safety Fundamentals 2024' },
    { id: '2', title: 'Lean Six Sigma White Belt' },
    { id: '3', title: 'Advanced Machining Center Operation' },
    { id: '4', title: 'Quality Assurance - Basic' },
  ];
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      toast({
        title: 'Enrolled Successfully',
        description: 'You have been added to the training program.',
      });
      router.push('/training');
    }, 1000);
  };
  return (
    <div className="max-w-2xl mx-auto space-y-8 page-fade-in">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
          <ChevronLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">Enrollment Protocol</h1>
          <p className="text-muted-foreground font-medium text-sm">Join a new organizational development program</p>
        </div>
      </div>
      <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium">
        <CardHeader className="pb-8">
          <CardTitle className="text-lg font-heading">Initiate Enrollment</CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Configure your training node parameters</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-8">
            <div className="space-y-3">
              <Label htmlFor="program" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Strategic Program Node</Label>
              <Select required>
                <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft">
                  <SelectValue placeholder="Select a program node" />
                </SelectTrigger>
                <SelectContent className="rounded-2xl shadow-premium">
                  {programs.map(p => (
                    <SelectItem key={p.id} value={p.id} className="rounded-xl m-1">{p.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-3">
              <Label htmlFor="reason" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Rational Optimization Context (Optional)</Label>
              <Input id="reason" placeholder="e.g. Skill gap resolution, maturity escalation..." className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft" />
            </div>
            <div className="pt-6 flex gap-4">
              <Button type="button" variant="outline" className="flex-1 rounded-xl border-primary/20 hover:bg-primary/5 text-primary h-12" onClick={() => router.back()}>Abort</Button>
              <Button type="submit" className="flex-1 rounded-xl shadow-glow subtle-shine h-12 font-bold" disabled={isSubmitting}>
                {isSubmitting ? 'Synchronizing...' : 'Establish Enrollment'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
