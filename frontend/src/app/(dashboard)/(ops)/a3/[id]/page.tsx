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
import { useI18n } from '@/contexts/i18n-context';

export default function A3DetailsPage() {
  const { t } = useI18n();
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
    <div className="space-y-8 page-fade-in">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 transition-all" onClick={() => router.push('/a3')}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-heading font-bold tracking-tight ">{a3.title}</h1>
              <Badge variant="outline" className="rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">{a3.a3_number}</Badge>
            </div>
            <p className="text-muted-foreground font-medium text-sm mt-1">Author: {a3.author_name} • Intelligence Node: {a3.department || 'N/A'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary" onClick={() => toast({ title: 'Export', description: 'Starting PDF export...' })}>
            <Download className="h-4 w-4 mr-2" />
            Export Protocol
          </Button>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine" onClick={() => setIsEditing(true)}>
            <Edit className="h-4 w-4 mr-2" />
            Refine Analysis
          </Button>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <Card className="lg:col-span-2 rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-lg font-heading">Structural Analysis</CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Decomposition of organizational abnormalities</CardDescription>
          </CardHeader>
          <CardContent className="space-y-10">
            <section className="space-y-3">
              <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary/60 flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary/40" />
                1. Background Architecture
              </h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap pl-3.5 border-l border-primary/10">{getSectionContent('background')}</p>
            </section>
            <section className="space-y-3">
              <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary/60 flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary/40" />
                2. Current State Synchronization
              </h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap pl-3.5 border-l border-primary/10">{getSectionContent('current_condition')}</p>
            </section>
            <section className="space-y-3">
              <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary/60 flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary/40" />
                3. Strategic Targets
              </h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap pl-3.5 border-l border-primary/10">{getSectionContent('goal')}</p>
            </section>
            <section className="space-y-3">
              <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary/60 flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary/40" />
                4. Root Cause Intelligence
              </h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap pl-3.5 border-l border-primary/10">{getSectionContent('root_cause')}</p>
            </section>
          </CardContent>
        </Card>

        <div className="space-y-8">
          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader>
              <CardTitle className="text-lg font-heading">Protocol Velocity</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
                  <span>Execution Pulse</span>
                  <span className="text-primary">{a3.progress_percentage}%</span>
                </div>
                <Progress value={a3.progress_percentage} className="h-2 bg-primary/10" />
              </div>
              
              <div className="space-y-4 pt-4 border-t border-border/10">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60">Status Node</span>
                  <Badge variant="secondary" className="capitalize rounded-md font-bold">{a3.status}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60">Priority Layer</span>
                  <Badge variant={a3.priority === 'critical' || a3.priority === 'high' ? 'destructive' : 'warning'} className="capitalize rounded-md font-bold">
                    {a3.priority}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60">Logic Type</span>
                  <span className="text-xs font-bold capitalize text-foreground/80">{a3.a3_type.replace('_', ' ')}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md">
            <CardHeader>
              <CardTitle className="text-lg font-heading">Implementation</CardTitle>
              <CardDescription className="text-xs font-medium uppercase tracking-wider">Countermeasures and follow-up protocol</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <section className="space-y-2">
                  <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">Countermeasures</h4>
                  <p className="text-sm font-medium">{getSectionContent('countermeasures')}</p>
                </section>
                <section className="space-y-2 pt-6 border-t border-border/10">
                  <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">Implementation Timeline</h4>
                  <p className="text-sm font-medium">{getSectionContent('implementation_plan')}</p>
                </section>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
