'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Save,
  FileText,
  User,
  Calendar,
  DollarSign,
  Plus,
  Trash2,
  AlertCircle,
  Clock,
  Briefcase,
  Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
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
import { Badge } from '@/components/ui/badge';
import { usePipelineStore } from '@/stores/pipeline';
import { useToast } from '@/hooks/use-toast';
import { generateId } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';
import type { Priority } from '@/types';

interface RFQLineItem {
  id: string;
  part_number: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  target_price?: number;
  notes?: string;
}

interface RFQFormData {
  customer_id: string;
  title: string;
  description: string;
  priority: Priority;
  due_date: string;
  received_date: string;
  estimated_value: number;
  currency: string;
  notes: string;
  tags: string[];
  line_items: RFQLineItem[];
}

export default function NewRFQPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const { createRFQ } = usePipelineStore();
  
  const [isSaving, setIsSaving] = React.useState(false);
  const [formData, setFormData] = React.useState<RFQFormData>({
    customer_id: '',
    title: '',
    description: '',
    priority: 'medium',
    due_date: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    received_date: new Date().toISOString().split('T')[0],
    estimated_value: 0,
    currency: 'USD',
    notes: '',
    tags: [],
    line_items: [
      {
        id: generateId(),
        part_number: '',
        description: '',
        quantity: 1,
        unit_of_measure: 'pcs',
      },
    ],
  });

  const handleAddLineItem = () => {
    setFormData((prev) => ({
      ...prev,
      line_items: [
        ...prev.line_items,
        {
          id: generateId(),
          part_number: '',
          description: '',
          quantity: 1,
          unit_of_measure: 'pcs',
        },
      ],
    }));
  };

  const handleRemoveLineItem = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      line_items: prev.line_items.filter((item) => item.id !== id),
    }));
  };

  const handleUpdateLineItem = (id: string, updates: Partial<RFQLineItem>) => {
    setFormData((prev) => ({
      ...prev,
      line_items: prev.line_items.map((item) =>
        item.id === id ? { ...item, ...updates } : item
      ),
    }));
  };

  const handleSave = async () => {
    if (!formData.title || !formData.customer_id) {
      toast({
        variant: 'destructive',
        title: t('pages.pipeline.new.validation.requiredFieldsMissing'),
        description: t('pages.pipeline.new.validation.provideTitleAndCustomer'),
      });
      return;
    }

    setIsSaving(true);
    try {
      await createRFQ(formData as any);
      toast({
        title: t('pages.pipeline.new.toast.rfqCreated'),
        description: t('pages.pipeline.new.toast.rfqCreatedDescription'),
      });
      router.push('/pipeline');
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: t('pages.pipeline.new.toast.rfqCreateFailed'),
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-8 page-fade-in pb-12">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              {t('pages.pipeline.new.title')}
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <span>{t('pages.pipeline.new.subtitle')}</span>
              <span className="opacity-30">|</span>
              <span>{t('pages.pipeline.new.station')}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="default" className="rounded-rams-sm border-rams-line h-10 px-6 transition-none" onClick={() => router.back()}>
            {t('common.discard')}
          </Button>
          <Button onClick={handleSave} disabled={isSaving} size="default" className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none">
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                {t('common.synchronizing')}
              </>
            ) : (
              <>
                <Save className="mr-2 h-3.5 w-3.5" />
                {t('pages.pipeline.new.establishProtocol')}
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-3">
                <FileText className="h-4 w-4 text-rams-orange" />
                {t('pages.pipeline.new.opportunityParameters')}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-8 space-y-8">
              <div className="grid gap-8 sm:grid-cols-2">
                <div className="sm:col-span-2 space-y-2">
                  <Label htmlFor="title" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.pipeline.new.labels.strategicTitle')}</Label>
                  <Input
                    id="title"
                    value={formData.title}
                    onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                    placeholder={t('pages.pipeline.new.placeholders.title')}
                    className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="customer" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.pipeline.new.labels.customerNode')}</Label>
                  <Input
                    id="customer"
                    value={formData.customer_id}
                    onChange={(e) => setFormData((prev) => ({ ...prev, customer_id: e.target.value }))}
                    placeholder={t('pages.pipeline.new.placeholders.customer')}
                    className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="priority" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.pipeline.new.labels.priorityLayer')}</Label>
                  <Select
                    value={formData.priority}
                    onValueChange={(v: Priority) => setFormData((prev) => ({ ...prev, priority: v }))}
                  >
                    <SelectTrigger id="priority" className="h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-bold uppercase tracking-wider">
                      <SelectValue placeholder={t('common.priority.label')} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">{t('pages.pipeline.new.priority.low')}</SelectItem>
                      <SelectItem value="medium">{t('pages.pipeline.new.priority.medium')}</SelectItem>
                      <SelectItem value="high">{t('pages.pipeline.new.priority.high')}</SelectItem>
                      <SelectItem value="urgent">{t('pages.pipeline.new.priority.urgent')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.pipeline.new.labels.detailedContext')}</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder={t('pages.pipeline.new.placeholders.description')}
                  className="rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed h-32"
                  rows={4}
                />
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b border-rams-line bg-rams-panel/20 p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] flex items-center gap-3">
                <Briefcase className="h-4 w-4 text-rams-orange" />
                {t('pages.pipeline.new.labels.lineIntelligence')}
              </CardTitle>
              <Button variant="outline" size="sm" onClick={handleAddLineItem} className="rounded-rams-sm border-rams-line h-8 text-[9px] font-black uppercase tracking-widest">
                <Plus className="mr-2 h-3.5 w-3.5" />
                {t('pages.pipeline.new.labels.addNode')}
              </Button>
            </CardHeader>
            <CardContent className="p-8">
              <div className="space-y-8">
                {formData.line_items.map((item, index) => (
                  <div key={item.id} className="grid gap-8 border border-rams-line bg-rams-panel/10 p-6 relative group transition-none">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-2 right-2 h-7 w-7 text-muted-foreground/20 hover:text-rams-red hover:bg-rams-red/5 rounded-none opacity-0 group-hover:opacity-100 transition-none"
                      onClick={() => handleRemoveLineItem(item.id)}
                      disabled={formData.line_items.length === 1}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                    <div className="grid gap-8 sm:grid-cols-4">
                      <div className="sm:col-span-1 space-y-2">
                        <Label className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40 ml-1">{t('pages.pipeline.new.labels.partNode')}</Label>
                        <Input
                          value={item.part_number}
                          onChange={(e) => handleUpdateLineItem(item.id, { part_number: e.target.value })}
                          placeholder={t('pages.pipeline.new.placeholders.partNumber')}
                          className="h-9 rounded-none bg-rams-module border-rams-line text-[10px] font-mono font-bold"
                        />
                      </div>
                      <div className="sm:col-span-3 space-y-2">
                        <Label className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40 ml-1">{t('pages.pipeline.new.labels.specification')}</Label>
                        <Input
                          value={item.description}
                          onChange={(e) => handleUpdateLineItem(item.id, { description: e.target.value })}
                          placeholder={t('pages.pipeline.new.placeholders.itemDescription')}
                          className="h-9 rounded-none bg-rams-module border-rams-line text-[10px] font-bold uppercase"
                        />
                      </div>
                    </div>
                    <div className="grid gap-8 sm:grid-cols-3">
                      <div className="space-y-2">
                        <Label className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40 ml-1">{t('pages.pipeline.new.labels.magnitude')}</Label>
                        <Input
                          type="number"
                          value={item.quantity}
                          onChange={(e) => handleUpdateLineItem(item.id, { quantity: Number(e.target.value) })}
                          className="h-9 rounded-none bg-rams-module border-rams-line text-[10px] font-mono font-bold"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40 ml-1">{t('pages.pipeline.new.labels.unitProtocol')}</Label>
                        <Input
                          value={item.unit_of_measure}
                          onChange={(e) => handleUpdateLineItem(item.id, { unit_of_measure: e.target.value })}
                          placeholder={t('pages.pipeline.new.placeholders.unit')}
                          className="h-9 rounded-none bg-rams-module border-rams-line text-[10px] font-bold uppercase"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/40 ml-1">{t('pages.pipeline.new.labels.targetValuation')}</Label>
                        <div className="relative">
                          <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/20" />
                          <Input
                            type="number"
                            value={item.target_price || ''}
                            onChange={(e) => handleUpdateLineItem(item.id, { target_price: Number(e.target.value) })}
                            className="pl-9 h-9 rounded-none bg-rams-module border-rams-line text-[10px] font-mono font-bold"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-8">
          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.pipeline.new.labels.temporalHorizon')}</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-8">
              <div className="space-y-2">
                <Label htmlFor="receivedDate" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.pipeline.new.labels.ingestionDate')}</Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/20" />
                  <Input
                    id="receivedDate"
                    type="date"
                    value={formData.received_date}
                    onChange={(e) => setFormData((prev) => ({ ...prev, received_date: e.target.value }))}
                    className="pl-10 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="dueDate" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.pipeline.new.labels.strategicDeadline')}</Label>
                <div className="relative">
                  <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/20" />
                  <Input
                    id="dueDate"
                    type="date"
                    value={formData.due_date}
                    onChange={(e) => setFormData((prev) => ({ ...prev, due_date: e.target.value }))}
                    className="pl-10 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                  />
                </div>
              </div>
              <div className="pt-8 border-t border-rams-line">
                <Label htmlFor="estimatedValue" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('pages.pipeline.new.labels.estimatedMagnitude')}</Label>
                <div className="relative mt-2">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/20" />
                  <Input
                    id="estimatedValue"
                    type="number"
                    value={formData.estimated_value}
                    onChange={(e) => setFormData((prev) => ({ ...prev, estimated_value: Number(e.target.value) }))}
                    className="pl-10 h-10 rounded-rams-sm bg-rams-panel border-rams-line text-[11px] font-mono font-bold"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-rams-sm border border-rams-line bg-rams-module shadow-none">
            <CardHeader className="bg-rams-panel/20 border-b border-rams-line p-6">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('pages.pipeline.new.labels.protocolNotes')}</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <Textarea
                id="internalNotes"
                value={formData.notes}
                onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
                placeholder={t('pages.pipeline.new.placeholders.notes')}
                className="rounded-rams-sm bg-rams-panel border-rams-line text-[11px] uppercase leading-relaxed h-48 resize-none"
                rows={6}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
