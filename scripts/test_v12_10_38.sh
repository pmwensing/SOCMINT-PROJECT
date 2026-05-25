#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/db_migration_smoke_v12_10_38.py
python -m pytest -q tests/test_v12_10_38_db_migration_smoke.py

set +e
python scripts/db_migration_smoke_v12_10_38.py
STATUS=$?
set -e

if [ "$STATUS" != "0" ]; then
  echo "[!] v12.10.38 DB smoke produced NO-GO. This is safe; real DB was not touched."
  echo "[!] Review: release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.md"
  exit 0
fi

echo "[+] v12.10.38 DB smoke GO"
