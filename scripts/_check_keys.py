import json

with open("frontend/src/locales/en.json") as f:
    d = json.load(f)

p = d.get("pages", {}).get("executive", {})
print("Has ops:", "ops" in p)
print("Has sqdcp:", "sqdcp" in p)
print("kpi keys:", list(p.get("kpi", {}).keys()) if "kpi" in p else "MISSING")
print("ops keys:", list(p.get("ops", {}).keys()) if "ops" in p else "MISSING")

# Check common.user
c = d.get("common", {})
print("Has common.user:", "user" in c)
