#!/usr/bin/env python3
"""
Full translation sync script.
Copies all missing keys from en.json to other locale files.
Uses English values as placeholders that need human translation review.
"""

import json
import os
from pathlib import Path
from typing import Any

# Path to locales directory
LOCALES_DIR = Path("/home/aaron/IdeaProjects/Management-Software/frontend/src/locales")

def flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Flatten a nested dictionary into dot-notation keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(d: dict, sep: str = ".") -> dict:
    """Convert dot-notation keys back to nested dictionary."""
    result = {}
    for key, value in sorted(d.items()):
        parts = key.split(sep)
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # Handle collision: existing scalar value being overwritten by dict
                current[part] = {"_value": current[part]}
            current = current[part]
        current[parts[-1]] = value
    return result


def load_locale(locale: str) -> dict:
    """Load a locale file."""
    file_path = LOCALES_DIR / f"{locale}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_locale(locale: str, data: dict) -> None:
    """Save a locale file."""
    file_path = LOCALES_DIR / f"{locale}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved {file_path}")


def sync_all():
    """Sync all translations from en.json to other locales."""
    print("Loading English translations...")
    en_data = load_locale("en")
    en_flat = flatten_dict(en_data)
    print(f"  English has {len(en_flat)} keys")
    
    for locale in ["fr", "de", "es", "ar"]:
        print(f"\nSyncing {locale.upper()} translations...")
        locale_data = load_locale(locale)
        locale_flat = flatten_dict(locale_data)
        
        # Find missing keys
        missing_keys = set(en_flat.keys()) - set(locale_flat.keys())
        
        if missing_keys:
            print(f"  Found {len(missing_keys)} missing translations")
            
            # Add English values for missing keys (as placeholders)
            for key in missing_keys:
                locale_flat[key] = en_flat[key]
            
            # Convert back to nested structure
            locale_data = unflatten_dict(locale_flat)
            
            # Preserve meta information
            if "meta" not in locale_data:
                locale_data["meta"] = {}
            
            meta_info = {
                "fr": {"locale": "fr", "name": "French", "nativeName": "Français", "flag": "🇫🇷", "direction": "ltr"},
                "de": {"locale": "de", "name": "German", "nativeName": "Deutsch", "flag": "🇩🇪", "direction": "ltr"},
                "es": {"locale": "es", "name": "Spanish", "nativeName": "Español", "flag": "🇪🇸", "direction": "ltr"},
                "ar": {"locale": "ar", "name": "Arabic", "nativeName": "العربية", "flag": "🇸🇦", "direction": "rtl"},
            }
            locale_data["meta"] = meta_info.get(locale, locale_data.get("meta", {}))
            
            # Save updated locale
            save_locale(locale, locale_data)
            print(f"  Added {len(missing_keys)} new translations (English placeholders)")
        else:
            print("  All translations present")


if __name__ == "__main__":
    sync_all()
    print("\n✅ Translation sync complete!")
    print("\n⚠️  NOTE: New translations are English placeholders.")
    print("   They need professional translation review for:")
    print("   - French (fr.json)")
    print("   - German (de.json)")  
    print("   - Spanish (es.json)")
    print("   - Arabic (ar.json)")
