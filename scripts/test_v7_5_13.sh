#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v7.5.13"
python3 -m compileall -q src/socmint

echo "[+] v7.5.13 master delivery index tests"
pytest -q \
  tests/test_dossier_finalization_master_delivery_index_v7_5_13.py \
  tests/test_dossier_finalization_master_delivery_index_routes_v7_5_13.py
