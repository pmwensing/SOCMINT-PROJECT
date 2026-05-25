#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

if [ ! -f release/model_migration_reconciliation/MODEL_MIGRATION_RECONCILIATION_V12_10_32.json ]; then
  echo "[+] Missing v12.10.32 reconciliation JSON; generating it first"
  python scripts/model_migration_reconciliation_audit_v12_10_32.py
fi

python -m py_compile scripts/extract_p0_p1_migration_candidates_v12_10_33.py
python -m pytest -q tests/test_v12_10_33_p0_p1_candidate_extractor.py
python scripts/extract_p0_p1_migration_candidates_v12_10_33.py

echo "[+] v12.10.33 P0/P1 migration candidate extractor passed"
