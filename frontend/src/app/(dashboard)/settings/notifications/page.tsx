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
import { useI18n } from '@/contexts/i18n-context';

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
    <div className="flex flex-col sm:flex-row sm:items-center justify-between py-6 border-b border-rams-line/40 last:border-0 group transition-none">
      <div className="flex items-start gap-4 mb-4 sm:mb-0">
        <div className={cn('p-3 rounded-none border border-rams-line transition-none', critical ? 'bg-rams-red/10 text-rams-red' : 'bg-rams-panel text-rams-orange')}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="space-y-1">
          <p className="font-heading font-bold text-sm tracking-tight">{label}</p>
          <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">{description}</p>
        </div>
      </div>
      <div className="flex items-center gap-8 bg-rams-panel/30 p-3 rounded-none border border-rams-line">
        <div className="flex items-center gap-3">
          <Mail className={cn('h-4 w-4 transition-none', value.email ? 'text-rams-orange' : 'text-muted-foreground/40')} />
          <Switch 
            checked={value.email} 
            onCheckedChange={() => toggle('email')}
            disabled={critical && value.email}
          />
        </div>
        <div className="flex items-center gap-3 border-l border-rams-line/40 pl-8">
          <Smartphone className={cn('h-4 w-4 transition-none', value.push ? 'text-rams-orange' : 'text-muted-foreground/40')} />
          <Switch 
            checked={value.push} 
            onCheckedChange={() => toggle('push')}
          />
        </div>
        <div className="flex items-center gap-3 border-l border-rams-line/40 pl-8">
          <Bell className={cn('h-4 w-4 transition-none', value.inApp ? 'text-rams-orange' : 'text-muted-foreground/40')} />
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
  const { t } = useI18n();
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
    <div className="space-y-8 animate-in fade-in duration-150 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              {t('settings.notifications.title')}
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">{t('settings.notifications.subtitle')}</p>
          </div>
        </div>
        <Button onClick={handleSave} disabled={isSaving} className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none" size="default">
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
              {t('settings.notifications.calibrating')}
            </>
          ) : (
            <>
              <Save className="mr-2 h-3.5 w-3.5" />
              {t('settings.notifications.saveRouting')}
            </>
          )}
        </Button>
      </div>

      {/* RFQ & Quotes */}
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden">
        <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
            <FileText className="h-4 w-4 text-rams-orange" />
            {t('settings.notifications.pipelineCommerce')}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <NotificationRow
            label={t('settings.notifications.inboundRfqSignal')}
            description={t('settings.notifications.inboundRfqSignalDesc')}
            icon={FileText}
            value={settings.newRfq}
            onChange={(v) => handleChange('newRfq', v)}
          />
          <NotificationRow
            label={t('settings.notifications.approvalRequest')}
            description={t('settings.notifications.approvalRequestDesc')}
            icon={CheckCircle}
            value={settings.quoteApproval}
            onChange={(v) => handleChange('quoteApproval', v)}
          />
          <NotificationRow
            label={t('settings.notifications.commerceOutcome')}
            description={t('settings.notifications.commerceOutcomeDesc')}
            icon={Package}
            value={settings.quoteWonLost}
            onChange={(v) => handleChange('quoteWonLost', v)}
          />
        </CardContent>
      </Card>

      {/* Quality */}
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden">
        <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
            <Shield className="h-4 w-4 text-rams-orange" />
            {t('settings.notifications.qualityAssuranceAlerts')}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <NotificationRow
            label={t('settings.notifications.abnormalityDetected')}
            description={t('settings.notifications.abnormalityDetectedDesc')}
            icon={AlertTriangle}
            value={settings.ncrCreated}
            onChange={(v) => handleChange('ncrCreated', v)}
            critical
          />
          <NotificationRow
            label={t('settings.notifications.resolutionProtocol')}
            description={t('settings.notifications.resolutionProtocolDesc')}
            icon={CheckCircle}
            value={settings.capaAssigned}
            onChange={(v) => handleChange('capaAssigned', v)}
          />
          <NotificationRow
            label={t('settings.notifications.inspectionThreshold')}
            description={t('settings.notifications.inspectionThresholdDesc')}
            icon={CheckCircle}
            value={settings.inspectionDue}
            onChange={(v) => handleChange('inspectionDue', v)}
          />
        </CardContent>
      </Card>

      {/* Production */}
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden">
        <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
            <Package className="h-4 w-4 text-rams-orange" />
            {t('settings.notifications.productionFloorTelemetry')}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <NotificationRow
            label={t('settings.notifications.workOrderEvolution')}
            description={t('settings.notifications.workOrderEvolutionDesc')}
            icon={Package}
            value={settings.workOrderStatus}
            onChange={(v) => handleChange('workOrderStatus', v)}
          />
          <NotificationRow
            label={t('settings.notifications.andonEscalation')}
            description={t('settings.notifications.andonEscalationDesc')}
            icon={AlertTriangle}
            value={settings.andonAlert}
            onChange={(v) => handleChange('andonAlert', v)}
            critical
          />
        </CardContent>
      </Card>

      {/* Digest */}
      <Card className="rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden">
        <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
          <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
            <Mail className="h-4 w-4 text-rams-orange" />
            {t('settings.notifications.strategicSummaries')}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-1">
          <div className="flex items-center justify-between p-5 rounded-none bg-rams-panel/20 border border-rams-line group">
            <div>
              <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t('settings.notifications.dailyCommandSummary')}</p>
              <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">{t('settings.notifications.dailyCommandSummaryDesc')}</p>
            </div>
            <Switch 
              checked={settings.dailyDigest} 
              onCheckedChange={(v) => handleChange('dailyDigest', v)}
            />
          </div>
          <div className="flex items-center justify-between p-5 rounded-none bg-rams-panel/20 border border-rams-line group">
            <div>
              <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t('settings.notifications.weeklyPerformanceIntelligence')}</p>
              <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">{t('settings.notifications.weeklyPerformanceIntelligenceDesc')}</p>
            </div>
            <Switch 
              checked={settings.weeklyReport} 
              onCheckedChange={(v) => handleChange('weeklyReport', v)}
            />
          </div>
          <div className="flex items-center justify-between p-5 rounded-none bg-rams-panel border border-rams-line">
            <Label htmlFor="digestTime" className="flex-1">
              <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{t('settings.notifications.dispatchSynchronization')}</p>
              <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">{t('settings.notifications.dispatchSynchronizationDesc')}</p>
            </Label>
            <Select 
              value={settings.digestTime} 
              onValueChange={(v) => handleChange('digestTime', v)}
            >
              <SelectTrigger id="digestTime" className="w-48 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[10px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="06:00">{t('settings.notifications.digestTimeOptions.0600')}</SelectItem>
                <SelectItem value="07:00">{t('settings.notifications.digestTimeOptions.0700')}</SelectItem>
                <SelectItem value="08:00">{t('settings.notifications.digestTimeOptions.0800')}</SelectItem>
                <SelectItem value="09:00">{t('settings.notifications.digestTimeOptions.0900')}</SelectItem>
                <SelectItem value="18:00">{t('settings.notifications.digestTimeOptions.1800')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
