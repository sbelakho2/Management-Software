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
import { useI18n } from '@/contexts/i18n-context';
export default function AndonSettingsPage() {
  const { t } = useI18n();
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
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">{t('andon.settings.title') || 'Signal Configuration'}</h1>
            <p className="text-muted-foreground font-medium text-sm">{t('andon.settings.subtitle') || 'Configure multi-channel alerts and organizational response protocols'}</p>
          </div>
        </div>
        <Button size="lg" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-12 px-8" onClick={handleSubmit} disabled={isSubmitting}>
          <Save className="h-4 w-4 mr-2" />
          {isSubmitting ? (t('andon.settings.calibrating') || 'Calibrating...') : (t('andon.settings.saveConfiguration') || 'Save Configuration')}
        </Button>
      </div>
      <div className="grid gap-8">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
          <CardHeader className="pb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-rams-panel border border-rams-line text-rams-orange">
                <Bell className="h-5 w-5" />
              </div>
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('andon.settings.notificationIntelligence.title') || 'Notification Intelligence'}</CardTitle>
            </div>
            <CardDescription className="text-xs font-medium uppercase tracking-wider pl-11">{t('andon.settings.notificationIntelligence.subtitle') || 'Strategic routing for anomalous signals'}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            <div className="flex items-center justify-between p-5 bg-rams-panel border border-rams-line group transition-none hover:bg-rams-panel/50">
              <div className="space-y-1">
                <Label className="text-[11px] font-black uppercase tracking-tight">{t('andon.settings.notificationIntelligence.criticalEscalation') || 'Critical Escalation'}</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{t('andon.settings.notificationIntelligence.criticalEscalationDesc') || 'Notify global supervisors immediately for LINE STOP protocols'}</p>
              </div>
              <Switch defaultChecked className="data-[state=checked]:bg-rams-orange" />
            </div>
            <div className="flex items-center justify-between p-5 bg-rams-panel border border-rams-line group transition-none hover:bg-rams-panel/50">
              <div className="space-y-1">
                <Label className="text-[11px] font-black uppercase tracking-tight">{t('andon.settings.notificationIntelligence.qualityAbnormalities') || 'Quality Abnormalities'}</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{t('andon.settings.notificationIntelligence.qualityAbnormalitiesDesc') || 'Notify Quality Engineer node after 5 mins of unresolved state'}</p>
              </div>
              <Switch defaultChecked className="data-[state=checked]:bg-rams-orange" />
            </div>
            <div className="flex items-center justify-between p-5 bg-rams-panel border border-rams-line group transition-none hover:bg-rams-panel/50">
              <div className="space-y-1">
                <Label className="text-[11px] font-black uppercase tracking-tight">{t('andon.settings.notificationIntelligence.maintenanceDispatch') || 'Maintenance Dispatch'}</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{t('andon.settings.notificationIntelligence.maintenanceDispatchDesc') || 'Initiate immediate technician node request for machine breakdowns'}</p>
              </div>
              <Switch defaultChecked className="data-[state=checked]:bg-rams-orange" />
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
          <CardHeader className="pb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-rams-panel border border-rams-line text-rams-orange">
                <Volume2 className="h-5 w-5" />
              </div>
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('andon.settings.protocolChannels.title') || 'Protocol Channels'}</CardTitle>
            </div>
            <CardDescription className="text-xs font-medium uppercase tracking-wider pl-11">{t('andon.settings.protocolChannels.subtitle') || 'Multi-modal signal delivery methods'}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            <div className="flex items-center justify-between p-5 bg-rams-panel border border-rams-line group transition-none hover:bg-rams-panel/50">
              <div className="space-y-1">
                <Label className="text-[11px] font-black uppercase tracking-tight">{t('andon.settings.protocolChannels.visualCommandMesh') || 'Visual Command Mesh'}</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{t('andon.settings.protocolChannels.visualCommandMeshDesc') || 'Flash strategic warnings on all synchronized shop floor monitors'}</p>
              </div>
              <Switch defaultChecked className="data-[state=checked]:bg-rams-orange" />
            </div>
            <div className="flex items-center justify-between p-5 bg-rams-panel border border-rams-line group transition-none hover:bg-rams-panel/50">
              <div className="space-y-1">
                <Label className="text-[11px] font-black uppercase tracking-tight">{t('andon.settings.protocolChannels.mobileSmsGateway') || 'Mobile SMS Gateway'}</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{t('andon.settings.protocolChannels.mobileSmsGatewayDesc') || 'Dispatch text alerts to active on-call intelligence nodes'}</p>
              </div>
              <Switch className="data-[state=checked]:bg-rams-orange" />
            </div>
            <div className="flex items-center justify-between p-5 bg-rams-panel border border-rams-line group transition-none hover:bg-rams-panel/50">
              <div className="space-y-1">
                <Label className="text-[11px] font-black uppercase tracking-tight">{t('andon.settings.protocolChannels.osIntelligencePush') || 'OS Intelligence Push'}</Label>
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{t('andon.settings.protocolChannels.osIntelligencePushDesc') || 'Show native browser notifications for active organizational alerts'}</p>
              </div>
              <Switch defaultChecked className="data-[state=checked]:bg-rams-orange" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
