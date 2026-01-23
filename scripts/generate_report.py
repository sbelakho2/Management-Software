
import os
import re
from collections import defaultdict
from datetime import datetime

def parse_errors(log_file):
    errors_by_file = defaultdict(list)
    total_errors = 0
    
    # Regex to match mypy output: file:line: error: message [code]
    # Example: backend/src/sensei/services/ops/today_screen_v2/shop_floor.py:92: error: "WorkOrderAtRisk" has no attribute "days_until_due"  [attr-defined]
    pattern = re.compile(r'^([^:]+):(\d+): error: (.+)$')

    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            match = pattern.match(line)
            if match:
                file_path = match.group(1)
                line_num = match.group(2)
                message = match.group(3)
                
                errors_by_file[file_path].append({
                    'line': line_num,
                    'message': message
                })
                total_errors += 1
            elif "Found" in line and "errors in" in line:
                # Summary line at the bottom
                pass
            else:
                # Capture continuation lines or other output if needed, 
                # but for now we focus on the error lines.
                pass
                
    return errors_by_file, total_errors

def generate_markdown(errors_by_file, total_errors, output_file):
    with open(output_file, 'w') as f:
        f.write(f"# Sensei OS - Full Backend Audit Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Errors Found:** {total_errors}\n")
        f.write(f"**Files Affected:** {len(errors_by_file)}\n\n")
        
        f.write("## Executive Summary\n")
        f.write("This report details critical wiring issues found during the static analysis audit of the backend codebase. ")
        f.write("The primary issues found are `[attr-defined]` (attributes missing on classes) and `[call-arg]` (incorrect function signatures). ")
        f.write("These indicate a mismatch between the Data Models/SQLAlchemy schemas and the Service layer business logic.\n\n")
        
        f.write("## Detailed Error Log by File\n\n")
        
        # Sort files alphabetically
        sorted_files = sorted(errors_by_file.keys())
        
        for file_path in sorted_files:
            file_errors = errors_by_file[file_path]
            f.write(f"### `{file_path}`\n")
            f.write(f"**Errors:** {len(file_errors)}\n\n")
            f.write("| Line | Error Message |\n")
            f.write("|------|---------------|\n")
            
            for err in file_errors:
                # Escape pipes in message to not break table
                safe_msg = err['message'].replace('|', '\|')
                f.write(f"| {err['line']} | `{safe_msg}` |\n")
            
            f.write("\n")

if __name__ == "__main__":
    if not os.path.exists("backend_errors.log"):
        print("Error: backend_errors.log not found.")
    else:
        errors, count = parse_errors("backend_errors.log")
        generate_markdown(errors, count, "FULL_AUDIT_REPORT.md")
        print(f"Generated FULL_AUDIT_REPORT.md with {count} errors.")
