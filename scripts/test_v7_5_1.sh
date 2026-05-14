#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v7.5.1"
python3 -m compileall -q src/socmint

echo "[+] v7.5.1 finalization tests"
pytest -q \
  tests/test_dossier_finalization_v7_5_1.py \
  tests/test_dossier_finalization_routes_v7_5_1.py
