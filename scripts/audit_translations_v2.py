import json
import re

def detect_latin(text):
    # Detect strings that have significant Latin characters (a-z) 
    # but ignore placeholders like {val}
    cleaned = re.sub(r'\{[^}]+\}', '', text)
    if re.search(r'[a-zA-Z]{2,}', cleaned):
        return True
    return False

def check_file(lang):
    try:
        with open('frontend/src/locales/en.json') as f:
            en_data = json.load(f)
        
        with open(f'frontend/src/locales/{lang}.json') as f:
            target_data = json.load(f)
    except FileNotFoundError:
        print(f"Could not find files for {lang}")
        return

    suspicious = []

    def walk(en_node, target_node, path):
        if isinstance(en_node, dict) and isinstance(target_node, dict):
            for k, v in en_node.items():
                if k in target_node:
                    walk(v, target_node[k], path + "." + k if path else k)
        elif isinstance(en_node, str) and isinstance(target_node, str):
            # Check 1: Identity
            if en_node == target_node and len(en_node.strip()) > 1 and not en_node.isdigit() and en_node not in ["S"]:
               suspicious.append(f"IDENTICAL|{path}|{target_node}")
            # Check 2: Latin in Arabic
            elif lang == 'ar' and detect_latin(target_node) and target_node != "S":
               suspicious.append(f"LATIN|{path}|{target_node}")

    walk(en_data, target_data, "")
    
    print(f"--- Suspicious in {lang}.json ({len(suspicious)}) ---")
    for s in suspicious: 
        print(s)

if __name__ == "__main__":
    check_file('ar')
