# Page Component Co-location Pattern

## Recommended: `_components/` Directory

Large page files should extract reusable sub-components into a `_components/`
directory co-located with the page file. This pattern is already used by the
**Today** page and should be adopted across the codebase.

### Reference Implementation

```
src/app/(dashboard)/today/
  page.tsx                          # Main page composition
  _components/
    my-work-dashboard.tsx           # Work queue dashboard
    drill-answer-modal.tsx          # Drill practice modal
    sensei-pulse.tsx                # AI pulse indicator
    shift-handover-card.tsx         # Shift handover summary
```

### When to Extract

- Page file exceeds **400 lines**
- Component is only used by that page (not shared)
- Component has its own state management or data fetching
- Component is independently testable

### How to Extract

1. Create `_components/` directory next to `page.tsx`
2. Move component to a new file with kebab-case naming
3. Import in `page.tsx` with relative path: `from './_components/my-component'`
4. The `_` prefix prevents Next.js from treating the directory as a route segment

### Pages That Would Benefit

| Page | Lines | Suggested Extractions |
|------|-------|-----------------------|
| `hr/page.tsx` | ~1480 | Employee table, recruitment pipeline, training matrix |
| `warehouse/page.tsx` | ~500+ | Inventory table, receiving form, shipping table |
| `finance/page.tsx` | ~400+ | GL table, AP/AR views, budget chart |
| `executive/page.tsx` | ~450 | NL2SQL interface, risk analysis form |
| `maintenance/page.tsx` | ~500+ | Asset tree, work order table |

### Shared Components

Components used across multiple pages go in `src/components/ui/` or
`src/components/layout/` — NOT in `_components/`.
