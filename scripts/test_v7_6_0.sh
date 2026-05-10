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

echo "[+] v7.6.0 compile"
python3 -m compileall -q src/socmint scripts/connector_runtime_installer_smoke_v7_6_0.py scripts/connector_runtime_smoke_v7_5_9.py

echo "[+] v7.6.0 installer/runtime smoke"
python3 scripts/connector_runtime_installer_smoke_v7_6_0.py

echo "[+] v7.6.0 v7.5.9 runtime regression"
python3 scripts/connector_runtime_smoke_v7_5_9.py

echo "[+] v7.6.0 full dossier regression"
pytest -q tests/test_entity_dossier_v7_5.py
