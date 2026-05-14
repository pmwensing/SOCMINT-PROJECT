#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

if [ -f .env ]; then
  set +u
  set -a
  . ./.env
  set +a
  set -u
fi

echo "[+] Compile"
python3 -m compileall -q src/socmint

echo "[+] Route check"
python3 - <<'PY'
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.scope_lock_routes import register_scope_lock_routes
from socmint.build_audit_routes import register_build_audit_routes
from socmint.entity_profile_intelligence_routes import register_entity_profile_intelligence_routes

app = create_app()
register_full_report_aliases(app)
register_scope_lock_routes(app)
register_build_audit_routes(app)
register_entity_profile_intelligence_routes(app)
required = {
    "/api/v1/workbench/scope-lock",
    "/api/v1/workbench/build-spec-lock",
    "/api/v1/workbench/drift-report",
    "/api/v1/workbench/audit-report",
    "/api/v1/dossier-builder/v3/intelligence/build",
    "/api/v1/dossier-builder/v3/intelligence/summary",
    "/api/v1/dossier-builder/v3/intelligence/markdown",
}
rules = {rule.rule for rule in app.url_map.iter_rules()}
missing = sorted(required - rules)
if missing:
    raise SystemExit(f"missing v7.5 route(s): {missing}")
for rule in sorted(rules):
    if rule in required or "dossier-v2" in rule or rule.endswith("/dossier"):
        print(rule)
PY

echo "[+] Tests"
pytest -q \
  tests/test_entity_dossier_v7_5.py \
  tests/test_build_scope_lock_v7_5.py \
  tests/test_build_audit_report_v7_5.py \
  tests/test_dossier_quality_v7_5.py \
  tests/test_dossier_export_enforcement_v7_5.py \
  tests/test_dossier_evidence_manifest_v7_5.py
