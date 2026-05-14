#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python3 -m pytest -q \
  tests/test_distribution_release_ledger_v10_17.py \
  tests/test_distribution_export_verification_v10_16.py \
  tests/test_distribution_packet_export_v10_15.py

python3 - <<'PY'
from src.socmint.wsgi import app
routes = {rule.rule for rule in app.url_map.iter_rules()}
required = {
    "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/seal",
    "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/markdown",
    "/api/v1/dossier-builder/v3/distribution-release-ledger/<case_id>",
}
missing = sorted(required - routes)
if missing:
    raise SystemExit(f"missing routes: {missing}")
print("v10.17 routes ok")
PY
