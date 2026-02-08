#!/usr/bin/env python3
"""Fix doubled finally blocks in quality.ts."""

filepath = "frontend/src/stores/quality.ts"

with open(filepath, "r") as f:
    lines = f.readlines()

result = []
i = 0
removed = 0

while i < len(lines):
    # Look for pattern: "    finally {" followed by "      endOp(set, 'xxx');" followed by "    }"
    # If the NEXT 3 lines are the same pattern, skip the duplicate
    if (
        i + 5 < len(lines)
        and "finally {" in lines[i]
        and "endOp(set," in lines[i + 1]
        and lines[i + 2].strip() == "}"
        and "finally {" in lines[i + 3]
        and "endOp(set," in lines[i + 4]
        and lines[i + 5].strip() == "}"
    ):
        # Keep first finally, skip second
        result.append(lines[i])
        result.append(lines[i + 1])
        result.append(lines[i + 2])
        i += 6  # Skip the duplicate
        removed += 1
        continue

    result.append(lines[i])
    i += 1

with open(filepath, "w") as f:
    f.writelines(result)

# Recount
with open(filepath, "r") as f:
    content = f.read()

start_count = content.count("startOp(set,")
end_count = content.count("endOp(set,")
print(f"Removed {removed} duplicate finally blocks")
print(f"startOp calls: {start_count}")
print(f"endOp calls: {end_count}")
