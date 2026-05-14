#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v7.5.10"
python3 -m compileall -q src/socmint

echo "[+] v7.5.10 closeout report tests"
pytest -q \
  tests/test_dossier_finalization_closeout_report_v7_5_10.py \
  tests/test_dossier_finalization_closeout_report_routes_v7_5_10.py
