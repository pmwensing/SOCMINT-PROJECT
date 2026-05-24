#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

echo "[+] v12.10.31A Drift Lock Audit"

set +e
python scripts/drift_lock_audit_v12_10_31A.py
STATUS=$?
set -e

if [ ! -f release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31A.json ]; then
  echo "[-] Missing JSON drift report"
  exit 1
fi

if [ ! -f release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31A.md ]; then
  echo "[-] Missing Markdown drift report"
  exit 1
fi

python - <<'PY'
import json
from pathlib import Path

p = Path("release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31A.json")
data = json.loads(p.read_text())

assert data["audit"] == "v12.10.31A Drift Lock Audit"
assert "summary" in data
assert "checks" in data
assert data["checks"]

names = {c["name"] for c in data["checks"]}
required = {
    "framework_detection",
    "entrypoint_detection",
    "alembic_heads_and_chain",
    "models_vs_migrations",
    "static_route_scan",
    "runtime_v12_route_registration",
    "version_metadata",
}
missing = required - names
assert not missing, missing

print("[+] Drift report structure valid")
print("[+] Overall:", data["summary"]["overall_status"])
print("[+] Drift lock:", data["summary"]["drift_lock"])
PY

exit "$STATUS"
