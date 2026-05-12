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

echo "[+] v8.2.0 membership quota compile"
"$PYTHON_BIN" -m compileall -q src/socmint/membership.py src/socmint/membership_routes.py tests/test_membership_quotas_v8_2.py

echo "[+] v8.2.0 membership quota tests"
"$PYTHON_BIN" -m pytest -q tests/test_membership_quotas_v8_2.py

echo "[+] v8.2.0 membership quota smoke passed"
