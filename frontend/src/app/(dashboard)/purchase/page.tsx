'use client';

import * as React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Plus, ShoppingCart, Truck, FileText } from 'lucide-react';
import { apiClient } from '@/api/client';

export default function PurchasePage() {
  const [orders, setOrders] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    apiClient.get('/purchase/orders').then((data) => {
      setOrders(data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-8 page-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-heading font-bold tracking-tight">Purchase Orders</h1>
          <p className="text-muted-foreground">Manage supplier relations and procurement cycles</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="rounded-xl">
            <Truck className="mr-2 h-4 w-4" />
            Suppliers
          </Button>
          <Button className="rounded-xl shadow-glow">
            <Plus className="mr-2 h-4 w-4" />
            New Order
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {[
          { label: 'Open Requisitions', value: '12', icon: FileText, color: 'text-primary' },
          { label: 'Pending POs', value: '8', icon: ShoppingCart, color: 'text-warning' },
          { label: 'Receipts Today', value: '4', icon: Truck, color: 'text-success' },
        ].map((stat, i) => (
          <Card key={i} className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">{stat.label}</p>
                  <p className="text-3xl font-heading font-bold tracking-tight mt-1">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-2xl bg-muted/20 ${stat.color}`}>
                  <stat.icon className="h-5 w-5" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>PO Number</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Total</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">Loading orders...</TableCell>
                </TableRow>
              ) : orders.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">No purchase orders found</TableCell>
                </TableRow>
              ) : (
                orders.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-mono font-bold text-primary">{order.po_number}</TableCell>
                    <TableCell className="font-medium">{order.supplier_name || 'Generic Supplier'}</TableCell>
                    <TableCell>{new Date(order.created_at).toLocaleDateString()}</TableCell>
                    <TableCell className="font-heading font-bold">${order.total_amount || '0.00'}</TableCell>
                    <TableCell>
                      <span className="px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-tighter bg-primary/10 text-primary">
                        {order.status}
                      </span>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
