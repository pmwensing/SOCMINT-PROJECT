#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile \
  scripts/drift_lock_audit_v12_10_31A.py \
  src/socmint/dashboard.py \
  src/socmint/v12_10_command_center.py \
  src/socmint/v12_10_command_center_routes.py \
  src/socmint/v12_10_29_ui.py

python -m pytest -q tests/test_v12_10_31A_drift_lock_audit.py
python -m pytest -q tests/test_v12_10_31B_drift_correction.py
python -m pytest -q tests/test_v12_10_31C_runtime_route_audit.py

set +e
python scripts/drift_lock_audit_v12_10_31A.py
AUDIT_STATUS=$?
set -e

echo "[+] Drift report:"
echo "    release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31C.md"

python - <<'PY'
import json
from pathlib import Path

p = Path("release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31C.json")
data = json.loads(p.read_text())
summary = data["summary"]

print("[+] Summary:")
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
    print(f"    {key}: {summary.get(key)}")
PY

exit "$AUDIT_STATUS"
