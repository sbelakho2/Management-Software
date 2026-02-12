import json
import os
import copy
from typing import Dict, Any

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Add newline at end

def merge_dict(d1, d2):
    """
    Merge d2 into d1. 
    If a key exists in both and both are dicts, merge recursively.
    If a key exists in both and one is dict and other is string, specific handling:
       - convert string to dict with `_value` key.
    If key in d2 but not d1, copy d2's value.
    """
    for k, v in d2.items():
        if k in d1:
            if isinstance(d1[k], dict) and isinstance(v, dict):
                merge_dict(d1[k], v)
            elif isinstance(d1[k], dict) and not isinstance(v, dict):
                # d1 is dict, v (source) is string. check if d1 has _value, otherwise set it?
                # Actually, we want to construct the union of structures.
                # If d1 is dict, let's assume it's the correct structure. 
                # We might want to add '_value': v into d1 if not present.
                if "_value" not in d1[k]:
                    d1[k]["_value"] = v
            elif not isinstance(d1[k], dict) and isinstance(v, dict):
                # d1 is string, v is dict. Convert d1 to dict
                old_val = d1[k]
                d1[k] = copy.deepcopy(v)
                # clear values in d1[k] (we are building structure, values come later)
                # No, wait. We are merging structures.
                # If we convert d1 to dict, preserve old val as _value
                d1[k]["_value"] = old_val
            else:
                # Both are strings (or non-dicts). d1 already has a value.
                # Do nothing structure-wise.
                pass
        else:
            d1[k] = copy.deepcopy(v)

def fill_missing(target, source, master_structure):
    """
    Fill missing keys in target using values from source, guided by master_structure.
    """
    for k, v in master_structure.items():
        if k not in target:
            # Target completely missing this key
            if k in source:
                target[k] = copy.deepcopy(source[k])
            else:
                # Should not happen if master_structure is union, but v might be deep structure
                target[k] = copy.deepcopy(v) 
        
        # If target[k] is a string but master says it should be dict (or contain more)
        if isinstance(v, dict):
            if not isinstance(target[k], dict):
                # Convert target[k] to dict
                old_val = target[k]
                target[k] = {}
                if "_value" in v:
                     target[k]["_value"] = old_val
                
            fill_missing(target[k], source.get(k, {}), v)
        else:
             # v is leaf. target[k] should be leaf.
             pass

def sanitize_values(data, example_source):
    """
    Walk through data. If we find a dict where we expect a string (and it has _value),
    ensure it keeps that structure.
    Also, if we copied values, they are there.
    """
    pass

def main():
    base_dir = "frontend/src/locales"
    languages = ["en", "ar", "de", "es", "fr"]
    files = {}
    
    # 1. Load all files
    for lang in languages:
        path = os.path.join(base_dir, f"{lang}.json")
        try:
            files[lang] = load_json(path)
        except Exception as e:
            print(f"Error loading {lang}: {e}")
            return

    # 2. Build Master Structure (Union of all keys)
    master = {}
    for lang, data in files.items():
        merge_dict(master, data)
    
    # 3. Fill missing keys in each file
    # We use English as the primary source for filling missing values, 
    # then fallback to any other language if English is also missing it (unlikely but possible)
    
    for lang in languages:
        # We start with existing data
        current_data = files[lang]
        
        # We need to fill holes.
        # Strategy: Iterate master structure. If key missing in current, get from EN.
        
        # A recursive function to fill
        def fill_recursive(curr, struct, src_en):
            for k, v in struct.items():
                if isinstance(v, dict):
                    if k not in curr:
                        # Missing whole block. keys are missing.
                        curr[k] = {}
                        # Try to copy from EN
                        if k in src_en and isinstance(src_en[k], dict):
                             # deep copy from EN
                             curr[k] = copy.deepcopy(src_en[k])
                        # If not in EN, copy from structure (which contains *some* value from the union)
                        else:
                             curr[k] = copy.deepcopy(v)
                    
                    elif not isinstance(curr[k], dict):
                        # curr[k] is string, but struct is dict. Convert.
                        val = curr[k]
                        curr[k] = {"_value": val}
                        # Now fill the rest of the dict
                        fill_recursive(curr[k], v, src_en.get(k, {}))
                    
                    else:
                        # Recurse
                        fill_recursive(curr[k], v, src_en.get(k, {}))
                
                else: 
                    # v is non-dict (leaf)
                    if k not in curr:
                        # Missing leaf. Copy from EN if available
                        if k in src_en and not isinstance(src_en[k], dict):
                            curr[k] = src_en[k]
                        elif k in src_en and isinstance(src_en[k], dict) and "_value" in src_en[k]:
                             curr[k] = src_en[k]["_value"]
                        else:
                             curr[k] = v # Value from whichever file contributed to master
                    elif isinstance(curr[k], dict):
                         # curr has dict where struct has leaf (string)?
                         # This implies inconsistencies in master structure creation or conflict handling.
                         # If one file has string and another has dict, master became dict.
                         # So v should be dict?
                         # Wait, merge_dict handles string vs dict by making it dict.
                         # So if struct has a leaf, then ALL files must have had a leaf there.
                         pass

        fill_recursive(current_data, master, files["en"])
        
        # Save file
        files[lang] = current_data

    # 4. Save files
    for lang in languages:
        path = os.path.join(base_dir, f"{lang}.json")
        save_json(path, files[lang])
        print(f"Updated {lang}.json")

if __name__ == "__main__":
    main()
