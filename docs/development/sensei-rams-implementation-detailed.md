# Sensei-Rams Implementation Detailed Guide (v3.0)

This document provides the exhaustive technical specification for implementing the **Sensei-Rams Industrial Functionalist** design system. Every developer must follow these implementation patterns to ensure the interface maintains its proprietary "Industrial Instrument" feel and high-precision rendering.

---

## 1. Global Environment & "Industrial Bezel"

The foundational layer of Sensei OS 3.0 is a fixed structural frame that replaces the standard "web page" metaphor with a "Control Station" metaphor.

### 1.1 The Root Layout Bezel
The main viewport is wrapped in a fixed 8px industrial bezel.

**File**: `frontend/src/app/layout.tsx`
```tsx
// Fixed 8px industrial bezel around the viewport
<div className="fixed inset-0 border-[8px] border-rams-chassis pointer-events-none z-[100] hidden md:block" aria-hidden="true" />

// Screw Detail Components (One in each corner)
const ScrewHead = ({ className }: { className: string }) => (
  <div className={cn("fixed z-[101] hidden md:block opacity-30 select-none", className)}>
    <svg width="12" height="12" viewBox="0 0 12 12">
      <circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1" />
      <path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1" />
    </svg>
  </div>
);

// Metadata Footer (Status Bar)
<div className="fixed bottom-0 left-0 right-0 h-8 bg-rams-chassis z-[100] border-t border-rams-border px-6 hidden md:flex items-center justify-between text-[10px] font-mono opacity-60 uppercase tracking-widest">
  <div className="flex gap-6">
    <span>STATION: SENSEI-ALPHA-01</span>
    <span>OS_VER: 3.0.0-RAMS</span>
  </div>
  <div className="flex gap-6 text-right">
    <span>INTEGRITY: OPTIMAL</span>
    <span>LATENCY: 14MS</span>
  </div>
</div>
```

### 1.2 Tactile Texture & Grid Overlay
To remove the "clinical" digital smoothness, a subtle grain overlay and an engineering grid are applied globally.

**CSS Snippet**:
```css
/* Grain Overlay */
.grain-overlay {
  position: fixed;
  inset: 0;
  z-index: -5;
  pointer-events: none;
  opacity: 0.2;
  mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
}

/* Engineering Blueprint Grid (20px) */
.blueprint-grid {
  background-image: radial-gradient(circle, #CCCCCC 0.5px, transparent 0.5px);
  background-size: 20px 20px;
}
```

---

## 2. Layout System: The "Modular Rack"

### 2.1 The Sidebar (Rack Chassis)
The sidebar is not a list; it is a rack of modules.
*   **Navigation Slots**: Each nav item should have a `border-transparent` by default and a `border-rams-orange` or `shadow-[inset_2px_0_0_0_#FFBE00]` when active.
*   **Section Headers**: Use 9px font-black with high letter-spacing (`tracking-[0.25em]`).

### 2.2 The "Process Pipe" Navigation
Instead of breadcrumbs, use a visual connecting line between process stages.

```tsx
<div className="flex items-center gap-0">
  <div className="px-2 py-1 bg-rams-panel border border-rams-border rounded-sm">Step 1</div>
  <div className="h-[2px] w-8 bg-rams-orange/40" /> {/* The "Pipe" */}
  <div className="px-2 py-1 bg-rams-module border border-rams-border rounded-sm">Step 2</div>
</div>
```

---

## 3. Tailwind Configuration: The Braun System

The `tailwind.config.ts` must be locked to these specific values. Do not use generic Tailwind colors (e.g., `slate`, `zinc`).

### 3.1 Colors
```typescript
rams: {
  chassis: '#F2F2F2', // The main off-white background
  module: '#E6E6E6',  // Primary card/sidebar background
  panel: '#D9D9D9',   // Inset panel background
  border: '#CCCCCC',  // Structural 1px lines
  orange: '#FFBE00',  // Braun primary accent
  red: '#D62D2D',     // Industrial matte red
  green: '#2D8C3C',    // Functional green
  steel: '#4A90E2',   // Technical blue
}
```

### 3.2 Borders & Radius
Sensei-Rams uses sharp or micro-rounded corners.
*   **Standard Radius**: `2px` (`rounded-sm`) or `4px` (`rounded-md`).
*   **Zero Radius**: Used for "stacked" modules and grouped buttons.
*   **Shadows**: Replaced by `box-shadow: inset 1px 1px 0 rgba(255,255,255,0.5), inset -1px -1px 0 rgba(0,0,0,0.05)`.

---

## 4. High-Precision Typography Implementation

### 4.1 Tabular Numerals
All numeric data (OEE, Takt Time, Part Counts) **MUST** use tabular figures to prevent horizontal jumping during updates.

**Implementation**:
```tsx
<span className="font-mono tabular-nums tracking-tighter text-3xl font-bold">
  {value}
</span>
```

### 4.2 Labeling (The Dymo Tape Pattern)
Used for critical section headers.

**Tailwind Classes**:
`bg-black text-white px-2 py-0.5 font-mono text-[10px] uppercase font-bold tracking-widest rotate-[-0.5deg] shadow-sm inline-block`

---

## 5. Component Implementation Patterns

### 5.1 Industrial Stat Card (The "Module")
Stat cards should look like physical modules slotted into a rack.

*   **Structure**: 1px solid border (`#CCCCCC`), no shadow, `#E6E6E6` background.
*   **Header**: Small all-caps label with 0.25em tracking.
*   **Metrics**: Large `JetBrains Mono` font.
*   **Quirk**: Add a `perforated-grille` background to a 4px strip at the bottom of the card for "ventilation".

### 5.2 Mechanical Buttons & Toggles
Buttons and toggles must feel tactile and mechanical.

*   **Buttons**: Solid matte background, 1px border.
*   **Toggle Switches**: Use a circular "knob" SVG on a linear track. Avoid rounded-pill sliders.
*   **Active State**: `scale-[0.98]` with `box-shadow: inset 0 2px 4px rgba(0,0,0,0.1)`.
*   **Transition**: `transition-none` for "instant" mechanical response.

### 5.3 Industrial Data Visualization
Data visualization should mimic physical gauges and blueprint markings.

*   **Analog Needle Gauge**: Use for single-value ranges (e.g., Temperature, Speed). Render as a semi-circular arc with 1px tick marks and a needle that rotates on its axis.
*   **Blueprint Annotations**: For highlighting data, use "Red Ink" circles or arrows that appear slightly hand-drawn (use `roughjs` or similar SVG path jitter).
*   **Andon Status Array**: Implementation of the vertical light stack.

```tsx
<div className="flex flex-col gap-1 border border-rams-border p-1 bg-rams-panel">
  <div className={cn("h-3 w-3 rounded-full", active === 'red' ? "bg-rams-red shadow-glow-red" : "bg-black/10")} />
  <div className={cn("h-3 w-3 rounded-full", active === 'yellow' ? "bg-rams-orange shadow-glow-orange" : "bg-black/10")} />
  <div className={cn("h-3 w-3 rounded-full", active === 'green' ? "bg-rams-green shadow-glow-green" : "bg-black/10")} />
</div>
```

---

## 6. Industrial Quirks & Visual Effects

### 6.1 Perforated Grilles
Used for "empty" space or decorative dividers.

```css
.perforated-grille {
  background-image: radial-gradient(circle, #CCCCCC 1px, transparent 1px);
  background-size: 6px 6px;
}
```

### 6.2 Ink Stamps (Approval/Status)
For "Completed" or "Approved" states, use a randomly rotated stamp overlay.

**Classes**:
`border-4 border-rams-red/80 text-rams-red/80 px-4 py-2 font-black uppercase tracking-widest rotate-[-12deg] opacity-60 mix-blend-multiply select-none pointer-events-none`

---

## 7. Accessibility & RTL (Industrial Precision)

### 7.1 Contrast
The Braun Palette is naturally high-contrast (`#1A1A1A` on `#F2F2F2` is > 15:1). Do not use light-grey text for "muted" labels; use 40% opacity of the main foreground color.

### 7.2 RTL Support
The "Industrial Machine" layout should not simply flip.
*   **Monospace Data**: Stays LTR (Numbers are universal in manufacturing).
*   **Mechanical Switches**: The "Throw" direction should remain consistent or be mirrored carefully based on the physical control metaphor.
*   **Bezel Metadata**: Station ID and System Time remain in their respective corners to preserve the "Chassis" layout.

---

## 8. Anti-Blur Rendering Checklist
Before submitting any UI change, verify:
1. [ ] `antialiased` is applied to the body.
2. [ ] `text-rendering: optimizeLegibility` is set.
3. [ ] No fractional pixel values (e.g., `w-[10.5px]`). Use `w-[11px]`.
4. [ ] All borders are solid 1px (no 0.5px hair-lines).
5. [ ] Font-weight for UI text is at least `500`.

---
*End of Specification*
