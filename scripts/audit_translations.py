import json
import sys

def check_untranslated(en, target, prefix=""):
    untranslated = []
    for k, v in target.items():
        full_key = f"{prefix}{k}"
        if isinstance(v, dict):
            if k in en and isinstance(en[k], dict):
                untranslated.extend(check_untranslated(en[k], v, f"{full_key}."))
        else:
            if k in en and not isinstance(en[k], dict):
                # Check for exact match or match with RLM
                en_val = en[k]
                target_val = v
                if target_val == en_val or target_val == en_val + '\u200F':
                     untranslated.append(full_key)
    return untranslated

def main():
    if len(sys.argv) < 3:
        print("Usage: python script.py en.json target.json")
        sys.exit(1)
        
    en_path = sys.argv[1]
    target_path = sys.argv[2]
    
    with open(en_path, 'r', encoding='utf-8') as f:
        en = json.load(f)
        
    with open(target_path, 'r', encoding='utf-8') as f:
        target = json.load(f)
        
    untranslated = check_untranslated(en, target)
    print(f"Found {len(untranslated)} potentially untranslated keys in {target_path}")
    for k in untranslated:
        print(k)

if __name__ == "__main__":
    main()
