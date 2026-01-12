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
  partNumber: string;
  description: string;
  quantity: number;
  unitOfMeasure: string;
  targetPrice?: number;
  notes?: string;
}

interface RFQFormData {
  customerId: string;
  title: string;
  description: string;
  priority: Priority;
  dueDate: string;
  receivedDate: string;
  estimatedValue: number;
  currency: string;
  notes: string;
  tags: string[];
  lineItems: RFQLineItem[];
}

export default function NewRFQPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { createRFQ } = usePipelineStore();
  
  const [isSaving, setIsSaving] = React.useState(false);
  const [formData, setFormData] = React.useState<RFQFormData>({
    customerId: '',
    title: '',
    description: '',
    priority: 'medium',
    dueDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    receivedDate: new Date().toISOString().split('T')[0],
    estimatedValue: 0,
    currency: 'USD',
    notes: '',
    tags: [],
    lineItems: [
      {
        id: generateId(),
        partNumber: '',
        description: '',
        quantity: 1,
        unitOfMeasure: 'pcs',
      },
    ],
  });

  const handleAddLineItem = () => {
    setFormData((prev) => ({
      ...prev,
      lineItems: [
        ...prev.lineItems,
        {
          id: generateId(),
          partNumber: '',
          description: '',
          quantity: 1,
          unitOfMeasure: 'pcs',
        },
      ],
    }));
  };

  const handleRemoveLineItem = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      lineItems: prev.lineItems.filter((item) => item.id !== id),
    }));
  };

  const handleUpdateLineItem = (id: string, updates: Partial<RFQLineItem>) => {
    setFormData((prev) => ({
      ...prev,
      lineItems: prev.lineItems.map((item) =>
        item.id === id ? { ...item, ...updates } : item
      ),
    }));
  };

  const handleSave = async () => {
    if (!formData.title || !formData.customerId) {
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">New RFQ</h1>
            <p className="text-muted-foreground">Create a new Request for Quote</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            <Save className="mr-2 h-4 w-4" />
            {isSaving ? 'Saving...' : 'Create RFQ'}
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                General Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <Label htmlFor="title">RFQ Title</Label>
                  <Input
                    id="title"
                    value={formData.title}
                    onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                    placeholder="e.g. Precision Parts for Aerospace Project"
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label htmlFor="customer">Customer</Label>
                  <Input
                    id="customer"
                    value={formData.customerId}
                    onChange={(e) => setFormData((prev) => ({ ...prev, customerId: e.target.value }))}
                    placeholder="Search customers..."
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label htmlFor="priority">Priority</Label>
                  <Select
                    value={formData.priority}
                    onValueChange={(v: Priority) => setFormData((prev) => ({ ...prev, priority: v }))}
                  >
                    <SelectTrigger id="priority" className="mt-1.5">
                      <SelectValue placeholder="Select priority" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="Additional details about the RFQ..."
                  className="mt-1.5"
                  rows={4}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Briefcase className="h-5 w-5" />
                Line Items
              </CardTitle>
              <Button variant="outline" size="sm" onClick={handleAddLineItem}>
                <Plus className="mr-2 h-4 w-4" />
                Add Item
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {formData.lineItems.map((item, index) => (
                  <div key={item.id} className="grid gap-4 border rounded-lg p-4 relative bg-muted/30">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-2 right-2 h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={() => handleRemoveLineItem(item.id)}
                      disabled={formData.lineItems.length === 1}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <div className="grid gap-4 sm:grid-cols-4">
                      <div className="sm:col-span-1">
                        <Label>Part Number</Label>
                        <Input
                          value={item.partNumber}
                          onChange={(e) => handleUpdateLineItem(item.id, { partNumber: e.target.value })}
                          placeholder="PN-123"
                          className="mt-1"
                        />
                      </div>
                      <div className="sm:col-span-3">
                        <Label>Description</Label>
                        <Input
                          value={item.description}
                          onChange={(e) => handleUpdateLineItem(item.id, { description: e.target.value })}
                          placeholder="Part description..."
                          className="mt-1"
                        />
                      </div>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-3">
                      <div>
                        <Label>Quantity</Label>
                        <Input
                          type="number"
                          value={item.quantity}
                          onChange={(e) => handleUpdateLineItem(item.id, { quantity: Number(e.target.value) })}
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label>Unit of Measure</Label>
                        <Input
                          value={item.unitOfMeasure}
                          onChange={(e) => handleUpdateLineItem(item.id, { unitOfMeasure: e.target.value })}
                          placeholder="pcs, kg, etc."
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label>Target Price (Optional)</Label>
                        <div className="relative mt-1">
                          <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <Input
                            type="number"
                            value={item.targetPrice || ''}
                            onChange={(e) => handleUpdateLineItem(item.id, { targetPrice: Number(e.target.value) })}
                            className="pl-9"
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

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Timeline & Value</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="receivedDate">Received Date</Label>
                <div className="relative mt-1.5">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="receivedDate"
                    type="date"
                    value={formData.receivedDate}
                    onChange={(e) => setFormData((prev) => ({ ...prev, receivedDate: e.target.value }))}
                    className="pl-9"
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="dueDate">Due Date</Label>
                <div className="relative mt-1.5">
                  <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="dueDate"
                    type="date"
                    value={formData.dueDate}
                    onChange={(e) => setFormData((prev) => ({ ...prev, dueDate: e.target.value }))}
                    className="pl-9"
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="estimatedValue">Estimated Value</Label>
                <div className="relative mt-1.5">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="estimatedValue"
                    type="number"
                    value={formData.estimatedValue}
                    onChange={(e) => setFormData((prev) => ({ ...prev, estimatedValue: Number(e.target.value) }))}
                    className="pl-9"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Additional Info</CardTitle>
            </CardHeader>
            <CardContent>
              <Label htmlFor="internalNotes">Internal Notes</Label>
              <Textarea
                id="internalNotes"
                value={formData.notes}
                onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
                placeholder="Internal notes, not visible to customer..."
                className="mt-1.5"
                rows={5}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
