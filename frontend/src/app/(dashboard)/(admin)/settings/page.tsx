'use client';

import * as React from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
  User,
  Bell,
  Shield,
  Palette,
  Globe,
  Building2,
  Users,
  Database,
  Key,
  Mail,
  Smartphone,
  Link2,
  ChevronRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface SettingsSection {
  id: string;
  label: string;
  description: string;
  icon: typeof User;
  href: string;
  category: 'personal' | 'organization' | 'system';
}

const sections: SettingsSection[] = [
  // Personal
  { id: 'profile', label: 'Profile', description: 'Your personal information and preferences', icon: User, href: '/settings/profile', category: 'personal' },
  { id: 'notifications', label: 'Notifications', description: 'Email, push, and in-app notification settings', icon: Bell, href: '/settings/notifications', category: 'personal' },
  { id: 'security', label: 'Security', description: 'Password, 2FA, and session management', icon: Shield, href: '/settings/security', category: 'personal' },
  { id: 'appearance', label: 'Appearance', description: 'Theme, colors, and display preferences', icon: Palette, href: '/settings/appearance', category: 'personal' },
  { id: 'language', label: 'Language & Region', description: 'Language, timezone, and date formats', icon: Globe, href: '/settings/language', category: 'personal' },
  
  // Organization
  { id: 'company', label: 'Company', description: 'Company information and branding', icon: Building2, href: '/settings/company', category: 'organization' },
  { id: 'team', label: 'Team Members', description: 'Manage users, roles, and permissions', icon: Users, href: '/settings/team', category: 'organization' },
  { id: 'api', label: 'API Keys', description: 'Manage API access and integrations', icon: Key, href: '/settings/api', category: 'organization' },
  { id: 'integrations', label: 'Integrations', description: 'Connect with external services', icon: Link2, href: '/settings/integrations', category: 'organization' },
  
  // System
  { id: 'data', label: 'Data Management', description: 'Backups, exports, and data retention', icon: Database, href: '/settings/data', category: 'system' },
  { id: 'email', label: 'Email Settings', description: 'Email templates and delivery settings', icon: Mail, href: '/settings/email', category: 'system' },
  { id: 'mobile', label: 'Mobile App', description: 'PWA settings and offline configuration', icon: Smartphone, href: '/settings/mobile', category: 'system' },
];

function SettingsNav({ className }: { className?: string }) {
  const pathname = usePathname();
  const router = useRouter();
  
  const personalSections = sections.filter(s => s.category === 'personal');
  const orgSections = sections.filter(s => s.category === 'organization');
  const systemSections = sections.filter(s => s.category === 'system');

  const NavSection = ({ title, items }: { title: string; items: SettingsSection[] }) => (
    <div className="mb-6">
      <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        {title}
      </h3>
      <div className="space-y-1">
        {items.map((section) => {
          const Icon = section.icon;
          const isActive = pathname === section.href;
          return (
            <button
              key={section.id}
              onClick={() => router.push(section.href)}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors',
                isActive 
                  ? 'bg-primary text-primary-foreground' 
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              )}
            >
              <Icon className="h-4 w-4" />
              {section.label}
            </button>
          );
        })}
      </div>
    </div>
  );

  return (
    <nav className={className}>
      <NavSection title="Personal" items={personalSections} />
      <NavSection title="Organization" items={orgSections} />
      <NavSection title="System" items={systemSections} />
    </nav>
  );
}

function SettingsCard({ section }: { section: SettingsSection }) {
  const router = useRouter();
  const Icon = section.icon;
  
  return (
    <Card 
      className="hover:border-primary/50 cursor-pointer transition-colors"
      onClick={() => router.push(section.href)}
    >
      <CardContent className="p-4 flex items-center gap-4">
        <div className="p-2 bg-muted rounded-lg">
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medium">{section.label}</h3>
          <p className="text-sm text-muted-foreground truncate">{section.description}</p>
        </div>
        <ChevronRight className="h-5 w-5 text-muted-foreground" />
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const personalSections = sections.filter(s => s.category === 'personal');
  const orgSections = sections.filter(s => s.category === 'organization');
  const systemSections = sections.filter(s => s.category === 'system');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and application preferences</p>
      </div>

      {/* Mobile View - Cards */}
      <div className="lg:hidden space-y-6">
        <div>
          <h2 className="text-lg font-semibold mb-3">Personal</h2>
          <div className="space-y-2">
            {personalSections.map((section) => (
              <SettingsCard key={section.id} section={section} />
            ))}
          </div>
        </div>
        
        <div>
          <h2 className="text-lg font-semibold mb-3">Organization</h2>
          <div className="space-y-2">
            {orgSections.map((section) => (
              <SettingsCard key={section.id} section={section} />
            ))}
          </div>
        </div>
        
        <div>
          <h2 className="text-lg font-semibold mb-3">System</h2>
          <div className="space-y-2">
            {systemSections.map((section) => (
              <SettingsCard key={section.id} section={section} />
            ))}
          </div>
        </div>
      </div>

      {/* Desktop View - Grid */}
      <div className="hidden lg:grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Personal Settings</CardTitle>
            <CardDescription>Your preferences and account</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {personalSections.map((section) => {
              const Icon = section.icon;
              return (
                <a
                  key={section.id}
                  href={section.href}
                  className="flex items-center gap-3 p-2 rounded-md hover:bg-muted transition-colors"
                >
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{section.label}</p>
                    <p className="text-xs text-muted-foreground">{section.description}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </a>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Organization</CardTitle>
            <CardDescription>Company and team settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {orgSections.map((section) => {
              const Icon = section.icon;
              return (
                <a
                  key={section.id}
                  href={section.href}
                  className="flex items-center gap-3 p-2 rounded-md hover:bg-muted transition-colors"
                >
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{section.label}</p>
                    <p className="text-xs text-muted-foreground">{section.description}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </a>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">System</CardTitle>
            <CardDescription>Data and technical settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {systemSections.map((section) => {
              const Icon = section.icon;
              return (
                <a
                  key={section.id}
                  href={section.href}
                  className="flex items-center gap-3 p-2 rounded-md hover:bg-muted transition-colors"
                >
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{section.label}</p>
                    <p className="text-xs text-muted-foreground">{section.description}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </a>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
