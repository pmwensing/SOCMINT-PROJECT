#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

echo "[+] v10.13 certification dashboard tests"
python3 -m pytest -q \
  tests/test_certification_dashboard_v10_13.py \
  tests/test_dossier_certification_index_v10_12.py

echo "[+] v10.13 route registration smoke"
python3 - <<'PY'
from src.socmint.wsgi import app
routes = {rule.rule for rule in app.url_map.iter_rules()}
required = {
    "/dossier/certification-dashboard",
    "/api/v1/dossier-builder/v3/certification-dashboard/<case_id>",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/summary",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/markdown",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>",
}
missing = sorted(required - routes)
if missing:
    raise SystemExit(f"missing routes: {missing}")
print("registered certification routes:")
for route in sorted(required):
    print(f"  {route}")
PY

echo "[+] v10.13 smoke complete"
