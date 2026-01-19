'use client';
import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ChevronLeft, Award, Calendar, User, FileCheck } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useI18n } from '@/contexts/i18n-context';
export default function CertificationDetailsPage() {
  const { t } = useI18n();
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
    <div className="max-w-3xl mx-auto space-y-8 page-fade-in pb-12">
      <div className="flex items-center justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.back()}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('training.certifications.detail.title') || 'Certification Details'}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">STATION: ACADEMY-CERT-01</p>
          </div>
        </div>
        <Button variant="outline" className="rounded-rams-sm border-rams-line">{t('training.certifications.detail.downloadCertificate') || 'Download Certificate'}</Button>
      </div>
      <Card className="overflow-hidden border-rams-line rounded-rams-sm bg-rams-module shadow-none">
        <div className="h-1 bg-rams-orange" />
        <CardHeader className="text-center pb-2 bg-rams-panel/20">
          <div className="mx-auto bg-rams-orange/10 w-16 h-16 border border-rams-orange/20 flex items-center justify-center mb-4">
            <Award className="h-8 w-8 text-rams-orange" />
          </div>
          <CardTitle className="text-2xl font-sans font-black uppercase tracking-tight">{cert.title}</CardTitle>
          <CardDescription className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground/60">{t('training.certifications.detail.certificateOfAchievement') || 'Certificate of Achievement'}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 p-8">
          <div className="flex justify-center">
            <Badge variant="success" className="px-2 py-0.5 rounded-none text-[9px] font-black uppercase tracking-widest">{cert.status.toUpperCase()}</Badge>
          </div>
          
          <div className="grid gap-6 md:grid-cols-2 pt-4">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <User className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">{t('training.certifications.detail.awardedTo') || 'Awarded To'}</p>
                  <p className="text-muted-foreground">{cert.holder}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">{t('training.certifications.detail.issueDate') || 'Issue Date'}</p>
                  <p className="text-muted-foreground">{cert.issuedDate}</p>
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <FileCheck className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">{t('training.certifications.detail.finalScore') || 'Final Score'}</p>
                  <p className="text-muted-foreground">{cert.score}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">{t('training.certifications.detail.expiresOn') || 'Expires On'}</p>
                  <p className="text-muted-foreground">{cert.expiryDate}</p>
                </div>
              </div>
            </div>
          </div>
          <div className="pt-6 border-t text-center">
            <h4 className="font-medium text-sm mb-2">{t('training.certifications.detail.scopeOfCertification') || 'Scope of Certification'}</h4>
            <p className="text-sm text-muted-foreground italic leading-relaxed">
              "{cert.description}"
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
