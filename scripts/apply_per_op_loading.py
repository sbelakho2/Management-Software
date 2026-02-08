#!/usr/bin/env python3
"""Apply per-operation loading pattern to a Zustand store file.

Usage: python3 apply_per_op_loading.py <store_file> <state_interface_name>
"""
import re
import sys

filepath = sys.argv[1]
state_name = sys.argv[2]

with open(filepath, "r") as f:
    content = f.read()

# 1. Add loadingOps and isOpLoading to the state interface
# Find "loading: boolean;" or "isLoading: boolean;" in the interface
loading_field = "loading" if "loading: boolean;" in content else "isLoading"

# Add loadingOps after loading field in the interface
old_loading = f"  {loading_field}: boolean;"
new_loading = f"""  /** @deprecated Use loadingOps for per-operation states */
  {loading_field}: boolean;
  /** Set of currently in-progress operation names */
  loadingOps: Set<string>;"""

if "loadingOps: Set<string>" not in content:
    content = content.replace(old_loading, new_loading, 1)

# 2. Add isOpLoading to actions in interface (before the closing })
# Find the interface closing brace
interface_match = re.search(
    rf"interface {state_name}\s*\{{", content
)
if interface_match:
    # Find the closing brace
    brace_count = 0
    pos = interface_match.start()
    for i in range(pos, len(content)):
        if content[i] == "{":
            brace_count += 1
        elif content[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                # Insert isOpLoading before closing brace
                if "isOpLoading" not in content:
                    content = content[:i] + "  /** Check if a specific operation is in progress */\n  isOpLoading: (op: string) => boolean;\n" + content[i:]
                break

# 3. Add startOp/endOp helper functions before the create call
create_pattern = rf"export const \w+ = create<{state_name}>\("
create_match = re.search(create_pattern, content)
if create_match and "function startOp" not in content:
    helpers = f"""
/* ── Per-operation loading helpers ─────────────────────────────────── */
function startOp(set: (fn: (s: {state_name}) => Partial<{state_name}>) => void, op: string) {{
  set((s) => {{
    const next = new Set(s.loadingOps);
    next.add(op);
    return {{ loadingOps: next, {loading_field}: true, error: null }};
  }});
}}
function endOp(set: (fn: (s: {state_name}) => Partial<{state_name}>) => void, op: string) {{
  set((s) => {{
    const next = new Set(s.loadingOps);
    next.delete(op);
    return {{ loadingOps: next, {loading_field}: next.size > 0 }};
  }});
}}

"""
    content = content[:create_match.start()] + helpers + content[create_match.start():]

# 4. Add loadingOps initialization and isOpLoading in store body
init_pattern = rf"{loading_field}: false,"
if "loadingOps: new Set" not in content:
    # Find it in the store body (after create<)
    store_start = content.find(f"create<{state_name}>")
    if store_start > 0:
        init_pos = content.find(init_pattern, store_start)
        if init_pos > 0:
            content = content[:init_pos + len(init_pattern)] + f"\n  loadingOps: new Set<string>()," + content[init_pos + len(init_pattern):]

# Add isOpLoading implementation
if "isOpLoading: (op" not in content:
    # Find a good place - after loadingOps init or after error: null
    error_init = content.find("error: null,", content.find(f"create<{state_name}>"))
    if error_init > 0:
        insert_pos = error_init + len("error: null,")
        content = content[:insert_pos] + f"\n  isOpLoading: (op: string) => get().loadingOps.has(op)," + content[insert_pos:]

# 5. Replace set({ loading/isLoading: true, error: null }) with startOp
lines = content.split("\n")
result = []
current_method = None

for line in lines:
    method_match = re.match(r"\s+(\w+):\s*async\s*\(", line)
    if method_match:
        current_method = method_match.group(1)

    if f"set({{ {loading_field}: true, error: null }});" in line and current_method:
        indent = len(line) - len(line.lstrip())
        result.append(" " * indent + f"startOp(set, '{current_method}');")
        continue

    if current_method and f"getErrorMessage(error), {loading_field}: false" in line:
        indent = len(line) - len(line.lstrip())
        result.append(" " * indent + "set({ error: getErrorMessage(error) });")
        continue

    if current_method and f"{loading_field}: false, error:" in line:
        new_line = line.replace(f"{loading_field}: false, ", "")
        result.append(new_line)
        continue

    if current_method and f"{loading_field}: false" in line:
        new_line = line.replace(f", {loading_field}: false", "").replace(f"{loading_field}: false, ", "").replace(f"{loading_field}: false", "")
        stripped = new_line.strip()
        if stripped and stripped not in ("", ","):
            result.append(new_line)
        continue

    result.append(line)

# 6. Add finally blocks with endOp
lines2 = "\n".join(result).split("\n")
result2 = []
current_method = None
i = 0

while i < len(lines2):
    line = lines2[i]

    method_match = re.match(r"\s+(\w+):\s*async\s*\(", line)
    if method_match:
        current_method = method_match.group(1)

    # Look for closing of catch block
    if (
        current_method
        and line.strip() == "}"
        and i > 0
        and ("getErrorMessage(error)" in lines2[i - 1] or "return null;" in lines2[i - 1])
        and "finally" not in (lines2[i + 1] if i + 1 < len(lines2) else "")
    ):
        indent = len(line) - len(line.lstrip())
        result2.append(line)
        result2.append(" " * indent + "finally {")
        result2.append(" " * (indent + 2) + f"endOp(set, '{current_method}');")
        result2.append(" " * indent + "}")
        i += 1
        continue

    result2.append(line)
    i += 1

content = "\n".join(result2)

with open(filepath, "w") as f:
    f.write(content)

# Verify
starts = re.findall(r"startOp\(set, '(\w+)'\)", content)
ends = re.findall(r"endOp\(set, '(\w+)'\)", content)
missing = set(starts) - set(ends)

print(f"File: {filepath}")
print(f"startOp calls: {len(starts)}")
print(f"endOp calls: {len(ends)}")
if missing:
    print(f"WARNING: Methods missing endOp: {missing}")
print("Done!")
