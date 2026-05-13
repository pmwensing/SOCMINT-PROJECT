#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

echo "[+] v10.12 certification index tests"
python3 -m pytest -q \
  tests/test_dossier_certification_index_v10_12.py \
  tests/test_dossier_export_certification_v10_11.py

echo "[+] v10.12 route registration smoke"
python3 - <<'PY'
from src.socmint.wsgi import app
routes = {rule.rule for rule in app.url_map.iter_rules()}
required = {
    "/api/v1/dossier-builder/v3/certification-index/<case_id>",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/summary",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/markdown",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>",
}
missing = sorted(required - routes)
if missing:
    raise SystemExit(f"missing routes: {missing}")
print("registered routes:")
for route in sorted(required):
    print(f"  {route}")
PY

echo "[+] v10.12 smoke complete"
