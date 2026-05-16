#!/usr/bin/env bash
# Automated Lint Fix for v10.32 Productization/UX PR #139

# Navigate to repo root
dir=$(dirname "$0")
cd "$dir"/../

# List of files in PR #139 that need lint fix
files=(
    src/socmint/v10_32_productization_ux_layer.py
    src/socmint/v10_32_productization_ux_routes.py
    tests/test_v10_32_productization_ux.py
    tests/test_v10_32_productization_ux_routes.py
)

# Apply EOF newline and remove trailing whitespace
for file in "${files[@]}"; do
    [ -f "$file" ] || continue
    # Remove trailing whitespace
    sed -i 's/[ 	]*$//' "$file"
    # Add newline at EOF if missing
    sed -i -e '$a\' "$file"
done

# Commit changes
git add "${files[@]}"
git commit -m "v10.32: fix lint errors (EOF newlines + trailing whitespace)"
git push origin feat/v10.32-productization-ux

echo "Lint fix applied and pushed. PR #139 ready for CI re-run."