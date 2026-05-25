#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/iterative_db_smoke_repair_loop_v12_10_44.py
python -m pytest -q tests/test_v12_10_44_iterative_db_smoke_repair_loop.py

set +e
python scripts/iterative_db_smoke_repair_loop_v12_10_44.py
STATUS=$?
set -e

python - <<'PY'
import json
from pathlib import Path

p = Path("release/db_smoke_repair_loop/ITERATIVE_DB_SMOKE_REPAIR_LOOP_V12_10_44.json")
data = json.loads(p.read_text())

assert data["production_db_touched"] is False
assert data["real_config_upgrade_run"] is False
assert data["schema_mutation"] == "temp_sqlite_only"

print("[+] v12.10.44 final_status:", data["final_status"])
print("[+] release_status:", data["release_status"])
print("[+] schema_lock:", data["schema_lock"])
print("[+] smoke_status:", data["final"]["smoke_status"])
print("[+] probable_failing_table:", data["final"].get("probable_failing_table"))
PY

if [ "$STATUS" != "0" ]; then
  echo "[!] v12.10.44 still HOLD. Review latest locator repair target:"
  echo "    cat release/db_smoke_exact_failure/DB_SMOKE_FAILED_TABLE_REPAIR_TARGET_V12_10_42.md"
  exit 0
fi

echo "[+] v12.10.44 DB smoke loop PASS GO"
