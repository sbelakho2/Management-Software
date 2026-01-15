'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, Bell, BellOff, Volume2, Smartphone } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
export default function AndonSettingsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      toast({
        title: 'Protocol Calibrated',
        description: 'Signal notification preferences have been updated.',
      });
      router.push('/andon');
    }, 1000);
  };
  return (
    <div className="max-w-3xl mx-auto space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.back()}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">Signal Configuration</h1>
            <p className="text-muted-foreground font-medium text-sm">Configure multi-channel alerts and organizational response protocols</p>
          </div>
        </div>
        <Button size="lg" className="rounded-xl shadow-glow subtle-shine h-12 px-8" onClick={handleSubmit} disabled={isSubmitting}>
          <Save className="h-4 w-4 mr-2" />
          {isSubmitting ? 'Calibrating...' : 'Save Configuration'}
        </Button>
      </div>
      <div className="grid gap-8">
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium">
          <CardHeader className="pb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary shadow-sm">
                <Bell className="h-5 w-5" />
              </div>
              <CardTitle className="text-lg font-heading">Notification Intelligence</CardTitle>
            </div>
            <CardDescription className="text-xs font-medium uppercase tracking-wider pl-11">Strategic routing for anomalous signals</CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            <div className="flex items-center justify-between p-5 rounded-2xl bg-muted/10 border border-border/5 group transition-all hover:bg-primary/5">
              <div className="space-y-1">
                <Label className="font-heading font-bold text-sm tracking-tight">Critical Escalation</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">Notify global supervisors immediately for LINE STOP protocols</p>
              </div>
              <Switch defaultChecked className="data-[state=checked]:bg-primary" />
            </div>
            <div className="flex items-center justify-between p-5 rounded-2xl bg-muted/10 border border-border/5 group transition-all hover:bg-primary/5">
              <div className="space-y-1">
                <Label className="font-heading font-bold text-sm tracking-tight">Quality Abnormalities</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">Notify Quality Engineer node after 5 mins of unresolved state</p>
              </div>
              <Switch defaultChecked className="data-[state=checked]:bg-primary" />
            </div>
            <div className="flex items-center justify-between p-5 rounded-2xl bg-muted/10 border border-border/5 group transition-all hover:bg-primary/5">
              <div className="space-y-1">
                <Label className="font-heading font-bold text-sm tracking-tight">Maintenance Dispatch</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">Initiate immediate technician node request for machine breakdowns</p>
              </div>
              <Switch defaultChecked className="data-[state=checked]:bg-primary" />
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium">
          <CardHeader className="pb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary shadow-sm">
                <Volume2 className="h-5 w-5" />
              </div>
              <CardTitle className="text-lg font-heading">Protocol Channels</CardTitle>
            </div>
            <CardDescription className="text-xs font-medium uppercase tracking-wider pl-11">Multi-modal signal delivery methods</CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            <div className="flex items-center justify-between p-5 rounded-2xl bg-muted/10 border border-border/5 group transition-all hover:bg-primary/5">
              <div className="space-y-1">
                <Label className="font-heading font-bold text-sm tracking-tight">Visual Command Mesh</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">Flash strategic warnings on all synchronized shop floor monitors</p>
              </div>
              <Switch defaultChecked className="data-[state=checked]:bg-primary" />
            </div>
            <div className="flex items-center justify-between p-5 rounded-2xl bg-muted/10 border border-border/5 group transition-all hover:bg-primary/5">
              <div className="space-y-1">
                <Label className="font-heading font-bold text-sm tracking-tight">Mobile SMS Gateway</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">Dispatch text alerts to active on-call intelligence nodes</p>
              </div>
              <Switch className="data-[state=checked]:bg-primary" />
            </div>
            <div className="flex items-center justify-between p-5 rounded-2xl bg-muted/10 border border-border/5 group transition-all hover:bg-primary/5">
              <div className="space-y-1">
                <Label className="font-heading font-bold text-sm tracking-tight">OS Intelligence Push</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">Show native browser notifications for active organizational alerts</p>
              </div>
              <Switch defaultChecked className="data-[state=checked]:bg-primary" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
