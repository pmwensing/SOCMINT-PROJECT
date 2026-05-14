#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v7.5.9"
python3 -m compileall -q src/socmint

echo "[+] v7.5.9 handoff export verifier tests"
pytest -q \
  tests/test_dossier_finalization_handoff_export_verify_v7_5_9.py \
  tests/test_dossier_finalization_handoff_export_verify_routes_v7_5_9.py
