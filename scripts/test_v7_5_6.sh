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

echo "[+] v7.5.6 compile"
python3 -m compileall -q src/socmint scripts/full_report_retention_smoke_v7_5_6.py

echo "[+] v7.5.6 retention smoke"
python3 scripts/full_report_retention_smoke_v7_5_6.py

echo "[+] v7.5.6 regression tests"
pytest -q tests/test_entity_dossier_v7_5.py
