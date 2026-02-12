import json
import os
from typing import Dict, Set

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def flatten_keys(data: Dict, parent_key: str = '', keys: Set[str] = None) -> Set[str]:
    if keys is None:
        keys = set()
    
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            keys.add(new_key)
            flatten_keys(v, new_key, keys)
    
    return keys

def main():
    base_dir = "frontend/src/locales"
    languages = ["en", "ar", "de", "es", "fr"]
    
    keys_map = {}
    
    for lang in languages:
        path = os.path.join(base_dir, f"{lang}.json")
        try:
            data = load_json(path)
            keys_map[lang] = flatten_keys(data)
            print(f"Loaded {lang}.json with {len(keys_map[lang])} keys")
        except FileNotFoundError:
            print(f"Error: {path} not found")
            return

    base_lang = "en"
    base_keys = keys_map[base_lang]
    
    # Check for missing keys in other languages
    for lang in languages:
        if lang == base_lang:
            continue
        
        missing_in_lang = base_keys - keys_map[lang]
        missing_in_base = keys_map[lang] - base_keys
        
        if missing_in_lang:
            print(f"\nMissing keys in {lang} (present in {base_lang}):")
            for k in sorted(missing_in_lang):
                print(f"  {k}")
        
        if missing_in_base:
            print(f"\nExtra keys in {lang} (missing in {base_lang}):")
            for k in sorted(missing_in_base):
                print(f"  {k}")

if __name__ == "__main__":
    main()
