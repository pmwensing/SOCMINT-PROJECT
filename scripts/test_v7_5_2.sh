#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v7.5.2"
python3 -m compileall -q src/socmint

echo "[+] v7.5.2 finalization export tests"
pytest -q \
  tests/test_dossier_finalization_export_v7_5_2.py \
  tests/test_dossier_finalization_export_routes_v7_5_2.py
