#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python3 -m pytest -q \
  tests/test_release_ledger_dashboard_v10_18.py \
  tests/test_distribution_release_ledger_v10_17.py \
  tests/test_distribution_export_verification_v10_16.py

python3 - <<'PY'
from src.socmint.wsgi import app
routes = {rule.rule for rule in app.url_map.iter_rules()}
required = {
    "/dossier/release-ledger-dashboard",
    "/api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>",
    "/api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>/markdown",
}
missing = sorted(required - routes)
if missing:
    raise SystemExit(f"missing routes: {missing}")
print("v10.18 routes ok")
PY
