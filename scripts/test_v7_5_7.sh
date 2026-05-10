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

echo "[+] v7.5.7 compile"
python3 -m compileall -q src/socmint scripts/full_report_retention_ui_smoke_v7_5_7.py

echo "[+] v7.5.7 retention UI action smoke"
python3 scripts/full_report_retention_ui_smoke_v7_5_7.py

echo "[+] v7.5.7 v7.5.6 human-equivalent regression"
python3 scripts/full_report_human_equivalent_smoke_v7_5_6.py

echo "[+] v7.5.7 dossier regression tests"
pytest -q tests/test_entity_dossier_v7_5.py
