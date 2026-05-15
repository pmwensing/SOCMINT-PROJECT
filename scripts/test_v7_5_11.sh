#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v7.5.11"
python3 -m compileall -q src/socmint

echo "[+] v7.5.11 closeout export bundle tests"
pytest -q \
  tests/test_dossier_finalization_closeout_export_bundle_v7_5_11.py \
  tests/test_dossier_finalization_closeout_export_bundle_routes_v7_5_11.py
