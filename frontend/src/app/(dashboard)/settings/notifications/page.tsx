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
    <div className="flex items-center justify-between py-4 border-b last:border-0">
      <div className="flex items-start gap-3">
        <div className={cn('p-2 rounded-lg', critical ? 'bg-danger/10' : 'bg-muted')}>
          <Icon className={cn('h-4 w-4', critical ? 'text-danger' : 'text-muted-foreground')} />
        </div>
        <div>
          <p className="font-medium text-sm">{label}</p>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Mail className={cn('h-4 w-4', value.email ? 'text-primary' : 'text-muted-foreground')} />
          <Switch 
            checked={value.email} 
            onCheckedChange={() => toggle('email')}
            disabled={critical && value.email}
          />
        </div>
        <div className="flex items-center gap-2">
          <Smartphone className={cn('h-4 w-4', value.push ? 'text-primary' : 'text-muted-foreground')} />
          <Switch 
            checked={value.push} 
            onCheckedChange={() => toggle('push')}
          />
        </div>
        <div className="flex items-center gap-2">
          <Bell className={cn('h-4 w-4', value.inApp ? 'text-primary' : 'text-muted-foreground')} />
          <Switch 
            checked={value.inApp} 
            onCheckedChange={() => toggle('inApp')}
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
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push('/settings')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Notification Settings</h1>
          <p className="text-muted-foreground">Choose how you want to be notified</p>
        </div>
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Save Changes
            </>
          )}
        </Button>
      </div>

      {/* Channel Legend */}
      <Card className="bg-muted/50">
        <CardContent className="py-4">
          <div className="flex items-center gap-6 text-sm">
            <span className="text-muted-foreground">Notification channels:</span>
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4" />
              <span>Email</span>
            </div>
            <div className="flex items-center gap-2">
              <Smartphone className="h-4 w-4" />
              <span>Push</span>
            </div>
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              <span>In-App</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* RFQ & Quotes */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4" />
            RFQ & Quotes
          </CardTitle>
          <CardDescription>Notifications related to requests for quotes and quotations</CardDescription>
        </CardHeader>
        <CardContent>
          <NotificationRow
            label="New RFQ Received"
            description="When a new RFQ is created or assigned to you"
            icon={FileText}
            value={settings.newRfq}
            onChange={(v) => handleChange('newRfq', v)}
          />
          <NotificationRow
            label="Quote Approval Required"
            description="When a quote needs your approval"
            icon={CheckCircle}
            value={settings.quoteApproval}
            onChange={(v) => handleChange('quoteApproval', v)}
          />
          <NotificationRow
            label="Quote Won/Lost"
            description="When a quote status changes to won or lost"
            icon={Package}
            value={settings.quoteWonLost}
            onChange={(v) => handleChange('quoteWonLost', v)}
          />
        </CardContent>
      </Card>

      {/* Quality */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Quality Management
          </CardTitle>
          <CardDescription>NCRs, CAPAs, and inspection notifications</CardDescription>
        </CardHeader>
        <CardContent>
          <NotificationRow
            label="NCR Created"
            description="When a new non-conformance is reported"
            icon={AlertTriangle}
            value={settings.ncrCreated}
            onChange={(v) => handleChange('ncrCreated', v)}
            critical
          />
          <NotificationRow
            label="CAPA Assigned"
            description="When a CAPA is assigned to you"
            icon={CheckCircle}
            value={settings.capaAssigned}
            onChange={(v) => handleChange('capaAssigned', v)}
          />
          <NotificationRow
            label="Inspection Due"
            description="Reminders for upcoming inspections"
            icon={CheckCircle}
            value={settings.inspectionDue}
            onChange={(v) => handleChange('inspectionDue', v)}
          />
        </CardContent>
      </Card>

      {/* Production */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Package className="h-4 w-4" />
            Production
          </CardTitle>
          <CardDescription>Work orders and production alerts</CardDescription>
        </CardHeader>
        <CardContent>
          <NotificationRow
            label="Work Order Status"
            description="Status changes on work orders you're following"
            icon={Package}
            value={settings.workOrderStatus}
            onChange={(v) => handleChange('workOrderStatus', v)}
          />
          <NotificationRow
            label="Andon Alerts"
            description="Production line alerts and escalations"
            icon={AlertTriangle}
            value={settings.andonAlert}
            onChange={(v) => handleChange('andonAlert', v)}
            critical
          />
        </CardContent>
      </Card>

      {/* General */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4" />
            Collaboration
          </CardTitle>
          <CardDescription>Tasks, mentions, and team activity</CardDescription>
        </CardHeader>
        <CardContent>
          <NotificationRow
            label="Task Assigned"
            description="When a task is assigned to you"
            icon={CheckCircle}
            value={settings.taskAssigned}
            onChange={(v) => handleChange('taskAssigned', v)}
          />
          <NotificationRow
            label="Mentioned in Comment"
            description="When someone @mentions you in a comment"
            icon={MessageSquare}
            value={settings.mentionedInComment}
            onChange={(v) => handleChange('mentionedInComment', v)}
          />
        </CardContent>
      </Card>

      {/* System */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4" />
            System
          </CardTitle>
          <CardDescription>Security and system notifications</CardDescription>
        </CardHeader>
        <CardContent>
          <NotificationRow
            label="Security Alerts"
            description="Login attempts and security events"
            icon={Shield}
            value={settings.securityAlerts}
            onChange={(v) => handleChange('securityAlerts', v)}
            critical
          />
          <NotificationRow
            label="System Updates"
            description="New features and maintenance notices"
            icon={Bell}
            value={settings.systemUpdates}
            onChange={(v) => handleChange('systemUpdates', v)}
          />
        </CardContent>
      </Card>

      {/* Digest */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Email Digest
          </CardTitle>
          <CardDescription>Periodic summary emails</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-medium text-sm">Daily Digest</p>
              <p className="text-xs text-muted-foreground">Summary of daily activity and pending items</p>
            </div>
            <Switch 
              checked={settings.dailyDigest} 
              onCheckedChange={(v) => handleChange('dailyDigest', v)}
            />
          </div>
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-medium text-sm">Weekly Report</p>
              <p className="text-xs text-muted-foreground">Weekly metrics and team performance summary</p>
            </div>
            <Switch 
              checked={settings.weeklyReport} 
              onCheckedChange={(v) => handleChange('weeklyReport', v)}
            />
          </div>
          <div className="flex items-center justify-between py-2">
            <Label htmlFor="digestTime" className="flex-1">
              <p className="font-medium text-sm">Digest Time</p>
              <p className="text-xs text-muted-foreground">When to send daily digest emails</p>
            </Label>
            <Select 
              value={settings.digestTime} 
              onValueChange={(v) => handleChange('digestTime', v)}
            >
              <SelectTrigger id="digestTime" className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="06:00">6:00 AM</SelectItem>
                <SelectItem value="07:00">7:00 AM</SelectItem>
                <SelectItem value="08:00">8:00 AM</SelectItem>
                <SelectItem value="09:00">9:00 AM</SelectItem>
                <SelectItem value="18:00">6:00 PM</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
