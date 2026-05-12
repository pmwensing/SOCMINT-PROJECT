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
  echo "[!] Then rerun: bash scripts/test_v7_7_0.sh"
  exit 1
fi

echo "[+] v7.7.0 using $PYTHON_BIN"

echo "[+] v7.7.0 compile"
"$PYTHON_BIN" -m compileall -q src/socmint scripts/spine_intelligence_smoke_v7_7_0.py scripts/connector_runtime_repair_smoke_v7_6_1.py

echo "[+] v7.7.0 Spine intelligence smoke"
"$PYTHON_BIN" scripts/spine_intelligence_smoke_v7_7_0.py

echo "[+] v7.7.0 v7.6.1 runtime repair regression"
"$PYTHON_BIN" scripts/connector_runtime_repair_smoke_v7_6_1.py

echo "[+] v7.7.0 full dossier regression"
"$PYTHON_BIN" -m pytest -q tests/test_entity_dossier_v7_5.py
