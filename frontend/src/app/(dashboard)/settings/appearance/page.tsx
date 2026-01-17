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
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import { useI18n } from '@/contexts/i18n-context';

type ThemeMode = 'light' | 'dark' | 'system';
type AccentColor = 'blue' | 'green' | 'purple' | 'orange' | 'red';
type FontSize = 'small' | 'medium' | 'large';
type DensityMode = 'comfortable' | 'compact';

interface AppearanceSettings {
  theme: ThemeMode;
  accentColor: AccentColor;
  fontSize: FontSize;
  density: DensityMode;
  reducedMotion: boolean;
  sidebarCollapsed: boolean;
}

const defaultSettings: AppearanceSettings = {
  theme: 'system',
  accentColor: 'blue',
  fontSize: 'medium',
  density: 'comfortable',
  reducedMotion: false,
  sidebarCollapsed: false,
};

const themeOptions = [
  { value: 'light', label: 'Light', icon: Sun, description: 'Light background with dark text' },
  { value: 'dark', label: 'Dark', icon: Moon, description: 'Dark background with light text' },
  { value: 'system', label: 'System', icon: Monitor, description: 'Follow your system preferences' },
];

const accentColors: { value: AccentColor; label: string; color: string }[] = [
  { value: 'blue', label: 'Blue', color: 'bg-blue-500' },
  { value: 'green', label: 'Green', color: 'bg-green-500' },
  { value: 'purple', label: 'Purple', color: 'bg-purple-500' },
  { value: 'orange', label: 'Orange', color: 'bg-orange-500' },
  { value: 'red', label: 'Red', color: 'bg-red-500' },
];

const fontSizeOptions = [
  { value: 'small', label: 'Small', description: '14px base' },
  { value: 'medium', label: 'Medium', description: '16px base (default)' },
  { value: 'large', label: 'Large', description: '18px base' },
];

const densityOptions = [
  { value: 'comfortable', label: 'Comfortable', description: 'More spacing for easier reading' },
  { value: 'compact', label: 'Compact', description: 'More content on screen' },
];

export default function AppearanceSettingsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [isSaving, setIsSaving] = React.useState(false);
  const [settings, setSettings] = React.useState<AppearanceSettings>(defaultSettings);

  const handleChange = <K extends keyof AppearanceSettings>(
    key: K, 
    value: AppearanceSettings[K]
  ) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    
    // Apply theme change immediately
    if (key === 'theme') {
      applyTheme(value as ThemeMode);
    }
  };

  const applyTheme = (theme: ThemeMode) => {
    const root = document.documentElement;
    if (theme === 'system') {
      const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      root.classList.toggle('dark', systemDark);
    } else {
      root.classList.toggle('dark', theme === 'dark');
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
  };

  return (
    <div className="space-y-8 page-fade-in max-w-4xl">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10 hover:text-primary transition-all" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="space-y-1">
            <h1 className="text-3xl font-heading font-bold tracking-tight ">
              Appearance
            </h1>
            <p className="text-muted-foreground font-medium text-sm">Customize your personal viewing experience and interface aesthetics</p>
          </div>
        </div>
        <Button onClick={handleSave} disabled={isSaving} className="rounded-2xl shadow-glow subtle-shine h-12 px-8" size="lg">
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Applying...
            </>
          ) : (
            <>
              <Save className="mr-2 h-5 w-5" />
              Save Configuration
            </>
          )}
        </Button>
      </div>

      {/* Theme */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading flex items-center gap-3">
            <Sun className="h-5 w-5 text-primary/60" />
            Interface Theme
          </CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Choose your preferred organizational lighting mode</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            {themeOptions.map((option) => {
              const Icon = option.icon;
              const isSelected = settings.theme === option.value;
              return (
                <button
                  key={option.value}
                  onClick={() => handleChange('theme', option.value as ThemeMode)}
                  className={cn(
                    'relative flex flex-col items-center gap-4 p-6 rounded-2xl border-2 transition-all duration-300 group',
                    isSelected 
                      ? 'border-primary bg-primary/5 shadow-glow' 
                      : 'border-border/40 hover:border-primary/20 hover:bg-muted/50'
                  )}
                >
                  {isSelected && (
                    <div className="absolute top-3 right-3 p-1.5 bg-primary text-primary-foreground rounded-full shadow-glow">
                      <Check className="h-3 w-3" />
                    </div>
                  )}
                  <div className={cn(
                    'p-4 rounded-2xl transition-transform duration-500 group-hover:scale-110 shadow-sm',
                    option.value === 'dark' ? 'bg-slate-900 border border-slate-800' : 'bg-white border border-slate-200'
                  )}>
                    <Icon className={cn(
                      'h-8 w-8',
                      option.value === 'dark' ? 'text-slate-100' : 'text-slate-900'
                    )} />
                  </div>
                  <div className="text-center">
                    <p className="font-heading font-bold text-sm tracking-tight">{option.label}</p>
                    <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60 mt-1">{option.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Accent Color */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading flex items-center gap-3">
            <Palette className="h-5 w-5 text-primary/60" />
            Accent Parameters
          </CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Define the primary signature color for your intelligence layer</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {accentColors.map((color) => {
              const isSelected = settings.accentColor === color.value;
              return (
                <button
                  key={color.value}
                  onClick={() => handleChange('accentColor', color.value)}
                  className={cn(
                    'relative flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition-all duration-300 group',
                    isSelected 
                      ? 'border-foreground bg-foreground/5 shadow-premium' 
                      : 'border-border/40 hover:border-primary/20'
                  )}
                  title={color.label}
                >
                  <div className={cn('w-10 h-10 rounded-full shadow-inner-soft transition-transform duration-300 group-hover:scale-110', color.color)}>
                    {isSelected && (
                      <div className="flex items-center justify-center h-full">
                        <Check className="h-5 w-5 text-white" />
                      </div>
                    )}
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{color.label}</span>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Typography */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading flex items-center gap-3">
            <Type className="h-5 w-5 text-primary/60" />
            Visual Hierarchy
          </CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Calibrate data density and information legibility</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div>
              <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1 mb-4 block">Information Scale</Label>
              <div className="grid gap-4 sm:grid-cols-3">
                {fontSizeOptions.map((option) => {
                  const isSelected = settings.fontSize === option.value;
                  return (
                    <button
                      key={option.value}
                      onClick={() => handleChange('fontSize', option.value as FontSize)}
                      className={cn(
                        'flex items-center justify-between p-5 rounded-2xl border-2 transition-all duration-300',
                        isSelected 
                          ? 'border-primary bg-primary/5 shadow-sm' 
                          : 'border-border/40 hover:border-primary/20'
                      )}
                    >
                      <div className="text-left">
                        <p className={cn(
                          'font-heading font-bold tracking-tight',
                          option.value === 'small' && 'text-sm',
                          option.value === 'medium' && 'text-base',
                          option.value === 'large' && 'text-lg'
                        )}>
                          {option.label}
                        </p>
                        <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">{option.description}</p>
                      </div>
                      {isSelected && (
                        <div className="p-1.5 bg-primary text-primary-foreground rounded-full shadow-glow">
                          <Check className="h-3 w-3" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Layout */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading flex items-center gap-3">
            <Layout className="h-5 w-5 text-primary/60" />
            Spatial Orchestration
          </CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Optimize the physical distribution of interface components</CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          <div>
            <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60 ml-1 mb-4 block">Interface Density</Label>
            <div className="grid gap-4 sm:grid-cols-2">
              {densityOptions.map((option) => {
                const isSelected = settings.density === option.value;
                return (
                  <button
                    key={option.value}
                    onClick={() => handleChange('density', option.value as DensityMode)}
                    className={cn(
                      'flex items-center justify-between p-5 rounded-2xl border-2 transition-all duration-300',
                      isSelected 
                        ? 'border-primary bg-primary/5 shadow-sm' 
                        : 'border-border/40 hover:border-primary/20'
                    )}
                  >
                    <div className="text-left">
                      <p className="font-heading font-bold tracking-tight">{option.label}</p>
                      <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">{option.description}</p>
                    </div>
                    {isSelected && (
                      <div className="p-1.5 bg-primary text-primary-foreground rounded-full shadow-glow">
                        <Check className="h-3 w-3" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center justify-between p-5 rounded-2xl bg-muted/30 border border-border/40">
            <div>
              <p className="font-heading font-bold tracking-tight">Compact Navigation</p>
              <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">Minimize sidebar footprint by default</p>
            </div>
            <Switch 
              checked={settings.sidebarCollapsed} 
              onCheckedChange={(v) => handleChange('sidebarCollapsed', v)}
              className="data-[state=checked]:bg-primary"
            />
          </div>
        </CardContent>
      </Card>

      {/* Accessibility */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading">Inclusion & Access</CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Calibrate the interface for universal operational access</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-5 rounded-2xl bg-muted/30 border border-border/40">
            <div>
              <p className="font-heading font-bold tracking-tight">Kinetic Reduction</p>
              <p className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground/60">Minimize interface motion and transitions</p>
            </div>
            <Switch 
              checked={settings.reducedMotion} 
              onCheckedChange={(v) => handleChange('reducedMotion', v)}
              className="data-[state=checked]:bg-primary"
            />
          </div>
        </CardContent>
      </Card>

      {/* Preview */}
      <Card className="border-dashed border-primary/20 bg-primary/[0.02]">
        <CardHeader>
          <CardTitle className="text-lg font-heading">Operational Preview</CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">Simulated environment with current parameters</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border border-border/40 rounded-[2rem] p-8 bg-background/50 backdrop-blur-md shadow-premium overflow-hidden relative">
            <div className="absolute top-0 right-0 p-4 opacity-5">
              <Shield className="h-24 w-24 text-primary" />
            </div>
            <div className="flex items-center gap-5 mb-8">
              <div className={cn('w-14 h-14 rounded-2xl shadow-glow subtle-shine transition-all duration-500', accentColors.find(c => c.value === settings.accentColor)?.color)} />
              <div>
                <p className={cn(
                  'font-heading font-bold tracking-tight',
                  settings.fontSize === 'small' && 'text-sm',
                  settings.fontSize === 'medium' && 'text-xl',
                  settings.fontSize === 'large' && 'text-2xl'
                )}>
                  Intelligence Module 04
                </p>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground/60">Live Operational Stream</p>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <Button className="rounded-xl shadow-glow" size={settings.density === 'compact' ? 'sm' : 'default'}>
                Execute Command
              </Button>
              <Button variant="outline" className="rounded-xl" size={settings.density === 'compact' ? 'sm' : 'default'}>
                View Analytics
              </Button>
              <Button variant="ghost" className="rounded-xl" size={settings.density === 'compact' ? 'sm' : 'default'}>
                Dismiss
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
