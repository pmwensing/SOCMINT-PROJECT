#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile v10.27"
python3 -m compileall -q src/socmint

echo "[+] v10.27 final delivery evidence capsule tests"
pytest -q \
  tests/test_v10_27_final_delivery_evidence_capsule.py \
  tests/test_v10_27_final_delivery_evidence_capsule_routes.py
