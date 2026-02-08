#!/usr/bin/env python3
"""Replace all loading:true/false patterns in quality.ts with startOp/endOp."""
import re

filepath = "frontend/src/stores/quality.ts"

with open(filepath, "r") as f:
    content = f.read()

lines = content.split("\n")
result = []
current_method = None

for line in lines:
    # Detect method name from async declaration
    method_match = re.match(r"\s+(\w+):\s*async\s*\(", line)
    if method_match:
        current_method = method_match.group(1)

    # Skip already-converted methods
    if current_method == "fetchInspections":
        result.append(line)
        continue

    # Replace set({ loading: true, error: null });
    if "set({ loading: true, error: null });" in line and current_method:
        indent = len(line) - len(line.lstrip())
        result.append(" " * indent + f"startOp(set, '{current_method}');")
        continue

    # Replace: set({ error: getErrorMessage(error), loading: false });
    if current_method and "getErrorMessage(error), loading: false" in line:
        indent = len(line) - len(line.lstrip())
        result.append(" " * indent + "set({ error: getErrorMessage(error) });")
        continue

    # Replace: set({ error: ..., loading: false });  (other patterns)
    if current_method and "loading: false, error:" in line:
        new_line = line.replace("loading: false, ", "")
        result.append(new_line)
        continue

    # Remove loading: false from set() calls (in try blocks, like set({ data: x, loading: false }))
    if current_method and "loading: false" in line:
        new_line = line.replace(", loading: false", "").replace("loading: false, ", "").replace("loading: false", "")
        stripped = new_line.strip()
        if stripped and stripped not in ("", ","):
            result.append(new_line)
        continue

    result.append(line)

content = "\n".join(result)

# Now we need to add endOp calls. The pattern is:
# try { ... } catch (error: unknown) { set({ error: ... }); }
# We need to convert these to try/catch/finally with endOp

# Replace catch blocks to add finally
# Pattern: } catch (error: unknown) {\n      set({ error: ... });\n    }
# to: } catch (error: unknown) {\n      set({ error: ... });\n    } finally {\n      endOp(set, 'methodName');\n    }

lines = content.split("\n")
result = []
i = 0
current_method = None

while i < len(lines):
    line = lines[i]

    # Detect method name
    method_match = re.match(r"\s+(\w+):\s*async\s*\(", line)
    if method_match:
        current_method = method_match.group(1)

    # Skip already-converted methods
    if current_method == "fetchInspections":
        result.append(line)
        i += 1
        continue

    # Look for closing of catch block: "    }" after a set({ error: ...}) line
    # Check if this is a catch-close followed by method-close
    if (
        current_method
        and line.strip() == "}"
        and i > 0
        and "getErrorMessage(error)" in lines[i - 1]
    ):
        indent = len(line) - len(line.lstrip())
        result.append(line)  # close catch
        result.append(" " * indent + f"finally {{")
        result.append(" " * (indent + 2) + f"endOp(set, '{current_method}');")
        result.append(" " * indent + "}")
        i += 1
        continue

    result.append(line)
    i += 1

with open(filepath, "w") as f:
    f.write("\n".join(result))

# Verify
with open(filepath, "r") as f:
    content = f.read()

start_count = content.count("startOp(set,")
end_count = content.count("endOp(set,")
old_count = content.count("loading: true, error: null")

print(f"startOp calls: {start_count}")
print(f"endOp calls: {end_count}")
print(f"Remaining old loading patterns: {old_count}")
print("Done!")
