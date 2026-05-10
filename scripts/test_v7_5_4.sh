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

echo "[+] v7.5.4 compile"
python3 -m compileall -q src/socmint scripts/full_report_runtime_smoke_v7_5_4.py

echo "[+] v7.5.4 runtime smoke"
python3 scripts/full_report_runtime_smoke_v7_5_4.py

echo "[+] v7.5.4 regression tests"
pytest -q tests/test_entity_dossier_v7_5.py
