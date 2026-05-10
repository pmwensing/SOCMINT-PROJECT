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

echo "[+] v7.5.9 compile"
python3 -m compileall -q src/socmint scripts/connector_runtime_smoke_v7_5_9.py scripts/command_center_smoke_v7_5_8.py

echo "[+] v7.5.9 connector runtime smoke"
python3 scripts/connector_runtime_smoke_v7_5_9.py

echo "[+] v7.5.9 command center regression"
python3 scripts/command_center_smoke_v7_5_8.py

echo "[+] v7.5.9 full dossier regression"
pytest -q tests/test_entity_dossier_v7_5.py
