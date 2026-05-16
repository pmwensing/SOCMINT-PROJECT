#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v10.29"
python3 -m compileall -q src/socmint

echo "[+] v10.29 final delivery dashboard API tests"
pytest -q \
  tests/test_v10_29_final_delivery_dashboard_api.py \
  tests/test_v10_29_final_delivery_dashboard_api_routes.py
