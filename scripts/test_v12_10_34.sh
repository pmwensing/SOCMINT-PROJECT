#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

if [ ! -f release/p0_p1_migration_review/P0_P1_MIGRATION_CANDIDATES_V12_10_33.json ]; then
  echo "[+] Missing v12.10.33 P0/P1 candidate JSON; generating it first"
  python scripts/extract_p0_p1_migration_candidates_v12_10_33.py
fi

python -m py_compile scripts/human_review_gate_v12_10_34.py
python -m pytest -q tests/test_v12_10_34_human_review_gate.py
python scripts/human_review_gate_v12_10_34.py generate
python scripts/human_review_gate_v12_10_34.py refuse-migration

echo "[+] v12.10.34 human review gate passed"
