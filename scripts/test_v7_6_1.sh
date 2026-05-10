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

echo "[+] v7.6.1 compile"
python3 -m compileall -q src/socmint scripts/connector_runtime_repair_smoke_v7_6_1.py scripts/connector_runtime_installer_smoke_v7_6_0.py

echo "[+] v7.6.1 connector runtime repair smoke"
python3 scripts/connector_runtime_repair_smoke_v7_6_1.py

echo "[+] v7.6.1 v7.6.0 installer regression"
python3 scripts/connector_runtime_installer_smoke_v7_6_0.py

echo "[+] v7.6.1 full dossier regression"
pytest -q tests/test_entity_dossier_v7_5.py
