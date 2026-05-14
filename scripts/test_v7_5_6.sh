#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v7.5.6"
python3 -m compileall -q src/socmint

echo "[+] v7.5.6 certificate bundle verifier tests"
pytest -q \
  tests/test_dossier_finalization_certificate_bundle_verify_v7_5_6.py \
  tests/test_dossier_finalization_certificate_bundle_verify_routes_v7_5_6.py
