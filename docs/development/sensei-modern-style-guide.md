# Sensei OS Design System: Sensei-Rams (Version 3.0)

> **The authoritative technical specification for Sensei OS frontend architecture.**
> 
> **Version 3.0** - Updated January 2026
> **Philosophy**: "Less, but better" (Dieter Rams) meets High-Precision Industrial Functionalism.

---

## 1. Design Philosophy: Functional Honesty

Sensei OS 3.0 rejects the generic, "soft" aesthetics of modern SaaS (Glassmorphism, blurs, gradients) in favor of **Functional Honesty**. Inspired by Dieter Rams' work at Braun and high-end scientific equipment, the interface is treated as a **Professional Industrial Instrument**.

### The 10 Principles of Sensei-Rams Design

| Principle | Application in Sensei OS |
|-----------|--------------------------|
| **Good design is innovative** | We use cutting-edge tech to simplify complex manufacturing flows. |
| **Good design makes a product useful** | Utility over decoration. Every pixel must serve a functional purpose. |
| **Good design is aesthetic** | Beauty derived from precision, alignment, and neutrality. |
| **Good design makes a product understandable** | The layout explicitly explains the process (The "Process Pipe"). |
| **Good design is unobtrusive** | The UI is a tool, not a distraction. It recedes until needed. |
| **Good design is honest** | No fake depth. No simulated materials. Digital honesty. |
| **Good design is long-lasting** | Neutrality ensures the interface doesn't feel dated in 6 months. |
| **Good design is thorough down to the last detail** | 4px grid alignment is absolute. Kerning is precise. |
| **Good design is environmentally friendly** | Low-energy color palettes and optimized rendering. |
| **Good design is as little design as possible** | If a line can be removed, remove it. |

---

## 2. Typography: The Precision of Print

To eliminate the "blurry/low-res" feel of generic dashboards, Sensei-Rams uses high-fidelity typography engineered for legibility.

### 2.1 Font Stack

| Layer | Font | Characteristics |
|-------|------|-----------------|
| **Body & UI** | `Geist Sans` or `Inter` | High x-height, geometric neutral, crisp rendering. |
| **Data & Metrics** | `JetBrains Mono` | Tabular figures, distinct character shapes, professional. |
| **Labels & System** | `SF Mono` or `Roboto Mono` | For technical metadata and Dymo-style labels. |

### 2.2 Rendering Rules (Anti-Blur Protocol)

All text must adhere to these rendering standards to maintain "High-Res" status:

*   **Subpixel Rendering**: Force `antialiased` with `text-rendering: optimizeLegibility`.
*   **Body Weight**: Body text must use `font-weight: 500` (Medium) to ensure crisp stroke visibility on standard-DPI screens.
*   **Tight Kerning**: Use `tracking-[-0.015em]` for headings and `tracking-[-0.01em]` for body text.
*   **Zero Shadows**: No `text-shadow`. No "glow" on text. Contrast is achieved via value, not effects.

---

## 3. The "Sensei-Rams" Palette: Braun Warm-Grey System

Rejects the blue-tinted "Cool Grey" of tech-SaaS for the functional warmth of industrial hardware.

### 3.1 Core Tokens

| Token | HSL / Hex | Usage |
|-------|-----------|-------|
| `--background` | `#F2F2F2` (240 10% 95%) | The "Chassis" background. Matte, off-white. |
| `--surface-01` | `#E6E6E6` (240 5% 90%) | Primary module background. |
| `--surface-02` | `#D9D9D9` (240 5% 85%) | Inset panels and secondary modules. |
| `--border` | `#CCCCCC` (240 5% 80%) | 1px solid structural lines. |
| `--foreground` | `#1A1A1A` (0 0% 10%) | High-contrast text. |

### 3.2 Functional Accents (The Rams Palette)

| Color | Usage | Principle |
|-------|-------|-----------|
| **Braun Orange** (`#FFBE00`) | Primary Actions | High visibility, mechanical feel. |
| **Functional Green** (`#2D8C3C`) | Healthy / Operational | Semantic, not decorative. |
| **Industrial Red** (`#D62D2D`) | Error / Critical | High urgency, matte finish. |
| **Steel Blue** (`#4A90E2`) | Info / Intelligence | Reserved for AI and ML data layers. |

---

## 4. Structural Layout: The Command Station

The layout is not a "web page" but a **Modular Rack System**.

### 4.1 The "Bezel" Frame
The viewport is surrounded by a fixed 8px inner margin (The Bezel) that contains system metadata:
*   **Bottom Margin**: Displays `STATION_ID`, `SYS_TIME`, and `CONNECTIVITY_STATUS` in 10px Monospace.
*   **Corner Detail**: 4px "Screw Head" SVGs in the four corners of the main viewport frame.

### 4.2 The "Grid of Necessity"
*   **Alignment**: Every element must snap to a **4px baseline grid**.
*   **Zero Shadows**: Depth is created using `border-inset` and `border-outset` effects (1px solid lines) rather than drop shadows.
*   **Module Spacing**: Use `gap-1` (4px) or `gap-0` with shared borders to create a "racked" look.

---

## 5. Component Standards

### 5.1 The "Dymo Tape" Label
Used for high-urgency section headers or identification.
*   **Style**: Solid background (Black or Red), White all-caps text, `font-mono`, slightly skewed (`rotate-[-0.5deg]`).
*   **Purpose**: Mimics physical labels stuck onto a control panel.

### 5.2 Perforated Grilles (Visual Quirk)
*   **Style**: A pattern of 2px circular dots spaced 6px apart in a grid.
*   **Usage**: Used as background for "empty" module slots or as the `grab-handle` area for draggable items.

### 5.3 Mechanical Toggles
*   **Style**: Circular "knobs" on a linear track. 
*   **Feedback**: Animation must be snappy (`duration-100`) with a slight "rebound" to mimic a physical spring.

---

## 6. Visual Management (Lean/TPS)

The interface is an extension of the shop floor's visual management system.

### 6.1 Andon Light Stacks
Persistent system health indicator in the global header.
*   **Visual**: Three vertically stacked circles (Greyed out when inactive).
*   **Logic**:
    *   **Top (Red)**: Critical Abnormalities.
    *   **Middle (Yellow)**: Risks/Priorities.
    *   **Bottom (Green)**: Operational Stability.

### 6.2 Physical Kanban Signals
*   **Visual**: Cards have a "Punch Hole" SVG in the top-right corner.
*   **Data Layout**: Part numbers and quantities are 2x the size of descriptive text to ensure "Glanceability" from 2 meters away.

---

## 7. Anti-Patterns (What to Avoid)

| ❌ Generic SaaS Pattern | ✅ Sensei-Rams Alternative |
|-------------------------|---------------------------|
| Large `rounded-3xl` corners | Sharp or `rounded-sm` (2px - 4px) corners. |
| Glassmorphism / Backdrop Blur | Solid, matte warm-grey surfaces. |
| Soft "Cloud" Shadows | 1px solid borders (`#CCCCCC`). |
| "Floating" Elements | "Slotted" or "Racked" modular components. |
| Plus Jakarta Sans / Bricolage | Geist Sans / Inter / JetBrains Mono. |
| Pulse/Glow effects on buttons | High-contrast color shifts on hover. |

---

## 8. Technical Implementation

### 8.1 Tailwind Configuration Requirements
```typescript
{
  theme: {
    extend: {
      colors: {
        rams: {
          chassis: '#F2F2F2',
          module: '#E6E6E6',
          panel: '#D9D9D9',
          orange: '#FFBE00',
          red: '#D62D2D',
          green: '#2D8C3C',
        }
      },
      borderRadius: {
        'sm': '2px',
        'md': '4px',
      }
    }
  }
}
```

### 8.2 Global CSS Reset
```css
body {
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: var(--rams-chassis);
}
```

---

*This document is the single source of truth for the Sensei OS visual language. Deviation from these principles results in "Visual Debt" and is prohibited.*
