'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Sun,
  Moon,
  Monitor,
  Palette,
  Type,
  Layout,
  Save,
  Loader2,
  Check,
  Shield,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';
import { useUIStore } from '@/stores';
import { useToast } from '@/hooks/use-toast';

type ThemeMode = 'light' | 'dark' | 'system';
type AccentColor = 'orange' | 'blue' | 'green' | 'purple' | 'red';
type FontSize = 'small' | 'medium' | 'large';
type DensityMode = 'comfortable' | 'compact';

const APPEARANCE_STORAGE_KEY = 'sensei-appearance';

interface AppearanceSettings {
  accentColor: AccentColor;
  fontSize: FontSize;
  density: DensityMode;
  reducedMotion: boolean;
}

const defaultAppearanceSettings: AppearanceSettings = {
  accentColor: 'orange',
  fontSize: 'medium',
  density: 'comfortable',
  reducedMotion: false,
};

const themeOptions = [
  { value: 'light', labelKey: 'settings.appearance.lightMode', label: 'Light', icon: Sun, descriptionKey: 'settings.appearance.lightModeDesc', description: 'Light background with dark text' },
  { value: 'dark', labelKey: 'settings.appearance.darkMode', label: 'Dark', icon: Moon, descriptionKey: 'settings.appearance.darkModeDesc', description: 'Dark background with light text' },
  { value: 'system', labelKey: 'settings.appearance.systemDefault', label: 'System', icon: Monitor, descriptionKey: 'settings.appearance.systemDefaultDesc', description: 'Follow your system preferences' },
];

const accentColors: { value: AccentColor; labelKey: string; label: string; color: string; hsl: string; hex: string }[] = [
  { value: 'orange', labelKey: 'settings.appearance.senseiOrange', label: 'Sensei Orange', color: 'bg-[#FFBE00]', hsl: '43 100% 50%', hex: '#FFBE00' },
  { value: 'blue', labelKey: 'common.blue', label: 'Blue', color: 'bg-blue-500', hsl: '217 91% 60%', hex: '#3B82F6' },
  { value: 'green', labelKey: 'common.green', label: 'Green', color: 'bg-green-500', hsl: '142 71% 45%', hex: '#22C55E' },
  { value: 'purple', labelKey: 'common.purple', label: 'Purple', color: 'bg-purple-500', hsl: '262 83% 58%', hex: '#8B5CF6' },
  { value: 'red', labelKey: 'common.red', label: 'Red', color: 'bg-red-500', hsl: '0 84% 60%', hex: '#EF4444' },
];

const fontSizeOptions = [
  { value: 'small', labelKey: 'settings.appearance.fontSizeSmall', label: 'Small', descriptionKey: 'settings.appearance.fontSizeSmallDesc', description: '14px base', scale: '0.875' },
  { value: 'medium', labelKey: 'settings.appearance.fontSizeMedium', label: 'Medium', descriptionKey: 'settings.appearance.fontSizeMediumDesc', description: '16px base (default)', scale: '1' },
  { value: 'large', labelKey: 'settings.appearance.fontSizeLarge', label: 'Large', descriptionKey: 'settings.appearance.fontSizeLargeDesc', description: '18px base', scale: '1.125' },
];

const densityOptions = [
  { value: 'comfortable', labelKey: 'settings.appearance.comfortable', label: 'Comfortable', descriptionKey: 'settings.appearance.comfortableDesc', description: 'More spacing for easier reading' },
  { value: 'compact', labelKey: 'settings.appearance.compact', label: 'Compact', descriptionKey: 'settings.appearance.compactDesc', description: 'More content on screen' },
];

function getStoredAppearance(): AppearanceSettings {
  if (typeof window === 'undefined') return defaultAppearanceSettings;
  try {
    const stored = localStorage.getItem(APPEARANCE_STORAGE_KEY);
    if (stored) return { ...defaultAppearanceSettings, ...JSON.parse(stored) };
  } catch (e) { /* ignore */ }
  return defaultAppearanceSettings;
}

function saveAppearance(settings: AppearanceSettings): void {
  if (typeof window === 'undefined') return;
  try { localStorage.setItem(APPEARANCE_STORAGE_KEY, JSON.stringify(settings)); } catch (e) { /* ignore */ }
}

function applyAccentColor(color: AccentColor): void {
  const root = document.documentElement;
  const colorConfig = accentColors.find(c => c.value === color);
  if (colorConfig) {
    // Apply to --accent CSS variable
    root.style.setProperty('--accent', colorConfig.hsl);
    root.style.setProperty('--accent-foreground', color === 'orange' ? '0 0% 0%' : '0 0% 100%');
    // Also update primary to match accent for consistency
    root.style.setProperty('--primary', colorConfig.hsl);
    root.style.setProperty('--primary-foreground', color === 'orange' ? '0 0% 0%' : '0 0% 100%');
    // Update ring color to match
    root.style.setProperty('--ring', colorConfig.hsl);
    // Update rams-accent dynamically via custom property
    root.style.setProperty('--rams-accent', colorConfig.hex);
    root.dataset.accent = color;
  }
}

function applyFontSize(size: FontSize): void {
  const root = document.documentElement;
  root.style.fontSize = size === 'small' ? '14px' : size === 'large' ? '18px' : '16px';
  root.dataset.fontSize = size;
}

function applyDensity(density: DensityMode): void {
  const root = document.documentElement;
  root.classList.remove('density-comfortable', 'density-compact');
  root.classList.add(`density-${density}`);
  root.dataset.density = density;
}

function applyReducedMotion(reduced: boolean): void {
  const root = document.documentElement;
  if (reduced) root.classList.add('reduce-motion');
  else root.classList.remove('reduce-motion');
}

export default function AppearanceSettingsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { toast } = useToast();
  const { theme, setTheme, sidebarState, setSidebarState, compactMode, setCompactMode } = useUIStore();
  const [isSaving, setIsSaving] = React.useState(false);
  const [appearance, setAppearance] = React.useState<AppearanceSettings>(defaultAppearanceSettings);
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
    const stored = getStoredAppearance();
    setAppearance(stored);
    applyAccentColor(stored.accentColor);
    applyFontSize(stored.fontSize);
    applyDensity(stored.density);
    applyReducedMotion(stored.reducedMotion);
  }, []);

  const handleThemeChange = (newTheme: ThemeMode) => setTheme(newTheme);

  const handleAppearanceChange = <K extends keyof AppearanceSettings>(key: K, value: AppearanceSettings[K]) => {
    const newSettings = { ...appearance, [key]: value };
    setAppearance(newSettings);
    switch (key) {
      case 'accentColor': applyAccentColor(value as AccentColor); break;
      case 'fontSize': applyFontSize(value as FontSize); break;
      case 'density': applyDensity(value as DensityMode); setCompactMode(value === 'compact'); break;
      case 'reducedMotion': applyReducedMotion(value as boolean); break;
    }
    saveAppearance(newSettings);
  };

  const handleSidebarToggle = (collapsed: boolean) => setSidebarState(collapsed ? 'collapsed' : 'expanded');

  const handleSave = async () => {
    setIsSaving(true);
    saveAppearance(appearance);
    await new Promise(resolve => setTimeout(resolve, 500));
    setIsSaving(false);
    toast({ title: t('common.success'), description: t('settings.appearance.saveSuccess') });
  };

  if (!mounted) return <div className="flex items-center justify-center h-[400px]"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-150">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between border-b border-rams-line pb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-rams-sm hover:bg-rams-panel transition-none" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-2xl font-sans font-black uppercase tracking-tight opacity-90">{t('settings.appearance.title')}</h1>
            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-[0.2em]">{t('settings.appearance.subtitle')}</p>
          </div>
        </div>
        <Button onClick={handleSave} disabled={isSaving} className="rounded-rams-sm bg-rams-orange text-black font-black uppercase tracking-widest text-[10px] h-10 px-8 transition-none" size="default">
          {isSaving ? <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />{t('settings.appearance.saving')}</> : <><Save className="mr-2 h-3.5 w-3.5" />{t('settings.appearance.save')}</>}
        </Button>
      </div>

      <div className="space-y-12">
        <section className="space-y-6">
          <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70 flex items-center gap-3">
            <Sun className="h-3.5 w-3.5 text-rams-orange" />{t('settings.appearance.themeMode')}
          </h3>
          <div className="grid gap-1 sm:grid-cols-3">
            {themeOptions.map((option) => {
              const Icon = option.icon;
              const isSelected = theme === option.value;
              return (
                <button key={option.value} onClick={() => handleThemeChange(option.value as ThemeMode)}
                  className={cn('relative flex flex-col items-center gap-4 p-6 rounded-none border border-rams-line bg-rams-module transition-none group',
                    isSelected ? 'border-rams-orange bg-rams-panel/50 shadow-[inset_0_2px_0_0_#FFBE00]' : 'hover:bg-rams-panel/30 hover:border-rams-line')}>
                  <div className={cn('p-4 rounded-none transition-none border border-rams-line', option.value === 'dark' ? 'bg-rams-chassis' : 'bg-white')}>
                    <Icon className={cn('h-6 w-6', option.value === 'dark' ? 'text-foreground' : 'text-slate-900')} />
                  </div>
                  <div className="text-center">
                    <p className="font-sans font-black text-xs uppercase tracking-tight">{t(option.labelKey)}</p>
                    <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">{t(option.descriptionKey)}</p>
                  </div>
                  {isSelected && <div className="absolute top-2 right-2"><Check className="h-4 w-4 text-rams-orange" /></div>}
                </button>
              );
            })}
          </div>
        </section>

        <section className="space-y-6">
          <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70 flex items-center gap-3">
            <Palette className="h-3.5 w-3.5 text-rams-orange" />{t('settings.appearance.accentColor')}
          </h3>
          <div className="flex flex-wrap gap-1">
            {accentColors.map((color) => {
              const isSelected = appearance.accentColor === color.value;
              return (
                <button key={color.value} onClick={() => handleAppearanceChange('accentColor', color.value)} title={t(color.labelKey)}
                  className={cn('relative flex flex-col items-center gap-2 p-4 rounded-none border border-rams-line bg-rams-module transition-none group',
                    isSelected ? 'border-rams-orange bg-rams-panel shadow-[inset_0_2px_0_0_#FFBE00]' : 'hover:bg-rams-panel/30')}>
                  <div className={cn('w-8 h-8 rounded-none border border-black/10 shadow-none transition-none', color.color)}>
                    {isSelected && <div className="flex items-center justify-center h-full"><Check className="h-4 w-4 text-white" /></div>}
                  </div>
                  <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/60">{t(color.labelKey)}</span>
                </button>
              );
            })}
          </div>
        </section>

        <div className="grid gap-12 lg:grid-cols-2">
          <section className="space-y-6">
            <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70 flex items-center gap-3">
              <Type className="h-3.5 w-3.5 text-rams-orange" />{t('settings.appearance.fontSize')}
            </h3>
            <div className="space-y-1">
              {fontSizeOptions.map((option) => {
                const isSelected = appearance.fontSize === option.value;
                return (
                  <button key={option.value} onClick={() => handleAppearanceChange('fontSize', option.value as FontSize)}
                    className={cn('w-full flex items-center justify-between p-4 rounded-none border border-rams-line bg-rams-module transition-none',
                      isSelected ? 'border-rams-orange bg-rams-panel/50 shadow-[inset_2px_0_0_0_#FFBE00]' : 'hover:bg-rams-panel/30 hover:border-rams-line')}>
                    <div className="text-left">
                      <p className={cn('font-sans font-black uppercase tracking-tight text-foreground/80',
                        option.value === 'small' && 'text-xs', option.value === 'medium' && 'text-sm', option.value === 'large' && 'text-base')}>{t(option.labelKey)}</p>
                      <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40">{t(option.descriptionKey).toUpperCase()}</p>
                    </div>
                    {isSelected && <div className="p-1.5 bg-rams-orange text-black rounded-none border border-black/10"><Check className="h-3 w-3" /></div>}
                  </button>
                );
              })}
            </div>
          </section>

          <section className="space-y-6">
            <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70 flex items-center gap-3">
              <Layout className="h-3.5 w-3.5 text-rams-orange" />{t('settings.appearance.density')}
            </h3>
            <div className="space-y-1">
              {densityOptions.map((option) => {
                const isSelected = appearance.density === option.value;
                return (
                  <button key={option.value} onClick={() => handleAppearanceChange('density', option.value as DensityMode)}
                    className={cn('w-full flex items-center justify-between p-4 rounded-none border border-rams-line bg-rams-module transition-none',
                      isSelected ? 'border-rams-orange bg-rams-panel/50 shadow-[inset_2px_0_0_0_#FFBE00]' : 'hover:bg-rams-panel/30 hover:border-rams-line')}>
                    <div className="text-left">
                      <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80">{t(option.labelKey)}</p>
                      <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40">{t(option.descriptionKey).toUpperCase()}</p>
                    </div>
                    {isSelected && <div className="p-1.5 bg-rams-orange text-black rounded-none border border-black/10"><Check className="h-3 w-3" /></div>}
                  </button>
                );
              })}
            </div>
          </section>
        </div>

        <section className="space-y-1">
          <div className="flex items-center justify-between p-5 rounded-none bg-rams-panel/20 border border-rams-line group">
            <div>
              <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 transition-none group-hover:text-rams-orange">{t('settings.appearance.compactNavigation')}</p>
              <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">{t('settings.appearance.compactNavigationDesc')}</p>
            </div>
            <Switch checked={sidebarState === 'collapsed'} onCheckedChange={handleSidebarToggle} />
          </div>
          <div className="flex items-center justify-between p-5 rounded-none bg-rams-panel/20 border border-rams-line group">
            <div>
              <p className="font-sans font-black text-xs uppercase tracking-tight text-foreground/80 transition-none group-hover:text-rams-orange">{t('settings.appearance.reducedMotion')}</p>
              <p className="text-[9px] uppercase tracking-widest font-bold text-muted-foreground/40 mt-1">{t('settings.appearance.reducedMotionDesc')}</p>
            </div>
            <Switch checked={appearance.reducedMotion} onCheckedChange={(v) => handleAppearanceChange('reducedMotion', v)} />
          </div>
        </section>

        <section className="space-y-6">
          <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-foreground/70 flex items-center gap-3">
            <Shield className="h-3.5 w-3.5 text-rams-orange" />{t('settings.appearance.livePreview')}
          </h3>
          <div className="border border-rams-line rounded-none p-8 bg-rams-chassis overflow-hidden relative group">
            <div className="absolute top-0 right-0 p-4 opacity-5">
              <Shield className="h-24 w-24 text-foreground" />
            </div>
            <div className="flex items-center gap-6 mb-10 relative z-10">
              <div className={cn('w-12 h-12 rounded-none border border-black/10 shadow-none transition-none', accentColors.find(c => c.value === appearance.accentColor)?.color)} />
              <div>
                <p className={cn('font-sans font-black uppercase tracking-tight text-foreground/90',
                  appearance.fontSize === 'small' && 'text-sm', appearance.fontSize === 'medium' && 'text-xl', appearance.fontSize === 'large' && 'text-2xl')}>
                  {t('settings.appearance.preview.title')}
                </p>
                <p className="text-[9px] font-mono font-black uppercase tracking-[0.3em] text-muted-foreground/40 mt-1">{t('settings.appearance.preview.subtitle')}</p>
              </div>
            </div>
            <div className="grid gap-1 sm:grid-cols-3 relative z-10">
              <Button className="rounded-none bg-rams-orange text-black font-black uppercase tracking-widest text-[9px] h-10 border border-black/10 transition-none" size="sm">{t('settings.appearance.preview.primaryAction')}</Button>
              <Button variant="outline" className="rounded-none border-rams-line bg-rams-module text-foreground/70 font-black uppercase tracking-widest text-[9px] h-10 transition-none" size="sm">{t('settings.appearance.preview.secondaryAction')}</Button>
              <Button variant="ghost" className="rounded-none hover:bg-rams-panel text-muted-foreground/40 font-black uppercase tracking-widest text-[9px] h-10 transition-none" size="sm">{t('settings.appearance.preview.tertiaryAction')}</Button>
            </div>
            <div className="absolute inset-0 perforated-bg opacity-5 pointer-events-none" />
          </div>
        </section>
      </div>
    </div>
  );
}
