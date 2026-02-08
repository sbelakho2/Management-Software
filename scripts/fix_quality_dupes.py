#!/usr/bin/env python3
"""Fix doubled finally blocks in quality.ts - remove the second duplicate finally in each pair."""
import re

filepath = "frontend/src/stores/quality.ts"

with open(filepath, "r") as f:
    content = f.read()

# Remove duplicated finally blocks: pattern is:
# } finally {
#   endOp(set, 'xxx');
# }
# finally {
#   endOp(set, 'xxx');
# }
# We want to keep only the first one

pattern = r"(\n\s+\} finally \{\n\s+endOp\(set, '(\w+)'\);\n\s+\})\n\s+finally \{\n\s+endOp\(set, '\2'\);\n\s+\}"

count = len(re.findall(pattern, content))
content = re.sub(pattern, r"\1", content)

with open(filepath, "w") as f:
    f.write(content)

# Also check for fetchInspections: it already had a manually added finally block,
# now might have the script's block too

start_count = content.count("startOp(set,")
end_count = content.count("endOp(set,")
print(f"Removed {count} duplicate finally blocks")
print(f"startOp calls: {start_count}")
print(f"endOp calls: {end_count}")
