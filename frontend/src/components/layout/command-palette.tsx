'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  Home,
  FileText,
  Calculator,
  Users,
  Package,
  Factory,
  ClipboardCheck,
  AlertTriangle,
  LayoutGrid,
  GraduationCap,
  Settings,
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
  const { logout } = useAuthStore();
  const [search, setSearch] = React.useState('');
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const commands: CommandItem[] = React.useMemo(() => [
    // Navigation
    { id: 'nav-today', label: 'Go to Today', icon: Home, action: () => router.push('/today'), keywords: ['home', 'dashboard'], group: 'Navigation' },
    { id: 'nav-pipeline', label: 'Go to Pipeline', icon: FileText, action: () => router.push('/pipeline'), keywords: ['rfq', 'request'], group: 'Navigation' },
    { id: 'nav-quotes', label: 'Go to Quotes', icon: Calculator, action: () => router.push('/quotes'), keywords: ['quote', 'pricing'], group: 'Navigation' },
    { id: 'nav-customers', label: 'Go to Customers', icon: Users, action: () => router.push('/customers'), keywords: ['customer', 'client'], group: 'Navigation' },
    { id: 'nav-products', label: 'Go to Products', icon: Package, action: () => router.push('/products'), keywords: ['product', 'item'], group: 'Navigation' },
    { id: 'nav-production', label: 'Go to Production', icon: Factory, action: () => router.push('/production'), keywords: ['manufacturing', 'work order'], group: 'Navigation' },
    { id: 'nav-quality', label: 'Go to Quality', icon: ClipboardCheck, action: () => router.push('/quality'), keywords: ['quality', 'inspection', 'ncr'], group: 'Navigation' },
    { id: 'nav-andon', label: 'Go to Andon', icon: AlertTriangle, action: () => router.push('/andon'), keywords: ['andon', 'alert'], group: 'Navigation' },
    { id: 'nav-obeya', label: 'Go to Obeya', icon: LayoutGrid, action: () => router.push('/obeya'), keywords: ['obeya', 'board', 'visual'], group: 'Navigation' },
    { id: 'nav-training', label: 'Go to Training', icon: GraduationCap, action: () => router.push('/training'), keywords: ['training', 'learning'], group: 'Navigation' },
    { id: 'nav-settings', label: 'Go to Settings', icon: Settings, action: () => router.push('/settings'), keywords: ['settings', 'preferences'], group: 'Navigation' },

    // Actions
    { id: 'action-new-rfq', label: 'Create New RFQ', icon: Plus, action: () => router.push('/pipeline/new'), keywords: ['create', 'new', 'rfq'], group: 'Actions' },
    { id: 'action-new-quote', label: 'Create New Quote', icon: Plus, action: () => router.push('/quotes/new'), keywords: ['create', 'new', 'quote'], group: 'Actions' },
    { id: 'action-new-customer', label: 'Create New Customer', icon: Plus, action: () => router.push('/customers/new'), keywords: ['create', 'new', 'customer'], group: 'Actions' },
    { id: 'action-new-task', label: 'Create New Task', icon: Plus, action: () => router.push('/tasks/new'), keywords: ['create', 'new', 'task'], group: 'Actions' },

    // Theme
    { 
      id: 'theme-toggle', 
      label: theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode', 
      icon: theme === 'dark' ? Sun : Moon, 
      action: () => setTheme(theme === 'dark' ? 'light' : 'dark'), 
      keywords: ['theme', 'dark', 'light', 'mode'], 
      group: 'Preferences' 
    },

    // Account
    { id: 'account-profile', label: 'View Profile', icon: User, action: () => router.push('/settings/profile'), keywords: ['profile', 'account'], group: 'Account' },
    { id: 'account-logout', label: 'Log Out', icon: LogOut, action: async () => { await logout(); router.push('/login'); }, keywords: ['logout', 'sign out'], group: 'Account' },
  ], [router, theme, setTheme, logout]);

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
        <div className="flex items-center border-b px-3">
          <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
          <Input
            ref={inputRef}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Type a command or search..."
            className="flex h-12 w-full rounded-md bg-transparent py-3 text-sm outline-none border-0 focus-visible:ring-0 placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
        <div className="max-h-[400px] overflow-y-auto p-2">
          {filteredCommands.length === 0 ? (
            <p className="p-4 text-center text-sm text-muted-foreground">
              No results found.
            </p>
          ) : (
            Object.entries(groupedCommands).map(([group, items]) => (
              <div key={group} className="mb-4">
                <p className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                  {group}
                </p>
                {items.map((cmd) => {
                  flatIndex++;
                  const currentIndex = flatIndex;
                  return (
                    <button
                      key={cmd.id}
                      onClick={() => {
                        cmd.action();
                        setCommandPaletteOpen(false);
                        setSearch('');
                      }}
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
