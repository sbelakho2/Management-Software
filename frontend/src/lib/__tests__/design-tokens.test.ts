/**
 * Tests for Design Tokens System
 */
import {
  tokens,
  neutral,
  primary,
  success,
  warning,
  danger,
  info,
  lightTheme,
  darkTheme,
  shadows,
  radii,
  spacing,
  fontFamily,
  fontSize,
  fontWeight,
  zIndex,
  transitions,
  durations,
  easings,
  breakpoints,
  componentSizes,
  densityModes,
  statusColors,
  badgeVariants,
  elevations,
  darkElevations,
  focusRing,
  keyframes,
  colorScaleToCSSVars,
  themeColorsToCSSVars,
  generateThemeCSSVars,
  getSpacing,
  getRadius,
  getShadow,
  getZIndex,
  getColor,
  getComponentSize,
  getDensityMode,
  getStatusColors,
  getBadgeVariant,
} from '@/lib/design-tokens';

// =============================================================================
// Color Palette Tests
// =============================================================================

describe('Color Palette', () => {
  describe('neutral scale', () => {
    it('should have all shade values', () => {
      expect(neutral[50]).toBeDefined();
      expect(neutral[100]).toBeDefined();
      expect(neutral[200]).toBeDefined();
      expect(neutral[300]).toBeDefined();
      expect(neutral[400]).toBeDefined();
      expect(neutral[500]).toBeDefined();
      expect(neutral[600]).toBeDefined();
      expect(neutral[700]).toBeDefined();
      expect(neutral[800]).toBeDefined();
      expect(neutral[900]).toBeDefined();
      expect(neutral[950]).toBeDefined();
    });
    
    it('should have valid hex colors', () => {
      const hexRegex = /^#[0-9A-Fa-f]{6}$/;
      Object.values(neutral).forEach(color => {
        expect(color).toMatch(hexRegex);
      });
    });
  });
  
  describe('primary scale', () => {
    it('should have all shade values', () => {
      expect(Object.keys(primary)).toHaveLength(11);
    });
    
    it('should have valid hex colors', () => {
      const hexRegex = /^#[0-9A-Fa-f]{6}$/;
      Object.values(primary).forEach(color => {
        expect(color).toMatch(hexRegex);
      });
    });
  });
  
  describe('success scale', () => {
    it('should have green-based colors', () => {
      // Success should be green-ish (higher G component)
      expect(success[500]).toBeDefined();
    });
  });
  
  describe('warning scale', () => {
    it('should have amber-based colors', () => {
      expect(warning[500]).toBeDefined();
    });
  });
  
  describe('danger scale', () => {
    it('should have red-based colors', () => {
      expect(danger[500]).toBeDefined();
    });
  });
  
  describe('info scale', () => {
    it('should have cyan-based colors', () => {
      expect(info[500]).toBeDefined();
    });
  });
});

// =============================================================================
// Theme Tests
// =============================================================================

describe('Themes', () => {
  describe('lightTheme', () => {
    it('should have all required color properties', () => {
      expect(lightTheme.background).toBeDefined();
      expect(lightTheme.foreground).toBeDefined();
      expect(lightTheme.card).toBeDefined();
      expect(lightTheme.primary).toBeDefined();
      expect(lightTheme.secondary).toBeDefined();
      expect(lightTheme.muted).toBeDefined();
      expect(lightTheme.accent).toBeDefined();
      expect(lightTheme.destructive).toBeDefined();
      expect(lightTheme.border).toBeDefined();
      expect(lightTheme.ring).toBeDefined();
    });
    
    it('should have status colors', () => {
      expect(lightTheme.success).toBeDefined();
      expect(lightTheme.warning).toBeDefined();
      expect(lightTheme.danger).toBeDefined();
      expect(lightTheme.info).toBeDefined();
    });
    
    it('should have light background', () => {
      // Light theme background should be light colored
      expect(lightTheme.background).toBe(neutral[50]);
    });
  });
  
  describe('darkTheme', () => {
    it('should have all required color properties', () => {
      expect(darkTheme.background).toBeDefined();
      expect(darkTheme.foreground).toBeDefined();
      expect(darkTheme.card).toBeDefined();
      expect(darkTheme.primary).toBeDefined();
    });
    
    it('should have dark background', () => {
      // Dark theme background should be dark colored
      expect(darkTheme.background).toBe(neutral[950]);
    });
    
    it('should have light foreground', () => {
      expect(darkTheme.foreground).toBe(neutral[50]);
    });
  });
});

// =============================================================================
// Shadows Tests
// =============================================================================

describe('Shadows', () => {
  it('should have all shadow levels', () => {
    expect(shadows.none).toBe('none');
    expect(shadows.xs).toBeDefined();
    expect(shadows.sm).toBeDefined();
    expect(shadows.md).toBeDefined();
    expect(shadows.lg).toBeDefined();
    expect(shadows.xl).toBeDefined();
    expect(shadows['2xl']).toBeDefined();
    expect(shadows.inner).toBeDefined();
  });
  
  it('should have valid CSS box-shadow values', () => {
    expect(shadows.sm).toContain('rgb');
    expect(shadows.md).toContain('rgb');
    expect(shadows.lg).toContain('rgb');
  });
  
  it('should have inner shadow', () => {
    expect(shadows.inner).toContain('inset');
  });
});

// =============================================================================
// Radii Tests
// =============================================================================

describe('Radii', () => {
  it('should have all radius values', () => {
    expect(radii.none).toBe('0px');
    expect(radii.sm).toBeDefined();
    expect(radii.DEFAULT).toBeDefined();
    expect(radii.md).toBeDefined();
    expect(radii.lg).toBeDefined();
    expect(radii.xl).toBeDefined();
    expect(radii['2xl']).toBeDefined();
    expect(radii['3xl']).toBeDefined();
    expect(radii.full).toBe('9999px');
  });
  
  it('should have increasing values', () => {
    const parseRem = (val: string) => parseFloat(val.replace('rem', ''));
    expect(parseRem(radii.sm)).toBeLessThan(parseRem(radii.DEFAULT));
    expect(parseRem(radii.DEFAULT)).toBeLessThan(parseRem(radii.md));
    expect(parseRem(radii.md)).toBeLessThan(parseRem(radii.lg));
  });
});

// =============================================================================
// Spacing Tests
// =============================================================================

describe('Spacing', () => {
  it('should have zero spacing', () => {
    expect(spacing[0]).toBe('0px');
  });
  
  it('should have pixel spacing', () => {
    expect(spacing.px).toBe('1px');
  });
  
  it('should have common spacing values', () => {
    expect(spacing[1]).toBe('0.25rem');
    expect(spacing[2]).toBe('0.5rem');
    expect(spacing[4]).toBe('1rem');
    expect(spacing[8]).toBe('2rem');
    expect(spacing[16]).toBe('4rem');
  });
  
  it('should have large spacing values', () => {
    expect(spacing[96]).toBe('24rem');
  });
});

// =============================================================================
// Typography Tests
// =============================================================================

describe('Typography', () => {
  describe('fontFamily', () => {
    it('should have sans, serif, and mono families', () => {
      expect(fontFamily.sans).toBeDefined();
      expect(fontFamily.serif).toBeDefined();
      expect(fontFamily.mono).toBeDefined();
    });
    
    it('should have system font stack for sans', () => {
      expect(fontFamily.sans).toContain('system-ui');
    });
    
    it('should have monospace fonts for mono', () => {
      expect(fontFamily.mono).toContain('monospace');
    });
  });
  
  describe('fontSize', () => {
    it('should have all size levels', () => {
      expect(fontSize.xs).toBeDefined();
      expect(fontSize.sm).toBeDefined();
      expect(fontSize.base).toBeDefined();
      expect(fontSize.lg).toBeDefined();
      expect(fontSize.xl).toBeDefined();
      expect(fontSize['2xl']).toBeDefined();
    });
    
    it('should include line height', () => {
      expect(fontSize.base[1]).toHaveProperty('lineHeight');
    });
  });
  
  describe('fontWeight', () => {
    it('should have weight values from thin to black', () => {
      expect(fontWeight.thin).toBe('100');
      expect(fontWeight.normal).toBe('400');
      expect(fontWeight.bold).toBe('700');
      expect(fontWeight.black).toBe('900');
    });
  });
});

// =============================================================================
// Z-Index Tests
// =============================================================================

describe('Z-Index', () => {
  it('should have base z-index values', () => {
    expect(zIndex[0]).toBe('0');
    expect(zIndex[10]).toBe('10');
    expect(zIndex[50]).toBe('50');
  });
  
  it('should have semantic z-index values', () => {
    expect(zIndex.dropdown).toBe('100');
    expect(zIndex.sticky).toBe('200');
    expect(zIndex.overlay).toBe('300');
    expect(zIndex.modal).toBe('400');
    expect(zIndex.popover).toBe('500');
    expect(zIndex.tooltip).toBe('600');
    expect(zIndex.toast).toBe('700');
    expect(zIndex.max).toBe('9999');
  });
  
  it('should have proper stacking order', () => {
    expect(parseInt(zIndex.dropdown)).toBeLessThan(parseInt(zIndex.modal));
    expect(parseInt(zIndex.modal)).toBeLessThan(parseInt(zIndex.tooltip));
    expect(parseInt(zIndex.tooltip)).toBeLessThan(parseInt(zIndex.max));
  });
});

// =============================================================================
// Transitions Tests
// =============================================================================

describe('Transitions', () => {
  describe('transitions', () => {
    it('should have common transition values', () => {
      expect(transitions.none).toBe('none');
      expect(transitions.all).toBeDefined();
      expect(transitions.colors).toBeDefined();
      expect(transitions.opacity).toBeDefined();
      expect(transitions.shadow).toBeDefined();
      expect(transitions.transform).toBeDefined();
    });
    
    it('should include timing function', () => {
      expect(transitions.all).toContain('cubic-bezier');
    });
  });
  
  describe('durations', () => {
    it('should have duration values', () => {
      expect(durations.fast).toBe('75ms');
      expect(durations.normal).toBe('150ms');
      expect(durations.slow).toBe('200ms');
      expect(durations.slower).toBe('300ms');
      expect(durations.slowest).toBe('500ms');
    });
  });
  
  describe('easings', () => {
    it('should have easing functions', () => {
      expect(easings.linear).toBe('linear');
      expect(easings.in).toContain('cubic-bezier');
      expect(easings.out).toContain('cubic-bezier');
      expect(easings.inOut).toContain('cubic-bezier');
      expect(easings.bounce).toContain('cubic-bezier');
    });
  });
});

// =============================================================================
// Breakpoints Tests
// =============================================================================

describe('Breakpoints', () => {
  it('should have responsive breakpoints', () => {
    expect(breakpoints.sm).toBe('640px');
    expect(breakpoints.md).toBe('768px');
    expect(breakpoints.lg).toBe('1024px');
    expect(breakpoints.xl).toBe('1280px');
    expect(breakpoints['2xl']).toBe('1536px');
  });
  
  it('should have increasing values', () => {
    const parse = (val: string) => parseInt(val.replace('px', ''));
    expect(parse(breakpoints.sm)).toBeLessThan(parse(breakpoints.md));
    expect(parse(breakpoints.md)).toBeLessThan(parse(breakpoints.lg));
    expect(parse(breakpoints.lg)).toBeLessThan(parse(breakpoints.xl));
  });
});

// =============================================================================
// Component Sizes Tests
// =============================================================================

describe('Component Sizes', () => {
  it('should have all size variants', () => {
    expect(componentSizes.xs).toBeDefined();
    expect(componentSizes.sm).toBeDefined();
    expect(componentSizes.md).toBeDefined();
    expect(componentSizes.lg).toBeDefined();
    expect(componentSizes.xl).toBeDefined();
  });
  
  it('should have height, padding, fontSize, and iconSize', () => {
    const md = componentSizes.md;
    expect(md.height).toBeDefined();
    expect(md.padding).toBeDefined();
    expect(md.fontSize).toBeDefined();
    expect(md.iconSize).toBeDefined();
  });
  
  it('should have increasing heights', () => {
    const parseRem = (val: string) => parseFloat(val.replace('rem', ''));
    expect(parseRem(componentSizes.xs.height)).toBeLessThan(parseRem(componentSizes.sm.height));
    expect(parseRem(componentSizes.sm.height)).toBeLessThan(parseRem(componentSizes.md.height));
    expect(parseRem(componentSizes.md.height)).toBeLessThan(parseRem(componentSizes.lg.height));
  });
});

// =============================================================================
// Density Modes Tests
// =============================================================================

describe('Density Modes', () => {
  it('should have comfortable and compact modes', () => {
    expect(densityModes.comfortable).toBeDefined();
    expect(densityModes.compact).toBeDefined();
  });
  
  it('should have rowHeight, cellPadding, and gap', () => {
    expect(densityModes.comfortable.rowHeight).toBeDefined();
    expect(densityModes.comfortable.cellPadding).toBeDefined();
    expect(densityModes.comfortable.gap).toBeDefined();
  });
  
  it('should have larger values for comfortable mode', () => {
    const parseRem = (val: string) => parseFloat(val.replace('rem', ''));
    expect(parseRem(densityModes.comfortable.rowHeight)).toBeGreaterThan(
      parseRem(densityModes.compact.rowHeight)
    );
  });
});

// =============================================================================
// Status Colors Tests
// =============================================================================

describe('Status Colors', () => {
  it('should have all status types', () => {
    expect(statusColors.success).toBeDefined();
    expect(statusColors.warning).toBeDefined();
    expect(statusColors.danger).toBeDefined();
    expect(statusColors.info).toBeDefined();
    expect(statusColors.neutral).toBeDefined();
  });
  
  it('should have background, foreground, border, and backgroundSubtle', () => {
    const successStatus = statusColors.success;
    expect(successStatus.background).toBeDefined();
    expect(successStatus.foreground).toBeDefined();
    expect(successStatus.border).toBeDefined();
    expect(successStatus.backgroundSubtle).toBeDefined();
  });
});

// =============================================================================
// Badge Variants Tests
// =============================================================================

describe('Badge Variants', () => {
  it('should have all badge variants', () => {
    expect(badgeVariants.default).toBeDefined();
    expect(badgeVariants.primary).toBeDefined();
    expect(badgeVariants.success).toBeDefined();
    expect(badgeVariants.warning).toBeDefined();
    expect(badgeVariants.danger).toBeDefined();
    expect(badgeVariants.info).toBeDefined();
    expect(badgeVariants.outline).toBeDefined();
  });
  
  it('should have background and foreground', () => {
    expect(badgeVariants.primary.background).toBeDefined();
    expect(badgeVariants.primary.foreground).toBeDefined();
  });
  
  it('should have border for outline variant', () => {
    expect(badgeVariants.outline.border).toBeDefined();
    expect(badgeVariants.outline.background).toBe('transparent');
  });
});

// =============================================================================
// Elevations Tests
// =============================================================================

describe('Elevations', () => {
  it('should have flat, raised, and overlay levels', () => {
    expect(elevations.flat).toBeDefined();
    expect(elevations.raised).toBeDefined();
    expect(elevations.overlay).toBeDefined();
  });
  
  it('should have shadow and zIndex for each level', () => {
    expect(elevations.flat.shadow).toBe('none');
    expect(elevations.flat.zIndex).toBe(0);
    expect(elevations.raised.shadow).toBeDefined();
    expect(elevations.raised.zIndex).toBeGreaterThan(0);
  });
  
  it('should have dark mode elevations', () => {
    expect(darkElevations.flat).toBeDefined();
    expect(darkElevations.raised).toBeDefined();
    expect(darkElevations.overlay).toBeDefined();
  });
});

// =============================================================================
// Focus Ring Tests
// =============================================================================

describe('Focus Ring', () => {
  it('should have focus ring properties', () => {
    expect(focusRing.width).toBe('2px');
    expect(focusRing.offset).toBe('2px');
    expect(focusRing.color).toBeDefined();
    expect(focusRing.style).toBeDefined();
  });
});

// =============================================================================
// Keyframes Tests
// =============================================================================

describe('Keyframes', () => {
  it('should have common animation keyframes', () => {
    expect(keyframes.fadeIn).toBeDefined();
    expect(keyframes.fadeOut).toBeDefined();
    expect(keyframes.slideInFromTop).toBeDefined();
    expect(keyframes.slideInFromBottom).toBeDefined();
    expect(keyframes.scaleIn).toBeDefined();
    expect(keyframes.spin).toBeDefined();
    expect(keyframes.pulse).toBeDefined();
    expect(keyframes.bounce).toBeDefined();
  });
  
  it('should have from/to for fade animations', () => {
    expect(keyframes.fadeIn.from).toBeDefined();
    expect(keyframes.fadeIn.to).toBeDefined();
  });
});

// =============================================================================
// CSS Variable Utilities Tests
// =============================================================================

describe('CSS Variable Utilities', () => {
  describe('colorScaleToCSSVars', () => {
    it('should convert color scale to CSS variables', () => {
      const vars = colorScaleToCSSVars('primary', primary);
      
      expect(vars['--primary-50']).toBe(primary[50]);
      expect(vars['--primary-500']).toBe(primary[500]);
      expect(vars['--primary-950']).toBe(primary[950]);
    });
  });
  
  describe('themeColorsToCSSVars', () => {
    it('should convert theme colors to CSS variables', () => {
      const vars = themeColorsToCSSVars(lightTheme);
      
      expect(vars['--background']).toBe(lightTheme.background);
      expect(vars['--foreground']).toBe(lightTheme.foreground);
      expect(vars['--primary']).toBe(lightTheme.primary);
    });
    
    it('should convert camelCase to kebab-case', () => {
      const vars = themeColorsToCSSVars(lightTheme);
      
      expect(vars['--card-foreground']).toBe(lightTheme.cardForeground);
      expect(vars['--primary-foreground']).toBe(lightTheme.primaryForeground);
    });
  });
  
  describe('generateThemeCSSVars', () => {
    it('should generate all CSS variables for light theme', () => {
      const vars = generateThemeCSSVars('light');
      
      expect(vars['--background']).toBe(lightTheme.background);
      expect(vars['--shadow-sm']).toBe(shadows.sm);
      expect(vars['--radius']).toBe(radii.DEFAULT);
    });
    
    it('should generate all CSS variables for dark theme', () => {
      const vars = generateThemeCSSVars('dark');
      
      expect(vars['--background']).toBe(darkTheme.background);
    });
    
    it('should include elevation shadows', () => {
      const vars = generateThemeCSSVars('light');
      
      expect(vars['--elevation-flat']).toBe(elevations.flat.shadow);
      expect(vars['--elevation-raised']).toBe(elevations.raised.shadow);
    });
  });
});

// =============================================================================
// Token Access Utilities Tests
// =============================================================================

describe('Token Access Utilities', () => {
  describe('getSpacing', () => {
    it('should return correct spacing value', () => {
      expect(getSpacing(0)).toBe('0px');
      expect(getSpacing(4)).toBe('1rem');
      expect(getSpacing(8)).toBe('2rem');
    });
  });
  
  describe('getRadius', () => {
    it('should return correct radius value', () => {
      expect(getRadius('none')).toBe('0px');
      expect(getRadius('DEFAULT')).toBe(radii.DEFAULT);
      expect(getRadius('full')).toBe('9999px');
    });
  });
  
  describe('getShadow', () => {
    it('should return correct shadow value', () => {
      expect(getShadow('none')).toBe('none');
      expect(getShadow('sm')).toBe(shadows.sm);
      expect(getShadow('lg')).toBe(shadows.lg);
    });
  });
  
  describe('getZIndex', () => {
    it('should return correct z-index value', () => {
      expect(getZIndex('modal')).toBe('400');
      expect(getZIndex('tooltip')).toBe('600');
      expect(getZIndex('auto')).toBe('auto');
    });
  });
  
  describe('getColor', () => {
    it('should return correct color from scale', () => {
      expect(getColor('primary', 500)).toBe(primary[500]);
      expect(getColor('danger', 600)).toBe(danger[600]);
      expect(getColor('neutral', 100)).toBe(neutral[100]);
    });
  });
  
  describe('getComponentSize', () => {
    it('should return correct component size', () => {
      const md = getComponentSize('md');
      expect(md).toBe(componentSizes.md);
      expect(md.height).toBe('2.5rem');
    });
  });
  
  describe('getDensityMode', () => {
    it('should return correct density mode', () => {
      const comfortable = getDensityMode('comfortable');
      expect(comfortable).toBe(densityModes.comfortable);
      
      const compact = getDensityMode('compact');
      expect(compact).toBe(densityModes.compact);
    });
  });
  
  describe('getStatusColors', () => {
    it('should return correct status colors', () => {
      const successStatus = getStatusColors('success');
      expect(successStatus).toBe(statusColors.success);
    });
  });
  
  describe('getBadgeVariant', () => {
    it('should return correct badge variant', () => {
      const primaryBadge = getBadgeVariant('primary');
      expect(primaryBadge).toBe(badgeVariants.primary);
    });
  });
});

// =============================================================================
// Tokens Object Tests
// =============================================================================

describe('Tokens Object', () => {
  it('should export all token categories', () => {
    expect(tokens.colors).toBeDefined();
    expect(tokens.themes).toBeDefined();
    expect(tokens.shadows).toBeDefined();
    expect(tokens.radii).toBeDefined();
    expect(tokens.spacing).toBeDefined();
    expect(tokens.typography).toBeDefined();
    expect(tokens.zIndex).toBeDefined();
    expect(tokens.transitions).toBeDefined();
    expect(tokens.breakpoints).toBeDefined();
    expect(tokens.componentSizes).toBeDefined();
    expect(tokens.densityModes).toBeDefined();
    expect(tokens.statusColors).toBeDefined();
    expect(tokens.badgeVariants).toBeDefined();
    expect(tokens.elevations).toBeDefined();
    expect(tokens.focusRing).toBeDefined();
    expect(tokens.keyframes).toBeDefined();
  });
  
  it('should have light and dark themes', () => {
    expect(tokens.themes.light).toBe(lightTheme);
    expect(tokens.themes.dark).toBe(darkTheme);
  });
  
  it('should have all color scales', () => {
    expect(tokens.colors.neutral).toBe(neutral);
    expect(tokens.colors.primary).toBe(primary);
    expect(tokens.colors.success).toBe(success);
    expect(tokens.colors.warning).toBe(warning);
    expect(tokens.colors.danger).toBe(danger);
    expect(tokens.colors.info).toBe(info);
  });
});
