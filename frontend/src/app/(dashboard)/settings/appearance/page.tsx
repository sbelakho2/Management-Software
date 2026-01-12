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
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';

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
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push('/settings')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Appearance</h1>
          <p className="text-muted-foreground">Customize the look and feel of the application</p>
        </div>
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Save Changes
            </>
          )}
        </Button>
      </div>

      {/* Theme */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Sun className="h-4 w-4" />
            Theme
          </CardTitle>
          <CardDescription>Choose your preferred color scheme</CardDescription>
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
                    'relative flex flex-col items-center gap-3 p-4 border rounded-lg transition-colors',
                    isSelected 
                      ? 'border-primary bg-primary/5' 
                      : 'hover:bg-muted'
                  )}
                >
                  {isSelected && (
                    <div className="absolute top-2 right-2 p-1 bg-primary text-primary-foreground rounded-full">
                      <Check className="h-3 w-3" />
                    </div>
                  )}
                  <div className={cn(
                    'p-3 rounded-lg',
                    option.value === 'dark' ? 'bg-gray-800' : 'bg-gray-100'
                  )}>
                    <Icon className={cn(
                      'h-6 w-6',
                      option.value === 'dark' ? 'text-gray-100' : 'text-gray-800'
                    )} />
                  </div>
                  <div className="text-center">
                    <p className="font-medium text-sm">{option.label}</p>
                    <p className="text-xs text-muted-foreground">{option.description}</p>
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
          <CardTitle className="text-base flex items-center gap-2">
            <Palette className="h-4 w-4" />
            Accent Color
          </CardTitle>
          <CardDescription>Primary color used throughout the interface</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            {accentColors.map((color) => {
              const isSelected = settings.accentColor === color.value;
              return (
                <button
                  key={color.value}
                  onClick={() => handleChange('accentColor', color.value)}
                  className={cn(
                    'relative flex flex-col items-center gap-2 p-3 border rounded-lg transition-all',
                    isSelected 
                      ? 'border-foreground scale-105' 
                      : 'hover:border-muted-foreground'
                  )}
                  title={color.label}
                >
                  <div className={cn('w-8 h-8 rounded-full', color.color)}>
                    {isSelected && (
                      <div className="flex items-center justify-center h-full">
                        <Check className="h-4 w-4 text-white" />
                      </div>
                    )}
                  </div>
                  <span className="text-xs">{color.label}</span>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Typography */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Type className="h-4 w-4" />
            Typography
          </CardTitle>
          <CardDescription>Adjust font size for better readability</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label className="text-sm font-medium mb-3 block">Font Size</Label>
              <div className="grid gap-3 sm:grid-cols-3">
                {fontSizeOptions.map((option) => {
                  const isSelected = settings.fontSize === option.value;
                  return (
                    <button
                      key={option.value}
                      onClick={() => handleChange('fontSize', option.value as FontSize)}
                      className={cn(
                        'flex items-center justify-between p-3 border rounded-lg transition-colors',
                        isSelected 
                          ? 'border-primary bg-primary/5' 
                          : 'hover:bg-muted'
                      )}
                    >
                      <div className="text-left">
                        <p className={cn(
                          'font-medium',
                          option.value === 'small' && 'text-sm',
                          option.value === 'large' && 'text-lg'
                        )}>
                          {option.label}
                        </p>
                        <p className="text-xs text-muted-foreground">{option.description}</p>
                      </div>
                      {isSelected && (
                        <div className="p-1 bg-primary text-primary-foreground rounded-full">
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
          <CardTitle className="text-base flex items-center gap-2">
            <Layout className="h-4 w-4" />
            Layout
          </CardTitle>
          <CardDescription>Control spacing and layout preferences</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <Label className="text-sm font-medium mb-3 block">Display Density</Label>
            <div className="grid gap-3 sm:grid-cols-2">
              {densityOptions.map((option) => {
                const isSelected = settings.density === option.value;
                return (
                  <button
                    key={option.value}
                    onClick={() => handleChange('density', option.value as DensityMode)}
                    className={cn(
                      'flex items-center justify-between p-3 border rounded-lg transition-colors',
                      isSelected 
                        ? 'border-primary bg-primary/5' 
                        : 'hover:bg-muted'
                    )}
                  >
                    <div className="text-left">
                      <p className="font-medium text-sm">{option.label}</p>
                      <p className="text-xs text-muted-foreground">{option.description}</p>
                    </div>
                    {isSelected && (
                      <div className="p-1 bg-primary text-primary-foreground rounded-full">
                        <Check className="h-3 w-3" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center justify-between py-2 border-t">
            <div>
              <p className="font-medium text-sm">Collapse Sidebar by Default</p>
              <p className="text-xs text-muted-foreground">Start with a minimized sidebar</p>
            </div>
            <Switch 
              checked={settings.sidebarCollapsed} 
              onCheckedChange={(v) => handleChange('sidebarCollapsed', v)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Accessibility */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Accessibility</CardTitle>
          <CardDescription>Settings for improved accessibility</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-medium text-sm">Reduce Motion</p>
              <p className="text-xs text-muted-foreground">Minimize animations throughout the interface</p>
            </div>
            <Switch 
              checked={settings.reducedMotion} 
              onCheckedChange={(v) => handleChange('reducedMotion', v)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Preview */}
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base">Preview</CardTitle>
          <CardDescription>See how your settings look</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg p-4 bg-muted/30">
            <div className="flex items-center gap-3 mb-4">
              <div className={cn('w-10 h-10 rounded-full', accentColors.find(c => c.value === settings.accentColor)?.color)} />
              <div>
                <p className={cn(
                  'font-medium',
                  settings.fontSize === 'small' && 'text-sm',
                  settings.fontSize === 'large' && 'text-lg'
                )}>
                  Sample Text
                </p>
                <p className="text-sm text-muted-foreground">This is how your content will appear</p>
              </div>
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              <Button size={settings.density === 'compact' ? 'sm' : 'default'}>
                Primary Button
              </Button>
              <Button variant="outline" size={settings.density === 'compact' ? 'sm' : 'default'}>
                Secondary
              </Button>
              <Button variant="ghost" size={settings.density === 'compact' ? 'sm' : 'default'}>
                Ghost
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
