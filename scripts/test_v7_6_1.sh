#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if [ -x ./venv/bin/python ]; then
    PYTHON_BIN="./venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

if [ -f .env ]; then
  set +u
  set -a
  . ./.env
  set +a
  set -u
fi

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import sqlalchemy
PY
then
  echo "[!] Missing Python dependencies for $PYTHON_BIN"
  echo "[!] Run: make install"
  echo "[!] Then rerun: make test761"
  exit 1
fi

echo "[+] v7.6.1 using $PYTHON_BIN"

echo "[+] v7.6.1 compile"
"$PYTHON_BIN" -m compileall -q src/socmint scripts/connector_runtime_repair_smoke_v7_6_1.py scripts/connector_runtime_installer_smoke_v7_6_0.py

echo "[+] v7.6.1 connector runtime repair smoke"
"$PYTHON_BIN" scripts/connector_runtime_repair_smoke_v7_6_1.py

echo "[+] v7.6.1 v7.6.0 installer regression"
"$PYTHON_BIN" scripts/connector_runtime_installer_smoke_v7_6_0.py

echo "[+] v7.6.1 full dossier regression"
"$PYTHON_BIN" -m pytest -q tests/test_entity_dossier_v7_5.py
