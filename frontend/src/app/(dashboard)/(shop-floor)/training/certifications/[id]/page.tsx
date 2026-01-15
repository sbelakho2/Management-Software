'use client';
import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ChevronLeft, Award, Calendar, User, FileCheck } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
export default function CertificationDetailsPage() {
  const router = useRouter();
  const params = useParams();
  // Mock data for display
  const cert = {
    id: params.id,
    title: 'Precision Machining Level 2',
    issuedBy: 'Internal Training Dept',
    issuedDate: '2023-05-15',
    expiryDate: '2025-05-15',
    status: 'active',
    holder: 'John Doe',
    score: '94/100',
    description: 'Demonstrated proficiency in operating multi-axis machining centers with tolerances within 0.001".',
  };
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">Certification Details</h1>
          </div>
        </div>
        <Button variant="outline">Download Certificate</Button>
      </div>
      <Card className="overflow-hidden border-primary/20">
        <div className="h-2 bg-primary" />
        <CardHeader className="text-center pb-2">
          <div className="mx-auto bg-primary/10 w-16 h-16 rounded-full flex items-center justify-center mb-4">
            <Award className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl font-serif tracking-tight">{cert.title}</CardTitle>
          <CardDescription>Certificate of Achievement</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex justify-center">
            <Badge className="px-4 py-1 text-sm">{cert.status.toUpperCase()}</Badge>
          </div>
          
          <div className="grid gap-6 md:grid-cols-2 pt-4">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <User className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">Awarded To</p>
                  <p className="text-muted-foreground">{cert.holder}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">Issue Date</p>
                  <p className="text-muted-foreground">{cert.issuedDate}</p>
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <FileCheck className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">Final Score</p>
                  <p className="text-muted-foreground">{cert.score}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">Expires On</p>
                  <p className="text-muted-foreground">{cert.expiryDate}</p>
                </div>
              </div>
            </div>
          </div>
          <div className="pt-6 border-t text-center">
            <h4 className="font-medium text-sm mb-2">Scope of Certification</h4>
            <p className="text-sm text-muted-foreground italic leading-relaxed">
              "{cert.description}"
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
