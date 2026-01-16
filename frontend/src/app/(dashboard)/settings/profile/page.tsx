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
  { value: 'Africa/Casablanca', label: '(GMT+0) Casablanca' },
  { value: 'Europe/Paris', label: '(GMT+1) Paris' },
  { value: 'Europe/London', label: '(GMT+0) London' },
  { value: 'America/New_York', label: '(GMT-5) New York' },
  { value: 'America/Los_Angeles', label: '(GMT-8) Los Angeles' },
];

const departments = [
  'Engineering',
  'Production',
  'Quality',
  'Sales',
  'Operations',
  'Finance',
  'Human Resources',
  'IT',
];

import { useAuthStore } from '@/stores/auth-store';
import { useToast } from '@/hooks/use-toast';

export default function ProfileSettingsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { user, updateProfile } = useAuthStore();
  const [isSaving, setIsSaving] = React.useState(false);
  const [formData, setFormData] = React.useState<ProfileFormData>({
    firstName: user?.full_name?.split(' ')[0] || 'John',
    lastName: user?.full_name?.split(' ').slice(1).join(' ') || 'Doe',
    email: user?.email || 'john.doe@sensei.ma',
    phone: (user as any)?.phone || '+212 5XX-XXXXXX',
    jobTitle: (user as any)?.job_title || 'Production Manager',
    department: (user as any)?.department || 'Production',
    location: (user as any)?.location || 'Casablanca, Morocco',
    bio: (user as any)?.bio || 'Experienced manufacturing professional with focus on lean processes and continuous improvement.',
    timezone: (user as any)?.timezone || 'Africa/Casablanca',
  });

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
        title: 'Profile Updated',
        description: 'Your changes have been saved successfully.',
      });
    } catch (error) {
      toast({
        title: 'Update Failed',
        description: 'There was an error saving your changes.',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const fullName = `${formData.firstName} ${formData.lastName}`;

  return (
    <div className="space-y-8 page-fade-in max-w-4xl">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 hover:text-primary transition-all" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              Profile Settings
            </h1>
            <p className="text-muted-foreground font-medium text-sm">Manage your personal identity and organizational role</p>
          </div>
        </div>
        <Button onClick={handleSave} disabled={isSaving} className="rounded-2xl shadow-glow subtle-shine h-12 px-8" size="lg">
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Synchronizing...
            </>
          ) : (
            <>
              <Save className="mr-2 h-5 w-5" />
              Save Changes
            </>
          )}
        </Button>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Avatar Card */}
        <Card className="lg:col-span-1 overflow-hidden relative group">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary/50 to-accent/50 opacity-0 group-hover:opacity-100 transition-opacity" />
          <CardContent className="pt-10 text-center space-y-4">
            <div className="relative inline-block">
              <div className="p-1 rounded-full bg-gradient-to-br from-primary/20 to-accent/20">
                <Avatar className="h-28 w-28 border-4 border-background shadow-premium">
                  <AvatarImage src="/avatar.jpg" alt={fullName} />
                  <AvatarFallback className="text-3xl font-heading bg-muted/30">{getInitials(fullName)}</AvatarFallback>
                </Avatar>
              </div>
              <button className="absolute bottom-1 right-1 p-2.5 bg-primary text-primary-foreground rounded-xl shadow-glow hover:scale-110 active:scale-95 transition-all duration-300">
                <Camera className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-1">
              <h3 className="text-xl font-heading font-bold tracking-tight">{fullName}</h3>
              <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-primary/60">{formData.jobTitle}</p>
              <div className="flex items-center justify-center gap-2 text-muted-foreground/60 text-xs font-medium">
                <Building2 className="h-3 w-3" />
                {formData.department}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Basic Info */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg font-heading">Basic Information</CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Your public identity and biography</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="space-y-2.5">
                <Label htmlFor="firstName" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">First Name</Label>
                <Input
                  id="firstName"
                  value={formData.firstName}
                  onChange={(e) => handleChange('firstName', e.target.value)}
                  className="h-12"
                />
              </div>
              <div className="space-y-2.5">
                <Label htmlFor="lastName" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Last Name</Label>
                <Input
                  id="lastName"
                  value={formData.lastName}
                  onChange={(e) => handleChange('lastName', e.target.value)}
                  className="h-12"
                />
              </div>
            </div>

            <div className="space-y-2.5">
              <Label htmlFor="bio" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Bio</Label>
              <Textarea
                id="bio"
                placeholder="Professional summary..."
                value={formData.bio}
                onChange={(e) => handleChange('bio', e.target.value)}
                rows={4}
                className="rounded-2xl bg-background/50 border-border/50 focus:border-primary/50 transition-all shadow-inner-soft resize-none"
              />
            </div>
          </CardContent>
        </Card>

        {/* Contact Info */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-lg font-heading">Contact Information</CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">How the organization communicates with you</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="space-y-2.5">
                <Label htmlFor="email" className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">
                  <Mail className="h-3 w-3" />
                  Email Address
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  className="h-12"
                />
              </div>
              <div className="space-y-2.5">
                <Label htmlFor="phone" className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">
                  <Phone className="h-3 w-3" />
                  Phone Number
                </Label>
                <Input
                  id="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => handleChange('phone', e.target.value)}
                  className="h-12"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Work Info */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-lg font-heading">Organizational Role</CardTitle>
            <CardDescription className="text-xs font-medium uppercase tracking-wider">Your position within the factory hierarchy</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2.5">
                <Label htmlFor="jobTitle" className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">
                  <Briefcase className="h-3 w-3" />
                  Job Title
                </Label>
                <Input
                  id="jobTitle"
                  value={formData.jobTitle}
                  onChange={(e) => handleChange('jobTitle', e.target.value)}
                  className="h-12"
                />
              </div>
              <div className="space-y-2.5">
                <Label htmlFor="department" className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">
                  <Building2 className="h-3 w-3" />
                  Department
                </Label>
                <Select 
                  value={formData.department} 
                  onValueChange={(value) => handleChange('department', value)}
                >
                  <SelectTrigger id="department" className="h-12 rounded-2xl bg-background/50 border-border/50">
                    <SelectValue placeholder="Select department" />
                  </SelectTrigger>
                  <SelectContent className="rounded-2xl shadow-premium">
                    {departments.map(dept => (
                      <SelectItem key={dept} value={dept} className="rounded-xl m-1">{dept}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2.5">
                <Label htmlFor="location" className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">
                  <MapPin className="h-3 w-3" />
                  Location
                </Label>
                <Input
                  id="location"
                  value={formData.location}
                  onChange={(e) => handleChange('location', e.target.value)}
                  className="h-12"
                />
              </div>
              <div className="space-y-2.5">
                <Label htmlFor="timezone" className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1">Timezone</Label>
                <Select 
                  value={formData.timezone} 
                  onValueChange={(value) => handleChange('timezone', value)}
                >
                  <SelectTrigger id="timezone" className="h-12 rounded-2xl bg-background/50 border-border/50">
                    <SelectValue placeholder="Select timezone" />
                  </SelectTrigger>
                  <SelectContent className="rounded-2xl shadow-premium">
                    {timezones.map(tz => (
                      <SelectItem key={tz.value} value={tz.value} className="rounded-xl m-1">{tz.label}</SelectItem>
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
