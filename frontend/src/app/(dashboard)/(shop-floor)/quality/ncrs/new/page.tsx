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
        title: t('modules.quality.ncr.new.validationError'),
        description: t('modules.quality.ncr.new.titleDescRequired'),
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
        title: t('modules.quality.ncr.new.ncrCreated'),
        description: t('modules.quality.ncr.new.recordedSuccess') || `NCR has been successfully recorded.`,
      });
      router.push('/quality?tab=ncrs');
    } catch (error) {
      toast({
        title: t('common.error'),
        description: t('modules.quality.ncr.new.createFailed'),
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
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('modules.quality.ncr.new.title')}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('modules.quality.ncr.new.subtitle')}</span>
              <span className="opacity-30">|</span>
              <span>STATION: QUALITY-ENTRY-01</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.back()} disabled={isSubmitting}>
            {t('common.abort')}
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting} size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            {isSubmitting ? (
              t('common.synchronizing')
            ) : (
              <>
                <Save className="h-3.5 w-3.5 mr-2" />
                {t('modules.quality.ncr.new.establishNcr')}
              </>
            )}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="animate-in fade-in slide-in-from-bottom-2 duration-500">
        <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('modules.quality.ncr.new.ncrParameters')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-8 p-8">
            <div className="space-y-2">
              <Label htmlFor="title" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.ncr.new.issueTitleProtocol')} *</Label>
              <Input
                id="title"
                placeholder={t('modules.quality.ncr.new.placeholders.title')}
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="severity" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.ncr.new.severityMagnitude')}</Label>
                <Select
                  value={form.severity}
                  onValueChange={(value) => setForm({ ...form, severity: value })}
                >
                  <SelectTrigger className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="minor">{t('modules.quality.ncr.new.severity.minor')}</SelectItem>
                    <SelectItem value="major">{t('modules.quality.ncr.new.severity.major')}</SelectItem>
                    <SelectItem value="critical">{t('modules.quality.ncr.new.severity.critical')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="location" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.ncr.new.detectionNode')}</Label>
                <Input
                  id="location"
                  placeholder={t('modules.quality.ncr.new.placeholders.location')}
                  value={form.location}
                  onChange={(e) => setForm({ ...form, location: e.target.value })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-2">
                <Label htmlFor="productId" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.ncr.new.relatedProduct')}</Label>
                <Input
                  id="productId"
                  placeholder={t('modules.quality.ncr.new.placeholders.partNumber')}
                  value={form.productId}
                  onChange={(e) => setForm({ ...form, productId: e.target.value.toUpperCase() })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="workOrderId" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.ncr.new.associatedWo')}</Label>
                <Input
                  id="workOrderId"
                  placeholder={t('modules.quality.ncr.new.placeholders.woNumber')}
                  value={form.workOrderId}
                  onChange={(e) => setForm({ ...form, workOrderId: e.target.value.toUpperCase() })}
                  className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('modules.quality.ncr.new.discrepancyIntelligence')} *</Label>
              <Textarea
                id="description"
                placeholder={t('modules.quality.ncr.new.placeholders.description')}
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
