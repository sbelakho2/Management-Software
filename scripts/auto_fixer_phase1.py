#!/usr/bin/env python3
"""
Automated fixer for common mypy errors
This script will systematically fix the most common patterns
"""

import re
from pathlib import Path
from typing import Dict, List, Set
import subprocess

# Track all changes
changes_made = []

def add_missing_import(file_path: str, import_line: str, after_line: str = None):
    """Add a missing import to a file"""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Check if import already exists
    if any(import_line.strip() in line for line in lines):
        return False
    
    # Find where to insert (after other imports or after docstring)
    insert_idx = 0
    in_docstring = False
    for i, line in enumerate(lines):
        if '"""' in line:
            in_docstring = not in_docstring
        if not in_docstring and (line.startswith('from ') or line.startswith('import ')):
            insert_idx = i + 1
    
    lines.insert(insert_idx, import_line + '\n')
    
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    changes_made.append(f"Added import to {file_path}: {import_line}")
    return True

def fix_auth_settings_import():
    """Fix missing settings import in auth.py"""
    file_path = "backend/src/sensei/api/v1/endpoints/auth.py"
    import_line = "from sensei.core.config import settings"
    add_missing_import(file_path, import_line)

def fix_document_intelligence_duplicate_return():
    """Fix duplicate return statement in document_intelligence.py"""
    file_path = "backend/src/sensei/services/ai/document_intelligence.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove the erroneous duplicate return after _default_table
    # Lines 843-850 have an unreachable return statement with undefined variables
    pattern = r'(def _default_table.*?confidence=0\.50,\s*\)\s*)\n\s*return ExtractedTable\([^)]*table_bbox[^)]*\)'
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, r'\1', content, flags=re.DOTALL)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        changes_made.append(f"Fixed duplicate return in {file_path}")
        return True
    
    return False

def fix_missing_any_import():
    """Fix missing 'Any' import in files that use it"""
    # qms_quality.py line 1432
    file_path = "backend/src/sensei/services/quality/qms_quality.py"
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Check if Any is used but not imported
    uses_any = any('Any' in line and 'import Any' not in line for line in lines)
    has_typing_import = any('from typing import' in line for line in lines)
    
    if uses_any:
        for i, line in enumerate(lines):
            if 'from typing import' in line and 'Any' not in line:
                # Add Any to existing typing import
                lines[i] = line.rstrip().rstrip(')') + ', Any)\n' if line.rstrip().endswith(')') else line.rstrip() + ', Any\n'
                
                with open(file_path, 'w') as f:
                    f.writelines(lines)
                
                changes_made.append(f"Added 'Any' to typing imports in {file_path}")
                return True
    
    return False

def fix_ai_reasoning_imports():
    """Fix missing imports in ai_reasoning.py"""
    file_path = "backend/src/sensei/services/ai/ai_reasoning.py"
    
    # Add Any import
    add_missing_import(file_path, "from typing import Any")
    
    # Note: SearchResult and SearchChunk might need to be defined or imported from elsewhere
    # This needs manual investigation
    changes_made.append(f"MANUAL: Check SearchResult and SearchChunk in {file_path}")

def fix_visual_quality_undefined_uuid():
    """Fix undefined UUID in visual_quality_inspection.py"""
    file_path = "backend/src/sensei/services/ai/visual_quality_inspection.py"
    add_missing_import(file_path, "from uuid import UUID")

def fix_smart_ingestion_undefined():
    """Fix undefined variables in smart_ingestion.py"""
    # This needs manual investigation - variables might be typos or logic errors
    changes_made.append(f"MANUAL: Check undefined variables in backend/src/sensei/services/smart_ingestion.py")

def main():
    print("Starting automated fixes...")
    print("="*80)
    
    # Phase 1: Fix critical undefined variables/imports
    print("\nPhase 1: Fixing critical undefined variables and missing imports...")
    fix_auth_settings_import()
    fix_document_intelligence_duplicate_return()
    fix_missing_any_import()
    fix_ai_reasoning_imports()
    fix_visual_quality_undefined_uuid()
    fix_smart_ingestion_undefined()
    
    print(f"\nTotal automated changes: {len([c for c in changes_made if not c.startswith('MANUAL')])}")
    print(f"Manual review needed: {len([c for c in changes_made if c.startswith('MANUAL')])}")
    
    print("\n" + "="*80)
    print("Changes Made:")
    print("="*80)
    for change in changes_made:
        print(f"  - {change}")
    
    print("\n" + "="*80)
    print("Next Steps:")
    print("="*80)
    print("1. Review the automated changes")
    print("2. Address manual review items")
    print("3. Continue with Phase 2 fixes (model attributes)")
    print("4. Run mypy again to verify")

if __name__ == '__main__':
    main()
