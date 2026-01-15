'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';

export default function NewTaskPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const [form, setForm] = React.useState({
    title: '',
    description: '',
    priority: 'medium',
    dueDate: '',
    assigneeId: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      toast({ title: 'Task Protocol Established', description: 'The task has been assigned successfully.' });
      router.push('/tasks');
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to create task.', variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">New Assignment</h1>
            <p className="text-muted-foreground font-medium text-sm">Assign a new strategic task node to yourself or a teammate</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary h-12 px-8" onClick={() => router.back()}>Abort</Button>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine h-12 px-8" onClick={handleSubmit} disabled={isSubmitting}>
            <Save className="h-4 w-4 mr-2" />
            {isSubmitting ? 'Synchronizing...' : 'Create Assignment'}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium overflow-hidden">
          <CardHeader className="pb-8 border-b border-border/5 bg-muted/5 p-8">
            <CardTitle className="text-lg font-heading">Protocol Parameters</CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Configure the assignment metadata and priority layer</CardDescription>
          </CardHeader>
          <CardContent className="space-y-8 p-8">
            <div className="space-y-3">
              <Label htmlFor="title" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Assignment Title *</Label>
              <Input
                id="title"
                placeholder="Specify the strategic objective..."
                className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
            </div>
            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-3">
                <Label htmlFor="priority" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Priority Layer</Label>
                <Select value={form.priority} onValueChange={(v) => setForm({ ...form, priority: v })}>
                  <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-2xl shadow-premium">
                    <SelectItem value="low" className="rounded-xl m-1">Low</SelectItem>
                    <SelectItem value="medium" className="rounded-xl m-1">Medium</SelectItem>
                    <SelectItem value="high" className="rounded-xl m-1">High</SelectItem>
                    <SelectItem value="urgent" className="rounded-xl m-1">Urgent</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-3">
                <Label htmlFor="dueDate" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Temporal Horizon</Label>
                <div className="relative">
                  <Input
                    id="dueDate"
                    type="date"
                    className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft"
                    value={form.dueDate}
                    onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
                  />
                </div>
              </div>
            </div>
            <div className="space-y-3">
              <Label htmlFor="description" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Detailed Intelligence</Label>
              <div className="relative">
                <Textarea
                  id="description"
                  placeholder="Incorporate additional context and required outcomes for this protocol..."
                  className="rounded-[1.5rem] bg-background/50 border-border/50 shadow-inner-soft focus:border-primary/50 transition-all min-h-[160px] resize-none"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
