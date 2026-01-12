'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  AlertTriangle,
  Clock,
  User,
  CheckCircle2,
  AlertCircle,
  FileText,
  History,
  MessageSquare,
  ShieldAlert,
  Save,
  MoreHorizontal,
  Search,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useQualityStore } from '@/stores/quality';
import { cn, formatDate } from '@/lib/utils';

export default function NCRDetailsPage() {
  const router = useRouter();
  const params = useParams();
  const { ncrs, fetchNCRs } = useQualityStore();

  const ncr = React.useMemo(() => 
    ncrs.find(n => n.id === params?.id) || ncrs[0], 
    [ncrs, params?.id]
  );

  React.useEffect(() => {
    if (ncrs.length === 0) {
      fetchNCRs();
    }
  }, [ncrs.length, fetchNCRs]);

  if (!ncr) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const statusConfig = {
    open: { label: 'Open', variant: 'warning' as const, icon: AlertCircle },
    investigating: { label: 'Investigating', variant: 'default' as const, icon: Search },
    disposed: { label: 'Disposed', variant: 'success' as const, icon: CheckCircle2 },
    closed: { label: 'Closed', variant: 'secondary' as const, icon: ShieldAlert },
  };

  const severityConfig = {
    minor: { label: 'Minor', class: 'bg-slate-100 text-slate-800' },
    major: { label: 'Major', class: 'bg-orange-100 text-orange-800' },
    critical: { label: 'Critical', class: 'bg-red-100 text-red-800' },
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{ncr.ncr_number}</h1>
              <Badge variant={statusConfig[ncr.status as keyof typeof statusConfig]?.variant || 'default'}>
                {statusConfig[ncr.status as keyof typeof statusConfig]?.label || ncr.status}
              </Badge>
              <Badge className={severityConfig[ncr.severity as keyof typeof severityConfig]?.class}>
                {severityConfig[ncr.severity as keyof typeof severityConfig]?.label || ncr.severity}
              </Badge>
            </div>
            <p className="text-muted-foreground">{ncr.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline">
            <MessageSquare className="h-4 w-4 mr-2" />
            Comment
          </Button>
          <Button>
            Assign CAPA
          </Button>
          <Button variant="outline" size="icon">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Non-Conformance Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1">
                  <span className="text-sm text-muted-foreground font-medium">Description</span>
                  <p className="text-sm leading-relaxed">{ncr.description || 'No description provided.'}</p>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between border-b pb-2 text-sm">
                    <span className="text-muted-foreground">Product</span>
                    <span className="font-medium">Precision Bracket Type A</span>
                  </div>
                  <div className="flex justify-between border-b pb-2 text-sm">
                    <span className="text-muted-foreground">Work Order</span>
                    <span className="font-medium">WO-2024-001</span>
                  </div>
                  <div className="flex justify-between border-b pb-2 text-sm">
                    <span className="text-muted-foreground">Quantity Affected</span>
                    <span className="font-medium">12 pcs</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="investigation">
            <TabsList>
              <TabsTrigger value="investigation">Investigation</TabsTrigger>
              <TabsTrigger value="disposition">Disposition</TabsTrigger>
              <TabsTrigger value="attachments">Attachments</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>
            <TabsContent value="investigation" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Root Cause Analysis</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-4 bg-muted/30 border rounded-lg">
                    <h4 className="font-medium mb-2">Findings</h4>
                    <p className="text-sm text-muted-foreground">
                      Initial investigation suggests a misalignment in the fixture during the secondary milling operation.
                      The coolant flow was also found to be partially blocked, leading to heat buildup.
                    </p>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1">
                      <Label>Category</Label>
                      <p className="text-sm font-medium">Machine Failure</p>
                    </div>
                    <div className="space-y-1">
                      <Label>Investigated By</Label>
                      <p className="text-sm font-medium">Sarah Johnson</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>Reported On</span>
                </div>
                <span className="font-medium">{formatDate(ncr.created_at)}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <User className="h-4 w-4" />
                  <span>Reported By</span>
                </div>
                <span className="font-medium">John Smith</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Department</span>
                </div>
                <span className="font-medium">Production</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Containment Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: 'Isolate affected batch', status: 'completed' },
                { label: 'Stop machine station CNC-04', status: 'completed' },
                { label: 'Inspect previous 10 units', status: 'in_progress' },
              ].map((action, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  {action.status === 'completed' ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : (
                    <Clock className="h-4 w-4 text-blue-500" />
                  )}
                  <span className={action.status === 'completed' ? 'line-through text-muted-foreground' : ''}>
                    {action.label}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
