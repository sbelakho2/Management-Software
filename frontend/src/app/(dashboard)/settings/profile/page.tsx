'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Camera,
  Mail,
  Phone,
  Building2,
  Briefcase,
  MapPin,
  Save,
  Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { getInitials } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

interface ProfileFormData {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  jobTitle: string;
  department: string;
  location: string;
  bio: string;
  timezone: string;
}

const timezones = [
  { value: 'Africa/Casablanca', labelKey: 'settings.profile.timezones.africaCasablanca' },
  { value: 'Europe/Paris', labelKey: 'settings.profile.timezones.europeParis' },
  { value: 'Europe/London', labelKey: 'settings.profile.timezones.europeLondon' },
  { value: 'America/New_York', labelKey: 'settings.profile.timezones.americaNewYork' },
  { value: 'America/Los_Angeles', labelKey: 'settings.profile.timezones.americaLosAngeles' },
];

const departments = [
  { value: 'Engineering', labelKey: 'settings.profile.departments.engineering' },
  { value: 'Production', labelKey: 'settings.profile.departments.production' },
  { value: 'Quality', labelKey: 'settings.profile.departments.quality' },
  { value: 'Sales', labelKey: 'settings.profile.departments.sales' },
  { value: 'Operations', labelKey: 'settings.profile.departments.operations' },
  { value: 'Finance', labelKey: 'settings.profile.departments.finance' },
  { value: 'Human Resources', labelKey: 'settings.profile.departments.humanResources' },
  { value: 'IT', labelKey: 'settings.profile.departments.it' },
];

import { useAuthStore } from '@/stores/auth-store';
import { useToast } from '@/hooks/use-toast';

export default function ProfileSettingsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const { user, updateProfile } = useAuthStore();
  const [isSaving, setIsSaving] = React.useState(false);
  const [formData, setFormData] = React.useState<ProfileFormData>(() => ({
    firstName: user?.full_name?.split(' ')[0] || '',
    lastName: user?.full_name?.split(' ').slice(1).join(' ') || '',
    email: user?.email || '',
    phone: (user as any)?.phone || '',
    jobTitle: (user as any)?.job_title || '',
    department: (user as any)?.department || '',
    location: (user as any)?.location || '',
    bio: (user as any)?.bio || '',
    timezone: (user as any)?.timezone || 'Africa/Casablanca',
  }));

  const handleChange = (field: keyof ProfileFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const { email, ...rest } = formData;
      await updateProfile({
        full_name: `${formData.firstName} ${formData.lastName}`,
        email,
        // job_title, department, etc are not in User type yet, but we'll try to update them if API supports
        ...rest
      } as any);
      toast({
        title: t('settings.profile.toast.updated.title'),
        description: t('settings.profile.toast.updated.description'),
      });
    } catch (error) {
      toast({
        title: t('settings.profile.toast.failed.title'),
        description: t('settings.profile.toast.failed.description'),
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const fullName = `${formData.firstName} ${formData.lastName}`;

  return (
    <div className="space-y-8 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">
              {t('settings.profile.title')}
            </h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">{t('settings.profile.subtitle')}</p>
          </div>
        </div>
        <Button onClick={handleSave} disabled={isSaving} className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none" size="default">
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
              {t('settings.profile.synchronizing')}
            </>
          ) : (
            <>
              <Save className="mr-2 h-3.5 w-3.5" />
              {t('settings.profile.saveChanges')}
            </>
          )}
        </Button>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Avatar Card */}
        <Card className="lg:col-span-1 rounded-rams-sm border border-rams-line bg-rams-module overflow-hidden relative group">
          <div className="absolute top-0 left-0 w-full h-1 bg-rams-orange/20" />
          <CardContent className="pt-10 text-center space-y-6">
            <div className="relative inline-block">
              <div className="p-1 border border-rams-line bg-rams-panel">
                <Avatar className="h-28 w-28 rounded-none border border-rams-line">
                  <AvatarImage src="/avatar.jpg" alt={fullName} />
                  <AvatarFallback className="text-3xl font-sans font-black bg-rams-chassis text-muted-foreground/40">{getInitials(fullName)}</AvatarFallback>
                </Avatar>
              </div>
              <button className="absolute -bottom-2 -right-2 p-3 bg-rams-orange text-black rounded-none border border-black/10 hover:bg-rams-orange/90 transition-none">
                <Camera className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-sans font-black uppercase tracking-tight text-foreground/90">{fullName}</h3>
              <p className="text-[10px] uppercase tracking-[0.25em] font-black text-rams-orange">{formData.jobTitle}</p>
              <div className="flex items-center justify-center gap-2 text-muted-foreground/40 text-[9px] font-mono font-bold uppercase tracking-widest">
                <Building2 className="h-3 w-3" />
                {formData.department}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Basic Info */}
        <Card className="lg:col-span-2 rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('settings.profile.basicInfo')}</CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="firstName" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.profile.firstName')}</Label>
                <Input
                  id="firstName"
                  value={formData.firstName}
                  onChange={(e) => handleChange('firstName', e.target.value)}
                  className="bg-rams-panel border-rams-line h-10 text-[11px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.profile.lastName')}</Label>
                <Input
                  id="lastName"
                  value={formData.lastName}
                  onChange={(e) => handleChange('lastName', e.target.value)}
                  className="bg-rams-panel border-rams-line h-10 text-[11px]"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="bio" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.profile.personnelSummary')}</Label>
              <Textarea
                id="bio"
                placeholder={t('settings.profile.personnelSummaryPlaceholder')}
                value={formData.bio}
                onChange={(e) => handleChange('bio', e.target.value)}
                rows={4}
                className="bg-rams-panel border-rams-line resize-none text-[11px] uppercase leading-relaxed h-32"
              />
            </div>
          </CardContent>
        </Card>

        {/* Contact Info */}
        <Card className="lg:col-span-3 rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('settings.profile.communicationNodes')}</CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="email" className="flex items-center gap-2 text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">
                  <Mail className="h-3 w-3" />
                  {t('settings.profile.emailAddress')}
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  className="bg-rams-panel border-rams-line h-10 text-[11px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone" className="flex items-center gap-2 text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">
                  <Phone className="h-3 w-3" />
                  {t('settings.profile.phoneNumber')}
                </Label>
                <Input
                  id="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => handleChange('phone', e.target.value)}
                  className="bg-rams-panel border-rams-line h-10 text-[11px]"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Work Info */}
        <Card className="lg:col-span-3 rounded-rams-sm border border-rams-line bg-rams-module">
          <CardHeader className="bg-rams-panel/20 border-b border-rams-line">
            <CardTitle className="text-xs font-black uppercase tracking-[0.2em]">{t('settings.profile.organizationalRole')}</CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <Label htmlFor="jobTitle" className="flex items-center gap-2 text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">
                  <Briefcase className="h-3 w-3" />
                  {t('settings.profile.jobTitle')}
                </Label>
                <Input
                  id="jobTitle"
                  value={formData.jobTitle}
                  onChange={(e) => handleChange('jobTitle', e.target.value)}
                  className="bg-rams-panel border-rams-line h-10 text-[11px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="department" className="flex items-center gap-2 text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">
                  <Building2 className="h-3 w-3" />
                  {t('settings.profile.department')}
                </Label>
                <Select 
                  value={formData.department} 
                  onValueChange={(value) => handleChange('department', value)}
                >
                  <SelectTrigger id="department" className="bg-rams-panel border-rams-line h-10 text-[11px]">
                    <SelectValue placeholder={t('settings.profile.selectDepartment')} />
                  </SelectTrigger>
                  <SelectContent>
                      {departments.map(dept => (
                        <SelectItem key={dept.value} value={dept.value}>{t(dept.labelKey).toUpperCase()}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="location" className="flex items-center gap-2 text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">
                  <MapPin className="h-3 w-3" />
                  {t('settings.profile.location')}
                </Label>
                <Input
                  id="location"
                  value={formData.location}
                  onChange={(e) => handleChange('location', e.target.value)}
                  className="bg-rams-panel border-rams-line h-10 text-[11px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="timezone" className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50 ml-1">{t('settings.profile.timezoneSync')}</Label>
                <Select 
                  value={formData.timezone} 
                  onValueChange={(value) => handleChange('timezone', value)}
                >
                  <SelectTrigger id="timezone" className="bg-rams-panel border-rams-line h-10 text-[11px]">
                    <SelectValue placeholder={t('settings.profile.selectTimezone')} />
                  </SelectTrigger>
                  <SelectContent>
                    {timezones.map(tz => (
                      <SelectItem key={tz.value} value={tz.value}>{t(tz.labelKey).toUpperCase()}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
