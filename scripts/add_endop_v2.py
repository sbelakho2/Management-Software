#!/usr/bin/env python3
"""Add finally { endOp(set, 'method'); } to store files with various catch patterns."""
import re
import sys

filepath = sys.argv[1]

with open(filepath, "r") as f:
    content = f.read()

# Find all methods that have startOp but no endOp
starts = re.findall(r"startOp\(set, '(\w+)'\)", content)
ends = re.findall(r"endOp\(set, '(\w+)'\)", content)
missing = set(starts) - set(ends)

if not missing:
    print("All balanced already!")
    sys.exit(0)

lines = content.split("\n")
result = []
current_method = None
i = 0

while i < len(lines):
    line = lines[i]

    # Detect method name
    m = re.match(r"\s+(\w+):\s*async\s*\(", line)
    if m:
        current_method = m.group(1)

    # Look for the closing brace of a try-catch that belongs to a method with startOp
    # The closing pattern is "  }," which ends the method, preceded by "  }" which ends the catch
    # We need to find the last "}" before "}," in each method
    
    # Strategy: find "} catch" blocks and track brace depth
    # Simpler: just find "    }," lines (method closing) and insert finally before them
    # for methods that have startOp but no endOp
    
    if (
        current_method in missing
        and line.strip() == "},"
    ):
        # This might be the method-closing brace
        # Look backwards to see if the preceding block is a catch
        # Find the last non-empty line before this
        j = i - 1
        while j >= 0 and lines[j].strip() == "":
            j -= 1
        
        if j >= 0 and lines[j].strip() == "}":
            # This closes a block (could be catch or try)
            # Check if there's a catch above
            indent = len(line) - len(line.lstrip())
            # Insert finally before the closing },
            result.append(f"{' ' * (indent + 4)}finally {{")
            result.append(f"{' ' * (indent + 6)}endOp(set, '{current_method}');")
            result.append(f"{' ' * (indent + 4)}}}")
            missing.discard(current_method)

    result.append(line)
    i += 1

content = "\n".join(result)

with open(filepath, "w") as f:
    f.write(content)

# Verify
starts2 = re.findall(r"startOp\(set, '(\w+)'\)", content)
ends2 = re.findall(r"endOp\(set, '(\w+)'\)", content)
missing2 = set(starts2) - set(ends2)
print(f"startOp: {len(starts2)}, endOp: {len(ends2)}")
if missing2:
    print(f"Still missing: {missing2}")
else:
    print("All balanced!")
