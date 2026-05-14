#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:$PWD/src"

python - <<'PY'
from src.socmint.wsgi import app

routes = {rule.rule for rule in app.url_map.iter_rules()}
required = [
    "/api/v1/dossier-builder/v3/certification-index/<case_id>",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/summary",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/markdown",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/export-certification-index/<case_id>",
    "/api/v1/dossier-builder/v3/export-certification-index/<case_id>/summary",
    "/api/v1/dossier-builder/v3/export-certification-index/<case_id>/review",
]

missing = [route for route in required if route not in routes]
if missing:
    print("[FAIL] missing certification index routes")
    for route in missing:
        print(f" - {route}")
    raise SystemExit(1)

print("[PASS] v10.23 certification index smoke")
for route in required:
    print(f" - {route}")
PY
