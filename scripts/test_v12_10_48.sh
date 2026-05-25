#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/full_db_smoke_trace_capture_v12_10_48.py
python -m pytest -q tests/test_v12_10_48_full_db_smoke_trace_capture.py
python scripts/full_db_smoke_trace_capture_v12_10_48.py

echo "[+] v12.10.48 full DB smoke trace capture passed"
