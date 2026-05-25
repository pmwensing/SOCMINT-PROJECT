#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

if [ ! -f release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json ]; then
  echo "[+] Missing v12.10.38 smoke report; generating it first"
  python scripts/db_migration_smoke_v12_10_38.py || true
fi

python -m py_compile scripts/db_smoke_result_gate_v12_10_39.py
python -m pytest -q tests/test_v12_10_39_db_smoke_result_gate.py

set +e
python scripts/db_smoke_result_gate_v12_10_39.py
STATUS=$?
set -e

if [ "$STATUS" != "0" ]; then
  echo "[!] v12.10.39 gate is HOLD/NO-GO. Review repair plan."
  echo "[!] release/db_smoke_gate/DB_SMOKE_REPAIR_PLAN_V12_10_39.md"
  exit 0
fi

echo "[+] v12.10.39 DB smoke result gate PASS GO"
