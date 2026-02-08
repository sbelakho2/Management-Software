#!/usr/bin/env python3
"""Add finally { endOp(set, 'method'); } to all catch blocks missing them in a store file."""
import re
import sys

filepath = sys.argv[1]

with open(filepath, "r") as f:
    lines = f.readlines()

result = []
current_method = None
i = 0

while i < len(lines):
    line = lines[i]

    # Detect method name
    m = re.match(r"\s+(\w+):\s*async\s*\(", line)
    if m:
        current_method = m.group(1)

    # Detect: "} catch ..." followed by "  set({ error: ... });" followed by "}"
    # Pattern: current line is "}" that closes a catch block
    if (
        current_method
        and line.strip() == "}"
        and i >= 2
        and "catch" in lines[i - 2]
        and "set({" in lines[i - 1]
        and "error" in lines[i - 1]
    ):
        # Check if next line is NOT already "finally"
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
        if "finally" not in next_line:
            indent = len(line) - len(line.lstrip())
            result.append(line)
            result.append(" " * indent + "finally {\n")
            result.append(" " * (indent + 2) + f"endOp(set, '{current_method}');\n")
            result.append(" " * indent + "}\n")
            i += 1
            continue

    # Also handle: catch with return null on the next line after error set
    if (
        current_method
        and line.strip() == "}"
        and i >= 3
        and "catch" in lines[i - 3]
        and "set({" in lines[i - 2]
        and "return null" in lines[i - 1]
    ):
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
        if "finally" not in next_line:
            indent = len(line) - len(line.lstrip())
            result.append(line)
            result.append(" " * indent + "finally {\n")
            result.append(" " * (indent + 2) + f"endOp(set, '{current_method}');\n")
            result.append(" " * indent + "}\n")
            i += 1
            continue

    result.append(line)
    i += 1

with open(filepath, "w") as f:
    f.writelines(result)

# Verify
with open(filepath, "r") as f:
    content = f.read()
starts = re.findall(r"startOp\(set, '(\w+)'\)", content)
ends = re.findall(r"endOp\(set, '(\w+)'\)", content)
missing = set(starts) - set(ends)
print(f"startOp: {len(starts)}, endOp: {len(ends)}")
if missing:
    print(f"Still missing endOp: {missing}")
else:
    print("All balanced!")
