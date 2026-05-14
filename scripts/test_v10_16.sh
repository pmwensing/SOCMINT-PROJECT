#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

echo "[+] v10.16 distribution export verification tests"
python3 -m pytest -q \
  tests/test_distribution_export_verification_v10_16.py \
  tests/test_distribution_packet_export_v10_15.py \
  tests/test_distribution_actions_v10_14.py \
  tests/test_certification_dashboard_v10_13.py \
  tests/test_dossier_certification_index_v10_12.py

echo "[+] v10.16 route registration smoke"
python3 - <<'PY'
from src.socmint.wsgi import app
routes = {rule.rule for rule in app.url_map.iter_rules()}
required = {
    "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify",
    "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify/markdown",
    "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/build",
    "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/download",
    "/dossier/certification-dashboard",
}
missing = sorted(required - routes)
if missing:
    raise SystemExit(f"missing routes: {missing}")
print("registered distribution verification routes:")
for route in sorted(required):
    print(f"  {route}")
PY

echo "[+] v10.16 smoke complete"
