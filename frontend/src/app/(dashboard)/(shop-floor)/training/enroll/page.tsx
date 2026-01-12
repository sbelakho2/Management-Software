'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, GraduationCap, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
export default function EnrollTrainingPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const programs = [
    { id: '1', title: 'Safety Fundamentals 2024' },
    { id: '2', title: 'Lean Six Sigma White Belt' },
    { id: '3', title: 'Advanced Machining Center Operation' },
    { id: '4', title: 'Quality Assurance - Basic' },
  ];
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      toast({
        title: 'Enrolled Successfully',
        description: 'You have been added to the training program.',
      });
      router.push('/training');
    }, 1000);
  };
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Enroll in Training</h1>
          <p className="text-muted-foreground">Join a new development program</p>
        </div>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Enrollment Form</CardTitle>
          <CardDescription>Select a program and confirm your enrollment</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="program">Training Program</Label>
              <Select required>
                <SelectTrigger>
                  <SelectValue placeholder="Select a program" />
                </SelectTrigger>
                <SelectContent>
                  {programs.map(p => (
                    <SelectItem key={p.id} value={p.id}>{p.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reason">Reason for Enrollment (Optional)</Label>
              <Input id="reason" placeholder="e.g., Required for promotion, Skill refresh..." />
            </div>
            <div className="pt-4 flex gap-2">
              <Button type="button" variant="outline" className="flex-1" onClick={() => router.back()}>Cancel</Button>
              <Button type="submit" className="flex-1" disabled={isSubmitting}>
                {isSubmitting ? 'Enrolling...' : 'Confirm Enrollment'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
