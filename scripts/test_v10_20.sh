#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python3 -m pytest -q \
  tests/test_entity_profile_intelligence_v10_20.py \
  tests/test_dossier_builder_v10_3.py

python3 - <<'PY'
from src.socmint.wsgi import app
routes = {rule.rule for rule in app.url_map.iter_rules()}
required = {
    "/api/v1/dossier-builder/v3/intelligence/build",
    "/api/v1/dossier-builder/v3/intelligence/summary",
    "/api/v1/dossier-builder/v3/intelligence/markdown",
}
missing = sorted(required - routes)
if missing:
    raise SystemExit(f"missing routes: {missing}")
print("v10.20 intelligence routes ok")
PY
