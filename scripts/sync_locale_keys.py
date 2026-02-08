#!/usr/bin/env python3
"""Sync missing i18n keys from en.json to other locale files."""
import json


def merge_deep(target, source, counter):
    for key, value in source.items():
        if key not in target:
            target[key] = value
            counter[0] += 1
        elif isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_deep(target[key], value, counter)


with open("frontend/src/locales/en.json") as f:
    en = json.load(f)

for locale in ["fr", "ar", "es", "de"]:
    path = f"frontend/src/locales/{locale}.json"
    with open(path) as f:
        d = json.load(f)

    counter = [0]
    merge_deep(d, en, counter)

    with open(path, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

    print(f"{locale}: added {counter[0]} missing top-level keys")
