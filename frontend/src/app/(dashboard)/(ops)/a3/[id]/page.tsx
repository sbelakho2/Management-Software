'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { 
  ChevronLeft, 
  Edit, 
  Download, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  FileText,
  Users,
  Target,
  MessageSquare
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { useA3Store } from '@/stores/a3';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';

export default function A3DetailsPage() {
  const router = useRouter();
  const params = useParams();
  const { id } = params;
  const { toast } = useToast();
  
  const { 
    fetchA3ById, 
    updateA3, 
    isLoading 
  } = useA3Store();

  const [a3, setA3] = React.useState<any>(null);
  const [isEditing, setIsEditing] = React.useState(false);

  React.useEffect(() => {
    if (id) {
      loadA3();
    }
  }, [id]);

  const loadA3 = async () => {
    try {
      const data = await fetchA3ById(id as string);
      if (data) {
        setA3(data);
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load A3 details',
        variant: 'destructive',
      });
    }
  };

  if (isLoading && !a3) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-3/4" />
        <div className="grid gap-6 md:grid-cols-3">
          <Skeleton className="h-96 md:col-span-2" />
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  if (!a3) {
    return <div className="py-12 text-center">A3 Report not found</div>;
  }

  // Helper to find specific sections
  const getSectionContent = (type: string) => {
    return a3.sections?.find((s: any) => s.section_type === type)?.content || 'No content provided.';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push('/a3')}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{a3.title}</h1>
              <Badge variant="outline">{a3.a3_number}</Badge>
            </div>
            <p className="text-muted-foreground">Author: {a3.author_name} | Dept: {a3.department || 'N/A'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => toast({ title: 'Export', description: 'Starting PDF export...' })}>
            <Download className="h-4 w-4 mr-2" />
            Export PDF
          </Button>
          <Button onClick={() => setIsEditing(true)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Report
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Analysis & Background</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <section className="space-y-2">
              <h3 className="font-semibold text-sm uppercase text-muted-foreground">1. Background</h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{getSectionContent('background')}</p>
            </section>
            <section className="space-y-2">
              <h3 className="font-semibold text-sm uppercase text-muted-foreground">2. Current Status</h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{getSectionContent('current_condition')}</p>
            </section>
            <section className="space-y-2">
              <h3 className="font-semibold text-sm uppercase text-muted-foreground">3. Goals / Targets</h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{getSectionContent('goal')}</p>
            </section>
            <section className="space-y-2">
              <h3 className="font-semibold text-sm uppercase text-muted-foreground">4. Root Cause Analysis</h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{getSectionContent('root_cause')}</p>
            </section>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Status & Progress</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Overall Progress</span>
                  <span>{a3.progress_percentage}%</span>
                </div>
                <Progress value={a3.progress_percentage} />
              </div>
              <div className="flex items-center justify-between py-2 border-t">
                <span className="text-sm text-muted-foreground">Status</span>
                <Badge className="capitalize">{a3.status}</Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-t">
                <span className="text-sm text-muted-foreground">Priority</span>
                <Badge variant={a3.priority === 'critical' || a3.priority === 'high' ? 'destructive' : 'warning'} className="capitalize">
                  {a3.priority}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-t">
                <span className="text-sm text-muted-foreground">Type</span>
                <span className="text-sm font-medium capitalize">{a3.a3_type.replace('_', ' ')}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Implementation</CardTitle>
              <CardDescription>Countermeasures and follow-up</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <section className="space-y-2">
                  <h4 className="font-medium text-xs uppercase text-muted-foreground">Countermeasures</h4>
                  <p className="text-sm">{getSectionContent('countermeasures')}</p>
                </section>
                <section className="space-y-2 pt-4 border-t">
                  <h4 className="font-medium text-xs uppercase text-muted-foreground">Implementation Plan</h4>
                  <p className="text-sm">{getSectionContent('implementation_plan')}</p>
                </section>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
