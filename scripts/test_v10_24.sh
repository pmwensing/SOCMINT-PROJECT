#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v10.24"
python3 -m compileall -q src/socmint

echo "[+] v10.24 final delivery workspace tests"
pytest -q \
  tests/test_v10_24_final_delivery_workspace.py \
  tests/test_v10_24_final_delivery_workspace_routes.py
