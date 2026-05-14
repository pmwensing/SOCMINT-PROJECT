#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v7.5.5"
python3 -m compileall -q src/socmint

echo "[+] v7.5.5 certificate bundle tests"
pytest -q \
  tests/test_dossier_finalization_certificate_bundle_v7_5_5.py \
  tests/test_dossier_finalization_certificate_bundle_routes_v7_5_5.py
