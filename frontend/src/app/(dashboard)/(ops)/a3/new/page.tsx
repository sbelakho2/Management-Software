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

export default function NewA3Page() {
  const router = useRouter();
  const { toast } = useToast();
  const [isSaving, setIsSaving] = React.useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
    toast({
      title: 'A3 Report Created',
      description: 'The new A3 report has been successfully initialized.',
    });
    router.push('/a3');
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">New A3 Report</h1>
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
