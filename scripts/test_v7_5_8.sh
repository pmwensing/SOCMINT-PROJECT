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

echo "[+] v7.5.8 compile"
python3 -m compileall -q src/socmint scripts/command_center_smoke_v7_5_8.py scripts/full_report_retention_ui_smoke_v7_5_7.py

echo "[+] v7.5.8 command center UX smoke"
python3 scripts/command_center_smoke_v7_5_8.py

echo "[+] v7.5.8 retention UI regression"
python3 scripts/full_report_retention_ui_smoke_v7_5_7.py

echo "[+] v7.5.8 full dossier regression"
pytest -q tests/test_entity_dossier_v7_5.py
