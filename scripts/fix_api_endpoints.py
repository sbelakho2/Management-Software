#!/usr/bin/env python3
"""
Fix API endpoint type annotations.
Changes `current_user = Depends(...)` to `current_user: User = Depends(...)`
and `db = Depends(...)` to `db: AsyncSession = Depends(...)`
"""

import re
from pathlib import Path
import sys

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_SRC = BASE_DIR / "backend" / "src"


def fix_api_endpoint_file(file_path: Path) -> int:
    """Fix type annotations in a single API endpoint file."""
    
    content = file_path.read_text(encoding='utf-8')
    original = content
    changes = 0
    
    # Pattern 1: Fix `current_user = Depends(get_current_user)`
    # Need to check if already has type annotation
    pattern1 = r'(\n\s+)(current_user)\s*=\s*(Depends\(get_current_user\))'
    
    def replace_current_user(match):
        nonlocal changes
        indent = match.group(1)
        # Check if already has type annotation by looking backward
        # This is simple - just add the type hint
        changes += 1
        return f'{indent}current_user: User = {match.group(3)}'
    
    # Only replace if not already typed
    if 'current_user = Depends(get_current_user)' in content and \
       'current_user: User' not in content:
        content = re.sub(pattern1, replace_current_user, content)
    
    # Pattern 2: Fix `db = Depends(get_db)` or `db = Depends(get_async_session)`
    pattern2 = r'(\n\s+)(db)\s*=\s*(Depends\(get_(?:db|async_session)\))'
    
    def replace_db(match):
        nonlocal changes
        indent = match.group(1)
        changes += 1
        return f'{indent}db: AsyncSession = {match.group(3)}'
    
    if ('db = Depends(get_db)' in content or 'db = Depends(get_async_session)' in content) and \
       'db: AsyncSession' not in content:
        content = re.sub(pattern2, replace_db, content)
    
    # Pattern 3: Look for CurrentUser/DBSession imports and use them if present
    # If file uses CurrentUser type alias, don't change it
    if 'from sensei.api.deps import CurrentUser' in content:
        # File already uses proper type alias, skip
        pass
    else:
        # Need to add import if we made changes
        if changes > 0 and 'from sensei.models.user import User' not in content:
            # Add User import after existing imports
            import_pattern = r'(from sensei\.api\.deps import.*)'
            if re.search(import_pattern, content):
                content = re.sub(
                    import_pattern,
                    lambda m: f'{m.group(1)}\nfrom sensei.models.user import User',
                    content,
                    count=1
                )
            
        if changes > 0 and 'from sqlalchemy.ext.asyncio import AsyncSession' not in content:
            # Add AsyncSession import
            import_pattern = r'(from sqlalchemy(?:\.ext\.asyncio)? import.*)'
            if re.search(import_pattern, content):
                # Check if we need to add it
                content = re.sub(
                    r'(from sqlalchemy import.*)',
                    lambda m: f'{m.group(1)}\nfrom sqlalchemy.ext.asyncio import AsyncSession',
                    content,
                    count=1
                )
    
    # Only write if changed
    if content != original:
        file_path.write_text(content, encoding='utf-8')
        print(f"  ✓ Fixed {changes} annotations in {file_path.relative_to(BASE_DIR)}")
        return changes
    
    return 0


def fix_sql_alchemy_filters(file_path: Path) -> int:
    """Fix SQLAlchemy filter type hints from List[bool] to List[Any]."""
    
    content = file_path.read_text(encoding='utf-8')
    original = content
    changes = 0
    
    # Pattern: filters: List[bool] = []
    pattern = r'filters:\s*List\[bool\]\s*=\s*\[\]'
    replacement = 'filters: List[Any] = []'
    
    new_content = re.sub(pattern, replacement, content)
    if new_content != content:
        changes = len(re.findall(pattern, content))
        content = new_content
        
        # Ensure 'Any' is imported
        if 'from typing import' in content and ', Any' not in content and 'Any' not in content:
            content = re.sub(
                r'from typing import ([^)]+)',
                lambda m: f'from typing import {m.group(1)}, Any' if 'Any' not in m.group(1) else m.group(0),
                content,
                count=1
            )
    
    if content != original:
        file_path.write_text(content, encoding='utf-8')
        print(f"  ✓ Fixed {changes} filter type hints in {file_path.relative_to(BASE_DIR)}")
        return changes
    
    return 0


def main():
    """Main execution."""
    
    print("=" * 80)
    print("API Endpoint Type Annotation Fixer")
    print("=" * 80)
    print()
    
    # Find all API endpoint files
    api_endpoints_dir = BACKEND_SRC / "sensei" / "api" / "v1" / "endpoints"
    
    if not api_endpoints_dir.exists():
        print(f"ERROR: API endpoints directory not found: {api_endpoints_dir}")
        sys.exit(1)
    
    python_files = list(api_endpoints_dir.glob("*.py"))
    print(f"Found {len(python_files)} Python files in {api_endpoints_dir.relative_to(BASE_DIR)}")
    print()
    
    total_changes = 0
    files_modified = 0
    
    print("Processing files...")
    print("-" * 80)
    
    for file_path in sorted(python_files):
        if file_path.name == "__init__.py":
            continue
            
        changes = fix_api_endpoint_file(file_path)
        filter_changes = fix_sql_alchemy_filters(file_path)
        
        if changes > 0 or filter_changes > 0:
            total_changes += changes + filter_changes
            files_modified += 1
    
    print("-" * 80)
    print(f"\nSummary:")
    print(f"  Files modified: {files_modified}")
    print(f"  Total changes: {total_changes}")
    print()
    
    if total_changes > 0:
        print("✓ API endpoint type annotations fixed!")
        print("  Run 'mypy' again to verify fixes.")
    else:
        print("⚠ No changes made. Patterns may not match or files already fixed.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
