'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Plus, Trash2, Search, Save, Send } from 'lucide-react';
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { apiClient } from '@/api/client';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';
interface RequisitionLine {
  id: string;
  product_id: string;
  product_name: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  estimated_unit_price: number;
  notes: string;
}

interface Product {
  id: string;
  name: string;
  sku: string;
  unit_of_measure: string;
  standard_cost: number;
}

export default function NewPurchaseRequisitionPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = React.useState(false);
  const [products, setProducts] = React.useState<Product[]>([]);
  const [searchQuery, setSearchQuery] = React.useState('');
  
  // Form state
  const [justification, setJustification] = React.useState('');
  const [priority, setPriority] = React.useState<'low' | 'medium' | 'high' | 'urgent'>('medium');
  const [requiredDate, setRequiredDate] = React.useState('');
  const [lines, setLines] = React.useState<RequisitionLine[]>([]);

  // Fetch products for selection
  React.useEffect(() => {
    const fetchProducts = async () => {
      try {
        const res = await apiClient.get('/products');
        const data = (res as { data: Product[] })?.data || (res as Product[]) || [];
        setProducts(data);
      } catch (error) {
        console.error('Failed to fetch products:', error);
      }
    };
    fetchProducts();
  }, []);

  const addLine = () => {
    const newLine: RequisitionLine = {
      id: crypto.randomUUID(),
      product_id: '',
      product_name: '',
      description: '',
      quantity: 1,
      unit_of_measure: 'EA',
      estimated_unit_price: 0,
      notes: '',
    };
    setLines([...lines, newLine]);
  };

  const removeLine = (id: string) => {
    setLines(lines.filter(line => line.id !== id));
  };

  const updateLine = (id: string, updates: Partial<RequisitionLine>) => {
    setLines(lines.map(line => 
      line.id === id ? { ...line, ...updates } : line
    ));
  };

  const handleProductSelect = (lineId: string, productId: string) => {
    const product = products.find(p => p.id === productId);
    if (product) {
      updateLine(lineId, {
        product_id: productId,
        product_name: product.name,
        unit_of_measure: product.unit_of_measure || 'EA',
        estimated_unit_price: product.standard_cost || 0,
      });
    }
  };

  const calculateTotal = () => {
    return lines.reduce((sum, line) => sum + (line.quantity * line.estimated_unit_price), 0);
  };

  const handleSubmit = async (asDraft: boolean = true) => {
    if (lines.length === 0) {
      toast({
        title: 'Error',
        description: 'Please add at least one line item',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const payload = {
        justification,
        priority,
        required_date: requiredDate || null,
        status: asDraft ? 'draft' : 'submitted',
        lines: lines.map(line => ({
          product_id: line.product_id || null,
          description: line.description || line.product_name,
          quantity: line.quantity,
          unit_of_measure: line.unit_of_measure,
          estimated_unit_price: line.estimated_unit_price,
          notes: line.notes,
        })),
      };

      await apiClient.post('/purchase/requisitions', payload);
      
      toast({
        title: 'Success',
        description: asDraft ? 'Requisition saved as draft' : 'Requisition submitted for approval',
      });
      
      router.push('/purchase');
    } catch (error) {
      console.error('Failed to create requisition:', error);
      toast({
        title: 'Error',
        description: 'Failed to create requisition. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const filteredProducts = products.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.sku?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-8 page-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl" asChild>
            <Link href="/purchase">
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight ">
              New Purchase Requisition
            </h1>
            <p className="text-muted-foreground">Request materials or services for procurement</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            className="rounded-xl"
            onClick={() => handleSubmit(true)}
            disabled={loading}
          >
            <Save className="mr-2 h-4 w-4" />
            Save Draft
          </Button>
          <Button 
            className="rounded-xl shadow-glow"
            onClick={() => handleSubmit(false)}
            disabled={loading}
          >
            <Send className="mr-2 h-4 w-4" />
            Submit for Approval
          </Button>
        </div>
      </div>

      {/* Form */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Requisition Details */}
          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader>
              <CardTitle>Requisition Details</CardTitle>
              <CardDescription>Provide justification and priority for this request</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="justification">Business Justification *</Label>
                <Textarea
                  id="justification"
                  placeholder="Explain why these items are needed..."
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  className="min-h-[100px] rounded-xl"
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="priority">Priority</Label>
                  <Select value={priority} onValueChange={(v: any) => setPriority(v)}>
                    <SelectTrigger className="rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="required_date">Required By</Label>
                  <Input
                    id="required_date"
                    type="date"
                    value={requiredDate}
                    onChange={(e) => setRequiredDate(e.target.value)}
                    className="rounded-xl"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Line Items */}
          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Line Items</CardTitle>
                <CardDescription>Add products or services to request</CardDescription>
              </div>
              <Button onClick={addLine} className="rounded-xl">
                <Plus className="mr-2 h-4 w-4" />
                Add Item
              </Button>
            </CardHeader>
            <CardContent>
              {lines.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <p>No items added yet</p>
                  <p className="text-sm">Click "Add Item" to start building your requisition</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[250px]">Product/Description</TableHead>
                      <TableHead className="w-[100px]">Qty</TableHead>
                      <TableHead className="w-[80px]">UoM</TableHead>
                      <TableHead className="w-[120px]">Est. Price</TableHead>
                      <TableHead className="w-[120px]">Subtotal</TableHead>
                      <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {lines.map((line) => (
                      <TableRow key={line.id}>
                        <TableCell>
                          <Select
                            value={line.product_id}
                            onValueChange={(v) => handleProductSelect(line.id, v)}
                          >
                            <SelectTrigger className="rounded-lg">
                              <SelectValue placeholder="Select product..." />
                            </SelectTrigger>
                            <SelectContent>
                              {filteredProducts.slice(0, 50).map((product) => (
                                <SelectItem key={product.id} value={product.id}>
                                  {product.name} ({product.sku})
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Input
                            placeholder="Or enter description..."
                            value={line.description}
                            onChange={(e) => updateLine(line.id, { description: e.target.value })}
                            className="mt-2 rounded-lg text-sm"
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min={1}
                            value={line.quantity}
                            onChange={(e) => updateLine(line.id, { quantity: parseInt(e.target.value) || 1 })}
                            className="rounded-lg"
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            value={line.unit_of_measure}
                            onChange={(e) => updateLine(line.id, { unit_of_measure: e.target.value })}
                            className="rounded-lg"
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            step="0.01"
                            min={0}
                            value={line.estimated_unit_price}
                            onChange={(e) => updateLine(line.id, { estimated_unit_price: parseFloat(e.target.value) || 0 })}
                            className="rounded-lg"
                          />
                        </TableCell>
                        <TableCell className="font-medium">
                          ${(line.quantity * line.estimated_unit_price).toFixed(2)}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            onClick={() => removeLine(line.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Summary */}
          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader>
              <CardTitle>Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Line Items</span>
                <span className="font-medium">{lines.length}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Total Quantity</span>
                <span className="font-medium">{lines.reduce((sum, l) => sum + l.quantity, 0)}</span>
              </div>
              <div className="border-t pt-4">
                <div className="flex justify-between">
                  <span className="font-medium">Estimated Total</span>
                  <span className="text-xl font-heading font-bold text-primary">
                    ${calculateTotal().toFixed(2)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Add Products */}
          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader>
              <CardTitle>Quick Add</CardTitle>
              <CardDescription>Search and add products</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search products..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 rounded-xl"
                />
              </div>
              <div className="max-h-[300px] overflow-y-auto space-y-2">
                {filteredProducts.slice(0, 10).map((product) => (
                  <div
                    key={product.id}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 cursor-pointer"
                    onClick={() => {
                      const newLine: RequisitionLine = {
                        id: crypto.randomUUID(),
                        product_id: product.id,
                        product_name: product.name,
                        description: '',
                        quantity: 1,
                        unit_of_measure: product.unit_of_measure || 'EA',
                        estimated_unit_price: product.standard_cost || 0,
                        notes: '',
                      };
                      setLines([...lines, newLine]);
                    }}
                  >
                    <div>
                      <p className="text-sm font-medium">{product.name}</p>
                      <p className="text-xs text-muted-foreground">{product.sku}</p>
                    </div>
                    <Plus className="h-4 w-4 text-muted-foreground" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
