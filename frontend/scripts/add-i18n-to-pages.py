#!/usr/bin/env python3
"""
Script to add i18n support to all page.tsx files in the frontend.
This adds useI18n import and replaces hardcoded strings with t() calls.
"""

import os
import re
import json
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent.parent
PAGES_DIR = FRONTEND_DIR / "src" / "app"

# Common patterns to replace
HARDCODED_PATTERNS = {
    # Page titles and headers
    r'"([A-Z][a-z]+ [A-Z][a-z]+)"': lambda m: f't("pages.{m.group(1).lower().replace(" ", "_")}.title") || "{m.group(1)}"',
    # Button labels
    r'>Save<': '>{{t("common.save") || "Save"}}<',
    r'>Cancel<': '>{{t("common.cancel") || "Cancel"}}<',
    r'>Delete<': '>{{t("common.delete") || "Delete"}}<',
    r'>Edit<': '>{{t("common.edit") || "Edit"}}<',
    r'>Create<': '>{{t("common.create") || "Create"}}<',
    r'>Add<': '>{{t("common.add") || "Add"}}<',
    r'>Remove<': '>{{t("common.remove") || "Remove"}}<',
    r'>Search<': '>{{t("common.search") || "Search"}}<',
    r'>Filter<': '>{{t("common.filter") || "Filter"}}<',
    r'>Clear<': '>{{t("common.clear") || "Clear"}}<',
    r'>Close<': '>{{t("common.close") || "Close"}}<',
    r'>Back<': '>{{t("common.back") || "Back"}}<',
    r'>Next<': '>{{t("common.next") || "Next"}}<',
    r'>Submit<': '>{{t("common.submit") || "Submit"}}<',
    r'>Export<': '>{{t("common.export") || "Export"}}<',
    r'>Import<': '>{{t("common.import") || "Import"}}<',
}

def find_all_pages():
    """Find all page.tsx files in the app directory."""
    pages = []
    for root, dirs, files in os.walk(PAGES_DIR):
        for file in files:
            if file == "page.tsx":
                pages.append(Path(root) / file)
    return pages

def has_i18n_import(content: str) -> bool:
    """Check if the file already imports useI18n."""
    return "useI18n" in content

def add_i18n_import(content: str) -> str:
    """Add useI18n import if not present."""
    if has_i18n_import(content):
        return content
    
    # Find the last import statement
    import_pattern = r"(import .+ from ['\"][^'\"]+['\"];?\n)(?!import)"
    matches = list(re.finditer(import_pattern, content))
    
    if matches:
        last_import = matches[-1]
        insert_pos = last_import.end()
        import_line = "import { useI18n } from '@/contexts/i18n-context';\n"
        content = content[:insert_pos] + import_line + content[insert_pos:]
    
    return content

def add_t_hook(content: str) -> str:
    """Add const { t } = useI18n() hook if not present."""
    if "const { t }" in content or "{ t }" in content:
        return content
    
    # Find the function component and add the hook
    patterns = [
        r"(export default function \w+\([^)]*\) \{)",
        r"(export function \w+\([^)]*\) \{)",
        r"(function \w+\([^)]*\) \{)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            insert_pos = match.end()
            hook_line = "\n  const { t } = useI18n();"
            content = content[:insert_pos] + hook_line + content[insert_pos:]
            break
    
    return content

def process_page(page_path: Path) -> tuple[bool, str]:
    """Process a single page file and add i18n support."""
    with open(page_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Skip if it's a 'use client' component without proper structure
    if "'use client'" not in content and '"use client"' not in content:
        return False, "Not a client component"
    
    # Add import
    content = add_i18n_import(content)
    
    # Add hook
    content = add_t_hook(content)
    
    # Check if content changed
    if content != original_content:
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, "Updated"
    
    return False, "Already has i18n"

def main():
    pages = find_all_pages()
    print(f"Found {len(pages)} page.tsx files")
    
    updated = 0
    skipped = 0
    
    for page in sorted(pages):
        rel_path = page.relative_to(FRONTEND_DIR)
        changed, reason = process_page(page)
        if changed:
            print(f"✓ Updated: {rel_path}")
            updated += 1
        else:
            print(f"- Skipped: {rel_path} ({reason})")
            skipped += 1
    
    print(f"\nSummary: {updated} updated, {skipped} skipped")

if __name__ == "__main__":
    main()
