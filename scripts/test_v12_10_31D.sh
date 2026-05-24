#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/drift_lock_audit_v12_10_31A.py

python -m pytest -q tests/test_v12_10_31A_drift_lock_audit.py
python -m pytest -q tests/test_v12_10_31B_drift_correction.py
python -m pytest -q tests/test_v12_10_31C_runtime_route_audit.py
python -m pytest -q tests/test_v12_10_31D_force_route_lock.py

set +e
python scripts/drift_lock_audit_v12_10_31A.py
AUDIT_STATUS=$?
set -e

python - <<'PY'
import json
from pathlib import Path

p = Path("release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31D.json")
data = json.loads(p.read_text())
summary = data["summary"]

print("[+] v12.10.31D summary")
for key in [
    "overall_status",
    "drift_lock",
    "framework",
    "primary_entrypoint",
    "alembic_heads",
    "missing_v12_routes",
    "model_tables_missing_migrations",
    "version_unique_count",
]:
    print(f"{key}: {summary.get(key)}")

assert summary["framework"] == "flask"
assert summary["primary_entrypoint"] == "src/socmint/dashboard.py"
assert summary["alembic_heads"] == "0017_v12_10_schema_reconciliation"
assert summary["missing_v12_routes"] == 0
assert summary["version_unique_count"] == 1
PY

exit "$AUDIT_STATUS"
