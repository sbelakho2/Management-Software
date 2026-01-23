#!/usr/bin/env python3
"""
Comprehensive Multi-Phase Auto-Fixer
Handles the 1907 mypy errors systematically

This is a LARGE-scale codebase repair that requires:
1. Understanding the data model layer
2. Fixing base classes
3. Fixing API layer type inference
4. Fixing service layer model usage
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
import sys

changes = []

# ============================================================================
# Phase 2: Fix Model Base Classes
# ============================================================================

def add_mixin_attributes_to_base():
    """
    The main issue is that ModelT (generic type variable) doesn't know about
    SoftDeleteMixin attributes. We need to ensure the base classes properly
    define these attributes for type checkers.
    """
    base_file = "backend/src/sensei/models/base.py"
    
    with open(base_file, 'r') as f:
        content = f.read()
    
    # Check if SoftDeleteMixin has proper type annotations
    if 'class SoftDeleteMixin' in content:
        # Ensure deleted_at is properly typed
        if 'deleted_at: Mapped[Optional[datetime]]' not in content and 'deleted_at = Column' in content:
            # The mixin needs proper type hints
            content = content.replace(
                'class SoftDeleteMixin:',
                'class SoftDeleteMixin:\n    """Mixin for soft delete functionality"""\n    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)'
            )
            changes.append("Updated SoftDeleteMixin with type hints in base.py")
    
    with open(base_file, 'w') as f:
        f.write(content)

# ============================================================================
# Phase 3: Fix API Endpoint Type Annotations
# ============================================================================

def fix_api_current_user_annotations():
    """
    The 'object.id' errors are because FastAPI's Depends() returns 'object' type.
    We need to add proper type annotations to route handlers.
    """
    
    # Pattern: def some_route(..., current_user = Depends(get_current_user))
    # Should be: def some_route(..., current_user: User = Depends(get_current_user))
    
    api_files = list(Path("backend/src/sensei/api/v1/endpoints").glob("*.py"))
    
    for file_path in api_files:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Fix: current_user = Depends -> current_user: User = Depends
        content = re.sub(
            r'(\s+current_user)\s*=\s*Depends\(get_current_user\)',
            r'\1: User = Depends(get_current_user)',
            content
        )
        
        # Fix: db = Depends -> db: AsyncSession = Depends
        content = re.sub(
            r'(\s+db)\s*=\s*Depends\(get_db\)',
            r'\1: AsyncSession = Depends(get_db)',
            content
        )
        
        if content != original_content:
            # Make sure imports are present
            if ': User' in content and 'from sensei.models.user import User' not in content:
                # Add import after other model imports
                content = re.sub(
                    r'(from sensei\.models\.[a-z_]+ import [^\n]+\n)',
                    r'\1from sensei.models.user import User\n',
                    content,
                    count=1
                )
            
            if ': AsyncSession' in content and 'from sqlalchemy.ext.asyncio import AsyncSession' not in content:
                content = re.sub(
                    r'(from sqlalchemy[^\n]*\n)',
                    r'\1from sqlalchemy.ext.asyncio import AsyncSession\n',
                    content,
                    count=1
                )
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            changes.append(f"Fixed type annotations in {file_path.name}")

# ============================================================================
# Phase 4: Fix SQLAlchemy Query Type Issues
# ============================================================================

def fix_sqlalchemy_and_bool_filters():
    """
    Fix issues where plain 'bool' is being passed to and_() which expects ColumnElement
    This happens when building dynamic filters.
    """
    
    api_files = list(Path("backend/src/sensei/api/v1/endpoints").glob("*.py"))
    
    for file_path in api_files:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern: filters.append(SomeModel.field == value)
        # Then: query = query.where(and_(*filters))
        # Problem: filters is List[bool] not List[ColumnElement]
        
        # Fix by changing filter list type hint
        content = re.sub(
            r'filters:\s*list\[bool\]\s*=\s*\[\]',
            r'filters: List[Any] = []  # SQLAlchemy filter expressions',
            content
        )
        
        content = re.sub(
            r'filters:\s*List\[bool\]\s*=\s*\[\]',
            r'filters: List[Any] = []  # SQLAlchemy filter expressions',
            content
        )
        
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            
            changes.append(f"Fixed filter type hints in {file_path.name}")

# ============================================================================
# Main Execution
# ============================================================================

def main():
    print("="*80)
    print("PHASE 2: Comprehensive Auto-Fixer")
    print("="*80)
    print("")
    print("This will fix:")
    print("  - Model base class annotations")
    print("  - API endpoint type annotations") 
    print("  - SQLAlchemy query filter types")
    print("")
    print("Starting fixes...")
    print("-"*80)
    
    try:
        add_mixin_attributes_to_base()
        print("✓ Phase 2.1: Fixed model base classes")
        
        fix_api_current_user_annotations()
        print(f"✓ Phase 2.2: Fixed API endpoint annotations ({len([c for c in changes if 'annotations in' in c])} files)")
        
        fix_sqlalchemy_and_bool_filters()
        print(f"✓ Phase 2.3: Fixed SQLAlchemy filter types ({len([c for c in changes if 'filter type' in c])} files)")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("-"*80)
    print(f"\nTotal changes made: {len(changes)}")
    
    if changes:
        print("\nDetailed changes:")
        for change in changes[:20]:  # Show first 20
            print(f"  • {change}")
        if len(changes) > 20:
            print(f"  ... and {len(changes) - 20} more")
    
    print("\n" + "="*80)
    print("Phase 2 Complete!")
    print("="*80)
    print("\nNext: Run mypy again to see remaining errors")
    print("Command: python -m mypy backend/src/sensei --show-error-codes | grep 'Found.*errors'")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
