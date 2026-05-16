#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v10.26"
python3 -m compileall -q src/socmint

echo "[+] v10.26 final delivery audit trail tests"
pytest -q \
  tests/test_v10_26_final_delivery_audit_trail.py \
  tests/test_v10_26_final_delivery_audit_trail_routes.py
