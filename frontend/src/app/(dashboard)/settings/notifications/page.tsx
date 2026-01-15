'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Bell,
  Mail,
  Smartphone,
  MessageSquare,
  AlertTriangle,
  CheckCircle,
  FileText,
  Package,
  Shield,
  Users,
  Save,
  Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { cn } from '@/lib/utils';

interface NotificationChannel {
  email: boolean;
  push: boolean;
  inApp: boolean;
}

interface NotificationSettings {
  // RFQ & Quotes
  newRfq: NotificationChannel;
  quoteApproval: NotificationChannel;
  quoteWonLost: NotificationChannel;
  
  // Quality
  ncrCreated: NotificationChannel;
  capaAssigned: NotificationChannel;
  inspectionDue: NotificationChannel;
  
  // Production
  workOrderStatus: NotificationChannel;
  andonAlert: NotificationChannel;
  
  // General
  taskAssigned: NotificationChannel;
  mentionedInComment: NotificationChannel;
  
  // System
  securityAlerts: NotificationChannel;
  systemUpdates: NotificationChannel;
  
  // Digest
  dailyDigest: boolean;
  weeklyReport: boolean;
  digestTime: string;
}

const defaultSettings: NotificationSettings = {
  newRfq: { email: true, push: true, inApp: true },
  quoteApproval: { email: true, push: true, inApp: true },
  quoteWonLost: { email: true, push: false, inApp: true },
  
  ncrCreated: { email: true, push: true, inApp: true },
  capaAssigned: { email: true, push: true, inApp: true },
  inspectionDue: { email: true, push: false, inApp: true },
  
  workOrderStatus: { email: false, push: true, inApp: true },
  andonAlert: { email: true, push: true, inApp: true },
  
  taskAssigned: { email: true, push: true, inApp: true },
  mentionedInComment: { email: true, push: true, inApp: true },
  
  securityAlerts: { email: true, push: true, inApp: true },
  systemUpdates: { email: true, push: false, inApp: true },
  
  dailyDigest: true,
  weeklyReport: true,
  digestTime: '08:00',
};

interface NotificationRowProps {
  label: string;
  description: string;
  icon: typeof Bell;
  value: NotificationChannel;
  onChange: (channel: NotificationChannel) => void;
  critical?: boolean;
}

function NotificationRow({ label, description, icon: Icon, value, onChange, critical }: NotificationRowProps) {
  const toggle = (key: keyof NotificationChannel) => {
    // Don't allow disabling critical notifications
    if (critical && key === 'email' && value.email) return;
    onChange({ ...value, [key]: !value[key] });
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between py-6 border-b border-border/40 last:border-0 group transition-all">
      <div className="flex items-start gap-4 mb-4 sm:mb-0">
        <div className={cn('p-3 rounded-2xl shadow-sm transition-transform duration-300 group-hover:scale-110', critical ? 'bg-danger/10 text-danger' : 'bg-primary/5 text-primary')}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="space-y-1">
          <p className="font-heading font-bold text-sm tracking-tight">{label}</p>
          <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">{description}</p>
        </div>
      </div>
      <div className="flex items-center gap-8 bg-muted/30 p-3 rounded-2xl border border-border/40">
        <div className="flex items-center gap-3">
          <Mail className={cn('h-4 w-4 transition-colors', value.email ? 'text-primary' : 'text-muted-foreground/40')} />
          <Switch 
            checked={value.email} 
            onCheckedChange={() => toggle('email')}
            disabled={critical && value.email}
            className="data-[state=checked]:bg-primary"
          />
        </div>
        <div className="flex items-center gap-3 border-l border-border/40 pl-8">
          <Smartphone className={cn('h-4 w-4 transition-colors', value.push ? 'text-primary' : 'text-muted-foreground/40')} />
          <Switch 
            checked={value.push} 
            onCheckedChange={() => toggle('push')}
            className="data-[state=checked]:bg-primary"
          />
        </div>
        <div className="flex items-center gap-3 border-l border-border/40 pl-8">
          <Bell className={cn('h-4 w-4 transition-colors', value.inApp ? 'text-primary' : 'text-muted-foreground/40')} />
          <Switch 
            checked={value.inApp} 
            onCheckedChange={() => toggle('inApp')}
            className="data-[state=checked]:bg-primary"
          />
        </div>
      </div>
    </div>
  );
}

export default function NotificationsSettingsPage() {
  const router = useRouter();
  const [isSaving, setIsSaving] = React.useState(false);
  const [settings, setSettings] = React.useState<NotificationSettings>(defaultSettings);

  const handleChange = <K extends keyof NotificationSettings>(
    key: K, 
    value: NotificationSettings[K]
  ) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
  };

  return (
    <div className="space-y-8 page-fade-in max-w-4xl">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 hover:text-primary transition-all" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              Notification Center
            </h1>
            <p className="text-muted-foreground font-medium text-sm">Configure multi-channel intelligence dispatch parameters</p>
          </div>
        </div>
        <Button onClick={handleSave} disabled={isSaving} className="rounded-2xl shadow-glow subtle-shine h-12 px-8" size="lg">
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Calibrating...
            </>
          ) : (
            <>
              <Save className="mr-2 h-5 w-5" />
              Save Routing
            </>
          )}
        </Button>
      </div>

      {/* Channel Legend */}
      <Card className="bg-primary/[0.02] border-primary/10">
        <CardContent className="py-5">
          <div className="flex flex-wrap items-center gap-8 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">
            <span className="text-primary/60">Intelligence Channels:</span>
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-primary/5"><Mail className="h-3.5 w-3.5" /></div>
              <span>Email Protocol</span>
            </div>
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-primary/5"><Smartphone className="h-3.5 w-3.5" /></div>
              <span>Mobile Push</span>
            </div>
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-primary/5"><Bell className="h-3.5 w-3.5" /></div>
              <span>OS Console</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* RFQ & Quotes */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading flex items-center gap-3">
            <FileText className="h-5 w-5 text-primary/60" />
            Pipeline & Commerce
          </CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Alerts related to RFQ velocity and quotation approvals</CardDescription>
        </CardHeader>
        <CardContent className="pt-0">
          <NotificationRow
            label="Inbound RFQ Signal"
            description="When a new RFQ enters the pipeline or is assigned"
            icon={FileText}
            value={settings.newRfq}
            onChange={(v) => handleChange('newRfq', v)}
          />
          <NotificationRow
            label="Approval Request"
            description="When a quotation requires strategic sign-off"
            icon={CheckCircle}
            value={settings.quoteApproval}
            onChange={(v) => handleChange('quoteApproval', v)}
          />
          <NotificationRow
            label="Commerce Outcome"
            description="When a quote reaches a terminal won/lost state"
            icon={Package}
            value={settings.quoteWonLost}
            onChange={(v) => handleChange('quoteWonLost', v)}
          />
        </CardContent>
      </Card>

      {/* Quality */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading flex items-center gap-3">
            <Shield className="h-5 w-5 text-primary/60" />
            Quality Assurance
          </CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Signals for non-conformances and inspection gates</CardDescription>
        </CardHeader>
        <CardContent className="pt-0">
          <NotificationRow
            label="Abnormality Detected (NCR)"
            description="When a new non-conformance protocol is initiated"
            icon={AlertTriangle}
            value={settings.ncrCreated}
            onChange={(v) => handleChange('ncrCreated', v)}
            critical
          />
          <NotificationRow
            label="Resolution Protocol (CAPA)"
            description="When a corrective action is assigned for execution"
            icon={CheckCircle}
            value={settings.capaAssigned}
            onChange={(v) => handleChange('capaAssigned', v)}
          />
          <NotificationRow
            label="Inspection Threshold"
            description="Reminders for upcoming quality gate synchronizations"
            icon={CheckCircle}
            value={settings.inspectionDue}
            onChange={(v) => handleChange('inspectionDue', v)}
          />
        </CardContent>
      </Card>

      {/* Production */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading flex items-center gap-3">
            <Package className="h-5 w-5 text-primary/60" />
            Production Floor
          </CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Real-time status changes and factory floor alerts</CardDescription>
        </CardHeader>
        <CardContent className="pt-0">
          <NotificationRow
            label="Work Order Evolution"
            description="Status transitions on tracked production orders"
            icon={Package}
            value={settings.workOrderStatus}
            onChange={(v) => handleChange('workOrderStatus', v)}
          />
          <NotificationRow
            label="Andon Escalation"
            description="Immediate production line alerts requiring attention"
            icon={AlertTriangle}
            value={settings.andonAlert}
            onChange={(v) => handleChange('andonAlert', v)}
            critical
          />
        </CardContent>
      </Card>

      {/* Digest */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading flex items-center gap-3">
            <Mail className="h-5 w-5 text-primary/60" />
            Strategic Digests
          </CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Synchronized periodic intelligence summaries</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between p-5 rounded-2xl bg-muted/30 border border-border/40">
            <div>
              <p className="font-heading font-bold tracking-tight">Daily Command Summary</p>
              <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">Briefing of previous day activity and pending tasks</p>
            </div>
            <Switch 
              checked={settings.dailyDigest} 
              onCheckedChange={(v) => handleChange('dailyDigest', v)}
              className="data-[state=checked]:bg-primary"
            />
          </div>
          <div className="flex items-center justify-between p-5 rounded-2xl bg-muted/30 border border-border/40">
            <div>
              <p className="font-heading font-bold tracking-tight">Weekly Performance Intelligence</p>
              <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">Aggregate metrics and organizational velocity report</p>
            </div>
            <Switch 
              checked={settings.weeklyReport} 
              onCheckedChange={(v) => handleChange('weeklyReport', v)}
              className="data-[state=checked]:bg-primary"
            />
          </div>
          <div className="flex items-center justify-between p-5 rounded-2xl bg-primary/[0.02] border border-primary/10">
            <Label htmlFor="digestTime" className="flex-1">
              <p className="font-heading font-bold tracking-tight">Dispatch Synchronization</p>
              <p className="text-[10px] uppercase tracking-widest font-bold text-primary/60">Target delivery time for daily intelligence briefing</p>
            </Label>
            <Select 
              value={settings.digestTime} 
              onValueChange={(v) => handleChange('digestTime', v)}
            >
              <SelectTrigger id="digestTime" className="w-40 h-12 rounded-xl bg-background border-border/50">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="rounded-2xl shadow-premium">
                <SelectItem value="06:00" className="rounded-xl m-1">06:00 AM (Sunrise)</SelectItem>
                <SelectItem value="07:00" className="rounded-xl m-1">07:00 AM</SelectItem>
                <SelectItem value="08:00" className="rounded-xl m-1">08:00 AM (Shift Start)</SelectItem>
                <SelectItem value="09:00" className="rounded-xl m-1">09:00 AM</SelectItem>
                <SelectItem value="18:00" className="rounded-xl m-1">06:00 PM (Shift End)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
