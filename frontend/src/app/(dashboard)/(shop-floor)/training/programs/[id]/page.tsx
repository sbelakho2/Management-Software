'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ChevronLeft, Clock, BookOpen, Users, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

export default function ProgramDetailsPage() {
  const router = useRouter();
  const params = useParams();

  // Mock data for display
  const program = {
    id: params.id,
    title: 'Advanced Machining Center Operation',
    description: 'Comprehensive training on high-speed CNC centers, including setup, programming, and maintenance.',
    category: 'Technical Skills',
    level: 'Advanced',
    duration: '40 hours',
    instructor: 'Robert Smith',
    enrolledCount: 12,
    completionRate: 85,
    modules: [
      { id: 'm1', title: 'Unit 1: Safety & Pre-checks', duration: '4h', status: 'completed' },
      { id: 'm2', title: 'Unit 2: Setup & Calibration', duration: '8h', status: 'completed' },
      { id: 'm3', title: 'Unit 3: Advanced Programming', duration: '12h', status: 'in_progress' },
      { id: 'm4', title: 'Unit 4: Quality & Inspection', duration: '8h', status: 'todo' },
      { id: 'm5', title: 'Unit 5: Maintenance Basics', duration: '8h', status: 'todo' },
    ]
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{program.title}</h1>
            <Badge variant="outline">{program.level}</Badge>
          </div>
          <p className="text-muted-foreground">{program.category}</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Program Description</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed">{program.description}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Curriculum</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {program.modules.map((module, idx) => (
                  <div key={module.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-bold">
                        {idx + 1}
                      </div>
                      <div>
                        <p className="text-sm font-medium">{module.title}</p>
                        <p className="text-xs text-muted-foreground">{module.duration}</p>
                      </div>
                    </div>
                    {module.status === 'completed' ? (
                      <CheckCircle className="h-5 w-5 text-emerald-500" />
                    ) : module.status === 'in_progress' ? (
                      <Badge variant="secondary">In Progress</Badge>
                    ) : (
                      <Badge variant="outline">Scheduled</Badge>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between text-sm py-2 border-b">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Clock className="h-4 w-4" /> Duration
                </span>
                <span className="font-medium">{program.duration}</span>
              </div>
              <div className="flex items-center justify-between text-sm py-2 border-b">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Users className="h-4 w-4" /> Instructor
                </span>
                <span className="font-medium">{program.instructor}</span>
              </div>
              <div className="flex items-center justify-between text-sm py-2">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <BookOpen className="h-4 w-4" /> Enrolled
                </span>
                <span className="font-medium">{program.enrolledCount} active users</span>
              </div>
              <div className="pt-4">
                <Button className="w-full">Continue Learning</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
