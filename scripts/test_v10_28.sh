#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v10.28"
python3 -m compileall -q src/socmint

echo "[+] v10.28 final delivery capsule export pack tests"
pytest -q \
  tests/test_v10_28_final_delivery_capsule_export_pack.py \
  tests/test_v10_28_final_delivery_capsule_export_pack_routes.py
