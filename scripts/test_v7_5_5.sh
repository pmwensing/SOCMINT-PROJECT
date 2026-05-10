#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

if [ -f .env ]; then
  set +u
  set -a
  . ./.env
  set +a
  set -u
fi

echo "[+] v7.5.5 compile"
python3 -m compileall -q src/socmint scripts/full_report_history_compare_smoke_v7_5_5.py

echo "[+] v7.5.5 history compare smoke"
python3 scripts/full_report_history_compare_smoke_v7_5_5.py

echo "[+] v7.5.5 regression tests"
pytest -q tests/test_entity_dossier_v7_5.py
