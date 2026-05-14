#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v7.5.3"
python3 -m compileall -q src/socmint

echo "[+] v7.5.3 finalization export verifier tests"
pytest -q \
  tests/test_dossier_finalization_export_verify_v7_5_3.py \
  tests/test_dossier_finalization_export_verify_routes_v7_5_3.py
