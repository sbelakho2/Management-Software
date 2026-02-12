import json
import re

def has_arabic(text):
    if not isinstance(text, str): return False
    # Arabic unicode range
    return bool(re.search(r'[\u0600-\u06FF]', text))

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
            # Check for English contamination
            # Logic: If lang is Arabic, and text has NO Arabic chars, and is not just digits/symbols
            # And it has some Latin chars.
            if lang == 'ar':
                if not has_arabic(target_node):
                    if re.search(r'[a-zA-Z]', target_node):
                        # exclude brand
                        if target_node not in ["S", "Sensei", "sensei", "SENSEI"]:
                             missing[path] = target_node
            
            # For other languages, we can check for identity with English
            elif en_node == target_node and len(en_node) > 3:
                missing[path] = target_node

    walk(en_data, target_data, "")
    
    with open(f'scripts/missing_{lang}_strict.json', 'w') as f:
        json.dump(missing, f, indent=2)
    print(f"extracted {len(missing)} strictly missing items to scripts/missing_{lang}_strict.json")

if __name__ == "__main__":
    extract_missing('de')
