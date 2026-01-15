'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Save,
  FileText,
  Target,
  Search,
  Zap,
  CheckCircle2,
  BarChart3,
  Users,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';

import { useA3Store } from '@/stores/a3';

export default function NewA3Page() {
  const router = useRouter();
  const { toast } = useToast();
  const createA3 = useA3Store(state => state.createA3);
  const [isSaving, setIsSaving] = React.useState(false);
  const [title, setTitle] = React.useState('');

  const handleSave = async () => {
    if (!title) {
      toast({
        title: 'Error',
        description: 'Please enter a title for the A3 report.',
        variant: 'destructive',
      });
      return;
    }

    setIsSaving(true);
    try {
      await createA3({ 
        title,
        status: 'draft',
        priority: 'medium',
        a3_type: 'problem_solving'
      });
      toast({
        title: 'A3 Report Created',
        description: 'The new A3 report has been successfully initialized.',
      });
      router.push('/a3');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create A3 report. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">New A3 Report</h1>
            <p className="text-muted-foreground">Initialize a new structured problem-solving report</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            <Save className="mr-2 h-4 w-4" />
            {isSaving ? 'Initializing...' : 'Create A3'}
          </Button>
        </div>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Basic Information</CardTitle>
          <CardDescription>Enter the title and basic details for this A3 report</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">A3 Title</Label>
            <Input 
              id="title"
              placeholder="e.g., Reducing Defect Rate in Assembly Line A" 
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4 text-primary" />
              1. Background
            </CardTitle>
            <CardDescription>Define the context and importance of the problem</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder="Why are we talking about this? What is the business context?" 
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Target className="h-4 w-4 text-primary" />
              2. Current Condition
            </CardTitle>
            <CardDescription>Describe the current state with data/facts</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder="What is happening now? Use charts, images, or data if possible." 
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="h-4 w-4 text-primary" />
              3. Goal / Target Condition
            </CardTitle>
            <CardDescription>Define what success looks like</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder="What specific outcome do we want to achieve? By when?" 
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Search className="h-4 w-4 text-primary" />
              4. Root Cause Analysis
            </CardTitle>
            <CardDescription>Identify the underlying cause(s)</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder="Use 5-Whys or Fishbone to find the real cause." 
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Zap className="h-4 w-4 text-primary" />
              5. Countermeasures
            </CardTitle>
            <CardDescription>Proposed actions to address root causes</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder="What are we going to do to fix it?" 
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="h-4 w-4 text-primary" />
              6. Implementation Plan
            </CardTitle>
            <CardDescription>Who, what, when, where</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea 
              placeholder="Detailed steps for implementation." 
              className="min-h-[120px]"
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-4 w-4 text-primary" />
            Team & Stakeholders
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Report Owner</Label>
              <Input placeholder="Search users..." />
            </div>
            <div className="space-y-2">
              <Label>Contributors</Label>
              <Input placeholder="Add team members..." />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
