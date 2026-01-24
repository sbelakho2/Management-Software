'use client';

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  ArrowLeft,
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  ShieldCheck,
  MessageSquare,
  Save,
  Lock
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useI18n } from '@/contexts/i18n-context';
import { useQuotingHelperStore, DisciplineType, WorkPacket } from '@/stores/quoting-helper';
import { cn } from '@/lib/utils';
import { PageGuard } from '@/components/layout/page-guard';

export default function DisciplinePacketPage() {
  return <DisciplinePacketContent />;
}

function DisciplinePacketContent() {
  const { id: packetId } = useParams();
  const router = useRouter();
  const { t } = useI18n();
  const { workPackets, updateWorkPacket } = useQuotingHelperStore();
  
  const packet = workPackets.find(p => p.id === packetId);
  const [outputs, setOutputs] = React.useState<any>(packet?.outputs || {});
  const [isSaving, setIsSaving] = React.useState(false);

  if (!packet) {
    return <div className="p-8 text-[10px] uppercase font-mono">{t('common.quotingHelper.packet.packetNotFound')}</div>;
  }

  const handleSave = async (newStatus?: string) => {
    setIsSaving(true);
    await updateWorkPacket(packet.id, { 
      outputs, 
      status: (newStatus as any) || packet.status 
    });
    setIsSaving(false);
  };

  const renderDisciplineForm = () => {
    switch (packet.discipline) {
      case 'ee':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.ee.form.minFinePitch')}</Label>
                <Input 
                  type="number" 
                  step="0.01"
                  value={outputs.fine_pitch_min_mm || ''} 
                  onChange={e => setOutputs({...outputs, fine_pitch_min_mm: e.target.value})}
                  className="bg-rams-panel border-rams-line font-mono"
                />
              </div>
              <div className="flex items-center space-x-2 pt-8">
                <input 
                  type="checkbox" 
                  id="needs_xray"
                  className="h-4 w-4 rounded-none border-rams-line text-rams-orange focus:ring-rams-orange"
                  checked={outputs.needs_xray || false}
                  onChange={e => setOutputs({...outputs, needs_xray: e.target.checked})}
                />
                <Label htmlFor="needs_xray" className="text-[10px] uppercase font-black tracking-widest cursor-pointer">{t('common.disciplines.ee.form.requiresXray')}</Label>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.ee.form.dfmFindings')}</Label>
              <Textarea 
                value={outputs.dfm_findings || ''}
                onChange={e => setOutputs({...outputs, dfm_findings: e.target.value})}
                className="bg-rams-panel border-rams-line font-mono min-h-[120px]"
                placeholder={t('common.disciplines.ee.form.dfmPlaceholder')}
              />
            </div>
          </div>
        );
      case 'embedded':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.embedded.form.programmingMinutes')}</Label>
                <Input 
                  type="number" 
                  value={outputs.programming_minutes || ''} 
                  onChange={e => setOutputs({...outputs, programming_minutes: e.target.value})}
                  className="bg-rams-panel border-rams-line font-mono"
                />
              </div>
              <div className="flex items-center space-x-2 pt-8">
                <input 
                  type="checkbox" 
                  id="fixture_needed"
                  className="h-4 w-4 rounded-none border-rams-line text-rams-orange focus:ring-rams-orange"
                  checked={outputs.fixture_needed || false}
                  onChange={e => setOutputs({...outputs, fixture_needed: e.target.checked})}
                />
                <Label htmlFor="fixture_needed" className="text-[10px] uppercase font-black tracking-widest cursor-pointer">{t('common.disciplines.embedded.form.fixtureNeeded')}</Label>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.embedded.form.ipConstraints')}</Label>
              <Textarea 
                value={outputs.ip_constraints || ''}
                onChange={e => setOutputs({...outputs, ip_constraints: e.target.value})}
                className="bg-rams-panel border-rams-line font-mono h-24"
              />
            </div>
          </div>
        );
      case 'me':
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.me.form.enclosureRisks')}</Label>
              <Textarea 
                value={outputs.enclosure_risks || ''}
                onChange={e => setOutputs({...outputs, enclosure_risks: e.target.value})}
                className="bg-rams-panel border-rams-line font-mono h-32"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.me.form.labelingMethod')}</Label>
              <Input 
                value={outputs.labeling_method || ''} 
                onChange={e => setOutputs({...outputs, labeling_method: e.target.value})}
                className="bg-rams-panel border-rams-line font-mono"
              />
            </div>
          </div>
        );
      case 'mfge':
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.mfge.form.lineAssignment')}</Label>
              <Input 
                value={outputs.line_assignment || ''} 
                onChange={e => setOutputs({...outputs, line_assignment: e.target.value})}
                className="bg-rams-panel border-rams-line font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.mfge.form.specialTraining')}</Label>
              <Textarea 
                value={outputs.special_training || ''}
                onChange={e => setOutputs({...outputs, special_training: e.target.value})}
                className="bg-rams-panel border-rams-line font-mono h-32"
              />
            </div>
          </div>
        );
      case 'qe':
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.qe.form.inspectionLevel')}</Label>
              <Input 
                value={outputs.inspection_level || ''} 
                onChange={e => setOutputs({...outputs, inspection_level: e.target.value})}
                className="bg-rams-panel border-rams-line font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.qe.form.complianceDocs')}</Label>
              <Textarea 
                value={outputs.compliance_docs || ''}
                onChange={e => setOutputs({...outputs, compliance_docs: e.target.value})}
                className="bg-rams-panel border-rams-line font-mono h-32"
              />
            </div>
          </div>
        );
      case 'purchasing':
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.purchasing.form.topCostDrivers')}</Label>
              <Textarea 
                value={outputs.top_cost_drivers || ''}
                onChange={e => setOutputs({...outputs, top_cost_drivers: e.target.value})}
                className="bg-rams-panel border-rams-line font-mono h-24"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{t('common.disciplines.purchasing.form.longLeadMitigation')}</Label>
              <Textarea 
                value={outputs.long_lead_mitigation || ''}
                onChange={e => setOutputs({...outputs, long_lead_mitigation: e.target.value})}
                className="bg-rams-panel border-rams-line font-mono h-24"
              />
            </div>
          </div>
        );
      default:
        return (
          <div className="space-y-4">
            <p className="text-[10px] uppercase font-mono text-muted-foreground">{t('common.quotingHelper.packet.genericDiscipline', { discipline: packet.discipline })}</p>
            <Textarea 
              value={JSON.stringify(outputs, null, 2)}
              onChange={e => {
                try { setOutputs(JSON.parse(e.target.value)); } catch(e) {}
              }}
              className="bg-rams-panel border-rams-line font-mono h-64"
            />
          </div>
        );
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.back()} className="text-[10px] uppercase font-black hover:text-rams-orange">
          <ArrowLeft className="mr-2 h-3.5 w-3.5" /> {t('common.quotingHelper.packet.backToWorkbench')}
        </Button>
        <div className="flex gap-2">
          <Badge variant="outline" className="bg-rams-panel border-rams-line text-[10px] font-mono">
            {packet.due_at ? t('common.quotingHelper.packet.sla', { date: new Date(packet.due_at).toLocaleDateString() }) : t('common.quotingHelper.packet.noDeadline')}
          </Badge>
          <Badge className={cn(
            "text-[10px] font-mono uppercase",
            packet.status === 'done' ? "bg-rams-green/10 text-rams-green" : "bg-rams-orange/10 text-rams-orange"
          )}>
            {packet.status}
          </Badge>
        </div>
      </div>

      <div className="bg-rams-panel p-8 border border-rams-line space-y-2">
        <h1 className="text-3xl font-black uppercase italic tracking-tighter flex items-center gap-4">
          {t('common.quotingHelper.packet.reviewPacket', { discipline: t(`common.disciplines.${packet.discipline}.title`) })}
          {packet.status === 'done' && <ShieldCheck className="h-8 w-8 text-rams-green" />}
        </h1>
        <p className="text-xs text-muted-foreground uppercase tracking-[0.2em]">{t('common.quotingHelper.packet.structuredContribution')}</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <Card className="bg-rams-module border-rams-line shadow-none">
            <CardHeader className="border-b border-rams-line/50">
              <CardTitle className="text-[11px] font-black uppercase tracking-widest flex items-center gap-2">
                <FileText className="h-3.5 w-3.5 text-rams-orange" />
                {t('common.quotingHelper.packet.technicalInputs')}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-8">
              {renderDisciplineForm()}
            </CardContent>
          </Card>

          <Card className="bg-rams-module border-rams-line shadow-none">
            <CardHeader className="border-b border-rams-line/50">
              <CardTitle className="text-[11px] font-black uppercase tracking-widest flex items-center gap-2">
                <MessageSquare className="h-3.5 w-3.5 text-rams-orange" />
                {t('common.quotingHelper.packet.internalNotes')}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <Textarea 
                value={packet.notes || ''}
                onChange={e => updateWorkPacket(packet.id, { notes: e.target.value })}
                className="bg-rams-panel border-rams-line font-mono min-h-[100px]"
                placeholder={t('common.quotingHelper.packet.notesPlaceholder')}
              />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-rams-module border-rams-line shadow-none">
            <CardHeader className="border-b border-rams-line/50">
              <CardTitle className="text-[11px] font-black uppercase tracking-widest">{t('common.quotingHelper.packet.actions')}</CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-3">
              <Button 
                onClick={() => handleSave()} 
                disabled={isSaving}
                className="w-full h-11 bg-rams-panel border border-rams-line hover:bg-rams-panel-hover text-foreground text-[10px] uppercase font-black tracking-widest"
              >
                <Save className="mr-2 h-3.5 w-3.5" /> {t('common.quotingHelper.packet.saveProgress')}
              </Button>
              <Separator className="bg-rams-line/30 my-4" />
              <Button 
                onClick={() => handleSave('done')}
                disabled={isSaving}
                className="w-full h-11 bg-rams-green hover:bg-rams-green/90 text-white text-[10px] uppercase font-black tracking-widest"
              >
                <CheckCircle2 className="mr-2 h-3.5 w-3.5" /> {t('common.quotingHelper.packet.signOff')}
              </Button>
              <Button 
                onClick={() => handleSave('blocked')}
                disabled={isSaving}
                className="w-full h-11 bg-rams-red/10 text-rams-red hover:bg-rams-red/20 border border-rams-red/30 text-[10px] uppercase font-black tracking-widest"
              >
                <AlertCircle className="mr-2 h-3.5 w-3.5" /> {t('common.quotingHelper.packet.flagBlocker')}
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-rams-module border-rams-line shadow-none opacity-50">
            <CardHeader className="pb-2">
              <CardTitle className="text-[9px] font-black uppercase tracking-widest flex items-center gap-2">
                <Lock className="h-3 w-3" /> {t('common.quotingHelper.packet.auditLog')}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-[9px] font-mono uppercase space-y-1">
              <p>{t('common.quotingHelper.packet.created')}: {new Date(packet.created_at || Date.now()).toLocaleString()}</p>
              <p>{t('common.quotingHelper.packet.owner')}: {t('common.quotingHelper.packet.assignedToYou')}</p>
              <p>{t('common.quotingHelper.packet.status')}: {packet.status}</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
