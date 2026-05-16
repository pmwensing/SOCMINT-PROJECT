#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v10.25"
python3 -m compileall -q src/socmint

echo "[+] v10.25 final delivery operator console tests"
pytest -q \
  tests/test_v10_25_final_delivery_operator_console.py \
  tests/test_v10_25_final_delivery_operator_console_routes.py
