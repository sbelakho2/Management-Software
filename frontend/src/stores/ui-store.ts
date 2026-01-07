import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';
type ViewMode = 'list' | 'kanban' | 'calendar';
type SidebarState = 'expanded' | 'collapsed' | 'hidden';

interface UIState {
  // Theme
  theme: Theme;
  resolvedTheme: 'light' | 'dark';
  
  // Sidebar
  sidebarState: SidebarState;
  sidebarWidth: number;
  
  // View preferences
  defaultViewMode: ViewMode;
  showCompletedTasks: boolean;
  showArchived: boolean;
  compactMode: boolean;
  
  // Modals & Dialogs
  activeModal: string | null;
  modalData: Record<string, unknown> | null;
  
  // Command Palette
  commandPaletteOpen: boolean;
  
  // Notifications
  notificationPanelOpen: boolean;
  unreadCount: number;
  
  // Search
  globalSearchOpen: boolean;
  recentSearches: string[];
  
  // Actions
  setTheme: (theme: Theme) => void;
  setSidebarState: (state: SidebarState) => void;
  setSidebarWidth: (width: number) => void;
  setDefaultViewMode: (mode: ViewMode) => void;
  setShowCompletedTasks: (show: boolean) => void;
  setShowArchived: (show: boolean) => void;
  setCompactMode: (compact: boolean) => void;
  openModal: (modalId: string, data?: Record<string, unknown>) => void;
  closeModal: () => void;
  toggleCommandPalette: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  toggleNotificationPanel: () => void;
  setUnreadCount: (count: number) => void;
  decrementUnreadCount: () => void;
  toggleGlobalSearch: () => void;
  setGlobalSearchOpen: (open: boolean) => void;
  addRecentSearch: (query: string) => void;
  clearRecentSearches: () => void;
}

function getResolvedTheme(theme: Theme): 'light' | 'dark' {
  if (theme === 'system') {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  }
  return theme;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      // Initial state
      theme: 'system',
      resolvedTheme: 'light',
      sidebarState: 'expanded',
      sidebarWidth: 256,
      defaultViewMode: 'list',
      showCompletedTasks: false,
      showArchived: false,
      compactMode: false,
      activeModal: null,
      modalData: null,
      commandPaletteOpen: false,
      notificationPanelOpen: false,
      unreadCount: 0,
      globalSearchOpen: false,
      recentSearches: [],

      // Actions
      setTheme: (theme) => {
        const resolvedTheme = getResolvedTheme(theme);
        set({ theme, resolvedTheme });
        
        // Apply to document
        if (typeof document !== 'undefined') {
          document.documentElement.classList.remove('light', 'dark');
          document.documentElement.classList.add(resolvedTheme);
        }
      },

      setSidebarState: (sidebarState) => set({ sidebarState }),
      
      setSidebarWidth: (sidebarWidth) => set({ sidebarWidth }),
      
      setDefaultViewMode: (defaultViewMode) => set({ defaultViewMode }),
      
      setShowCompletedTasks: (showCompletedTasks) => set({ showCompletedTasks }),
      
      setShowArchived: (showArchived) => set({ showArchived }),
      
      setCompactMode: (compactMode) => set({ compactMode }),
      
      openModal: (modalId, data) => set({ 
        activeModal: modalId, 
        modalData: data || null 
      }),
      
      closeModal: () => set({ 
        activeModal: null, 
        modalData: null 
      }),
      
      toggleCommandPalette: () => set((state) => ({ 
        commandPaletteOpen: !state.commandPaletteOpen 
      })),
      
      setCommandPaletteOpen: (commandPaletteOpen) => set({ commandPaletteOpen }),
      
      toggleNotificationPanel: () => set((state) => ({ 
        notificationPanelOpen: !state.notificationPanelOpen 
      })),
      
      setUnreadCount: (unreadCount) => set({ unreadCount }),
      
      decrementUnreadCount: () => set((state) => ({ 
        unreadCount: Math.max(0, state.unreadCount - 1) 
      })),
      
      toggleGlobalSearch: () => set((state) => ({ 
        globalSearchOpen: !state.globalSearchOpen 
      })),
      
      setGlobalSearchOpen: (globalSearchOpen) => set({ globalSearchOpen }),
      
      addRecentSearch: (query) => {
        const { recentSearches } = get();
        const filtered = recentSearches.filter((s) => s !== query);
        const updated = [query, ...filtered].slice(0, 10);
        set({ recentSearches: updated });
      },
      
      clearRecentSearches: () => set({ recentSearches: [] }),
    }),
    {
      name: 'ui-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        theme: state.theme,
        sidebarState: state.sidebarState,
        sidebarWidth: state.sidebarWidth,
        defaultViewMode: state.defaultViewMode,
        showCompletedTasks: state.showCompletedTasks,
        showArchived: state.showArchived,
        compactMode: state.compactMode,
        recentSearches: state.recentSearches,
      }),
      onRehydrateStorage: () => (state) => {
        // Apply theme on rehydration
        if (state?.theme) {
          const resolvedTheme = getResolvedTheme(state.theme);
          state.resolvedTheme = resolvedTheme;
          
          if (typeof document !== 'undefined') {
            document.documentElement.classList.remove('light', 'dark');
            document.documentElement.classList.add(resolvedTheme);
          }
        }
      },
    }
  )
);

// Listen for system theme changes
if (typeof window !== 'undefined') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    const { theme, setTheme } = useUIStore.getState();
    if (theme === 'system') {
      // Re-trigger to update resolved theme
      setTheme('system');
    }
  });
}
