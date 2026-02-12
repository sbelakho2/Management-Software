import json
import re

def is_english_like(text, key):
    # Heuristics for "Is this English?"
    if not isinstance(text, str): return False
    if text == "S": return False # Brand mark
    if len(text) < 2: return False
    
    # If it matches the English text exactly (or close enough)
    # Use strict equality with en_val for now
    return False 

def extract_missing(lang):
    try:
        with open('frontend/src/locales/en.json') as f:
            en_data = json.load(f)
        
        with open(f'frontend/src/locales/{lang}.json') as f:
            target_data = json.load(f)
    except FileNotFoundError:
        print(f"Could not find files for {lang}")
        return

    missing = {}

    def walk(en_node, target_node, path):
        if isinstance(en_node, dict) and isinstance(target_node, dict):
            for k, v in en_node.items():
                if k in target_node:
                    walk(v, target_node[k], path + "." + k if path else k)
        elif isinstance(en_node, str) and isinstance(target_node, str):
            # If target equals English, it's a candidate
            if en_node == target_node and en_node not in ["S", "Sensei", "sensei"]:
                missing[path] = target_node
            # If target has Latin characters and lang is Arabic
            elif lang == 'ar' and re.search(r'[a-zA-Z]{2,}', target_node):
                 # Ignore if it looks like technical code e.g. "AOI", "ICT", "NPI" inside a sentence?
                 # ideally we translate explanations but acronyms stay.
                 # But "SYSTEM_INITIALIZATION..." is definitely untranslated.
                 missing[path] = target_node

    walk(en_data, target_data, "")
    
    with open(f'scripts/missing_{lang}.json', 'w') as f:
        json.dump(missing, f, indent=2)
    print(f"extracted {len(missing)} items to scripts/missing_{lang}.json")

if __name__ == "__main__":
    extract_missing('ar')
