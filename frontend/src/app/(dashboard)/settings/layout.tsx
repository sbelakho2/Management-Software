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

interface SettingsLayoutProps {
  children: React.ReactNode;
}

const sections = [
  // Personal
  { id: 'profile', label: 'Profile', icon: User, href: '/settings/profile', category: 'personal', adminOnly: false },
  { id: 'account', label: 'Account', icon: Settings, href: '/settings/account', category: 'personal', adminOnly: false },
  { id: 'appearance', label: 'Appearance', icon: Palette, href: '/settings/appearance', category: 'personal', adminOnly: false },
  { id: 'security', label: 'Security', icon: Shield, href: '/settings/security', category: 'personal', adminOnly: false },
  { id: 'notifications', label: 'Notifications', icon: Bell, href: '/settings/notifications', category: 'personal', adminOnly: false },
  { id: 'language', label: 'Language', icon: Globe, href: '/settings/language', category: 'personal', adminOnly: false },
  
  // Organization (admin only)
  { id: 'company', label: 'Company', icon: Building2, href: '/settings/company', category: 'organization', adminOnly: true },
  { id: 'team', label: 'Team Members', icon: Users, href: '/settings/team', category: 'organization', adminOnly: true },
  { id: 'api', label: 'API Keys', icon: Key, href: '/settings/api', category: 'organization', adminOnly: true },
  { id: 'integrations', label: 'Integrations', icon: Link2, href: '/settings/integrations', category: 'organization', adminOnly: true },
  
  // System (admin only)
  { id: 'data', label: 'Data Management', icon: Database, href: '/settings/data', category: 'system', adminOnly: true },
  { id: 'email', label: 'Email Settings', icon: Mail, href: '/settings/email', category: 'system', adminOnly: true },
  { id: 'mobile', label: 'Mobile App', icon: Smartphone, href: '/settings/mobile', category: 'system', adminOnly: true },
];

export default function SettingsLayout({ children }: SettingsLayoutProps) {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';

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

  const NavSection = ({ title, items }: { title: string; items: typeof sections }) => {
    if (items.length === 0) return null;
    
    return (
      <div className="mb-8">
        <h3 className="px-4 mb-3 text-[10px] font-bold text-muted-foreground/50 uppercase tracking-[0.2em]">
          {title}
        </h3>
        <div className="space-y-1">
          {items.map((section) => {
            const Icon = section.icon;
            const isActive = pathname === section.href;
            return (
              <Link
                key={section.id}
                href={section.href}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5 text-sm rounded-xl transition-all duration-300 group',
                  isActive 
                    ? 'bg-primary text-primary-foreground shadow-glow font-semibold scale-[1.02]' 
                    : 'hover:bg-primary/5 text-muted-foreground hover:text-primary'
                )}
              >
                <Icon className={cn("h-4 w-4 shrink-0 transition-transform duration-300 group-hover:scale-110", isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-primary")} />
                <span className="truncate tracking-tight">{section.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col lg:flex-row gap-12 page-fade-in">
      <aside className="w-full lg:w-64 shrink-0 hidden lg:block">
        <div className="sticky top-24">
          <NavSection title="Personal" items={personalSections} />
          {orgSections.length > 0 && <NavSection title="Organization" items={orgSections} />}
          {systemSections.length > 0 && <NavSection title="System" items={systemSections} />}
        </div>
      </aside>
      <main className="flex-1 max-w-4xl">
        {children}
      </main>
    </div>
  );
}
