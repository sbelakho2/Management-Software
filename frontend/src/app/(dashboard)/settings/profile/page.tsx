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
      await updateProfile({
        full_name: `${formData.firstName} ${formData.lastName}`,
        email: formData.email,
        // job_title, department, etc are not in User type yet, but we'll try to update them if API supports
        ...formData
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
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push('/settings')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Profile Settings</h1>
          <p className="text-muted-foreground">Manage your personal information</p>
        </div>
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Save Changes
            </>
          )}
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Avatar Card */}
        <Card className="lg:col-span-1">
          <CardContent className="pt-6 text-center">
            <div className="relative inline-block">
              <Avatar className="h-24 w-24">
                <AvatarImage src="/avatar.jpg" alt={fullName} />
                <AvatarFallback className="text-2xl">{getInitials(fullName)}</AvatarFallback>
              </Avatar>
              <button className="absolute bottom-0 right-0 p-2 bg-primary text-primary-foreground rounded-full shadow-lg hover:bg-primary/90 transition-colors">
                <Camera className="h-4 w-4" />
              </button>
            </div>
            <h3 className="mt-4 text-lg font-semibold">{fullName}</h3>
            <p className="text-sm text-muted-foreground">{formData.jobTitle}</p>
            <p className="text-sm text-muted-foreground">{formData.department}</p>
          </CardContent>
        </Card>

        {/* Basic Info */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Basic Information</CardTitle>
            <CardDescription>Your public profile information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="firstName">First Name</Label>
                <Input
                  id="firstName"
                  value={formData.firstName}
                  onChange={(e) => handleChange('firstName', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName">Last Name</Label>
                <Input
                  id="lastName"
                  value={formData.lastName}
                  onChange={(e) => handleChange('lastName', e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="bio">Bio</Label>
              <Textarea
                id="bio"
                placeholder="Tell us about yourself..."
                value={formData.bio}
                onChange={(e) => handleChange('bio', e.target.value)}
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* Contact Info */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-base">Contact Information</CardTitle>
            <CardDescription>How others can reach you</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="email" className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  Email Address
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone" className="flex items-center gap-2">
                  <Phone className="h-4 w-4" />
                  Phone Number
                </Label>
                <Input
                  id="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => handleChange('phone', e.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Work Info */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-base">Work Information</CardTitle>
            <CardDescription>Your role and location</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <Label htmlFor="jobTitle" className="flex items-center gap-2">
                  <Briefcase className="h-4 w-4" />
                  Job Title
                </Label>
                <Input
                  id="jobTitle"
                  value={formData.jobTitle}
                  onChange={(e) => handleChange('jobTitle', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="department" className="flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  Department
                </Label>
                <Select 
                  value={formData.department} 
                  onValueChange={(value) => handleChange('department', value)}
                >
                  <SelectTrigger id="department">
                    <SelectValue placeholder="Select department" />
                  </SelectTrigger>
                  <SelectContent>
                    {departments.map(dept => (
                      <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="location" className="flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  Location
                </Label>
                <Input
                  id="location"
                  value={formData.location}
                  onChange={(e) => handleChange('location', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Select 
                  value={formData.timezone} 
                  onValueChange={(value) => handleChange('timezone', value)}
                >
                  <SelectTrigger id="timezone">
                    <SelectValue placeholder="Select timezone" />
                  </SelectTrigger>
                  <SelectContent>
                    {timezones.map(tz => (
                      <SelectItem key={tz.value} value={tz.value}>{tz.label}</SelectItem>
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
