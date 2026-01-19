'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Save, X, AlertCircle } from 'lucide-react';
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
import { useQualityStore } from '@/stores';
import { useI18n } from '@/contexts/i18n-context';

export default function NewNCRPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const { createNCR } = useQualityStore();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const [form, setForm] = React.useState({
    title: '',
    description: '',
    severity: 'minor',
    productId: '',
    workOrderId: '',
    location: '',
    detectedBy: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title || !form.description) {
      toast({
        title: t('quality.ncr.new.validationError') || 'Validation Error',
        description: t('quality.ncr.new.titleDescRequired') || 'Title and Description are required.',
        variant: 'destructive',
      });
      return;
    }

    setIsSubmitting(true);
    try {
      await createNCR({
        title: form.title,
        description: form.description,
        severity: form.severity as any,
        product_id: form.productId || undefined,
        work_order_id: form.workOrderId || undefined,
      });
      toast({
        title: t('quality.ncr.new.ncrCreated') || 'NCR Created',
        description: t('quality.ncr.new.recordedSuccess') || `NCR has been successfully recorded.`,
      });
      router.push('/quality?tab=ncrs');
    } catch (error) {
      toast({
        title: t('common.error') || 'Error',
        description: t('quality.ncr.new.createFailed') || 'Failed to create NCR.',
        variant: 'destructive',
      });
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
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('quality.ncr.new.title') || 'Initialize NCR Protocol'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('quality.ncr.new.subtitle') || 'Non-Conformance Reporting'}</span>
              <span className="opacity-30">|</span>
              <span>STATION: QUALITY-ENTRY-01</span>
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
                {t('quality.ncr.new.establishNcr') || 'ESTABLISH_NCR'}
              </>
            )}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="animate-in fade-in slide-in-from-bottom-2 duration-500">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('quality.ncr.new.ncrParameters') || 'Non-Conformance Parameters'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-8 p-8">
            <div className="space-y-2">
              <Label htmlFor="title" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.ncr.new.issueTitleProtocol') || 'Issue Title Protocol'} *</Label>
              <Input
                id="title"
                placeholder="e.g., Dimensional deviation in bracket holes"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="severity" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.ncr.new.severityMagnitude') || 'Severity Magnitude'}</Label>
                <Select
                  value={form.severity}
                  onValueChange={(value) => setForm({ ...form, severity: value })}
                >
                  <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="minor">MINOR_PROTOCOL</SelectItem>
                    <SelectItem value="major">MAJOR_RISK</SelectItem>
                    <SelectItem value="critical">CRITICAL_BREACH</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="location" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.ncr.new.detectionNode') || 'Detection Node (Location)'}</Label>
                <Input
                  id="location"
                  placeholder="e.g., Assembly Line 2"
                  value={form.location}
                  onChange={(e) => setForm({ ...form, location: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="productId" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.ncr.new.relatedProduct') || 'Related Product Node'}</Label>
                <Input
                  id="productId"
                  placeholder="PART_NUMBER"
                  value={form.productId}
                  onChange={(e) => setForm({ ...form, productId: e.target.value.toUpperCase() })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="workOrderId" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.ncr.new.associatedWo') || 'Associated WO Node'}</Label>
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
              <Label htmlFor="description" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('quality.ncr.new.discrepancyIntelligence') || 'Discrepancy Intelligence'} *</Label>
              <Textarea
                id="description"
                placeholder="Provide detailed evidence regarding the discrepancy protocol..."
                rows={5}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed h-48 resize-none"
                required
              />
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
