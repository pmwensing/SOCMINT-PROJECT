#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python3 -m pytest -q \
  tests/test_distribution_handoff_packet_v10_19.py \
  tests/test_release_ledger_dashboard_v10_18.py \
  tests/test_distribution_release_ledger_v10_17.py

python3 - <<'PY'
from src.socmint.wsgi import app
routes = {rule.rule for rule in app.url_map.iter_rules()}
required = {
    "/api/v1/dossier-builder/v3/distribution-handoff/<case_id>",
    "/api/v1/dossier-builder/v3/distribution-handoff/<case_id>/markdown",
    "/dossier/release-ledger-dashboard",
}
missing = sorted(required - routes)
if missing:
    raise SystemExit(f"missing routes: {missing}")
print("v10.19 routes ok")
PY
