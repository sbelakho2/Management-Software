import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Construction } from 'lucide-react';
import { useI18n } from '@/contexts/i18n-context';

interface ComingSoonProps {
  title: string;
  description?: string;
  backHref?: string;
}

export function ComingSoon({ 
  title, 
  description, 
  backHref = "/today" 
}: ComingSoonProps) {
  const { t } = useI18n();
  return (
    <div className="flex items-center justify-center min-h-[400px] p-6">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-primary/10 rounded-full">
              <Construction className="h-10 w-10 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl">{title}</CardTitle>
          <CardDescription>{description ?? t('components.comingSoon.defaultMessage')}</CardDescription>
        </CardHeader>
        <CardContent>
          <Link href={backHref}>
            <Button>{t('components.comingSoon.goBack')}</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
