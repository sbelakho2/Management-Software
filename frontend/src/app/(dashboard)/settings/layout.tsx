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

interface SettingsLayoutProps {
  children: React.ReactNode;
}

const sections = [
  // Personal
  { id: 'profile', label: 'Profile', icon: User, href: '/settings/profile', category: 'personal' },
  { id: 'account', label: 'Account', icon: Settings, href: '/settings/account', category: 'personal' },
  { id: 'appearance', label: 'Appearance', icon: Palette, href: '/settings/appearance', category: 'personal' },
  { id: 'security', label: 'Security', icon: Shield, href: '/settings/security', category: 'personal' },
  { id: 'notifications', label: 'Notifications', icon: Bell, href: '/settings/notifications', category: 'personal' },
  { id: 'language', label: 'Language', icon: Globe, href: '/settings/language', category: 'personal' },
  
  // Organization
  { id: 'company', label: 'Company', icon: Building2, href: '/settings/company', category: 'organization' },
  { id: 'team', label: 'Team Members', icon: Users, href: '/settings/team', category: 'organization' },
  { id: 'api', label: 'API Keys', icon: Key, href: '/settings/api', category: 'organization' },
  { id: 'integrations', label: 'Integrations', icon: Link2, href: '/settings/integrations', category: 'organization' },
  
  // System
  { id: 'data', label: 'Data Management', icon: Database, href: '/settings/data', category: 'system' },
  { id: 'email', label: 'Email Settings', icon: Mail, href: '/settings/email', category: 'system' },
  { id: 'mobile', label: 'Mobile App', icon: Smartphone, href: '/settings/mobile', category: 'system' },
];

export default function SettingsLayout({ children }: SettingsLayoutProps) {
  const pathname = usePathname();

  // If we are on the main settings page, we might want a different layout or just show the cards.
  // But for sub-pages, we definitely want the sidebar.
  if (pathname === '/settings') {
    return <>{children}</>;
  }

  const NavSection = ({ title, items }: { title: string; items: typeof sections }) => (
    <div className="mb-6">
      <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
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
                'flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors',
                isActive 
                  ? 'bg-primary text-primary-foreground' 
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              )}
            >
              <Icon className="h-4 w-4" />
              {section.label}
            </Link>
          );
        })}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col lg:flex-row gap-8">
      <aside className="w-full lg:w-64 shrink-0 hidden lg:block">
        <NavSection title="Personal" items={sections.filter(s => s.category === 'personal')} />
        <NavSection title="Organization" items={sections.filter(s => s.category === 'organization')} />
        <NavSection title="System" items={sections.filter(s => s.category === 'system')} />
      </aside>
      <main className="flex-1">
        {children}
      </main>
    </div>
  );
}
