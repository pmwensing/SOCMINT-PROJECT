#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/drift_lock_audit_v12_10_31A.py
python -m pytest -q tests/test_v12_10_31A_drift_lock_audit.py

set +e
bash scripts/test_v12_10_31A_drift_lock.sh
STATUS=$?
set -e

if [ "$STATUS" = "0" ]; then
  echo "[+] v12.10.31A Drift Lock: PASS"
else
  echo "[!] v12.10.31A Drift Lock: FAIL — review release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31A.md"
fi

exit "$STATUS"
