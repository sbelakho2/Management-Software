#!/usr/bin/env python3
"""Add accessibility attributes to clickable table rows across dashboard pages.

Adds: role="link", tabIndex={0}, and onKeyDown handler for Enter/Space
to all <tr> elements that have onClick={() => router.push(...)}
"""
import re
import sys

files = [
    "frontend/src/app/(dashboard)/(shop-floor)/quality/page.tsx",
    "frontend/src/app/(dashboard)/hr/page.tsx",
    "frontend/src/app/(dashboard)/(shop-floor)/production/page.tsx",
    "frontend/src/app/(dashboard)/(shop-floor)/maintenance/page.tsx",
    "frontend/src/app/(dashboard)/(shop-floor)/training/page.tsx",
]

total_fixed = 0

for filepath in files:
    try:
        with open(filepath) as f:
            content = f.read()
    except FileNotFoundError:
        print(f"  SKIP: {filepath} not found")
        continue

    # Check if import already exists
    has_import = "clickableRow" in content

    # Pattern: <tr ...onClick={() => router.push(...)} ...>
    # We need to add: role="link" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); router.push(...); } }}
    
    # Match <tr with onClick that contains router.push
    pattern = r'(<tr\s+[^>]*?)onClick=\{?\(\)\s*=>\s*router\.push\(`([^`]+)`\)\}?'
    
    def replace_tr(m):
        prefix = m.group(0)
        route = m.group(2)
        # Check if already has role attribute
        if 'role=' in m.group(1):
            return prefix
        # Add accessibility attributes
        return (
            m.group(1) + 
            'role="link"\n'
            '                      tabIndex={0}\n'
            f'                      onKeyDown={{(e) => {{ if (e.key === "Enter" || e.key === " ") {{ e.preventDefault(); router.push(`{route}`); }} }}}}\n'
            f'                      onClick={{() => router.push(`{route}`)}}'
        )

    new_content, count = re.subn(pattern, replace_tr, content)
    
    if count > 0:
        # Also add aria-label to action buttons that use MoreHorizontal icon
        # Pattern: <Button variant="ghost" size="icon-sm">
        #            <MoreHorizontal .../>
        # Add aria-label="Actions"
        more_pattern = r'(<Button\s+variant="ghost"\s+size="icon-sm")(>)\s*\n(\s*<MoreHorizontal)'
        def add_aria_label(m):
            if 'aria-label' in m.group(1):
                return m.group(0)
            return m.group(1) + ' aria-label="Actions"' + m.group(2) + '\n' + m.group(3)
        
        new_content, label_count = re.subn(more_pattern, add_aria_label, new_content)
        
        with open(filepath, "w") as f:
            f.write(new_content)
        
        total_fixed += count
        print(f"  {filepath}: {count} clickable rows fixed, {label_count} action buttons labeled")
    else:
        print(f"  {filepath}: no clickable rows found")

print(f"\nTotal: {total_fixed} rows made accessible")
