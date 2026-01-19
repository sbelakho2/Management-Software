'use client';

import { useEffect } from 'react';

const APPEARANCE_STORAGE_KEY = 'sensei-appearance';

type AccentColor = 'orange' | 'blue' | 'green' | 'purple' | 'red';
type FontSize = 'small' | 'medium' | 'large';
type DensityMode = 'comfortable' | 'compact';

interface AppearanceSettings {
  accentColor: AccentColor;
  fontSize: FontSize;
  density: DensityMode;
  reducedMotion: boolean;
}

const accentColors: Record<AccentColor, { hsl: string; foreground: string; hex: string }> = {
  orange: { hsl: '43 100% 50%', foreground: '0 0% 0%', hex: '#FFBE00' },
  blue: { hsl: '217 91% 60%', foreground: '0 0% 100%', hex: '#3B82F6' },
  green: { hsl: '142 71% 45%', foreground: '0 0% 100%', hex: '#22C55E' },
  purple: { hsl: '262 83% 58%', foreground: '0 0% 100%', hex: '#8B5CF6' },
  red: { hsl: '0 84% 60%', foreground: '0 0% 100%', hex: '#EF4444' },
};

function applyAccentColor(color: AccentColor): void {
  const root = document.documentElement;
  const colorConfig = accentColors[color];
  if (colorConfig) {
    // Apply to --accent CSS variable
    root.style.setProperty('--accent', colorConfig.hsl);
    root.style.setProperty('--accent-foreground', colorConfig.foreground);
    // Also update primary to match accent for consistency
    root.style.setProperty('--primary', colorConfig.hsl);
    root.style.setProperty('--primary-foreground', colorConfig.foreground);
    // Update ring color to match
    root.style.setProperty('--ring', colorConfig.hsl);
    // Update rams-orange dynamically via custom property
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

export function AppearanceInitializer() {
  useEffect(() => {
    try {
      const stored = localStorage.getItem(APPEARANCE_STORAGE_KEY);
      if (stored) {
        const settings: AppearanceSettings = JSON.parse(stored);
        if (settings.accentColor) applyAccentColor(settings.accentColor);
        if (settings.fontSize) applyFontSize(settings.fontSize);
        if (settings.density) applyDensity(settings.density);
        if (typeof settings.reducedMotion === 'boolean') applyReducedMotion(settings.reducedMotion);
      }
    } catch (e) {
      // Ignore parsing errors
    }
  }, []);

  return null;
}
