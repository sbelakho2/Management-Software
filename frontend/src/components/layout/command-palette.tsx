'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  Search,
  Plus,
  LogOut,
  User,
  Moon,
  Sun,
  type LucideIcon,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { useUIStore, useAuthStore } from '@/stores';
import { hasPageAccess } from '@/lib/page-access';
import { NAV_SECTIONS, QUICK_ACTIONS } from '@/lib/navigation';
import { UserRole } from '@/types';
import { useI18n } from '@/contexts/i18n-context';

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon?: LucideIcon;
  shortcut?: string;
  action: () => void;
  keywords?: string[];
  group: string;
}

export function CommandPalette() {
  const router = useRouter();
  const { commandPaletteOpen, setCommandPaletteOpen, theme, setTheme } = useUIStore();
  const { user, logout } = useAuthStore();
  const { t, isRTL } = useI18n();
  const [search, setSearch] = React.useState('');
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const listboxId = React.useId();

  const userRoles = React.useMemo(() => {
    if (!user) return [] as UserRole[];
    return user.roles && user.roles.length > 0 ? user.roles : [user.role as UserRole];
  }, [user]);

  const commands: CommandItem[] = React.useMemo(() => {
    const allCommands: CommandItem[] = [];

    // Add Navigation commands from NAV_SECTIONS
    NAV_SECTIONS.forEach(section => {
      section.items.forEach(item => {
        if (hasPageAccess(item.href, userRoles)) {
          allCommands.push({
            id: `nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`,
            label: item.label,
            icon: item.icon,
            action: () => router.push(item.href),
            keywords: item.keywords,
            group: t('navigation.menu')
          });
        }
      });
    });

    // Add Quick Actions
    QUICK_ACTIONS.forEach(action => {
      if (hasPageAccess(action.href, userRoles)) {
        allCommands.push({
          id: action.id,
          label: action.label,
          icon: action.icon,
          action: () => router.push(action.href),
          keywords: action.keywords,
          group: t('common.actions')
        });
      }
    });

    // Add common commands
    allCommands.push({ 
      id: 'theme-toggle', 
      label: theme === 'dark' ? t('settings.appearance.lightMode') : t('settings.appearance.darkMode'), 
      icon: theme === 'dark' ? Sun : Moon, 
      action: () => setTheme(theme === 'dark' ? 'light' : 'dark'), 
      keywords: ['theme', 'dark', 'light', 'mode'], 
      group: t('settings.preferences')
    });

    if (hasPageAccess('/settings/profile', userRoles)) {
      allCommands.push({
        id: 'account-profile',
        label: t('userMenu.profile'),
        icon: User,
        action: () => router.push('/settings/profile'),
        keywords: ['profile', 'account'],
        group: t('settings.account'),
      });
    }

    allCommands.push({
      id: 'account-logout',
      label: t('auth.logout'),
      icon: LogOut,
      action: async () => { await logout(); router.push('/login'); },
      keywords: ['logout', 'sign out'],
      group: t('settings.account'),
    });

    return allCommands;
  }, [router, theme, setTheme, logout, userRoles, t]);

  const filteredCommands = React.useMemo(() => {
    if (!search.trim()) return commands;
    
    const searchLower = search.toLowerCase();
    return commands.filter((cmd) => {
      const labelMatch = cmd.label.toLowerCase().includes(searchLower);
      const descMatch = cmd.description?.toLowerCase().includes(searchLower);
      const keywordMatch = cmd.keywords?.some((kw) => kw.includes(searchLower));
      return labelMatch || descMatch || keywordMatch;
    });
  }, [commands, search]);

  const groupedCommands = React.useMemo(() => {
    const groups: Record<string, CommandItem[]> = {};
    filteredCommands.forEach((cmd) => {
      if (!groups[cmd.group]) groups[cmd.group] = [];
      groups[cmd.group].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  const activeDescendantId = filteredCommands[selectedIndex]
    ? `${listboxId}-item-${selectedIndex}`
    : undefined;

  // Keyboard navigation
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!commandPaletteOpen) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((i) => Math.min(i + 1, filteredCommands.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((i) => Math.max(i - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action();
            setCommandPaletteOpen(false);
            setSearch('');
          }
          break;
        case 'Escape':
          e.preventDefault();
          setCommandPaletteOpen(false);
          setSearch('');
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [commandPaletteOpen, filteredCommands, selectedIndex, setCommandPaletteOpen]);

  // Reset selection when search changes
  React.useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  // Focus input when opened
  React.useEffect(() => {
    if (commandPaletteOpen) {
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [commandPaletteOpen]);

  // Global shortcut
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(!commandPaletteOpen);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [commandPaletteOpen, setCommandPaletteOpen]);

  let flatIndex = -1;

  return (
    <Dialog open={commandPaletteOpen} onOpenChange={(open) => {
      setCommandPaletteOpen(open);
      if (!open) setSearch('');
    }}>
      <DialogContent className="overflow-hidden p-0 shadow-lg max-w-2xl">
        <div className={cn("flex items-center border-b px-3", isRTL && "flex-row-reverse")}>
          <Search className={cn("h-4 w-4 shrink-0 opacity-50", isRTL ? "ml-2" : "mr-2")} />
          <Input
            ref={inputRef}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`${t('forms.typeToSearch')}`}
            className="flex h-12 w-full rounded-md bg-transparent py-3 text-sm outline-none border-0 focus-visible:ring-0 placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
            role="combobox"
            aria-autocomplete="list"
            aria-controls={listboxId}
            aria-expanded={commandPaletteOpen}
            aria-activedescendant={activeDescendantId}
          />
        </div>
        <div className="max-h-[400px] overflow-y-auto p-2" role="listbox" id={listboxId} aria-label={t('common.search')}>
          {filteredCommands.length === 0 ? (
            <p className="p-4 text-center text-sm text-muted-foreground">
              {t('common.noResults')}
            </p>
          ) : (
            Object.entries(groupedCommands).map(([group, items]) => (
              <div key={group} className="mb-4" role="presentation">
                <p className="px-2 py-1.5 text-xs font-medium text-muted-foreground" role="presentation">
                  {group}
                </p>
                {items.map((cmd) => {
                  flatIndex++;
                  const currentIndex = flatIndex;
                  const itemId = `${listboxId}-item-${currentIndex}`;
                  return (
                    <button
                      key={cmd.id}
                      onClick={() => {
                        cmd.action();
                        setCommandPaletteOpen(false);
                        setSearch('');
                      }}
                      id={itemId}
                      role="option"
                      aria-selected={currentIndex === selectedIndex}
                      className={cn(
                        'relative flex w-full cursor-default select-none items-center rounded-sm px-2 py-2 text-sm outline-none',
                        currentIndex === selectedIndex && 'bg-accent text-accent-foreground'
                      )}
                      onMouseEnter={() => setSelectedIndex(currentIndex)}
                    >
                      {cmd.icon && <cmd.icon className="mr-3 h-4 w-4 shrink-0 opacity-50" />}
                      <span className="flex-1 text-left">{cmd.label}</span>
                      {cmd.shortcut && (
                        <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                          {cmd.shortcut}
                        </kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
