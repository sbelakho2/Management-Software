#!/bin/bash
set -e

# Base path
BASE="frontend/src/app/(dashboard)"

# Group: Admin
mv "$BASE/admin" "$BASE/(admin)/"
mv "$BASE/settings" "$BASE/(admin)/"
mv "$BASE/analytics" "$BASE/(admin)/"
mv "$BASE/executive" "$BASE/(admin)/"

# Group: Shop Floor
mv "$BASE/production" "$BASE/(shop-floor)/"
mv "$BASE/andon" "$BASE/(shop-floor)/"
mv "$BASE/maintenance" "$BASE/(shop-floor)/"
mv "$BASE/quality" "$BASE/(shop-floor)/"
mv "$BASE/training" "$BASE/(shop-floor)/"
mv "$BASE/products" "$BASE/(shop-floor)/"

# Group: Sales
mv "$BASE/pipeline" "$BASE/(sales)/"
mv "$BASE/quotes" "$BASE/(sales)/"
mv "$BASE/customers" "$BASE/(sales)/"

# Group: Ops
mv "$BASE/today" "$BASE/(ops)/"
mv "$BASE/obeya" "$BASE/(ops)/"
mv "$BASE/project-management" "$BASE/(ops)/"
mv "$BASE/a3" "$BASE/(ops)/"
mv "$BASE/exceptions" "$BASE/(ops)/"
mv "$BASE/ctq" "$BASE/(ops)/"

echo "Frontend logical grouping completed."
