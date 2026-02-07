'use client';
import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ChevronLeft, Award, Calendar, User, FileCheck } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useI18n } from '@/contexts/i18n-context';
import { useTrainingStore } from '@/stores/training';

export default function CertificationDetailsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useParams();
  
  const { records, userSkills, fetchRecords, fetchUserSkills, isLoading } = useTrainingStore();

  React.useEffect(() => {
    fetchRecords();
    fetchUserSkills();
  }, [fetchRecords, fetchUserSkills]);

  const cert = React.useMemo(() => {
    // Try to find in Training Records first (usually contains score/history)
    const record = records.find(r => r.id === params.id);
    if (record) {
        return {
            id: record.id,
            title: record.training_title,
            issuedBy: 'System Authority', // Placeholder
            issuedDate: record.completed_at ? new Date(record.completed_at).toLocaleDateString() : '-',
            expiryDate: '-', // Records might not have expiry, skills do
            status: record.status,
            holder: record.user_name,
            score: record.score ? `${record.score}/100` : '-',
            description: `Training record for ${record.training_title}`,
        };
    }

    // Fallback to UserSkills (current certification status)
    const skill = userSkills.find(s => s.id === params.id);
    if (skill) {
        return {
            id: skill.id,
            title: skill.skill_name,
            issuedBy: 'Competency Board',
            issuedDate: skill.certified_at ? new Date(skill.certified_at).toLocaleDateString() : '-',
            expiryDate: skill.expires_at ? new Date(skill.expires_at).toLocaleDateString() : 'No Expiry',
            status: skill.status,
            holder: `User ${skill.user_id}`, // Ideally would fetch user name, but we might verify if userSkills has it
            score: `Proficiency: ${skill.proficiency_level}`,
            description: `Verified competency level ${skill.proficiency_level} for ${skill.skill_name}`,
        };
    }
    
    return null;
  }, [records, userSkills, params.id]);

  if (!cert && !isLoading) {
      // Allow fallback to mock if real data not found for demo purposes or show Not Found
      // For now, let's keep the UI safe.
      return (
         <div className="flex flex-col items-center justify-center p-12">
             <div className="text-muted-foreground font-mono uppercase">Certification Record Not Found</div>
             <Button variant="link" onClick={() => router.back()}>Return to Console</Button>
         </div>
      );
  }

  // Use a loading state if data is loading and no cert found yet
  if (!cert && isLoading) {
     return <div className="p-12 text-center text-xs font-mono uppercase animate-pulse">Retrieving Certification Data...</div>;
  }

  // If found (or we want to fallback to mock for safety, but we want real data now)
  // We will trust the found cert. TypeScript needs help knowing cert is non-null after early returns.
  const certData = cert!;

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
          <CardTitle className="text-2xl font-sans font-black uppercase tracking-tight">{certData.title}</CardTitle>
          <CardDescription className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground/60">{t('training.certifications.detail.certificateOfAchievement') || 'Certificate of Achievement'}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 p-8">
          <div className="flex justify-center">
            <Badge variant="success" className="px-2 py-0.5 rounded-none text-[9px] font-black uppercase tracking-widest">{certData.status.toUpperCase()}</Badge>
          </div>
          
          <div className="grid gap-6 md:grid-cols-2 pt-4">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <User className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">{t('training.certifications.detail.awardedTo') || 'Awarded To'}</p>
                  <p className="text-muted-foreground">{certData.holder}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">{t('training.certifications.detail.issueDate') || 'Issue Date'}</p>
                  <p className="text-muted-foreground">{certData.issuedDate}</p>
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <FileCheck className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">{t('training.certifications.detail.finalScore') || 'Final Score'}</p>
                  <p className="text-muted-foreground">{certData.score}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <p className="font-medium">{t('training.certifications.detail.expiresOn') || 'Expires On'}</p>
                  <p className="text-muted-foreground">{certData.expiryDate}</p>
                </div>
              </div>
            </div>
          </div>
          <div className="pt-6 border-t text-center">
            <h4 className="font-medium text-sm mb-2">{t('training.certifications.detail.scopeOfCertification') || 'Scope of Certification'}</h4>
            <p className="text-sm text-muted-foreground italic leading-relaxed">
              "{certData.description}"
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
