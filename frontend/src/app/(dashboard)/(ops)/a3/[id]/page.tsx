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

export default function A3DetailsPage() {
  const router = useRouter();
  const params = useParams();

  // Mock data for display
  const a3 = {
    id: params.id,
    a3_number: 'A3-2024-001',
    title: 'Optimization of Machining Center B Cycle Time',
    status: 'in_progress',
    type: 'problem_solving',
    priority: 'high',
    author: 'John Doe',
    sponsor: 'Jane Smith',
    progress: 45,
    department: 'Manufacturing',
    background: 'Cycle times for Center B have increased by 15% over the last 3 months due to frequent tool changes and setup delays.',
    currentStatus: 'Average cycle time: 42 mins. Targeted cycle time: 35 mins.',
    goals: 'Reduce setup time by 20% and tool change time by 10%.',
    analysis: 'Root cause identified as lack of standardized setup kits and disorganized tool crib.',
    proposedActions: [
      { id: '1', task: 'Implement Shadow Boards', owner: 'Mike R.', status: 'completed' },
      { id: '2', task: 'Standardize Setup Sheets', owner: 'John D.', status: 'in_progress' },
      { id: '3', task: 'Pre-kit Tools for Shift', owner: 'Sarah L.', status: 'todo' },
    ]
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
            <p className="text-muted-foreground">Author: {a3.author} | Dept: {a3.department}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export PDF
          </Button>
          <Button onClick={() => setIsEditing?.(true)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Report
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <section className="space-y-2">
              <h3 className="font-semibold text-sm uppercase text-muted-foreground">1. Background</h3>
              <p className="text-sm leading-relaxed">{a3.background}</p>
            </section>
            <section className="space-y-2">
              <h3 className="font-semibold text-sm uppercase text-muted-foreground">2. Current Status</h3>
              <p className="text-sm leading-relaxed">{a3.currentStatus}</p>
            </section>
            <section className="space-y-2">
              <h3 className="font-semibold text-sm uppercase text-muted-foreground">3. Goals / Targets</h3>
              <p className="text-sm leading-relaxed">{a3.goals}</p>
            </section>
            <section className="space-y-2">
              <h3 className="font-semibold text-sm uppercase text-muted-foreground">4. Root Cause Analysis</h3>
              <p className="text-sm leading-relaxed">{a3.analysis}</p>
            </section>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Overall Progress</span>
                  <span>{a3.progress}%</span>
                </div>
                <Progress value={a3.progress} />
              </div>
              <div className="flex items-center justify-between py-2 border-t">
                <span className="text-sm text-muted-foreground">Status</span>
                <Badge>{a3.status}</Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-t">
                <span className="text-sm text-muted-foreground">Priority</span>
                <Badge variant="warning">{a3.priority}</Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Proposed Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {a3.proposedActions.map(action => (
                  <li key={action.id} className="flex items-start gap-3 text-sm">
                    {action.status === 'completed' ? (
                      <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                    ) : action.status === 'in_progress' ? (
                      <Clock className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                    ) : (
                      <div className="h-4 w-4 border rounded-full shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p className="font-medium">{action.task}</p>
                      <p className="text-xs text-muted-foreground">Owner: {action.owner}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
