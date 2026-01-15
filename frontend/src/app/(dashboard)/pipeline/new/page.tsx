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
        title: 'Required Fields Missing',
        description: 'Please provide a title and customer.',
      });
      return;
    }

    setIsSaving(true);
    try {
      await createRFQ(formData as any);
      toast({
        title: 'RFQ Created',
        description: 'The new RFQ has been successfully created.',
      });
      router.push('/pipeline');
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'Failed to create RFQ. Please try again.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-8 page-fade-in max-w-5xl mx-auto">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 hover:text-primary transition-all" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              New Intelligence Opportunity
            </h1>
            <p className="text-muted-foreground font-medium text-sm">Initiate a new Request for Quote protocol</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary" onClick={() => router.back()}>
            Discard
          </Button>
          <Button onClick={handleSave} disabled={isSaving} size="lg" className="rounded-xl shadow-glow subtle-shine h-12 px-8">
            <Save className="mr-2 h-5 w-5" />
            {isSaving ? 'Synchronizing...' : 'Establish RFQ'}
          </Button>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader>
              <CardTitle className="text-lg font-heading flex items-center gap-3">
                <div className="p-2 rounded-xl bg-primary/10 text-primary">
                  <FileText className="h-5 w-5" />
                </div>
                Opportunity Parameters
              </CardTitle>
              <CardDescription className="text-xs font-medium uppercase tracking-wider pl-11">Core intelligence for the request protocol</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 sm:grid-cols-2">
                <div className="sm:col-span-2 space-y-2.5">
                  <Label htmlFor="title" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Strategic Title</Label>
                  <Input
                    id="title"
                    value={formData.title}
                    onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                    placeholder="e.g. Precision Parts for Aerospace Project"
                    className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50"
                  />
                </div>
                <div className="space-y-2.5">
                  <Label htmlFor="customer" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Customer Node</Label>
                  <Input
                    id="customer"
                    value={formData.customer_id}
                    onChange={(e) => setFormData((prev) => ({ ...prev, customer_id: e.target.value }))}
                    placeholder="Search intelligence partners..."
                    className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft"
                  />
                </div>
                <div className="space-y-2.5">
                  <Label htmlFor="priority" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Priority Layer</Label>
                  <Select
                    value={formData.priority}
                    onValueChange={(v: Priority) => setFormData((prev) => ({ ...prev, priority: v }))}
                  >
                    <SelectTrigger id="priority" className="h-12 rounded-2xl bg-background/50 border-border/50 shadow-inner-soft">
                      <SelectValue placeholder="Select priority" />
                    </SelectTrigger>
                    <SelectContent className="rounded-2xl shadow-premium">
                      <SelectItem value="low" className="rounded-xl m-1">Low</SelectItem>
                      <SelectItem value="medium" className="rounded-xl m-1">Medium</SelectItem>
                      <SelectItem value="high" className="rounded-xl m-1">High</SelectItem>
                      <SelectItem value="urgent" className="rounded-xl m-1">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2.5">
                <Label htmlFor="description" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Detailed Context</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="Additional intelligence regarding the RFQ protocol..."
                  className="rounded-[1.5rem] bg-background/50 border-border/50 shadow-inner-soft focus:border-primary/50 transition-all resize-none"
                  rows={4}
                />
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b border-border/5 bg-muted/5 p-6">
              <div className="space-y-1">
                <CardTitle className="text-lg font-heading flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-primary/10 text-primary">
                    <Briefcase className="h-5 w-5" />
                  </div>
                  Line Intelligence
                </CardTitle>
                <CardDescription className="text-xs font-medium uppercase tracking-wider">Product nodes and quantity requirements</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={handleAddLineItem} className="rounded-xl border-primary/20 text-primary hover:bg-primary/5">
                <Plus className="mr-2 h-4 w-4" />
                Add Node
              </Button>
            </CardHeader>
            <CardContent className="p-6">
              <div className="space-y-6">
                {formData.line_items.map((item, index) => (
                  <div key={item.id} className="grid gap-6 border border-border/10 rounded-[1.5rem] p-6 relative bg-muted/10 group transition-all hover:bg-muted/20">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-4 right-4 h-8 w-8 text-muted-foreground/40 hover:text-danger hover:bg-danger/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                      onClick={() => handleRemoveLineItem(item.id)}
                      disabled={formData.line_items.length === 1}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <div className="grid gap-6 sm:grid-cols-4">
                      <div className="sm:col-span-1 space-y-2">
                        <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/40 ml-1">Part Node</Label>
                        <Input
                          value={item.part_number}
                          onChange={(e) => handleUpdateLineItem(item.id, { part_number: e.target.value })}
                          placeholder="PN-XXXX"
                          className="h-11 rounded-xl bg-background/50 border-border/50"
                        />
                      </div>
                      <div className="sm:col-span-3 space-y-2">
                        <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/40 ml-1">Specification</Label>
                        <Input
                          value={item.description}
                          onChange={(e) => handleUpdateLineItem(item.id, { description: e.target.value })}
                          placeholder="Node description protocol..."
                          className="h-11 rounded-xl bg-background/50 border-border/50"
                        />
                      </div>
                    </div>
                    <div className="grid gap-6 sm:grid-cols-3">
                      <div className="space-y-2">
                        <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/40 ml-1">Magnitude</Label>
                        <Input
                          type="number"
                          value={item.quantity}
                          onChange={(e) => handleUpdateLineItem(item.id, { quantity: Number(e.target.value) })}
                          className="h-11 rounded-xl bg-background/50 border-border/50"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/40 ml-1">Unit Protocol</Label>
                        <Input
                          value={item.unit_of_measure}
                          onChange={(e) => handleUpdateLineItem(item.id, { unit_of_measure: e.target.value })}
                          placeholder="pcs, kg, etc."
                          className="h-11 rounded-xl bg-background/50 border-border/50"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/40 ml-1">Target Valuation</Label>
                        <div className="relative">
                          <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/30" />
                          <Input
                            type="number"
                            value={item.target_price || ''}
                            onChange={(e) => handleUpdateLineItem(item.id, { target_price: Number(e.target.value) })}
                            className="pl-9 h-11 rounded-xl bg-background/50 border-border/50"
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
          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader>
              <CardTitle className="text-lg font-heading">Temporal Horizon</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2.5">
                <Label htmlFor="receivedDate" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Ingestion Date</Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-primary/40" />
                  <Input
                    id="receivedDate"
                    type="date"
                    value={formData.received_date}
                    onChange={(e) => setFormData((prev) => ({ ...prev, received_date: e.target.value }))}
                    className="pl-10 h-12 rounded-xl bg-background/50 border-border/50 shadow-inner-soft"
                  />
                </div>
              </div>
              <div className="space-y-2.5">
                <Label htmlFor="dueDate" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Strategic Deadline</Label>
                <div className="relative">
                  <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-primary/40" />
                  <Input
                    id="dueDate"
                    type="date"
                    value={formData.due_date}
                    onChange={(e) => setFormData((prev) => ({ ...prev, due_date: e.target.value }))}
                    className="pl-10 h-12 rounded-xl bg-background/50 border-border/50 shadow-inner-soft"
                  />
                </div>
              </div>
              <div className="pt-4 border-t border-border/5">
                <Label htmlFor="estimatedValue" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Estimated Magnitude</Label>
                <div className="relative mt-2.5">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-primary/40" />
                  <Input
                    id="estimatedValue"
                    type="number"
                    value={formData.estimated_value}
                    onChange={(e) => setFormData((prev) => ({ ...prev, estimated_value: Number(e.target.value) }))}
                    className="pl-10 h-12 rounded-xl bg-background/50 border-border/50 shadow-inner-soft"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader>
              <CardTitle className="text-lg font-heading">Protocol Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                id="internalNotes"
                value={formData.notes}
                onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
                placeholder="Confidential intelligence, restricted access..."
                className="rounded-[1.5rem] bg-background/50 border-border/50 shadow-inner-soft transition-all focus:border-primary/50 resize-none"
                rows={6}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
