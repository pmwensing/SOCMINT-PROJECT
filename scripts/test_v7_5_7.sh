#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v7.5.7"
python3 -m compileall -q src/socmint

echo "[+] v7.5.7 certificate handoff index tests"
pytest -q \
  tests/test_dossier_finalization_certificate_handoff_index_v7_5_7.py \
  tests/test_dossier_finalization_certificate_handoff_index_routes_v7_5_7.py
