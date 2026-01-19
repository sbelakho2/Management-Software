'use client';

import * as React from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useI18n } from '@/contexts/i18n-context';
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
  Settings,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useAuthStore } from '@/stores';
import { cn } from '@/lib/utils';
import { SectionHeader } from '@/components/ui/content-card';

interface SettingsSection {
  id: string;
  label: string;
  description: string;
  descriptionKey: string;
  labelKey: string;
  icon: typeof User;
  href: string;
  category: 'personal' | 'organization' | 'system';
  adminOnly?: boolean;
}

const sections: SettingsSection[] = [
  // Personal
  { id: 'profile', label: 'Profile', labelKey: 'settings.profile.title', description: 'Your personal information and preferences', descriptionKey: 'settings.profile.subtitle', icon: User, href: '/settings/profile', category: 'personal' },
  { id: 'notifications', label: 'Notifications', labelKey: 'settings.notifications.title', description: 'Email, push, and in-app notification settings', descriptionKey: 'settings.notifications.subtitle', icon: Bell, href: '/settings/notifications', category: 'personal' },
  { id: 'security', label: 'Security', labelKey: 'settings.security.title', description: 'Password, 2FA, and session management', descriptionKey: 'settings.security.subtitle', icon: Shield, href: '/settings/security', category: 'personal' },
  { id: 'appearance', label: 'Appearance', labelKey: 'settings.appearance.title', description: 'Theme, colors, and display preferences', descriptionKey: 'settings.appearance.subtitle', icon: Palette, href: '/settings/appearance', category: 'personal' },
  { id: 'language', label: 'Language & Region', labelKey: 'settings.localization.title', description: 'Language, timezone, and date formats', descriptionKey: 'settings.localization.description', icon: Globe, href: '/settings/language', category: 'personal' },
  
  // Organization
  { id: 'company', label: 'Company', labelKey: 'pages.settings.company.title', description: 'Company information and branding', descriptionKey: 'pages.settings.company.subtitle', icon: Building2, href: '/settings/company', category: 'organization', adminOnly: true },
  { id: 'team', label: 'Team Members', labelKey: 'pages.settings.team.title', description: 'Manage users, roles, and permissions', descriptionKey: 'pages.settings.team.subtitle', icon: Users, href: '/settings/team', category: 'organization', adminOnly: true },
  { id: 'api', label: 'API Keys', labelKey: 'pages.settings.api.title', description: 'Manage API access and integrations', descriptionKey: 'pages.settings.api.subtitle', icon: Key, href: '/settings/api', category: 'organization', adminOnly: true },
  { id: 'integrations', label: 'Integrations', labelKey: 'pages.settings.integrations.title', description: 'Connect with external services', descriptionKey: 'pages.settings.integrations.subtitle', icon: Link2, href: '/settings/integrations', category: 'organization', adminOnly: true },
  
  // System
  { id: 'data', label: 'Data Management', labelKey: 'pages.settings.data.title', description: 'Backups, exports, and data retention', descriptionKey: 'pages.settings.data.subtitle', icon: Database, href: '/settings/data', category: 'system', adminOnly: true },
  { id: 'email', label: 'Email Settings', labelKey: 'pages.settings.email.title', description: 'Email templates and delivery settings', descriptionKey: 'pages.settings.email.subtitle', icon: Mail, href: '/settings/email', category: 'system', adminOnly: true },
  { id: 'mobile', label: 'Mobile App', labelKey: 'pages.settings.mobile.title', description: 'PWA settings and offline configuration', descriptionKey: 'pages.settings.mobile.subtitle', icon: Smartphone, href: '/settings/mobile', category: 'system', adminOnly: true },
];

function SettingsNav({ className }: { className?: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuthStore();
  const { t } = useI18n();
  const isAdmin = user?.role === 'admin';
  
  const filteredSections = sections.filter(s => !s.adminOnly || isAdmin);
  const personalSections = filteredSections.filter(s => s.category === 'personal');
  const orgSections = filteredSections.filter(s => s.category === 'organization');
  const systemSections = filteredSections.filter(s => s.category === 'system');

  const NavSection = ({ titleKey, items }: { titleKey: string; items: SettingsSection[] }) => (
    <div className="mb-6">
      <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        {t(titleKey)}
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
                'w-full flex items-center gap-3 px-3 py-2 text-sm rounded-none transition-none',
                isActive 
                  ? 'bg-rams-panel text-foreground border-l-2 border-l-rams-orange' 
                  : 'hover:bg-rams-panel/50 text-muted-foreground hover:text-foreground'
              )}
            >
              <Icon className="h-4 w-4" />
              {t(section.labelKey)}
            </button>
          );
        })}
      </div>
    </div>
  );

  return (
    <nav className={className}>
      <NavSection titleKey="pages.settings.sections.personal" items={personalSections} />
      <NavSection titleKey="pages.settings.sections.organizational" items={orgSections} />
      <NavSection titleKey="pages.settings.sections.system" items={systemSections} />
    </nav>
  );
}

function SettingsCard({ section }: { section: SettingsSection }) {
  const router = useRouter();
  const { t } = useI18n();
  const Icon = section.icon;
  
  return (
    <Card 
      className="group cursor-pointer rounded-rams-sm border border-rams-line bg-rams-module hover:border-rams-orange/40 transition-none"
      onClick={() => router.push(section.href)}
    >
      <CardContent className="p-6 flex items-center gap-6">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-none bg-rams-panel border border-rams-line text-muted-foreground/40 transition-none group-hover:border-rams-orange group-hover:text-rams-orange">
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 group-hover:text-rams-orange transition-none">{t(section.labelKey)}</h3>
          <p className="text-[10px] text-muted-foreground/60 line-clamp-1 font-medium mt-1 uppercase tracking-tight">{t(section.descriptionKey)}</p>
        </div>
        <ChevronRight className="h-4 w-4 text-muted-foreground/20 group-hover:text-rams-orange group-hover:translate-x-0.5 transition-all" />
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const { t } = useI18n();
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';
  
  const filteredSections = sections.filter(s => !s.adminOnly || isAdmin);
  const personalSections = filteredSections.filter(s => s.category === 'personal');
  const orgSections = filteredSections.filter(s => s.category === 'organization');
  const systemSections = filteredSections.filter(s => s.category === 'system');

  return (
    <div className="space-y-10 page-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between border-b border-rams-line pb-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90 flex items-center gap-3">
            <Settings className="h-6 w-6 text-rams-orange" />
            {t('pages.settings.title')}
          </h1>
          <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em] flex items-center gap-2">
            <span>{t('pages.settings.subtitle')}</span>
            <span className="opacity-30">|</span>
            <span>{t('pages.settings.station')}</span>
          </p>
        </div>
      </div>

      <div className="space-y-16">
        <section>
          <h2 className="text-[9px] font-black uppercase tracking-[0.3em] text-muted-foreground/30 mb-6 flex items-center gap-4">
            <div className="h-1.5 w-1.5 bg-rams-orange" />
            {t('pages.settings.sections.personal')}
            <div className="h-px flex-1 bg-rams-line/30" />
          </h2>
          <div className="grid gap-1 md:grid-cols-2 lg:grid-cols-3">
            {personalSections.map((section) => (
              <SettingsCard key={section.id} section={section} />
            ))}
          </div>
        </section>
        
        {orgSections.length > 0 && (
          <section>
            <h2 className="text-[9px] font-black uppercase tracking-[0.3em] text-muted-foreground/30 mb-6 flex items-center gap-4">
              <div className="h-1.5 w-1.5 bg-rams-orange" />
              {t('pages.settings.sections.organizational')}
              <div className="h-px flex-1 bg-rams-line/30" />
            </h2>
            <div className="grid gap-1 md:grid-cols-2 lg:grid-cols-3">
              {orgSections.map((section) => (
                <SettingsCard key={section.id} section={section} />
              ))}
            </div>
          </section>
        )}
        
        {systemSections.length > 0 && (
          <section>
            <h2 className="text-[9px] font-black uppercase tracking-[0.3em] text-muted-foreground/30 mb-6 flex items-center gap-4">
              <div className="h-1.5 w-1.5 bg-rams-orange" />
              {t('pages.settings.sections.system')}
              <div className="h-px flex-1 bg-rams-line/30" />
            </h2>
            <div className="grid gap-1 md:grid-cols-2 lg:grid-cols-3">
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
