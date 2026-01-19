'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X, ClipboardCheck } from 'lucide-react';
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
import { useI18n } from '@/contexts/i18n-context';
export default function NewInspectionPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [form, setForm] = React.useState({
    title: '',
    type: 'first_article',
    productId: '',
    workOrderId: '',
    inspector: '',
    notes: '',
  });
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      toast({ title: t('quality.inspection.new.inspectionStarted') || 'Inspection Started', description: t('quality.inspection.new.initializedSuccess') || 'New inspection record has been initialized.' });
      router.push('/quality?tab=inspections');
    } catch (error) {
      toast({ title: t('common.error') || 'Error', description: t('quality.inspection.new.createFailed') || 'Failed to create inspection.', variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };
  return (
    <div className="max-w-3xl mx-auto space-y-8 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('quality.inspection.new.title') || 'Initialize Gate Sync'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('quality.inspection.new.subtitle') || 'Quality Inspection Inception'}</span>
              <span className="opacity-30">|</span>
              <span>STATION: QUALITY-PLANNING-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.back()} disabled={isSubmitting}>
            {t('common.abort') || 'ABORT'}
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting} size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            {isSubmitting ? (
              t('common.synchronizing') || 'SYNCHRONIZING...'
            ) : (
              <>
                <Save className="h-3.5 w-3.5 mr-2" />
                {t('quality.inspection.new.establishInspection') || 'ESTABLISH_INSPECTION'}
              </>
            )}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="animate-in fade-in slide-in-from-bottom-2 duration-500">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-3">
              <ClipboardCheck className="h-4 w-4 text-rams-orange" />
              {t('quality.inspection.new.gateParameters') || 'Inspection Gate Parameters'}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-8 p-8">
            <div className="space-y-2">
              <Label htmlFor="title" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.inspection.new.protocolIdentity') || 'Inspection Protocol Identity'} *</Label>
              <Input
                id="title"
                placeholder="e.g., Final Inspection Protocol - BRK-2024"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="type" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.inspection.new.phaseNode') || 'Inspection Phase Node'}</Label>
                <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}>
                  <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="first_article">FIRST_ARTICLE_(FAI)</SelectItem>
                    <SelectItem value="in_process">IN-PROCESS_SYNC</SelectItem>
                    <SelectItem value="final">FINAL_GATE_INSPECTION</SelectItem>
                    <SelectItem value="receiving">RECEIVING_PROTOCOL</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="inspector" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.inspection.new.assignedInspector') || 'Assigned Inspector Node'}</Label>
                <Input
                  id="inspector"
                  placeholder="OPERATIVE_IDENTITY"
                  value={form.inspector}
                  onChange={(e) => setForm({ ...form, inspector: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="productId" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.inspection.new.productPartNode') || 'Product Part Node'}</Label>
                <Input
                  id="productId"
                  placeholder="PART_NUMBER"
                  value={form.productId}
                  onChange={(e) => setForm({ ...form, productId: e.target.value.toUpperCase() })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="workOrderId" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.inspection.new.associatedWoSync') || 'Associated WO Sync'}</Label>
                <Input
                  id="workOrderId"
                  placeholder="WO_NUMBER"
                  value={form.workOrderId}
                  onChange={(e) => setForm({ ...form, workOrderId: e.target.value.toUpperCase() })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.inspection.new.initialObservation') || 'Initial Observation Intel'}</Label>
              <Textarea
                id="notes"
                placeholder="Incorporate initial findings and contextual data..."
                rows={4}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                className="rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed h-48 resize-none"
              />
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
