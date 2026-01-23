#!/usr/bin/env python3
"""
Comprehensive error analysis and categorization script
"""
import re
from collections import defaultdict
from pathlib import Path

def parse_full_report():
    """Parse the FULL_AUDIT_REPORT.md and categorize all errors"""
    
    errors = []
    current_file = None
    
    with open('FULL_AUDIT_REPORT.md', 'r') as f:
        for line in f:
            # Match file headers
            if line.startswith('### `backend/'):
                current_file = line.strip().replace('### `', '').replace('`', '')
                continue
            
            # Match error lines in table
            if current_file and line.startswith('| ') and not line.startswith('| Line'):
                parts = line.split('|')
                if len(parts) >= 3:
                    try:
                        line_num = parts[1].strip()
                        message = parts[2].strip().replace('`', '')
                        
                        # Extract error code
                        code_match = re.search(r'\[([a-z-]+)\]$', message)
                        error_code = code_match.group(1) if code_match else 'unknown'
                        
                        errors.append({
                            'file': current_file,
                            'line': line_num,
                            'message': message,
                            'code': error_code
                        })
                    except:
                        pass
    
    return errors

def categorize_errors(errors):
    """Categorize errors by type and priority"""
    
    categories = {
        'attr-defined': [],  # Missing attributes
        'call-arg': [],      # Function signature mismatch
        'arg-type': [],      # Argument type mismatch
        'assignment': [],    # Assignment type mismatch
        'import-untyped': [],# Missing type stubs
        'name-defined': [],  # Undefined variables (CRITICAL)
        'import-not-found': [], # Missing imports (CRITICAL)
        'operator': [],      # Operator type issues
        'misc': [],          # Miscellaneous
        'other': []          # Everything else
    }
    
    for error in errors:
        code = error['code']
        if code in categories:
            categories[code].append(error)
        else:
            categories['other'].append(error)
    
    return categories

def analyze_attr_defined_errors(errors):
    """Analyze attr-defined errors to find patterns"""
    patterns = defaultdict(list)
    
    for err in errors:
        msg = err['message']
        
        # Extract the missing attribute
        if 'has no attribute' in msg:
            match = re.search(r'"([^"]+)" has no attribute "([^"]+)"', msg)
            if match:
                class_name = match.group(1)
                attr_name = match.group(2)
                patterns[f"{class_name}.{attr_name}"].append(err)
    
    return patterns

def analyze_call_arg_errors(errors):
    """Analyze call-arg errors"""
    patterns = defaultdict(list)
    
    for err in errors:
        msg = err['message']
        
        # Extract function being called
        if 'Unexpected keyword argument' in msg or 'Too many arguments' in msg:
            patterns['signature_mismatch'].append(err)
        elif 'Missing positional argument' in msg:
            patterns['missing_args'].append(err)
    
    return patterns

def main():
    print("Parsing FULL_AUDIT_REPORT.md...")
    errors = parse_full_report()
    print(f"Total errors parsed: {len(errors)}")
    
    print("\nCategorizing errors...")
    categories = categorize_errors(errors)
    
    print("\n" + "="*80)
    print("ERROR BREAKDOWN BY CATEGORY")
    print("="*80)
    
    for category, error_list in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        if error_list:
            print(f"\n{category.upper()}: {len(error_list)} errors")
            
            if category == 'attr-defined' and len(error_list) > 0:
                patterns = analyze_attr_defined_errors(error_list)
                print("\n  Top missing attributes:")
                for pattern, errs in sorted(patterns.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
                    print(f"    {pattern}: {len(errs)} occurrences")
            
            if category == 'call-arg' and len(error_list) > 0:
                patterns = analyze_call_arg_errors(error_list)
                print("\n  Breakdown:")
                for pattern, errs in patterns.items():
                    print(f"    {pattern}: {len(errs)} errors")
    
    print("\n" + "="*80)
    print("FILES WITH MOST ERRORS")
    print("="*80)
    
    files_errors = defaultdict(int)
    for err in errors:
        files_errors[err['file']] += 1
    
    for file, count in sorted(files_errors.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {count:4d}  {file}")
    
    # Generate priority fix list
    print("\n" + "="*80)
    print("PRIORITY FIX ORDER")
    print("="*80)
    
    print("\n1. CRITICAL - Undefined Variables/Imports (Will cause runtime crashes):")
    critical = categories['name-defined'] + categories['import-not-found']
    critical_files = set(e['file'] for e in critical)
    for f in sorted(critical_files):
        count = sum(1 for e in critical if e['file'] == f)
        print(f"   - {f} ({count} errors)")
    
    print("\n2. HIGH - Model Attribute Issues (Most common, ~513 errors):")
    attr_files = defaultdict(int)
    for err in categories['attr-defined']:
        attr_files[err['file']] += 1
    for file, count in sorted(attr_files.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   - {file} ({count} errors)")
    
    print("\n3. HIGH - Function Signature Mismatches (~282 errors):")
    call_files = defaultdict(int)
    for err in categories['call-arg']:
        call_files[err['file']] += 1
    for file, count in sorted(call_files.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   - {file} ({count} errors)")

if __name__ == '__main__':
    main()
