#!/usr/bin/env python3
"""
Generate missing translations for en.json based on used keys.
"""
import json
import re
import sys
import os

def camel_to_title(name):
    """Convert camelCase to Title Case"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)
    s3 = re.sub('([0-9]+)', r' \1 ', s2)
    return ' '.join(word.capitalize() for word in s3.split()).strip()

def key_to_value(key):
    """Convert a translation key to a human-readable value"""
    parts = key.split('.')
    last_part = parts[-1]
    return camel_to_title(last_part)

def nested_set(dic, keys, value):
    """Set a value in a nested dictionary, handling conflicts"""
    for key in keys[:-1]:
        if key not in dic:
            dic[key] = {}
        elif not isinstance(dic[key], dict):
            old_val = dic[key]
            dic[key] = {"_value": old_val}
        dic = dic[key]
    
    final_key = keys[-1]
    if final_key not in dic:
        dic[final_key] = value

def get_nested(dic, keys):
    """Get a value from nested dictionary"""
    for key in keys:
        if not isinstance(dic, dict):
            return None
        dic = dic.get(key)
        if dic is None:
            return None
    return dic

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.dirname(script_dir)
    
    # Read keys from temp file
    keys_file = '/tmp/all_keys.txt'
    if not os.path.exists(keys_file):
        print(f"Error: {keys_file} not found")
        sys.exit(1)
    
    with open(keys_file, 'r') as f:
        all_keys = [line.strip() for line in f if line.strip() and '.' in line]
    
    # Filter valid keys
    valid_keys = [k for k in all_keys if re.match(r'^[a-zA-Z][a-zA-Z0-9_.]*$', k)]
    
    # Read existing translations
    locale_file = os.path.join(frontend_dir, 'src/locales/en.json')
    with open(locale_file, 'r') as f:
        translations = json.load(f)
    
    # Find missing keys
    missing = []
    for key in valid_keys:
        parts = key.split('.')
        val = get_nested(translations, parts)
        if val is None:
            missing.append(key)
    
    print(f"Total keys used: {len(valid_keys)}")
    print(f"Missing keys: {len(missing)}")
    
    # Generate translations for missing keys
    for key in missing:
        parts = key.split('.')
        value = key_to_value(key)
        nested_set(translations, parts, value)
    
    # Write updated translations
    with open(locale_file, 'w') as f:
        json.dump(translations, f, indent=2, ensure_ascii=False)
    
    print(f"Done! Updated {locale_file}")

if __name__ == '__main__':
    main()
