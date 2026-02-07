import json
import re

def add_rlm(text, use_rlm=False):
    if not use_rlm:
        return text
    if not isinstance(text, str):
        return text
    # If the text ends with a "weak" character (Latin letter, digit, common punctuation), append RLM.
    # This ensures that if this text follows Arabic text or is in an RTL context, the weak char
    # stays at the end visually.
    if re.search(r'[a-zA-Z0-9\.\-\:\)\(\]\[\}\{\"\'\!\?]$', text):
        return text + '\u200F'
    return text

def sync_keys(source, target, use_rlm=False):
    changed = False
    for key, value in source.items():
        if key not in target:
            if isinstance(value, dict):
                target[key] = {}
                sync_keys(value, target[key], use_rlm)
            else:
                target[key] = add_rlm(value, use_rlm)
            changed = True
        else:
            if isinstance(value, dict):
                if not isinstance(target[key], dict):
                    # Type mismatch, overwrite with empty dict and sync
                    target[key] = {}
                    changed = True
                if sync_keys(value, target[key], use_rlm):
                    changed = True
            # If key exists and is string, valid. If key exists and source is string but target is dict, invalid.
            elif isinstance(target[key], dict):
                 # Source is value, target is dict. Mismatch. Overwrite.
                 target[key] = add_rlm(value, use_rlm)
                 changed = True
            
    return changed

def main():
    try:
        with open('frontend/src/locales/en.json', 'r', encoding='utf-8') as f:
            en_data = json.load(f)
        
        target_locales = ['ar', 'fr', 'es', 'de']
        
        for locale in target_locales:
            file_path = f'frontend/src/locales/{locale}.json'
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    target_data = json.load(f)
            except FileNotFoundError:
                print(f"Warning: {file_path} not found. Skipping.")
                continue

            use_rlm = (locale == 'ar')
            if sync_keys(en_data, target_data, use_rlm):
                print(f"Updated {locale}.json with new keys.")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(target_data, f, ensure_ascii=False, indent=2)
            else:
                print(f"{locale}.json is already in sync.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
