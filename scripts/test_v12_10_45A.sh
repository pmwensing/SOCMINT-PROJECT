#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/missing_table_block_detector_v12_10_45A.py
python -m pytest -q tests/test_v12_10_45A_missing_table_block_detector.py
python scripts/missing_table_block_detector_v12_10_45A.py

echo "[+] v12.10.45A missing table block detector passed"
