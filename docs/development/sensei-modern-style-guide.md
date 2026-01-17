# Sensei Modern Design System

> **The authoritative style guide for Sensei OS frontend components**
> 
> **Version 2.0** - Updated January 2026

Sensei Modern is a premium enterprise design language that combines glass-morphism, subtle gradients, and refined typography to create an intelligent, futuristic manufacturing management interface.

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [What's New in 2.0](#whats-new-in-20)
3. [Color Tokens](#color-tokens)
4. [Typography](#typography)
5. [Spacing & Layout](#spacing--layout)
6. [Component Patterns](#component-patterns)
   - [Stat Cards](#stat-cards)
   - [Goal Progress Bars](#goal-progress-bars)
   - [Content Cards](#content-cards)
   - [Quick Action Items](#quick-action-items)
   - [Page Headers](#page-headers)
   - [Tables](#tables)
   - [Buttons](#buttons)
   - [Ambient Status Indicators](#ambient-status-indicators)
   - [Confidence Indicators](#confidence-indicators)
7. [Bento Grid Layouts](#bento-grid-layouts)
8. [Animation & Transitions](#animation--transitions)
9. [Accessibility](#accessibility)
10. [Code Examples](#code-examples)
11. [Shared Components](#shared-components)

---

## Design Philosophy

Sensei Modern is built on these core principles:

| Principle | Description |
|-----------|-------------|
| **Glass-morphism** | Semi-transparent surfaces with backdrop blur create depth and hierarchy |
| **Subtle Gradients** | Text and accents use gradient effects for premium feel |
| **Micro-interactions** | Hover states, transitions, and animations provide tactile feedback |
| **Information Density** | Enterprise-grade data presentation without visual clutter |
| **Consistent Rhythm** | Predictable spacing and sizing creates visual harmony |
| **Cognitive Load Reduction** | Chunking, goal progress, and clear hierarchy (Miller's Law) |
| **Manufacturing Context** | Emergency states, ambient status for time-critical operations |

---

## What's New in 2.0

### UX Psychology Enhancements

| Feature | UX Principle | Description |
|---------|--------------|-------------|
| **Goal Progress Bars** | Goal-Gradient Effect | Visual progress toward targets increases motivation |
| **Stat Sections** | Miller's Law | Group stats into semantic clusters of 3-4 items |
| **Spotlight Cards** | Von Restorff Effect | Make critical metrics stand out |
| **Staggered Animations** | Progressive Disclosure | Smooth list item reveals |

### Manufacturing-Specific Features

| Feature | Purpose |
|---------|---------|
| **Critical Alert Animation** | Pulsing border for urgent situations |
| **Ambient Status Indicators** | System health at a glance |
| **Confidence Indicators** | AI/ML prediction transparency |

### Modern CSS Patterns

| Feature | Technology |
|---------|------------|
| **Container Queries** | Component-driven responsiveness |
| **Bento Grid** | Asymmetric dashboard layouts |
| **Reduced Motion Alternatives** | Better accessibility |

---

## Color Tokens

Colors are defined as CSS custom properties in `globals.css` using HSL values.

### Primary Palette

```css
:root {
  /* Sensei Modern 2.0 - Premium Enterprise Palette - Light */
  --background: 240 20% 99%;
  --foreground: 240 10% 4%;
  --card: 0 0% 100%;
  --card-foreground: 240 10% 4%;
  --primary: 263 70% 50%;        /* Sensei Violet */
  --primary-foreground: 210 40% 98%;
  --secondary: 240 4.8% 95.9%;
  --secondary-foreground: 240 5.9% 10%;
  --muted: 240 4.8% 95.9%;
  --muted-foreground: 240 3.8% 46.1%;
  --accent: 142 70% 45%;         /* Action Mint */
  --accent-foreground: 210 40% 98%;
  --border: 240 5.9% 90%;
  --ring: 263 70% 50%;
  --radius: 1rem;
}
```

### Status Colors

```css
:root {
  --success: 142.1 76.2% 36.3%;
  --success-foreground: 355.7 100% 97.3%;
  --warning: 38 92% 50%;
  --warning-foreground: 48 96% 8.9%;
  --danger: 0 84.2% 60.2%;
  --danger-foreground: 210 40% 98%;
  --info: 210 100% 50%;           /* NEW in 2.0 */
  --info-foreground: 210 40% 98%;
}
```

### Goal Progress Colors (NEW in 2.0)

```css
:root {
  --goal-track: 240 4.8% 92%;
  --goal-fill: 263 70% 50%;
}
```

### Color Usage Guidelines

| Token | Use For |
|-------|---------|
| `primary` | Primary actions, active states, key metrics |
| `success` / `emerald-500` | Positive trends, completed states, healthy metrics |
| `warning` / `amber-500` | Caution states, pending items, in-progress |
| `danger` / `destructive` | Errors, critical alerts, negative trends |
| `muted-foreground` | Secondary text, labels, descriptions |

---

## Typography

### Font Stack

```css
font-family: var(--font-sans), system-ui, sans-serif;
```

### Text Styles

| Style | Classes | Usage |
|-------|---------|-------|
| **Page Title** | `text-4xl font-heading font-bold tracking-tight` | Main page headers |
| **Card Title** | `text-xl font-heading font-bold` | Section headers |
| **Stat Value** | `text-3xl font-heading font-bold tracking-tight` | Large numeric values |
| **Micro Label** | `text-[10px] font-bold uppercase tracking-widest` | Stat card labels, trend indicators |
| **Body Text** | `text-sm text-muted-foreground` | Descriptions, helper text |
| **Table Header** | `text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60` | Column headers |

### Gradient Text

For premium emphasis on key values and headings:

```tsx
className="bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70"
```

For status-specific gradient text:

```tsx
// Success
className="bg-clip-text text-transparent bg-gradient-to-br from-success to-success/70"

// Danger
className="bg-clip-text text-transparent bg-gradient-to-br from-danger to-danger/70"

// Warning
className="bg-clip-text text-transparent bg-gradient-to-br from-warning to-warning/70"
```

---

## Spacing & Layout

### Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `gap-4` | 1rem | Grid gaps, standard spacing |
| `gap-6` | 1.5rem | Section spacing |
| `gap-8` | 2rem | Major section breaks |
| `pt-6` | 1.5rem | Card content padding top |
| `p-3` | 0.75rem | Icon container padding |
| `p-4` | 1rem | Quick action item padding |

### Border Radius Scale

| Class | Usage |
|-------|-------|
| `rounded-xl` | Buttons, inputs, small elements |
| `rounded-2xl` | Quick action items, icon containers |
| `rounded-[2rem]` | Stat cards, standard cards |
| `rounded-[2.5rem]` | Large content cards, table containers |
| `rounded-full` | Avatars, circular indicators |

### Grid Layouts

```tsx
// Stat cards grid
<div className="grid gap-4 md:grid-cols-4">

// Two-column content
<div className="grid gap-6 md:grid-cols-2">

// Three-column quick actions
<div className="grid gap-4 md:grid-cols-3">
```

---

## Component Patterns

### Stat Cards

The **authoritative** stat card pattern for Sensei Modern:

```tsx
<Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
  <CardContent className="pt-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
          {label}
        </p>
        <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70 mt-1">
          {value}
        </p>
        {trend && (
          <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 mt-2">
            {trend}
          </p>
        )}
      </div>
      <div className="p-3 rounded-2xl shadow-sm bg-{color}/10 text-{color}">
        <Icon className="h-5 w-5" />
      </div>
    </div>
  </CardContent>
</Card>
```

#### Key Requirements:

| Element | Specification |
|---------|---------------|
| **Card** | `rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md` |
| **Hover** | `transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1` |
| **Layout** | `flex items-center justify-between` - label/value LEFT, icon RIGHT |
| **Label** | `text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60` |
| **Value** | `text-3xl font-heading font-bold tracking-tight` with gradient text |
| **Icon Container** | `p-3 rounded-2xl shadow-sm bg-{color}/10 text-{color}` |
| **Icon Size** | `h-5 w-5` (NOT h-4 w-4) |

#### Icon Container Color Variants:

```tsx
// Primary (default)
className="p-3 rounded-2xl shadow-sm bg-primary/10 text-primary"

// Success
className="p-3 rounded-2xl shadow-sm bg-emerald-500/10 text-emerald-600"

// Warning
className="p-3 rounded-2xl shadow-sm bg-warning/10 text-warning"

// Danger
className="p-3 rounded-2xl shadow-sm bg-danger/10 text-danger"

// Info (NEW in 2.0)
className="p-3 rounded-2xl shadow-sm bg-blue-500/10 text-blue-600"

// Neutral
className="p-3 rounded-2xl shadow-sm bg-muted/30 text-foreground"
```

#### Spotlight Variant (Von Restorff Effect - NEW in 2.0)

For the most important metric that needs to stand out:

```tsx
<div className="stat-card stat-card-spotlight">
  {/* Card content */}
</div>
```

CSS Classes:
```css
.stat-card-spotlight {
  @apply relative overflow-hidden;
  background: linear-gradient(135deg, hsl(var(--primary) / 0.08) 0%, transparent 50%);
  border-color: hsl(var(--primary) / 0.25);
}
```

#### Critical Alert State (NEW in 2.0)

For emergency/urgent situations:

```tsx
<div className="stat-card stat-card-critical">
  {/* Card content */}
</div>
```

CSS Animation:
```css
.stat-card-critical {
  animation: critical-pulse 2s ease-in-out infinite;
  border-color: hsl(var(--danger) / 0.4);
}
```

### Goal Progress Bars (NEW in 2.0)

Visual progress toward targets (Goal-Gradient Effect):

```tsx
<div className="stat-card">
  <div className="flex items-start justify-between">
    {/* Value and label */}
    <div>
      <p className="stat-card-value">847</p>
      <p className="stat-card-label">Units Today</p>
    </div>
    {/* Icon */}
    <div className="stat-card-icon bg-primary/10 text-primary">
      <Package className="h-5 w-5" />
    </div>
  </div>
  
  {/* Goal Progress Bar */}
  <div className="mt-4 space-y-1.5">
    <div className="goal-progress-track">
      <div className="goal-progress-fill" style={{ width: '84.7%' }} />
    </div>
    <div className="flex justify-between text-[10px] text-muted-foreground">
      <span>847 / 1000 target</span>
      <span>85%</span>
    </div>
  </div>
</div>
```

### Stat Sections (Miller's Law - NEW in 2.0)

Group related stats into semantic clusters:

```tsx
<section>
  <h3 className="stat-section-label">Production Metrics</h3>
  <div className="grid grid-cols-3 gap-4">
    <StatCard label="Units Today" value="847" icon={Package} />
    <StatCard label="Line Efficiency" value="94.2%" icon={Gauge} />
    <StatCard label="Yield Rate" value="98.7%" icon={Target} />
  </div>
</section>

<section className="mt-8">
  <h3 className="stat-section-label">Quality Indicators</h3>
  <div className="grid grid-cols-3 gap-4">
    <StatCard label="NCRs" value="3" icon={AlertTriangle} />
    <StatCard label="First Pass" value="96.1%" icon={CheckCircle} />
    <StatCard label="Inspections" value="24" icon={ClipboardCheck} />
  </div>
</section>
```

### Content Cards

For larger content sections (tables, charts, forms):

```tsx
<Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium overflow-hidden">
  <CardHeader>
    <CardTitle className="text-xl font-heading font-bold flex items-center gap-2">
      <Icon className="h-5 w-5 text-primary" />
      {title}
    </CardTitle>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
</Card>
```

### Quick Action Items

For navigation links and action buttons in grids:

```tsx
<div 
  className="flex items-center justify-between p-4 rounded-2xl bg-muted/20 border border-border/10 hover:bg-muted/30 transition-colors cursor-pointer"
  onClick={handleClick}
>
  <div className="flex items-center gap-4">
    <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
      <Icon className="h-4 w-4" />
    </div>
    <div>
      <div className="text-sm font-bold">{title}</div>
      <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
        {description}
      </div>
    </div>
  </div>
  <ArrowRight className="h-4 w-4 text-muted-foreground" />
</div>
```

### Page Headers

Standard page header structure:

```tsx
<div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
  <div className="space-y-1">
    <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
      {pageTitle}
    </h1>
    <p className="text-muted-foreground font-medium">
      {pageDescription}
    </p>
  </div>
  <div className="flex items-center gap-3">
    {/* Action buttons */}
  </div>
</div>
```

### Tables

Table styling is handled globally in `globals.css`:

```css
table {
  @apply w-full border-separate border-spacing-0 text-left text-sm;
}
th {
  @apply px-4 py-4 font-heading font-bold text-muted-foreground/60 border-b bg-muted/5 uppercase tracking-widest text-[10px];
}
td {
  @apply px-4 py-4 border-b border-border/20 text-foreground/80 transition-colors;
}
tr {
  @apply transition-all duration-300 hover:bg-primary/5;
}
```

### Buttons

#### Primary Button
```tsx
<Button size="lg" className="rounded-xl shadow-glow subtle-shine">
  <Icon className="h-4 w-4 mr-2" />
  {label}
</Button>
```

#### Outline Button
```tsx
<Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
  <Icon className="h-4 w-4 mr-2" />
  {label}
</Button>
```

### Ambient Status Indicators (NEW in 2.0)

For system health status at a glance:

```tsx
<div className="ambient-status">
  <span className="ambient-status-dot">
    <span className="ambient-status-dot-ping bg-emerald-400" />
    <span className="ambient-status-dot-solid bg-emerald-500" />
  </span>
  <span className="ambient-status-label">All Systems Operational</span>
</div>
```

Status variants:
- **Operational**: `bg-emerald-400/500`
- **Warning**: `bg-amber-400/500`
- **Critical**: `bg-red-400/500`
- **Offline**: `bg-gray-400/500` (no ping animation)

### Confidence Indicators (NEW in 2.0)

For AI/ML prediction transparency:

```tsx
<div className="confidence-indicator">
  <div className="confidence-bar">
    <div className="confidence-fill" style={{ width: '85%' }} />
  </div>
  <span className="confidence-label">85%</span>
</div>
```

Usage with predictions:
```tsx
<div className="flex items-center gap-2">
  <span className="text-2xl font-bold">1,234</span>
  <span className="text-sm text-muted-foreground">predicted units</span>
  <ConfidenceIndicator confidence={85} />
</div>
```

---

## Bento Grid Layouts (NEW in 2.0)

Asymmetric dashboard layouts for visual hierarchy:

```tsx
<div className="bento-grid">
  {/* Large spotlight card - 2x2 */}
  <div className="bento-span-2x2">
    <StatCard spotlight label="OEE" value="87.3%" icon={Gauge} />
  </div>
  
  {/* Standard cards - 1x1 */}
  <StatCard label="Availability" value="92%" icon={Clock} />
  <StatCard label="Performance" value="95%" icon={Zap} />
  <StatCard label="Quality" value="98.2%" icon={Award} />
  <StatCard label="Output" value="1,247" icon={Package} />
  
  {/* Wide card for charts - 2x1 */}
  <div className="bento-span-2x1">
    <ContentCard title="Hourly Output">
      <TrendChart data={hourlyData} />
    </ContentCard>
  </div>
</div>
```

Grid utilities:
```css
.bento-grid {
  @apply grid gap-4;
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: minmax(120px, auto);
}

.bento-span-2x2 { @apply col-span-2 row-span-2; }
.bento-span-2x1 { @apply col-span-2; }
.bento-span-1x2 { @apply row-span-2; }
```

---

## Animation & Transitions

### Standard Transitions

```css
/* Card hover */
transition-all duration-500

/* Quick interactions */
transition-colors

/* Smooth state changes */
transition-all duration-300
```

### Hover Effects

| Effect | Classes |
|--------|---------|
| **Stat Card Lift** | `hover:shadow-premium-hover hover:-translate-y-1` |
| **Table Row** | `hover:bg-primary/5` |
| **Quick Action** | `hover:bg-muted/30` |
| **Button Glow** | `shadow-glow` (defined in Tailwind config) |
| **Critical Pulse** | `animate-critical-pulse` (emergency state) |

### Staggered List Animations (NEW in 2.0)

```tsx
<div className="stagger-list">
  <QuickActionItem icon={Wrench} label="Schedule Maintenance" />
  <QuickActionItem icon={Package} label="New Work Order" />
  <QuickActionItem icon={Users} label="Assign Team" />
</div>
```

CSS:
```css
.stagger-list > * { @apply animate-fade-slide-in; }
.stagger-list > *:nth-child(1) { animation-delay: 0ms; }
.stagger-list > *:nth-child(2) { animation-delay: 50ms; }
.stagger-list > *:nth-child(3) { animation-delay: 100ms; }
.stagger-list > *:nth-child(4) { animation-delay: 150ms; }
```

### Hover Reveal Pattern (NEW in 2.0)

Elements that appear on hover:

```tsx
<button className="group flex items-center justify-between">
  <span>Action Label</span>
  <ChevronRight className="h-4 w-4 hover-reveal" />
</button>
```

CSS:
```css
.hover-reveal {
  @apply opacity-0 -translate-x-2 transition-all duration-300;
}
.group:hover .hover-reveal {
  @apply opacity-100 translate-x-0;
}
```

### Page Animations

```tsx
// Page fade-in
<div className="space-y-8 page-fade-in">
```

Defined in `globals.css`:
```css
.page-fade-in {
  @apply animate-in fade-in duration-700 ease-out;
}
```

---

## Accessibility

### Focus States

All interactive elements have visible focus indicators:

```css
* {
  @apply border-border outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background;
}
```

### Color Contrast

- Body text uses `text-foreground/80` for WCAG AA compliance
- Labels use `text-muted-foreground/60` - ensure sufficient contrast
- Interactive elements must have `:hover` and `:focus` states

### Reduced Motion

Users who prefer reduced motion get subtle alternatives instead of no feedback:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  
  /* Provide subtle feedback via opacity/border instead of movement */
  .stat-card:hover,
  .content-card:hover,
  .quick-action-item:hover {
    transform: none !important;
    opacity: 0.95;
    border-color: hsl(var(--primary) / 0.2);
  }
}
```

---

## Code Examples

### Complete Stat Card Component

```tsx
function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  variant = 'default',
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  trend?: string;
  variant?: 'default' | 'warning' | 'danger' | 'success';
}) {
  const variantStyles = {
    default: 'bg-primary/10 text-primary',
    warning: 'bg-amber-500/10 text-amber-600',
    danger: 'bg-destructive/10 text-destructive',
    success: 'bg-emerald-500/10 text-emerald-600',
  };

  return (
    <Card className="rounded-[2rem] border-border/40 bg-card/40 backdrop-blur-md transition-all duration-500 hover:shadow-premium-hover hover:-translate-y-1">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
              {title}
            </p>
            <p className="text-3xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              {value}
            </p>
            {trend && (
              <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 mt-2">
                {trend}
              </p>
            )}
          </div>
          <div className={`p-4 rounded-2xl shadow-sm ${variantStyles[variant]}`}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Complete Dashboard Page Structure

```tsx
export default function DashboardPage() {
  return (
    <div className="space-y-8 page-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-heading font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
            Dashboard Title
          </h1>
          <p className="text-muted-foreground font-medium">
            Dashboard description text
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="lg" className="rounded-xl border-primary/20 hover:bg-primary/5 text-primary">
            <Filter className="h-4 w-4 mr-2" />
            Filter
          </Button>
          <Button size="lg" className="rounded-xl shadow-glow subtle-shine">
            <Plus className="h-4 w-4 mr-2" />
            Add New
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard title="Metric One" value={42} icon={Activity} variant="default" />
        <StatCard title="Metric Two" value={128} icon={Users} variant="success" />
        <StatCard title="Metric Three" value={7} icon={AlertTriangle} variant="warning" />
        <StatCard title="Metric Four" value={3} icon={XCircle} variant="danger" />
      </div>

      {/* Content Card */}
      <Card className="rounded-[2.5rem] border-border/40 bg-card/40 backdrop-blur-md shadow-premium overflow-hidden">
        <CardHeader>
          <CardTitle className="text-xl font-heading font-bold">
            Main Content
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Table or content */}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Quick action items */}
      </div>
    </div>
  );
}
```

---

## File References

| File | Purpose |
|------|---------|
| `frontend/src/app/globals.css` | CSS custom properties, global styles, component classes |
| `frontend/src/components/ui/stat-card.tsx` | **NEW** Shared StatCard component |
| `frontend/src/components/ui/content-card.tsx` | **NEW** Shared ContentCard, BentoGrid components |
| `frontend/src/components/ui/quick-action.tsx` | **NEW** Shared QuickAction components |
| `frontend/src/components/ui/design-system.tsx` | Token constants, validation utilities |
| `frontend/tailwind.config.ts` | Tailwind theme extensions |
| `frontend/src/app/(dashboard)/hr/page.tsx` | Reference implementation |
| `frontend/src/app/(dashboard)/warehouse/page.tsx` | Reference implementation |

---

## Shared Components (NEW in 2.0)

### StatCard Component

```tsx
import { StatCard, StatSection, AmbientStatus, ConfidenceIndicator } from '@/components/ui/stat-card';

// Basic usage
<StatCard
  value="1,247"
  label="Units Produced"
  icon={Package}
  iconColor="success"
  trend="up"
  trendValue="+12%"
/>

// With goal progress
<StatCard
  value="847"
  label="Daily Target"
  icon={Target}
  goal={{ current: 847, target: 1000 }}
/>

// Spotlight for critical metric
<StatCard
  spotlight
  value="87.3%"
  label="OEE"
  icon={Gauge}
/>

// Critical alert state
<StatCard
  critical
  value="3"
  label="Line Stoppages"
  icon={AlertTriangle}
  iconColor="danger"
/>
```

### QuickAction Component

```tsx
import { QuickActionItem, QuickActionList } from '@/components/ui/quick-action';

<QuickActionList>
  <QuickActionItem
    icon={Wrench}
    label="Schedule Maintenance"
    description="Plan preventive work"
    badge={5}
    onClick={() => {}}
  />
  <QuickActionItem
    icon={Package}
    label="Create Work Order"
    href="/production/new"
    iconColor="success"
  />
</QuickActionList>
```

### ContentCard Component

```tsx
import { ContentCard, BentoGrid, BentoItem, SectionHeader } from '@/components/ui/content-card';

<ContentCard
  title="Recent Orders"
  icon={ShoppingCart}
  action={<Button variant="ghost">View All</Button>}
>
  <Table>...</Table>
</ContentCard>

// Bento layout
<BentoGrid>
  <BentoItem span="2x2">
    <StatCard spotlight value="87%" label="OEE" icon={Gauge} />
  </BentoItem>
  <BentoItem>
    <StatCard value="95%" label="Availability" icon={Clock} />
  </BentoItem>
</BentoGrid>
```

---

## Anti-Patterns to Avoid

| ❌ Don't | ✅ Do |
|---------|-------|
| Icon on the LEFT side of stat cards | Icon on the RIGHT in container |
| `h-4 w-4` icons in stat cards | `h-5 w-5` icons |
| Bare icons without container | Icons in `p-3 rounded-2xl` container |
| `rounded-full` for icon containers | `rounded-2xl` for icon containers |
| `text-sm text-muted-foreground` for labels | `text-[10px] font-bold uppercase tracking-widest` |
| Plain `<Card>` without styling | Full glass-morphism card classes or `.stat-card` |
| Missing hover animations | `hover:shadow-premium-hover hover:-translate-y-1` |
| Too many stats in one row (6+) | Group into sections of 3-4 (Miller's Law) |
| No goal visibility | Add progress bars for targets |
| Same visual weight for all cards | Use spotlight for critical metrics |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Jan 2026 | Goal progress, stat sections, spotlight/critical states, bento grids, shared components |
| 1.0 | Jan 2026 | Initial Sensei Modern specification |

---

*This document is the authoritative source for Sensei Modern styling. All new components and pages must adhere to these patterns.*
