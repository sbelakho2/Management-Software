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
import { useAuthStore } from '@/stores';
import { cn } from '@/lib/utils';

interface SettingsSection {
  id: string;
  label: string;
  description: string;
  icon: typeof User;
  href: string;
  category: 'personal' | 'organization' | 'system';
  adminOnly?: boolean;
}

const sections: SettingsSection[] = [
  // Personal
  { id: 'profile', label: 'Profile', description: 'Your personal information and preferences', icon: User, href: '/settings/profile', category: 'personal' },
  { id: 'notifications', label: 'Notifications', description: 'Email, push, and in-app notification settings', icon: Bell, href: '/settings/notifications', category: 'personal' },
  { id: 'security', label: 'Security', description: 'Password, 2FA, and session management', icon: Shield, href: '/settings/security', category: 'personal' },
  { id: 'appearance', label: 'Appearance', description: 'Theme, colors, and display preferences', icon: Palette, href: '/settings/appearance', category: 'personal' },
  { id: 'language', label: 'Language & Region', description: 'Language, timezone, and date formats', icon: Globe, href: '/settings/language', category: 'personal' },
  
  // Organization
  { id: 'company', label: 'Company', description: 'Company information and branding', icon: Building2, href: '/settings/company', category: 'organization', adminOnly: true },
  { id: 'team', label: 'Team Members', description: 'Manage users, roles, and permissions', icon: Users, href: '/settings/team', category: 'organization', adminOnly: true },
  { id: 'api', label: 'API Keys', description: 'Manage API access and integrations', icon: Key, href: '/settings/api', category: 'organization', adminOnly: true },
  { id: 'integrations', label: 'Integrations', description: 'Connect with external services', icon: Link2, href: '/settings/integrations', category: 'organization', adminOnly: true },
  
  // System
  { id: 'data', label: 'Data Management', description: 'Backups, exports, and data retention', icon: Database, href: '/settings/data', category: 'system', adminOnly: true },
  { id: 'email', label: 'Email Settings', description: 'Email templates and delivery settings', icon: Mail, href: '/settings/email', category: 'system', adminOnly: true },
  { id: 'mobile', label: 'Mobile App', description: 'PWA settings and offline configuration', icon: Smartphone, href: '/settings/mobile', category: 'system', adminOnly: true },
];

function SettingsNav({ className }: { className?: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';
  
  const filteredSections = sections.filter(s => !s.adminOnly || isAdmin);
  const personalSections = filteredSections.filter(s => s.category === 'personal');
  const orgSections = filteredSections.filter(s => s.category === 'organization');
  const systemSections = filteredSections.filter(s => s.category === 'system');

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
      className="group cursor-pointer rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1.5 hover:border-primary/20"
      onClick={() => router.push(section.href)}
    >
      <CardContent className="p-6 flex items-center gap-6">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-sm transition-transform duration-500 group-hover:scale-110 group-hover:bg-primary group-hover:text-primary-foreground">
          <Icon className="h-7 w-7" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-heading font-bold text-lg tracking-tight group-hover:text-primary transition-colors">{section.label}</h3>
          <p className="text-xs text-muted-foreground line-clamp-1 font-medium mt-1 leading-relaxed">{section.description}</p>
        </div>
        <ChevronRight className="h-5 w-5 text-muted-foreground/30 group-hover:text-primary group-hover:translate-x-1 transition-all" />
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';
  
  const filteredSections = sections.filter(s => !s.adminOnly || isAdmin);
  const personalSections = filteredSections.filter(s => s.category === 'personal');
  const orgSections = filteredSections.filter(s => s.category === 'organization');
  const systemSections = filteredSections.filter(s => s.category === 'system');

  return (
    <div className="space-y-10 page-fade-in max-w-6xl mx-auto">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
          Control Center
        </h1>
        <p className="text-muted-foreground font-medium">Configure your personal interface and enterprise parameters</p>
      </div>

      <div className="space-y-12">
        <section>
          <h2 className="text-[10px] font-bold uppercase tracking-[0.3em] text-muted-foreground/40 mb-6 flex items-center gap-3">
            <span className="h-px flex-1 bg-border/50" />
            Personal Intelligence
            <span className="h-px flex-1 bg-border/50" />
          </h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {personalSections.map((section) => (
              <SettingsCard key={section.id} section={section} />
            ))}
          </div>
        </section>
        
        {orgSections.length > 0 && (
          <section>
            <h2 className="text-[10px] font-bold uppercase tracking-[0.3em] text-muted-foreground/40 mb-6 flex items-center gap-3">
              <span className="h-px flex-1 bg-border/50" />
              Organizational Parameters
              <span className="h-px flex-1 bg-border/50" />
            </h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {orgSections.map((section) => (
                <SettingsCard key={section.id} section={section} />
              ))}
            </div>
          </section>
        )}
        
        {systemSections.length > 0 && (
          <section>
            <h2 className="text-[10px] font-bold uppercase tracking-[0.3em] text-muted-foreground/40 mb-6 flex items-center gap-3">
              <span className="h-px flex-1 bg-border/50" />
              System Architecture
              <span className="h-px flex-1 bg-border/50" />
            </h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {systemSections.map((section) => (
                <SettingsCard key={section.id} section={section} />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
