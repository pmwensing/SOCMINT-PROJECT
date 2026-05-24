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

set +e
python scripts/drift_lock_audit_v12_10_31A.py
AUDIT_STATUS=$?
set -e

echo "[+] Drift report:"
echo "    release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31B.md"

exit "$AUDIT_STATUS"
