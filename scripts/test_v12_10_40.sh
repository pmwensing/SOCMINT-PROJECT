#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

if [ ! -f release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json ]; then
  python scripts/db_migration_smoke_v12_10_38.py || true
fi

if [ ! -f release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json ]; then
  python scripts/db_smoke_result_gate_v12_10_39.py || true
fi

python -m py_compile scripts/db_smoke_failure_extractor_v12_10_40.py
python -m pytest -q tests/test_v12_10_40_db_smoke_failure_extractor.py
python scripts/db_smoke_failure_extractor_v12_10_40.py

echo "[+] v12.10.40 DB smoke failure extractor passed"
