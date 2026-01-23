'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import { 
  User, 
  Settings, 
  Shield, 
  Bell, 
  Globe, 
  Building2, 
  Users, 
  Key, 
  Link2, 
  Database, 
  Mail, 
  Smartphone,
  Palette
} from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { useAuthStore } from '@/stores';
import { useI18n } from '@/contexts/i18n-context';

interface SettingsLayoutProps {
  children: React.ReactNode;
}

const sections = [
  // Personal
  { id: 'profile', labelKey: 'settings.profile.title', icon: User, href: '/settings/profile', category: 'personal', adminOnly: false },
  { id: 'account', labelKey: 'settings.account.title', icon: Settings, href: '/settings/account', category: 'personal', adminOnly: false },
  { id: 'appearance', labelKey: 'settings.appearance.title', icon: Palette, href: '/settings/appearance', category: 'personal', adminOnly: false },
  { id: 'security', labelKey: 'settings.security.title', icon: Shield, href: '/settings/security', category: 'personal', adminOnly: false },
  { id: 'notifications', labelKey: 'settings.notifications.title', icon: Bell, href: '/settings/notifications', category: 'personal', adminOnly: false },
  { id: 'language', labelKey: 'settings.localization.title', icon: Globe, href: '/settings/language', category: 'personal', adminOnly: false },
  
  // Organization (admin only)
  { id: 'company', labelKey: 'pages.settings.company.title', icon: Building2, href: '/settings/company', category: 'organization', adminOnly: true },
  { id: 'team', labelKey: 'pages.settings.team.title', icon: Users, href: '/settings/team', category: 'organization', adminOnly: true },
  { id: 'api', labelKey: 'pages.settings.api.title', icon: Key, href: '/settings/api', category: 'organization', adminOnly: true },
  { id: 'integrations', labelKey: 'pages.settings.integrations.title', icon: Link2, href: '/settings/integrations', category: 'organization', adminOnly: true },
  
  // System (admin only)
  { id: 'data', labelKey: 'pages.settings.data.title', icon: Database, href: '/settings/data', category: 'system', adminOnly: true },
  { id: 'email', labelKey: 'pages.settings.email.title', icon: Mail, href: '/settings/email', category: 'system', adminOnly: true },
  { id: 'mobile', labelKey: 'pages.settings.mobile.title', icon: Smartphone, href: '/settings/mobile', category: 'system', adminOnly: true },
];

export default function SettingsLayout({ children }: SettingsLayoutProps) {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const { t } = useI18n();
  const isAdmin = user?.role === 'admin' || user?.role === 'ceo' || user?.roles?.includes('admin') || user?.roles?.includes('ceo');

  // If we are on the main settings page, we might want a different layout or just show the cards.
  // But for sub-pages, we definitely want the sidebar.
  if (pathname === '/settings') {
    return <>{children}</>;
  }

  // Filter sections based on admin status
  const filteredSections = sections.filter(s => !s.adminOnly || isAdmin);
  const personalSections = filteredSections.filter(s => s.category === 'personal');
  const orgSections = filteredSections.filter(s => s.category === 'organization');
  const systemSections = filteredSections.filter(s => s.category === 'system');

  const NavSection = ({ titleKey, items }: { titleKey: string; items: typeof sections }) => {
    if (items.length === 0) return null;
    
    return (
      <div className="mb-8">
        <h3 className="px-4 mb-3 text-[10px] font-black text-muted-foreground/40 uppercase tracking-[0.25em]">
          {t(titleKey)}
        </h3>
        <div className="space-y-0.5">
          {items.map((section) => {
            const Icon = section.icon;
            const isActive = pathname === section.href;
            return (
              <Link
                key={section.id}
                href={section.href}
                className={cn(
                  'flex items-center gap-3 px-4 py-2 text-[11px] font-bold uppercase tracking-wider rounded-rams-sm transition-none group border border-transparent',
                  isActive 
                    ? 'bg-rams-panel text-foreground border-rams-line shadow-[inset_2px_0_0_0_#FFBE00]' 
                    : 'text-muted-foreground/60 hover:bg-rams-panel/50 hover:text-foreground'
                )}
              >
                <Icon className={cn("h-3.5 w-3.5 shrink-0 transition-none", isActive ? "text-rams-orange" : "text-muted-foreground/40 group-hover:text-foreground")} />
                <span className="truncate">{t(section.labelKey)}</span>
              </Link>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col lg:flex-row gap-12 page-fade-in pb-12">
      <aside className="w-full lg:w-64 shrink-0 hidden lg:block">
        <div className="sticky top-8 bg-rams-module border border-rams-line rounded-rams-sm p-4">
          <NavSection titleKey="pages.settings.sections.personal" items={personalSections} />
          {orgSections.length > 0 && <NavSection titleKey="pages.settings.sections.organizational" items={orgSections} />}
          {systemSections.length > 0 && <NavSection titleKey="pages.settings.sections.system" items={systemSections} />}
        </div>
      </aside>
      <main className="flex-1 max-w-4xl">
        <div className="bg-rams-module border border-rams-line rounded-rams-sm p-8 min-h-[600px] relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-rams-orange/10" />
          {children}
          <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
        </div>
      </main>
    </div>
  );
}
