#!/usr/bin/env python3
"""
Fix SQLAlchemy filter type hints from List[bool] to List[Any].
"""

import re
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_SRC = BASE_DIR / "backend" / "src"


def fix_filter_types(file_path: Path) -> int:
    """Fix filter type hints in a file."""
    content = file_path.read_text(encoding='utf-8')
    original = content
    changes = 0
    
    # Pattern 1: filters: List[bool] = []
    pattern1 = r'\bfilters:\s*List\[bool\]\s*=\s*\[\]'
    if re.search(pattern1, content):
        content = re.sub(pattern1, 'filters: List[Any] = []', content)
        changes += len(re.findall(pattern1, original))
    
    # Pattern 2: filters: list[bool] = []
    pattern2 = r'\bfilters:\s*list\[bool\]\s*=\s*\[\]'
    if re.search(pattern2, content):
        content = re.sub(pattern2, 'filters: list[Any] = []', content)
        changes += len(re.findall(pattern2, original))
    
    # If we made changes, ensure Any is imported
    if changes > 0 and content != original:
        # Check if Any is already imported
        has_any_import = bool(re.search(r'from typing import.*\bAny\b', content))
        
        if not has_any_import:
            # Try to add Any to existing typing import
            def add_any_to_import(match):
                imports = match.group(1)
                # Check if Any is already there (shouldn't be, but double-check)
                if 'Any' in imports:
                    return match.group(0)
                # Add Any to the list
                # Handle both single-line and multi-line imports
                if '(' in imports:  # Multi-line import
                    # Find last import before closing paren
                    imports = imports.replace(')', ', Any)')
                else:  # Single-line import
                    imports = imports.rstrip() + ', Any'
                return f'from typing import {imports}'
            
            # Try to find and update typing import
            typing_pattern = r'from typing import ([^;\n]+)'
            if re.search(typing_pattern, content):
                content = re.sub(typing_pattern, add_any_to_import, content, count=1)
            else:
                # No typing import found, add one at the top after module docstring
                # Find first non-docstring, non-comment line
                lines = content.split('\n')
                insert_index = 0
                in_docstring = False
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        if not in_docstring:
                            in_docstring = True
                            if stripped.endswith('"""') or stripped.endswith("'''"):
                                in_docstring = False
                        else:
                            in_docstring = False
                    elif not in_docstring and not stripped.startswith('#') and stripped:
                        insert_index = i
                        break
                
                lines.insert(insert_index, 'from typing import Any')
                content = '\n'.join(lines)
    
    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return changes
    
    return 0


def main():
    """Main execution."""
    print("=" * 80)
    print("SQLAlchemy Filter Type Fixer")
    print("=" * 80)
    print()
    
    # Find all Python files in API endpoints and services
    api_dir = BACKEND_SRC / "sensei" / "api"
    services_dir = BACKEND_SRC / "sensei" / "services"
    
    python_files = []
    if api_dir.exists():
        python_files.extend(api_dir.rglob("*.py"))
    if services_dir.exists():
        python_files.extend(services_dir.rglob("*.py"))
    
    print(f"Found {len(python_files)} Python files to check")
    print()
    
    total_changes = 0
    files_modified = 0
    
    print("Processing files...")
    print("-" * 80)
    
    for file_path in sorted(python_files):
        if file_path.name == "__init__.py":
            continue
            
        changes = fix_filter_types(file_path)
        
        if changes > 0:
            print(f"  ✓ Fixed {changes} filter types in {file_path.relative_to(BASE_DIR)}")
            total_changes += changes
            files_modified += 1
    
    print("-" * 80)
    print(f"\nSummary:")
    print(f"  Files modified: {files_modified}")
    print(f"  Total changes: {total_changes}")
    print()
    
    if total_changes > 0:
        print("✓ SQLAlchemy filter types fixed!")
    else:
        print("⚠ No changes needed.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
