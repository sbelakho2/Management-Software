'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Save,
  LayoutGrid,
  Users,
  Target,
  BarChart3,
  Plus,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
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

export default function NewObeyaBoardPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [isSaving, setIsSaving] = React.useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
    toast({
      title: 'Obeya Board Created',
      description: 'Your new digital obeya board has been successfully initialized.',
    });
    router.push('/obeya');
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">New Strategic Obeya</h1>
            <p className="text-muted-foreground font-medium text-sm">Create a centralized organizational intelligence node for your team</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary h-12 px-8" onClick={() => router.back()}>
            Abort
          </Button>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine h-12 px-8 font-bold" onClick={handleSave} disabled={isSaving}>
            <Save className="h-4 w-4 mr-2" />
            {isSaving ? 'Initializing...' : 'Establish Board'}
          </Button>
        </div>
      </div>

      <div className="grid gap-8">
        <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium overflow-hidden">
          <CardHeader className="pb-8 border-b border-border/5 bg-muted/5 p-8">
            <CardTitle className="text-lg font-heading">Protocol Configuration</CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Basic parameters and ownership nodes</CardDescription>
          </CardHeader>
          <CardContent className="p-8 space-y-8">
            <div className="grid gap-8 sm:grid-cols-2">
              <div className="sm:col-span-2 space-y-3">
                <Label htmlFor="name" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Strategic Board Identity</Label>
                <Input id="name" placeholder="e.g. Operations Tier 2 Command Center" className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50" />
              </div>
              <div className="space-y-3">
                <Label htmlFor="team" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Departmental Node</Label>
                <Select>
                  <SelectTrigger id="team" className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft">
                    <SelectValue placeholder="Identify team" />
                  </SelectTrigger>
                  <SelectContent className="rounded-2xl shadow-premium">
                    <SelectItem value="ops" className="rounded-xl m-1">Operations</SelectItem>
                    <SelectItem value="eng" className="rounded-xl m-1">Engineering</SelectItem>
                    <SelectItem value="quality" className="rounded-xl m-1">Quality Assurance</SelectItem>
                    <SelectItem value="sales" className="rounded-xl m-1">Strategic Sales</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-3">
                <Label htmlFor="owner" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Primary Custodian</Label>
                <Input id="owner" placeholder="Search user nodes..." className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft" />
              </div>
            </div>
            <div className="space-y-3">
              <Label htmlFor="desc" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Strategic Context</Label>
              <Textarea id="desc" placeholder="Purpose and scope of this management protocol..." className="rounded-[1.5rem] bg-background/50 border-border/50 shadow-inner-soft focus:border-primary/50 transition-all min-h-[100px] resize-none" rows={3} />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium">
          <CardHeader className="p-8">
            <CardTitle className="text-lg font-heading">Intelligence Modules (SQDCP)</CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Select categorical nodes to activate on board</CardDescription>
          </CardHeader>
          <CardContent className="p-8 pt-0">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {[
                { id: 'safety', label: 'Safety (S)', color: 'bg-emerald-500' },
                { id: 'quality', label: 'Quality (Q)', color: 'bg-blue-500' },
                { id: 'delivery', label: 'Delivery (D)', color: 'bg-amber-500' },
                { id: 'cost', label: 'Cost (C)', color: 'bg-rose-500' },
                { id: 'people', label: 'People (P)', color: 'bg-purple-500' },
                { id: 'exceptions', label: 'Exceptions Log', color: 'bg-slate-500' },
              ].map((module) => (
                <div key={module.id} className="flex items-center justify-between p-5 rounded-2xl bg-muted/10 border border-border/5 group transition-all hover:bg-primary/5">
                  <div className="flex items-center gap-4">
                    <div className={cn("w-1.5 h-8 rounded-full shadow-glow", module.color)} />
                    <span className="font-heading font-bold text-sm tracking-tight text-foreground/80">{module.label}</span>
                  </div>
                  <input type="checkbox" defaultChecked className="h-5 w-5 rounded-lg border-border/40 bg-background/50 text-primary focus:ring-primary transition-all cursor-pointer" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
