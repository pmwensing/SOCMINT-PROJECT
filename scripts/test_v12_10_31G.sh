#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/drift_lock_audit_v12_10_31A.py
python -m pytest -q tests/test_v12_10_31F_clean_drift_auditor.py
python -m pytest -q tests/test_v12_10_31G_route_deep_diag.py

set +e
python scripts/drift_lock_audit_v12_10_31A.py
AUDIT_STATUS=$?
set -e

python - <<'PY'
import json
from pathlib import Path

p = Path("release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31G.json")
data = json.loads(p.read_text())
summary = data["summary"]

print("[+] v12.10.31G summary")
for key in [
    "overall_status",
    "drift_lock",
    "framework",
    "primary_entrypoint",
    "dashboard_module_file",
    "alembic_heads",
    "missing_v12_routes",
    "missing_v12_endpoint_suffixes",
    "v12_like_routes_after_lock",
    "v12_like_endpoints_after_lock",
    "route_lock_errors",
    "model_tables_missing_migrations",
    "version_unique_count",
]:
    print(f"{key}: {summary.get(key)}")

assert summary["framework"] == "flask"
assert summary["primary_entrypoint"] == "src/socmint/dashboard.py"
assert summary["missing_v12_routes"] == 0
assert summary["missing_v12_endpoint_suffixes"] == 0
assert summary["version_unique_count"] == 1
PY

exit "$AUDIT_STATUS"
